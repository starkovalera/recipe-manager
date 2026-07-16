from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.db.base import Base


def run_migrations(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def reset_database_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        if database_url.startswith("postgresql://") or database_url.startswith("postgresql+"):
            with engine.begin() as connection:
                connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                connection.execute(text("CREATE SCHEMA public"))
        else:
            Base.metadata.drop_all(engine)
    finally:
        engine.dispose()
