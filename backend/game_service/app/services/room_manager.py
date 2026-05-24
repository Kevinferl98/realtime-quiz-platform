import asyncio
import logging
from contextlib import suppress
from typing import Dict, Optional
from fastapi import WebSocket
from app.services.redis_client import RedisClient
from app.services.connection_manager import ConnectionManager
from app.services.quiz_engine import QuizEngine

logger = logging.getLogger(__name__)

QUIZ_LOCK_TTL = 60

class RoomManager:
    """Coordinates real-time quiz rooms by binding networking, distributed state, and game loops."""
    def __init__(self, redis_client: RedisClient, connection_manager: ConnectionManager) -> None:
        self._redis = redis_client
        self._connection_manager = connection_manager

        self._quiz_tasks: Dict[str, asyncio.Task] = {}
        self._ws_to_player: Dict[WebSocket, str] = {}
        self._answer_events: Dict[str, asyncio.Event] = {}

        self._global_lock = asyncio.Lock()
        self._subscribe_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Starts the background distributed Redis Pub/Sub listener service."""
        async with self._global_lock:
            if self._running:
                return
            self._running = True

        self._subscribe_task = asyncio.create_task(self._listen_redis_pubsub())
        logger.info("RoomManager Core Engine started, listening to Pub/Sub")

    async def stop(self) -> None:
        """Cancels all active quiz loops and background subscription listeners."""
        self._running = False

        if self._subscribe_task:
            self._subscribe_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._subscribe_task

        # Cancel all running quizzes to ensure clean worker shutdown without memory leaks.
        async with self._global_lock:
            for task in self._quiz_tasks.values():
                task.cancel()
            for task in self._quiz_tasks.values():
                with suppress(asyncio.CancelledError):
                    await task
            self._quiz_tasks.clear()

        logger.info("RoomManager terminated successfully")

    async def connect(self, room_id: str, websocket: WebSocket) -> None:
        """Delegates incoming physical WebSocket routing to the ConnectionManager mapping."""
        await self._connection_manager.add_connection(room_id, websocket)
        logger.debug("WebSocket source successfully registered", extra={"room_id": room_id})

    async def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        """Handles connection teardown, removing player sessions and cleanup of empty rooms."""
        player_id = self._ws_to_player.pop(websocket, None)
        remaining_count = await self._connection_manager.remove_connection(room_id, websocket)

        # Automatically shutdown game tasks if the room becomes empty.
        if remaining_count == 0:
            await self._cleanup_room_resources(room_id)

        if player_id:
            await self._redis.remove_player(room_id, player_id)
            players = await self._redis.get_players(room_id)
            await self._redis.publish_room_message(
                room_id, {
                    "type": "player_left",
                    "players": [p["name"] for p in players]
                }
            )

        logger.debug("WebSocket source disconnected and deallocated", extra={"room_id": room_id})

    async def register_player_ws(self, websocket: WebSocket, player_id: str) -> None:
        """Maps a verified WebSocket connection to its unique internal player ID string."""
        self._ws_to_player[websocket] = player_id

    async def start_quiz(self, room_id: str) -> None:
        """Acquires a distributed lock and spawns a background game loop for the room."""
        lock_key = f"quiz_lock:{room_id}"
        acquired = await self._redis.acquire_lock(lock_key, QUIZ_LOCK_TTL)
        if not acquired:
            logger.warning("Cannot start quiz: lock already acquired by another instance", extra={"room_id": room_id})
            return

        async with self._global_lock:
            if room_id in self._quiz_tasks:
                await self._redis.release_lock(lock_key)
                logger.warning("Quiz for this room is already running locally", extra={"room_id": room_id})
                return

            engine = QuizEngine(room_id, lock_key, self._redis, self._answer_events)
            task = asyncio.create_task(self._wrapped_quiz_runner(room_id, engine))
            self._quiz_tasks[room_id] = task

    async def _wrapped_quiz_runner(self, room_id: str, engine: QuizEngine) -> None:
        """Safely executes the quiz lifecycle and guarantees lock release on termination."""
        try:
            await engine.run_lifecycle()
        finally:
            async with self._global_lock:
                self._quiz_tasks.pop(room_id, None)
            await self._redis.release_lock(engine.lock_key)

    async def _cleanup_room_resources(self, room_id: str) -> None:
        """Forcefully halts and unregisters game loops linked to a dead room ID."""
        async with self._global_lock:
            task = self._quiz_tasks.pop(room_id, None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        logger.info("Room resources and tasks released (empty room)", extra={"room_id": room_id})

    async def _listen_redis_pubsub(self) -> None:
        """Mounts the primary cross-instance message router subscription broker."""
        await self._redis.subscribe_rooms(self._handle_inbound_pubsub_msg)

    async def _handle_inbound_pubsub_msg(self, room_id: str, message: dict) -> None:
        """Processes cross-process notifications and dispatches payloads to local WebSockets."""
        if message.get("type") == "answer_submitted":
            q_idx = message.get("current_question_index")
            event_key = f"{room_id}:{q_idx}"

            # Unblocks the sleeping local QuizEngine instantly if everyone answered early.
            event = self._answer_events.get(event_key)
            if event:
                answers_count = await self._redis.count_answers(room_id, q_idx)
                players = await self._redis.get_players(room_id)
                if players and answers_count >= len(players):
                    event.set()

        # Execute local broadcast outside global orchestration locks.
        stale_sockets = await self._connection_manager.broadcast_to_room(room_id, message)

        for ws in stale_sockets:
            await self.disconnect(room_id, ws)