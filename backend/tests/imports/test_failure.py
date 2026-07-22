from collections.abc import Callable

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import session as session_module
from app.db.base import Base
from app.imports.error_codes import (
    ExtractorUnavailableError,
    InvalidExtractionResult,
    NotARecipeError,
    RecipeTooLongError,
    ResultParseError,
    SecondaryResourceUploadError,
)
from app.imports.job_stages.failure import process_import_failure
from app.imports.outcomes import ImportProcessingDisposition
from app.imports.storage_cleanup import cleanup_import_storage
from app.local.users import ensure_default_user
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobErrorCode,
    ImportJobStatus,
    JobEvent,
    Notification,
    NotificationType,
)
from app.storage.constants import StorageLocation


class FakeStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        assert location is StorageLocation.USER_MEDIA
        self.deleted_keys.append(storage_key)


class PartiallyFailingStorage(FakeStorage):
    def delete(self, location: StorageLocation, storage_key: str) -> None:
        assert location is StorageLocation.USER_MEDIA
        self.deleted_keys.append(storage_key)
        if storage_key == "upload-1":
            raise OSError("delete failed")


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def configure_failure_session(session: Session) -> None:
    session_module.SessionLocal = sessionmaker(bind=session.get_bind(), expire_on_commit=False)


def create_job(
    session: Session,
    *,
    attempt_count: int = 1,
    status: ImportJobStatus = ImportJobStatus.RUNNING,
) -> ImportJob:
    user = ensure_default_user(session)
    job = ImportJob(
        owner_id=user.id,
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="import-1",
        status=status,
        attempt_count=attempt_count,
    )
    session.add(job)
    session.commit()
    return job


def get_events(session: Session, job_id: str) -> list[JobEvent]:
    return list(session.scalars(select(JobEvent).where(JobEvent.import_job_id == job_id)))


def get_notifications(session: Session) -> list[Notification]:
    return list(session.scalars(select(Notification)))


def test_retryable_failure_returns_job_to_queue_without_final_notification() -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ExtractorUnavailableError(provider_message="provider unavailable"),
    )

    session.refresh(job)
    assert result.disposition is ImportProcessingDisposition.RETRYABLE_FAILURE
    assert result.detailed_error_code == "EXTRACTOR_UNAVAILABLE"
    assert job.status is ImportJobStatus.QUEUED
    assert job.attempt_count == 1
    assert job.started_at is None
    assert job.finished_at is None
    assert job.error_code is None
    assert job.error_message is None
    assert get_notifications(session) == []
    assert get_events(session, job.id)[-1].payload == {
        "error": {
            "import_job_code": "IMPORT_EXTRACTION_FAILED",
            "code": "EXTRACTOR_UNAVAILABLE",
            "message": "Import extraction failed: extractor unavailable.",
        },
        "retryable": True,
        "terminal": False,
        "attempt_count": 1,
        "max_attempts": 3,
        "provider_message": "provider unavailable",
    }
    assert storage.deleted_keys == ["secondary-1"]


@pytest.mark.parametrize(
    ("error_factory", "expected_code", "expected_message"),
    [
        (lambda: RuntimeError("raw unexpected detail"), "UNEXPECTED_ERROR", "Import failed."),
        (
            lambda: SecondaryResourceUploadError(resource_type="URL"),
            "SECONDARY_RESOURCE_UPLOADING_FAILED",
            SecondaryResourceUploadError.message,
        ),
        (ResultParseError, "RESULT_PARSE_FAILED", ResultParseError.message),
        (InvalidExtractionResult, "INVALID_EXTRACTION_RESULT", InvalidExtractionResult.message),
        (ExtractorUnavailableError, "EXTRACTOR_UNAVAILABLE", ExtractorUnavailableError.message),
    ],
)
def test_each_retryable_error_returns_job_to_queue(
    error_factory: Callable[[], Exception],
    expected_code: str,
    expected_message: str,
) -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=error_factory(),
    )

    session.refresh(job)
    event = get_events(session, job.id)[-1]
    assert result.disposition is ImportProcessingDisposition.RETRYABLE_FAILURE
    assert result.detailed_error_code == expected_code
    assert job.status is ImportJobStatus.QUEUED
    assert event.payload["error"]["code"] == expected_code
    assert event.payload["error"]["message"] == expected_message
    assert event.payload["retryable"] is True
    assert event.payload["terminal"] is False
    assert get_notifications(session) == []
    assert storage.deleted_keys == ["secondary-1"]


