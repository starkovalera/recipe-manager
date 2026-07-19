import dramatiq

from app.core.config import get_settings
from app.core.dramatiq import broker as _broker  # noqa: F401
from app.imports.jobs import process_import_job
from app.imports.outcomes import ImportProcessingResult


def run_import_job(import_job_id: str) -> ImportProcessingResult:
    return process_import_job(import_job_id)


@dramatiq.actor(max_retries=get_settings().import_task_max_retries)
def import_recipe_task(import_job_id: str) -> None:
    run_import_job(import_job_id)
