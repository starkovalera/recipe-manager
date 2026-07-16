from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.constants import UserRole
from app.api.deps import get_current_user
from app.auth import provider as provider_module
from app.auth.constants import AuthProviderType
from app.auth.types import AuthInvitation, AuthInvitationStatus
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models import User, UserRoleAssignment


class StubInvitationProvider:
    provider = AuthProviderType.CLERK

    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.revoked: list[str] = []

    def create_invitation(self, email: str, *, redirect_url: str) -> AuthInvitation:
        self.created.append((email, redirect_url))
        return AuthInvitation(
            id="auth-invitation-1",
            email=email,
            status=AuthInvitationStatus.PENDING,
            created_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            expires_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        )

    def revoke_invitation(self, invitation_id: str) -> AuthInvitation:
        self.revoked.append(invitation_id)
        return AuthInvitation(
            id=invitation_id,
            email="person@example.com",
            status=AuthInvitationStatus.REVOKED,
            created_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            expires_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        )


def create_client(monkeypatch) -> tuple[TestClient, sessionmaker[Session], StubInvitationProvider]:
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

    with session_factory.begin() as session:
        superadmin = User(
            id="superadmin",
            email="admin@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
        )
        session.add(superadmin)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: superadmin
    provider = StubInvitationProvider()
    monkeypatch.setattr(provider_module, "_auth_provider", provider)
    return TestClient(app), session_factory, provider


def test_superadmin_creates_lists_and_revokes_invitation(monkeypatch):
    client, _session_factory, provider = create_client(monkeypatch)

    created = client.post("/internal/invitations", json={"email": "PERSON@example.com"})
    assert created.status_code == 201, created.json()
    listed = client.get("/internal/invitations")
    revoked = client.post(f"/internal/invitations/{created.json()['id']}/revoke")
    revoked_again = client.post(f"/internal/invitations/{created.json()['id']}/revoke")

    assert created.json()["email"] == "person@example.com"
    assert created.json()["status"] == "PENDING"
    assert created.json()["authProvider"] == "CLERK"
    assert created.json()["authInvitationId"] == "auth-invitation-1"
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == created.json()["id"]
    assert listed.json()["items"][0]["status"] == "PENDING"
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"
    assert revoked_again.json()["id"] == revoked.json()["id"]
    assert revoked_again.json()["status"] == "REVOKED"
    assert provider.created == [("person@example.com", "http://127.0.0.1:5173/sign-up")]
    assert provider.revoked == ["auth-invitation-1"]


def test_invitation_api_requires_superadmin(monkeypatch):
    client, session_factory, _provider = create_client(monkeypatch)
    with session_factory.begin() as session:
        ordinary_user = User(id="ordinary", email="ordinary@example.test", role_assignments=[])
        session.add(ordinary_user)
    client.app.dependency_overrides[get_current_user] = lambda: ordinary_user

    assert client.get("/internal/invitations").status_code == 403
    assert client.post("/internal/invitations", json={"email": "person@example.com"}).status_code == 403


def test_invitation_api_validates_email(monkeypatch):
    client, _session_factory, provider = create_client(monkeypatch)

    response = client.post("/internal/invitations", json={"email": "not-an-email"})

    assert response.status_code == 422
    assert provider.created == []
