from fastapi import FastAPI
from app.api.routes import router
from app.api.routes_ws import router_ws
from app.core.config import config
from app.dependencies import get_room_manager
from app.services.quiz_grpc_client import QuizServiceClient
from contextlib import asynccontextmanager
from my_observability import (
    setup_observability,
    setup_fastapi_logging,
    init_telemetry,
    shutdown_telemetry
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

setup_observability(
    log_level=config.LOG_LEVEL
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_telemetry(
        service_name=config.OTEL_SERVICE_NAME,
        environment=config.ENV,
        endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
        protocol="grpc"
    )

    # Room Manager initialization
    manager = get_room_manager()
    await manager.start()
    app.state.room_manager = manager

    # gRPC Client initialization
    quiz_client = QuizServiceClient()
    await quiz_client.start()
    app.state.quiz_client = quiz_client

    yield

    # Clean after shutdown
    await quiz_client.close()
    await manager.stop()
    shutdown_telemetry()

app = FastAPI(lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app)
setup_fastapi_logging(app)

app.include_router(router)
app.include_router(router_ws)