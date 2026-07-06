from fastapi import Request, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.services.quiz_generator_service import QuizGeneratorService
from app.core.config import config
from app.core.security import decode_access_token
from app.exception import AuthenticationError
from my_observability import get_logger

logger = get_logger(__name__)
security_scheme = HTTPBearer()

async def get_quiz_service(request: Request) -> QuizGeneratorService:
    ollama_client = request.app.state.ollama_client
    prompt_manager = request.app.state.prompt_manager

    return QuizGeneratorService(
        ollama_client=ollama_client,
        model_name=config.MODEL_NAME,
        prompt_manager=prompt_manager
    )

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> None:
    token = credentials.credentials
    try:
        decode_access_token(token)
    except Exception as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise AuthenticationError()