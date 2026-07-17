import logging

from fastapi import APIRouter, Response, status

from app.access.constants import ADMIN_PAGE_ROLES, UserRole
from app.access.rules import can_retry_embedding, can_retry_import, get_owner_id, require_any_role
from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.core.errors import ImportNotFoundError, ImportRetryFailedError, RecipeEmbeddingNotFoundError
from app.core.logging import bind_logger
from app.db.session import db_transaction
from app.embeddings.queries import get_recipe_embedding_with_recipe, list_internal_recipe_embeddings
from app.embeddings.service import retry_recipe_embedding
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.jobs import compensate_import_retry_publish_failure, request_import_retry
from app.imports.queries import get_import_job_unscoped, list_internal_import_jobs
from app.models import ImportJob, RecipeEmbedding
from app.queueing.provider import get_queue_publisher
from app.schemas.imports import ImportJobOut
from app.schemas.internal import InternalImportJobListOut, InternalRecipeEmbeddingListOut
from app.schemas.recipes import RecipeEmbeddingOut
from app.schemas.search import SearchExplainResponseOut, SearchRequestIn
from app.services.search import explain_search

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(IMPORT_LOG_COMPONENT)


@router.get("/import-jobs", response_model=InternalImportJobListOut)
def get_internal_import_jobs(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[ImportJob]]:
    require_any_role(current_user, ADMIN_PAGE_ROLES)
    owner_id = get_owner_id(current_user, allow_all=[UserRole.SUPERADMIN])
    return {"items": list_internal_import_jobs(session, owner_id=owner_id)}


@router.get("/embeddings", response_model=InternalRecipeEmbeddingListOut)
def get_internal_recipe_embeddings(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[RecipeEmbedding]]:
    require_any_role(current_user, ADMIN_PAGE_ROLES)
    owner_id = get_owner_id(current_user, allow_all=[UserRole.SUPERADMIN])
    return {"items": list_internal_recipe_embeddings(session, owner_id=owner_id)}


@router.post("/import-jobs/{job_id}/retry", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
def retry_internal_import_job(
    job_id: str,
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> ImportJob:
    require_any_role(current_user, ADMIN_PAGE_ROLES)
    with db_transaction(session):
        job = get_import_job_unscoped(session, job_id)
        if job is None or not can_retry_import(current_user, job):
            raise ImportNotFoundError()
        owner_id = job.owner_id
    result = request_import_retry(
        session,
        job_id=job_id,
        owner_id=owner_id,
        max_import_attempts=settings.max_import_attempts,
        max_parallel_imports=settings.max_parallel_imports_per_client,
    )
    try:
        get_queue_publisher().publish_import_job(job_id)
    except Exception as error:
        reverted_job, reverted = compensate_import_retry_publish_failure(
            session,
            job_id=job_id,
            owner_id=owner_id,
            notification_id=result.notification_id,
        )
        log = bind_logger(logger, component=IMPORT_LOG_COMPONENT, owner_id=owner_id, import_job_id=job_id)
        if reverted:
            log.error(f"{IMPORT_LOG_COMPONENT} Import retry enqueue failed", error=repr(error))
            raise ImportRetryFailedError() from error
        log.info(f"{IMPORT_LOG_COMPONENT} Import retry enqueue result is ambiguous", error=repr(error))
        response.status_code = status.HTTP_200_OK
        return reverted_job
    return result.job


@router.post("/embeddings/{recipe_id}/retry", response_model=RecipeEmbeddingOut)
def retry_internal_recipe_embedding(recipe_id: str, session: SessionDep, current_user: CurrentUserDep) -> RecipeEmbedding:
    require_any_role(current_user, ADMIN_PAGE_ROLES)
    embedding = get_recipe_embedding_with_recipe(session, recipe_id)
    if embedding is None or not can_retry_embedding(current_user, embedding):
        raise RecipeEmbeddingNotFoundError()
    return retry_recipe_embedding(session, recipe_id, embedding.recipe.owner_id)


@router.post("/search/explain", response_model=SearchExplainResponseOut)
def explain_internal_search(request: SearchRequestIn, session: SessionDep, current_user: CurrentUserDep) -> SearchExplainResponseOut:
    require_any_role(current_user, ADMIN_PAGE_ROLES)
    owner_id = get_owner_id(current_user, allow_all=[UserRole.SUPERADMIN])
    return explain_search(session, owner_id, request, current_user_id=current_user.id)
