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
    Ingredient,
    RecipeImage,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceRole,
    RecipeResourceStatus,
    Recipe,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    SourceType,
    SourceName,
    Tag,
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
    assert detail["tags"] == ["quick"]
    assert detail["coverOptions"][0]["kind"] == "DEFAULT"
    assert detail["sources"][0]["status"] == "used"
    assert detail["reviewFlags"][0]["reasonCode"] == "LOW_CONFIDENCE"


def test_recipe_list_marks_only_open_review_flags():
    client, SessionLocal = client_with_session()
    recipe_id, flag_id = seed_recipe(SessionLocal)

    client.patch(f"/recipes/{recipe_id}/review-flags/{flag_id}", json={"status": "resolved"})

    response = client.get("/recipes")

    assert response.status_code == 200
    assert response.json()["items"][0]["hasOpenReviewFlags"] is False


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
        session.add(recipe)
        session.flush()
        recipe.cover_image_id = cover_image.id
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


def test_patch_recipe_trims_and_truncates_note():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)

    response = client.patch(f"/recipes/{recipe_id}", json={"note": " " + ("x" * 600) + " "})

    assert response.status_code == 200
    assert len(response.json()["note"]) == 500
    assert response.json()["note"] == "x" * 500


def test_patch_recipe_updates_full_editable_fields_and_cover():
    client, SessionLocal = client_with_session()
    recipe_id, _ = seed_recipe(SessionLocal)
    detail = client.get(f"/recipes/{recipe_id}").json()
    source_image_id = detail["images"][0]["id"]

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={
            "title": "Better Soup",
            "cookTimeMinutes": 35,
            "nutritionEstimate": {"calories": 200, "proteinGrams": 8, "fatGrams": 2, "carbsGrams": 30},
            "ingredients": [{"name": "Tomato", "quantity": "2", "unit": "pcs", "note": "ripe"}],
            "instructions": ["Chop tomatoes", "Cook"],
            "tags": ["dinner", "quick"],
            "note": "new note",
            "coverSelection": {"kind": "IMAGE", "imageId": source_image_id},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Better Soup"
    assert payload["cookTimeMinutes"] == 35
    assert payload["nutritionEstimate"]["calories"] == 200
    assert payload["ingredients"][0]["name"] == "Tomato"
    assert payload["instructions"] == ["Chop tomatoes", "Cook"]
    assert payload["tags"] == ["dinner", "quick"]
    assert payload["coverImage"]["id"] == source_image_id
    assert [option["kind"] for option in payload["coverOptions"]] == ["DEFAULT", "IMAGE"]
    assert payload["coverOptions"][1]["label"] == "Current cover"
    assert payload["coverOptions"][1]["selected"] is True


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
        session.add(recipe)
        session.flush()
        recipe.cover_image_id = source_image.id
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
            image_id=source_image.id,
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
