from fastapi import APIRouter
from app.schemas.generation import QuizGenerateRequest, QuizGenerateResponse

router = APIRouter(prefix="/v1/ai", tags=["AI Generation"])

@router.post(
    "/generate",
    response_model=QuizGenerateResponse,
    status_code=200,
    summary="Generate a quiz using AI"
)
def generate_quiz(request: QuizGenerateRequest) -> QuizGenerateResponse:
    return QuizGenerateResponse(
        title="title",
        description="description",
        questions=[]
    )