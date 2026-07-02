from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.main import create_app
from app.models import Ingredient, Recipe, SourceName, Tag, User


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    monkeypatch.setenv("MAX_TAGS_PER_USER", "50")
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
    return TestClient(app), SessionLocal


def test_search_suggestions_return_owner_scoped_direct_matches():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        tag = Tag(owner_id=user.id, name="quick")
        deleted_tag = Tag(owner_id=user.id, name="quick deleted")
        other_user = User(id="other-user", email="other@example.test")
        foreign_tag = Tag(owner_id=other_user.id, name="quick foreign")
        recipe = Recipe(
            owner_id=user.id,
            title="Quick soup",
            source_name=SourceName.INSTAGRAM,
            author_name="fast_chef",
            instructions=["Cook"],
            tags=[tag],
        )
        recipe.ingredients.append(Ingredient(name="Chicken", position=0))
        other_recipe = Recipe(owner_id=other_user.id, title="Quick private soup", instructions=["Hide"])
        deleted_tag.deleted_at = datetime.now(timezone.utc)
        session.add_all([recipe, deleted_tag, other_user, foreign_tag, other_recipe])
        session.commit()

    response = client.get("/search/suggestions?q=quick")

    assert response.status_code == 200
    payload = response.json()
    assert {"type": "tag", "id": tag.id, "recipeId": None, "value": None, "label": "quick"} in payload["items"]
    assert {"type": "title", "id": None, "recipeId": recipe.id, "value": None, "label": "Quick soup"} in payload["items"]
    labels = [item["label"] for item in payload["items"]]
    assert "quick deleted" not in labels
    assert "quick foreign" not in labels
    assert "Quick private soup" not in labels


def test_search_suggestions_include_source_author_and_primary_ingredient_query():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(
            owner_id=user.id,
            title="Dinner",
            source_name=SourceName.THREADS,
            author_name="dinner_author",
            instructions=["Cook"],
        )
        recipe.ingredients.append(Ingredient(name="Cottage cheese 5%", position=0))
        session.add(recipe)
        session.commit()

    author_response = client.get("/search/suggestions?q=dinner")
    ingredient_response = client.get("/search/suggestions?q=cottage")
    source_response = client.get("/search/suggestions?q=thr")

    assert author_response.status_code == 200
    assert {"type": "author_name", "id": None, "recipeId": None, "value": "dinner_author", "label": "dinner_author"} in author_response.json()["items"]
    assert ingredient_response.status_code == 200
    assert ingredient_response.json()["items"][0] == {
        "type": "ingredient_query",
        "id": None,
        "recipeId": None,
        "value": "cottage",
        "label": "Ingredient - cottage",
    }
    assert "ingredient_name" not in [item["type"] for item in ingredient_response.json()["items"]]
    assert source_response.status_code == 200
    assert {"type": "source_name", "id": None, "recipeId": None, "value": "THREADS", "label": "THREADS"} in source_response.json()["items"]
