from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.constants import AuthProviderType
from app.auth.types import AuthProviderError
from app.db import session as session_module
from app.db.base import Base
from app.invitations.constants import InvitationStatus
from app.maintenance import invitations as maintenance_invitations
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import Invitation


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class Provider:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.revoked: list[str] = []

    def revoke_invitation(self, invitation_id: str) -> None:
        self.revoked.append(invitation_id)
        if self.error:
            raise self.error


def _add(factory, *, invitation_id: str, expired: bool = True) -> None:
    with factory() as session:
        session.add(
            Invitation(
                id=invitation_id,
                auth_provider=AuthProviderType.CLERK,
                auth_invitation_id=f"auth-{invitation_id}",
                email=f"{invitation_id}@example.test",
                expires_at=datetime.now(timezone.utc) + (-timedelta(hours=1) if expired else timedelta(hours=1)),
            )
        )
        session.commit()


def _configure(monkeypatch, factory, provider) -> None:
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(maintenance_invitations, "get_settings", lambda: SimpleNamespace(maintenance_batch_size=100))
    monkeypatch.setattr(maintenance_invitations, "get_auth_provider", lambda: provider)


def test_expired_invitation_is_revoked_then_finalized(monkeypatch) -> None:
    factory = _factory()
    _add(factory, invitation_id="one")
    provider = Provider()
    _configure(monkeypatch, factory, provider)

    result = maintenance_invitations.cleanup_expired_invitations()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert provider.revoked == ["auth-one"]
    with factory() as session:
        assert session.get(Invitation, "one").status is InvitationStatus.EXPIRED


def test_provider_failure_leaves_invitation_pending(monkeypatch) -> None:
    factory = _factory()
    _add(factory, invitation_id="one")
    _configure(monkeypatch, factory, Provider(AuthProviderError("unavailable")))

    result = maintenance_invitations.cleanup_expired_invitations()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    with factory() as session:
        assert session.get(Invitation, "one").status is InvitationStatus.PENDING


def test_fresh_invitation_is_ignored(monkeypatch) -> None:
    factory = _factory()
    _add(factory, invitation_id="one", expired=False)
    provider = Provider()
    _configure(monkeypatch, factory, provider)

    assert maintenance_invitations.cleanup_expired_invitations().disposition is MaintenanceProcessingDisposition.NOOP
    assert provider.revoked == []
