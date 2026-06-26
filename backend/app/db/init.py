from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.models import User

DEFAULT_USER_ID = "local-user"
DEFAULT_USER_EMAIL = "local@example.test"


def ensure_default_user(session: Session) -> User:
    user = session.get(User, DEFAULT_USER_ID)
    if user is not None:
        return user
    user = User(id=DEFAULT_USER_ID, email=DEFAULT_USER_EMAIL)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def run_migrations(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
