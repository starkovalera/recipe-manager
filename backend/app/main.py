from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.runtime import prepare_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_runtime(get_settings())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Recipe Manager API", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
