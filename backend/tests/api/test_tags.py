from collections.abc import Generator
from datetime import datetime, timezone

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
from app.models import Ingredient, Recipe, RecipeStatus, SourceName, Tag, User
from app.tags.queries import list_active_tags as query_tags
from tests.api.support import install_local_user_override


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
    install_local_user_override(app, SessionLocal)
    return TestClient(app), SessionLocal


def test_tags_list_returns_active_owner_tags_only():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        active = Tag(owner_id=user.id, name="active")
        deleted = Tag(owner_id=user.id, name="deleted")
        deleted.deleted_at = datetime.now(timezone.utc)
        other = Tag(owner_id="other-user", name="other")
        session.add_all([active, deleted, other])
        session.commit()

    response = client.get("/tags")

    assert response.status_code == 200
    names = [tag["name"] for tag in response.json()["items"]]
    assert "active" in names
    assert "deleted" not in names
    assert "other" not in names


def test_tags_list_is_paginated_and_owner_scoped():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        tags = [Tag(owner_id=user.id, name=f"tag-{index}") for index in range(5)]
        deleted = Tag(owner_id=user.id, name="tag-deleted")
        deleted.deleted_at = datetime.now(timezone.utc)
        other_user = User(id="other-user", email="other@example.test")
        foreign = Tag(owner_id=other_user.id, name="tag-foreign")
        session.add_all([*tags, deleted, other_user, foreign])
        session.commit()
        expected_tags = query_tags(session, user.id)

    response = client.get("/tags?limit=2&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(expected_tags)
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert [tag["name"] for tag in payload["items"]] == [tag.name for tag in expected_tags[1:3]]
    assert "tag-deleted" not in [tag.name for tag in expected_tags]
    assert "tag-foreign" not in [tag.name for tag in expected_tags]


def test_tag_create_rejects_duplicate_active_name_case_insensitively():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        session.add(Tag(owner_id=user.id, name="Dinner"))
        session.commit()

    response = client.post("/tags", json={"name": "dinner"})

    assert response.status_code == 409
    assert response.json()["errorCode"] == "DUPLICATE_TAG"


def test_tag_create_enforces_active_tag_limit(monkeypatch):
    monkeypatch.setenv("MAX_TAGS_PER_USER", "1")
    get_settings.cache_clear()
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        for tag in session.query(Tag).filter_by(owner_id=user.id).all():
            tag.deleted_at = datetime.now(timezone.utc)
        session.add(Tag(owner_id=user.id, name="existing"))
        session.commit()

    response = client.post("/tags", json={"name": "new"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TAG_LIMIT_EXCEEDED"


def test_tag_patch_usage_and_soft_delete_preserves_recipe_links():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        tag = Tag(owner_id=user.id, name="quick", description="old")
        recipe = Recipe(
            owner_id=user.id,
            title="Soup",
            source_name=SourceName.MANUAL,
            instructions=["Cook."],
            tags=[tag],
        )
        recipe.ingredients.append(Ingredient(name="Water", position=0))
        session.add(recipe)
        session.commit()
        tag_id = tag.id

    patch_response = client.patch(f"/tags/{tag_id}", json={"name": "fast", "description": "new"})
    usage_response = client.get(f"/tags/{tag_id}/usage")
    delete_response = client.delete(f"/tags/{tag_id}")
    list_response = client.get("/tags")

    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "fast"
    assert patch_response.json()["description"] == "new"
    assert usage_response.status_code == 200
    assert usage_response.json()["recipeCount"] == 1
    assert delete_response.status_code == 200
    assert delete_response.json()["deletedAt"] is not None
    assert "fast" not in [tag["name"] for tag in list_response.json()["items"]]
    with SessionLocal() as session:
        saved = session.get(Tag, tag_id)
        assert saved is not None
        assert saved.deleted_at is not None
        assert len(saved.recipes) == 1


def test_tag_usage_excludes_pending_recipes():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        tag = Tag(owner_id=user.id, name="quick")
        session.add_all(
            [
                Recipe(owner_id=user.id, title="Active", instructions=["Cook"], tags=[tag]),
                Recipe(
                    owner_id=user.id,
                    title="Pending",
                    instructions=["Cook"],
                    tags=[tag],
                    status=RecipeStatus.DELETION_PENDING,
                ),
            ]
        )
        session.commit()
        tag_id = tag.id

    response = client.get(f"/tags/{tag_id}/usage")

    assert response.status_code == 200
    assert response.json()["recipeCount"] == 1


def test_tag_patch_name_without_description_preserves_description():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        tag = Tag(owner_id=user.id, name="quick", description="Keep me")
        session.add(tag)
        session.commit()
        tag_id = tag.id

    response = client.patch(f"/tags/{tag_id}", json={"name": "fast"})

    assert response.status_code == 200
    assert response.json()["name"] == "fast"
    assert response.json()["description"] == "Keep me"
