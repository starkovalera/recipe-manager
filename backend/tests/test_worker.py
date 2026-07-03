from app import worker


def test_worker_entrypoint_discovers_import_tasks():
    assert worker.import_tasks.import_recipe_task.actor_name == "import_recipe_task"
    assert worker.embedding_tasks.embed_recipe_task.actor_name == "embed_recipe_task"
