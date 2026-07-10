from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.base import Base
from app.db.defaults import DEFAULT_TAG_NAMES, DEFAULT_USER_EMAIL, DEFAULT_USER_ID
from app.models import Tag, User, UserSettings


def ensure_default_user(session: Session, recipe_language: str | None = None) -> User:
    recipe_language = recipe_language or get_settings().recipe_language
    user = session.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, email=DEFAULT_USER_EMAIL)
        session.add(user)
        session.flush()

    if user.settings is None:
        user.settings = UserSettings(recipe_language=recipe_language)
    elif user.settings.recipe_language != recipe_language:
        user.settings.recipe_language = recipe_language

    existing_tag_names = {
        tag.name
        for tag in session.query(Tag).filter_by(owner_id=user.id).all()
    }
    for tag_name in DEFAULT_TAG_NAMES:
        if tag_name not in existing_tag_names:
            session.add(Tag(owner_id=user.id, name=tag_name))

    session.commit()
    return user


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
