from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import db_session
from app.imports.error_codes import ImportProcessingErrorCode
from app.imports.error_policy import IMPORT_ERROR_POLICIES
from app.imports.events import build_job_event
from app.imports.queries import get_import_job_unscoped_for_update, list_stale_import_job_ids
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.models import ImportEventType, ImportJobStatus
from app.notifications.notification_data import ImportFailedNotification, build_notification
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message
from app.queueing.queries import has_pending_outbox_message


def reconcile_stale_imports() -> MaintenanceProcessingResult:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.stale_import_minutes)
    with db_session() as session:
        job_ids = list_stale_import_job_ids(
            session,
            cutoff=cutoff,
            limit=settings.maintenance_batch_size,
        )

    changed_count = 0
    scheduled_message_ids: list[str] = []
    policy = IMPORT_ERROR_POLICIES[ImportProcessingErrorCode.STALE_IMPORT_RECOVERY]
    error_payload = {
        "import_job_code": policy.import_job_error_code.value,
        "code": ImportProcessingErrorCode.STALE_IMPORT_RECOVERY,
        "message": policy.description,
    }

    for job_id in job_ids:
        with db_session() as session:
            job = get_import_job_unscoped_for_update(session, job_id)
            if job is None or job.status not in {ImportJobStatus.QUEUED, ImportJobStatus.RUNNING}:
                continue
            stale_timestamp = job.started_at if job.status is ImportJobStatus.RUNNING else job.updated_at
            if stale_timestamp is not None and stale_timestamp.tzinfo is None:
                stale_timestamp = stale_timestamp.replace(tzinfo=timezone.utc)
            if stale_timestamp is None or stale_timestamp > cutoff:
                continue
            if has_pending_outbox_message(session, QueueMessageType.IMPORT_JOB, job.id):
                continue

            changed_count += 1
            terminal = job.attempt_count >= settings.max_import_attempts
            if terminal:
                job.set_failed(policy.import_job_error_code, ImportProcessingErrorCode.STALE_IMPORT_RECOVERY)
                build_notification(
                    session,
                    ImportFailedNotification,
                    owner_id=job.owner_id,
                    entity_id=job.id,
                )
            else:
                job.set_queued_for_retry()
                scheduled_message_ids.append(schedule_outbox_message(session, QueueMessageType.IMPORT_JOB, job.id).id)

            build_job_event(
                session,
                import_job_id=job.id,
                event_type=ImportEventType.IMPORT_FAILED,
                error=error_payload,
                retryable=True,
                terminal=terminal,
                attempt_count=job.attempt_count,
                max_attempts=settings.max_import_attempts,
                reason="maintenance_stale_recovery",
            )

    failure_count = sum(not dispatch_outbox_message(message_id) for message_id in scheduled_message_ids)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif changed_count:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.STALE_IMPORT_RECONCILIATION,
        disposition=disposition,
        scanned_count=len(job_ids),
        changed_count=changed_count,
        scheduled_count=len(scheduled_message_ids),
        failure_count=failure_count,
    )
