from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import db_session
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.reports import MaintenanceReport, save_maintenance_report_if_required
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
from app.storage.runtime import get_storage_service


@dataclass(frozen=True)
class IntegrityCheckResult:
    invariant: str
    count: int
    records: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class IntegrityCheck:
    invariant: str
    find_records: Callable[[Session], tuple[dict[str, str], ...]]


def _successful_import_missing_recipe(session: Session) -> tuple[dict[str, str], ...]:
    job_ids = session.scalars(
        select(ImportJob.id).where(
            ImportJob.status.in_({ImportJobStatus.SUCCEEDED, ImportJobStatus.SUCCEEDED_WITH_FLAGS}),
            ImportJob.created_recipe_id.is_(None),
        )
    )
    return tuple({"importJobId": job_id} for job_id in job_ids)


def _ready_embedding_missing_data(session: Session) -> tuple[dict[str, str], ...]:
    recipe_ids = session.scalars(
        select(RecipeEmbedding.recipe_id).where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.READY,
            or_(
                RecipeEmbedding.embedding.is_(None),
                RecipeEmbedding.input_hash.is_(None),
                RecipeEmbedding.model.is_(None),
            ),
        )
    )
    return tuple({"recipeId": recipe_id} for recipe_id in recipe_ids)


def _running_embedding_missing_attempt_timestamp(session: Session) -> tuple[dict[str, str], ...]:
    recipe_ids = session.scalars(
        select(RecipeEmbedding.recipe_id).where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.RUNNING,
            RecipeEmbedding.last_attempt_at.is_(None),
        )
    )
    return tuple({"recipeId": recipe_id} for recipe_id in recipe_ids)


def _pending_user_missing_deletion_timestamp(session: Session) -> tuple[dict[str, str], ...]:
    user_ids = session.scalars(
        select(User.id).where(
            User.status == UserStatus.DELETION_PENDING,
            User.deletion_requested_at.is_(None),
        )
    )
    return tuple({"userId": user_id} for user_id in user_ids)


def _published_outbox_missing_published_timestamp(session: Session) -> tuple[dict[str, str], ...]:
    records = session.execute(
        select(QueueOutboxMessage.id, QueueOutboxMessage.entity_id).where(
            QueueOutboxMessage.status == QueueOutboxStatus.PUBLISHED,
            QueueOutboxMessage.published_at.is_(None),
        )
    )
    return tuple({"outboxMessageId": message_id, "entityId": entity_id} for message_id, entity_id in records)


def _foreign_recipe_cover_image(session: Session) -> tuple[dict[str, str], ...]:
    records = session.execute(
        select(Recipe.id, Recipe.cover_image_id)
        .join(RecipeImage, RecipeImage.id == Recipe.cover_image_id)
        .where(RecipeImage.recipe_id != Recipe.id)
    )
    return tuple({"recipeId": recipe_id, "coverImageId": cover_image_id} for recipe_id, cover_image_id in records)


INTEGRITY_CHECKS = (
    IntegrityCheck("successful_import_missing_recipe", _successful_import_missing_recipe),
    IntegrityCheck("ready_embedding_missing_data", _ready_embedding_missing_data),
    IntegrityCheck("running_embedding_missing_attempt_timestamp", _running_embedding_missing_attempt_timestamp),
    IntegrityCheck("pending_user_missing_deletion_timestamp", _pending_user_missing_deletion_timestamp),
    IntegrityCheck("published_outbox_missing_published_timestamp", _published_outbox_missing_published_timestamp),
    IntegrityCheck("foreign_recipe_cover_image", _foreign_recipe_cover_image),
)


def run_integrity_check() -> MaintenanceProcessingResult:
    """Report configured database invariant violations without mutating domain records."""
    settings = get_settings()
    storage = get_storage_service(settings)
    started_at = datetime.now(timezone.utc)
    check_results: list[IntegrityCheckResult] = []
    errors: list[dict[str, object]] = []
    for check in INTEGRITY_CHECKS:
        try:
            with db_session() as session:
                records = check.find_records(session)
            check_results.append(IntegrityCheckResult(check.invariant, len(records), records))
        except Exception as error:
            errors.append({"invariant": check.invariant, "errorType": type(error).__name__})

    anomaly_count = sum(item.count for item in check_results)
    failure_count = len(errors)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif anomaly_count:
        disposition = MaintenanceProcessingDisposition.ANOMALIES_FOUND
    else:
        disposition = MaintenanceProcessingDisposition.NOOP

    report = MaintenanceReport(
        schema_version=1,
        report_id=uuid4().hex,
        operation=MaintenanceOperation.INTEGRITY_CHECK,
        environment=settings.app_env.value,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        disposition=disposition,
        parameters={},
        summary={"anomalyCount": anomaly_count, "failureCount": failure_count},
        details={"checks": [{"invariant": item.invariant, "count": item.count, "records": item.records} for item in check_results]},
        errors=tuple(errors),
    )
    try:
        save_maintenance_report_if_required(storage, report)
    except Exception:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
        failure_count += 1

    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.INTEGRITY_CHECK,
        disposition=disposition,
        scanned_count=len(INTEGRITY_CHECKS),
        failure_count=failure_count,
        anomaly_count=anomaly_count,
    )
