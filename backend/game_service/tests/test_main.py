from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_closes_resources_in_shutdown_order():
    events = []

    manager = MagicMock()
    manager.start = AsyncMock(side_effect=lambda: events.append("manager.start"))
    manager.stop = AsyncMock(side_effect=lambda: events.append("manager.stop"))

    redis_client = MagicMock()
    redis_client.close = AsyncMock(side_effect=lambda: events.append("redis.close"))

    quiz_client = MagicMock()
    quiz_client.start = AsyncMock(side_effect=lambda: events.append("quiz.start"))
    quiz_client.close = AsyncMock(side_effect=lambda: events.append("quiz.close"))

    with (
        patch("app.main.get_room_manager", return_value=manager),
        patch("app.main.get_redis_client", return_value=redis_client),
        patch("app.main.QuizServiceClient", return_value=quiz_client),
        patch("app.main.init_telemetry"),
        patch("app.main.shutdown_telemetry", side_effect=lambda: events.append("telemetry.shutdown")),
    ):
        async with lifespan(app):
            pass

    assert events == [
        "manager.start",
        "quiz.start",
        "quiz.close",
        "manager.stop",
        "redis.close",
        "telemetry.shutdown",
    ]
