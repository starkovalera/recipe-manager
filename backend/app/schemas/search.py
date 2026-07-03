from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.base import CamelModel
from app.schemas.recipes import RecipeImageOut

SearchSuggestionType = Literal["tag", "ingredient_query", "source_name", "author_name", "title"]


class SearchSuggestionOut(CamelModel):
    type: SearchSuggestionType
    id: str | None = None
    recipe_id: str | None = None
    value: str | None = None
    label: str


class SearchSuggestionListOut(CamelModel):
    items: list[SearchSuggestionOut]


class SearchChipIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    type: SearchSuggestionType
    id: str | None = None
    recipe_id: str | None = None
    value: str | None = None


class SearchRequestIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    selected: list[SearchChipIn] = Field(default_factory=list)
    limit: int = Field(default=24, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MatchReasonOut(CamelModel):
    type: Literal["semantic", "filter"]
    label: str
    score: float | None = None


class SearchResultOut(CamelModel):
    id: str
    title: str
    note: str | None = None
    cover_image: RecipeImageOut | None = None
    has_open_review_flags: bool
    match_reasons: list[MatchReasonOut]


class SearchResponseOut(CamelModel):
    items: list[SearchResultOut]
    limit: int
    offset: int
    has_more: bool
