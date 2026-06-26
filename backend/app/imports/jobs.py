from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.schemas import ReadySource, ready_source_id
from app.core.errors import ApiError, ErrorCode
from app.db.init import ensure_default_user
from app.imports.sources import source_assessments
from app.imports.sources import review_reason_codes, should_create_review_flag
from app.core.config import get_settings
from app.models import (
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    ImportSourceStatus,
    Ingredient,
    Recipe,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    RecipeSource,
    RecipeSourceStatus,
    SourceType,
)
from app.schemas.imports import ImportJobOut


def serialize_import_job(job: ImportJob) -> ImportJobOut:
    return ImportJobOut(
        jobId=job.id,
        status=job.status.value,
        createdRecipeId=job.created_recipe_id,
        errorCode=job.error_code,
        errorMessage=job.error_message,
        createdAt=job.created_at,
        startedAt=job.started_at,
        finishedAt=job.finished_at,
    )


def create_import_job(session: Session, client_id: str, client_import_id: str, text: str | None, url: str | None) -> ImportJob:
    normalized_text = text.strip() if text else None
    normalized_url = url.strip() if url else None
    if not normalized_text and not normalized_url:
        raise ApiError(ErrorCode.NOT_A_RECIPE, "Add a recipe URL, upload at least one recipe image, or add recipe text.")

    user = ensure_default_user(session)
    existing = session.scalar(select(ImportJob).where(ImportJob.owner_id == user.id, ImportJob.client_import_id == client_import_id))
    if existing is not None:
        return existing

    job = ImportJob(owner_id=user.id, client_id=client_id, client_import_id=client_import_id, status=ImportJobStatus.PENDING)
    position = 0
    if normalized_text:
        job.sources.append(ImportJobSource(type=SourceType.TEXT, status=ImportSourceStatus.READY, text=normalized_text, position=position))
        position += 1
    if normalized_url:
        job.sources.append(ImportJobSource(type=SourceType.URL, status=ImportSourceStatus.READY, url=normalized_url, position=position))
    session.add(job)
    session.commit()
    session.refresh(job)
    process_import_job(session, job.id)
    return session.get(ImportJob, job.id)


def process_import_job(session: Session, job_id: str) -> None:
    job = session.get(ImportJob, job_id)
    if job is None or job.status == ImportJobStatus.SUCCEEDED:
        return
    job.status = ImportJobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    session.commit()

    ready_sources: list[ReadySource] = []
    for source in job.sources:
        if source.type == SourceType.TEXT and source.text:
            ready_sources.append(ReadySource(type="TEXT", text=source.text, position=source.position))
        elif source.type == SourceType.URL and source.url:
            ready_sources.append(ReadySource(type="URL", url=source.url, text=source.url, position=source.position))

    provider = FakeRecipeExtractionProvider()
    import anyio

    result = anyio.run(provider.extract, ready_sources)
    if result.not_a_recipe or result.recipe is None:
        job.status = ImportJobStatus.FAILED
        job.error_code = ErrorCode.NOT_A_RECIPE.value
        job.error_message = "The provided sources do not contain a recipe."
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        return

    recipe_result = result.recipe
    recipe = Recipe(
        owner_id=job.owner_id,
        title=recipe_result.title,
        instructions=recipe_result.instructions,
        servings=recipe_result.servings,
        cook_time_minutes=recipe_result.cookTimeMinutes,
        nutrition_estimate=recipe_result.nutritionEstimate.model_dump() if recipe_result.nutritionEstimate else None,
        author_name=recipe_result.authorName,
    )
    for index, ingredient in enumerate(recipe_result.ingredients):
        recipe.ingredients.append(
            Ingredient(
                name=ingredient.name,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                position=index,
            )
        )
    assessments = source_assessments([ready_source_id(source) for source in ready_sources], recipe_result.quality)
    for source in ready_sources:
        source_id = ready_source_id(source)
        assessment = assessments[source_id]
        recipe.sources.append(
            RecipeSource(
                owner_id=job.owner_id,
                type=SourceType[source.type],
                url=source.url,
                text=source.text,
                source_ref=source_id,
                position=source.position,
                status=RecipeSourceStatus(assessment.status),
                assessment_reason=assessment.reason,
                assessment_confidence=assessment.confidence,
            )
        )
    warn_confidence = get_settings().import_warn_confidence
    reasons = review_reason_codes(recipe_result.quality, warn_confidence)
    if should_create_review_flag(recipe_result.quality, warn_confidence):
        recipe.review_flags.append(
            RecipeReviewFlag(
                owner_id=job.owner_id,
                type=RecipeReviewFlagType.CONTENT_WARNING,
                status=RecipeReviewFlagStatus.OPEN,
                reason_code=",".join(reasons),
                message=f"Review suggested: {', '.join(reasons)}.",
                details={**recipe_result.quality.model_dump(), "reasons": reasons},
            )
        )
    session.add(recipe)
    session.flush()
    job.created_recipe_id = recipe.id
    job.status = ImportJobStatus.SUCCEEDED
    job.finished_at = datetime.now(timezone.utc)
    session.commit()


def get_import_job(session: Session, job_id: str) -> ImportJob:
    job = session.get(ImportJob, job_id)
    if job is None:
        raise ApiError(ErrorCode.IMPORT_NOT_FOUND, "Import job not found.", status_code=404)
    return job
