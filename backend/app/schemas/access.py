from datetime import datetime
from typing import Literal

from pydantic import field_serializer

from app.access.constants import UserRole
from app.models import UserStatus
from app.schemas.base import CamelModel


class AvailableRoleOut(CamelModel):
    value: UserRole
    label: str


class RoleStatisticOut(CamelModel):
    role: UserRole
    user_count: int


class AccessUserOut(CamelModel):
    id: str
    email: str
    roles: list[UserRole]
    status: UserStatus
    created_at: datetime | None = None

    @field_serializer("roles")
    def serialize_roles(self, roles: list[UserRole]) -> list[UserRole]:
        return sorted(roles, key=lambda role: role.value)


class AccessUserListOut(CamelModel):
    available_roles: list[AvailableRoleOut]
    statistics: list[RoleStatisticOut]
    items: list[AccessUserOut]


class AccessUserStatusIn(CamelModel):
    status: Literal[UserStatus.ACTIVE, UserStatus.DEACTIVATED]
