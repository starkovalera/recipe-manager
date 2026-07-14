from dataclasses import dataclass
from typing import Protocol

from app.auth.constants import AuthProviderType


class AuthProviderError(Exception):
    """An authentication provider returned an unavailable or unusable response."""


@dataclass(frozen=True)
class AuthenticatedIdentity:
    auth_provider: AuthProviderType
    auth_user_id: str


@dataclass(frozen=True)
class AuthUser:
    id: str
    primary_email: str


class AuthProvider(Protocol):
    provider: AuthProviderType

    def get_user(self, auth_user_id: str) -> AuthUser: ...
