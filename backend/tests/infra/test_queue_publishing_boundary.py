import ast
from pathlib import Path

from app.queueing.types import QueuePublisher

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
IMPORT_LAMBDA_PATH = APP_ROOT / "lambdas" / "imports.py"
EMBEDDING_LAMBDA_PATH = APP_ROOT / "lambdas" / "embeddings.py"
ACCOUNT_DELETION_LAMBDA_PATH = APP_ROOT / "lambdas" / "account_deletion.py"
ACCOUNT_DELETION_PROCESSING_PATH = APP_ROOT / "users" / "deletion.py"

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


def test_boto3_imports_stay_in_aws_adapters():
    violations: list[str] = []
    allowed_modules = {"queueing/sqs.py", "storage/s3.py"}

    for path in APP_ROOT.rglob("*.py"):
        relative_path = path.relative_to(APP_ROOT).as_posix()
        if relative_path in allowed_modules:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(line.strip() == "import boto3" or line.strip().startswith("from boto3") for line in lines):
            violations.append(relative_path)

    assert violations == [], "boto3 imports found outside AWS adapters:\n" + "\n".join(violations)


def test_queue_publisher_protocol_keeps_supported_operations():
    assert {
        "publish_import_job",
        "publish_recipe_embedding",
        "publish_account_deletion",
    } <= set(QueuePublisher.__dict__)


def test_import_lambda_handler_keeps_infrastructure_boundary() -> None:
    tree = ast.parse(IMPORT_LAMBDA_PATH.read_text(encoding="utf-8"), filename=str(IMPORT_LAMBDA_PATH))
    imported_symbols: set[tuple[str, str]] = set()
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_modules.add(module)
            imported_symbols.update((module, alias.name) for alias in node.names)

    required_symbols = {
        ("app.imports.jobs", "process_import_job"),
        ("app.imports.outcomes", "ImportProcessingDisposition"),
        ("app.queueing.messages", "ImportJobQueueMessage"),
    }
    assert required_symbols <= imported_symbols

    prohibited_prefixes = (
        "boto3",
        "sqlalchemy",
        "sqlmodel",
        "app.db",
        "app.models",
        "app.imports.error_codes",
        "app.imports.error_policy",
        "app.imports.storage_cleanup",
        "app.storage",
    )
    prohibited_modules = {
        module for module in imported_modules if any(module == prefix or module.startswith(f"{prefix}.") for prefix in prohibited_prefixes)
    }
    prohibited_symbols = {
        symbol
        for _, symbol in imported_symbols
        if symbol == "SqsQueuePublisher" or (symbol.endswith("Error") and symbol != "InvalidSqsRecordError")
    }

    assert prohibited_modules == set()
    assert prohibited_symbols == set()


def test_embedding_lambda_handler_keeps_infrastructure_boundary() -> None:
    tree = ast.parse(EMBEDDING_LAMBDA_PATH.read_text(encoding="utf-8"), filename=str(EMBEDDING_LAMBDA_PATH))
    imported_symbols: set[tuple[str, str]] = set()
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_modules.add(module)
            imported_symbols.update((module, alias.name) for alias in node.names)

    required_symbols = {
        ("app.embeddings.constants", "EmbeddingProcessingDisposition"),
        ("app.embeddings.processing", "process_recipe_embedding"),
        ("app.queueing.messages", "RecipeEmbeddingQueueMessage"),
    }
    assert required_symbols <= imported_symbols

    prohibited_prefixes = (
        "boto3",
        "sqlalchemy",
        "sqlmodel",
        "app.db",
        "app.models",
        "app.embeddings.factory",
        "app.embeddings.provider",
        "app.embeddings.runtime",
        "app.queueing.outbox",
        "app.queueing.provider",
        "app.queueing.sqs",
    )
    prohibited_modules = {
        module for module in imported_modules if any(module == prefix or module.startswith(f"{prefix}.") for prefix in prohibited_prefixes)
    }

    assert prohibited_modules == set()


def test_account_deletion_processing_uses_storage_boundary() -> None:
    content = ACCOUNT_DELETION_PROCESSING_PATH.read_text(encoding="utf-8")

    assert "LocalStorageService" not in content
    assert "app.storage.local" not in content


def test_account_deletion_lambda_handler_keeps_infrastructure_boundary() -> None:
    tree = ast.parse(
        ACCOUNT_DELETION_LAMBDA_PATH.read_text(encoding="utf-8"),
        filename=str(ACCOUNT_DELETION_LAMBDA_PATH),
    )
    imported_symbols: set[tuple[str, str]] = set()
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_modules.add(module)
            imported_symbols.update((module, alias.name) for alias in node.names)

    required_symbols = {
        ("app.queueing.messages", "AccountDeletionQueueMessage"),
        ("app.users.constants", "AccountDeletionProcessingDisposition"),
        ("app.users.deletion", "process_account_deletion"),
    }
    assert required_symbols <= imported_symbols

    prohibited_prefixes = (
        "boto3",
        "sqlalchemy",
        "sqlmodel",
        "app.auth",
        "app.db",
        "app.models",
        "app.queueing.outbox",
        "app.queueing.provider",
        "app.queueing.sqs",
        "app.storage",
    )
    prohibited_modules = {
        module for module in imported_modules if any(module == prefix or module.startswith(f"{prefix}.") for prefix in prohibited_prefixes)
    }

    assert prohibited_modules == set()
