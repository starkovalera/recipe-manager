from datetime import datetime
from typing import Literal

from pydantic import field_serializer

from app.access.constants import UserRole
from app.models import UserStatus
from app.schemas.base import CamelModel
from app.schemas.pagination import PaginatedOutMixin


class AvailableRoleOut(CamelModel):
    value: UserRole
    label: str


class AvailableStatusOut(CamelModel):
    value: UserStatus
    label: str


class RoleStatisticOut(CamelModel):
    role: UserRole
    user_count: int


class AccessUserOut(CamelModel):
    id: str
    auth_user_id: str | None
    email: str
    roles: list[UserRole]
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    deletion_requested_at: datetime | None = None

    @field_serializer("roles")
    def serialize_roles(self, roles: list[UserRole]) -> list[UserRole]:
        return sorted(roles, key=lambda role: role.value)


class AccessUserListOut(PaginatedOutMixin):
    available_roles: list[AvailableRoleOut]
    available_statuses: list[AvailableStatusOut]
    statistics: list[RoleStatisticOut]
    items: list[AccessUserOut]


class AccessUserStatusIn(CamelModel):
    status: Literal[UserStatus.ACTIVE, UserStatus.DEACTIVATED]
