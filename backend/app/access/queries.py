from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.access.constants import UserRole
from app.models import User, UserRoleAssignment, UserStatus


def list_access_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).options(selectinload(User.role_assignments)).order_by(User.created_at, User.id)))


def get_access_user(session: Session, user_id: str) -> User | None:
    return session.scalar(select(User).where(User.id == user_id).options(selectinload(User.role_assignments)))


def assign_user_role(session: Session, user: User, role: UserRole) -> None:
    if role not in user.roles:
        user.role_assignments.append(UserRoleAssignment(role=role))


def revoke_user_role(session: Session, user: User, role: UserRole) -> None:
    assignment = next((item for item in user.role_assignments if item.role == role), None)
    if assignment is not None:
        session.delete(assignment)


def count_role_assignments(session: Session, role: UserRole) -> int:
    return session.scalar(select(func.count()).select_from(UserRoleAssignment).where(UserRoleAssignment.role == role)) or 0


def count_active_superadmins(session: Session) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(User)
            .join(UserRoleAssignment)
            .where(
                User.status == UserStatus.ACTIVE,
                UserRoleAssignment.role == UserRole.SUPERADMIN,
            )
        )
        or 0
    )


def list_active_superadmin_ids_for_update(session: Session) -> list[str]:
    return list(
        session.scalars(
            select(User.id)
            .join(UserRoleAssignment)
            .where(
                User.status == UserStatus.ACTIVE,
                UserRoleAssignment.role == UserRole.SUPERADMIN,
            )
            .order_by(User.id)
            .with_for_update()
        )
    )
