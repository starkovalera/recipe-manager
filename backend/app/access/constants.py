from enum import StrEnum


class UserRole(StrEnum):
    DEBUG = "DEBUG"
    SUPERADMIN = "SUPERADMIN"


ADMIN_PAGE_ROLES = frozenset({UserRole.DEBUG, UserRole.SUPERADMIN})
