import json
from pathlib import Path

from app.lambdas import maintenance as maintenance_lambda
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOT = REPOSITORY_ROOT / "docker" / "production"
DOCKERFILE = PRODUCTION_ROOT / "Dockerfile"
FIXTURE_ROOT = PRODUCTION_ROOT / "fixtures" / "maintenance-lambda"


def test_maintenance_lambda_target_uses_shared_runtime_and_handler_command() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    target = dockerfile.split("FROM lambda-runtime AS maintenance-lambda-runtime", maxsplit=1)[1]

    assert "FROM lambda-runtime AS maintenance-lambda-runtime" in dockerfile
    assert 'CMD ["app.lambdas.maintenance.handler"]' in target
    assert 'com.recipe-manager.artifact="recipe-manager-maintenance"' in target
    assert 'test ! -e /usr/local/bin/ffmpeg' in target
    assert 'test ! -e /usr/local/bin/ffprobe' in target


def test_maintenance_lambda_fixtures_cover_each_disposition_and_malformed_record(monkeypatch) -> None:
    outcomes = {
        MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION: MaintenanceProcessingResult(
            MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION,
            MaintenanceProcessingDisposition.COMPLETED,
        ),
        MaintenanceOperation.STALE_IMPORT_RECONCILIATION: MaintenanceProcessingResult(
            MaintenanceOperation.STALE_IMPORT_RECONCILIATION,
            MaintenanceProcessingDisposition.RETRYABLE_FAILURE,
        ),
        MaintenanceOperation.INTEGRITY_CHECK: MaintenanceProcessingResult(
            MaintenanceOperation.INTEGRITY_CHECK,
            MaintenanceProcessingDisposition.ANOMALIES_FOUND,
        ),
    }
    monkeypatch.setattr(maintenance_lambda, "run_maintenance_operation", outcomes.__getitem__)

    valid = json.loads((FIXTURE_ROOT / "valid-operation.json").read_text(encoding="utf-8"))
    retryable = json.loads((FIXTURE_ROOT / "retryable-failure.json").read_text(encoding="utf-8"))
    anomaly = json.loads((FIXTURE_ROOT / "anomaly-result.json").read_text(encoding="utf-8"))
    malformed = json.loads((FIXTURE_ROOT / "malformed-record.json").read_text(encoding="utf-8"))

    assert maintenance_lambda.handler(valid, None) == {"batchItemFailures": []}
    assert maintenance_lambda.handler(retryable, None) == {
        "batchItemFailures": [{"itemIdentifier": "maintenance-fixture-retryable"}]
    }
    assert maintenance_lambda.handler(anomaly, None) == {"batchItemFailures": []}
    assert maintenance_lambda.handler(malformed, None) == {
        "batchItemFailures": [{"itemIdentifier": "maintenance-fixture-malformed"}]
    }
