from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.api.health import router as health_router
from backend.app.api.compression import router as compression_router
from backend.app.api.auth import router as auth_router
from backend.app.services.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orbit Observatory",
        description="Context-compression plugin for month-long single sessions",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(compression_router, prefix="/api", tags=["compression"])
    app.include_router(auth_router, prefix="/api", tags=["auth"])

    return app


app = create_app()