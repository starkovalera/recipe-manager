from datetime import datetime

from app.access.constants import UserRole
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
    created_at: datetime | None = None


class AccessUserListOut(CamelModel):
    available_roles: list[AvailableRoleOut]
    statistics: list[RoleStatisticOut]
    items: list[AccessUserOut]
