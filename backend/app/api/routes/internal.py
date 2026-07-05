from fastapi import APIRouter

from app.api.deps import CurrentAdminUserDep, SessionDep
from app.core.errors import ApiError, ErrorCode
from app.embeddings.diagnostics import list_internal_recipe_embeddings
from app.embeddings.queries import get_recipe_embedding_with_recipe
from app.embeddings.service import retry_recipe_embedding
from app.imports.queries import list_internal_import_jobs
from app.models import ImportJob, RecipeEmbedding
from app.schemas.internal import InternalImportJobListOut, InternalRecipeEmbeddingListOut
from app.schemas.recipes import RecipeEmbeddingOut
from app.schemas.search import EmbeddingInputPreviewOut, SearchExplainResponseOut, SearchRequestIn
from app.services.search import explain_search, get_embedding_input_preview

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/import-jobs", response_model=InternalImportJobListOut)
def get_internal_import_jobs(session: SessionDep, _current_user: CurrentAdminUserDep) -> dict[str, list[ImportJob]]:
    return {"items": list_internal_import_jobs(session)}


@router.get("/embeddings", response_model=InternalRecipeEmbeddingListOut)
def get_internal_recipe_embeddings(session: SessionDep, _current_user: CurrentAdminUserDep) -> dict[str, list[RecipeEmbedding]]:
    return {"items": list_internal_recipe_embeddings(session)}


@router.post("/embeddings/{recipe_id}/retry", response_model=RecipeEmbeddingOut)
def retry_internal_recipe_embedding(recipe_id: str, session: SessionDep, _current_user: CurrentAdminUserDep) -> RecipeEmbedding:
    embedding = get_recipe_embedding_with_recipe(session, recipe_id)
    if embedding is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe embedding not found.", status_code=404)
    return retry_recipe_embedding(session, recipe_id, embedding.recipe.owner_id)


@router.post("/search/explain", response_model=SearchExplainResponseOut)
def explain_internal_search(request: SearchRequestIn, session: SessionDep, current_user: CurrentAdminUserDep) -> SearchExplainResponseOut:
    return explain_search(session, current_user.id, request)


@router.get("/recipes/{recipe_id}/embedding-input", response_model=EmbeddingInputPreviewOut)
def get_internal_recipe_embedding_input(recipe_id: str, session: SessionDep, _current_user: CurrentAdminUserDep) -> EmbeddingInputPreviewOut:
    return get_embedding_input_preview(session, recipe_id)
