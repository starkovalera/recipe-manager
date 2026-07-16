import base64
import json
from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from svix.webhooks import Webhook

from app.api.deps import get_session
from app.auth.constants import AuthProviderType
from app.auth.types import AuthenticatedIdentity, AuthUser
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.defaults import DEFAULT_TAG_NAMES
from app.invitations.constants import InvitationStatus
from app.main import create_app
from app.models import ClerkWebhookEvent, Invitation, Tag, User, UserSettings, UserStatus
from app.users import provisioning as provisioning_module

WEBHOOK_SECRET = f"whsec_{base64.b64encode(b'test-webhook-secret').decode()}"


def create_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="TEST",
        database_url="sqlite:///:memory:",
        clerk_webhook_signing_secret=WEBHOOK_SECRET,
        recipe_language="ru",
    )
    return TestClient(app), session_factory


def webhook_payload(
    event_type: str,
    *,
    auth_user_id: str,
    email: str | None = None,
    primary_email_address_id: str | None = "email-primary",
    email_addresses: list[dict[str, str]] | None = None,
) -> dict:
    data: dict = {"id": auth_user_id}
    if email_addresses is not None:
        data.update(
            {
                "primary_email_address_id": primary_email_address_id,
                "email_addresses": email_addresses,
            }
        )
    elif email is not None:
        data.update(
            {
                "primary_email_address_id": primary_email_address_id,
                "email_addresses": [
                    {
                        "id": "email-primary",
                        "email_address": email,
                    }
                ],
            }
        )
    return {
        "object": "event",
        "type": event_type,
        "data": data,
        "instance_id": "ins_test",
        "timestamp": 1716883200,
        "event_attributes": {},
    }


def signed_headers(body: str, *, message_id: str) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc)
    webhook = Webhook(WEBHOOK_SECRET)
    return {
        "svix-id": message_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": webhook.sign(message_id, timestamp, body),
        "content-type": "application/json",
    }


def post_webhook(client: TestClient, payload: dict, *, message_id: str):
    body = json.dumps(payload, separators=(",", ":"))
    return client.post("/webhooks/clerk", content=body, headers=signed_headers(body, message_id=message_id))


def test_signed_user_created_webhook_provisions_user_without_trusted_identity_header():
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="USER@example.test")

    response = post_webhook(client, payload, message_id="msg_created")

    assert response.status_code == 200
    assert response.json() == {"processed": True}
    with session_factory() as session:
        user = session.scalar(select(User).where(User.auth_user_id == "auth-user"))
        assert user is not None
        assert user.email == "user@example.test"
        assert user.settings is not None
        assert user.settings.recipe_language == "ru"
        assert {tag.name for tag in user.tags} == set(DEFAULT_TAG_NAMES)
        assert user.roles == set()
        event = session.get(ClerkWebhookEvent, "msg_created")
        assert event is not None
        assert event.event_type == "user.created"


def test_user_created_webhook_accepts_pending_invitation_for_primary_email():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(
            Invitation(
                id="invitation-1",
                auth_provider=AuthProviderType.CLERK,
                auth_invitation_id="auth-invitation-1",
                email="user@example.test",
                status=InvitationStatus.PENDING,
            )
        )
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="USER@example.test")

    response = post_webhook(client, payload, message_id="msg_invited")

    assert response.status_code == 200
    with session_factory() as session:
        invitation = session.get(Invitation, "invitation-1")
        assert invitation is not None
        assert invitation.status is InvitationStatus.ACCEPTED
        assert invitation.accepted_at is not None


def test_user_updated_webhook_does_not_accept_pending_invitation():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add_all(
            [
                User(id="user-1", auth_user_id="auth-user", email="user@example.test"),
                Invitation(
                    id="invitation-1",
                    auth_provider=AuthProviderType.CLERK,
                    auth_invitation_id="auth-invitation-1",
                    email="user@example.test",
                    status=InvitationStatus.PENDING,
                ),
            ]
        )
    payload = webhook_payload("user.updated", auth_user_id="auth-user", email="user@example.test")

    assert post_webhook(client, payload, message_id="msg_updated_invitation").status_code == 200

    with session_factory() as session:
        invitation = session.get(Invitation, "invitation-1")
        assert invitation is not None
        assert invitation.status is InvitationStatus.PENDING


