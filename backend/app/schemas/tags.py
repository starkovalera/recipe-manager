from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import CamelModel
from app.schemas.pagination import PaginatedOutMixin


class TagOut(CamelModel):
    id: str
    name: str
    description: str | None = None
    deleted_at: datetime | None = None


class TagListOut(PaginatedOutMixin):
    items: list[TagOut]


class TagCreateIn(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None


class TagPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None


class TagUsageOut(CamelModel):
    recipe_count: int
