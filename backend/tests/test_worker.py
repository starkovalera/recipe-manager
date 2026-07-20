from app import worker
from app.embeddings import tasks as embedding_tasks
from app.embeddings.outcomes import EmbeddingProcessingDisposition, EmbeddingProcessingResult
from app.users import tasks as user_tasks


def test_worker_entrypoint_discovers_import_tasks():
    assert worker.import_tasks.import_recipe_task.actor_name == "import_recipe_task"
    assert worker.embedding_tasks.embed_recipe_task.actor_name == "embed_recipe_task"
    assert worker.user_tasks.delete_account_task.actor_name == "delete_account_task"


def test_embedding_actor_calls_processing_orchestrator(monkeypatch):
    processed: list[str] = []

    def process(recipe_id: str) -> EmbeddingProcessingResult:
        processed.append(recipe_id)
        return EmbeddingProcessingResult(
            recipe_id=recipe_id,
            disposition=EmbeddingProcessingDisposition.SUCCEEDED,
        )

    monkeypatch.setattr(embedding_tasks, "process_recipe_embedding", process)

    embedding_tasks.embed_recipe_task.fn("recipe-1")

    assert processed == ["recipe-1"]


def test_account_deletion_actor_calls_processing_orchestrator(monkeypatch):
    processed: list[str] = []
    monkeypatch.setattr(user_tasks, "process_account_deletion", processed.append)

    user_tasks.delete_account_task.fn("user-1")

    assert processed == ["user-1"]
    assert user_tasks.delete_account_task.options["max_retries"] == 3
