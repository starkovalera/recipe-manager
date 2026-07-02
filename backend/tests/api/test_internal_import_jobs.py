from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.imports.events import record_job_event
from app.main import create_app
from app.models import ImportJob, ImportJobSource, ImportJobStatus, ImportSourceStatus, SourceType


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app), SessionLocal


def test_internal_import_jobs_returns_jobs_sources_events_and_status_history():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        job = ImportJob(
            owner_id=user.id,
            client_id="client-1",
            client_import_id="import-1",
            dedupe_key="import-1",
            status=ImportJobStatus.SUCCEEDED,
        )
        job.sources.append(
            ImportJobSource(
                type=SourceType.URL,
                status=ImportSourceStatus.READY,
                url="https://example.com/post",
                position=0,
            )
        )
        session.add(job)
        record_job_event(job, "queued", {"clientImportId": "import-1"})
        record_job_event(job, "worker_started", {"status": "running"})
        record_job_event(job, "recipe_created", {"recipeId": "recipe-1", "status": "succeeded"})
        session.commit()

    response = client.get("/internal/import-jobs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == job.id
    assert item["ownerId"] == "local-user"
    assert item["clientId"] == "client-1"
    assert item["status"] == "succeeded"
    assert item["sources"][0]["type"] == "URL"
    assert item["sources"][0]["url"] == "https://example.com/post"
    assert [event["eventType"] for event in item["events"]] == ["queued", "worker_started", "recipe_created"]
    assert [entry["status"] for entry in item["statusHistory"]] == ["queued", "running", "succeeded"]
