from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from sqlalchemy.orm import Session

from app.core.security import client_id_from_header
from app.db.session import get_session
from app.imports.jobs import create_import_job, get_import_job, serialize_import_job
from app.schemas.imports import ImportJobOut

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportJobOut)
def create_import(
    clientImportId: str = Form(...),
    text: str | None = Form(None),
    url: str | None = Form(None),
    files: list[UploadFile] = File(default_factory=list),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    session: Session = Depends(get_session),
) -> ImportJobOut:
    job = create_import_job(
        session=session,
        client_id=client_id_from_header(x_client_id),
        client_import_id=clientImportId.strip()[:128],
        text=text,
        url=url,
        files=files,
    )
    return serialize_import_job(job)


@router.get("/{job_id}", response_model=ImportJobOut)
def poll_import(job_id: str, session: Session = Depends(get_session)) -> ImportJobOut:
    return serialize_import_job(get_import_job(session, job_id))
