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
from app.models import Ingredient, Recipe, User, UserRoleAssignment


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


def seed_recipe(session_factory, roles: list[UserRole]):
    with session_factory() as session:
        owner = User(
            id="owner",
            email="owner@example.test",
            role_assignments=[UserRoleAssignment(role=role) for role in roles],
        )
        recipe = Recipe(owner=owner, title="Soup", instructions=["Heat"])
        recipe.ingredients.append(Ingredient(name="Water", search_name="water", position=0))
        session.add(recipe)
        session.commit()
        return owner, recipe.id


def test_recipe_debug_is_included_only_for_debug_role():
    client, session_factory = client_with_session()
    owner, recipe_id = seed_recipe(session_factory, [UserRole.DEBUG])
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["debug"]["embeddingInput"]["input"] == "soup water heat"
    assert "resources" in response.json()["debug"]


def test_recipe_debug_is_omitted_for_regular_and_superadmin_only_users():
    for roles in ([], [UserRole.SUPERADMIN]):
        client, session_factory = client_with_session()
        owner, recipe_id = seed_recipe(session_factory, roles)
        client.app.dependency_overrides[get_current_user] = lambda owner=owner: owner

        response = client.get(f"/recipes/{recipe_id}")

        assert response.status_code == 200
        assert "debug" not in response.json()


def test_superadmin_cannot_open_foreign_recipe():
    client, session_factory = client_with_session()
    _owner, recipe_id = seed_recipe(session_factory, [])
    superadmin = User(
        id="admin",
        email="admin@example.test",
        role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
    )
    client.app.dependency_overrides[get_current_user] = lambda: superadmin

    assert client.get(f"/recipes/{recipe_id}").status_code == 404


def test_separate_embedding_input_endpoint_is_removed():
    client, session_factory = client_with_session()
    owner, recipe_id = seed_recipe(session_factory, [UserRole.DEBUG])
    client.app.dependency_overrides[get_current_user] = lambda: owner

    assert client.get(f"/internal/recipes/{recipe_id}/embedding-input").status_code == 404
