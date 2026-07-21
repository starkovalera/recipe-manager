from collections.abc import Callable

from app.maintenance.accounts import reconcile_stale_account_deletions
from app.maintenance.constants import MaintenanceOperation
from app.maintenance.embeddings import reconcile_stale_embeddings
from app.maintenance.imports import reconcile_stale_imports
from app.maintenance.integrity import check_integrity
from app.maintenance.invitations import cleanup_expired_invitations
from app.maintenance.outbox import reconcile_pending_outbox
from app.maintenance.recipes import reconcile_stale_recipe_deletions
from app.maintenance.types import MaintenanceProcessingResult

MaintenanceHandler = Callable[[], MaintenanceProcessingResult]

MAINTENANCE_OPERATION_HANDLERS: dict[MaintenanceOperation, MaintenanceHandler] = {
    MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION: reconcile_pending_outbox,
    MaintenanceOperation.STALE_IMPORT_RECONCILIATION: reconcile_stale_imports,
    MaintenanceOperation.STALE_EMBEDDING_RECONCILIATION: reconcile_stale_embeddings,
    MaintenanceOperation.STALE_RECIPE_DELETION_RECONCILIATION: reconcile_stale_recipe_deletions,
    MaintenanceOperation.EXPIRED_INVITATION_CLEANUP: cleanup_expired_invitations,
    MaintenanceOperation.STALE_ACCOUNT_DELETION_RECONCILIATION: reconcile_stale_account_deletions,
    MaintenanceOperation.INTEGRITY_CHECK: check_integrity,
}


def run_maintenance_operation(operation: MaintenanceOperation) -> MaintenanceProcessingResult:
    result = MAINTENANCE_OPERATION_HANDLERS[operation]()
    if result.operation is not operation:
        raise RuntimeError("Maintenance handler returned an unexpected operation.")
    return result
