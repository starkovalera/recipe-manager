from app.imports.events import build_job_event
from app.models import ImportEventType, ImportJob, ImportJobErrorCode


def test_build_job_event_appends_event_with_payload() -> None:
    job = ImportJob(owner_id="owner-1", client_id="client-1", client_import_id="import-1", dedupe_key="dedupe-1")

    event = build_job_event(job, ImportEventType.IMPORT_STARTED, status="running")

    assert event in job.events
    assert event.event_type == ImportEventType.IMPORT_STARTED
    assert event.payload == {"status": "running"}


def test_build_job_event_adds_exception_message_to_payload() -> None:
    job = ImportJob(owner_id="owner-1", client_id="client-1", client_import_id="import-1", dedupe_key="dedupe-1")

    event = build_job_event(job, ImportEventType.IMPORT_FAILED, error=ValueError("bad import"))

    assert event.payload == {"error": "bad import"}


def test_build_job_event_adds_job_error_fields_to_payload() -> None:
    job = ImportJob(
        owner_id="owner-1",
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="dedupe-1",
        error_code=ImportJobErrorCode.IMPORT_PROCESSING_FAILED,
        error_message="SECONDARY_RESOURCE_UPLOADING_FAILED",
    )

    event = build_job_event(job, ImportEventType.IMPORT_FAILED, resource_type="image")

    assert event.payload == {
        "resource_type": "image",
        "error_code": ImportJobErrorCode.IMPORT_PROCESSING_FAILED,
        "error_message": "SECONDARY_RESOURCE_UPLOADING_FAILED",
    }
