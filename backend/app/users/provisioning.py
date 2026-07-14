from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.auth.current_user import ensure_user_is_active
from app.auth.provider import get_auth_provider
from app.auth.types import AuthenticatedIdentity, AuthProviderError
from app.core.errors import AuthUserLookupError, EmailAlreadyLinkedError
from app.db.defaults import DEFAULT_TAG_NAMES
from app.db.session import db_transaction
from app.models import Tag, User, UserSettings, new_id
from app.users.queries import get_user_by_auth_identity, get_user_by_email


@dataclass(frozen=True)
class UserProvisioningResult:
    user: User
    created: bool


def initialize_user_defaults(user: User, *, recipe_language: str) -> None:
    if user.settings is None:
        user.settings = UserSettings(recipe_language=recipe_language)
    elif user.settings.recipe_language != recipe_language:
        user.settings.recipe_language = recipe_language

    existing_tag_names = {tag.name for tag in user.tags}
    user.tags.extend(Tag(name=name) for name in DEFAULT_TAG_NAMES if name not in existing_tag_names)


def create_user(
    session: Session,
    *,
    user_id: str,
    email: str,
    recipe_language: str,
    auth_provider: AuthProviderType = AuthProviderType.CLERK,
    auth_user_id: str | None = None,
) -> User:
    user = User(
        id=user_id,
        auth_provider=auth_provider,
        auth_user_id=auth_user_id,
        email=email.strip().casefold(),
    )
    initialize_user_defaults(user, recipe_language=recipe_language)
    session.add(user)
    session.flush()
    return user


def _recover_provisioning_race(
    session: Session,
    identity: AuthenticatedIdentity,
    email: str,
    error: IntegrityError,
) -> UserProvisioningResult:
    with db_transaction(session):
        user = get_user_by_auth_identity(session, identity.auth_provider, identity.auth_user_id)
        if user is not None:
            return UserProvisioningResult(user=ensure_user_is_active(user), created=False)
        if get_user_by_email(session, email) is not None:
            raise EmailAlreadyLinkedError() from error
    raise error


def provision_current_user(
    session: Session,
    identity: AuthenticatedIdentity,
    *,
    recipe_language: str,
) -> UserProvisioningResult:
    with db_transaction(session):
        user = get_user_by_auth_identity(session, identity.auth_provider, identity.auth_user_id)
        if user is not None:
            return UserProvisioningResult(user=ensure_user_is_active(user), created=False)

    try:
        auth_user = get_auth_provider().get_user(identity.auth_user_id)
    except AuthProviderError as error:
        raise AuthUserLookupError() from error
    if auth_user.id != identity.auth_user_id:
        raise AuthUserLookupError()
    email = auth_user.primary_email.strip().casefold()

    try:
        with db_transaction(session):
            user = get_user_by_auth_identity(session, identity.auth_provider, identity.auth_user_id)
            if user is not None:
                return UserProvisioningResult(user=ensure_user_is_active(user), created=False)
            if get_user_by_email(session, email) is not None:
                raise EmailAlreadyLinkedError()
            user = create_user(
                session,
                user_id=new_id(),
                auth_provider=identity.auth_provider,
                auth_user_id=identity.auth_user_id,
                email=email,
                recipe_language=recipe_language,
            )
        return UserProvisioningResult(user=user, created=True)
    except IntegrityError as error:
        return _recover_provisioning_race(session, identity, email, error)
