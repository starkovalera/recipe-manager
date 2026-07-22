from pathlib import Path

from app.maintenance.constants import MaintenanceOperation
from app.maintenance.dispatcher import MAINTENANCE_OPERATION_HANDLERS

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
MAINTENANCE_ROOT = APP_ROOT / "maintenance"


def _maintenance_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MAINTENANCE_ROOT.glob("*.py"))


def test_maintenance_does_not_execute_account_deletion_or_embedding_provider() -> None:
    source = _maintenance_source()

    assert "process_account_deletion" not in source
    assert "get_embedding_provider" not in source


def test_deferred_storage_operations_have_no_executable_handlers() -> None:
    deferred = {
        "failed_import_artifact_cleanup",
        "orphaned_upload_cleanup",
        "temporary_resource_cleanup",
    }

    assert deferred.isdisjoint(operation.value for operation in MaintenanceOperation)
    assert set(MAINTENANCE_OPERATION_HANDLERS) == set(MaintenanceOperation)


def test_maintenance_does_not_publish_directly_through_dramatiq_actors() -> None:
    assert ".send(" not in _maintenance_source()
