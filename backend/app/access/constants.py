from enum import StrEnum


class UserRole(StrEnum):
    DEBUG = "DEBUG"
    SUPERADMIN = "SUPERADMIN"


class AccessUserSort(StrEnum):
    EMAIL = "email"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


ADMIN_PAGE_ROLES = frozenset({UserRole.DEBUG, UserRole.SUPERADMIN})
