import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.reports import MaintenanceReport, save_maintenance_report_if_required
from app.storage.constants import StorageLocation, StorageSystemPurpose
from app.storage.types import StorageSystemContext, StoredFile


class RecordingStorage:
    def __init__(self) -> None:
        self.save_calls: list[dict] = []

    def save(self, location, content, original_name, mime_type, *, context):
        self.save_calls.append(
            {
                "location": location,
                "content": content,
                "original_name": original_name,
                "mime_type": mime_type,
                "context": context,
            }
        )
        return StoredFile("report.json", original_name, mime_type, len(content))


def build_report(*, anomaly_count: int = 0, failure_count: int = 0) -> MaintenanceReport:
    started_at = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)
    return MaintenanceReport(
        schema_version=1,
        report_id="report-1",
        operation=MaintenanceOperation.INTEGRITY_CHECK,
        environment="TEST",
        started_at=started_at,
        finished_at=datetime(2026, 7, 23, 10, 1, tzinfo=timezone.utc),
        disposition=MaintenanceProcessingDisposition.ANOMALIES_FOUND,
        parameters={"batchSize": 100},
        summary={"anomalyCount": anomaly_count, "failureCount": failure_count},
        details={"records": [{"importJobId": "job-1", "storageKey": "imports/source/owner/job/key.jpg"}]},
        errors=(),
    )


def test_clean_report_is_logged_without_storage_write(monkeypatch) -> None:
    storage = RecordingStorage()
    log_calls: list[tuple[str, dict]] = []

    class RecordingLogger:
        def info(self, message: str, **meta) -> None:
            log_calls.append((message, meta))

    monkeypatch.setattr("app.maintenance.reports.logger", RecordingLogger())

    assert save_maintenance_report_if_required(storage, build_report()) is None

    assert storage.save_calls == []
    assert log_calls == [
        (
            "Maintenance operation completed without reportable findings.",
            {"operation": "integrity_check", "report_id": "report-1"},
        )
    ]


@pytest.mark.parametrize(("anomaly_count", "failure_count"), [(1, 0), (0, 1)])
def test_reportable_result_is_saved_as_utf8_json(anomaly_count: int, failure_count: int) -> None:
    storage = RecordingStorage()
    report = build_report(anomaly_count=anomaly_count, failure_count=failure_count)

    saved = save_maintenance_report_if_required(storage, report)

    assert saved is not None
    assert len(storage.save_calls) == 1
    call = storage.save_calls[0]
    assert call["location"] is StorageLocation.SYSTEM_ARTIFACTS
    assert call["original_name"] == "integrity-check-report-1.json"
    assert call["mime_type"] == "application/json"
    assert call["context"] == StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type="integrity-check",
        report_id="report-1",
        created_at=report.started_at,
    )
    payload = json.loads(call["content"].decode("utf-8"))
    assert payload["operation"] == "integrity_check"
    assert payload["disposition"] == "ANOMALIES_FOUND"
    assert payload["details"]["records"][0] == {
        "importJobId": "job-1",
        "storageKey": "imports/source/owner/job/key.jpg",
    }


@pytest.mark.parametrize(
    "details",
    [
        {"payload": b"secret"},
        {"email": "person@example.test"},
        {"sourceUrl": "https://example.test/private"},
        {"authData": {"subject": "provider-user"}},
        {"aiPayload": {"prompt": "private source text"}},
        {"record": object()},
    ],
)
def test_report_rejects_sensitive_or_non_json_details(details: dict[str, object]) -> None:
    report = build_report(anomaly_count=1)

    with pytest.raises(ValidationError):
        MaintenanceReport(**{**report.model_dump(), "details": details})
