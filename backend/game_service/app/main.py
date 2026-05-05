from fastapi import FastAPI
from app.api.routes import router
from app.api.routes_ws import router_ws
from app.logging_config import setup_logging
from app.middleware.logging_middleware import setup_http_logging
from app.dependencies import get_room_manager
from app.telemetry import setup_telemetry, shutdown_telemetry
from contextlib import asynccontextmanager

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = get_room_manager()
    await manager.start()

    app.state.room_manager = manager

    yield

    await manager.stop()
    shutdown_telemetry()

app = FastAPI(lifespan=lifespan)

setup_telemetry(app)
setup_http_logging(app)

app.include_router(router)
app.include_router(router_ws)