def test_user_created_webhook_does_not_accept_expired_invitation():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(
            Invitation(
                id="invitation-1",
                auth_provider=AuthProviderType.CLERK,
                auth_invitation_id="auth-invitation-1",
                email="user@example.test",
                status=InvitationStatus.PENDING,
                expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
        )
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")

    assert post_webhook(client, payload, message_id="msg_expired_invitation").status_code == 200

    with session_factory() as session:
        invitation = session.get(Invitation, "invitation-1")
        assert invitation is not None
        assert invitation.status is InvitationStatus.EXPIRED
        assert invitation.accepted_at is None


def test_duplicate_webhook_is_idempotent():
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")

    first_response = post_webhook(client, payload, message_id="msg_duplicate")
    second_response = post_webhook(client, payload, message_id="msg_duplicate")

    assert first_response.json() == {"processed": True}
    assert second_response.json() == {"processed": False}
    with session_factory() as session:
        assert len(session.scalars(select(User)).all()) == 1
        assert len(session.scalars(select(UserSettings)).all()) == 1
        assert len(session.scalars(select(Tag)).all()) == len(DEFAULT_TAG_NAMES)
        event_count = session.execute(text("SELECT COUNT(*) FROM clerk_webhook_events WHERE event_id = 'msg_duplicate'")).scalar_one()
        assert event_count == 1


def test_explicit_provisioning_then_webhook_converges_without_duplicate_defaults(monkeypatch):
    client, session_factory = create_client()

    class StubAuthProvider:
        def get_user(self, auth_user_id: str) -> AuthUser:
            return AuthUser(id=auth_user_id, primary_email="user@example.test")

    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: StubAuthProvider())
    with session_factory() as session:
        identity = AuthenticatedIdentity(
            auth_provider=AuthProviderType.CLERK,
            auth_user_id="auth-user",
        )
        provisioning_module.provision_current_user(session, identity, recipe_language="ru")
        session.commit()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")

    response = post_webhook(client, payload, message_id="msg_after_provision")

    assert response.status_code == 200
    with session_factory() as session:
        assert len(session.scalars(select(User)).all()) == 1
        assert len(session.scalars(select(UserSettings)).all()) == 1
        assert len(session.scalars(select(Tag)).all()) == len(DEFAULT_TAG_NAMES)


def test_webhook_provisioning_then_explicit_provisioning_converges_without_provider_call(monkeypatch):
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")
    assert post_webhook(client, payload, message_id="msg_before_provision").status_code == 200

    class FailingAuthProvider:
        def get_user(self, auth_user_id: str) -> AuthUser:
            raise AssertionError("provider must not be called for an existing identity")

    monkeypatch.setattr(provisioning_module, "get_auth_provider", lambda: FailingAuthProvider())
    with session_factory() as session:
        result = provisioning_module.provision_current_user(
            session,
            AuthenticatedIdentity(auth_provider=AuthProviderType.CLERK, auth_user_id="auth-user"),
            recipe_language="ru",
        )

        assert result.created is False
        assert result.user.email == "user@example.test"
        assert len(session.scalars(select(User)).all()) == 1
        assert len(session.scalars(select(UserSettings)).all()) == 1
        assert len(session.scalars(select(Tag)).all()) == len(DEFAULT_TAG_NAMES)


def test_user_updated_webhook_updates_existing_identity_email():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="old@example.test"))
    payload = webhook_payload("user.updated", auth_user_id="auth-user", email="NEW@example.test")

    response = post_webhook(client, payload, message_id="msg_updated")

    assert response.status_code == 200
    with session_factory() as session:
        user = session.get(User, "user-1")
        assert user is not None
        assert user.email == "new@example.test"


def test_user_updated_email_collision_returns_conflict_without_marking_event_processed():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add_all(
            [
                User(id="user-1", auth_user_id="auth-user", email="old@example.test"),
                User(id="user-2", auth_user_id="other-auth-user", email="taken@example.test"),
            ]
        )
    payload = webhook_payload("user.updated", auth_user_id="auth-user", email="taken@example.test")

    response = post_webhook(client, payload, message_id="msg_collision")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "EMAIL_ALREADY_LINKED"
    with session_factory() as session:
        user = session.get(User, "user-1")
        assert user is not None
        assert user.email == "old@example.test"
        event_count = session.execute(text("SELECT COUNT(*) FROM clerk_webhook_events WHERE event_id = 'msg_collision'")).scalar_one()
        assert event_count == 0


def test_user_deleted_webhook_marks_existing_user_deletion_pending():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))
    payload = webhook_payload("user.deleted", auth_user_id="auth-user")

    response = post_webhook(client, payload, message_id="msg_deleted")

    assert response.status_code == 200
    with session_factory() as session:
        user = session.get(User, "user-1")
        assert user is not None
        assert user.status is UserStatus.DELETION_PENDING
        assert user.deletion_requested_at is not None


