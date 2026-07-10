import dramatiq

from app.core.dramatiq import broker as _broker  # noqa: F401
from app.imports.jobs import process_import_job


def run_import_job(import_job_id: str) -> None:
    process_import_job(import_job_id)


@dramatiq.actor
def import_recipe_task(import_job_id: str) -> None:
    run_import_job(import_job_id)
