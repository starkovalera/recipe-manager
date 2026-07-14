from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedIdentity
from app.core.errors import AccountDeactivatedError, AccountDeletionPendingError, UserNotProvisionedError
from app.models import User, UserStatus
from app.users.queries import get_user_by_auth_identity


def ensure_user_is_active(user: User) -> User:
    if user.status is UserStatus.DEACTIVATED:
        raise AccountDeactivatedError()
    if user.status is UserStatus.DELETION_PENDING:
        raise AccountDeletionPendingError()
    return user


def resolve_current_user(session: Session, identity: AuthenticatedIdentity) -> User:
    user = get_user_by_auth_identity(
        session,
        identity.auth_provider,
        identity.auth_user_id,
    )
    if user is None:
        raise UserNotProvisionedError()
    return ensure_user_is_active(user)
