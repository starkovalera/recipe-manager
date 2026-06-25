from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_app_engine(database_url: str | None = None):
    settings = get_settings()
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url and url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = create_app_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
