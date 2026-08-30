import pytest
import json
from unittest.mock import AsyncMock, MagicMock, call
from app.services.redis.redis_client import RedisClient
from app.schemas.multiplayer import Question, RoomAnswer
from app.models.multiplayer import Player, LeaderboardEntry

@pytest.fixture
def redis_client():
    client = RedisClient()
    client.redis = MagicMock()

    async_methods = (
        "hset",
        "hgetall",
        "hlen",
        "set",
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
    client._start_quiz_script = AsyncMock(return_value=1)
    client._add_player_script = AsyncMock(return_value=1)
    client.redis.time = AsyncMock(return_value=(1711000000, 0))

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
    questions = [Question(
        id="q1",
        question_text="Text",
        options=[],
        correct_option="B"
    )]

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
        "room:123:players",
        "room:123:scores",
    ]

    assert call.kwargs["args"][0] == "123"
    assert call.kwargs["args"][1] == "owner"
    assert call.kwargs["args"][2] == "quiz1"
    assert json.loads(call.kwargs["args"][3]) == [
        q.model_dump() for q in questions
    ]
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

    result = await redis_client.get_room("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123")

    assert result is not None
    assert result.room_id == "123"
    assert result.owner_id == "owner"
    assert result.quiz_id == "quiz1"
    assert result.status == "STARTED"
    assert result.current_question_index == 2

@pytest.mark.asyncio
async def test_add_player(redis_client, redis_pipeline):
    player = Player(player_id="p1", name="John")

    result = await redis_client.add_player_if_not_exists(
        room_id="123",
        player=player,
    )

    assert result is True

    redis_client._add_player_script.assert_awaited_once()

    call = redis_client._add_player_script.await_args

    assert call.kwargs["keys"] == [
        "room:123:players",
        "room:123:scores"
    ]

    assert call.kwargs["args"][0] == "p1"
    assert call.kwargs["args"][1] == "John"

@pytest.mark.asyncio
async def test_get_players(redis_client):
    redis_client.redis.hgetall.return_value = {
        "p1": "John",
        "p2": "Jane",
        "__room_meta__": "1",
    }

    result = await redis_client.get_players("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123:players")

    assert len(result) == 2
    assert all(player.player_id != "__room_meta__" for player in result)

@pytest.mark.asyncio
async def test_get_players_returns_empty_list_when_room_has_no_players(redis_client):
    redis_client.redis.hgetall.return_value = {}

    players = await redis_client.get_players("123")

    redis_client.redis.hgetall.assert_called_once_with("room:123:players")
    assert players == []

@pytest.mark.asyncio
async def test_count_players_excludes_internal_room_marker(redis_client):
    redis_client.redis.hlen.return_value = 3

    result = await redis_client.count_players("123")

    assert result == 2
    redis_client.redis.hlen.assert_called_once_with("room:123:players")

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
async def test_save_answer(redis_client, redis_pipeline):
    room_id = "123"
    q_index = 0
    player_id = "player_1"
    answer = "A"
    
    expected_timestamp = 1711000000.0
    await redis_client.save_answer(room_id, q_index, player_id, answer)

    redis_client.redis.time.assert_awaited_once()
    redis_client.redis.pipeline.assert_called_once_with(transaction=True)

    assert redis_pipeline.hsetnx.call_args == call(
        "room:123:answers:0",
        "player_1",
        RoomAnswer(answer=answer, timestamp=expected_timestamp).model_dump_json(),
    )

    redis_pipeline.expire.assert_called_once_with("room:123:answers:0", 300, nx=True)
    redis_pipeline.execute.assert_awaited_once_with()

@pytest.mark.asyncio
async def test_get_answers_success(redis_client):
    room_id = "room123"
    q_index = 0
    
    mock_data = {
        "p1": json.dumps({"answer": "A", "timestamp": 100.0}),
        "p2": json.dumps({"answer": "B", "timestamp": 101.5})
    }
    redis_client.redis.hgetall.return_value = mock_data
    
    result = await redis_client.get_answers(room_id, q_index)
    
    assert len(result) == 2
    assert result["p1"].answer == "A"
    assert isinstance(result["p2"].timestamp, float)
    assert result["p2"].timestamp == 101.5
    redis_client.redis.hgetall.assert_called_once_with(f"room:{room_id}:answers:{q_index}")

@pytest.mark.asyncio
async def test_get_answers_empty(redis_client):
    redis_client.redis.hgetall.return_value = {}
    
    result = await redis_client.get_answers("room123", 0)
    
    assert result == {}
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_get_leaderboard_returns_empty_list_when_no_scores(redis_client):
    redis_client.redis.zrevrange.return_value = []

    result = await redis_client.get_leaderboard(room_id="123", limit=5)

    redis_client.redis.zrevrange.assert_called_once_with(
        "room:123:scores",
        0,
        5,
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
        5,
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
        LeaderboardEntry(
            player_id="p1",
            name="John",
            score=100,
        ),
        LeaderboardEntry(
            player_id="p2",
            name="Jane",
            score=75,
        ),
        LeaderboardEntry(
            player_id="p3",
            name="James",
            score=50,
        ),
    ]

@pytest.mark.asyncio
async def test_get_leaderboard_excludes_internal_room_marker(redis_client, redis_pipeline):
    redis_client.redis.zrevrange.return_value = [
        ("p1", 100),
        ("__room_meta__", 0),
    ]
    redis_pipeline.execute.return_value = ["John"]

    result = await redis_client.get_leaderboard("123", limit=5)

    redis_pipeline.hget.assert_called_once_with("room:123:players", "p1")
    assert result == [LeaderboardEntry(player_id="p1", name="John", score=100)]

@pytest.mark.asyncio
async def test_try_start_room(redis_client):
    result = await redis_client.try_start_room(
        room_id="123",
    )

    assert result is True

    redis_client._start_quiz_script.assert_awaited_once()

    call = redis_client._start_quiz_script.await_args

    assert call.kwargs["keys"] == [
        "room:123"
    ]