import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, JsonValue, field_validator

from app.core.logging import bind_logger
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.schemas.base import to_camel
from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StorageSystemPurpose
from app.storage.types import StorageSystemContext, StoredFile

logger = bind_logger(logging.getLogger(__name__), component="recipes.maintenance")

_FORBIDDEN_REPORT_KEYS = frozenset(
    {
        "aipayload",
        "authdata",
        "credentials",
        "email",
        "sourcetext",
        "sourceurl",
    }
)


class MaintenanceReport(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        strict=True,
    )

    schema_version: int
    report_id: str
    operation: MaintenanceOperation
    environment: str
    started_at: datetime
    finished_at: datetime
    disposition: MaintenanceProcessingDisposition
    parameters: dict[str, JsonValue]
    summary: dict[str, int]
    details: dict[str, JsonValue]
    errors: tuple[dict[str, JsonValue], ...]

    @field_validator("parameters", "summary", "details", "errors")
    @classmethod
    def validate_report_fields(cls, value):
        _validate_report_keys(value)
        return value


def _validate_report_keys(value: object, *, key: str = "report") -> None:
    normalized_key = "".join(character for character in key.casefold() if character.isalnum())
    if normalized_key in _FORBIDDEN_REPORT_KEYS:
        raise ValueError(f"Maintenance report field {key!r} is not allowed.")
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            if not isinstance(nested_key, str):
                raise ValueError("Maintenance report object keys must be strings.")
            _validate_report_keys(nested_value, key=nested_key)
        return
    if isinstance(value, (list, tuple)):
        for nested_value in value:
            _validate_report_keys(nested_value, key=key)
        return


def save_maintenance_report_if_required(
    storage: StorageService,
    report: MaintenanceReport,
) -> StoredFile | None:
    anomaly_count = report.summary.get("anomalyCount", 0)
    failure_count = report.summary.get("failureCount", 0)
    if anomaly_count == 0 and failure_count == 0:
        logger.info(
            "Maintenance operation completed without reportable findings.",
            operation=report.operation.value,
            report_id=report.report_id,
        )
        return None

    report_type = report.operation.value.replace("_", "-")
    content = report.model_dump_json(by_alias=True).encode("utf-8")
    return storage.save(
        StorageLocation.SYSTEM_ARTIFACTS,
        content,
        f"{report_type}-{report.report_id}.json",
        "application/json",
        context=StorageSystemContext(
            purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
            report_type=report_type,
            report_id=report.report_id,
            created_at=report.started_at,
        ),
    )
