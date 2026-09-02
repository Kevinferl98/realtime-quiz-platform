import uuid
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError, TypeAdapter, BaseModel
from app.models.multiplayer import Player
from app.domain.room_session import RoomSession
from my_observability import get_logger
from app.services.redis.redis_client import RedisClient
from app.services.room_manager import RoomManager
from app.schemas.multiplayer import Room, RoomStatus
from app.schemas.websocket_messages import (
    ClientMessage,
    JoinAction,
    StartAction,
    AnswerAction,
    ErrorMessage,
    RoleMessage,
    PlayerJoinedMessage,
    AnswerSubmittedMessage
)
from app.schemas.auth import WSTicket, AccessTokenPayload

logger = get_logger(__name__)

client_message_adapter = TypeAdapter(ClientMessage)

class RoomWebSocketService:
    """Manages the lifecycle of individual WebSocket connections, parsing inbound user actions."""
    def __init__(self, manager: RoomManager, redis: RedisClient):
        self.manager = manager
        self.redis = redis

    async def handle_connection(self, websocket: WebSocket, room_id: str, ticket: str | None) -> None:
        """Accepts a connection, validates the ticket and starts the event loop."""
        registered = False
        try:
            ticket_data = await self._consume_ticket(ticket, room_id)
            if ticket_data.room_id != room_id:
                raise ValueError("Ticket not valid for this room")

            await websocket.accept()
            await self.manager.connect(room_id, websocket)
            registered = True

            session = await self._initialize_session(websocket, room_id, ticket_data.user_payload, ticket_data.player_id, ticket_data.username)
            await self.manager.register_player_ws(websocket, session.player_id)
            await self._event_loop(websocket, room_id, session)
        except ValueError as e:
            logger.warning(f"Rejected WebSocket connection: {e}")
            await websocket.close()
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected gracefully or timed out for room {room_id}")
        except Exception as e:
            logger.error(f"WebSocket closed with error in room {room_id}: {e}")
        finally:
            if registered:
                await self.handle_disconnect(websocket, room_id)

    async def _consume_ticket(self, ticket: str | None, room_id: str) -> WSTicket:
        """Atomically retrieves and deletes the ticket from Redis to prevent replay attacks."""
        if not ticket:
            return WSTicket(
                player_id=str(uuid.uuid4()),
                username=None,
                user_payload=None,
                room_id=room_id
            )

        ticket_data = await self.redis.retrieve_and_delete_ticket(ticket)
        if not ticket_data:
            logger.warning(f"Rejecting WS connection: invalid or expired ticket ({ticket})")
            raise ValueError("Invalid or expired ticket")

        return ticket_data

    async def _initialize_session(
            self,
            websocket: WebSocket,
            room_id: str,
            user_payload: AccessTokenPayload | None,
            player_id: str,
            username: str | None
    ) -> RoomSession:
        """Evaluates room state requirements and registers the initial session."""
        room = await self.redis.get_room(room_id)
        if not room:
            await self._send_message(
                websocket,
                ErrorMessage(code="ROOM_NOT_FOUND", message="Room not found")
            )
            await websocket.close()
            raise Exception("Room not found")

        # Prevent late-joins to keep quiz state and scoring synchronization coherent.
        if room.status != RoomStatus.CREATED:
            await self._send_message(
                websocket,
                ErrorMessage(code="ROOM_ALREADY_STARTED", message="Room already started")
            )
            await websocket.close()
            raise Exception("Room already started")

        role = self._resolve_role(player_id, room)

        session = RoomSession(
            player_id=player_id,
            username=username,
            role=role,
            user_payload=user_payload
        )

        await self._send_message(
            websocket,
            RoleMessage(role=session.role, player_id=session.player_id)
        )

        # Anonymous players are deferred from the Redis roster until they explicitly pick a name.
        if session.is_host or session.is_authenticated:
            await self._add_player(session, room_id, websocket)
        
        await self._broadcast_player_joined(room_id)

        return session

    async def _event_loop(self, websocket: WebSocket, room_id: str, session: RoomSession) -> None:
        """Continuously streams incoming JSON frames and routes them to explicit action handlers."""
        async for data in websocket.iter_json():
            try:
                message: ClientMessage = client_message_adapter.validate_python(data)

                match message:
                    case JoinAction():
                        await self._handle_join(room_id, session, message, websocket)
                    case StartAction():
                        await self._handle_start(websocket, room_id, session)
                    case AnswerAction():
                        await self._handle_answer(websocket, room_id, session, message)
            except ValidationError as e:
                logger.warning(f"Invalid WebSocket payload received in room {room_id}: {e}")
                await self._send_message(
                    websocket,
                    ErrorMessage(
                        code="INVALID_PAYLOAD",
                        message="Invalid message schema or payload content"
                    )
                )
    
    async def handle_disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Cleans up the localized active session inside RoomManager when the socket drops."""
        await self.manager.disconnect(room_id, websocket)

    async def _handle_join(self, room_id: str, session: RoomSession, data: JoinAction, websocket: WebSocket) -> None:
        """Finalizes the profile registration for non-authenticated guest players."""
        if session.is_authenticated:
            return

        session.set_username(data.name)

        await self._add_player(session, room_id, websocket)

        await self._broadcast_player_joined(room_id)

    async def _handle_start(self, websocket: WebSocket, room_id: str, session: RoomSession) -> None:
        """Triggers the quiz state transition if the requesting session is the designated host."""
        if not session.is_host:
            await self._send_message(
                websocket,
                ErrorMessage(code="FORBIDDEN", message="Only host can start the quiz")
            )
            return
        
        await self.manager.start_quiz(room_id)

    async def _handle_answer(self, websocket: WebSocket, room_id: str, session: RoomSession, data: AnswerAction) -> None:
        """Saves a player submission and notifies the cluster for real-time early-cutoff logic."""
        room_meta = await self.redis.get_room(room_id)
        if not room_meta:
            return

        if room_meta.status != RoomStatus.STARTED:
            await self._send_message(
                websocket,
                ErrorMessage(code="FORBIDDEN", message="The room has not started yet")
            )
            return

        question_index = room_meta.current_question_index

        saved = await self.redis.save_answer(
            room_id,
            question_index,
            session.player_id,
            data.answer
        )

        if not saved:
            await self._send_message(
                websocket,
                ErrorMessage(
                    code="ANSWER_ALREADY_SUBMITTED",
                    message="You have already submitted an answer for this question"
                )
            )
            return

        # Broadcast via Pub/Sub to allow any horizontal application instance to process the cutoff check.
        msg = AnswerSubmittedMessage(
            current_question_index=question_index
        )
        await self.redis.publish_room_message(room_id, msg.model_dump())
    
    def _resolve_role(self, player_id: str, room: Room) -> str:
        """Evaluates whether the caller maps directly to the unique creator of the room registry."""
        return "host" if player_id == room.owner_id else "player"
    
    async def _broadcast_player_joined(self, room_id: str) -> None:
        """Queries the complete room roster and distributes it to the cluster broadcast channel."""
        players = await self.redis.get_players(room_id)

        msg = PlayerJoinedMessage(
            players=[p.name for p in players if p.name]
        )

        await self.redis.publish_room_message(room_id, msg.model_dump())

    async def _send_message(self, websocket: WebSocket, message: BaseModel) -> None:
        """Helper to send a strongly typed Pydantic message model over the socket."""
        await websocket.send_json(message.model_dump())

    async def _add_player(self, session: RoomSession, room_id: str, websocket: WebSocket) -> None:
        added = await self.redis.add_player_if_not_exists(
            room_id,
            Player(player_id=session.player_id, name=session.username)
        )

        if not added:
            logger.warning(f"Blocked duplicate connection attempt for player {session.player_id} in room {room_id}")
            await self._send_message(
                websocket,
                ErrorMessage(
                    code="PLAYER_ALREADY_CONNECTED",
                    message="You are already connected to this room from another tab or device"
                )
            )
            await websocket.close()
            raise Exception("Player already connected")