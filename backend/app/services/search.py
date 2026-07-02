from sqlalchemy.orm import Session

from app.schemas.search import SearchSuggestionOut, SearchSuggestionType
from app.search.constants import DEFAULT_SEARCH_SUGGESTION_LIMIT
from app.search.queries import list_active_tag_suggestion_rows, list_recipe_suggestion_rows


def _matches_query(value: str | None, query: str) -> bool:
    if not value:
        return False
    return query in value.casefold()


def _append_unique_value_suggestion(
    suggestions: list[SearchSuggestionOut],
    seen: set[tuple[str, str]],
    *,
    suggestion_type: SearchSuggestionType,
    value: str | None,
    query: str,
) -> None:
    if not _matches_query(value, query):
        return
    assert value is not None
    key = (suggestion_type, value.casefold())
    if key in seen:
        return
    seen.add(key)
    suggestions.append(SearchSuggestionOut(type=suggestion_type, value=value, label=value))


def list_search_suggestions(session: Session, owner_id: str, *, query: str, limit: int = DEFAULT_SEARCH_SUGGESTION_LIMIT) -> list[SearchSuggestionOut]:
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return []

    suggestions: list[SearchSuggestionOut] = []
    seen_values: set[tuple[str, str]] = set()
    suggestions.append(
        SearchSuggestionOut(
            type="ingredient_query",
            value=normalized_query,
            label=f"Ingredient - {normalized_query}",
        )
    )

    for tag in list_active_tag_suggestion_rows(session, owner_id):
        if _matches_query(tag.name, normalized_query):
            suggestions.append(SearchSuggestionOut(type="tag", id=tag.id, label=tag.name))

    for recipe in list_recipe_suggestion_rows(session, owner_id):
        if _matches_query(recipe.title, normalized_query):
            suggestions.append(SearchSuggestionOut(type="title", recipe_id=recipe.id, label=recipe.title))
        _append_unique_value_suggestion(
            suggestions,
            seen_values,
            suggestion_type="source_name",
            value=recipe.source_name.value,
            query=normalized_query,
        )
        _append_unique_value_suggestion(
            suggestions,
            seen_values,
            suggestion_type="author_name",
            value=recipe.author_name,
            query=normalized_query,
        )

    return suggestions[:limit]
