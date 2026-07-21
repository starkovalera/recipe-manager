from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.maintenance import accounts as maintenance_accounts
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import ImportJob, ImportJobStatus, QueueOutboxMessage, User, UserStatus
from app.queueing.constants import QueueMessageType


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _add_pending(factory, *, active_import: bool = False, pending_intent: bool = False) -> None:
    with factory() as session:
        user = User(
            id="user-1",
            email="user@example.test",
            status=UserStatus.DELETION_PENDING,
            deletion_requested_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.add(user)
        if active_import:
            session.add(ImportJob(owner=user, client_id="job", status=ImportJobStatus.RUNNING))
        if pending_intent:
            session.add(QueueOutboxMessage(message_type=QueueMessageType.ACCOUNT_DELETION, entity_id=user.id))
        session.commit()


def _configure(monkeypatch, factory) -> list[str]:
    dispatched: list[str] = []
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        maintenance_accounts,
        "get_settings",
        lambda: SimpleNamespace(maintenance_batch_size=100, stale_account_deletion_minutes=60),
    )
    monkeypatch.setattr(maintenance_accounts, "dispatch_outbox_message", lambda value: dispatched.append(value) or True)
    return dispatched


def test_stale_pending_account_gets_durable_intent(monkeypatch) -> None:
    factory = _factory()
    _add_pending(factory)
    dispatched = _configure(monkeypatch, factory)

    result = maintenance_accounts.reconcile_stale_account_deletions()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert result.scheduled_count == 1
    assert len(dispatched) == 1
    with factory() as session:
        assert session.query(QueueOutboxMessage).filter_by(entity_id="user-1").count() == 1


def test_active_import_or_pending_intent_prevents_duplicate_schedule(monkeypatch) -> None:
    for active_import, pending_intent in [(True, False), (False, True)]:
        factory = _factory()
        _add_pending(factory, active_import=active_import, pending_intent=pending_intent)
        dispatched = _configure(monkeypatch, factory)

        result = maintenance_accounts.reconcile_stale_account_deletions()

        assert result.disposition is MaintenanceProcessingDisposition.NOOP
        assert dispatched == []


def test_account_maintenance_does_not_execute_deletion(monkeypatch) -> None:
    factory = _factory()
    _add_pending(factory)
    _configure(monkeypatch, factory)
    monkeypatch.setattr(
        "app.users.deletion.process_account_deletion",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    maintenance_accounts.reconcile_stale_account_deletions()

    with factory() as session:
        assert session.get(User, "user-1") is not None
