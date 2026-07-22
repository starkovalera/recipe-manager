import pytest

from app.maintenance import dispatcher
from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance.types import MaintenanceProcessingResult


def test_dispatcher_registry_covers_exactly_all_operations() -> None:
    assert set(dispatcher.MAINTENANCE_OPERATION_HANDLERS) == set(MaintenanceOperation)


def test_dispatcher_routes_operation_to_registered_handler(monkeypatch) -> None:
    expected = MaintenanceProcessingResult(
        MaintenanceOperation.INTEGRITY_CHECK,
        MaintenanceProcessingDisposition.NOOP,
    )
    monkeypatch.setitem(dispatcher.MAINTENANCE_OPERATION_HANDLERS, MaintenanceOperation.INTEGRITY_CHECK, lambda: expected)

    assert dispatcher.run_maintenance_operation(MaintenanceOperation.INTEGRITY_CHECK) is expected


def test_dispatcher_rejects_handler_result_for_another_operation(monkeypatch) -> None:
    monkeypatch.setitem(
        dispatcher.MAINTENANCE_OPERATION_HANDLERS,
        MaintenanceOperation.INTEGRITY_CHECK,
        lambda: MaintenanceProcessingResult(
            MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION,
            MaintenanceProcessingDisposition.NOOP,
        ),
    )

    with pytest.raises(RuntimeError, match="unexpected operation"):
        dispatcher.run_maintenance_operation(MaintenanceOperation.INTEGRITY_CHECK)
