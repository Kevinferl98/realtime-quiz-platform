from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Response
from app.auth import get_current_user
from app.core.http_cache import cache_control
from app.schemas.quiz import (
    AnswerResponse, AnswerRequest, QuizzesResponse,
    QuizCreateRequest, QuizCreateResponse, QuizDeleteResponse, QuizOut, QuizDetailResponse,
    QuestionOut, QuizzesResponsePaginated
)
from app.services.quiz_service import QuizService
from app.dependencies import get_quiz_service
from my_observability import get_logger
from app.core.config import config

logger = get_logger(__name__)
router = APIRouter(prefix="/quizzes", tags=["quizzes"])

def get_current_user_required(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user

@router.get(
    "/public",
    response_model=QuizzesResponsePaginated,
    summary="List public quizzes"
)
@cache_control(
    max_age=config.CACHE_PUBLIC_QUIZZES_TTL,
    stale_while_revalidate=config.CACHE_PUBLIC_QUIZZES_SWR
)
def list_public_quizzes(
        response: Response,
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        service: QuizService = Depends(get_quiz_service)
):
    quizzes, total = service.list_public_quizzes(page=page, limit=limit)

    logger.info(
        "public_quizzes_listed",
        page=page, limit=limit, count=len(quizzes)
    )

    return QuizzesResponsePaginated(
        quizzes = [QuizOut.model_validate(q) for q in quizzes],
        total=total,
        page=page,
        pages=(total + limit - 1) // limit
    )

@router.get(
    "/mine",
    response_model=QuizzesResponse,
    summary="List user's quizzes"
)
def list_my_quizzes(user=Depends(get_current_user_required), service: QuizService = Depends(get_quiz_service)):
    quizzes = service.list_personal_quizzes(user["sub"])

    logger.info(
        "personal_quizzes_listed",
        user_id= user["sub"], count= len(quizzes)
    )

    return QuizzesResponse(
        quizzes = [QuizOut.model_validate(q) for q in quizzes]
    )

@router.get(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    summary="Get quiz by id",
    responses={404: {"description": "Quiz not found"}}
)
def get_quiz(quiz_id: str = Path(..., min_length=1), service: QuizService = Depends(get_quiz_service)):
    quiz = service.get_quiz_by_id(quiz_id)

    logger.info("quiz_retrieved", quiz_id= quiz_id)

    return QuizDetailResponse(
        quizId=quiz["quizId"],
        title=quiz["title"],
        description=quiz.get("description"),
        questions=[
            QuestionOut.model_validate(q)
            for q in quiz.get("questions", [])
        ]
    )

@router.post(
    "/",
    response_model=QuizCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quiz"
)
def create_quiz(quiz: QuizCreateRequest, user=Depends(get_current_user_required), service: QuizService = Depends(get_quiz_service)):
    quiz_id = service.create_quiz(
        quiz_data=quiz,
        owner_id=user["sub"]
    )

    logger.info(
        "quiz_created",
        quiz_id= quiz_id, user_id= user["sub"]
    )

    return QuizCreateResponse(success=True, quizId=quiz_id)

@router.delete(
    "/{quiz_id}",
    response_model=QuizDeleteResponse,
    summary="Delete quiz",
    responses={
        404: {"description": "Quiz not found"},
        403: {"description": "Forbidden"}
    }
)
def delete_quiz(quiz_id: str = Path(..., min_length=1), user=Depends(get_current_user_required), service: QuizService = Depends(get_quiz_service)):
    service.delete_quiz(quiz_id=quiz_id, user_id=user["sub"])

    logger.info(
        "quiz_deleted",
        quiz_id= quiz_id, user_id= user["sub"]
    )

    return QuizDeleteResponse(success=True)
    
@router.post(
    "/{quiz_id}/answer",
    response_model=AnswerResponse,
    summary="Answer a quiz question"
)
def answer_question(payload: AnswerRequest, quiz_id: str = Path(..., min_length=1), service: QuizService = Depends(get_quiz_service)):
    correct = service.check_answer(quiz_id, payload.question_id, payload.answer)

    return AnswerResponse(correct=correct)