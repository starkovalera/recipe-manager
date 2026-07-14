import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.access import router as access_router
from app.api.routes.collections import router as collections_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.internal import router as internal_router
from app.api.routes.media import router as media_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.recipes import router as recipes_router
from app.api.routes.search import router as search_router
from app.api.routes.tags import router as tags_router
from app.api.routes.users import router as users_router
from app.core.config import AppEnv, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, log_error, log_info
from app.core.runtime import prepare_runtime
from app.db.init import reset_database_schema, run_migrations
from app.db.session import SessionLocal
from app.local.users import seed_preview_users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log_info(
        logger,
        "[recipes.runtime] Application startup",
        pid=os.getpid(),
        appEnv=settings.app_env,
        databaseUrl=settings.database_url,
        uploadDir=str(settings.upload_dir),
    )
    prepare_runtime(settings, reset_database=reset_database_schema)
    run_migrations(settings.database_url)
    if settings.app_env is AppEnv.PREVIEW:
        with SessionLocal.begin() as session:
            count = seed_preview_users(session, settings.preview_users_file, recipe_language=settings.recipe_language)
        log_info(logger, "[recipes.runtime] Preview users seeded", pid=os.getpid(), user_count=count)
    yield
    log_info(logger, "[recipes.runtime] Application shutdown", pid=os.getpid(), appEnv=settings.app_env)


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

    @app.middleware("http")
    async def log_runtime_request(request: Request, call_next):
        current_settings = get_settings()
        try:
            response = await call_next(request)
        except Exception as error:
            log_error(
                logger,
                "[recipes.http] Request failed",
                pid=os.getpid(),
                method=request.method,
                path=request.url.path,
                errorType=type(error).__name__,
                error=repr(error),
                appEnv=current_settings.app_env,
                databaseUrl=current_settings.database_url,
                uploadDir=str(current_settings.upload_dir),
            )
            raise
        log_info(
            logger,
            "[recipes.http] Request handled",
            pid=os.getpid(),
            method=request.method,
            path=request.url.path,
            statusCode=response.status_code,
            appEnv=current_settings.app_env,
            databaseUrl=current_settings.database_url,
            uploadDir=str(current_settings.upload_dir),
        )
        return response

    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(access_router)
    app.include_router(collections_router)
    app.include_router(imports_router)
    app.include_router(internal_router)
    app.include_router(media_router)
    app.include_router(notifications_router)
    app.include_router(recipes_router)
    app.include_router(search_router)
    app.include_router(tags_router)
    app.include_router(users_router)
    return app


app = create_app()
