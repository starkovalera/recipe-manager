from collections.abc import Generator

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user
from app.local.users import ensure_default_user
from app.models import User


def install_local_user_override(app: FastAPI, session_factory: sessionmaker[Session]) -> None:
    def override_current_user() -> Generator[User, None, None]:
        with session_factory() as session:
            yield ensure_default_user(session)

    app.dependency_overrides[get_current_user] = override_current_user
