import pytest

from app.access.constants import ADMIN_PAGE_ROLES, UserRole
from app.access.rules import (
    can_retry_embedding,
    can_retry_import,
    can_revoke_role,
    can_use_search_debug,
    get_owner_id,
    has_any_role,
    has_role,
    require_any_role,
    require_role,
)
from app.core.errors import ForbiddenError
from app.models import ImportJob, Recipe, RecipeEmbedding, User, UserRoleAssignment


def user_with_roles(user_id: str, *roles: UserRole) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.test",
        role_assignments=[UserRoleAssignment(role=role) for role in roles],
    )


def test_role_helpers_and_owner_scope():
    debug_user = user_with_roles("debug-user", UserRole.DEBUG)
    superadmin = user_with_roles("admin", UserRole.SUPERADMIN)

    assert has_role(debug_user, UserRole.DEBUG)
    assert has_any_role(debug_user, ADMIN_PAGE_ROLES)
    assert can_use_search_debug(superadmin)
    assert get_owner_id(debug_user, [UserRole.SUPERADMIN]) == debug_user.id
    assert get_owner_id(superadmin, [UserRole.SUPERADMIN]) is None
    require_role(debug_user, UserRole.DEBUG)
    require_any_role(debug_user, ADMIN_PAGE_ROLES)


def test_role_requirements_reject_missing_roles():
    user = user_with_roles("regular")

    with pytest.raises(ForbiddenError):
        require_role(user, UserRole.DEBUG)
    with pytest.raises(ForbiddenError):
        require_any_role(user, ADMIN_PAGE_ROLES)


def test_retry_rules_allow_owner_or_superadmin_only():
    owner = user_with_roles("owner", UserRole.DEBUG)
    other = user_with_roles("other", UserRole.DEBUG)
    superadmin = user_with_roles("admin", UserRole.SUPERADMIN)
    job = ImportJob(owner_id=owner.id, client_id="client")
    embedding = RecipeEmbedding(model="test", recipe=Recipe(owner_id=owner.id, title="Soup", instructions=[]))

    assert can_retry_import(owner, job)
    assert not can_retry_import(other, job)
    assert can_retry_import(superadmin, job)
    assert can_retry_embedding(owner, embedding)
    assert not can_retry_embedding(other, embedding)
    assert can_retry_embedding(superadmin, embedding)


def test_last_superadmin_role_cannot_be_revoked():
    superadmin = user_with_roles("admin", UserRole.SUPERADMIN)

    assert not can_revoke_role(superadmin, UserRole.SUPERADMIN, 1)
    assert can_revoke_role(superadmin, UserRole.SUPERADMIN, 2)
    assert can_revoke_role(superadmin, UserRole.DEBUG, 1)
