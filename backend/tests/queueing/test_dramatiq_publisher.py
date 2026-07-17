from app.embeddings.tasks import embed_recipe_task
from app.imports.tasks import import_recipe_task
from app.queueing.dramatiq import DramatiqQueuePublisher
from app.users.tasks import delete_account_task


def test_publish_import_job_sends_only_import_job_id(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(import_recipe_task, "send", sent.append)

    DramatiqQueuePublisher().publish_import_job("job-1")

    assert sent == ["job-1"]


def test_publish_recipe_embedding_sends_only_recipe_id(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(embed_recipe_task, "send", sent.append)

    DramatiqQueuePublisher().publish_recipe_embedding("recipe-1")

    assert sent == ["recipe-1"]


def test_publish_account_deletion_sends_only_user_id(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(delete_account_task, "send", sent.append)

    DramatiqQueuePublisher().publish_account_deletion("user-1")

    assert sent == ["user-1"]
