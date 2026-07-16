from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.access.constants import AccessUserSort, SortOrder, UserRole
from app.access.queries import (
    assign_user_role,
    count_access_users,
    count_active_superadmins,
    count_role_assignments,
    get_access_user,
    list_access_users,
    revoke_user_role,
)
from app.access.rules import can_change_user_status, can_revoke_role, require_role
from app.api.deps import CurrentUserDep, SessionDep
from app.core.errors import AccessUserNotFoundError, LastActiveSuperadminError, LastSuperadminError
from app.core.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.models import User, UserStatus
from app.schemas.access import (
    AccessUserListOut,
    AccessUserOut,
    AccessUserStatusIn,
    AvailableRoleOut,
    AvailableStatusOut,
    RoleStatisticOut,
)

router = APIRouter(prefix="/internal/access", tags=["access"])

_ACCESS_USER_SORT_PARAMETERS = {
    "email": AccessUserSort.EMAIL,
    "createdAt": AccessUserSort.CREATED_AT,
    "updatedAt": AccessUserSort.UPDATED_AT,
}


@router.get("/users", response_model=AccessUserListOut)
def get_access_users(
    session: SessionDep,
    current_user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    role: Annotated[UserRole | None, Query()] = None,
    status: Annotated[UserStatus | None, Query()] = None,
    sort_by: Annotated[Literal["email", "createdAt", "updatedAt"], Query(alias="sortBy")] = "updatedAt",
    sort_order: Annotated[SortOrder, Query(alias="sortOrder")] = SortOrder.DESC,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccessUserListOut:
    require_role(current_user, UserRole.SUPERADMIN)
    query_parameters = {"q": q, "role": role, "status": status}
    return AccessUserListOut(
        available_roles=[AvailableRoleOut(value=role, label=role.value.replace("_", " ").title()) for role in UserRole],
        available_statuses=[AvailableStatusOut(value=status, label=status.value.replace("_", " ").title()) for status in UserStatus],
        statistics=[RoleStatisticOut(role=role, user_count=count_role_assignments(session, role)) for role in UserRole],
        items=[
            AccessUserOut.model_validate(user)
            for user in list_access_users(
                session,
                **query_parameters,
                sort_by=_ACCESS_USER_SORT_PARAMETERS[sort_by],
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )
        ],
        total=count_access_users(session, **query_parameters),
        limit=limit,
        offset=offset,
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
