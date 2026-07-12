from enum import StrEnum


class UserRole(StrEnum):
    DEBUG = "debug"
    SUPERADMIN = "superadmin"


ADMIN_PAGE_ROLES = frozenset({UserRole.DEBUG, UserRole.SUPERADMIN})
