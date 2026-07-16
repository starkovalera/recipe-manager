from app.imports.events import build_job_event
from app.models import ImportEventType


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def test_build_job_event_adds_event_with_payload() -> None:
    session = FakeSession()

    event = build_job_event(session, import_job_id="job-1", event_type=ImportEventType.IMPORT_STARTED, status="running")

    assert session.added == [event]
    assert event.import_job_id == "job-1"
    assert event.event_type == ImportEventType.IMPORT_STARTED
    assert event.payload == {"status": "running"}


def test_build_job_event_preserves_error_payload() -> None:
    session = FakeSession()
    error_payload = {"code": "TEST_ERROR", "message": "Bad import"}

    event = build_job_event(session, import_job_id="job-1", event_type=ImportEventType.IMPORT_FAILED, error=error_payload)

    assert event.payload == {"error": error_payload}


def test_build_job_event_does_not_infer_job_error_fields() -> None:
    session = FakeSession()

    event = build_job_event(session, import_job_id="job-1", event_type=ImportEventType.IMPORT_FAILED, resource_type="image")

    assert event.payload == {"resource_type": "image"}
