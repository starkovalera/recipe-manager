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


def log_extraction_started(job: ImportJob, provider: str, **payload) -> None:
    logger.info("Extraction started.", job=job.to_dict(), provider=provider, **payload)


def log_extraction_finished(job: ImportJob, extraction_started_at: datetime | None = None, **payload) -> None:
    payload = payload or {}
    if extraction_started_at:
        payload["duration_ms"] = int((datetime.now(timezone.utc) - extraction_started_at).total_seconds() * 1000)
    logger.info("Import extraction finished.", job=job.to_dict(), **payload)


def log_recipe_tags_built(
    job: ImportJob,
    extracted_tags: list[str],
    matched_tags: list[str],
    ignored_tags: list[str],
    duplicated_tags: list[str],
    **payload,
) -> None:
    extracted_tags_count = len(extracted_tags)
    logger.info(
        f"Extraction tags processed. "
        f"[{len(matched_tags)}/{extracted_tags_count}] matched, "
        f"[{len(ignored_tags)}/{extracted_tags_count}] ignored, "
        f"[{len(duplicated_tags)}/{extracted_tags_count}] duplicated. ",
        job=job.to_dict(),
        extracted_tags=extracted_tags,
        matched_tags=matched_tags,
        ignored_tags=ignored_tags,
        duplicated_tags=duplicated_tags,
        **payload,
    )


def log_recipe_created(job: ImportJob, **payload) -> None:
    logger.info("Import recipe created.", job=job.to_dict(), **payload)
