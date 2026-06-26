from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.collections import router as collections_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.media import router as media_router
from app.api.routes.recipes import router as recipes_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.runtime import prepare_runtime
from app.db.init import ensure_default_user, run_migrations
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    prepare_runtime(settings)
    run_migrations(settings.database_url)
    with SessionLocal() as session:
        ensure_default_user(session)
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Recipe Manager API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(collections_router)
    app.include_router(imports_router)
    app.include_router(media_router)
    app.include_router(recipes_router)
    return app


app = create_app()
