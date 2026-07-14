from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import session as session_module
from app.db.base import Base
from app.imports.error_codes import SecondaryResourceUploadError
from app.imports.job_stages.failure import process_import_failure
from app.imports.storage_cleanup import cleanup_import_storage
from app.local.users import ensure_default_user
from app.models import ImportEventType, ImportJob, ImportJobErrorCode, ImportJobStatus, NotificationType


class FakeStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def delete(self, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)


class PartiallyFailingStorage(FakeStorage):
    def delete(self, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)
        if storage_key == "upload-1":
            raise OSError("delete failed")


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_job(session: Session, *, attempt_count: int = 1) -> ImportJob:
    user = ensure_default_user(session)
    job = ImportJob(
        owner_id=user.id,
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="import-1",
        status=ImportJobStatus.RUNNING,
        attempt_count=attempt_count,
    )
    session.add(job)
    session.commit()
    return job


def test_process_import_failure_sets_job_status_event_and_notification() -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=SecondaryResourceUploadError(resource_type="URL", url="https://example.com"),
    )

    assert storage.deleted_keys == ["secondary-1"]
    session.refresh(job)
    assert job.status == ImportJobStatus.FAILED
    assert job.error_code == ImportJobErrorCode.IMPORT_PROCESSING_FAILED
    assert job.error_message == "SECONDARY_RESOURCE_UPLOADING_FAILED"
    assert job.events[-1].event_type == ImportEventType.IMPORT_FAILED
    assert job.events[-1].payload == {
        "error": {
            "import_job_code": "IMPORT_PROCESSING_FAILED",
            "code": "SECONDARY_RESOURCE_UPLOADING_FAILED",
            "message": "Import processing failed due to secondary resource uploading issue.",
        },
        "resource_type": "URL",
        "url": "https://example.com",
        "attempt_count": 1,
        "max_attempts": 3,
    }
    assert job.owner.notifications[-1].type == NotificationType.IMPORT_FAILED


def test_cleanup_import_storage_attempts_every_key_when_one_delete_fails() -> None:
    storage = PartiallyFailingStorage()

    cleanup_import_storage(storage, ["upload-1", "upload-2"])

    assert storage.deleted_keys == ["upload-1", "upload-2"]


def test_process_import_failure_can_keep_storage_on_processing_failures() -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ValueError("unexpected"),
        cleanup_storage=False,
    )

    assert storage.deleted_keys == []
    session.refresh(job)
    assert job.error_code == ImportJobErrorCode.IMPORT_FAILED
    assert job.error_message == "UNEXPECTED_ERROR"
    assert job.events[-1].payload["error"] == {
        "import_job_code": "IMPORT_FAILED",
        "code": "UNEXPECTED_ERROR",
        "message": "unexpected",
    }


def test_process_import_failure_handles_missing_error() -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=None,
        cleanup_storage=False,
    )

    assert storage.deleted_keys == []
    session.refresh(job)
    assert job.status == ImportJobStatus.FAILED
    assert job.error_code == ImportJobErrorCode.IMPORT_FAILED
    assert job.error_message == "UNEXPECTED_ERROR"
    assert job.events[-1].payload["error"] == {
        "import_job_code": "IMPORT_FAILED",
        "code": "UNEXPECTED_ERROR",
        "message": "Import failed.",
    }


def test_process_import_failure_does_not_overwrite_terminal_job() -> None:
    session = create_session()
    job = create_job(session)
    job.status = ImportJobStatus.SUCCEEDED
    session.commit()
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ValueError("unexpected"),
        cleanup_storage=False,
    )

    session.refresh(job)
    assert job.status == ImportJobStatus.SUCCEEDED
    assert job.error_code is None
    assert job.events == []


def test_process_import_failure_deletes_primary_storage_after_final_attempt() -> None:
    session = create_session()
    job = create_job(session, attempt_count=3)
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ValueError("unexpected"),
    )

    assert storage.deleted_keys == ["secondary-1", "primary-1"]


def test_process_import_failure_commits_when_failure_logging_raises(monkeypatch) -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    session_module.SessionLocal = SessionLocal

    def raise_broken_pipe(*args, **kwargs):
        raise BrokenPipeError(232, "The pipe is being closed")

    monkeypatch.setattr("app.imports.job_stages.failure.log_import_failed", raise_broken_pipe)

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ValueError("unexpected"),
    )

    session.expire_all()
    assert job.status == ImportJobStatus.FAILED
    assert job.events[-1].event_type == ImportEventType.IMPORT_FAILED
    assert job.owner.notifications[-1].type == NotificationType.IMPORT_FAILED
    assert storage.deleted_keys == ["secondary-1"]
