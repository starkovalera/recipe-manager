import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import AppEnv
from app.db import session as session_module
from app.db.base import Base
from app.maintenance import orphaned_uploads
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import ImportJob, ImportJobSource, ImportJobStatus, RecipeImage, SourceType, User
from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.types import StorageObjectInfo, StorageObjectPage, StoredFile


class PaginatedStorage:
    list_all_objects = StorageService.list_all_objects

    def __init__(self, objects: dict[str, StorageObjectInfo]) -> None:
        self.objects = objects
        self.list_calls: list[dict] = []
        self.delete_calls: list[str] = []
        self.saved_reports: list[bytes] = []

    def list_objects(self, location, *, prefix, limit, cursor=None):
        self.list_calls.append({"prefix": prefix, "cursor": cursor})
        keys = sorted(key for key in self.objects if key.startswith(prefix) and (cursor is None or key > cursor))
        selected = keys[:1]
        has_more = len(keys) > 1
        return StorageObjectPage(
            objects=tuple(self.objects[key] for key in selected),
            next_cursor=selected[-1] if selected and has_more else None,
        )

    def delete(self, location, storage_key):
        self.delete_calls.append(storage_key)

    def save(self, location, content, original_name, mime_type, *, context):
        assert location is StorageLocation.SYSTEM_ARTIFACTS
        self.saved_reports.append(content)
        return StoredFile("report.json", original_name, mime_type, len(content))


class ListingFailureStorage(PaginatedStorage):
    def list_objects(self, location, *, prefix, limit, cursor=None):
        if prefix == "imports/source/":
            raise OSError("provider unavailable")
        return super().list_objects(location, prefix=prefix, limit=limit, cursor=cursor)


def object_info(storage_key: str, *, age_hours: int = 48) -> StorageObjectInfo:
    return StorageObjectInfo(
        storage_key=storage_key,
        size_bytes=42,
        last_modified_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
    )


def build_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def configure(monkeypatch, factory, storage: PaginatedStorage) -> None:
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        orphaned_uploads,
        "get_settings",
        lambda: SimpleNamespace(app_env=AppEnv.TEST, orphaned_upload_min_age_hours=24),
    )
    monkeypatch.setattr(orphaned_uploads, "get_storage_service", lambda _settings: storage)


def add_references(factory, *, import_key: str, recipe_key: str) -> None:
    with factory() as session:
        user = User(id="owner-1", email="owner@example.test")
        job = ImportJob(id="job-1", owner=user, client_id="job-1", status=ImportJobStatus.FAILED)
        session.add_all(
            [
                user,
                job,
                ImportJobSource(
                    import_job=job,
                    type=SourceType.IMAGE,
                    image_storage_key=import_key,
                    position=0,
                ),
                RecipeImage(
                    storage_key=recipe_key,
                    original_name="recipe.jpg",
                    mime_type="image/jpeg",
                    size_bytes=42,
                    position=0,
                ),
            ]
        )
        session.commit()


def test_orphan_detection_is_paginated_read_only_and_reports_old_anomalies(monkeypatch) -> None:
    factory = build_factory()
    referenced_source = "imports/source/owner-1/job-1/source.jpg"
    orphaned_derived = "imports/derived/owner-1/job-1/audio.mp3"
    referenced_recipe = "recipes/media/owner-1/recipe-1/cover.jpg"
    malformed = "imports/source/malformed.jpg"
    fresh = "recipes/media/owner-1/recipe-1/fresh.jpg"
    add_references(factory, import_key=referenced_source, recipe_key=referenced_recipe)
    storage = PaginatedStorage(
        {
            key: object_info(key, age_hours=1 if key == fresh else 48)
            for key in (referenced_source, orphaned_derived, referenced_recipe, malformed, fresh)
        }
    )
    configure(monkeypatch, factory, storage)

    result = orphaned_uploads.detect_orphaned_uploads()

    assert result.disposition is MaintenanceProcessingDisposition.ANOMALIES_FOUND
    assert result.scanned_count == 5
    assert result.anomaly_count == 2
    assert storage.delete_calls == []
    assert len(storage.saved_reports) == 1
    report = json.loads(storage.saved_reports[0])
    reported_keys = {item["storageKey"] for item in report["details"]["objects"]}
    assert reported_keys == {orphaned_derived, malformed}
    assert any(call["cursor"] is not None for call in storage.list_calls)


def test_orphan_detection_clean_run_does_not_save_report(monkeypatch) -> None:
    factory = build_factory()
    source_key = "imports/source/owner-1/job-1/source.jpg"
    recipe_key = "recipes/media/owner-1/recipe-1/cover.jpg"
    add_references(factory, import_key=source_key, recipe_key=recipe_key)
    storage = PaginatedStorage({key: object_info(key) for key in (source_key, recipe_key)})
    configure(monkeypatch, factory, storage)

    result = orphaned_uploads.detect_orphaned_uploads()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    assert result.anomaly_count == 0
    assert storage.saved_reports == []
    assert storage.delete_calls == []


def test_orphan_detection_listing_failure_is_retryable_and_reported(monkeypatch) -> None:
    factory = build_factory()
    storage = ListingFailureStorage({})
    configure(monkeypatch, factory, storage)

    result = orphaned_uploads.detect_orphaned_uploads()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.failure_count == 1
    assert len(storage.saved_reports) == 1
    assert storage.delete_calls == []
