class DomainError(Exception):
    """Base class for domain errors"""
    def __init__(self, status_code: int, title: str, detail:str):
        super().__init__(detail)
        self.status_code = status_code
        self.title = title
        self.detail = detail

class QuizNotFoundError(DomainError):
    def __init__(self, detail: str = "The requested quiz does not exist."):
        super().__init__(
            status_code=404,
            title="Quiz not found",
            detail=detail
        )

class QuizEmptyError(DomainError):
    def __init__(self, detail: str = "The requested quiz has no questions."):
        super().__init__(
            status_code=500,
            title="Quiz empty",
            detail=detail
        )

class CreateRoomError(DomainError):
    def __init__(self, detail: str = "Unable to create a room."):
        super().__init__(
            status_code=500,
            title="Room creation error",
            detail=detail
        )