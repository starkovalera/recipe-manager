from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.constants import UserRole
from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_session
from app.local.users import ensure_default_user
from app.main import create_app
from app.models import User, UserRoleAssignment, UserStatus


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def test_me_returns_capabilities_without_roles():
    client, session_factory = client_with_session()
    with session_factory() as session:
        user = ensure_default_user(session)
        client.app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": "local-user",
        "email": "local@example.test",
        "features": {"showAdminPages": True, "showRoleManagement": True, "showRecipeDebug": True},
    }
    assert "roles" not in response.json()


def test_superadmin_assigns_and_revokes_role_idempotently():
    client, session_factory = client_with_session()
    with session_factory() as session:
        superadmin = ensure_default_user(session)
        target = User(id="target", email="target@example.test")
        session.add(target)
        session.commit()
        client.app.dependency_overrides[get_current_user] = lambda: superadmin

    first = client.put("/internal/access/users/target/roles/DEBUG")
    second = client.put("/internal/access/users/target/roles/DEBUG")
    revoked = client.delete("/internal/access/users/target/roles/DEBUG")
    revoked_again = client.delete("/internal/access/users/target/roles/DEBUG")

    assert first.status_code == second.status_code == revoked.status_code == revoked_again.status_code == 200
    assert first.json()["roles"] == ["DEBUG"]
    assert revoked_again.json()["roles"] == []


def test_role_management_rejects_non_superadmin_and_last_superadmin_removal():
    client, session_factory = client_with_session()
    with session_factory() as session:
        superadmin = ensure_default_user(session)
        debug_user = User(
            id="debug-user",
            email="debug@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
        )
        session.add(debug_user)
        session.commit()
        client.app.dependency_overrides[get_current_user] = lambda: debug_user

    assert client.get("/internal/access/users").status_code == 403
    client.app.dependency_overrides[get_current_user] = lambda: superadmin
    response = client.delete("/internal/access/users/local-user/roles/SUPERADMIN")
    assert response.status_code == 409
    assert response.json()["errorCode"] == "LAST_SUPERADMIN"


def test_role_management_rejects_invalid_role_and_unknown_user():
    client, session_factory = client_with_session()
    with session_factory() as session:
        superadmin = ensure_default_user(session)
        client.app.dependency_overrides[get_current_user] = lambda: superadmin

    assert client.put("/internal/access/users/local-user/roles/owner").status_code == 422
    assert client.put("/internal/access/users/missing/roles/DEBUG").status_code == 404


def test_superadmin_deactivates_and_reactivates_user():
    client, session_factory = client_with_session()
    with session_factory() as session:
        superadmin = ensure_default_user(session)
        session.add(User(id="target", email="target@example.test"))
        session.commit()
        client.app.dependency_overrides[get_current_user] = lambda: superadmin

    deactivated = client.patch("/internal/access/users/target/status", json={"status": "DEACTIVATED"})
    reactivated = client.patch("/internal/access/users/target/status", json={"status": "ACTIVE"})

    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "DEACTIVATED"
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "ACTIVE"


def test_status_management_rejects_deletion_pending_and_last_active_superadmin_deactivation():
    client, session_factory = client_with_session()
    with session_factory() as session:
        superadmin = ensure_default_user(session)
        client.app.dependency_overrides[get_current_user] = lambda: superadmin

    invalid = client.patch("/internal/access/users/local-user/status", json={"status": "DELETION_PENDING"})
    last_superadmin = client.patch("/internal/access/users/local-user/status", json={"status": "DEACTIVATED"})

    assert invalid.status_code == 422
    assert last_superadmin.status_code == 409
    assert last_superadmin.json()["errorCode"] == "LAST_ACTIVE_SUPERADMIN"
    with session_factory() as session:
        assert session.get(User, "local-user").status is UserStatus.ACTIVE
