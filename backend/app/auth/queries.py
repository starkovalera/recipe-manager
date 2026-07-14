from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.constants import AuthProviderType
from app.models import User


def get_user_by_auth_identity(
    session: Session,
    auth_provider: AuthProviderType,
    auth_user_id: str,
) -> User | None:
    return session.scalar(
        select(User)
        .where(User.auth_provider == auth_provider, User.auth_user_id == auth_user_id)
        .options(selectinload(User.role_assignments), selectinload(User.settings))
    )
