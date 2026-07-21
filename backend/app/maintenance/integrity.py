from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import db_session
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult
from app.models import (
    ImportJob,
    ImportJobStatus,
    QueueOutboxMessage,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingStatus,
    RecipeImage,
    User,
    UserStatus,
)
from app.queueing.constants import QueueOutboxStatus


@dataclass(frozen=True)
class IntegrityAnomalyCount:
    invariant: str
    count: int


def _successful_import_missing_recipe(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(ImportJob).where(
            ImportJob.status.in_({ImportJobStatus.SUCCEEDED, ImportJobStatus.SUCCEEDED_WITH_FLAGS}),
            ImportJob.created_recipe_id.is_(None),
        )
    ) or 0


def _ready_embedding_missing_data(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(RecipeEmbedding).where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.READY,
            or_(
                RecipeEmbedding.embedding.is_(None),
                RecipeEmbedding.input_hash.is_(None),
                RecipeEmbedding.model.is_(None),
            ),
        )
    ) or 0


def _running_embedding_missing_attempt_timestamp(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(RecipeEmbedding).where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.RUNNING,
            RecipeEmbedding.last_attempt_at.is_(None),
        )
    ) or 0


def _pending_user_missing_deletion_timestamp(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(User).where(
            User.status == UserStatus.DELETION_PENDING,
            User.deletion_requested_at.is_(None),
        )
    ) or 0


def _published_outbox_missing_published_timestamp(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(QueueOutboxMessage).where(
            QueueOutboxMessage.status == QueueOutboxStatus.PUBLISHED,
            QueueOutboxMessage.published_at.is_(None),
        )
    ) or 0


def _foreign_recipe_cover_image(session: Session) -> int:
    return session.scalar(
        select(func.count())
        .select_from(Recipe)
        .join(RecipeImage, RecipeImage.id == Recipe.cover_image_id)
        .where(RecipeImage.recipe_id != Recipe.id)
    ) or 0


INTEGRITY_CHECKS: dict[str, Callable[[Session], int]] = {
    "successful_import_missing_recipe": _successful_import_missing_recipe,
    "ready_embedding_missing_data": _ready_embedding_missing_data,
    "running_embedding_missing_attempt_timestamp": _running_embedding_missing_attempt_timestamp,
    "pending_user_missing_deletion_timestamp": _pending_user_missing_deletion_timestamp,
    "published_outbox_missing_published_timestamp": _published_outbox_missing_published_timestamp,
    "foreign_recipe_cover_image": _foreign_recipe_cover_image,
}


def check_integrity() -> MaintenanceProcessingResult:
    anomaly_counts: list[IntegrityAnomalyCount] = []
    failure_count = 0
    with db_session() as session:
        for invariant, check in INTEGRITY_CHECKS.items():
            try:
                anomaly_counts.append(IntegrityAnomalyCount(invariant, check(session)))
            except Exception:
                failure_count += 1

    anomaly_count = sum(item.count for item in anomaly_counts)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif anomaly_count:
        disposition = MaintenanceProcessingDisposition.ANOMALIES_FOUND
    else:
        disposition = MaintenanceProcessingDisposition.NOOP
    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.INTEGRITY_CHECK,
        disposition=disposition,
        scanned_count=len(INTEGRITY_CHECKS),
        failure_count=failure_count,
        anomaly_count=anomaly_count,
    )
