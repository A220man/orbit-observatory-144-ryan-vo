from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.health import router as health_router
from app.api.compression import router as compression_router
from app.api.auth import router as auth_router
from app.api.sessions import router as sessions_router
from app.services.database import init_db, close_db


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
    app.include_router(sessions_router, prefix="/api", tags=["sessions"])

    return app


app = create_app()
