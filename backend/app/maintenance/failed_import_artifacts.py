from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath, PureWindowsPath
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import db_session
from app.imports.events import build_job_event
from app.imports.queries import (
    get_import_job_unscoped_for_update,
    list_failed_import_artifact_cleanup_candidate_ids,
    list_import_job_sources,
)
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.reports import MaintenanceReport, save_maintenance_report_if_required
from app.maintenance.storage import list_all_storage_objects
from app.maintenance.types import MaintenanceProcessingResult
from app.models import ImportEventType, ImportJob, ImportJobStatus
from app.queueing.constants import QueueMessageType
from app.queueing.queries import has_pending_outbox_message
from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StorageUserPurpose
from app.storage.runtime import get_storage_service
from app.storage.types import StorageUserContext


@dataclass(frozen=True)
class ImportSourceArtifactSnapshot:
    source_id: str
    storage_key: str | None


@dataclass(frozen=True)
class FailedImportArtifactSnapshot:
    import_job_id: str
    owner_id: str
    sources: tuple[ImportSourceArtifactSnapshot, ...]
    source_prefix: str
    derived_prefix: str


def _is_eligible_for_cleanup(job: ImportJob, *, cutoff: datetime, session: Session) -> bool:
    finished_at = job.finished_at
    if finished_at is not None and finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    return (
        job.status is ImportJobStatus.FAILED
        and finished_at is not None
        and finished_at <= cutoff
        and job.created_recipe_id is None
        and not has_pending_outbox_message(session, QueueMessageType.IMPORT_JOB, job.id)
    )


def _load_cleanup_snapshot(job_id: str, *, cutoff: datetime) -> FailedImportArtifactSnapshot | None:
    with db_session() as session:
        job = get_import_job_unscoped_for_update(session, job_id)
        if job is None or not _is_eligible_for_cleanup(job, cutoff=cutoff, session=session):
            return None
        sources = tuple(
            ImportSourceArtifactSnapshot(source.id, source.image_storage_key) for source in list_import_job_sources(session, job.id)
        )
        source_prefix = StorageUserContext(
            owner_id=job.owner_id,
            purpose=StorageUserPurpose.IMPORT_SOURCE,
            entity_id=job.id,
        ).build_prefix()
        derived_prefix = StorageUserContext(
            owner_id=job.owner_id,
            purpose=StorageUserPurpose.IMPORT_DERIVED,
            entity_id=job.id,
        ).build_prefix()
        return FailedImportArtifactSnapshot(
            import_job_id=job.id,
            owner_id=job.owner_id,
            sources=sources,
            source_prefix=f"{source_prefix}/",
            derived_prefix=f"{derived_prefix}/",
        )


def _cleanup_snapshot_storage(storage: StorageService, snapshot: FailedImportArtifactSnapshot) -> dict[str, object]:
    source_keys = [
        item.storage_key for item in list_all_storage_objects(storage, StorageLocation.USER_MEDIA, prefix=snapshot.source_prefix)
    ]
    derived_keys = [
        item.storage_key for item in list_all_storage_objects(storage, StorageLocation.USER_MEDIA, prefix=snapshot.derived_prefix)
    ]
    referenced_keys = [source.storage_key for source in snapshot.sources if source.storage_key is not None]
    suspicious_keys = []
    for key in referenced_keys:
        belongs_to_job = key.startswith(snapshot.source_prefix) or key.startswith(snapshot.derived_prefix)
        posix_key = PurePosixPath(key)
        windows_key = PureWindowsPath(key)
        safe_legacy_key = (
            "/" not in key
            and "\\" not in key
            and not posix_key.is_absolute()
            and not windows_key.is_absolute()
            and ".." not in posix_key.parts
            and ".." not in windows_key.parts
        )
        if not belongs_to_job and not safe_legacy_key:
            suspicious_keys.append(key)
    safe_referenced_keys = [key for key in referenced_keys if key not in suspicious_keys]
    safe_keys = sorted(set(source_keys) | set(derived_keys) | set(safe_referenced_keys))
    delete_outcomes: list[dict[str, object]] = []
    for storage_key in safe_keys:
        try:
            storage.delete(StorageLocation.USER_MEDIA, storage_key)
            delete_outcomes.append({"storageKey": storage_key, "deleted": True})
        except Exception as error:
            delete_outcomes.append(
                {
                    "storageKey": storage_key,
                    "deleted": False,
                    "errorType": type(error).__name__,
                }
            )

    remaining_keys = sorted(
        {item.storage_key for item in list_all_storage_objects(storage, StorageLocation.USER_MEDIA, prefix=snapshot.source_prefix)}
        | {item.storage_key for item in list_all_storage_objects(storage, StorageLocation.USER_MEDIA, prefix=snapshot.derived_prefix)}
    )
    return {
        "importJobId": snapshot.import_job_id,
        "ownerId": snapshot.owner_id,
        "sources": [{"importJobSourceId": source.source_id, "storageKey": source.storage_key} for source in snapshot.sources],
        "listedKeys": sorted(set(source_keys) | set(derived_keys)),
        "deleteOutcomes": delete_outcomes,
        "remainingKeys": remaining_keys,
        "suspiciousKeys": suspicious_keys,
    }


