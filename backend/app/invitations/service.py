import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.auth.provider import get_auth_provider
from app.auth.types import AuthProviderError
from app.core.errors import InvitationCreateError, InvitationNotFoundError, InvitationRevokeError
from app.core.logging import log_error
from app.db.session import db_transaction
from app.invitations.constants import InvitationStatus
from app.invitations.queries import get_invitation, list_pending_invitations_by_email
from app.models import Invitation, User, new_id

logger = logging.getLogger(__name__)


def accept_pending_invitations(
    session: Session,
    *,
    auth_provider: AuthProviderType,
    email: str,
    accepted_at: datetime,
) -> None:
    for invitation in list_pending_invitations_by_email(
        session,
        auth_provider,
        email.strip().casefold(),
    ):
        expires_at = invitation.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= accepted_at:
                invitation.status = InvitationStatus.EXPIRED
                continue
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = accepted_at


def create_invitation(
    session: Session,
    *,
    email: str,
    created_by: User,
    redirect_url: str,
) -> Invitation:
    provider = get_auth_provider()
    normalized_email = email.strip().casefold()
    try:
        auth_invitation = provider.create_invitation(normalized_email, redirect_url=redirect_url)
    except AuthProviderError as error:
        raise InvitationCreateError() from error

    try:
        with db_transaction(session):
            invitation = Invitation(
                id=new_id(),
                auth_provider=provider.provider,
                auth_invitation_id=auth_invitation.id,
                email=normalized_email,
                status=InvitationStatus(auth_invitation.status.value),
                created_by_user_id=created_by.id,
                expires_at=auth_invitation.expires_at,
            )
            session.add(invitation)
            session.flush()
        return invitation
    except Exception as error:
        try:
            provider.revoke_invitation(auth_invitation.id)
        except AuthProviderError as compensation_error:
            log_error(
                logger,
                "Invitation creation compensation failed.",
                auth_provider=provider.provider.value,
                auth_invitation_id=auth_invitation.id,
                error=repr(compensation_error),
            )
        raise InvitationCreateError() from error


def revoke_invitation(session: Session, invitation_id: str) -> Invitation:
    with db_transaction(session):
        invitation = get_invitation(session, invitation_id)
        if invitation is None:
            raise InvitationNotFoundError()
        if invitation.status is not InvitationStatus.PENDING:
            return invitation
        auth_invitation_id = invitation.auth_invitation_id

    try:
        get_auth_provider().revoke_invitation(auth_invitation_id)
    except AuthProviderError as error:
        raise InvitationRevokeError() from error

    with db_transaction(session):
        invitation = get_invitation(session, invitation_id)
        if invitation is None:
            raise InvitationNotFoundError()
        if invitation.status is InvitationStatus.PENDING:
            invitation.status = InvitationStatus.REVOKED
            invitation.updated_at = datetime.now(timezone.utc)
        session.flush()
    return invitation
