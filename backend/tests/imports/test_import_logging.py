from app.imports import logging as import_logging
from app.imports.logging import log_import_failed, log_import_started, log_recipe_created


class FakeLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def info(self, message: str, **payload) -> None:
        self.calls.append((message, payload))


def test_import_logging_accepts_job_snapshot(monkeypatch) -> None:
    logger = FakeLogger()
    monkeypatch.setattr(import_logging, "logger", logger)
    job_snapshot = {"id": "job-1", "status": "succeeded", "updated_at": "2026-07-08T10:00:00"}

    log_import_started(job_snapshot)
    log_recipe_created(job_snapshot, recipe_id="recipe-1")
    log_import_failed(job_snapshot, error={"code": "UNEXPECTED_ERROR"})

    assert logger.calls == [
        ("Import job processing started.", {"job": job_snapshot}),
        ("Import recipe created.", {"job": job_snapshot, "recipe_id": "recipe-1"}),
        ("Import job failed.", {"job": job_snapshot, "error": {"code": "UNEXPECTED_ERROR"}}),
    ]
