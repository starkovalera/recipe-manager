import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.defaults import DEFAULT_RECIPE_LANGUAGE, DEFAULT_TAG_NAMES, DEFAULT_USER_ID
from app.db.init import ensure_default_user
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobStatus,
    Ingredient,
    JobEvent,
    Notification,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEvent,
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
    UserSettings,
)


def create_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_ensure_default_user_is_idempotent():
    session = create_session()

    first = ensure_default_user(session)
    second = ensure_default_user(session)

    assert first.id == DEFAULT_USER_ID
    assert second.id == DEFAULT_USER_ID
    assert session.query(type(first)).count() == 1


def test_ensure_default_user_creates_settings_and_default_tags_idempotently():
    session = create_session()

    user = ensure_default_user(session, recipe_language="en")
    ensure_default_user(session, recipe_language="en")

    settings = session.get(UserSettings, user.id)
    tag_names = [tag.name for tag in session.query(Tag).filter_by(owner_id=user.id).order_by(Tag.name).all()]

    assert settings is not None
    assert DEFAULT_RECIPE_LANGUAGE == "ru"
    assert settings.recipe_language == "en"
    assert sorted(tag_names) == sorted(DEFAULT_TAG_NAMES)
    assert {"аэрогриль", "духовка", "мороженое"}.issubset(set(tag_names))
    assert session.query(Tag).filter_by(owner_id=user.id).count() == len(DEFAULT_TAG_NAMES)


def test_recipe_graph_persists_core_import_entities():
    session = create_session()
    user = ensure_default_user(session)
    tag = Tag(owner_id=user.id, name="dinner")
    recipe = Recipe(
        owner_id=user.id,
        title="Tomato Pasta",
        source_name=SourceName.OTHER,
        instructions=["Boil pasta", "Add sauce"],
        nutrition_estimate={"calories": 500},
        tags=[tag],
    )
    recipe.ingredients.append(Ingredient(name="Pasta", search_name="pasta", quantity="200", unit="g", position=0))
    image = RecipeImage(
        storage_key="dev/source.jpg",
        original_name="source.jpg",
        mime_type="image/jpeg",
        size_bytes=128,
        position=0,
    )
    recipe.images.append(image)
    recipe.resources.append(
        RecipeResource(
            owner_id=user.id,
            type=SourceType.IMAGE,
            source=RecipeResourceOrigin.MANUAL,
            role=RecipeResourceRole.SOURCE,
            image=image,
            position=0,
            status=RecipeResourceStatus.USED,
            assessment_reason="Selected as primary evidence by AI.",
            assessment_confidence=0.9,
        )
    )
    cover = RecipeImage(
        storage_key="dev/cover.jpg",
        original_name="cover.jpg",
        mime_type="image/jpeg",
        size_bytes=64,
        position=1,
    )
    recipe.images.append(cover)
    recipe.resources.append(
        RecipeResource(
            owner_id=user.id,
            type=SourceType.IMAGE,
            source=RecipeResourceOrigin.GENERATED,
            role=RecipeResourceRole.COVER_CANDIDATE,
            image=cover,
            position=1,
            status=RecipeResourceStatus.USED,
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
    job = ImportJob(
        owner_id=user.id,
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="import-1",
        status=ImportJobStatus.SUCCEEDED,
    )
    job.events.append(JobEvent(event_type=ImportEventType.IMPORT_CREATED, payload={"clientImportId": "import-1"}))
    recipe.import_jobs.append(job)
    user.notifications.append(
        Notification(
            type="import_succeeded",
            title="Import completed",
            message="Recipe imported.",
            entity_type="recipe",
            entity_id="recipe-1",
        )
    )
    session.add(recipe)
    session.flush()
    recipe.cover_image_id = cover.id
    session.commit()

    saved = session.query(Recipe).filter_by(title="Tomato Pasta").one()

    assert saved.owner.id == DEFAULT_USER_ID
    assert saved.ingredients[0].name == "Pasta"
    assert saved.tags[0].name == "dinner"
    assert saved.images[0].storage_key == "dev/source.jpg"
    assert saved.resources[0].status is RecipeResourceStatus.USED
    assert saved.resources[1].source is RecipeResourceOrigin.GENERATED
    assert saved.resources[1].role is RecipeResourceRole.COVER_CANDIDATE
    assert saved.cover_image_id == saved.resources[1].image_id
    assert saved.review_flags[0].reason_code == "LOW_CONFIDENCE"
    assert saved.import_jobs[0].client_import_id == "import-1"
    assert saved.import_jobs[0].dedupe_key == "import-1"
    assert saved.import_jobs[0].events[0].event_type == ImportEventType.IMPORT_CREATED
    assert saved.owner.notifications[0].type == "import_succeeded"


def test_ingredient_persists_search_name():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    recipe.ingredients.append(Ingredient(name="  Fresh   Bread  ", search_name="fresh bread", position=0))
    session.add(recipe)
    session.commit()

    saved = session.query(Ingredient).one()

    assert saved.search_name == "fresh bread"


def test_recipe_can_exist_without_embedding_row():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    session.add(recipe)
    session.commit()

    saved = session.get(Recipe, recipe.id)

    assert saved is not None
    assert saved.embedding is None


def test_recipe_embedding_is_one_to_optional_one():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    session.add(recipe)
    session.commit()

    embedding = RecipeEmbedding(
        recipe_id=recipe.id,
        model="test-embedding",
        status=RecipeEmbeddingStatus.STALE.value,
    )
    session.add(embedding)
    session.commit()
    session.refresh(recipe)

    assert recipe.embedding is not None
    assert recipe.embedding.recipe_id == recipe.id

    with pytest.raises(IntegrityError):
        session.execute(
            insert(RecipeEmbedding).values(
                recipe_id=recipe.id,
                model="test-embedding",
                status=RecipeEmbeddingStatus.STALE.value,
            )
        )
        session.commit()


def test_deleting_recipe_deletes_embedding_row():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.READY.value)
    session.add(recipe)
    session.commit()
    recipe_id = recipe.id

    session.delete(recipe)
    session.commit()

    assert session.get(RecipeEmbedding, recipe_id) is None


def test_recipe_embedding_event_belongs_to_embedding_and_cascades_with_recipe():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.STALE.value)
    session.add(recipe)
    session.flush()
    event = RecipeEmbeddingEvent(
        recipe_id=recipe.id,
        owner_id=user.id,
        event_type="scheduled",
        status_after=RecipeEmbeddingStatus.STALE.value,
        payload={"reason": "test"},
    )
    recipe.embedding.events.append(event)
    session.commit()
    event_id = event.id

    saved = session.get(RecipeEmbedding, recipe.id)
    assert saved is not None
    assert saved.events[0].id == event_id
    assert saved.events[0].payload == {"reason": "test"}

    session.delete(recipe)
    session.commit()

    assert session.get(RecipeEmbeddingEvent, event_id) is None
