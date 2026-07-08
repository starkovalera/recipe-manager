from app.models import ImportEventType, ImportJob, JobEvent


def build_job_event(job: ImportJob, event_type: ImportEventType, **payload) -> JobEvent:
    event = JobEvent(event_type=event_type, payload=payload)
    job.events.append(event)
    return event
