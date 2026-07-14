import httpx

from app.auth.clerk_client import ClerkClient
from app.auth.constants import AuthProviderType
from app.auth.types import AuthProviderError


def test_clerk_client_returns_primary_email_without_exposing_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.clerk.test/v1/users/user_123"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "id": "user_123",
                "primary_email_address_id": "email_2",
                "email_addresses": [
                    {"id": "email_1", "email_address": "secondary@example.test"},
                    {"id": "email_2", "email_address": "primary@example.test"},
                ],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ClerkClient(secret_key="secret", api_url="https://api.clerk.test", http_client=http_client)

    user = client.get_user("user_123")

    assert user.id == "user_123"
    assert user.primary_email == "primary@example.test"
    assert client.provider is AuthProviderType.CLERK


def test_clerk_client_raises_mapped_error_for_provider_failure():
    http_client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(503)))
    client = ClerkClient(secret_key="secret", api_url="https://api.clerk.test", http_client=http_client)

    try:
        client.get_user("user_123")
    except AuthProviderError as error:
        assert type(error).__name__ == "ClerkApiError"
    else:
        raise AssertionError("Expected ClerkApiError")
