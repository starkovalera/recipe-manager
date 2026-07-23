from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import db_session
from app.embeddings.events import add_embedding_event
from app.embeddings.queries import get_active_recipe_embedding_for_update, list_stale_recipe_embedding_ids
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.models import RecipeEmbeddingEventType, RecipeEmbeddingStatus
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message
from app.queueing.queries import has_pending_outbox_message


def reconcile_stale_embeddings() -> MaintenanceProcessingResult:
    """Select stale embedding work and requeue it without calling the provider.

    The operation mutates embedding state/events and outbox rows and may publish
    queue messages. It is not read-only and excludes fresh work and embeddings
    that already have pending delivery intents.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.stale_embedding_minutes)
    with db_session() as session:
        recipe_ids = list_stale_recipe_embedding_ids(
            session,
            cutoff=cutoff,
            limit=settings.maintenance_batch_size,
        )

    changed_count = 0
    message_ids: list[str] = []
    for recipe_id in recipe_ids:
        with db_session() as session:
            embedding = get_active_recipe_embedding_for_update(session, recipe_id)
            if embedding is None or embedding.status not in {
                RecipeEmbeddingStatus.RUNNING,
                RecipeEmbeddingStatus.STALE,
            }:
                continue
            stale_timestamp = embedding.last_attempt_at if embedding.status is RecipeEmbeddingStatus.RUNNING else embedding.updated_at
            if stale_timestamp is not None and stale_timestamp.tzinfo is None:
                stale_timestamp = stale_timestamp.replace(tzinfo=timezone.utc)
            if stale_timestamp is None or stale_timestamp > cutoff:
                continue
            if has_pending_outbox_message(session, QueueMessageType.RECIPE_EMBEDDING, recipe_id):
                continue

            if embedding.status is RecipeEmbeddingStatus.RUNNING:
                embedding.status = RecipeEmbeddingStatus.STALE
                embedding.error_message = None
                add_embedding_event(
                    session,
                    embedding=embedding,
                    owner_id=embedding.recipe.owner_id,
                    event_type=RecipeEmbeddingEventType.STALE_REQUEUED,
                    payload={"reason": "maintenance_stale_recovery"},
                )
            message_ids.append(schedule_outbox_message(session, QueueMessageType.RECIPE_EMBEDDING, recipe_id).id)
            changed_count += 1

    failure_count = sum(not dispatch_outbox_message(message_id) for message_id in message_ids)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif changed_count:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.STALE_EMBEDDING_RECONCILIATION,
        disposition=disposition,
        scanned_count=len(recipe_ids),
        changed_count=changed_count,
        scheduled_count=len(message_ids),
        failure_count=failure_count,
    )
