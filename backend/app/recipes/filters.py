from dataclasses import dataclass

from app.models import SourceName


@dataclass(frozen=True)
class RecipeListFilters:
    tag_id: str | None = None
    ingredient_queries: tuple[str, ...] = ()
    source_name: SourceName | None = None
    author_name: str | None = None
    title_recipe_id: str | None = None
