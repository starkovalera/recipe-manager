from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import db_session
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.recipes.deletion import RecipeDeletionProcessingDisposition, process_recipe_deletion
from app.recipes.queries import list_stale_recipe_deletion_ids


def reconcile_stale_recipe_deletions() -> MaintenanceProcessingResult:
    """Select stale deletion-pending recipes and retry their deletion workflow.

    The operation may delete media and database records through the shared
    deletion processor. It is not read-only and excludes active or fresh recipes.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.stale_recipe_deletion_minutes)
    with db_session() as session:
        recipe_ids = list_stale_recipe_deletion_ids(
            session,
            cutoff=cutoff,
            limit=settings.maintenance_batch_size,
        )

    changed_count = 0
    failure_count = 0
    for recipe_id in recipe_ids:
        result = process_recipe_deletion(recipe_id)
        if result.disposition is RecipeDeletionProcessingDisposition.COMPLETED:
            changed_count += 1
        elif result.disposition is RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE:
            failure_count += 1

    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif changed_count:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.STALE_RECIPE_DELETION_RECONCILIATION,
        disposition=disposition,
        scanned_count=len(recipe_ids),
        changed_count=changed_count,
        failure_count=failure_count,
    )
