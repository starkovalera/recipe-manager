from datetime import datetime, timezone

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


def test_clerk_client_deletes_user_through_provider_contract():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "user_123", "deleted": True})

    client = ClerkClient(
        secret_key="secret",
        api_url="https://api.clerk.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    client.delete_user("user_123")

    assert [(request.method, str(request.url)) for request in requests] == [("DELETE", "https://api.clerk.test/v1/users/user_123")]


def test_clerk_client_creates_sanitized_invitation():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://api.clerk.test/v1/invitations"
        assert request.read().decode() == ('{"email_address":"person@example.test","redirect_url":"http://127.0.0.1:5173/sign-up"}')
        return httpx.Response(
            200,
            json={
                "id": "inv_123",
                "email_address": "PERSON@example.test",
                "status": "pending",
                "created_at": 1_784_000_000_000,
                "updated_at": 1_784_000_001_000,
                "expires_at": 1_786_592_000_000,
                "url": "https://accounts.example.test/tickets/secret-ticket",
            },
        )

    client = ClerkClient(
        secret_key="secret",
        api_url="https://api.clerk.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    invitation = client.create_invitation(
        "person@example.test",
        redirect_url="http://127.0.0.1:5173/sign-up",
    )

    assert invitation.id == "inv_123"
    assert invitation.email == "person@example.test"
    assert invitation.status == "PENDING"
    assert invitation.created_at == datetime.fromtimestamp(1_784_000_000, timezone.utc)
    assert invitation.updated_at == datetime.fromtimestamp(1_784_000_001, timezone.utc)
    assert invitation.expires_at == datetime.fromtimestamp(1_786_592_000, timezone.utc)
    assert not hasattr(invitation, "url")


def test_clerk_client_revokes_invitation():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://api.clerk.test/v1/invitations/inv_123/revoke"
        return httpx.Response(
            200,
            json={
                "id": "inv_123",
                "email_address": "person@example.test",
                "status": "revoked",
                "created_at": 1_784_000_000_000,
                "updated_at": 1_784_000_001_000,
                "expires_at": 1_786_592_000_000,
            },
        )

    client = ClerkClient(
        secret_key="secret",
        api_url="https://api.clerk.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    invitation = client.revoke_invitation("inv_123")

    assert invitation.id == "inv_123"
    assert invitation.status == "REVOKED"


def test_clerk_invitation_error_does_not_expose_provider_payload_or_secret():
    response_body = {"errors": [{"code": "form_identifier_exists", "long_message": "sensitive provider detail"}]}
    client = ClerkClient(
        secret_key="super-secret",
        api_url="https://api.clerk.test",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(422, json=response_body))),
    )

    try:
        client.create_invitation("person@example.test", redirect_url="http://127.0.0.1:5173/sign-up")
    except AuthProviderError as error:
        rendered = repr(error)
        assert "super-secret" not in rendered
        assert "sensitive provider detail" not in rendered
        assert "form_identifier_exists" not in rendered
    else:
        raise AssertionError("Expected provider error")
