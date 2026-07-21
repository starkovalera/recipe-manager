from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.imports.error_codes import ImportProcessingErrorCode
from app.maintenance import imports as maintenance_imports
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import ImportJob, ImportJobErrorCode, ImportJobStatus, JobEvent, Notification, QueueOutboxMessage, User
from app.queueing.constants import QueueMessageType


def _session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _add_job(factory, *, job_id: str, status: ImportJobStatus, attempt_count: int, stale: bool = True) -> None:
    now = datetime.now(timezone.utc)
    timestamp = now - timedelta(hours=2) if stale else now
    with factory() as session:
        user = session.get(User, "user-1")
        if user is None:
            user = User(id="user-1", email="user@example.test")
            session.add(user)
        session.add(
            ImportJob(
                id=job_id,
                owner=user,
                client_id=job_id,
                status=status,
                attempt_count=attempt_count,
                started_at=timestamp if status is ImportJobStatus.RUNNING else None,
                updated_at=timestamp,
            )
        )
        session.commit()


def _configure(monkeypatch, factory) -> list[str]:
    dispatched: list[str] = []
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        maintenance_imports,
        "get_settings",
        lambda: SimpleNamespace(maintenance_batch_size=100, stale_import_minutes=30, max_import_attempts=3),
    )
    monkeypatch.setattr(
        maintenance_imports,
        "dispatch_outbox_message",
        lambda message_id: dispatched.append(message_id) or True,
    )
    return dispatched


def test_stale_running_import_is_requeued_without_resetting_attempt_count(monkeypatch) -> None:
    factory = _session_factory()
    _add_job(factory, job_id="job-1", status=ImportJobStatus.RUNNING, attempt_count=1)
    dispatched = _configure(monkeypatch, factory)

    result = maintenance_imports.reconcile_stale_imports()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert result.changed_count == 1
    assert result.scheduled_count == 1
    assert len(dispatched) == 1
    with factory() as session:
        job = session.get(ImportJob, "job-1")
        assert job.status is ImportJobStatus.QUEUED
        assert job.attempt_count == 1
        assert job.started_at is None
        assert session.query(QueueOutboxMessage).filter_by(entity_id="job-1").one().message_type is QueueMessageType.IMPORT_JOB
        event = session.query(JobEvent).filter_by(import_job_id="job-1").one()
        assert event.payload["error"]["code"] == ImportProcessingErrorCode.STALE_IMPORT_RECOVERY


def test_stale_import_with_pending_intent_is_not_scheduled_twice(monkeypatch) -> None:
    factory = _session_factory()
    _add_job(factory, job_id="job-1", status=ImportJobStatus.QUEUED, attempt_count=1)
    with factory() as session:
        session.add(QueueOutboxMessage(message_type=QueueMessageType.IMPORT_JOB, entity_id="job-1"))
        session.commit()
    _configure(monkeypatch, factory)

    result = maintenance_imports.reconcile_stale_imports()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    with factory() as session:
        assert session.query(QueueOutboxMessage).filter_by(entity_id="job-1").count() == 1


def test_stale_running_import_with_exhausted_attempts_is_terminal(monkeypatch) -> None:
    factory = _session_factory()
    _add_job(factory, job_id="job-1", status=ImportJobStatus.RUNNING, attempt_count=3)
    _configure(monkeypatch, factory)

    result = maintenance_imports.reconcile_stale_imports()

    assert result.changed_count == 1
    assert result.scheduled_count == 0
    with factory() as session:
        job = session.get(ImportJob, "job-1")
        assert job.status is ImportJobStatus.FAILED
        assert job.error_code is ImportJobErrorCode.IMPORT_PROCESSING_FAILED
        assert job.error_message == ImportProcessingErrorCode.STALE_IMPORT_RECOVERY
        assert session.query(Notification).filter_by(entity_id="job-1").count() == 1


def test_fresh_and_terminal_imports_are_ignored(monkeypatch) -> None:
    factory = _session_factory()
    _add_job(factory, job_id="fresh", status=ImportJobStatus.RUNNING, attempt_count=1, stale=False)
    _add_job(factory, job_id="failed", status=ImportJobStatus.FAILED, attempt_count=1)
    _configure(monkeypatch, factory)

    result = maintenance_imports.reconcile_stale_imports()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
