import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.services.redis_client import RedisClient
from app.schemas.multiplayer import Player

@pytest.fixture
def redis_client():
    client = RedisClient()
    client.redis = MagicMock()

    async_methods = (
        "hset",
        "hgetall",
        "set",
        "get",
        "smembers",
        "zincrby",
        "zrevrange",
        "publish",
        "eval"
    )

    for method in async_methods:
        setattr(client.redis, method, AsyncMock())

    client.redis.eval.return_value = 1
    client._create_room_script = AsyncMock(return_value=1)

    return client

@pytest.fixture
def redis_pipeline(redis_client):
    pipeline = MagicMock()
    pipe = MagicMock()

    pipe.execute = AsyncMock()
    pipeline.__aenter__ = AsyncMock(return_value=pipe)
    pipeline.__aexit__ = AsyncMock(return_value=None)

    redis_client.redis.pipeline.return_value = pipeline

    return pipe

@pytest.mark.asyncio
async def test_create_room(redis_client):
    questions = [
        {
            "id": "q1",
            "text": "Text",
            "correct_option": "B",
        },
    ]

    result = await redis_client.create_room(
        room_id="123",
        owner_id="owner",
        quiz_id="quiz1",
        questions=questions,
        ttl_seconds=50,
    )

    assert result is True

    redis_client._create_room_script.assert_awaited_once()

    call = redis_client._create_room_script.await_args

    assert call.kwargs["keys"] == [
        "room:123",
        "room:123:questions",
    ]

    assert call.kwargs["args"][0] == "123"
    assert call.kwargs["args"][1] == "owner"
    assert call.kwargs["args"][2] == "quiz1"
    assert json.loads(call.kwargs["args"][3]) == questions
    assert call.kwargs["args"][4] == 50

@pytest.mark.asyncio
async def test_get_room_meta(redis_client):
    redis_client.redis.hgetall.return_value = {
        "room_id": "123",
        "owner_id": "owner",
        "quiz_id": "quiz1",
        "status": "STARTED",
        "current_question_index": "2",
    }

    result = await redis_client.get_room_meta("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123")

    assert result["room_id"] == "123"
    assert result["owner_id"] == "owner"
    assert result["quiz_id"] == "quiz1"
    assert result["status"] == "STARTED"
    assert result["current_question_index"] == 2

@pytest.mark.asyncio
async def test_add_player(redis_client, redis_pipeline):
    player = Player(player_id="p1", name="John")

    await redis_client.add_player(
        room_id="123",
        player=player,
        ttl_seconds=60,
    )

    redis_client.redis.pipeline.assert_called_once_with(transaction=True)

    assert redis_pipeline.hset.call_args == call(
        "room:123:players",
        "p1",
        "John"
    )

    assert redis_pipeline.zadd.call_args == call(
        "room:123:scores",
        {"p1": 0},
    )

    redis_pipeline.expire.assert_has_calls(
        [
            call("room:123:players", 60),
            call("room:123:scores", 60),
        ],
        any_order=True,
    )

    redis_pipeline.execute.assert_awaited_once_with()

@pytest.mark.asyncio
async def test_get_players(redis_client):
    redis_client.redis.hgetall.return_value = {
        "p1": "John",
        "p2": "Jane",
    }

    result = await redis_client.get_players("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123:players")

    assert len(result) == 2

@pytest.mark.asyncio
async def test_get_players_returns_empty_list_when_room_has_no_players(redis_client):
    redis_client.redis.hgetall.return_value = {}

    players = await redis_client.get_players("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123:players")
    assert players == []

@pytest.mark.asyncio
async def test_remove_player(redis_client, redis_pipeline):
    await redis_client.remove_player(
        room_id="123",
        player_id="p1",
    )

    redis_client.redis.pipeline.assert_called_once_with(transaction=True)

    assert redis_pipeline.hdel.call_args == call(
        "room:123:players",
        "p1",
    )

    assert redis_pipeline.zrem.call_args == call(
        "room:123:scores",
        "p1",
    )

    redis_pipeline.execute.assert_awaited_once_with()

@pytest.mark.asyncio
async def test_increment(redis_client):
    await redis_client.increment_score("123", "p1", 3)
    redis_client.redis.zincrby.assert_called_once_with("room:123:scores", 3, "p1")

@pytest.mark.asyncio
async def test_publish_room_message(redis_client):
    await redis_client.publish_room_message("123", {"type": "msg"})
    redis_client.redis.publish.assert_called_once()

@pytest.mark.asyncio
async def test_subscribe_rooms(redis_client):
    pubsub_mock = MagicMock()
    pubsub_mock.psubscribe = AsyncMock()
    async def fake_listen():
        yield {"type":"pmessage","channel":"room_123","data":'{"type":"msg"}'}
    pubsub_mock.listen = fake_listen
    redis_client.redis.pubsub.return_value = pubsub_mock
    handler = AsyncMock()
    await redis_client.subscribe_rooms(handler)
    handler.assert_called_once_with("123", {"type":"msg"})

