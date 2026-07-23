from app.core.config import get_settings
from app.db.session import db_session
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.queueing.outbox import dispatch_outbox_message
from app.queueing.queries import list_pending_outbox_message_ids


def reconcile_pending_outbox() -> MaintenanceProcessingResult:
    """Select pending outbox rows and publish them, updating delivery state.

    This operation has broker side effects and is not read-only. It excludes
    already-published rows and does not mutate the referenced domain entities.
    """
    with db_session() as session:
        message_ids = list_pending_outbox_message_ids(
            session,
            limit=get_settings().maintenance_batch_size,
        )

    if not message_ids:
        return MaintenanceProcessingResult(
            operation=MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION,
            disposition=MaintenanceProcessingDisposition.NOOP,
        )

    failure_count = sum(not dispatch_outbox_message(message_id) for message_id in message_ids)
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION,
        disposition=(MaintenanceProcessingDisposition.RETRYABLE_FAILURE if failure_count else MaintenanceProcessingDisposition.COMPLETED),
        scanned_count=len(message_ids),
        changed_count=len(message_ids) - failure_count,
        failure_count=failure_count,
    )
