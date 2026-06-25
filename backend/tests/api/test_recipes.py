from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.main import create_app
from app.models import (
    Recipe,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    RecipeSource,
    RecipeSourceStatus,
    SourceType,
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


def seed_recipe(SessionLocal):
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(
            owner_id=user.id,
            title="Soup",
            instructions=["Heat water"],
            note="old",
        )
        recipe.sources.append(
            RecipeSource(
                owner_id=user.id,
                type=SourceType.TEXT,
                text="Soup recipe",
                position=0,
                status=RecipeSourceStatus.USED,
                assessment_reason="Selected as primary evidence by AI.",
                assessment_confidence=0.8,
            )
        )
        recipe.review_flags.append(
            RecipeReviewFlag(
                owner_id=user.id,
                type=RecipeReviewFlagType.CONTENT_WARNING,
                status=RecipeReviewFlagStatus.OPEN,
                reason_code="LOW_CONFIDENCE",
                message="Review suggested: LOW_CONFIDENCE.",
                details={"confidence": 0.7},
            )
        )
        session.add(recipe)
        session.commit()
        return recipe.id, recipe.review_flags[0].id


def test_recipe_list_and_detail_include_sources_and_flags():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    list_response = client.get("/recipes")
    detail_response = client.get(f"/recipes/{recipe_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["title"] == "Soup"
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["sources"][0]["status"] == "used"
    assert detail["reviewFlags"][0]["reasonCode"] == "LOW_CONFIDENCE"


def test_patch_recipe_trims_and_truncates_note():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(f"/recipes/{recipe_id}", json={"note": " " + ("x" * 600) + " "})

    assert response.status_code == 200
    assert len(response.json()["note"]) == 500
    assert response.json()["note"] == "x" * 500


def test_resolve_and_unresolve_review_flag():
    client, SessionLocal = client_with_session()
    recipe_id, flag_id = seed_recipe(SessionLocal)

    resolved = client.patch(f"/recipes/{recipe_id}/review-flags/{flag_id}", json={"status": "resolved"})
    reopened = client.patch(f"/recipes/{recipe_id}/review-flags/{flag_id}", json={"status": "open"})

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolvedAt"] is not None
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["resolvedAt"] is None
