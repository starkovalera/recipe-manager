from app.imports.events import build_job_event
from app.models import ImportEventType, ImportJob


def test_build_job_event_appends_event_with_payload() -> None:
    job = ImportJob(owner_id="owner-1", client_id="client-1", client_import_id="import-1", dedupe_key="dedupe-1")

    event = build_job_event(job, ImportEventType.IMPORT_STARTED, status="running")

    assert event in job.events
    assert event.event_type == ImportEventType.IMPORT_STARTED
    assert event.payload == {"status": "running"}


def test_build_job_event_preserves_error_payload() -> None:
    job = ImportJob(owner_id="owner-1", client_id="client-1", client_import_id="import-1", dedupe_key="dedupe-1")
    error_payload = {"code": "TEST_ERROR", "message": "Bad import"}

    event = build_job_event(job, ImportEventType.IMPORT_FAILED, error=error_payload)

    assert event.payload == {"error": error_payload}


def test_build_job_event_does_not_infer_job_error_fields() -> None:
    job = ImportJob(owner_id="owner-1", client_id="client-1", client_import_id="import-1", dedupe_key="dedupe-1")

    event = build_job_event(job, ImportEventType.IMPORT_FAILED, resource_type="image")

    assert event.payload == {"resource_type": "image"}
