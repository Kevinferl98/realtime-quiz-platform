from fastapi import Request
from app.services.quiz_generator_service import QuizGeneratorService
from app.core.config import config

async def get_quiz_service(request: Request) -> QuizGeneratorService:
    ollama_client = request.app.state.ollama_client
    prompt_manager = request.app.state.prompt_manager

    return QuizGeneratorService(
        ollama_client=ollama_client,
        model_name=config.MODEL_NAME,
        prompt_manager=prompt_manager
    )