from app.auth.clerk_client import create_clerk_client
from app.auth.types import AuthProvider
from app.core.config import Settings, get_settings

_auth_provider: AuthProvider | None = None


def create_auth_provider(settings: Settings) -> AuthProvider:
    return create_clerk_client(settings.clerk_secret_key, settings.clerk_api_url)


def get_auth_provider() -> AuthProvider:
    global _auth_provider

    if _auth_provider is None:
        _auth_provider = create_auth_provider(get_settings())
    return _auth_provider
