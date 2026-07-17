from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.constants import UserRole
from app.api.deps import get_session
from app.db.base import Base
from app.main import create_app
from app.models import QueueOutboxMessage, User, UserRoleAssignment, UserStatus
from app.queueing.constants import QueueMessageType, QueueOutboxStatus


def create_client(monkeypatch) -> tuple[TestClient, sessionmaker[Session], list[str]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    dispatched_message_ids: list[str] = []
    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        "app.api.routes.users.dispatch_outbox_message",
        lambda message_id: dispatched_message_ids.append(message_id) or True,
    )
    return TestClient(app), session_factory, dispatched_message_ids


def test_active_user_requests_idempotent_background_deletion(monkeypatch):
    client, session_factory, dispatched_message_ids = create_client(monkeypatch)
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))
    headers = {"X-Authenticated-Subject": "auth-user"}

    first = client.post("/me/deletion", headers=headers)
    second = client.post("/me/deletion", headers=headers)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json() == {"status": "DELETION_PENDING"}
    assert len(dispatched_message_ids) == 2
    with session_factory() as session:
        user = session.get(User, "user-1")
        assert user is not None
        assert user.status is UserStatus.DELETION_PENDING
        assert user.deletion_requested_at is not None
        messages = session.query(QueueOutboxMessage).all()
        assert [message.id for message in messages] == dispatched_message_ids
        assert all(message.message_type is QueueMessageType.ACCOUNT_DELETION for message in messages)
        assert all(message.status is QueueOutboxStatus.PENDING for message in messages)


def test_deletion_rejects_last_active_superadmin(monkeypatch):
    client, session_factory, published_user_ids = create_client(monkeypatch)
    with session_factory.begin() as session:
        session.add(
            User(
                id="admin",
                auth_user_id="auth-admin",
                email="admin@example.test",
                role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
            )
        )

    response = client.post("/me/deletion", headers={"X-Authenticated-Subject": "auth-admin"})

    assert response.status_code == 409
    assert response.json()["errorCode"] == "LAST_ACTIVE_SUPERADMIN"
    assert published_user_ids == []
    with session_factory() as session:
        assert session.get(User, "admin").status is UserStatus.ACTIVE


def test_deletion_rejects_deactivated_user(monkeypatch):
    client, session_factory, published_user_ids = create_client(monkeypatch)
    with session_factory.begin() as session:
        session.add(
            User(
                id="user-1",
                auth_user_id="auth-user",
                email="user@example.test",
                status=UserStatus.DEACTIVATED,
            )
        )

    response = client.post("/me/deletion", headers={"X-Authenticated-Subject": "auth-user"})

    assert response.status_code == 403
    assert response.json()["errorCode"] == "ACCOUNT_DEACTIVATED"
    assert published_user_ids == []


def test_deletion_stays_pending_when_outbox_dispatch_fails(monkeypatch):
    client, session_factory, dispatched_message_ids = create_client(monkeypatch)
    monkeypatch.setattr(
        "app.api.routes.users.dispatch_outbox_message", lambda message_id: dispatched_message_ids.append(message_id) or False
    )
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))

    response = client.post("/me/deletion", headers={"X-Authenticated-Subject": "auth-user"})

    assert response.status_code == 202
    assert response.json() == {"status": "DELETION_PENDING"}
    assert len(dispatched_message_ids) == 1
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING
        assert session.get(QueueOutboxMessage, dispatched_message_ids[0]).status is QueueOutboxStatus.PENDING
