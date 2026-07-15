from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from app.auth.constants import AuthProviderType


class AuthProviderError(Exception):
    """An authentication provider returned an unavailable or unusable response."""


class AuthInvitationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class AuthenticatedIdentity:
    auth_provider: AuthProviderType
    auth_user_id: str


@dataclass(frozen=True)
class AuthUser:
    id: str
    primary_email: str


@dataclass(frozen=True)
class AuthInvitation:
    id: str
    email: str
    status: AuthInvitationStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None


class AuthProvider(Protocol):
    provider: AuthProviderType

    def get_user(self, auth_user_id: str) -> AuthUser: ...

    def delete_user(self, auth_user_id: str) -> None: ...

    def create_invitation(self, email: str, *, redirect_url: str) -> AuthInvitation: ...

    def revoke_invitation(self, invitation_id: str) -> AuthInvitation: ...
