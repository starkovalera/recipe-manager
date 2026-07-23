import json
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import AppEnv
from app.db import session as session_module
from app.db.base import Base
from app.maintenance import integrity
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import User, UserStatus
from app.storage.types import StoredFile


class RecordingStorage:
    def __init__(self) -> None:
        self.saved_reports: list[bytes] = []

    def save(self, location, content, original_name, mime_type, *, context):
        self.saved_reports.append(content)
        return StoredFile("report.json", original_name, mime_type, len(content))


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def configure(monkeypatch, factory) -> RecordingStorage:
    storage = RecordingStorage()
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(integrity, "get_settings", lambda: SimpleNamespace(app_env=AppEnv.TEST))
    monkeypatch.setattr(integrity, "get_storage_service", lambda _settings: storage)
    return storage


def test_integrity_check_is_noop_for_consistent_database(monkeypatch) -> None:
    factory = _factory()
    storage = configure(monkeypatch, factory)

    result = integrity.run_integrity_check()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    assert result.anomaly_count == 0
    assert storage.saved_reports == []
    assert {check.invariant for check in integrity.INTEGRITY_CHECKS} == {
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
    storage = configure(monkeypatch, factory)

    result = integrity.run_integrity_check()

    assert result.disposition is MaintenanceProcessingDisposition.ANOMALIES_FOUND
    assert result.anomaly_count == 1
    report = json.loads(storage.saved_reports[0])
    pending_check = next(check for check in report["details"]["checks"] if check["invariant"] == "pending_user_missing_deletion_timestamp")
    assert pending_check["records"] == [{"userId": "user-1"}]
    with factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_integrity_query_failure_is_retryable(monkeypatch) -> None:
    factory = _factory()
    storage = configure(monkeypatch, factory)
    monkeypatch.setattr(
        integrity,
        "INTEGRITY_CHECKS",
        (
            *integrity.INTEGRITY_CHECKS,
            integrity.IntegrityCheck("broken", lambda _session: (_ for _ in ()).throw(RuntimeError("db"))),
        ),
    )

    result = integrity.run_integrity_check()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.failure_count == 1
    assert len(storage.saved_reports) == 1
