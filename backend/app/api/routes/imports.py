import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, Response, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep
from app.core.logging import bind_logger
from app.core.security import client_id_from_header
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.jobs import create_import_job, get_import_job
from app.imports.tasks import import_recipe_task
from app.models import ImportJob, ImportJobStatus
from app.schemas.imports import ImportJobOut

router = APIRouter(prefix="/imports", tags=["imports"])
logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def enqueue_import_job(import_job_id: str) -> None:
    import_recipe_task.send(import_job_id)


@router.post("", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_import(
    response: Response,
    client_import_id: Annotated[str, Form(alias="clientImportId")],
    session: SessionDep,
    current_user: CurrentUserDep,
    files: Annotated[list[UploadFile], File(default_factory=list)],
    text: Annotated[str | None, Form()] = None,
    url: Annotated[str | None, Form()] = None,
    x_client_id: Annotated[str | None, Header(alias="X-Client-Id")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ImportJob:
    result = create_import_job(
        session=session,
        owner_id=current_user.id,
        client_id=client_id_from_header(x_client_id),
        client_import_id=client_import_id.strip()[:128],
        text=text,
        url=url,
        files=files,
        idempotency_key=idempotency_key,
    )
    job = result.job
    if result.was_created and job.status == ImportJobStatus.QUEUED:
        enqueue_import_job(job.id)
        bind_logger(
            logger,
            component=IMPORT_LOG_COMPONENT,
            ownerId=current_user.id,
            importJobId=job.id,
            clientId=client_id_from_header(x_client_id),
        ).info(f"{IMPORT_LOG_COMPONENT} Import job enqueued")
    elif not result.was_created:
        response.status_code = status.HTTP_200_OK
    return job


@router.get("/{job_id}", response_model=ImportJobOut)
def poll_import(job_id: str, session: SessionDep, current_user: CurrentUserDep) -> ImportJob:
    return get_import_job(session, job_id, current_user.id)
