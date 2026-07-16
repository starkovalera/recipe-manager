from collections.abc import Collection

from app.access.constants import UserRole
from app.core.errors import ForbiddenError
from app.models import ImportJob, RecipeEmbedding, User, UserStatus


def has_role(user: User, role: UserRole) -> bool:
    return role in user.roles


def has_any_role(user: User, roles: Collection[UserRole]) -> bool:
    return bool(user.roles & set(roles))


def require_role(user: User, role: UserRole) -> None:
    if not has_role(user, role):
        raise ForbiddenError()


def require_any_role(user: User, roles: Collection[UserRole]) -> None:
    if not has_any_role(user, roles):
        raise ForbiddenError()


def get_owner_id(user: User, allow_all: Collection[UserRole] | None = None) -> str | None:
    if user.roles & set(allow_all or ()):
        return None
    return user.id


def can_retry_import(user: User, job: ImportJob) -> bool:
    return job.owner_id == user.id or has_role(user, UserRole.SUPERADMIN)


def can_retry_embedding(user: User, embedding: RecipeEmbedding) -> bool:
    return embedding.recipe.owner_id == user.id or has_role(user, UserRole.SUPERADMIN)


def can_use_search_debug(user: User) -> bool:
    return has_any_role(user, {UserRole.DEBUG, UserRole.SUPERADMIN})


def can_revoke_role(user: User, role: UserRole, assignment_count: int) -> bool:
    return not (role == UserRole.SUPERADMIN and has_role(user, UserRole.SUPERADMIN) and assignment_count == 1)


def can_change_user_status(user: User, status: UserStatus, active_superadmin_count: int) -> bool:
    return not (
        status is UserStatus.DEACTIVATED
        and user.status is UserStatus.ACTIVE
        and has_role(user, UserRole.SUPERADMIN)
        and active_superadmin_count == 1
    )


def can_delete_user(user: User, active_superadmin_count: int) -> bool:
    return not (has_role(user, UserRole.SUPERADMIN) and user.status is UserStatus.ACTIVE and active_superadmin_count == 1)
