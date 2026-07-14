from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.auth.constants import AuthProviderType
from app.auth.types import AuthUser
from app.db.base import Base
from app.main import create_app
from app.users import provisioning as provisioning_module


class StubAuthProvider:
    provider = AuthProviderType.CLERK

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_user(self, auth_user_id: str) -> AuthUser:
        self.calls.append(auth_user_id)
        return AuthUser(id=auth_user_id, primary_email="new@example.test")


def create_client(monkeypatch) -> tuple[TestClient, StubAuthProvider]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = StubAuthProvider()
    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: provider)
    return TestClient(app), provider


def test_explicit_provisioning_sequence_uses_only_authenticated_identity(monkeypatch):
    client, provider = create_client(monkeypatch)
    headers = {"X-Authenticated-Subject": "auth-user"}

    missing_response = client.get("/me", headers=headers)
    created_response = client.post(
        "/me/provision",
        headers=headers,
        json={"authUserId": "other-user", "email": "other@example.test"},
    )
    current_response = client.get("/me", headers=headers)
    repeated_response = client.post("/me/provision", headers=headers)

    assert missing_response.status_code == 409
    assert missing_response.json()["errorCode"] == "USER_NOT_PROVISIONED"
    assert created_response.status_code == 201
    assert created_response.json() == {
        "id": created_response.json()["id"],
        "email": "new@example.test",
        "features": {
            "showAdminPages": False,
            "showRoleManagement": False,
            "showRecipeDebug": False,
        },
    }
    assert current_response.status_code == 200
    assert current_response.json() == created_response.json()
    assert repeated_response.status_code == 200
    assert repeated_response.json() == created_response.json()
    assert provider.calls == ["auth-user"]
