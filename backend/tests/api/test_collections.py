from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.collections.queries import list_collections as query_collections
from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.main import create_app
from app.models import Collection, Recipe, User


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


def seed_recipe(SessionLocal):
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Cook"])
        session.add(recipe)
        session.commit()
        return recipe.id


def test_collection_create_list_detail_membership_and_delete():
    client, SessionLocal = client_with_session()
    recipe_id = seed_recipe(SessionLocal)

    created = client.post("/collections", json={"name": "Weeknight", "description": "Fast dinners"})
    collection_id = created.json()["id"]
    added = client.put(f"/collections/{collection_id}/recipes/{recipe_id}")
    detail = client.get(f"/collections/{collection_id}")
    recipe_detail = client.get(f"/recipes/{recipe_id}")
    listed = client.get("/collections")
    removed = client.delete(f"/collections/{collection_id}/recipes/{recipe_id}")
    after_remove = client.get(f"/collections/{collection_id}")
    deleted = client.delete(f"/collections/{collection_id}")

    assert created.status_code == 200
    assert created.json()["name"] == "Weeknight"
    assert added.status_code == 204
    assert detail.json()["recipes"][0]["id"] == recipe_id
    assert recipe_detail.json()["collections"][0]["id"] == collection_id
    assert listed.json()["items"][0]["recipeCount"] == 1
    assert removed.status_code == 204
    assert after_remove.json()["recipes"] == []
    assert deleted.status_code == 204
    assert client.get(f"/collections/{collection_id}").status_code == 404


def test_collection_list_is_paginated_and_owner_scoped():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        collections = [Collection(owner_id=user.id, name=f"Collection {index}") for index in range(5)]
        other_user = User(id="other-user", email="other@example.test")
        other_collection = Collection(owner_id=other_user.id, name="Private")
        session.add_all([*collections, other_user, other_collection])
        session.commit()
        assert len(query_collections(session, user.id)) == 5

    response = client.get("/collections?limit=2&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert [item["name"] for item in payload["items"]] == ["Collection 1", "Collection 2"]


def test_collection_endpoints_are_scoped_to_current_user():
    client, SessionLocal = client_with_session()
    recipe_id = seed_recipe(SessionLocal)
    with SessionLocal() as session:
        other_user = User(id="other-user", email="other@example.test")
        other_recipe = Recipe(owner_id=other_user.id, title="Private Soup", instructions=["Hide"])
        other_collection = Collection(owner_id=other_user.id, name="Private")
        session.add_all([other_user, other_recipe, other_collection])
        session.commit()
        other_recipe_id = other_recipe.id
        other_collection_id = other_collection.id

    listed = client.get("/collections")
    other_detail = client.get(f"/collections/{other_collection_id}")
    other_delete = client.delete(f"/collections/{other_collection_id}")
    add_other_recipe = client.put(f"/collections/{client.post('/collections', json={'name': 'Mine'}).json()['id']}/recipes/{other_recipe_id}")

    assert listed.json()["items"] == []
    assert other_detail.status_code == 404
    assert other_delete.status_code == 404
    assert add_other_recipe.status_code == 404
    assert client.get(f"/recipes/{recipe_id}").status_code == 200