def test_user_deleted_webhook_enqueues_deletion_after_state_is_committed(monkeypatch):
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))
    published_user_ids: list[str] = []
    monkeypatch.setattr("app.api.routes.webhooks.enqueue_account_deletion", published_user_ids.append)
    payload = webhook_payload("user.deleted", auth_user_id="auth-user")

    response = post_webhook(client, payload, message_id="msg_deleted_enqueue")

    assert response.status_code == 200
    assert published_user_ids == ["user-1"]
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_repeated_user_deleted_events_preserve_original_deletion_timestamp():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))

    first_payload = webhook_payload("user.deleted", auth_user_id="auth-user")
    second_payload = webhook_payload("user.deleted", auth_user_id="auth-user")
    assert post_webhook(client, first_payload, message_id="msg_deleted_1").status_code == 200
    with session_factory() as session:
        first_timestamp = session.get(User, "user-1").deletion_requested_at

    assert post_webhook(client, second_payload, message_id="msg_deleted_2").status_code == 200

    with session_factory() as session:
        user = session.get(User, "user-1")
        assert user is not None
        assert user.deletion_requested_at == first_timestamp


def test_invalid_signature_is_rejected_without_processing_payload():
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")

    response = client.post(
        "/webhooks/clerk",
        json=payload,
        headers={
            "svix-id": "msg_invalid",
            "svix-timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "svix-signature": "v1,invalid",
        },
    )

    assert response.status_code == 400
    with session_factory() as session:
        assert session.scalars(select(User)).all() == []


def test_signed_user_event_without_primary_email_is_rejected():
    client, session_factory = create_client()
    with session_factory.begin() as session:
        session.add(
            Invitation(
                id="invitation-1",
                auth_provider=AuthProviderType.CLERK,
                auth_invitation_id="auth-invitation-1",
                email="user@example.test",
                status=InvitationStatus.PENDING,
            )
        )
    payload = webhook_payload(
        "user.updated",
        auth_user_id="auth-user",
        primary_email_address_id="email-primary",
        email_addresses=[],
    )

    response = post_webhook(client, payload, message_id="msg_missing_email")

    assert response.status_code == 400
    with session_factory() as session:
        assert session.scalars(select(User)).all() == []
        assert session.get(Invitation, "invitation-1").status is InvitationStatus.PENDING
        event_count = session.execute(text("SELECT COUNT(*) FROM clerk_webhook_events WHERE event_id = 'msg_missing_email'")).scalar_one()
        assert event_count == 0


def test_missing_svix_id_is_rejected_without_database_mutations():
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")
    body = json.dumps(payload, separators=(",", ":"))
    headers = signed_headers(body, message_id="msg_missing_header")
    del headers["svix-id"]

    response = client.post("/webhooks/clerk", content=body, headers=headers)

    assert response.status_code == 400
    with session_factory() as session:
        assert session.scalars(select(User)).all() == []
        assert session.scalars(select(ClerkWebhookEvent)).all() == []


def test_webhook_signature_verification_uses_exact_raw_body():
    client, session_factory = create_client()
    payload = webhook_payload("user.created", auth_user_id="auth-user", email="user@example.test")
    signed_body = json.dumps(payload, separators=(",", ":"))
    modified_body = json.dumps(payload, indent=2)

    response = client.post(
        "/webhooks/clerk",
        content=modified_body,
        headers=signed_headers(signed_body, message_id="msg_modified_body"),
    )

    assert response.status_code == 400
    with session_factory() as session:
        assert session.scalars(select(User)).all() == []
        assert session.scalars(select(ClerkWebhookEvent)).all() == []


def test_primary_email_id_must_match_an_email_entry():
    client, session_factory = create_client()
    payload = webhook_payload(
        "user.created",
        auth_user_id="auth-user",
        primary_email_address_id="email-missing",
        email_addresses=[{"id": "email-other", "email_address": "user@example.test"}],
    )

    response = post_webhook(client, payload, message_id="msg_email_mismatch")

    assert response.status_code == 400
    with session_factory() as session:
        assert session.scalars(select(User)).all() == []
        assert session.scalars(select(ClerkWebhookEvent)).all() == []


def test_webhook_idempotency_uses_svix_id_instead_of_json_fields():
    client, session_factory = create_client()
    payload = webhook_payload("user.updated", auth_user_id="auth-user", email="user@example.test")

    first_response = post_webhook(client, payload, message_id="msg_delivery_1")
    second_response = post_webhook(client, payload, message_id="msg_delivery_2")

    assert first_response.json() == {"processed": True}
    assert second_response.json() == {"processed": True}
    with session_factory() as session:
        assert len(session.scalars(select(User)).all()) == 1
        assert {event.event_id for event in session.scalars(select(ClerkWebhookEvent)).all()} == {
            "msg_delivery_1",
            "msg_delivery_2",
        }
