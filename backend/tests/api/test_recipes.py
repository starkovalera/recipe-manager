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
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobStatus,
    Ingredient,
    JobEvent,
    Recipe,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeImage,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceRole,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    SourceName,
    SourceType,
    Tag,
    User,
)
from app.recipes.queries import list_recipes as query_recipes
from tests.api.support import install_local_user_override


class StaticEmbeddingProvider:
    model = "test-embedding"

    def embed(self, text: str) -> list[float]:
        return [0.1]


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    monkeypatch.setenv("MAX_RECIPE_INGREDIENTS", "50")
    monkeypatch.setenv("MAX_RECIPE_INSTRUCTION_CHARS", "1000")
    monkeypatch.setenv("MAX_RECIPE_NOTE_CHARS", "500")
    monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", lambda recipe_id, owner_id: True)
    monkeypatch.setattr("app.services.recipes.enqueue_recipe_embedding", lambda recipe_id, owner_id: True)
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


def seed_recipe(SessionLocal):
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(
            owner_id=user.id,
            title="Soup",
            cook_time_minutes=25,
            instructions=["Heat water"],
            nutrition_estimate={"calories": 120, "proteinGrams": 5},
            author_name="chef",
            source_name=SourceName.INSTAGRAM,
            note="old",
        )
        recipe.ingredients.append(Ingredient(name="Water", quantity="1", unit="cup", position=0))
        tag = Tag(owner_id=user.id, name="quick")
        recipe.tags.append(tag)
        source_image = RecipeImage(
            storage_key="source.jpg",
            original_name="source.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            position=0,
        )
        recipe.images.append(source_image)
        recipe.resources.append(
            RecipeResource(
                owner_id=user.id,
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.MANUAL,
                role=RecipeResourceRole.SOURCE,
                image=source_image,
                position=0,
                status=RecipeResourceStatus.USED,
            )
        )
        recipe.resources.append(
            RecipeResource(
                owner_id=user.id,
                type=SourceType.TEXT,
                source=RecipeResourceOrigin.MANUAL,
                role=RecipeResourceRole.SOURCE,
                text="Soup recipe",
                position=0,
                status=RecipeResourceStatus.USED,
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


def test_delete_recipe_preserves_import_history_and_deletes_recipe_media(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    (tmp_path / "source.jpg").write_bytes(b"recipe image")

    with SessionLocal() as session:
        user = ensure_default_user(session)
        job = ImportJob(
            owner_id=user.id,
            client_id="test-client",
            client_import_id="delete-recipe-import",
            dedupe_key="delete-recipe-import",
            status=ImportJobStatus.SUCCEEDED,
            created_recipe_id=recipe_id,
        )
        job.events.append(JobEvent(event_type=ImportEventType.RECIPE_CREATED, payload={"recipe_id": recipe_id}))
        session.add(job)
        session.commit()
        job_id = job.id

    response = client.delete(f"/recipes/{recipe_id}")

    assert response.status_code == 204
    assert not (tmp_path / "source.jpg").exists()
    with SessionLocal() as session:
        job = session.get(ImportJob, job_id)
        assert job is not None
        assert job.created_recipe_id is None
        assert [event.event_type for event in job.events] == [ImportEventType.RECIPE_CREATED]


def test_delete_recipe_succeeds_when_media_cleanup_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    attempted_keys: list[str] = []

    def fail_delete(_storage, storage_key: str) -> None:
        attempted_keys.append(storage_key)
        raise OSError("storage unavailable")

    monkeypatch.setattr("app.services.recipes.LocalStorageService.delete", fail_delete)

    response = client.delete(f"/recipes/{recipe_id}")

    assert response.status_code == 204
    assert attempted_keys == ["source.jpg"]
    with SessionLocal() as session:
        assert session.get(Recipe, recipe_id) is None


def test_recipe_list_and_detail_include_sources_and_flags():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    list_response = client.get("/recipes")
    detail_response = client.get(f"/recipes/{recipe_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["title"] == "Soup"
    assert list_response.json()["items"][0]["hasOpenReviewFlags"] is True
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["sourceName"] == "INSTAGRAM"
    assert detail["authorName"] == "chef"
    assert detail["nutritionEstimate"] == {"calories": 120, "proteinGrams": 5}
    assert len(detail["tags"]) == 1
    assert detail["tags"][0]["name"] == "quick"
    assert detail["tags"][0]["description"] is None
    assert detail["tags"][0]["deletedAt"] is None
    assert detail["coverOptions"][0]["kind"] == "DEFAULT"
    assert detail["sources"][0]["status"] == "used"
    assert detail["reviewFlags"][0]["reasonCode"] == "LOW_CONFIDENCE"


def test_recipe_list_is_paginated_and_owner_scoped():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipes = [Recipe(owner_id=user.id, title=f"Recipe {index}", instructions=["Cook"]) for index in range(5)]
        other_user = User(id="other-user", email="other@example.test")
        other_recipe = Recipe(owner_id=other_user.id, title="Private Recipe", instructions=["Hide"])
        session.add_all([*recipes, other_user, other_recipe])
        session.commit()
        assert len(query_recipes(session, user.id)) == 5

    response = client.get("/recipes?limit=2&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert len(payload["items"]) == 2
    assert "Private Recipe" not in [item["title"] for item in payload["items"]]


def test_recipe_list_applies_structured_search_filters():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        dinner = Tag(owner_id=user.id, name="dinner")
        breakfast = Tag(owner_id=user.id, name="breakfast")
        soup = Recipe(
            owner_id=user.id,
            title="Chicken Soup",
            source_name=SourceName.INSTAGRAM,
            author_name="soup_author",
            instructions=["Cook soup"],
            tags=[dinner],
        )
        soup.ingredients.append(Ingredient(name="Chicken", position=0))
        pancakes = Recipe(
            owner_id=user.id,
            title="Pancakes",
            source_name=SourceName.THREADS,
            author_name="cake_author",
            instructions=["Cook pancakes"],
            tags=[breakfast],
        )
        pancakes.ingredients.append(Ingredient(name="Flour", position=0))
        other_user = User(id="other-user", email="other@example.test")
        foreign = Recipe(owner_id=other_user.id, title="Private Chicken", instructions=["Hide"])
        foreign.ingredients.append(Ingredient(name="Chicken", position=0))
        session.add_all([soup, pancakes, other_user, foreign])
        session.commit()
        dinner_id = dinner.id
        soup_id = soup.id

    cases = [
        (f"/recipes?tag={dinner_id}", ["Chicken Soup"]),
        ("/recipes?ingredientQuery=chicken", ["Chicken Soup"]),
        ("/recipes?sourceName=INSTAGRAM", ["Chicken Soup"]),
        ("/recipes?authorName=soup_author", ["Chicken Soup"]),
        (f"/recipes?title={soup_id}", ["Chicken Soup"]),
        (f"/recipes?tag={dinner_id}&ingredientQuery=flour", []),
    ]

    for path, expected_titles in cases:
        response = client.get(path)

        assert response.status_code == 200
        payload = response.json()
        assert sorted(item["title"] for item in payload["items"]) == sorted(expected_titles)
        assert payload["total"] == len(expected_titles)


def test_recipe_list_applies_ingredient_query_contains_filters_with_and_semantics():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        protein = Tag(owner_id=user.id, name="protein")
        cottage_banana = Recipe(
            owner_id=user.id,
            title="Cottage Banana Bowl",
            instructions=["Mix"],
            tags=[protein],
        )
        cottage_banana.ingredients.append(Ingredient(name="Cottage cheese 5%", position=0))
        cottage_banana.ingredients.append(Ingredient(name="Banana", position=1))
        soft_cottage = Recipe(owner_id=user.id, title="Soft Cottage Toast", instructions=["Toast"])
        soft_cottage.ingredients.append(Ingredient(name="Soft cottage cheese", position=0))
        banana_only = Recipe(owner_id=user.id, title="Banana Snack", instructions=["Slice"])
        banana_only.ingredients.append(Ingredient(name="Banana", position=0))
        other_user = User(id="other-user", email="other@example.test")
        foreign = Recipe(owner_id=other_user.id, title="Private Cottage", instructions=["Hide"])
        foreign.ingredients.append(Ingredient(name="Cottage cheese 5%", position=0))
        session.add_all([cottage_banana, soft_cottage, banana_only, other_user, foreign])
        session.commit()
        protein_id = protein.id

    cases = [
        ("/recipes?ingredientQuery=cottage", ["Soft Cottage Toast", "Cottage Banana Bowl"]),
        ("/recipes?ingredientQuery=banana", ["Banana Snack", "Cottage Banana Bowl"]),
        ("/recipes?ingredientQuery=cottage&ingredientQuery=banana", ["Cottage Banana Bowl"]),
        (f"/recipes?tag={protein_id}&ingredientQuery=cottage", ["Cottage Banana Bowl"]),
    ]

    for path, expected_titles in cases:
        response = client.get(path)

        assert response.status_code == 200
        payload = response.json()
        assert sorted(item["title"] for item in payload["items"]) == sorted(expected_titles)
        assert payload["total"] == len(expected_titles)


def test_recipe_list_marks_only_open_review_flags():
    client, SessionLocal = client_with_session()
    recipe_id, flag_id = seed_recipe(SessionLocal)

    client.patch(f"/recipes/{recipe_id}/review-flags/{flag_id}", json={"status": "resolved"})

    response = client.get("/recipes")

    assert response.status_code == 200
    assert response.json()["items"][0]["hasOpenReviewFlags"] is False


def test_retry_embedding_endpoint_marks_stale_and_enqueues(monkeypatch):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.ingredients.append(Ingredient(name="Water", position=0))
        session.add(recipe)
        session.commit()
        recipe_id = recipe.id
    enqueued: list[tuple[str, str]] = []
    monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
    monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
    monkeypatch.setattr(
        "app.embeddings.service.enqueue_recipe_embedding",
        lambda recipe_id, owner_id: enqueued.append((recipe_id, owner_id)) or True,
    )

    response = client.post(f"/recipes/{recipe_id}/embedding/retry")

    assert response.status_code == 200
    assert response.json()["status"] == RecipeEmbeddingStatus.STALE.value
    assert enqueued == [(recipe_id, "local-user")]


def test_patch_recipe_succeeds_when_embedding_publish_fails(monkeypatch):
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.ingredients.append(Ingredient(name="Water", position=0))
        session.add(recipe)
        session.commit()
        recipe_id = recipe.id
    monkeypatch.setattr(
        "app.services.recipes.enqueue_recipe_embedding",
        lambda recipe_id, owner_id: False,
        raising=False,
    )

    response = client.patch(f"/recipes/{recipe_id}", json={"title": "Updated soup"})

    assert response.status_code == 200
    assert response.json()["title"] == "Updated soup"
    with SessionLocal() as session:
        recipe = session.get(Recipe, recipe_id)
        assert recipe is not None
        assert recipe.embedding is not None
        assert recipe.embedding.status is RecipeEmbeddingStatus.STALE
        assert [event.event_type for event in recipe.embedding.events] == [RecipeEmbeddingEventType.SCHEDULED]


def test_cover_options_select_source_image_for_generated_cover():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        source_image = RecipeImage(
            storage_key="source.jpg",
            original_name="source.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            position=0,
        )
        cover_image = RecipeImage(
            storage_key="cover.jpg",
            original_name="cover.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            position=-1,
        )
        recipe.images.extend([source_image, cover_image])
        recipe.resources.extend(
            [
                RecipeResource(
                    owner_id=user.id,
                    type=SourceType.IMAGE,
                    source=RecipeResourceOrigin.MANUAL,
                    role=RecipeResourceRole.SOURCE,
                    image=source_image,
                    position=0,
                    status=RecipeResourceStatus.USED,
                ),
                RecipeResource(
                    owner_id=user.id,
                    type=SourceType.IMAGE,
                    source=RecipeResourceOrigin.GENERATED,
                    role=RecipeResourceRole.COVER_CANDIDATE,
                    image=cover_image,
                    position=-1,
                    status=RecipeResourceStatus.USED,
                ),
            ]
        )
        recipe.cover_image = cover_image
        session.add(recipe)
        session.commit()
        recipe_id = recipe.id

    detail = client.get(f"/recipes/{recipe_id}").json()

    assert detail["coverImage"]["id"] == cover_image.id
    assert detail["coverOptions"][0]["kind"] == "DEFAULT"
    assert detail["coverOptions"][0]["selected"] is False
    assert detail["coverOptions"][1]["kind"] == "IMAGE"
    assert detail["coverOptions"][1]["image"]["id"] == cover_image.id
    assert detail["coverOptions"][1]["label"] == "Current cover"
    assert detail["coverOptions"][1]["selected"] is True
    assert detail["coverOptions"][2]["kind"] == "IMAGE"
    assert detail["coverOptions"][2]["label"] == "Image 1"
    assert detail["coverOptions"][2]["image"]["id"] == source_image.id
    assert detail["coverOptions"][2]["selected"] is False


def test_recipe_endpoints_are_scoped_to_current_user():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    with SessionLocal() as session:
        other_user = User(id="other-user", email="other@example.test")
        other_recipe = Recipe(owner_id=other_user.id, title="Private Soup", instructions=["Hide"])
        session.add_all([other_user, other_recipe])
        session.commit()
        other_recipe_id = other_recipe.id

    list_response = client.get("/recipes")
    other_detail = client.get(f"/recipes/{other_recipe_id}")
    other_patch = client.patch(f"/recipes/{other_recipe_id}", json={"title": "Leak"})
    other_delete = client.delete(f"/recipes/{other_recipe_id}")

    assert [item["id"] for item in list_response.json()["items"]] == [recipe_id]
    assert other_detail.status_code == 404
    assert other_patch.status_code == 404
    assert other_delete.status_code == 404


def test_patch_recipe_rejects_note_over_limit():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(f"/recipes/{recipe_id}", json={"note": " " + ("x" * 600) + " "})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "NOTE_TOO_LONG"


def test_patch_recipe_rejects_too_many_ingredients():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={"ingredients": [{"name": f"Ingredient {index}"} for index in range(51)]},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TEXT_TOO_LONG"


def test_patch_recipe_rejects_empty_ingredient_name():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(f"/recipes/{recipe_id}", json={"ingredients": [{"name": "   "}]})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_INGREDIENT"


def test_patch_recipe_rejects_too_long_instructions():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(f"/recipes/{recipe_id}", json={"instructions": ["x" * 1001]})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TEXT_TOO_LONG"


def test_patch_recipe_updates_full_editable_fields_and_cover():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    detail = client.get(f"/recipes/{recipe_id}").json()
    source_image_id = detail["images"][0]["id"]
    with SessionLocal() as session:
        user = ensure_default_user(session)
        dinner = Tag(owner_id=user.id, name="dinner", description="Evening")
        session.add(dinner)
        session.commit()
        dinner_id = dinner.id
        quick_id = detail["tags"][0]["id"]

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={
            "title": "Better Soup",
            "sourceName": "THREADS",
            "authorName": "better_chef",
            "cookTimeMinutes": 35,
            "nutritionEstimate": {"calories": 200, "proteinGrams": 8, "fatGrams": 2, "carbsGrams": 30},
            "ingredients": [{"name": "Tomato", "quantity": "2", "unit": "pcs", "note": "ripe"}],
            "instructions": ["Chop tomatoes", "Cook"],
            "tagIds": [dinner_id, quick_id],
            "note": "new note",
            "coverSelection": {"kind": "IMAGE", "imageId": source_image_id},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Better Soup"
    assert payload["sourceName"] == "THREADS"
    assert payload["authorName"] == "better_chef"
    assert payload["cookTimeMinutes"] == 35
    assert payload["nutritionEstimate"]["calories"] == 200
    assert payload["ingredients"][0]["name"] == "Tomato"
    assert payload["instructions"] == ["Chop tomatoes", "Cook"]
    assert [tag["name"] for tag in payload["tags"]] == ["dinner", "quick"]
    assert payload["coverImage"]["id"] == source_image_id
    assert [option["kind"] for option in payload["coverOptions"]] == ["DEFAULT", "IMAGE"]
    assert payload["coverOptions"][1]["label"] == "Current cover"
    assert payload["coverOptions"][1]["selected"] is True


def test_patch_recipe_rebuilds_search_text_when_search_fields_change():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    with SessionLocal() as session:
        recipe = session.query(Recipe).filter_by(id=recipe_id).one()
        recipe.search_text = "old"
        recipe.search_text_hash = "old-hash"
        session.commit()

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={
            "title": "Better Soup",
            "sourceName": "THREADS",
            "authorName": "thread_chef",
            "cookTimeMinutes": 45,
            "nutritionEstimate": {"calories": 150},
            "ingredients": [{"id": client.get(f"/recipes/{recipe_id}").json()["ingredients"][0]["id"], "name": "Filtered Water"}],
            "instructions": ["Simmer slowly"],
        },
    )

    assert response.status_code == 200
    with SessionLocal() as session:
        recipe = session.query(Recipe).filter_by(id=recipe_id).one()

    assert recipe.search_text_hash != "old-hash"
    assert "better soup" in recipe.search_text
    assert "threads" in recipe.search_text
    assert "thread_chef" in recipe.search_text
    assert "filtered water" in recipe.search_text
    assert "simmer slowly" in recipe.search_text
    assert "150" in recipe.search_text


def test_patch_recipe_updates_ingredients_by_id_creates_new_and_deletes_omitted():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    with SessionLocal() as session:
        recipe = session.query(Recipe).filter_by(id=recipe_id).one()
        existing_id = recipe.ingredients[0].id
        recipe.ingredients.append(Ingredient(name="Salt", quantity="1", unit="pinch", position=1))
        session.commit()
        omitted_id = recipe.ingredients[1].id

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={
            "ingredients": [
                {"id": existing_id, "name": "Filtered Water", "quantity": "2", "unit": "cups", "note": "warm"},
                {"name": "Pepper", "quantity": "1", "unit": "pinch", "note": None},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [ingredient["name"] for ingredient in payload["ingredients"]] == ["Filtered Water", "Pepper"]
    assert payload["ingredients"][0]["id"] == existing_id
    assert payload["ingredients"][0]["quantity"] == "2"
    assert payload["ingredients"][0]["unit"] == "cups"
    assert payload["ingredients"][0]["note"] == "warm"
    assert payload["ingredients"][1]["id"] != existing_id
    with SessionLocal() as session:
        ingredients = {ingredient.id: ingredient for ingredient in session.query(Ingredient).filter_by(recipe_id=recipe_id).all()}
    assert existing_id in ingredients
    assert omitted_id not in ingredients
    assert ingredients[existing_id].search_name == "filtered water"


def test_patch_recipe_rejects_invalid_deleted_or_foreign_tag_ids_without_auto_create():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    with SessionLocal() as session:
        user = ensure_default_user(session)
        deleted = Tag(owner_id=user.id, name="deleted")
        deleted.deleted_at = datetime.now(timezone.utc)
        other_user = User(id="other-user", email="other@example.test")
        foreign = Tag(owner_id=other_user.id, name="foreign")
        session.add_all([deleted, other_user, foreign])
        session.commit()
        deleted_id = deleted.id
        foreign_id = foreign.id

    for tag_ids in ([deleted_id], [foreign_id], ["missing-tag"]):
        response = client.patch(f"/recipes/{recipe_id}", json={"tagIds": tag_ids})

        assert response.status_code == 400
        assert response.json()["errorCode"] == "INVALID_TAG"

    legacy_response = client.patch(f"/recipes/{recipe_id}", json={"tags": ["new-freeform"]})

    assert legacy_response.status_code == 422
    with SessionLocal() as session:
        assert session.query(Tag).filter_by(name="new-freeform").first() is None


def test_delete_recipe_removes_it_from_list_and_detail():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.delete(f"/recipes/{recipe_id}")

    assert response.status_code == 204
    assert client.get(f"/recipes/{recipe_id}").status_code == 404
    assert client.get("/recipes").json()["items"] == []


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


def test_resolve_review_flag_succeeds_when_embedding_publish_fails(monkeypatch):
    client, SessionLocal = client_with_session()
    recipe_id, flag_id = seed_recipe(SessionLocal)
    monkeypatch.setattr(
        "app.services.recipes.enqueue_recipe_embedding",
        lambda recipe_id, owner_id: False,
        raising=False,
    )

    response = client.patch(f"/recipes/{recipe_id}/review-flags/{flag_id}", json={"status": "resolved"})

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    with SessionLocal() as session:
        recipe = session.get(Recipe, recipe_id)
        assert recipe is not None
        assert recipe.embedding is not None
        assert recipe.embedding.status is RecipeEmbeddingStatus.STALE
        assert [event.event_type for event in recipe.embedding.events] == [RecipeEmbeddingEventType.SCHEDULED]


def test_patch_recipe_source_status_marks_single_source_without_children():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        parent = RecipeResource(
            owner_id=user.id,
            type=SourceType.URL,
            source=RecipeResourceOrigin.MANUAL,
            role=RecipeResourceRole.SOURCE,
            url="https://example.test/post",
            position=0,
            status=RecipeResourceStatus.IGNORED,
        )
        child = RecipeResource(
            owner_id=user.id,
            type=SourceType.TEXT,
            source=RecipeResourceOrigin.URL,
            role=RecipeResourceRole.SOURCE,
            text="Soup recipe",
            position=1,
            status=RecipeResourceStatus.IGNORED,
        )
        child.parent = parent
        recipe.resources.extend([parent, child])
        session.add(recipe)
        session.commit()
        recipe_id = recipe.id
        parent_id = parent.id
        child_id = child.id

    response = client.patch(f"/recipes/{recipe_id}/sources/{parent_id}", json={"status": "used"})

    assert response.status_code == 200
    sources = {source["id"]: source for source in response.json()["sources"]}
    assert sources[parent_id]["status"] == "used"
    assert sources[child_id]["status"] == "ignored"


def test_delete_url_source_hides_children_but_keeps_current_cover_image_source():
    client, SessionLocal = client_with_session()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        source_image = RecipeImage(
            storage_key="url-image.jpg",
            original_name="url-image.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            position=0,
        )
        recipe.images.append(source_image)
        recipe.cover_image = source_image
        session.add(recipe)
        parent = RecipeResource(
            owner_id=user.id,
            type=SourceType.URL,
            source=RecipeResourceOrigin.MANUAL,
            role=RecipeResourceRole.SOURCE,
            url="https://example.test/post",
            position=0,
            status=RecipeResourceStatus.IGNORED,
        )
        text_child = RecipeResource(
            owner_id=user.id,
            type=SourceType.TEXT,
            source=RecipeResourceOrigin.URL,
            role=RecipeResourceRole.SOURCE,
            text="Soup recipe",
            position=1,
            status=RecipeResourceStatus.IGNORED,
        )
        image_child = RecipeResource(
            owner_id=user.id,
            type=SourceType.IMAGE,
            source=RecipeResourceOrigin.URL,
            role=RecipeResourceRole.SOURCE,
            image=source_image,
            position=2,
            status=RecipeResourceStatus.USED,
        )
        text_child.parent = parent
        image_child.parent = parent
        recipe.resources.extend([parent, text_child, image_child])
        session.commit()
        recipe_id = recipe.id
        parent_id = parent.id
        text_child_id = text_child.id
        image_child_id = image_child.id
        image_id = source_image.id

    response = client.patch(f"/recipes/{recipe_id}/sources/{parent_id}", json={"status": "deleted"})

    assert response.status_code == 200
    detail = response.json()
    assert detail["coverImage"]["id"] == image_id
    assert image_id in [option["image"]["id"] for option in detail["coverOptions"] if option["image"]]
    assert parent_id not in [source["id"] for source in detail["sources"]]
    assert text_child_id not in [source["id"] for source in detail["sources"]]
    assert image_child_id in [source["id"] for source in detail["sources"]]

    with SessionLocal() as session:
        rows = {resource.id: resource.status.value for resource in session.query(RecipeResource).all()}
    assert rows[parent_id] == "deleted"
    assert rows[text_child_id] == "deleted"
    assert rows[image_child_id] == "used"
