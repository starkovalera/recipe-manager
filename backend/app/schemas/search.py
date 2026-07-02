from typing import Literal

from app.schemas.base import CamelModel

SearchSuggestionType = Literal["tag", "ingredient_query", "source_name", "author_name", "title"]


class SearchSuggestionOut(CamelModel):
    type: SearchSuggestionType
    id: str | None = None
    recipe_id: str | None = None
    value: str | None = None
    label: str


class SearchSuggestionListOut(CamelModel):
    items: list[SearchSuggestionOut]
