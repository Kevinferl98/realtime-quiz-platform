from fastapi import FastAPI
from app.api.routes import router
from app.api.routes_ws import router_ws
from app.config import config
from app.dependencies import get_room_manager
from app.services.quiz_grpc_client import QuizServiceClient
from app.telemetry import setup_telemetry, shutdown_telemetry
from contextlib import asynccontextmanager
from my_observability import (
    setup_observability,
    setup_fastapi_logging
)

setup_observability(
    log_level=config.LOG_LEVEL
)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

setup_telemetry(app)
setup_fastapi_logging(app)

app.include_router(router)
app.include_router(router_ws)