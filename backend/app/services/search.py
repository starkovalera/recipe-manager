from sqlalchemy.orm import Session

from app.embeddings.runtime import get_embedding_provider
from app.models import Recipe, SourceName
from app.recipes.filters import RecipeListFilters
from app.schemas.recipes import RecipeImageOut
from app.schemas.search import (
    MatchReasonOut,
    SearchChipIn,
    SearchRequestIn,
    SearchResponseOut,
    SearchResultOut,
    SearchSuggestionOut,
    SearchSuggestionType,
)
from app.search.constants import DEFAULT_SEARCH_SUGGESTION_LIMIT
from app.search.queries import (
    list_active_tag_suggestion_rows,
    list_filtered_recipes,
    list_recipe_suggestion_rows,
    list_semantic_recipe_candidates,
    list_semantic_recipes_by_pgvector,
)


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


def _filters_from_selected_chips(selected: list[SearchChipIn]) -> RecipeListFilters:
    tag_id: str | None = None
    ingredient_queries: list[str] = []
    source_name: SourceName | None = None
    author_name: str | None = None
    title_recipe_id: str | None = None

    for chip in selected:
        if chip.type == "tag" and chip.id:
            tag_id = chip.id
        elif chip.type == "ingredient_query" and chip.value:
            ingredient_queries.append(chip.value)
        elif chip.type == "source_name" and chip.value:
            source_name = SourceName(chip.value)
        elif chip.type == "author_name" and chip.value:
            author_name = chip.value
        elif chip.type == "title" and chip.recipe_id:
            title_recipe_id = chip.recipe_id

    return RecipeListFilters(
        tag_id=tag_id,
        ingredient_queries=tuple(ingredient_queries),
        source_name=source_name,
        author_name=author_name,
        title_recipe_id=title_recipe_id,
    )


def _vector_distance(left: list[float], right: list[float]) -> float:
    return sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right, strict=False)) ** 0.5


def _cover_image(recipe: Recipe) -> RecipeImageOut | None:
    if recipe.cover_image_id is None:
        return None
    image = next((item for item in recipe.images if item.id == recipe.cover_image_id), None)
    return RecipeImageOut.model_validate(image) if image is not None else None


def _to_search_result(recipe: Recipe, match_reasons: list[MatchReasonOut]) -> SearchResultOut:
    return SearchResultOut(
        id=recipe.id,
        title=recipe.title,
        note=recipe.note,
        cover_image=_cover_image(recipe),
        has_open_review_flags=any(flag.status == "open" for flag in recipe.review_flags),
        match_reasons=match_reasons,
    )


def _semantic_search_recipes(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters,
    query_embedding: list[float],
    limit_plus_one: int,
    offset: int,
) -> list[Recipe]:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        return list_semantic_recipes_by_pgvector(
            session,
            owner_id,
            filters=filters,
            query_embedding=query_embedding,
            limit=limit_plus_one,
            offset=offset,
        )

    candidates = list_semantic_recipe_candidates(session, owner_id, filters=filters)
    ranked = sorted(
        candidates,
        key=lambda recipe: (_vector_distance(recipe.embedding.embedding or [], query_embedding), recipe.id) if recipe.embedding is not None else (float("inf"), recipe.id),
    )
    return ranked[offset : offset + limit_plus_one]


def search_recipes(session: Session, owner_id: str, request: SearchRequestIn) -> SearchResponseOut:
    filters = _filters_from_selected_chips(request.selected)
    text = (request.text or "").strip()
    limit_plus_one = request.limit + 1

    if text:
        _, provider = get_embedding_provider()
        query_embedding = provider.embed(text)
        recipes = _semantic_search_recipes(
            session,
            owner_id,
            filters=filters,
            query_embedding=query_embedding,
            limit_plus_one=limit_plus_one,
            offset=request.offset,
        )
        items = [
            _to_search_result(
                recipe,
                [MatchReasonOut(type="semantic", label="Semantic match")],
            )
            for recipe in recipes[: request.limit]
        ]
    else:
        recipes = list_filtered_recipes(session, owner_id, filters=filters, limit=limit_plus_one, offset=request.offset)
        items = [
            _to_search_result(
                recipe,
                [MatchReasonOut(type="filter", label="Selected filters")] if request.selected else [],
            )
            for recipe in recipes[: request.limit]
        ]

    return SearchResponseOut(
        items=items,
        limit=request.limit,
        offset=request.offset,
        has_more=len(recipes) > request.limit,
    )
