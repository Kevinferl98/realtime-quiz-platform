from app.services.redis_client import RedisClient
from app.services.room_manager import RoomManager
from app.services.connection_manager import ConnectionManager

_redis_instance = RedisClient()
_connection_manager_instance = ConnectionManager()
_manager_instance = RoomManager(redis_client=_redis_instance, connection_manager=_connection_manager_instance)

def get_redis_client() -> RedisClient:
    return _redis_instance

def get_room_manager() -> RoomManager:
    return _manager_instance