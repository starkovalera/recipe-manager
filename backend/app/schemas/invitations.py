from datetime import datetime

from pydantic import EmailStr

from app.auth.constants import AuthProviderType
from app.invitations.constants import InvitationStatus
from app.schemas.base import CamelModel


class InvitationCreateIn(CamelModel):
    email: EmailStr


class InvitationOut(CamelModel):
    id: str
    auth_provider: AuthProviderType
    auth_invitation_id: str
    email: str
    status: InvitationStatus
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    accepted_at: datetime | None


class InvitationListOut(CamelModel):
    items: list[InvitationOut]
