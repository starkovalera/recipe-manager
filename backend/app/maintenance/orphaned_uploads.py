import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import db_session
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.reports import MaintenanceReport, save_maintenance_report_if_required
from app.maintenance.storage import list_all_storage_objects
from app.maintenance.types import MaintenanceProcessingResult
from app.models import ImportJobSource, RecipeImage
from app.storage.constants import StorageLocation, StorageUserPurpose
from app.storage.keys import STORAGE_USER_PURPOSE_PREFIXES
from app.storage.runtime import get_storage_service
from app.storage.types import StorageObjectInfo

_STORAGE_SEGMENT = re.compile(r"[A-Za-z0-9_-]+")
_DETECTION_PURPOSES = (
    StorageUserPurpose.IMPORT_SOURCE,
    StorageUserPurpose.IMPORT_DERIVED,
    StorageUserPurpose.RECIPE_MEDIA,
)


def _load_storage_references(storage_keys: list[str]) -> dict[str, dict[str, list[str]]]:
    references = {key: {"importJobSourceIds": [], "recipeImageIds": []} for key in storage_keys}
    with db_session() as session:
        for offset in range(0, len(storage_keys), 500):
            batch = storage_keys[offset : offset + 500]
            for source_id, storage_key in session.execute(
                select(ImportJobSource.id, ImportJobSource.image_storage_key).where(ImportJobSource.image_storage_key.in_(batch))
            ):
                references[storage_key]["importJobSourceIds"].append(source_id)
            for image_id, storage_key in session.execute(
                select(RecipeImage.id, RecipeImage.storage_key).where(RecipeImage.storage_key.in_(batch))
            ):
                references[storage_key]["recipeImageIds"].append(image_id)
    return references


def _parse_storage_key(storage_key: str, purpose: StorageUserPurpose) -> dict[str, str] | None:
    prefix = STORAGE_USER_PURPOSE_PREFIXES[purpose]
    parts = storage_key.split("/")
    prefix_parts = prefix.split("/")
    if len(parts) != len(prefix_parts) + 3 or parts[: len(prefix_parts)] != prefix_parts:
        return None
    owner_id, entity_id, object_name = parts[-3:]
    if not all(_STORAGE_SEGMENT.fullmatch(value) for value in (owner_id, entity_id)) or not object_name:
        return None
    return {
        "purpose": purpose.value,
        "ownerId": owner_id,
        "entityId": entity_id,
    }


def _build_anomaly(
    item: StorageObjectInfo,
    purpose: StorageUserPurpose,
    references: dict[str, list[str]],
) -> dict[str, object] | None:
    parsed = _parse_storage_key(item.storage_key, purpose)
    has_reference = any(references.values())
    if parsed is not None and has_reference:
        return None
    anomaly: dict[str, object] = {
        "storageKey": item.storage_key,
        "sizeBytes": item.size_bytes,
        "lastModifiedAt": item.last_modified_at.isoformat(),
        "reason": "malformedStorageKey" if parsed is None else "unreferencedStorageObject",
    }
    if parsed is not None:
        anomaly.update(parsed)
    for key, record_ids in references.items():
        if record_ids:
            anomaly[key] = record_ids
    return anomaly


def detect_orphaned_uploads() -> MaintenanceProcessingResult:
    """Report old unreferenced user-media objects without deleting or repairing them."""
    settings = get_settings()
    storage = get_storage_service(settings)
    started_at = datetime.now(timezone.utc)
    cutoff = started_at - timedelta(hours=settings.orphaned_upload_min_age_hours)
    listed_objects: list[tuple[StorageUserPurpose, StorageObjectInfo]] = []
    errors: list[dict[str, object]] = []

    for purpose in _DETECTION_PURPOSES:
        prefix = f"{STORAGE_USER_PURPOSE_PREFIXES[purpose]}/"
        try:
            listed_objects.extend((purpose, item) for item in list_all_storage_objects(storage, StorageLocation.USER_MEDIA, prefix=prefix))
        except Exception as error:
            errors.append(
                {
                    "purpose": purpose.value,
                    "stage": "storageListing",
                    "errorType": type(error).__name__,
                }
            )

    anomalies: list[dict[str, object]] = []
    if not errors:
        try:
            references = _load_storage_references([item.storage_key for _, item in listed_objects])
            for purpose, item in listed_objects:
                last_modified_at = item.last_modified_at
                if last_modified_at.tzinfo is None:
                    last_modified_at = last_modified_at.replace(tzinfo=timezone.utc)
                if last_modified_at > cutoff:
                    continue
                anomaly = _build_anomaly(item, purpose, references[item.storage_key])
                if anomaly is not None:
                    anomalies.append(anomaly)
        except Exception as error:
            errors.append({"stage": "referenceQuery", "errorType": type(error).__name__})

    failure_count = len(errors)
    anomaly_count = len(anomalies)
    if failure_count:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    elif anomaly_count:
        disposition = MaintenanceProcessingDisposition.ANOMALIES_FOUND
    else:
        disposition = MaintenanceProcessingDisposition.NOOP

    report = MaintenanceReport(
        schema_version=1,
        report_id=uuid4().hex,
        operation=MaintenanceOperation.ORPHANED_UPLOAD_DETECTION,
        environment=settings.app_env.value,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        disposition=disposition,
        parameters={"minimumAgeHours": settings.orphaned_upload_min_age_hours},
        summary={"anomalyCount": anomaly_count, "failureCount": failure_count},
        details={"objects": anomalies},
        errors=tuple(errors),
    )
    try:
        save_maintenance_report_if_required(storage, report)
    except Exception:
        disposition = MaintenanceProcessingDisposition.RETRYABLE_FAILURE
        failure_count += 1

    return MaintenanceProcessingResult(
        operation=MaintenanceOperation.ORPHANED_UPLOAD_DETECTION,
        disposition=disposition,
        scanned_count=len(listed_objects),
        failure_count=failure_count,
        anomaly_count=anomaly_count,
    )
