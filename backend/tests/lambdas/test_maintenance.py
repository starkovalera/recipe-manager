import json
from types import SimpleNamespace

import pytest

from app.lambdas import maintenance
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult


def _record(message_id: str, body: object) -> dict:
    return {"messageId": message_id, "body": body if isinstance(body, str) else json.dumps(body)}


def test_maintenance_lambda_returns_exact_partial_failures(monkeypatch) -> None:
    dispositions = {
        MaintenanceOperation.INTEGRITY_CHECK: MaintenanceProcessingDisposition.ANOMALIES_FOUND,
        MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION: MaintenanceProcessingDisposition.RETRYABLE_FAILURE,
    }
    monkeypatch.setattr(
        maintenance,
        "run_maintenance_operation",
        lambda operation: MaintenanceProcessingResult(operation, dispositions[operation]),
    )

    response = maintenance.handler(
        {
            "Records": [
                _record("ok", {"operation": "integrity_check"}),
                _record("retry", {"operation": "pending_outbox_reconciliation"}),
                _record("invalid", {"operation": "unknown"}),
            ]
        },
        SimpleNamespace(aws_request_id="request-1"),
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "retry"}, {"itemIdentifier": "invalid"}]}


def test_maintenance_lambda_accepts_empty_batch() -> None:
    assert maintenance.handler({}, object()) == {"batchItemFailures": []}


def test_maintenance_lambda_marks_dispatcher_exception_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        maintenance,
        "run_maintenance_operation",
        lambda _operation: (_ for _ in ()).throw(RuntimeError("secret detail")),
    )

    assert maintenance.handler(
        {"Records": [_record("one", {"operation": "integrity_check"})]},
        object(),
    ) == {"batchItemFailures": [{"itemIdentifier": "one"}]}


def test_maintenance_lambda_rejects_missing_message_id() -> None:
    with pytest.raises(ValueError):
        maintenance.handler({"Records": [{"body": '{"operation":"integrity_check"}'}]}, object())


@pytest.mark.parametrize("body", [None, 1, "not-json", '{"operation":"integrity_check","extra":1}'])
def test_maintenance_lambda_marks_invalid_body_failed(body) -> None:
    record = {"messageId": "one", "body": body}
    assert maintenance.handler({"Records": [record]}, object()) == {
        "batchItemFailures": [{"itemIdentifier": "one"}]
    }
