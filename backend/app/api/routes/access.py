from fastapi import APIRouter

from app.access.constants import UserRole
from app.access.queries import assign_user_role, count_role_assignments, get_access_user, list_access_users, revoke_user_role
from app.access.rules import can_revoke_role, require_role
from app.api.deps import CurrentUserDep, SessionDep
from app.core.errors import AccessUserNotFoundError, LastSuperadminError
from app.schemas.access import AccessUserListOut, AccessUserOut, AvailableRoleOut, RoleStatisticOut

router = APIRouter(prefix="/internal/access", tags=["access"])


def _user_out(user) -> AccessUserOut:
    return AccessUserOut(id=user.id, email=user.email, roles=sorted(user.roles, key=lambda role: role.value), created_at=user.created_at)


@router.get("/users", response_model=AccessUserListOut)
def get_access_users(session: SessionDep, current_user: CurrentUserDep) -> AccessUserListOut:
    require_role(current_user, UserRole.SUPERADMIN)
    return AccessUserListOut(
        available_roles=[AvailableRoleOut(value=role, label=role.value.replace("_", " ").title()) for role in UserRole],
        statistics=[RoleStatisticOut(role=role, user_count=count_role_assignments(session, role)) for role in UserRole],
        items=[_user_out(user) for user in list_access_users(session)],
    )


@router.put("/users/{user_id}/roles/{role}", response_model=AccessUserOut)
def put_user_role(user_id: str, role: UserRole, session: SessionDep, current_user: CurrentUserDep) -> AccessUserOut:
    require_role(current_user, UserRole.SUPERADMIN)
    user = get_access_user(session, user_id)
    if user is None:
        raise AccessUserNotFoundError()
    assign_user_role(session, user, role)
    session.commit()
    session.refresh(user)
    return _user_out(user)


@router.delete("/users/{user_id}/roles/{role}", response_model=AccessUserOut)
def delete_user_role(user_id: str, role: UserRole, session: SessionDep, current_user: CurrentUserDep) -> AccessUserOut:
    require_role(current_user, UserRole.SUPERADMIN)
    user = get_access_user(session, user_id)
    if user is None:
        raise AccessUserNotFoundError()
    if not can_revoke_role(user, role, count_role_assignments(session, role)):
        raise LastSuperadminError()
    revoke_user_role(session, user, role)
    session.commit()
    session.refresh(user)
    return _user_out(user)
