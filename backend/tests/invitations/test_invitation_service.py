from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import provider as provider_module
from app.auth.constants import AuthProviderType
from app.auth.types import AuthInvitation, AuthInvitationStatus
from app.core.errors import InvitationCreateError
from app.db.base import Base
from app.invitations.service import create_invitation
from app.models import User


class StubInvitationProvider:
    provider = AuthProviderType.CLERK

    def __init__(self) -> None:
        self.revoked: list[str] = []

    def create_invitation(self, email: str, *, redirect_url: str) -> AuthInvitation:
        return AuthInvitation(
            id="duplicate-provider-id",
            email=email,
            status=AuthInvitationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def revoke_invitation(self, invitation_id: str) -> AuthInvitation:
        self.revoked.append(invitation_id)
        return AuthInvitation(
            id=invitation_id,
            email="person@example.com",
            status=AuthInvitationStatus.REVOKED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_local_persistence_failure_revokes_created_provider_invitation(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'invitations.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = StubInvitationProvider()
    monkeypatch.setattr(provider_module, "_auth_provider", provider)
    created_by = User(id="admin", email="admin@example.test")
    with session_factory.begin() as session:
        session.add(created_by)

    with session_factory() as session:
        create_invitation(
            session,
            email="first@example.com",
            created_by=created_by,
            redirect_url="http://127.0.0.1:5173/sign-up",
        )
        session.commit()

    with session_factory() as session, pytest.raises(InvitationCreateError):
        create_invitation(
            session,
            email="second@example.com",
            created_by=created_by,
            redirect_url="http://127.0.0.1:5173/sign-up",
        )

    assert provider.revoked == ["duplicate-provider-id"]
