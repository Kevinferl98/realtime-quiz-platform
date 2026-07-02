from fastapi import FastAPI
from app.api.routes import router
from app.exception import DomainError
from app.exception_handlers import domain_error_handler
from app.core.config import config
from my_observability import (
    setup_observability,
    setup_fastapi_logging
)

setup_observability(
    log_level=config.LOG_LEVEL
)

app = FastAPI()

setup_fastapi_logging(app)

app.include_router(router)
app.add_exception_handler(DomainError, domain_error_handler)