@pytest.mark.parametrize("error", [NotARecipeError(), RecipeTooLongError()])
def test_non_retryable_error_is_terminal(error: Exception) -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=error,
    )

    session.refresh(job)
    event = get_events(session, job.id)[-1]
    assert result.disposition is ImportProcessingDisposition.PERMANENT_FAILURE
    assert result.detailed_error_code == error.code
    assert job.status is ImportJobStatus.FAILED
    assert job.error_code is ImportJobErrorCode.IMPORT_EXTRACTION_FAILED
    assert job.error_message == error.code
    assert event.payload["retryable"] is False
    assert event.payload["terminal"] is True
    assert get_notifications(session)[-1].type is NotificationType.IMPORT_FAILED
    assert storage.deleted_keys == ["secondary-1", "primary-1"]


def test_retryable_error_is_terminal_after_final_attempt() -> None:
    session = create_session()
    job = create_job(session, attempt_count=3)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=ExtractorUnavailableError(),
    )

    session.refresh(job)
    event = get_events(session, job.id)[-1]
    assert result.disposition is ImportProcessingDisposition.PERMANENT_FAILURE
    assert result.detailed_error_code == "EXTRACTOR_UNAVAILABLE"
    assert job.status is ImportJobStatus.FAILED
    assert job.error_code is ImportJobErrorCode.IMPORT_EXTRACTION_FAILED
    assert job.error_message == "EXTRACTOR_UNAVAILABLE"
    assert event.payload["retryable"] is True
    assert event.payload["terminal"] is True
    assert get_notifications(session)[-1].type is NotificationType.IMPORT_FAILED
    assert storage.deleted_keys == ["secondary-1", "primary-1"]


@pytest.mark.parametrize(
    "status",
    [
        ImportJobStatus.SUCCEEDED,
        ImportJobStatus.SUCCEEDED_WITH_FLAGS,
        ImportJobStatus.FAILED,
        ImportJobStatus.CANCELLED,
    ],
)
def test_process_import_failure_is_noop_for_terminal_job(status: ImportJobStatus) -> None:
    session = create_session()
    job = create_job(session, status=status)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=RuntimeError("unexpected"),
    )

    assert result.disposition is ImportProcessingDisposition.NOOP
    assert result.detailed_error_code is None
    assert get_events(session, job.id) == []
    assert get_notifications(session) == []
    assert storage.deleted_keys == []


def test_process_import_failure_is_noop_for_missing_job() -> None:
    session = create_session()
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        "missing-job",
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=RuntimeError("unexpected"),
    )

    assert result.disposition is ImportProcessingDisposition.NOOP
    assert result.detailed_error_code is None
    assert get_notifications(session) == []
    assert storage.deleted_keys == []


@pytest.mark.parametrize("error", [ExtractorUnavailableError(), NotARecipeError()])
def test_process_import_failure_can_keep_all_storage(error: Exception) -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=error,
        cleanup_storage=False,
    )

    assert storage.deleted_keys == []


def test_process_import_failure_handles_missing_error_as_retryable_unexpected_error() -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=None,
        cleanup_storage=False,
    )

    session.refresh(job)
    assert result.disposition is ImportProcessingDisposition.RETRYABLE_FAILURE
    assert result.detailed_error_code == "UNEXPECTED_ERROR"
    assert job.status is ImportJobStatus.QUEUED
    assert get_events(session, job.id)[-1].payload["error"] == {
        "import_job_code": "IMPORT_FAILED",
        "code": "UNEXPECTED_ERROR",
        "message": "Import failed.",
    }


def test_cleanup_import_storage_attempts_every_key_when_one_delete_fails() -> None:
    storage = PartiallyFailingStorage()

    cleanup_import_storage(storage, StorageLocation.USER_MEDIA, ["upload-1", "upload-2"])

    assert storage.deleted_keys == ["upload-1", "upload-2"]


def test_process_import_failure_commits_when_failure_logging_raises(monkeypatch) -> None:
    session = create_session()
    job = create_job(session)
    storage = FakeStorage()
    configure_failure_session(session)

    def raise_broken_pipe(*args, **kwargs):
        raise BrokenPipeError(232, "The pipe is being closed")

    monkeypatch.setattr("app.imports.job_stages.failure.log_import_failed", raise_broken_pipe)

    result = process_import_failure(
        job.id,
        storage,
        primary_storage_keys=["primary-1"],
        secondary_storage_keys=["secondary-1"],
        max_import_attempts=3,
        error=NotARecipeError(),
    )

    session.expire_all()
    assert result.disposition is ImportProcessingDisposition.PERMANENT_FAILURE
    assert job.status is ImportJobStatus.FAILED
    assert get_events(session, job.id)[-1].event_type is ImportEventType.IMPORT_FAILED
    assert get_notifications(session)[-1].type is NotificationType.IMPORT_FAILED
    assert storage.deleted_keys == ["secondary-1", "primary-1"]
