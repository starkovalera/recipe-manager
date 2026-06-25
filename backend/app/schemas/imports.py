from datetime import datetime

from pydantic import BaseModel


class ImportJobOut(BaseModel):
    jobId: str
    status: str
    createdRecipeId: str | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    createdAt: datetime | None = None
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
