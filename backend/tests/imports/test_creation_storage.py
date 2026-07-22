from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.core.config import get_settings
from app.core.errors import ActiveImportExistsError, ImportCreationError
from app.db.base import Base
from app.imports.jobs import create as create_module
from app.imports.jobs.create import create_import_job
from app.models import User
from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.types import StorageWriteContext, StoredFile


class RecordingStorage:
    def __init__(self, session: Session, *, fail_delete: bool = False) -> None:
        self.session = session
        self.fail_delete = fail_delete
        self.saved: list[tuple[StorageLocation, StorageWriteContext, str]] = []
        self.deleted: list[tuple[StorageLocation, str]] = []

    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageWriteContext,
    ) -> StoredFile:
        assert not self.session.in_transaction()
        storage_key = f"saved-{len(self.saved) + 1}.jpg"
        self.saved.append((location, context, storage_key))
        return StoredFile(storage_key, original_name, mime_type, len(content))

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        self.deleted.append((location, storage_key))
        if self.fail_delete:
            raise OSError("cleanup failed")


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add(User(id="owner-1", email="owner@example.test"))
        session.commit()
        yield session


def upload(name: str) -> UploadFile:
    content = BytesIO()
    Image.new("RGB", (10, 10), color=(200, 20, 20)).save(content, format="JPEG")
    content.seek(0)
    return UploadFile(
        file=content,
        filename=name,
        headers=Headers({"content-type": "image/jpeg"}),
    )


def test_primary_uploads_run_between_database_transactions_with_one_job_context(monkeypatch, session: Session) -> None:
    storage = RecordingStorage(session)
    monkeypatch.setattr(create_module, "get_storage_service", lambda: storage)

    result = create_import_job(
        session,
        owner_id="owner-1",
        client_id="client-1",
        client_import_id="import-1",
        text=None,
        url=None,
        files=[upload("one.jpg"), upload("two.jpg")],
    )

    assert result.was_created is True
    assert [location for location, _, _ in storage.saved] == [StorageLocation.USER_MEDIA] * 2
    assert {context.entity_id for _, context, _ in storage.saved} == {result.job.id}
    assert {context.owner_id for _, context, _ in storage.saved} == {"owner-1"}
    assert {context.purpose for _, context, _ in storage.saved} == {StoragePurpose.IMPORT_SOURCE}


def test_authoritative_limit_failure_cleans_only_current_request_uploads(monkeypatch, session: Session) -> None:
    storage = RecordingStorage(session)
    monkeypatch.setattr(create_module, "get_storage_service", lambda: storage)
    counts = iter((0, get_settings().max_parallel_imports_per_client))
    monkeypatch.setattr(create_module, "count_import_jobs_by_statuses", lambda *_args: next(counts))

    with pytest.raises(ActiveImportExistsError):
        create_import_job(
            session,
            owner_id="owner-1",
            client_id="client-1",
            client_import_id="import-1",
            text=None,
            url=None,
            files=[upload("one.jpg")],
        )

    assert storage.deleted == [(StorageLocation.USER_MEDIA, "saved-1.jpg")]


def test_cleanup_failure_does_not_mask_authoritative_creation_error(monkeypatch, session: Session) -> None:
    storage = RecordingStorage(session, fail_delete=True)
    monkeypatch.setattr(create_module, "get_storage_service", lambda: storage)
    counts = iter((0, get_settings().max_parallel_imports_per_client))
    monkeypatch.setattr(create_module, "count_import_jobs_by_statuses", lambda *_args: next(counts))

    with pytest.raises(ActiveImportExistsError):
        create_import_job(
            session,
            owner_id="owner-1",
            client_id="client-1",
            client_import_id="import-1",
            text=None,
            url=None,
            files=[upload("one.jpg")],
        )


def test_unexpected_preflight_failure_uses_import_creation_error(monkeypatch, session: Session) -> None:
    def fail_preflight(*_args) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(create_module, "_get_existing_import", fail_preflight)

    with pytest.raises(ImportCreationError):
        create_import_job(
            session,
            owner_id="owner-1",
            client_id="client-1",
            client_import_id="import-1",
            text="Recipe",
            url=None,
        )
