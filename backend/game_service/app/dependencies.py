from app.services.redis_client import RedisClient
from app.services.room_manager import RoomManager
from app.services.connection_manager import ConnectionManager
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from my_observability import get_logger

_redis_instance = RedisClient()
_connection_manager_instance = ConnectionManager()
_manager_instance = RoomManager(redis_client=_redis_instance, connection_manager=_connection_manager_instance)

logger = get_logger(__name__)
security_scheme = HTTPBearer()

def get_redis_client() -> RedisClient:
    return _redis_instance

def get_room_manager() -> RoomManager:
    return _manager_instance

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        return payload
    except Exception as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")