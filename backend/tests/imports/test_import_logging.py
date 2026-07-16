from app.imports import logging as import_logging
from app.imports.logging import log_import_failed, log_import_started, log_recipe_created
from app.models import ImportJob, ImportJobStatus


class FakeLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def info(self, message: str, **payload) -> None:
        self.calls.append((message, payload))


def test_import_logging_accepts_import_job(monkeypatch) -> None:
    logger = FakeLogger()
    monkeypatch.setattr(import_logging, "logger", logger)
    job = ImportJob(
        id="job-1",
        owner_id="owner-1",
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="import-1",
        status=ImportJobStatus.SUCCEEDED,
    )
    job_payload = job.to_dict()

    log_import_started(job)
    log_recipe_created(job, recipe_id="recipe-1")
    log_import_failed(job, error={"code": "UNEXPECTED_ERROR"})

    assert logger.calls == [
        ("Import job processing started.", {"job": job_payload}),
        ("Import recipe created.", {"job": job_payload, "recipe_id": "recipe-1"}),
        ("Import job failed.", {"job": job_payload, "error": {"code": "UNEXPECTED_ERROR"}}),
    ]
