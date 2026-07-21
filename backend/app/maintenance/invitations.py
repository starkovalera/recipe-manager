from datetime import datetime, timezone

from app.auth.provider import get_auth_provider
from app.core.config import get_settings
from app.db.session import db_session
from app.invitations.constants import InvitationStatus
from app.invitations.queries import get_invitation_for_update, list_expired_pending_invitation_ids
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult


def cleanup_expired_invitations() -> MaintenanceProcessingResult:
    now = datetime.now(timezone.utc)
    with db_session() as session:
        invitation_ids = list_expired_pending_invitation_ids(
            session,
            now=now,
            limit=get_settings().maintenance_batch_size,
        )

    if not invitation_ids:
        return MaintenanceProcessingResult(
            operation=MaintenanceOperation.EXPIRED_INVITATION_CLEANUP,
            disposition=MaintenanceProcessingDisposition.NOOP,
        )

    changed_count = 0
    failure_count = 0
    provider = get_auth_provider()
    for invitation_id in invitation_ids:
        with db_session() as session:
            invitation = get_invitation_for_update(session, invitation_id)
            if invitation is None or invitation.status is not InvitationStatus.PENDING:
                continue
            expires_at = invitation.expires_at
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at is None or expires_at > now:
                continue
            auth_invitation_id = invitation.auth_invitation_id

        try:
            provider.revoke_invitation(auth_invitation_id)
        except Exception:
            failure_count += 1
            continue

        with db_session() as session:
            invitation = get_invitation_for_update(session, invitation_id)
            if invitation is None or invitation.status is not InvitationStatus.PENDING:
                continue
            expires_at = invitation.expires_at
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at is None or expires_at > now:
                continue
            invitation.status = InvitationStatus.EXPIRED
            changed_count += 1

    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif changed_count:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.EXPIRED_INVITATION_CLEANUP,
        disposition=disposition,
        scanned_count=len(invitation_ids),
        changed_count=changed_count,
        failure_count=failure_count,
    )
