import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router
from app.core.config import config
from app.exception import DomainError
from app.exception_handlers import domain_error_handler, global_exception_handler
from app.services.quiz_grpc_server import serve as serve_grpc
from app.db.mongo_client import mongo_db
from my_observability import (
    setup_observability,
    setup_fastapi_logging,
    init_telemetry,
    shutdown_telemetry
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

INFRASTRUCTURE_LOGGERS = {
    "pymongo": {"level": "WARNING"}
}

setup_observability(
    log_level=config.LOG_LEVEL,
    extra_loggers=INFRASTRUCTURE_LOGGERS
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_telemetry(
        service_name=config.OTEL_SERVICE_NAME,
        environment=config.ENV,
        endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
        protocol="grpc"
    )
    grpc_task = asyncio.create_task(serve_grpc())
    print("gRPC server stated on port 50051")
    mongo_db.connect()

    yield

    grpc_task.cancel()
    print("gRPC server stopped")
    mongo_db.close()
    shutdown_telemetry()

app = FastAPI(lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app)
setup_fastapi_logging(app)

app.include_router(router)
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, global_exception_handler)