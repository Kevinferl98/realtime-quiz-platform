from fastapi import APIRouter, Depends
from app.schemas.generation import QuizGenerateRequest, QuizGenerateResponse
from app.services.quiz_generator_service import QuizGeneratorService
from app.dependencies import get_quiz_service, verify_jwt

router = APIRouter(prefix="/v1/ai", tags=["AI Generation"])

@router.post(
    "/generate",
    response_model=QuizGenerateResponse,
    status_code=200,
    summary="Generate a quiz using AI",
    dependencies=[Depends(verify_jwt)]
)
async def generate_quiz(request: QuizGenerateRequest, quiz_service: QuizGeneratorService = Depends(get_quiz_service)) -> QuizGenerateResponse:
    return await quiz_service.generate_quiz_preview(request)