from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.constants import AuthProviderType
from app.invitations.constants import InvitationStatus
from app.models import Invitation


def list_invitations(session: Session) -> list[Invitation]:
    return list(session.scalars(select(Invitation).order_by(Invitation.created_at.desc(), Invitation.id)))


def get_invitation(session: Session, invitation_id: str) -> Invitation | None:
    return session.get(Invitation, invitation_id)


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
