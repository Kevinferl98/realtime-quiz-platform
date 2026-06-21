from fastapi import Depends, HTTPException
from app.repositories.quiz_repository import QuizRepository
from app.services.quiz_service import QuizService
from app.db.mongo_client import mongo_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from my_observability import get_logger

logger = get_logger(__name__)
security_scheme = HTTPBearer()

def get_quiz_repository() -> QuizRepository:
    return QuizRepository(mongo_db.quizzes)

def get_quiz_service(repo: QuizRepository = Depends(get_quiz_repository)) -> QuizService:
    return QuizService(repo)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        return payload
    except Exception as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")