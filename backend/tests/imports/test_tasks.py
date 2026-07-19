from app.imports import tasks
from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult


def test_run_import_job_returns_domain_result(monkeypatch) -> None:
    expected = ImportProcessingResult(
        import_job_id="job-1",
        disposition=ImportProcessingDisposition.RETRYABLE_FAILURE,
        detailed_error_code="EXTRACTOR_UNAVAILABLE",
    )
    monkeypatch.setattr(tasks, "process_import_job", lambda _job_id: expected)

    assert tasks.run_import_job("job-1") is expected


def test_import_recipe_task_delegates_to_domain_handler(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(tasks, "run_import_job", lambda import_job_id: calls.append(import_job_id))

    tasks.import_recipe_task.fn("job-1")

    assert calls == ["job-1"]


def test_import_recipe_task_disables_dramatiq_retries_by_default():
    assert tasks.import_recipe_task.options["max_retries"] == 0
