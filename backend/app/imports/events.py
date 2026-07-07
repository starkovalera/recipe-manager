from typing import Any

from app.models import ImportEventType, ImportJob, JobEvent


def record_job_event(job: ImportJob, event_type: ImportEventType, payload: dict[str, Any] | None = None) -> JobEvent:
    event = JobEvent(event_type=event_type, payload=payload)
    job.events.append(event)
    return event
