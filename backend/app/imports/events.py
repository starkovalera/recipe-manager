from app.models import ImportEventType, ImportJob, JobEvent


def build_job_event(job: ImportJob, event_type: ImportEventType, error: Exception | None = None, **payload) -> JobEvent:
    payload = payload or {}
    if error:
        payload["error"] = str(error)
    if job.error_code is not None:
        payload["error_code"] = job.error_code
    if job.error_message is not None:
        payload["error_message"] = job.error_message
    event = JobEvent(event_type=event_type, payload=payload)
    job.events.append(event)
    return event
