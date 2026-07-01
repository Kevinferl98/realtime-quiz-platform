class DomainError(Exception):
    """Base class for domain errors"""
    def __init__(self, status_code: int, title: str, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.title = title
        self.detail = detail

class PromptNotFoundError(DomainError):
    """Raised when a specific prompt template cannot be located."""
    def __init__(self, detail: str = "The requested prompt template could not be found."):
        super().__init__(
            status_code = 404,
            title = "Prompt Template Not Found",
            detail = detail
        )

class AIProviderError(DomainError):
    def __init__(self, status_code: int, title: str, detail: str):
        super().__init__(
            status_code = status_code,
            title = title,
            detail = detail
        )