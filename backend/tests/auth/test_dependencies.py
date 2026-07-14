import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps import get_authenticated_identity, get_current_user
from app.auth.constants import AuthProviderType
from app.auth.types import AuthenticatedIdentity
from app.core.errors import AuthenticationRequiredError, InvalidTrustedIdentityError
from app.db.base import Base
from app.models import User


def request_with_subject(subject: str | None) -> Request:
    headers = [] if subject is None else [(b"x-authenticated-subject", subject.encode())]
    return Request({"type": "http", "headers": headers})


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_authenticated_identity_comes_only_from_trusted_subject_header():
    identity = get_authenticated_identity(request_with_subject("auth-user"))

    assert identity == AuthenticatedIdentity(
        auth_provider=AuthProviderType.CLERK,
        auth_user_id="auth-user",
    )


def test_authenticated_identity_requires_trusted_subject_header():
    with pytest.raises(AuthenticationRequiredError):
        get_authenticated_identity(request_with_subject(None))


def test_authenticated_identity_rejects_blank_trusted_subject_header():
    with pytest.raises(InvalidTrustedIdentityError):
        get_authenticated_identity(request_with_subject("   "))


def test_current_user_lookup_closes_read_transaction_on_shared_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    session.add(User(id="internal-user", auth_user_id="auth-user", email="user@example.test"))
    session.commit()

    user = get_current_user(
        session,
        AuthenticatedIdentity(auth_provider=AuthProviderType.CLERK, auth_user_id="auth-user"),
    )

    assert user.id == "internal-user"
    assert session.in_transaction() is False
