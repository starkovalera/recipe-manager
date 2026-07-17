from pathlib import Path

ACTOR_NAMES = {
    "import_recipe_task",
    "embed_recipe_task",
    "delete_account_task",
}

ALLOWED_ACTOR_MODULES = {
    "embeddings/tasks.py",
    "imports/tasks.py",
    "queueing/dramatiq.py",
    "users/tasks.py",
    "worker.py",
}


def test_background_actor_references_stay_behind_queue_boundary():
    app_root = Path(__file__).resolve().parents[2] / "app"
    violations: list[str] = []

    for path in app_root.rglob("*.py"):
        relative_path = path.relative_to(app_root).as_posix()
        if relative_path in ALLOWED_ACTOR_MODULES:
            continue
        content = path.read_text(encoding="utf-8")
        referenced_actors = sorted(actor_name for actor_name in ACTOR_NAMES if actor_name in content)
        if referenced_actors:
            violations.append(f"{relative_path}: {', '.join(referenced_actors)}")

    assert violations == [], "Direct background actor references found outside queue infrastructure:\n" + "\n".join(violations)
