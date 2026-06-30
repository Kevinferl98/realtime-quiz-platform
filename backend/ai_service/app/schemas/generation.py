from pydantic import BaseModel, Field
from typing import List, Optional

class QuizGenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The theme or description on which to base the quiz"
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of questions to generate (min 1, max 15)"
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty level (easy, medium, hard)"
    )

class QuestionFields(BaseModel):
    question_text: str = Field(..., description="The text of the question")
    options: List[str] = Field(..., description="List of answer options")
    correct_answer: str = Field(..., description="The exact string corresponding to the correct answer")

class QuizGenerateResponse(BaseModel):
    title: str = Field(..., description="Title generated for the quiz")
    description: Optional[str] = Field(None, description="Brief description of the quiz")
    questions: List[QuestionFields] = Field(..., description="List of generated questions")