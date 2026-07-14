from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.constants import TRUSTED_SUBJECT_HEADER, AuthProviderType
from app.auth.current_user import resolve_current_user
from app.auth.types import AuthenticatedIdentity
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationRequiredError, InvalidTrustedIdentityError
from app.db.session import db_transaction, get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_authenticated_identity(request: Request) -> AuthenticatedIdentity:
    auth_user_id = request.headers.get(TRUSTED_SUBJECT_HEADER)
    if auth_user_id is None:
        raise AuthenticationRequiredError()
    auth_user_id = auth_user_id.strip()
    if not auth_user_id:
        raise InvalidTrustedIdentityError()
    return AuthenticatedIdentity(
        auth_provider=AuthProviderType.CLERK,
        auth_user_id=auth_user_id,
    )


AuthenticatedIdentityDep = Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)]


def get_current_user(session: SessionDep, identity: AuthenticatedIdentityDep) -> User:
    with db_transaction(session):
        return resolve_current_user(session, identity)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