def _finalize_cleanup(
    snapshot: FailedImportArtifactSnapshot,
    storage_result: dict[str, object],
    *,
    cutoff: datetime,
) -> bool:
    if storage_result["suspiciousKeys"] or storage_result["remainingKeys"]:
        return False
    if any(not outcome["deleted"] for outcome in storage_result["deleteOutcomes"]):
        return False

    removed_keys = {outcome["storageKey"] for outcome in storage_result["deleteOutcomes"]}
    with db_session() as session:
        job = get_import_job_unscoped_for_update(session, snapshot.import_job_id)
        if job is None or not _is_eligible_for_cleanup(job, cutoff=cutoff, session=session):
            return False
        sources = list_import_job_sources(session, job.id)
        for source in sources:
            if source.image_storage_key in removed_keys:
                source.image_storage_key = None
        if any(source.image_storage_key is not None for source in sources):
            return False
        job.status = ImportJobStatus.FAILED_ARTIFACTS_REMOVED
        build_job_event(
            session,
            import_job_id=job.id,
            event_type=ImportEventType.IMPORT_ARTIFACTS_REMOVED,
            removed_artifact_count=len(removed_keys),
        )
        return True


def cleanup_failed_import_artifacts() -> MaintenanceProcessingResult:
    """Select old failed imports and remove their retained source/derived artifacts.

    The operation deletes safe storage objects, clears their DB references, and
    finalizes job state/events. It is not read-only; it excludes jobs with a recipe,
    pending queue intent, unsafe key, or retention window that has not elapsed.
    """
    settings = get_settings()
    storage = get_storage_service(settings)
    started_at = datetime.now(timezone.utc)
    cutoff = started_at - timedelta(hours=settings.failed_import_artifact_retention_hours)
    details: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    changed_count = 0

    try:
        with db_session() as session:
            candidate_ids = list_failed_import_artifact_cleanup_candidate_ids(
                session,
                cutoff=cutoff,
                limit=settings.maintenance_batch_size,
            )
    except Exception as error:
        candidate_ids = []
        errors.append({"stage": "candidateQuery", "errorType": type(error).__name__})

    for job_id in candidate_ids:
        try:
            snapshot = _load_cleanup_snapshot(job_id, cutoff=cutoff)
            if snapshot is None:
                continue
            storage_result = _cleanup_snapshot_storage(storage, snapshot)
            finalized = _finalize_cleanup(snapshot, storage_result, cutoff=cutoff)
            storage_result["finalized"] = finalized
            details.append(storage_result)
            changed_count += int(finalized)
        except Exception as error:
            errors.append(
                {
                    "importJobId": job_id,
                    "stage": "cleanup",
                    "errorType": type(error).__name__,
                }
            )

    anomaly_count = sum(bool(detail["suspiciousKeys"]) for detail in details)
    failure_count = len(errors) + sum(
        bool(detail["remainingKeys"])
        or any(not outcome["deleted"] for outcome in detail["deleteOutcomes"])
        or not detail["finalized"]
        and not detail["suspiciousKeys"]
        for detail in details
    )
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif anomaly_count:
        disposition = MaintenanceProcessingDisposition.ANOMALIES_FOUND
    elif changed_count:
        disposition = MaintenanceProcessingDisposition.COMPLETED
    else:
        disposition = MaintenanceProcessingDisposition.NOOP

    report = MaintenanceReport(
        schema_version=1,
        report_id=uuid4().hex,
        operation=MaintenanceOperation.FAILED_IMPORT_ARTIFACT_CLEANUP,
        environment=settings.app_env.value,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        disposition=disposition,
        parameters={"cutoff": cutoff.isoformat(), "batchSize": settings.maintenance_batch_size},
        summary={"anomalyCount": anomaly_count, "failureCount": failure_count},
        details={"jobs": details},
        errors=tuple(errors),
    )
    try:
        save_maintenance_report_if_required(storage, report)
    except Exception:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
        failure_count += 1

    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.FAILED_IMPORT_ARTIFACT_CLEANUP,
        disposition=disposition,
        scanned_count=len(candidate_ids),
        changed_count=changed_count,
        failure_count=failure_count,
        anomaly_count=anomaly_count,
    )
