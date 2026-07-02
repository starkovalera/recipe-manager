from app.imports import tasks


def test_import_recipe_task_delegates_to_domain_handler(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(tasks, "run_import_job", lambda import_job_id: calls.append(import_job_id))

    tasks.import_recipe_task.fn("job-1")

    assert calls == ["job-1"]
