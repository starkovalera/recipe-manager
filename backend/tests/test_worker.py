from app import worker
from app.embeddings import tasks as embedding_tasks


def test_worker_entrypoint_discovers_import_tasks():
    assert worker.import_tasks.import_recipe_task.actor_name == "import_recipe_task"
    assert worker.embedding_tasks.embed_recipe_task.actor_name == "embed_recipe_task"


def test_embedding_actor_calls_processing_orchestrator(monkeypatch):
    processed: list[str] = []
    monkeypatch.setattr(embedding_tasks, "process_recipe_embedding", processed.append)

    embedding_tasks.embed_recipe_task.fn("recipe-1")

    assert processed == ["recipe-1"]
