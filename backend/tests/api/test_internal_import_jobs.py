from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.imports.events import record_job_event
from app.main import create_app
from app.models import (
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    ImportSourceStatus,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEvent,
    RecipeEmbeddingStatus,
    SourceType,
    User,
)


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


def test_internal_routes_require_admin_user():
    client, _ = client_with_session()
    client.app.dependency_overrides[get_current_user] = lambda: User(id="regular-user", email="regular@example.test")

    response = client.get("/internal/import-jobs")

    assert response.status_code == 403
    assert response.json() == {"errorCode": "FORBIDDEN", "message": "Admin access is required."}


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


def test_internal_embeddings_returns_recipe_embedding_status():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.embedding = RecipeEmbedding(
            model="test-embedding",
            input_hash="hash-1",
            status=RecipeEmbeddingStatus.READY.value,
            failed_attempts=1,
        )
        recipe.embedding.events.append(
            RecipeEmbeddingEvent(
                owner_id=user.id,
                event_type="saved",
                status_after=RecipeEmbeddingStatus.READY.value,
                payload={"dimension": 1536},
            )
        )
        recipe_without_embedding = Recipe(owner_id=user.id, title="No embedding", instructions=["Wait"])
        session.add(recipe)
        session.add(recipe_without_embedding)
        session.commit()

    response = client.get("/internal/embeddings")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["recipeId"] == recipe.id
    assert item["recipeTitle"] == "Soup"
    assert item["ownerId"] == "local-user"
    assert item["status"] == "ready"
    assert item["model"] == "test-embedding"
    assert item["inputHash"] == "hash-1"
    assert item["failedAttempts"] == 1
    assert len(response.json()["items"]) == 1
    assert item["events"][0]["eventType"] == "saved"
    assert item["events"][0]["statusAfter"] == "ready"
    assert item["events"][0]["payload"] == {"dimension": 1536}


def test_internal_embedding_retry_uses_existing_embedding_owner(monkeypatch):
    client, SessionLocal = client_with_session()
    enqueued: list[str] = []
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.embedding = RecipeEmbedding(
            model="test-embedding",
            input_hash="hash-1",
            status=RecipeEmbeddingStatus.FAILED.value,
            failed_attempts=1,
        )
        session.add(recipe)
        session.commit()
        recipe_id = recipe.id

    monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", enqueued.append)
    response = client.post(f"/internal/embeddings/{recipe_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == "stale"
    assert enqueued == [recipe_id]
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert [event.event_type for event in embedding.events] == ["retry_requested", "scheduled", "enqueued"]
