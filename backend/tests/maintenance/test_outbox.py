from types import SimpleNamespace

from app.maintenance.constants import MaintenanceOperation, MaintenanceProcessingDisposition
from app.maintenance import outbox as maintenance_outbox


def test_reconcile_pending_outbox_reports_exact_counters(monkeypatch) -> None:
    monkeypatch.setattr(maintenance_outbox, "get_settings", lambda: SimpleNamespace(maintenance_batch_size=3))
    monkeypatch.setattr(maintenance_outbox, "db_session", _session_scope)
    monkeypatch.setattr(
        maintenance_outbox,
        "list_pending_outbox_message_ids",
        lambda _session, *, limit: ["message-1", "message-2", "message-3"][:limit],
    )
    monkeypatch.setattr(maintenance_outbox, "dispatch_outbox_message", lambda message_id: message_id != "message-2")

    result = maintenance_outbox.reconcile_pending_outbox()

    assert result.operation is MaintenanceOperation.PENDING_OUTBOX_RECONCILIATION
    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.scanned_count == 3
    assert result.changed_count == 2
    assert result.failure_count == 1


def test_reconcile_pending_outbox_is_noop_without_rows(monkeypatch) -> None:
    monkeypatch.setattr(maintenance_outbox, "get_settings", lambda: SimpleNamespace(maintenance_batch_size=10))
    monkeypatch.setattr(maintenance_outbox, "db_session", _session_scope)
    monkeypatch.setattr(maintenance_outbox, "list_pending_outbox_message_ids", lambda _session, *, limit: [])

    result = maintenance_outbox.reconcile_pending_outbox()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP


class _session_scope:
    def __enter__(self):
        return object()

    def __exit__(self, *_args):
        return False
