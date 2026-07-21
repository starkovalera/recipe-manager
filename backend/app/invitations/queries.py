from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.invitations.constants import InvitationStatus
from app.models import Invitation


def list_invitations(session: Session) -> list[Invitation]:
    return list(session.scalars(select(Invitation).order_by(Invitation.created_at.desc(), Invitation.id)))


def get_invitation(session: Session, invitation_id: str) -> Invitation | None:
    return session.get(Invitation, invitation_id)


def get_invitation_for_update(session: Session, invitation_id: str) -> Invitation | None:
    return session.scalar(select(Invitation).where(Invitation.id == invitation_id).with_for_update())


def list_expired_pending_invitation_ids(
    session: Session,
    *,
    now: datetime,
    limit: int,
) -> list[str]:
    return list(
        session.scalars(
            select(Invitation.id)
            .where(
                Invitation.status == InvitationStatus.PENDING,
                Invitation.expires_at.is_not(None),
                Invitation.expires_at <= now,
            )
            .order_by(Invitation.expires_at, Invitation.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )


def list_pending_invitations_by_email(
    session: Session,
    auth_provider: AuthProviderType,
    email: str,
) -> list[Invitation]:
    return list(
        session.scalars(
            select(Invitation).where(
                Invitation.auth_provider == auth_provider,
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
    )
