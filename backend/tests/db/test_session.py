import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import session as session_module


def test_db_session_commits_and_closes(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)

    with engine.begin() as connection:
        connection.execute(text("create table items (id integer primary key, name text)"))

    with session_module.db_session() as session:
        session.execute(text("insert into items (name) values ('saved')"))

    with Session(engine) as session:
        assert session.execute(text("select name from items")).scalar_one() == "saved"


def test_db_session_rolls_back_on_error(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)

    with engine.begin() as connection:
        connection.execute(text("create table items (id integer primary key, name text)"))

    with pytest.raises(RuntimeError, match="boom"):
        with session_module.db_session() as session:
            session.execute(text("insert into items (name) values ('rolled-back')"))
            raise RuntimeError("boom")

    with Session(engine) as session:
        assert session.execute(text("select count(*) from items")).scalar_one() == 0


def test_db_transaction_uses_existing_session() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("create table items (id integer primary key, name text)"))

    with Session(engine) as session:
        with session_module.db_transaction(session):
            session.execute(text("insert into items (name) values ('inside-transaction')"))

        assert session.execute(text("select name from items")).scalar_one() == "inside-transaction"
        assert session.is_active


def test_db_transaction_rolls_back_on_error() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("create table items (id integer primary key, name text)"))

    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="boom"):
            with session_module.db_transaction(session):
                session.execute(text("insert into items (name) values ('rolled-back')"))
                raise RuntimeError("boom")

        assert session.execute(text("select count(*) from items")).scalar_one() == 0
