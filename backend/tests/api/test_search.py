from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.local.users import ensure_default_user
from app.main import create_app
from app.models import Ingredient, Recipe, RecipeEmbedding, RecipeEmbeddingStatus, SourceName, Tag, User
from app.services.search import _cosine_distance
from tests.api.support import install_local_user_override


class StaticEmbeddingProvider:
    model = "test-embedding"

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector

    def embed(self, text: str) -> list[float]:
        return self.vector


class VectorLike:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def __bool__(self) -> bool:
        raise ValueError("truth value is ambiguous")

    def tolist(self) -> list[float]:
        return self.values


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    monkeypatch.setenv("MAX_RECIPE_INGREDIENTS", "50")
    monkeypatch.setenv("MAX_RECIPE_INSTRUCTION_CHARS", "1000")
    monkeypatch.setenv("MAX_RECIPE_NOTE_CHARS", "500")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
    install_local_user_override(app, SessionLocal)
    return TestClient(app), SessionLocal


def add_recipe(
    session: Session,
    *,
    owner_id: str,
    title: str,
    vector: list[float] | None,
    status: RecipeEmbeddingStatus | None = RecipeEmbeddingStatus.READY,
    tags: list[Tag] | None = None,
    ingredients: list[str] | None = None,
    source_name: SourceName = SourceName.MANUAL,
    author_name: str | None = None,
) -> Recipe:
    recipe = Recipe(owner_id=owner_id, title=title, instructions=["Cook"], source_name=source_name, author_name=author_name)
    for position, ingredient_name in enumerate(ingredients or []):
        recipe.ingredients.append(Ingredient(name=ingredient_name, position=position))
    recipe.tags.extend(tags or [])
    if vector is not None and status is not None:
        recipe.embedding = RecipeEmbedding(model="test-embedding", status=status, embedding=vector, input_hash=f"hash-{title}")
    session.add(recipe)
    return recipe


def test_semantic_search_ranks_ready_embeddings_and_is_owner_scoped(monkeypatch, capsys):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        other_user = User(id="other-user", email="other@example.test")
        session.add(other_user)
        add_recipe(session, owner_id=user.id, title="Close Soup", vector=[1.0, 0.0])
        add_recipe(session, owner_id=user.id, title="Far Salad", vector=[0.0, 1.0])
        add_recipe(session, owner_id=other_user.id, title="Private Close", vector=[1.0, 0.0])
        session.commit()
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider([1.0, 0.0])))

    response = client.post("/search", json={"text": "warm soup", "limit": 10, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["items"]] == ["Close Soup", "Far Salad"]
    assert payload["hasMore"] is False
    assert payload["limit"] == 10
    assert payload["offset"] == 0
    assert all(item["matchReasons"][0]["type"] == "semantic" for item in payload["items"])
    assert payload["items"][0]["matchReasons"][0]["score"] == 1.0
    message = next(line for line in capsys.readouterr().out.splitlines() if "Semantic search completed" in line)
    assert '"owner_id": "local-user"' in message
    assert '"text_present": true' in message
    assert '"selected_chip_count": 0' in message
    assert '"provider_name": "test"' in message
    assert '"distance_metric": "cosine"' in message
    assert '"returned_count": 2' in message
    assert '"duration_ms"' in message
    assert '"ownerId"' not in message


def test_cosine_distance_handles_vector_like_database_values():
    assert _cosine_distance(VectorLike([1.0, 0.0]), [1.0, 0.0]) == pytest.approx(0.0)


def test_semantic_search_applies_selected_chips_as_hard_filters(monkeypatch):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        dessert = Tag(owner_id=user.id, name="dessert")
        dinner = Tag(owner_id=user.id, name="dinner")
        add_recipe(session, owner_id=user.id, title="Apple Cake", vector=[1.0, 0.0], tags=[dessert], ingredients=["Apple"])
        add_recipe(session, owner_id=user.id, title="Apple Soup", vector=[1.0, 0.0], tags=[dinner], ingredients=["Apple"])
        add_recipe(session, owner_id=user.id, title="Berry Cake", vector=[0.0, 1.0], tags=[dessert], ingredients=["Berry"])
        session.commit()
        dessert_id = dessert.id
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider([1.0, 0.0])))

    response = client.post(
        "/search",
        json={
            "text": "apple",
            "selected": [
                {"type": "tag", "id": dessert_id},
                {"type": "ingredient_query", "value": "apple"},
            ],
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Apple Cake"]


def test_search_without_text_returns_filtered_latest_recipes():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        add_recipe(session, owner_id=user.id, title="Banana Toast", vector=None, ingredients=["Banana"])
        add_recipe(session, owner_id=user.id, title="Apple Toast", vector=None, ingredients=["Apple"])
        session.commit()

    response = client.post(
        "/search",
        json={"selected": [{"type": "ingredient_query", "value": "banana"}], "limit": 10, "offset": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["items"]] == ["Banana Toast"]
    assert payload["hasMore"] is False


def test_semantic_search_excludes_non_ready_embeddings(monkeypatch):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        add_recipe(session, owner_id=user.id, title="Ready Recipe", vector=[1.0, 0.0], status=RecipeEmbeddingStatus.READY)
        add_recipe(session, owner_id=user.id, title="Skipped Recipe", vector=[1.0, 0.0], status=RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS)
        add_recipe(session, owner_id=user.id, title="No Embedding Recipe", vector=None)
        session.commit()
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider([1.0, 0.0])))

    response = client.post("/search", json={"text": "recipe", "limit": 10, "offset": 0})

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Ready Recipe"]


def test_search_uses_limit_plus_one_for_has_more(monkeypatch):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        add_recipe(session, owner_id=user.id, title="One", vector=[1.0, 0.0])
        add_recipe(session, owner_id=user.id, title="Two", vector=[0.0, 1.0])
        session.commit()
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider([1.0, 0.0])))

    response = client.post("/search", json={"text": "recipe", "limit": 1, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["items"]] == ["One"]
    assert payload["hasMore"] is True
