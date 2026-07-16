from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.access.constants import UserRole
from app.auth.constants import AuthProviderType
from app.db.base import Base
from app.local.users import seed_preview_users
from app.models import Tag, User, UserStatus


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def write_users(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_seed_preview_users_is_idempotent_and_synchronizes_exact_roles(tmp_path: Path):
    path = tmp_path / "users.toml"
    write_users(
        path,
        """
[[users]]
id = "preview-admin"
auth_provider = "CLERK"
auth_user_id = "provider-admin"
email = "admin@example.test"
status = "active"
roles = ["debug", "superadmin"]
""",
    )
    session = create_session()

    assert seed_preview_users(session, path, recipe_language="ru") == 1
    session.commit()
    write_users(
        path,
        """
[[users]]
id = "preview-admin"
auth_provider = "CLERK"
auth_user_id = "provider-admin"
email = "renamed@example.test"
status = "deactivated"
roles = ["debug"]
""",
    )
    assert seed_preview_users(session, path, recipe_language="en") == 1
    session.commit()

    user = session.get(User, "preview-admin")
    assert user is not None
    assert user.auth_provider is AuthProviderType.CLERK
    assert user.auth_user_id == "provider-admin"
    assert user.email == "renamed@example.test"
    assert user.status is UserStatus.DEACTIVATED
    assert user.roles == {UserRole.DEBUG}
    assert user.settings is not None and user.settings.recipe_language == "en"
    assert session.query(Tag).filter_by(owner_id=user.id).count() > 0


@pytest.mark.parametrize("duplicate_field", ["id", "auth_user_id", "email"])
def test_seed_preview_users_validates_complete_file_before_mutation(tmp_path: Path, duplicate_field: str):
    values = {
        "id": ("one", "two"),
        "auth_user_id": ("provider-one", "provider-two"),
        "email": ("one@example.test", "two@example.test"),
    }
    first = {key: pair[0] for key, pair in values.items()}
    second = {key: pair[1] for key, pair in values.items()}
    second[duplicate_field] = first[duplicate_field]
    path = tmp_path / "users.toml"
    write_users(
        path,
        f"""
[[users]]
id = "{first["id"]}"
auth_provider = "CLERK"
auth_user_id = "{first["auth_user_id"]}"
email = "{first["email"]}"
status = "active"
roles = []

[[users]]
id = "{second["id"]}"
auth_provider = "CLERK"
auth_user_id = "{second["auth_user_id"]}"
email = "{second["email"]}"
status = "active"
roles = []
""",
    )
    session = create_session()

    with pytest.raises(ValueError, match="Duplicate"):
        seed_preview_users(session, path, recipe_language="ru")

    assert session.query(User).count() == 0


def test_seed_preview_users_rejects_missing_and_invalid_files(tmp_path: Path):
    session = create_session()
    with pytest.raises(ValueError, match="does not exist"):
        seed_preview_users(session, tmp_path / "missing.toml", recipe_language="ru")

    path = tmp_path / "users.toml"
    write_users(
        path,
        """
[[users]]
id = "one"
auth_provider = "CLERK"
auth_user_id = "provider-one"
email = "one@example.test"
status = "unknown"
roles = ["made-up"]
""",
    )
    with pytest.raises(ValueError, match="status"):
        seed_preview_users(session, path, recipe_language="ru")
