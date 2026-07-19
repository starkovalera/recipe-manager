import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.db import session as session_module
from app.db.base import Base
from app.imports.error_codes import ExtractorUnavailableError, NotARecipeError
from app.imports.jobs import process as process_module
from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult
from app.local.users import ensure_default_user
from app.models import ImportJob, ImportJobSource, ImportJobStatus, ImportSourceStatus, SourceType


def create_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session_module.SessionLocal = SessionLocal
    return SessionLocal


def create_text_import(SessionLocal: sessionmaker[Session], *, status: ImportJobStatus = ImportJobStatus.QUEUED) -> str:
    with SessionLocal() as session:
        user = ensure_default_user(session)
        job = ImportJob(
            owner_id=user.id,
            client_id="client-1",
            client_import_id="import-1",
            dedupe_key="import-1",
            status=status,
        )
        job.sources.append(
            ImportJobSource(
                type=SourceType.TEXT,
                status=ImportSourceStatus.READY,
                text="Tomato soup recipe",
                position=0,
            )
        )
        session.add(job)
        session.commit()
        return job.id


@pytest.mark.parametrize("existing_status", [None, ImportJobStatus.RUNNING, ImportJobStatus.SUCCEEDED])
def test_process_import_job_returns_noop_without_invoking_pipeline(monkeypatch, existing_status: ImportJobStatus | None) -> None:
    SessionLocal = create_session_factory()
    job_id = "missing-job" if existing_status is None else create_text_import(SessionLocal, status=existing_status)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("pipeline must not run for a job that cannot be claimed")

    monkeypatch.setattr(process_module, "build_raw_sources", fail_if_called)

    result = process_module.process_import_job(job_id)

    assert result == ImportProcessingResult(
        import_job_id=job_id,
        disposition=ImportProcessingDisposition.NOOP,
    )


def test_process_import_job_returns_succeeded_after_persisting_recipe(monkeypatch) -> None:
    SessionLocal = create_session_factory()
    job_id = create_text_import(SessionLocal)
    monkeypatch.setattr(
        process_module,
        "get_recipe_extraction_provider",
        lambda: ("test", FakeRecipeExtractionProvider()),
    )
    monkeypatch.setattr(process_module, "dispatch_outbox_message", lambda _message_id: False)

    result = process_module.process_import_job(job_id)

    with SessionLocal() as session:
        job = session.get(ImportJob, job_id)
        assert job is not None
        assert job.status in {ImportJobStatus.SUCCEEDED, ImportJobStatus.SUCCEEDED_WITH_FLAGS}
    assert result == ImportProcessingResult(
        import_job_id=job_id,
        disposition=ImportProcessingDisposition.SUCCEEDED,
    )


@pytest.mark.parametrize(
    ("error", "expected_disposition", "expected_status"),
    [
        (
            ExtractorUnavailableError(),
            ImportProcessingDisposition.RETRYABLE_FAILURE,
            ImportJobStatus.QUEUED,
        ),
        (
            NotARecipeError(),
            ImportProcessingDisposition.PERMANENT_FAILURE,
            ImportJobStatus.FAILED,
        ),
    ],
)
def test_process_import_job_propagates_failure_result(
    monkeypatch,
    error: Exception,
    expected_disposition: ImportProcessingDisposition,
    expected_status: ImportJobStatus,
) -> None:
    SessionLocal = create_session_factory()
    job_id = create_text_import(SessionLocal)

    def raise_pipeline_error(*args, **kwargs):
        raise error

    monkeypatch.setattr(process_module, "build_raw_sources", raise_pipeline_error)

    result = process_module.process_import_job(job_id)

    with SessionLocal() as session:
        job = session.get(ImportJob, job_id)
        assert job is not None
        assert job.status is expected_status
    assert result.disposition is expected_disposition
    assert result.detailed_error_code == error.code


def test_process_import_job_propagates_pre_claim_exception(monkeypatch) -> None:
    SessionLocal = create_session_factory()
    job_id = create_text_import(SessionLocal)

    def raise_before_claim(*args, **kwargs):
        raise RuntimeError("database unavailable before claim")

    monkeypatch.setattr(process_module, "start_import_job", raise_before_claim)

    with pytest.raises(RuntimeError, match="database unavailable before claim"):
        process_module.process_import_job(job_id)

    with SessionLocal() as session:
        job = session.get(ImportJob, job_id)
        assert job is not None
        assert job.status is ImportJobStatus.QUEUED
        assert job.attempt_count == 0
