import asyncio
import time
from contextlib import suppress
from typing import Dict
from app.services.redis.redis_client import RedisClient
from my_observability import get_logger
from app.schemas.multiplayer import Question, RoomStatus

logger = get_logger(__name__)

QUESTION_DURATION = 15
LEADERBOARD_DURATION = 8
ANSWER_REVEAL_DURATION = 4

class QuizEngine:
    """Orchestrates the state, timing, and score calculations of a quiz game loop."""
    def __init__(self, room_id: str, lock_key: str, redis_client: RedisClient, events_map: Dict[str, asyncio.Event]):
        self.room_id = room_id
        self.lock_key = lock_key
        self._redis = redis_client
        self._events_map = events_map

    async def run_lifecycle(self) -> None:
        """Executes the complete quiz loop from question progression to the final leaderboard."""
        logger.info("Quiz lifecycle started", room_id=self.room_id)
        try:
            questions = await self._redis.get_questions(self.room_id)
            if not questions:
                logger.warning("No questions found for room", room_id=self.room_id)
                return

            # Initialize room state as started before entering the question loop.
            await self._redis.update_room_status(
                self.room_id,
                status=RoomStatus.STARTED,
            )

            for idx, question in enumerate(questions):
                is_last = idx == len(questions) - 1

                await self._redis.update_room_progress(self.room_id, index=idx)

                await self._redis.publish_room_message(
                    self.room_id,
                    {
                        "type": "question",
                        "question": question.model_dump(mode="json"),
                        "index": idx,
                    }
                )

                question_start = time.time()

                # Suspend execution until all answers are submitted or the timeout expires.
                await self._wait_for_answers_or_timeout(idx)

                await self._process_answers(question, idx, question_start)
                await asyncio.sleep(ANSWER_REVEAL_DURATION)

                await self._publish_leaderboard(final=is_last)

                if not is_last:
                    await asyncio.sleep(LEADERBOARD_DURATION)

            await self._redis.update_room_status(self.room_id, status=RoomStatus.FINISHED)

        except asyncio.CancelledError:
            logger.info("Quiz execution explicitly cancelled", room_id=self.room_id)
            with suppress(Exception):
                await self._redis.update_room_status(
                    self.room_id,
                    status=RoomStatus.CANCELLED,
                )
            raise
        except Exception as e:
            logger.exception("Critical crash in QuizEngine execution loop", room_id=self.room_id, exception=e)
            with suppress(Exception):
                await self._redis.update_room_status(
                    self.room_id,
                    status=RoomStatus.ERROR,
                )
            raise

    async def _wait_for_answers_or_timeout(self, question_index: int) -> None:
        """Blocks until the localized asyncio.Event triggers early or the max duration is reached."""
        event_key = f"{self.room_id}:{question_index}"
        event = self._events_map.setdefault(event_key, asyncio.Event())

        start_time = time.time()

        while time.time() - start_time < QUESTION_DURATION:
            remaining_time = QUESTION_DURATION - (time.time() - start_time)
            if remaining_time <= 0:
                break

            try:
                # Dynamic timeout handling ensures we don't oversleep if woken up falsely.
                await asyncio.wait_for(event.wait(), timeout=remaining_time)
                break
            except asyncio.TimeoutError:
                break

        self._events_map.pop(event_key, None)

    async def _process_answers(self, question: Question, question_index: int, start_time: float) -> None:
        """Evaluates answers from Redis and increments scores with time-based decay logic."""
        answers = await self._redis.get_answers(self.room_id, question_index)

        await self._redis.publish_room_message(
            self.room_id,
            {"type": "answer_result", "correct_answer": question.correct_option}
        )

        correct_option = question.correct_option
        for player_id, data in answers.items():
            if data.answer == correct_option:
                # Linear point scaling: faster answers earn closer to max_points.
                response_time = max(0.0, data.timestamp - start_time)
                time_ratio = min(response_time / QUESTION_DURATION, 1.0)

                max_points, min_points = 1000, 200
                points = int(max_points * (1.0 - time_ratio))
                points = max(points, min_points)

                await self._redis.increment_score(self.room_id, player_id, points)

        await self._redis.delete_answers(self.room_id, question_index)

    async def _publish_leaderboard(self, final: bool = False) -> None:
        """Fetches current scores and publishes the top 5 players to the room channel."""
        leaderboard = await self._redis.get_leaderboard(self.room_id, 5)

        leaderboard = [
            {
                "name": player.name,
                "score": player.score,
            }
            for player in leaderboard
        ]

        await self._redis.publish_room_message(
            self.room_id,
            {
                "type": "leaderboard",
                "final": final,
                "leaderboard": leaderboard,
                "show_for": LEADERBOARD_DURATION,
            },
        )