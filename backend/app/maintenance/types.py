from dataclasses import dataclass

from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition


@dataclass(frozen=True)
class MaintenanceProcessingResult:
    operation: MaintenanceOperation
    disposition: MaintenanceProcessingDisposition
    scanned_count: int = 0
    changed_count: int = 0
    scheduled_count: int = 0
    failure_count: int = 0
    anomaly_count: int = 0
