from __future__ import annotations

import httpx

from app.auth.constants import AuthProviderType
from app.auth.types import AuthProviderError, AuthUser


class ClerkApiError(AuthProviderError):
    """Clerk returned an unavailable or unusable response."""


class ClerkClient:
    provider = AuthProviderType.CLERK

    def __init__(
        self,
        *,
        secret_key: str,
        api_url: str = "https://api.clerk.com",
        timeout: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._secret_key = secret_key
        self._base_url = f"{api_url.rstrip('/')}/v1"
        self._client = http_client or httpx.Client(timeout=timeout)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._client.request(
                method,
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {self._secret_key}"},
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except (httpx.HTTPError, ValueError) as error:
            raise ClerkApiError("Clerk API request failed.") from error

    def get_user(self, clerk_user_id: str) -> AuthUser:
        payload = self._request("GET", f"/users/{clerk_user_id}")
        primary_email_id = payload.get("primary_email_address_id")
        primary_email = next(
            (item.get("email_address") for item in payload.get("email_addresses", []) if item.get("id") == primary_email_id),
            None,
        )
        if payload.get("id") != clerk_user_id or not isinstance(primary_email, str) or not primary_email:
            raise ClerkApiError("Clerk user response is missing a primary email.")
        return AuthUser(id=clerk_user_id, primary_email=primary_email.casefold())

    def delete_user(self, clerk_user_id: str) -> None:
        self._request("DELETE", f"/users/{clerk_user_id}")


def create_clerk_client(secret_key: str | None, api_url: str) -> ClerkClient:
    if not secret_key:
        raise ClerkApiError("Clerk secret key is not configured.")
    return ClerkClient(secret_key=secret_key, api_url=api_url)
