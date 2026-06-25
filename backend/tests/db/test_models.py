from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.init import DEFAULT_USER_ID, ensure_default_user
from app.models import (
    CoverImageSource,
    ImportJob,
    ImportJobStatus,
    Ingredient,
    Recipe,
    RecipeImage,
    RecipeImageRole,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    RecipeSource,
    RecipeSourceStatus,
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
        cover_image_source=CoverImageSource.AI,
        instructions=["Boil pasta", "Add sauce"],
        nutrition_estimate={"calories": 500},
        tags=[tag],
    )
    recipe.ingredients.append(Ingredient(name="Pasta", quantity="200", unit="g", position=0))
    image = RecipeImage(
        role=RecipeImageRole.SOURCE,
        storage_key="dev/source.jpg",
        original_name="source.jpg",
        mime_type="image/jpeg",
        size_bytes=128,
        position=0,
    )
    recipe.images.append(image)
    recipe.sources.append(
        RecipeSource(
            owner_id=user.id,
            type=SourceType.IMAGE,
            image=image,
            source_ref="upload_0",
            position=0,
            status=RecipeSourceStatus.USED,
            assessment_reason="Selected as primary evidence by AI.",
            assessment_confidence=0.9,
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
    session.commit()

    saved = session.query(Recipe).filter_by(title="Tomato Pasta").one()

    assert saved.owner.id == DEFAULT_USER_ID
    assert saved.ingredients[0].name == "Pasta"
    assert saved.tags[0].name == "dinner"
    assert saved.images[0].storage_key == "dev/source.jpg"
    assert saved.sources[0].status is RecipeSourceStatus.USED
    assert saved.review_flags[0].reason_code == "LOW_CONFIDENCE"
    assert saved.import_jobs[0].client_import_id == "import-1"
