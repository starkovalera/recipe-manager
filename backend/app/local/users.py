from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session, selectinload

from app.access.constants import UserRole
from app.access.queries import assign_user_role
from app.auth.constants import AuthProviderType
from app.core.config import get_settings
from app.core.errors import AccessUserNotFoundError
from app.models import User, UserRoleAssignment, UserStatus
from app.users.provisioning import create_user, initialize_user_defaults

LOCAL_USER_ID = "local-user"
LOCAL_USER_EMAIL = "local@example.test"


@dataclass(frozen=True)
class PreviewUserSeed:
    id: str
    auth_provider: AuthProviderType
    auth_user_id: str
    email: str
    status: UserStatus
    roles: frozenset[UserRole]


def ensure_default_user(session: Session, recipe_language: str | None = None) -> User:
    recipe_language = recipe_language or get_settings().recipe_language
    user = session.get(User, LOCAL_USER_ID)
    if user is None:
        user = create_user(
            session,
            user_id=LOCAL_USER_ID,
            email=LOCAL_USER_EMAIL,
            recipe_language=recipe_language,
        )
        user.role_assignments.extend(
            [
                UserRoleAssignment(role=UserRole.DEBUG),
                UserRoleAssignment(role=UserRole.SUPERADMIN),
            ]
        )
    else:
        initialize_user_defaults(user, recipe_language=recipe_language)

    session.commit()
    return user


def assign_role_to_auth_user(
    session: Session,
    auth_provider: AuthProviderType,
    auth_user_id: str,
    role: UserRole,
) -> User:
    user = session.scalar(
        select(User)
        .where(User.auth_provider == auth_provider, User.auth_user_id == auth_user_id)
        .options(selectinload(User.role_assignments))
    )
    if user is None:
        raise AccessUserNotFoundError()
    assign_user_role(session, user, role)
    session.flush()
    return user


def _required_text(row: dict, field: str, position: int) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Preview user {position} requires a non-empty {field}.")
    return value.strip()


def _parse_preview_users(path: Path) -> list[PreviewUserSeed]:
    if not path.is_file():
        raise ValueError(f"Preview users file does not exist: {path}")
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"Preview users file is invalid: {path}") from error

    rows = document.get("users")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Preview users file must contain at least one [[users]] entry.")

    seeds: list[PreviewUserSeed] = []
    seen_ids: set[str] = set()
    seen_auth_identities: set[tuple[AuthProviderType, str]] = set()
    seen_emails: set[str] = set()
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Preview user {position} must be a TOML table.")
        user_id = _required_text(row, "id", position)
        auth_user_id = _required_text(row, "auth_user_id", position)
        email = _required_text(row, "email", position).casefold()
        try:
            auth_provider = AuthProviderType(_required_text(row, "auth_provider", position))
        except ValueError as error:
            raise ValueError(f"Preview user {position} has an invalid auth_provider.") from error
        auth_identity = (auth_provider, auth_user_id)
        if user_id in seen_ids:
            raise ValueError(f"Duplicate preview user id: {user_id}")
        if auth_identity in seen_auth_identities:
            raise ValueError(f"Duplicate preview user auth identity: {auth_provider.value}/{auth_user_id}")
        if email in seen_emails:
            raise ValueError(f"Duplicate preview user email: {email}")
        seen_ids.add(user_id)
        seen_auth_identities.add(auth_identity)
        seen_emails.add(email)
        try:
            status = UserStatus(str(row.get("status")).upper())
        except (TypeError, ValueError) as error:
            raise ValueError(f"Preview user {position} has an invalid status.") from error
        raw_roles = row.get("roles")
        if not isinstance(raw_roles, list) or any(not isinstance(role, str) for role in raw_roles):
            raise ValueError(f"Preview user {position} roles must be a list of strings.")
        try:
            roles = frozenset(UserRole(role.upper()) for role in raw_roles)
        except ValueError as error:
            raise ValueError(f"Preview user {position} has an invalid role.") from error
        if len(roles) != len(raw_roles):
            raise ValueError(f"Preview user {position} contains duplicate roles.")
        seeds.append(
            PreviewUserSeed(
                id=user_id,
                auth_provider=auth_provider,
                auth_user_id=auth_user_id,
                email=email,
                status=status,
                roles=roles,
            )
        )
    return seeds


def _validate_database_identity_conflicts(session: Session, seeds: list[PreviewUserSeed]) -> None:
    seed_ids = {seed.id for seed in seeds}
    seed_auth_identities = {(seed.auth_provider, seed.auth_user_id) for seed in seeds}
    seed_emails = {seed.email for seed in seeds}
    existing = session.scalars(
        select(User).where(
            (User.id.in_(seed_ids))
            | (tuple_(User.auth_provider, User.auth_user_id).in_(seed_auth_identities))
            | (User.email.in_(seed_emails))
        )
    ).all()
    by_id = {seed.id: seed for seed in seeds}
    for user in existing:
        if user.id not in by_id:
            raise ValueError(f"Preview user identity conflicts with existing user: {user.id}")


def seed_preview_users(session: Session, path: Path, *, recipe_language: str) -> int:
    seeds = _parse_preview_users(path)
    _validate_database_identity_conflicts(session, seeds)

    for seed in seeds:
        user = session.get(User, seed.id)
        if user is None:
            user = create_user(
                session,
                user_id=seed.id,
                auth_provider=seed.auth_provider,
                auth_user_id=seed.auth_user_id,
                email=seed.email,
                recipe_language=recipe_language,
            )
        user.auth_provider = seed.auth_provider
        user.auth_user_id = seed.auth_user_id
        user.email = seed.email
        user.status = seed.status
        if seed.status is not UserStatus.DELETION_PENDING:
            user.deletion_requested_at = None

        existing_roles = {assignment.role: assignment for assignment in user.role_assignments}
        for role, assignment in existing_roles.items():
            if role not in seed.roles:
                session.delete(assignment)
        for role in seed.roles - existing_roles.keys():
            user.role_assignments.append(UserRoleAssignment(role=role))

        initialize_user_defaults(user, recipe_language=recipe_language)

    session.flush()
    return len(seeds)
