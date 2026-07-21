from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.maintenance import integrity
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import User, UserStatus


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_integrity_check_is_noop_for_consistent_database(monkeypatch) -> None:
    factory = _factory()
    monkeypatch.setattr(session_module, "SessionLocal", factory)

    result = integrity.check_integrity()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    assert result.anomaly_count == 0
    assert set(integrity.INTEGRITY_CHECKS) == {
        "successful_import_missing_recipe",
        "ready_embedding_missing_data",
        "running_embedding_missing_attempt_timestamp",
        "pending_user_missing_deletion_timestamp",
        "published_outbox_missing_published_timestamp",
        "foreign_recipe_cover_image",
    }


def test_integrity_check_reports_anomaly_counts_without_mutation(monkeypatch) -> None:
    factory = _factory()
    with factory() as session:
        session.add(User(id="user-1", email="user@example.test", status=UserStatus.DELETION_PENDING))
        session.commit()
    monkeypatch.setattr(session_module, "SessionLocal", factory)

    result = integrity.check_integrity()

    assert result.disposition is MaintenanceProcessingDisposition.ANOMALIES_FOUND
    assert result.anomaly_count == 1
    with factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_integrity_query_failure_is_retryable(monkeypatch) -> None:
    factory = _factory()
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setitem(integrity.INTEGRITY_CHECKS, "broken", lambda _session: (_ for _ in ()).throw(RuntimeError("db")))

    result = integrity.check_integrity()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.failure_count == 1
