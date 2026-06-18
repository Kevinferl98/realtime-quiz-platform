import uuid
from fastapi import WebSocket
from app.schemas.multiplayer import Player
from app.auth import get_current_user
from app.domain.room_session import RoomSession
from my_observability import get_logger

logger = get_logger(__name__)

class RoomWebSocketService:
    """Manages the lifecycle of individual WebSocket connections, parsing inbound user actions."""
    def __init__(self, manager, redis):
        self.manager = manager
        self.redis = redis

    async def handle_connection(self, websocket: WebSocket, room_id: str):
        """Accepts a connection, establishes the user session, and boots the main event loop."""
        await websocket.accept()

        await self.manager.connect(room_id, websocket)

        session = await self._initialize_session(websocket, room_id)

        await self.manager.register_player_ws(websocket, session.player_id)

        await self._event_loop(websocket, room_id, session)

    async def _initialize_session(self, websocket: WebSocket, room_id: str):
        """Authenticates the incoming socket connection and evaluates room state requirements."""
        token = websocket.query_params.get("token")
        user_payload = self._authenticate(token)

        player_id, username = self._resolve_identity(user_payload)

        room_meta = await self.redis.get_room_meta(room_id)
        if not room_meta:
            await websocket.send_json({
                "type": "error",
                "code": "ROOM_NOT_FOUND",
                "message": "Room not found"
            })
            await websocket.close()
            raise Exception("Room not found")

        # Prevent late-joins to keep quiz state and scoring synchronization coherent.
        if room_meta.get("started"):
            await websocket.send_json({
                "type": "error",
                "code": "ROOM_ALREADY_STARTED",
                "message": "Room already started"
            })
            await websocket.close()
            raise Exception("Room already started")

        role = self._resolve_role(player_id, room_meta)

        session = RoomSession(
            player_id=player_id,
            username=username,
            role=role,
            user_payload=user_payload
        )

        await websocket.send_json({
            "type": "role",
            "role": session.role,
            "player_id": session.player_id
        })

        # Anonymous players are deferred from the Redis roster until they explicitly pick a name.
        if session.is_host or session.is_authenticated:
            await self.redis.add_player(
                room_id,
                Player(player_id=session.player_id, name=session.username)
            )
        
        await self._broadcast_players(room_id, "player_joined")

        return session

    async def _event_loop(self, websocket: WebSocket, room_id: str, session: RoomSession):
        """Continuously streams incoming JSON frames and routes them to explicit action handlers."""
        try:
            async for data in websocket.iter_json():
                action = data.get("type")

                if action == "join":
                    await self._handle_join(websocket, room_id, session, data)
                elif action == "start":
                    await self._handle_start(websocket, room_id, session)
                elif action == "answer":
                    await self._handle_answer(room_id, session, data)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "code": "UNKNOWN_ACTION",
                        "message": "unknown action"
                    })

        except Exception as e:
            logger.exception("Error in WebSocket loop", exc_info=e)
        finally:
            await self.handle_disconnect(websocket, room_id)
    
    async def handle_disconnect(self, websocket: WebSocket, room_id: str):
        """Cleans up the localized active session inside RoomManager when the socket drops."""
        await self.manager.disconnect(room_id, websocket)

    async def _handle_join(self, websocket: WebSocket, room_id: str, session: RoomSession, data: dict):
        """Finalizes the profile registration for non-authenticated guest players."""
        if session.is_authenticated:
            return
        
        name = data.get("name")
        if not name:
            await websocket.send_json({
                "type": "error",
                "message": "Name required"
            })
            return

        session.set_username(name)

        await self.redis.add_player(
            room_id,
            Player(player_id=session.player_id, name=name)
        )

        await self._broadcast_players(room_id, "player_joined")

    async def _handle_start(self, websocket: WebSocket, room_id: str, session: RoomSession):
        """Triggers the quiz state transition if the requesting session is the designated host."""
        if not session.is_host:
            await websocket.send_json({
                "type": "error",
                "message": "Only host can start the quiz"
            })
            return
        
        await self.manager.start_quiz(room_id)

    async def _handle_answer(self, room_id: str, session: RoomSession, data: dict):
        """Saves a player submission and notifies the cluster for real-time early-cutoff logic."""
        answer = data.get("answer")

        room_meta = await self.redis.get_room_meta(room_id)
        if not room_meta:
            return
        
        question_index = room_meta.get("current_question_index", 0)

        await self.redis.save_answer(
            room_id,
            question_index,
            session.player_id,
            answer
        )

        # Broadcast via Pub/Sub to allow any horizontal application instance to process the cutoff check.
        await self.redis.publish_room_message(room_id, {
            "type": "answer_submitted",
            "current_question_index": question_index,
            "player_id": session.player_id,
        })
    
    def _authenticate(self, token):
        """Verifies JWT claims against core authentication systems, safely swallowing errors."""
        if not token:
            return None

        try:
            return get_current_user(f"Bearer {token}")
        except Exception:
            return None
    
    def _resolve_identity(self, user_payload):
        """Extracts claims from authenticated players or generates a random UUID for guests."""
        if user_payload:
            return (
                user_payload.get("sub"),
                user_payload.get("preferred_username", "User")
            )
        return str(uuid.uuid4()), None
    
    def _resolve_role(self, player_id: str, room_meta: dict):
        """Evaluates whether the caller maps directly to the unique creator of the room registry."""
        return "host" if player_id == room_meta["owner_id"] else "player"
    
    async def _broadcast_players(self, room_id: str, event_type: str):
        """Queries the complete room roster and distributes it to the cluster broadcast channel."""
        players = await self.redis.get_players(room_id)

        await self.redis.publish_room_message(room_id, {
            "type": event_type,
            "players": [p["name"] for p in players]
        })