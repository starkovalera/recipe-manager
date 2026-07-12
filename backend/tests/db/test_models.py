from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.constants import UserRole
from app.db.base import Base
from app.db.defaults import DEFAULT_RECIPE_LANGUAGE, DEFAULT_TAG_NAMES, DEFAULT_USER_ID
from app.db.init import ensure_default_user
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobErrorCode,
    ImportJobStatus,
    Ingredient,
    JobEvent,
    Notification,
    NotificationEntityType,
    NotificationType,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEvent,
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
    UserRoleAssignment,
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
    assert first.roles == {UserRole.DEBUG, UserRole.SUPERADMIN}


def test_default_user_roles_are_not_restored_after_revocation():
    session = create_session()
    user = ensure_default_user(session)
    assignment = session.get(UserRoleAssignment, (user.id, UserRole.DEBUG))
    session.delete(assignment)
    session.commit()

    user = ensure_default_user(session)

    assert user.roles == {UserRole.SUPERADMIN}


def test_user_supports_multiple_unique_role_assignments():
    session = create_session()
    account = ensure_default_user(session)

    assert account.roles == {UserRole.DEBUG, UserRole.SUPERADMIN}
    session.expunge_all()
    session.add(UserRoleAssignment(user_id=account.id, role=UserRole.DEBUG))
    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_deletes_role_assignments():
    session = create_session()
    account = ensure_default_user(session)
    session.delete(account)
    session.commit()

    assert session.query(UserRoleAssignment).count() == 0


def test_ensure_default_user_does_not_leave_an_implicit_transaction_open():
    session = create_session()

    ensure_default_user(session)

    assert session.in_transaction() is False


def test_import_job_error_codes_do_not_include_creation_failures():
    assert "IMPORT_CREATION_FAILED" not in {error_code.value for error_code in ImportJobErrorCode}


def test_import_job_starts_next_attempt_and_clears_previous_result_fields():
    job = ImportJob(
        owner_id="owner-1",
        client_id="client-1",
        status=ImportJobStatus.QUEUED,
        attempt_count=1,
        error_code=ImportJobErrorCode.IMPORT_FAILED,
        error_message="UNEXPECTED_ERROR",
        created_recipe_id="recipe-1",
        finished_at=datetime.now(timezone.utc),
    )

    job.set_running()

    assert job.status == ImportJobStatus.RUNNING
    assert job.attempt_count == 2
    assert job.error_code is None
    assert job.error_message is None
    assert job.created_recipe_id is None
    assert job.finished_at is None
    assert job.started_at is not None


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
    recipe.cover_image = cover
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
            type=NotificationType.IMPORT_SUCCEEDED,
            title="Import completed",
            message="Recipe imported.",
            entity_type=NotificationEntityType.RECIPE,
            entity_id="recipe-1",
        )
    )
    session.add(recipe)
    session.commit()

    saved = session.query(Recipe).filter_by(title="Tomato Pasta").one()

    assert saved.owner.id == DEFAULT_USER_ID
    assert saved.ingredients[0].name == "Pasta"
    assert saved.tags[0].name == "dinner"
    assert saved.images[0].storage_key == "dev/source.jpg"
    assert saved.resources[0].status is RecipeResourceStatus.USED
    assert saved.resources[1].source is RecipeResourceOrigin.GENERATED
    assert saved.resources[1].role is RecipeResourceRole.COVER_CANDIDATE
    assert saved.cover_image is saved.resources[1].image
    assert saved.cover_image_id == saved.cover_image.id
    assert saved.review_flags[0].reason_code == "LOW_CONFIDENCE"
    assert saved.import_jobs[0].client_import_id == "import-1"
    assert saved.import_jobs[0].dedupe_key == "import-1"
    assert saved.import_jobs[0].events[0].event_type == ImportEventType.IMPORT_CREATED
    assert saved.owner.notifications[0].type == NotificationType.IMPORT_SUCCEEDED


def test_recipe_cover_image_is_nullable_relationship():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    session.add(recipe)
    session.commit()

    saved = session.get(Recipe, recipe.id)

    assert saved is not None
    assert saved.cover_image is None


def test_deleting_recipe_with_cover_image_deletes_image_graph():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    cover_image = RecipeImage(
        storage_key="dev/cover.jpg",
        original_name="cover.jpg",
        mime_type="image/jpeg",
        size_bytes=64,
        position=0,
    )
    recipe.images.append(cover_image)
    recipe.cover_image = cover_image
    session.add(recipe)
    session.commit()
    recipe_id = recipe.id
    cover_image_id = cover_image.id

    session.delete(recipe)
    session.commit()

    assert session.get(Recipe, recipe_id) is None
    assert session.get(RecipeImage, cover_image_id) is None


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


def test_recipe_embedding_lifecycle_enum_names_match_values():
    assert {status.name: status.value for status in RecipeEmbeddingStatus} == {
        "STALE": "STALE",
        "RUNNING": "RUNNING",
        "READY": "READY",
        "FAILED": "FAILED",
        "SKIPPED_DUE_TO_FLAGS": "SKIPPED_DUE_TO_FLAGS",
    }
    assert {event_type.name: event_type.value for event_type in RecipeEmbeddingEventType} == {
        "SCHEDULED": "SCHEDULED",
        "ENQUEUED": "ENQUEUED",
        "STARTED": "STARTED",
        "SKIPPED_DUE_TO_FLAGS": "SKIPPED_DUE_TO_FLAGS",
        "ALREADY_READY": "ALREADY_READY",
        "PROVIDER_SUCCEEDED": "PROVIDER_SUCCEEDED",
        "SAVED": "SAVED",
        "STALE_REQUEUED": "STALE_REQUEUED",
        "FAILED": "FAILED",
        "RETRY_REQUESTED": "RETRY_REQUESTED",
    }


def test_recipe_embedding_is_one_to_optional_one():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    session.add(recipe)
    session.commit()

    embedding = RecipeEmbedding(
        recipe_id=recipe.id,
        model="test-embedding",
        status=RecipeEmbeddingStatus.STALE,
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
                status=RecipeEmbeddingStatus.STALE,
            )
        )
        session.commit()


def test_deleting_recipe_deletes_embedding_row():
    session = create_session()
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Toast", instructions=["Toast bread"])
    recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.READY)
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
    recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.STALE)
    session.add(recipe)
    session.flush()
    event = RecipeEmbeddingEvent(
        recipe_id=recipe.id,
        owner_id=user.id,
        event_type=RecipeEmbeddingEventType.SCHEDULED,
        status_after=RecipeEmbeddingStatus.STALE,
        payload={"reason": "test"},
    )
    recipe.embedding.events.append(event)
    session.commit()
    event_id = event.id

    saved = session.get(RecipeEmbedding, recipe.id)
    assert saved is not None
    assert saved.status is RecipeEmbeddingStatus.STALE
    assert saved.events[0].id == event_id
    assert saved.events[0].event_type is RecipeEmbeddingEventType.SCHEDULED
    assert saved.events[0].status_after is RecipeEmbeddingStatus.STALE
    assert saved.events[0].payload == {"reason": "test"}

    session.delete(recipe)
    session.commit()

    assert session.get(RecipeEmbeddingEvent, event_id) is None
