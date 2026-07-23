from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import AppEnv
from app.db import session as session_module
from app.db.base import Base
from app.maintenance import failed_import_artifacts
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    JobEvent,
    QueueOutboxMessage,
    Recipe,
    SourceType,
    User,
)
from app.queueing.constants import QueueMessageType
from app.storage.constants import StorageLocation
from app.storage.types import StorageObjectInfo, StorageObjectPage, StoredFile


class MemoryStorage:
    def __init__(self, objects: dict[str, bytes], *, unsafe_keys: set[str] | None = None) -> None:
        self.objects = objects
        self.unsafe_keys = unsafe_keys or set()
        self.deleted: list[str] = []
        self.saved_reports: list[bytes] = []

    def is_safe_key(self, location, storage_key):
        return storage_key not in self.unsafe_keys

    def list_objects(self, location, *, prefix, limit, cursor=None):
        keys = sorted(key for key in self.objects if key.startswith(prefix) and (cursor is None or key > cursor))
        selected = keys[: limit + 1]
        has_more = len(selected) > limit
        selected = selected[:limit]
        return StorageObjectPage(
            objects=tuple(StorageObjectInfo(key, len(self.objects[key]), datetime(2026, 7, 1, tzinfo=timezone.utc)) for key in selected),
            next_cursor=selected[-1] if has_more else None,
        )

    def delete(self, location, storage_key):
        self.deleted.append(storage_key)
        self.objects.pop(storage_key, None)

    def save(self, location, content, original_name, mime_type, *, context):
        assert location is StorageLocation.SYSTEM_ARTIFACTS
        self.saved_reports.append(content)
        return StoredFile("report.json", original_name, mime_type, len(content))


class ListingFailureStorage(MemoryStorage):
    def list_objects(self, location, *, prefix, limit, cursor=None):
        raise OSError("provider unavailable")


def build_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def add_job(
    factory,
    *,
    job_id: str,
    status: ImportJobStatus = ImportJobStatus.FAILED,
    finished_at: datetime | None = None,
    storage_keys: tuple[str, ...] = (),
    created_recipe: bool = False,
) -> None:
    with factory() as session:
        user = session.get(User, "owner-1")
        if user is None:
            user = User(id="owner-1", email="owner@example.test")
            session.add(user)
        job = ImportJob(
            id=job_id,
            owner=user,
            client_id=job_id,
            status=status,
            finished_at=finished_at or datetime.now(timezone.utc) - timedelta(days=40),
        )
        if created_recipe:
            recipe = Recipe(owner=user, title=f"Recipe {job_id}")
            session.add(recipe)
            job.created_recipe = recipe
        session.add(job)
        for position, storage_key in enumerate(storage_keys):
            session.add(
                ImportJobSource(
                    import_job=job,
                    type=SourceType.IMAGE,
                    image_storage_key=storage_key,
                    position=position,
                )
            )
        session.commit()


def configure(monkeypatch, factory, storage: MemoryStorage) -> None:
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        failed_import_artifacts,
        "get_settings",
        lambda: SimpleNamespace(
            app_env=AppEnv.TEST,
            failed_import_artifact_retention_hours=720,
            maintenance_batch_size=100,
        ),
    )
    monkeypatch.setattr(failed_import_artifacts, "get_storage_service", lambda _settings: storage)


def test_cleanup_excludes_ineligible_candidates(monkeypatch) -> None:
    factory = build_factory()
    add_job(factory, job_id="eligible")
    add_job(factory, job_id="fresh", finished_at=datetime.now(timezone.utc))
    add_job(factory, job_id="queued", status=ImportJobStatus.QUEUED)
    add_job(factory, job_id="cleaned", status=ImportJobStatus.FAILED_ARTIFACTS_REMOVED)
    add_job(factory, job_id="recipe-created", created_recipe=True)
    with factory() as session:
        session.add(QueueOutboxMessage(message_type=QueueMessageType.IMPORT_JOB, entity_id="eligible"))
        session.commit()
    storage = MemoryStorage({})
    configure(monkeypatch, factory, storage)

    result = failed_import_artifacts.cleanup_failed_import_artifacts()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    assert result.scanned_count == 0


def test_cleanup_removes_nested_legacy_and_unreferenced_artifacts(monkeypatch) -> None:
    factory = build_factory()
    source_prefix = "imports/source/owner-1/job-1/"
    derived_prefix = "imports/derived/owner-1/job-1/"
    nested_key = f"{source_prefix}nested.jpg"
    legacy_key = "legacy.jpg"
    add_job(factory, job_id="job-1", storage_keys=(nested_key, legacy_key))
    storage = MemoryStorage(
        {
            nested_key: b"nested",
            legacy_key: b"legacy",
            f"{source_prefix}leftover.jpg": b"leftover",
            f"{derived_prefix}audio.mp3": b"audio",
            f"{derived_prefix}poster.jpg": b"poster",
        }
    )
    configure(monkeypatch, factory, storage)

    result = failed_import_artifacts.cleanup_failed_import_artifacts()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert result.changed_count == 1
    assert storage.objects == {}
    assert storage.saved_reports == []
    with factory() as session:
        job = session.get(ImportJob, "job-1")
        assert job is not None and job.status is ImportJobStatus.FAILED_ARTIFACTS_REMOVED
        assert all(source.image_storage_key is None for source in job.sources)
        event = session.query(JobEvent).filter_by(import_job_id=job.id).one()
        assert event.event_type is ImportEventType.IMPORT_ARTIFACTS_REMOVED


def test_cleanup_reports_suspicious_nested_reference_without_deleting_it(monkeypatch) -> None:
    factory = build_factory()
    suspicious_key = "recipes/media/owner-1/recipe-1/image.jpg"
    add_job(factory, job_id="job-1", storage_keys=(suspicious_key,))
    storage = MemoryStorage({suspicious_key: b"recipe"})
    configure(monkeypatch, factory, storage)

    result = failed_import_artifacts.cleanup_failed_import_artifacts()

    assert result.disposition is MaintenanceProcessingDisposition.ANOMALIES_FOUND
    assert suspicious_key in storage.objects
    assert storage.deleted == []
    assert len(storage.saved_reports) == 1
    with factory() as session:
        job = session.get(ImportJob, "job-1")
        assert job is not None and job.status is ImportJobStatus.FAILED


def test_cleanup_reports_provider_unsafe_legacy_reference_without_deleting_it(monkeypatch) -> None:
    factory = build_factory()
    unsafe_key = "legacy.jpg"
    add_job(factory, job_id="job-1", storage_keys=(unsafe_key,))
    storage = MemoryStorage({unsafe_key: b"legacy"}, unsafe_keys={unsafe_key})
    configure(monkeypatch, factory, storage)

    result = failed_import_artifacts.cleanup_failed_import_artifacts()

    assert result.disposition is MaintenanceProcessingDisposition.ANOMALIES_FOUND
    assert unsafe_key in storage.objects
    assert storage.deleted == []
    assert len(storage.saved_reports) == 1


def test_cleanup_reports_listing_failure_and_keeps_job_retryable(monkeypatch) -> None:
    factory = build_factory()
    add_job(factory, job_id="job-1")
    storage = ListingFailureStorage({})
    configure(monkeypatch, factory, storage)

    result = failed_import_artifacts.cleanup_failed_import_artifacts()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.failure_count == 1
    assert len(storage.saved_reports) == 1
    with factory() as session:
        job = session.get(ImportJob, "job-1")
        assert job is not None and job.status is ImportJobStatus.FAILED
