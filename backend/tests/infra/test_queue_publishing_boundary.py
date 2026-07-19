from pathlib import Path

from app.queueing.types import QueuePublisher

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

TRANSPORT_SYMBOL_ALLOWED_MODULES = {
    "get_queue_publisher": {
        "queueing/outbox.py",
        "queueing/provider.py",
    },
    "DramatiqQueuePublisher": {
        "queueing/dramatiq.py",
        "queueing/provider.py",
    },
    "SqsQueuePublisher": {
        "queueing/provider.py",
        "queueing/sqs.py",
    },
    "import_recipe_task": {
        "imports/tasks.py",
        "queueing/dramatiq.py",
        "worker.py",
    },
    "embed_recipe_task": {
        "embeddings/tasks.py",
        "queueing/dramatiq.py",
        "worker.py",
    },
    "delete_account_task": {
        "queueing/dramatiq.py",
        "users/tasks.py",
        "worker.py",
    },
}


def test_transport_references_stay_inside_queue_infrastructure():
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        relative_path = path.relative_to(APP_ROOT).as_posix()
        content = path.read_text(encoding="utf-8")
        for symbol, allowed_modules in TRANSPORT_SYMBOL_ALLOWED_MODULES.items():
            if symbol in content and relative_path not in allowed_modules:
                violations.append(f"{relative_path}: {symbol}")

    assert violations == [], "Queue transport references found outside approved infrastructure:\n" + "\n".join(violations)


def test_actor_send_calls_stay_in_dramatiq_adapter():
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        relative_path = path.relative_to(APP_ROOT).as_posix()
        if relative_path == "queueing/dramatiq.py":
            continue
        content = path.read_text(encoding="utf-8")
        for actor_name in ("import_recipe_task", "embed_recipe_task", "delete_account_task"):
            if f"{actor_name}.send(" in content:
                violations.append(f"{relative_path}: {actor_name}.send")

    assert violations == [], "Actor send calls found outside the Dramatiq queue adapter:\n" + "\n".join(violations)


def test_sqs_send_message_calls_stay_in_sqs_adapter():
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        relative_path = path.relative_to(APP_ROOT).as_posix()
        if relative_path == "queueing/sqs.py":
            continue
        if ".send_message(" in path.read_text(encoding="utf-8"):
            violations.append(relative_path)

    assert violations == [], "SQS send_message calls found outside the SQS queue adapter:\n" + "\n".join(violations)


def test_boto3_imports_stay_in_sqs_adapter():
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        relative_path = path.relative_to(APP_ROOT).as_posix()
        if relative_path == "queueing/sqs.py":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(line.strip() == "import boto3" or line.strip().startswith("from boto3") for line in lines):
            violations.append(relative_path)

    assert violations == [], "boto3 imports found outside the SQS queue adapter:\n" + "\n".join(violations)


def test_queue_publisher_protocol_keeps_supported_operations():
    assert {
        "publish_import_job",
        "publish_recipe_embedding",
        "publish_account_deletion",
    } <= set(QueuePublisher.__dict__)
