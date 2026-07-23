import json

import pytest
from pydantic import ValidationError

from app.maintenance.constants import MaintenanceOperation
from app.maintenance.types import MaintenanceProcessingDisposition, MaintenanceProcessingResult
from app.queueing.messages import MaintenanceQueueMessage


def test_maintenance_operations_are_exactly_the_active_set() -> None:
    assert {operation.value for operation in MaintenanceOperation} == {
        "pending_outbox_reconciliation",
        "stale_import_reconciliation",
        "failed_import_artifact_cleanup",
        "orphaned_upload_detection",
        "stale_embedding_reconciliation",
        "stale_recipe_deletion_reconciliation",
        "expired_invitation_cleanup",
        "stale_account_deletion_reconciliation",
        "integrity_check",
    }


def test_maintenance_queue_message_is_operation_only() -> None:
    message = MaintenanceQueueMessage(operation=MaintenanceOperation.INTEGRITY_CHECK)

    assert json.loads(message.model_dump_json(by_alias=True)) == {"operation": "integrity_check"}


def test_maintenance_queue_message_rejects_unknown_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MaintenanceQueueMessage.model_validate({"operation": "unknown"})
    with pytest.raises(ValidationError):
        MaintenanceQueueMessage.model_validate({"operation": "integrity_check", "entityId": "1"})


def test_maintenance_processing_result_has_zero_counters_by_default() -> None:
    result = MaintenanceProcessingResult(
        operation=MaintenanceOperation.INTEGRITY_CHECK,
        disposition=MaintenanceProcessingDisposition.NOOP,
    )

    assert result.scanned_count == 0
    assert result.changed_count == 0
    assert result.scheduled_count == 0
    assert result.failure_count == 0
    assert result.anomaly_count == 0
