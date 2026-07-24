from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from app.media.access.constants import DownloadAccessMode, MediaItemErrorCode, MediaReferenceType
from app.schemas.base import CamelModel


class MediaReferenceIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    type: MediaReferenceType
    id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class MediaAccessRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MediaReferenceIn] = Field(min_length=1, max_length=100)


class DownloadGrantOut(CamelModel):
    url: str
    expires_at: datetime | None
    content_type: str
    # Describes browser retrieval mechanics only; it is not a provider or public/private classification.
    access_mode: DownloadAccessMode


class MediaAccessItemErrorOut(CamelModel):
    code: MediaItemErrorCode
    message: str


class MediaAccessItemOut(CamelModel):
    type: MediaReferenceType
    id: str
    grant: DownloadGrantOut | None = None
    error: MediaAccessItemErrorOut | None = None

    @model_validator(mode="after")
    def exactly_one_result(self):
        if (self.grant is None) == (self.error is None):
            raise ValueError("Media access item must contain exactly one of grant or error.")
        return self


class MediaAccessResponse(CamelModel):
    items: list[MediaAccessItemOut]
