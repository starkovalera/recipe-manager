from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.access.constants import AccessUserSort, SortOrder, UserRole
from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import User, UserRoleAssignment, UserStatus


def _access_user_filter_conditions(
    *,
    q: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    normalized_query = q.strip() if q else ""
    if normalized_query:
        conditions.append(
            or_(
                User.email.icontains(normalized_query, autoescape=True),
                User.id.icontains(normalized_query, autoescape=True),
                User.auth_user_id.icontains(normalized_query, autoescape=True),
            )
        )
    if role is not None:
        conditions.append(User.role_assignments.any(UserRoleAssignment.role == role))
    if status is not None:
        conditions.append(User.status == status)
    return conditions


def list_access_users(
    session: Session,
    *,
    q: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
    sort_by: AccessUserSort = AccessUserSort.UPDATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    limit: int | None = None,
    offset: int | None = None,
) -> list[User]:
    sort_column = {
        AccessUserSort.EMAIL: func.lower(User.email),
        AccessUserSort.CREATED_AT: User.created_at,
        AccessUserSort.UPDATED_AT: User.updated_at,
    }[AccessUserSort(sort_by)]
    order_expression = sort_column.asc() if SortOrder(sort_order) is SortOrder.ASC else sort_column.desc()
    query = (
        select(User)
        .where(*_access_user_filter_conditions(q=q, role=role, status=status))
        .options(selectinload(User.role_assignments))
        .order_by(order_expression, User.id.asc())
    )
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def count_access_users(
    session: Session,
    *,
    q: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> int:
    query = select(func.count()).select_from(User).where(*_access_user_filter_conditions(q=q, role=role, status=status))
    return session.scalar(query) or 0


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
