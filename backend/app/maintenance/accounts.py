from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import db_session
from app.imports.constants import ACTIVE_IMPORT_STATUSES
from app.imports.queries import count_import_jobs_by_statuses
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.models import UserStatus
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message
from app.queueing.queries import has_pending_outbox_message
from app.users.queries import get_user_for_update, list_stale_account_deletion_user_ids


def reconcile_stale_account_deletions() -> MaintenanceProcessingResult:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.stale_account_deletion_minutes)
    with db_session() as session:
        user_ids = list_stale_account_deletion_user_ids(
            session,
            cutoff=cutoff,
            limit=settings.maintenance_batch_size,
        )

    message_ids: list[str] = []
    for user_id in user_ids:
        with db_session() as session:
            user = get_user_for_update(session, user_id)
            if user is None or user.status is not UserStatus.DELETION_PENDING:
                continue
            requested_at = user.deletion_requested_at
            if requested_at is not None and requested_at.tzinfo is None:
                requested_at = requested_at.replace(tzinfo=timezone.utc)
            if requested_at is None or requested_at > cutoff:
                continue
            if count_import_jobs_by_statuses(session, user.id, ACTIVE_IMPORT_STATUSES):
                continue
            if has_pending_outbox_message(session, QueueMessageType.ACCOUNT_DELETION, user.id):
                continue
            message_ids.append(
                schedule_outbox_message(session, QueueMessageType.ACCOUNT_DELETION, user.id).id
            )

    failure_count = sum(not dispatch_outbox_message(message_id) for message_id in message_ids)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif message_ids:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.STALE_ACCOUNT_DELETION_RECONCILIATION,
        disposition=disposition,
        scanned_count=len(user_ids),
        changed_count=len(message_ids),
        scheduled_count=len(message_ids),
        failure_count=failure_count,
    )
