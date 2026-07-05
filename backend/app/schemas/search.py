from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.base import CamelModel
from app.schemas.recipes import RecipeImageOut

SearchSuggestionType = Literal["tag", "ingredient_query", "source_name", "author_name", "title"]
MatchReasonType = Literal["semantic", "filter", "tag", "ingredient_query", "source_name", "author_name", "title"]


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
    label: str | None = None


class SearchRequestIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    selected: list[SearchChipIn] = Field(default_factory=list)
    limit: int = Field(default=24, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MatchReasonOut(CamelModel):
    type: MatchReasonType
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


class SearchExplainFiltersOut(CamelModel):
    tag_id: str | None = None
    ingredient_queries: list[str]
    source_name: str | None = None
    author_name: str | None = None
    title_recipe_id: str | None = None


class SearchExplainDebugOut(CamelModel):
    rank: int | None = None
    distance: float | None = None
    similarity: float | None = None
    embedding_status: str | None = None
    embedding_model: str | None = None
    input_hash: str | None = None
    embedding_input_preview: str | None = None


class SearchExplainResultOut(SearchResultOut):
    debug: SearchExplainDebugOut


class SearchExplainResponseOut(CamelModel):
    text_present: bool
    filters: SearchExplainFiltersOut
    provider: str | None = None
    model: str | None = None
    distance_metric: str
    candidate_count: int
    returned_count: int
    limit: int
    offset: int
    has_more: bool
    snapshot_persisted: bool = False
    items: list[SearchExplainResultOut]


class EmbeddingInputPreviewOut(CamelModel):
    recipe_id: str
    input: str
    input_hash: str
