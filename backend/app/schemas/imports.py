from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class ImportJobOut(CamelModel):
    job_id: str = Field(validation_alias="id")
    status: str
    created_recipe_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
