from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.constants import AuthProviderType
from app.models import User, UserStatus


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


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def get_user_by_auth_identity_for_update(
    session: Session,
    auth_provider: AuthProviderType,
    auth_user_id: str,
) -> User | None:
    return session.scalar(
        select(User)
        .where(User.auth_provider == auth_provider, User.auth_user_id == auth_user_id)
        .options(selectinload(User.role_assignments))
        .with_for_update()
    )


def list_user_ids_by_status(session: Session, status: UserStatus) -> list[str]:
    return list(session.scalars(select(User.id).where(User.status == status).order_by(User.id)))
