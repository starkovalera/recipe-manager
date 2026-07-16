import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.auth.current_user import resolve_current_user
from app.auth.types import AuthenticatedIdentity
from app.core.errors import AccountDeactivatedError, AccountDeletionPendingError, UserNotProvisionedError
from app.db.base import Base
from app.models import User, UserStatus


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def identity(auth_user_id: str = "user_1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(auth_provider=AuthProviderType.CLERK, auth_user_id=auth_user_id)


def test_known_auth_identity_resolves_existing_user_without_writes():
    session = create_session()
    user = User(id="internal-1", auth_user_id="user_1", email="one@example.test")
    session.add(user)
    session.commit()

    resolved = resolve_current_user(session, identity())

    assert resolved.id == user.id
    assert not session.new
    assert not session.dirty
    assert not session.deleted


def test_unknown_auth_identity_is_not_provisioned_by_current_user_lookup():
    session = create_session()

    with pytest.raises(UserNotProvisionedError):
        resolve_current_user(session, identity("missing-user"))

    assert session.scalars(select(User)).all() == []


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (UserStatus.DEACTIVATED, AccountDeactivatedError),
        (UserStatus.DELETION_PENDING, AccountDeletionPendingError),
    ],
)
def test_inactive_user_status_is_rejected(status: UserStatus, error_type: type[Exception]):
    session = create_session()
    session.add(User(id="internal-1", auth_user_id="user_1", email="one@example.test", status=status))
    session.commit()

    with pytest.raises(error_type):
        resolve_current_user(session, identity())
