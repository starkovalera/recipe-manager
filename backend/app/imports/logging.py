import logging
from datetime import datetime, timezone

from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.models import ImportJob

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


def log_import_started(job: ImportJob, **payload) -> None:
    logger.info("Import job processing started.", job=job.to_dict(), **payload)


def log_import_failed(job: ImportJob, **payload) -> None:
    logger.info("Import job failed.", job=job.to_dict(), **payload)


def log_extraction_finished(job: ImportJob, extraction_started_at: datetime | None = None, **payload) -> None:
    payload = payload or {}
    if extraction_started_at:
        payload["duration_ms"] = int((datetime.now(timezone.utc) - extraction_started_at).total_seconds() * 1000)
    logger.info("Import extraction finished.", job=job.to_dict(), **payload)


def log_recipe_created(job: ImportJob, **payload) -> None:
    logger.info("Import recipe created.", job=job.to_dict(), **payload)
