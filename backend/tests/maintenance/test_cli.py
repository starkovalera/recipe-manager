from app.maintenance import cli
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult


def test_cli_maps_processing_dispositions_to_exit_codes(monkeypatch) -> None:
    for disposition, expected in [
        (MaintenanceProcessingDisposition.COMPLETED, 0),
        (MaintenanceProcessingDisposition.NOOP, 0),
        (MaintenanceProcessingDisposition.RETRYABLE_FAILURE, 1),
        (MaintenanceProcessingDisposition.ANOMALIES_FOUND, 2),
    ]:
        monkeypatch.setattr(
            cli,
            "run_maintenance_operation",
            lambda operation, disposition=disposition: MaintenanceProcessingResult(operation, disposition),
        )
        assert cli.main([MaintenanceOperation.INTEGRITY_CHECK.value]) == expected
