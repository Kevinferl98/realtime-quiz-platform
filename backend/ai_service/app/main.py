from fastapi import FastAPI
from app.api.routes import router
from app.exception import DomainError
from app.exception_handlers import domain_error_handler, global_exception_handler
from app.core.config import config
from my_observability import (
    setup_observability,
    setup_fastapi_logging,
    get_logger,
    init_telemetry,
    shutdown_telemetry
)
from ollama import AsyncClient
from contextlib import asynccontextmanager
from app.prompts.prompt_manager import PromptManager
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = get_logger(__name__)

setup_observability(
    log_level=config.LOG_LEVEL
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    prompt_manager = PromptManager()
    try:
        prompt_manager.load_prompts()
        app.state.prompt_manager = prompt_manager
    except Exception as exc:
        logger.error(f"Application startup failed due to prompt configuration error: {exc}")
        raise exc

    ollama_client = AsyncClient(
        host=config.OLLAMA_BASE_URL,
        timeout=60.0
    )
    app.state.ollama_client = ollama_client
    logger.info("Ollama client initialized successfully.")

    init_telemetry(
        service_name=config.OTEL_SERVICE_NAME,
        environment=config.ENV,
        endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
        protocol="grpc"
    )

    yield

    await ollama_client.close()
    logger.info("Application shutting down. HTTP client closed.")
    shutdown_telemetry()

app = FastAPI(lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app)
setup_fastapi_logging(app)

app.include_router(router)
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, global_exception_handler)