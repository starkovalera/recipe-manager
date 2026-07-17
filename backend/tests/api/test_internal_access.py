from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.constants import UserRole
from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models import ImportJob, ImportJobStatus, Recipe, RecipeEmbedding, RecipeEmbeddingStatus, User, UserRoleAssignment


class StubQueuePublisher:
    def __init__(self) -> None:
        self.import_job_ids: list[str] = []

    def publish_import_job(self, import_job_id: str) -> None:
        self.import_job_ids.append(import_job_id)

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        raise AssertionError(f"Unexpected embedding publication for {recipe_id}")

    def publish_account_deletion(self, user_id: str) -> None:
        raise AssertionError(f"Unexpected account deletion publication for {user_id}")


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def seed_internal_records(session_factory):
    with session_factory() as session:
        debug_user = User(
            id="debug-user",
            email="debug@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
        )
        other = User(id="other", email="other@example.test")
        superadmin = User(
            id="admin",
            email="admin@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
        )
        own_recipe = Recipe(owner=debug_user, title="Own Soup", instructions=[])
        own_recipe.embedding = RecipeEmbedding(model="test", status=RecipeEmbeddingStatus.READY)
        foreign_recipe = Recipe(owner=other, title="Foreign Soup", instructions=[])
        foreign_recipe.embedding = RecipeEmbedding(model="test", status=RecipeEmbeddingStatus.READY)
        session.add_all(
            [
                superadmin,
                own_recipe,
                foreign_recipe,
                ImportJob(owner=debug_user, client_id="debug-client"),
                ImportJob(owner=other, client_id="other-client"),
            ]
        )
        session.commit()
        return debug_user, superadmin


def test_debug_internal_lists_are_owner_scoped_and_superadmin_lists_are_unscoped():
    client, session_factory = client_with_session()
    debug_user, superadmin = seed_internal_records(session_factory)
    client.app.dependency_overrides[get_current_user] = lambda: debug_user

    debug_jobs = client.get("/internal/import-jobs").json()["items"]
    debug_embeddings = client.get("/internal/embeddings").json()["items"]

    assert [item["ownerId"] for item in debug_jobs] == ["debug-user"]
    assert [item["ownerId"] for item in debug_embeddings] == ["debug-user"]

    client.app.dependency_overrides[get_current_user] = lambda: superadmin
    assert {item["ownerId"] for item in client.get("/internal/import-jobs").json()["items"]} == {"debug-user", "other"}
    assert {item["ownerId"] for item in client.get("/internal/embeddings").json()["items"]} == {"debug-user", "other"}


def test_search_debug_marks_foreign_recipes_as_not_openable():
    client, session_factory = client_with_session()
    _debug_user, superadmin = seed_internal_records(session_factory)
    client.app.dependency_overrides[get_current_user] = lambda: superadmin

    response = client.post("/internal/search/explain", json={"limit": 10, "offset": 0})

    assert response.status_code == 200
    assert {item["title"]: item["canOpenRecipe"] for item in response.json()["items"]} == {
        "Own Soup": False,
        "Foreign Soup": False,
    }


def test_debug_search_is_owner_scoped_and_own_recipe_is_openable():
    client, session_factory = client_with_session()
    debug_user, _superadmin = seed_internal_records(session_factory)
    client.app.dependency_overrides[get_current_user] = lambda: debug_user

    response = client.post("/internal/search/explain", json={"limit": 10, "offset": 0})

    assert response.status_code == 200
    assert [(item["title"], item["canOpenRecipe"]) for item in response.json()["items"]] == [("Own Soup", True)]


def test_superadmin_can_retry_foreign_import_but_debug_user_cannot(monkeypatch):
    client, session_factory = client_with_session()
    with session_factory() as session:
        owner = User(id="owner", email="owner@example.test")
        debug_user = User(
            id="debug-user",
            email="debug@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
        )
        superadmin = User(
            id="admin",
            email="admin@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
        )
        job = ImportJob(owner=owner, client_id="client", status=ImportJobStatus.FAILED, attempt_count=1)
        session.add_all([debug_user, superadmin, job])
        session.commit()
        job_id = job.id
    publisher = StubQueuePublisher()
    monkeypatch.setattr("app.api.routes.internal.get_queue_publisher", lambda: publisher, raising=False)
    client.app.dependency_overrides[get_current_user] = lambda: debug_user
    assert client.post(f"/internal/import-jobs/{job_id}/retry").status_code == 404
    assert publisher.import_job_ids == []

    client.app.dependency_overrides[get_current_user] = lambda: superadmin
    response = client.post(f"/internal/import-jobs/{job_id}/retry")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert publisher.import_job_ids == [job_id]


def test_superadmin_can_retry_foreign_embedding_but_debug_user_cannot(monkeypatch):
    client, session_factory = client_with_session()
    with session_factory() as session:
        owner = User(id="owner", email="owner@example.test")
        debug_user = User(
            id="debug-user",
            email="debug@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
        )
        superadmin = User(
            id="admin",
            email="admin@example.test",
            role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
        )
        recipe = Recipe(owner=owner, title="Soup", instructions=[])
        recipe.embedding = RecipeEmbedding(model="test", status=RecipeEmbeddingStatus.FAILED)
        session.add_all([debug_user, superadmin, recipe])
        session.commit()
        recipe_id = recipe.id
    monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", lambda _recipe_id, _owner_id: True)
    client.app.dependency_overrides[get_current_user] = lambda: debug_user
    assert client.post(f"/internal/embeddings/{recipe_id}/retry").status_code == 404

    client.app.dependency_overrides[get_current_user] = lambda: superadmin
    response = client.post(f"/internal/embeddings/{recipe_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "STALE"
