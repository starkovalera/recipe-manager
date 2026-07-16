from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from app.auth.constants import AuthProviderType
from app.auth.types import AuthenticatedIdentity
from app.core.config import Settings, get_settings
from app.core.errors import InvalidWebhookError
from app.invitations.service import accept_pending_invitations
from app.models import ClerkWebhookEvent, UserStatus
from app.users.provisioning import synchronize_auth_user
from app.users.queries import get_user_by_auth_identity


class ClerkEmailAddress(BaseModel):
    id: str
    email_address: str


class ClerkUserPayload(BaseModel):
    id: str
    primary_email_address_id: str
    email_addresses: list[ClerkEmailAddress]

    @property
    def primary_email(self) -> str:
        email = next(
            (item.email_address for item in self.email_addresses if item.id == self.primary_email_address_id),
            None,
        )
        if email is None:
            raise InvalidWebhookError()
        return email


class ClerkDeletedUserPayload(BaseModel):
    id: str


class ClerkWebhookBody(BaseModel):
    type: str
    data: dict[str, Any]


@dataclass(frozen=True)
class VerifiedClerkWebhook:
    event_id: str
    event_type: str
    data: dict[str, Any]


async def verify_clerk_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> VerifiedClerkWebhook:
    if not settings.clerk_webhook_signing_secret:
        raise InvalidWebhookError()
    body = await request.body()
    try:
        payload = Webhook(settings.clerk_webhook_signing_secret).verify(body, dict(request.headers))
        webhook_body = ClerkWebhookBody.model_validate(payload)
    except (ValidationError, ValueError, WebhookVerificationError) as error:
        raise InvalidWebhookError() from error
    event_id = (request.headers.get("svix-id") or "").strip()
    if not event_id:
        raise InvalidWebhookError()
    return VerifiedClerkWebhook(
        event_id=event_id,
        event_type=webhook_body.type,
        data=webhook_body.data,
    )


VerifiedClerkWebhookDep = Annotated[VerifiedClerkWebhook, Depends(verify_clerk_webhook)]


@dataclass(frozen=True)
class ClerkWebhookProcessingResult:
    processed: bool
    deletion_user_id: str | None = None


def process_clerk_webhook(
    session: Session,
    event: VerifiedClerkWebhook,
    *,
    recipe_language: str,
) -> ClerkWebhookProcessingResult:
    if session.get(ClerkWebhookEvent, event.event_id) is not None:
        return ClerkWebhookProcessingResult(processed=False)

    deletion_user_id: str | None = None

    if event.event_type in {"user.created", "user.updated"}:
        try:
            user_payload = ClerkUserPayload.model_validate(event.data)
        except ValidationError as error:
            raise InvalidWebhookError() from error
        synchronize_auth_user(
            session,
            AuthenticatedIdentity(
                auth_provider=AuthProviderType.CLERK,
                auth_user_id=user_payload.id,
            ),
            email=user_payload.primary_email,
            recipe_language=recipe_language,
        )
        if event.event_type == "user.created":
            accept_pending_invitations(
                session,
                auth_provider=AuthProviderType.CLERK,
                email=user_payload.primary_email,
                accepted_at=datetime.now(timezone.utc),
            )
    elif event.event_type == "user.deleted":
        try:
            user_payload = ClerkDeletedUserPayload.model_validate(event.data)
        except ValidationError as error:
            raise InvalidWebhookError() from error
        user = get_user_by_auth_identity(session, AuthProviderType.CLERK, user_payload.id)
        if user is not None and user.status is not UserStatus.DELETION_PENDING:
            user.status = UserStatus.DELETION_PENDING
            user.deletion_requested_at = datetime.now(timezone.utc)
        if user is not None:
            deletion_user_id = user.id

    session.add(ClerkWebhookEvent(event_id=event.event_id, event_type=event.event_type))
    return ClerkWebhookProcessingResult(processed=True, deletion_user_id=deletion_user_id)
