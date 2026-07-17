import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, Response, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.core.errors import ImportRetryFailedError
from app.core.logging import bind_logger
from app.core.security import client_id_from_header
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.jobs import (
    compensate_import_retry_publish_failure,
    create_import_job,
    get_import_job,
    request_import_retry,
)
from app.models import ImportJob
from app.queueing.outbox import dispatch_outbox_message
from app.queueing.provider import get_queue_publisher
from app.schemas.imports import ImportJobOut

router = APIRouter(prefix="/imports", tags=["imports"])
logger = logging.getLogger(IMPORT_LOG_COMPONENT)


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
    if result.outbox_message_id is not None:
        published = dispatch_outbox_message(result.outbox_message_id)
        log = bind_logger(
            logger,
            component=IMPORT_LOG_COMPONENT,
            owner_id=current_user.id,
            import_job_id=job.id,
            client_id=client_id_from_header(x_client_id),
        )
        if published:
            log.info(f"{IMPORT_LOG_COMPONENT} Import job enqueued")
        else:
            log.info(f"{IMPORT_LOG_COMPONENT} Import job is pending outbox recovery")
    elif not result.was_created:
        response.status_code = status.HTTP_200_OK
    return job


@router.get("/{job_id}", response_model=ImportJobOut)
def poll_import(job_id: str, session: SessionDep, current_user: CurrentUserDep) -> ImportJob:
    return get_import_job(session, job_id, current_user.id)


@router.post("/{job_id}/retry", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
def retry_import(
    job_id: str,
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> ImportJob:
    result = request_import_retry(
        session,
        job_id=job_id,
        owner_id=current_user.id,
        max_import_attempts=settings.max_import_attempts,
        max_parallel_imports=settings.max_parallel_imports_per_client,
    )
    try:
        get_queue_publisher().publish_import_job(job_id)
    except Exception as error:
        job, reverted = compensate_import_retry_publish_failure(
            session,
            job_id=job_id,
            owner_id=current_user.id,
            notification_id=result.notification_id,
        )
        log = bind_logger(
            logger,
            component=IMPORT_LOG_COMPONENT,
            owner_id=current_user.id,
            import_job_id=job_id,
        )
        if reverted:
            log.error(f"{IMPORT_LOG_COMPONENT} Import retry enqueue failed", error=repr(error))
            raise ImportRetryFailedError() from error
        log.info(f"{IMPORT_LOG_COMPONENT} Import retry enqueue result is ambiguous", error=repr(error))
        response.status_code = status.HTTP_200_OK
        return job
    return result.job
