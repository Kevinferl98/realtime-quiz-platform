from pydantic import BaseModel, Field
from typing import List, Optional

class QuizGenerateRequest(BaseModel):
    topic: str = Field(
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
    options: List[str] = Field(..., min_length=4, max_length=4, description="List of answer options")
    correct_answer_index: int = Field(..., ge=0, le=3, description="The 0-based index of the correct answer inside the options array (0 to 3).")

class QuizGenerateResponse(BaseModel):
    title: str = Field(..., description="Title generated for the quiz")
    description: Optional[str] = Field(None, description="Brief description of the quiz")
    questions: List[QuestionFields] = Field(..., description="List of generated questions")