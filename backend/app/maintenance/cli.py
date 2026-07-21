import argparse
from collections.abc import Sequence

from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.dispatcher import run_maintenance_operation

EXIT_CODES = {
    MaintenanceProcessingDisposition.COMPLETED: 0,
    MaintenanceProcessingDisposition.NOOP: 0,
    MaintenanceProcessingDisposition.RETRYABLE_FAILURE: 1,
    MaintenanceProcessingDisposition.ANOMALIES_FOUND: 2,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Recipe Manager maintenance operation.")
    parser.add_argument("operation", choices=[operation.value for operation in MaintenanceOperation])
    arguments = parser.parse_args(argv)
    result = run_maintenance_operation(MaintenanceOperation(arguments.operation))
    return EXIT_CODES[result.disposition]


if __name__ == "__main__":
    raise SystemExit(main())