@pytest.mark.asyncio
async def test_locks(redis_client):
    redis_client.redis.set.return_value = True
    acquired = await redis_client.acquire_lock("key1")
    assert acquired is True

    redis_client.redis.set.return_value = False
    acquired = await redis_client.acquire_lock("key1")
    assert acquired is False

    redis_client._locks["key1"] = "val"
    redis_client.redis.eval.return_value = 1
    released = await redis_client.release_lock("key1")
    assert released is True

    redis_client._locks.pop("key1")
    released = await redis_client.release_lock("key1")
    assert released is False

@pytest.mark.asyncio
async def test_save_answer(redis_client):
    room_id = "room123"
    q_index = 0
    player_id = "player_1"
    answer = "A"
    
    fixed_time = 1711000000.0
    with patch("time.time", return_value=fixed_time):
        await redis_client.save_answer(room_id, q_index, player_id, answer)
    
    expected_key = f"room:{room_id}:answers:{q_index}"
    expected_value = json.dumps({
        "answer": answer,
        "ts": fixed_time
    })
    
    redis_client.redis.hset.assert_called_once_with(
        expected_key,
        player_id,
        expected_value
    )

@pytest.mark.asyncio
async def test_get_answers_success(redis_client):
    room_id = "room123"
    q_index = 0
    
    mock_data = {
        "p1": json.dumps({"answer": "A", "ts": 100.0}),
        "p2": json.dumps({"answer": "B", "ts": 101.5})
    }
    redis_client.redis.hgetall.return_value = mock_data
    
    result = await redis_client.get_answers(room_id, q_index)
    
    assert len(result) == 2
    assert result["p1"]["answer"] == "A"
    assert isinstance(result["p2"]["ts"], float)
    assert result["p2"]["ts"] == 101.5
    redis_client.redis.hgetall.assert_called_once_with(f"room:{room_id}:answers:{q_index}")

@pytest.mark.asyncio
async def test_get_answers_empty(redis_client):
    redis_client.redis.hgetall.return_value = {}
    
    result = await redis_client.get_answers("room123", 0)
    
    assert result == {}
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_set_question_start(redis_client):
    room_id = "room123"
    ttl = 30
    fixed_time = 1711000000.0
    
    with patch("time.time", return_value=fixed_time):
        await redis_client.set_question_start(room_id, ttl)
    
    redis_client.redis.set.assert_called_once_with(
        f"room:{room_id}:question_start",
        fixed_time,
        ex=ttl
    )

@pytest.mark.asyncio
async def test_get_question_start_found(redis_client):
    room_id = "room123"
    redis_client.redis.get.return_value = "1711000000.0"
    
    result = await redis_client.get_question_start(room_id)
    
    assert isinstance(result, float)
    assert result == 1711000000.0
    redis_client.redis.get.assert_called_once_with(f"room:{room_id}:question_start")

@pytest.mark.asyncio
async def test_get_question_start_none(redis_client):
    redis_client.redis.get.return_value = None
    
    result = await redis_client.get_question_start("room123")
    
    assert result is None

@pytest.mark.asyncio
async def test_get_leaderboard_returns_empty_list_when_no_scores(redis_client):
    redis_client.redis.zrevrange.return_value = []

    result = await redis_client.get_leaderboard(room_id="123", limit=5)

    redis_client.redis.zrevrange.assert_called_once_with(
        "room:123:scores",
        0,
        4,
        withscores=True
    )
    redis_client.redis.pipeline.assert_not_called()
    assert result == []

async def test_get_leaderboard(redis_client, redis_pipeline):
    redis_client.redis.zrevrange.return_value = [
        ("p1", 100),
        ("p2", 75),
        ("p3", 50)
    ]

    redis_pipeline.execute.return_value = ["John", "Jane", "James"]

    result = await redis_client.get_leaderboard(
        room_id="123",
        limit=5,
    )

    redis_client.redis.zrevrange.assert_called_once_with(
        "room:123:scores",
        0,
        4,
        withscores=True,
    )

    redis_client.redis.pipeline.assert_called_once_with(transaction=False)

    redis_pipeline.hget.assert_has_calls(
        [
            call("room:123:players", "p1"),
            call("room:123:players", "p2"),
            call("room:123:players", "p3"),
        ],
        any_order=True,
    )

    redis_pipeline.execute.assert_awaited_once_with()

    assert result == [
        {"player_id": "p1", "name": "John", "score": 100},
        {"player_id": "p2", "name": "Jane", "score": 75},
        {"player_id": "p3", "name": "James", "score": 50},
    ]