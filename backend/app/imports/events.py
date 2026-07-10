from typing import Any

from sqlalchemy.orm import Session

from app.models import ImportEventType, JobEvent


def build_job_event(
    session: Session,
    *,
    import_job_id: str,
    event_type: ImportEventType,
    **payload: Any,
) -> JobEvent:
    event = JobEvent(import_job_id=import_job_id, event_type=event_type, payload=payload)
    session.add(event)
    return event
