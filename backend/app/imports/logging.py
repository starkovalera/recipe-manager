import logging
from datetime import datetime, timezone
from typing import Any

from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.models import ImportJob

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


JobLogPayload = ImportJob | dict[str, Any]


def _job_payload(job: JobLogPayload) -> dict[str, Any]:
    if isinstance(job, ImportJob):
        return job.to_dict()
    return job


def log_import_started(job: JobLogPayload, **payload) -> None:
    logger.info("Import job processing started.", job=_job_payload(job), **payload)


def log_import_failed(job: JobLogPayload, **payload) -> None:
    logger.info("Import job failed.", job=_job_payload(job), **payload)


def log_extraction_finished(job: JobLogPayload, extraction_started_at: datetime | None = None, **payload) -> None:
    payload = payload or {}
    if extraction_started_at:
        payload["duration_ms"] = int((datetime.now(timezone.utc) - extraction_started_at).total_seconds() * 1000)
    logger.info("Import extraction finished.", job=_job_payload(job), **payload)


def log_recipe_created(job: JobLogPayload, **payload) -> None:
    logger.info("Import recipe created.", job=_job_payload(job), **payload)
