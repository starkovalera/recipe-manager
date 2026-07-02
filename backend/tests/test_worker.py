from app import worker


def test_worker_entrypoint_discovers_import_tasks():
    assert worker.import_tasks.import_recipe_task.actor_name == "import_recipe_task"
