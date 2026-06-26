from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.init import DEFAULT_USER_ID, ensure_default_user
from app.models import (
    ImportJob,
    ImportJobStatus,
    Ingredient,
    Recipe,
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
    recipe.ingredients.append(Ingredient(name="Pasta", quantity="200", unit="g", position=0))
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
    job = ImportJob(owner_id=user.id, client_id="client-1", client_import_id="import-1", status=ImportJobStatus.SUCCEEDED)
    recipe.import_jobs.append(job)
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
