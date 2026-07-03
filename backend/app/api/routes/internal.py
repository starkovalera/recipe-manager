from fastapi import APIRouter

from app.api.deps import SessionDep
from app.embeddings.diagnostics import list_internal_recipe_embeddings
from app.imports.queries import list_internal_import_jobs
from app.models import ImportJob, RecipeEmbedding
from app.schemas.internal import InternalImportJobListOut, InternalRecipeEmbeddingListOut

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/import-jobs", response_model=InternalImportJobListOut)
def get_internal_import_jobs(session: SessionDep) -> dict[str, list[ImportJob]]:
    return {"items": list_internal_import_jobs(session)}


@router.get("/embeddings", response_model=InternalRecipeEmbeddingListOut)
def get_internal_recipe_embeddings(session: SessionDep) -> dict[str, list[RecipeEmbedding]]:
    return {"items": list_internal_recipe_embeddings(session)}
