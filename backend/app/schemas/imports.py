from datetime import datetime

from pydantic import Field

from app.core.config import get_settings
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
    attempt_count: int
    max_attempts: int = Field(default_factory=lambda: get_settings().max_import_attempts)
