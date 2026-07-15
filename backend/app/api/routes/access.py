from fastapi import APIRouter

from app.access.constants import UserRole
from app.access.queries import (
    assign_user_role,
    count_active_superadmins,
    count_role_assignments,
    get_access_user,
    list_access_users,
    revoke_user_role,
)
from app.access.rules import can_change_user_status, can_revoke_role, require_role
from app.api.deps import CurrentUserDep, SessionDep
from app.core.errors import AccessUserNotFoundError, LastActiveSuperadminError, LastSuperadminError
from app.models import User, UserStatus
from app.schemas.access import AccessUserListOut, AccessUserOut, AccessUserStatusIn, AvailableRoleOut, RoleStatisticOut

router = APIRouter(prefix="/internal/access", tags=["access"])


@router.get("/users", response_model=AccessUserListOut)
def get_access_users(session: SessionDep, current_user: CurrentUserDep) -> AccessUserListOut:
    require_role(current_user, UserRole.SUPERADMIN)
    return AccessUserListOut(
        available_roles=[AvailableRoleOut(value=role, label=role.value.replace("_", " ").title()) for role in UserRole],
        statistics=[RoleStatisticOut(role=role, user_count=count_role_assignments(session, role)) for role in UserRole],
        items=[AccessUserOut.model_validate(user) for user in list_access_users(session)],
    )


@router.put("/users/{user_id}/roles/{role}", response_model=AccessUserOut)
def put_user_role(user_id: str, role: UserRole, session: SessionDep, current_user: CurrentUserDep) -> User:
    require_role(current_user, UserRole.SUPERADMIN)
    user = get_access_user(session, user_id)
    if user is None:
        raise AccessUserNotFoundError()
    assign_user_role(session, user, role)
    session.commit()
    session.refresh(user)
    return user


@router.delete("/users/{user_id}/roles/{role}", response_model=AccessUserOut)
def delete_user_role(user_id: str, role: UserRole, session: SessionDep, current_user: CurrentUserDep) -> User:
    require_role(current_user, UserRole.SUPERADMIN)
    user = get_access_user(session, user_id)
    if user is None:
        raise AccessUserNotFoundError()
    if not can_revoke_role(user, role, count_role_assignments(session, role)):
        raise LastSuperadminError()
    revoke_user_role(session, user, role)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/users/{user_id}/status", response_model=AccessUserOut)
def patch_user_status(
    user_id: str,
    request: AccessUserStatusIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> User:
    require_role(current_user, UserRole.SUPERADMIN)
    user = get_access_user(session, user_id)
    if user is None:
        raise AccessUserNotFoundError()
    status = UserStatus(request.status)
    if not can_change_user_status(user, status, count_active_superadmins(session)):
        raise LastActiveSuperadminError()
    user.status = status
    session.commit()
    session.refresh(user)
    return user
