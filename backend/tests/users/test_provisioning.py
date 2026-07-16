import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.auth.types import AuthenticatedIdentity, AuthProviderError, AuthUser
from app.core.errors import AuthUserLookupError, EmailAlreadyLinkedError
from app.db.base import Base
from app.db.defaults import DEFAULT_TAG_NAMES
from app.models import Tag, User, UserSettings
from app.users import provisioning as provisioning_module


class StubAuthProvider:
    provider = AuthProviderType.CLERK

    def __init__(self, auth_user: AuthUser | None = None, error: Exception | None = None) -> None:
        self.auth_user = auth_user
        self.error = error
        self.calls: list[str] = []

    def get_user(self, auth_user_id: str) -> AuthUser:
        self.calls.append(auth_user_id)
        if self.error is not None:
            raise self.error
        assert self.auth_user is not None
        return self.auth_user


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def identity(auth_user_id: str = "auth-user") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(auth_provider=AuthProviderType.CLERK, auth_user_id=auth_user_id)


def test_provision_new_user_creates_settings_and_default_tags_without_roles(monkeypatch):
    session = create_session()
    provider = StubAuthProvider(AuthUser(id="auth-user", primary_email="USER@example.test"))

    def get_provider():
        assert session.in_transaction() is False
        return provider

    monkeypatch.setattr(provisioning_module, "get_auth_provider", get_provider)

    result = provisioning_module.provision_current_user(session, identity(), recipe_language="ru")

    assert result.created is True
    assert result.user.auth_user_id == "auth-user"
    assert result.user.email == "user@example.test"
    assert result.user.roles == set()
    assert result.user.settings is not None
    assert result.user.settings.recipe_language == "ru"
    assert {tag.name for tag in result.user.tags} == set(DEFAULT_TAG_NAMES)
    assert provider.calls == ["auth-user"]
    assert session.scalars(select(UserSettings)).all() == [result.user.settings]
    assert {tag.name for tag in session.scalars(select(Tag))} == set(DEFAULT_TAG_NAMES)


def test_provision_existing_active_user_does_not_call_provider_or_change_defaults(monkeypatch):
    session = create_session()
    user = User(
        id="existing-user",
        auth_user_id="auth-user",
        email="existing@example.test",
        settings=UserSettings(recipe_language="en"),
        tags=[Tag(name="custom")],
    )
    session.add(user)
    session.commit()
    provider = StubAuthProvider(error=AssertionError("provider must not be called"))
    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: provider)

    result = provisioning_module.provision_current_user(session, identity(), recipe_language="ru")

    assert result.created is False
    assert result.user.id == "existing-user"
    assert result.user.settings is not None
    assert result.user.settings.recipe_language == "en"
    assert [tag.name for tag in result.user.tags] == ["custom"]
    assert provider.calls == []


def test_provision_rejects_email_owned_by_another_identity(monkeypatch):
    session = create_session()
    session.add(User(id="existing-user", auth_user_id="other-auth-user", email="user@example.test"))
    session.commit()
    provider = StubAuthProvider(AuthUser(id="auth-user", primary_email="user@example.test"))
    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: provider)

    with pytest.raises(EmailAlreadyLinkedError):
        provisioning_module.provision_current_user(session, identity(), recipe_language="ru")

    assert session.scalars(select(User)).all()[0].id == "existing-user"


def test_provision_maps_provider_failure_to_application_error(monkeypatch):
    session = create_session()
    provider = StubAuthProvider(error=AuthProviderError("provider detail"))
    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: provider)

    with pytest.raises(AuthUserLookupError):
        provisioning_module.provision_current_user(session, identity(), recipe_language="ru")

    assert session.scalars(select(User)).all() == []


def test_provision_recovers_when_concurrent_request_created_same_identity(monkeypatch):
    session = create_session()
    provider = StubAuthProvider(AuthUser(id="auth-user", primary_email="user@example.test"))
    concurrent_user = User(id="concurrent-user", auth_user_id="auth-user", email="user@example.test")
    lookup_results = iter([None, None, concurrent_user])
    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: provider)
    monkeypatch.setattr(
        provisioning_module,
        "get_user_by_auth_identity",
        lambda session, auth_provider, auth_user_id: next(lookup_results),
    )

    def raise_integrity_error(*args, **kwargs):
        raise provisioning_module.IntegrityError("insert", {}, RuntimeError("duplicate"))

    monkeypatch.setattr(provisioning_module, "create_user", raise_integrity_error)

    result = provisioning_module.provision_current_user(session, identity(), recipe_language="ru")

    assert result == provisioning_module.UserProvisioningResult(user=concurrent_user, created=False)
