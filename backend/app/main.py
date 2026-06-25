from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.recipes import router as recipes_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.runtime import prepare_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_runtime(get_settings())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Recipe Manager API", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(imports_router)
    app.include_router(recipes_router)
    return app


app = create_app()
