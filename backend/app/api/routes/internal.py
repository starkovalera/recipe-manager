from fastapi import APIRouter

from app.api.deps import SessionDep
from app.imports.queries import list_internal_import_jobs
from app.models import ImportJob
from app.schemas.internal import InternalImportJobListOut

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/import-jobs", response_model=InternalImportJobListOut)
def get_internal_import_jobs(session: SessionDep) -> dict[str, list[ImportJob]]:
    return {"items": list_internal_import_jobs(session)}
