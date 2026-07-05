import logging
import math
import time
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import RecipeNotFoundError
from app.core.logging import bind_logger
from app.embeddings.input import build_recipe_embedding_hash, build_recipe_embedding_input
from app.embeddings.runtime import get_embedding_provider
from app.models import Recipe, SourceName
from app.recipes.filters import RecipeListFilters
from app.recipes.queries import get_recipe_for_embedding_input_preview
from app.schemas.recipes import RecipeImageOut
from app.schemas.search import (
    EmbeddingInputPreviewOut,
    MatchReasonOut,
    SearchChipIn,
    SearchExplainDebugOut,
    SearchExplainFiltersOut,
    SearchExplainResponseOut,
    SearchExplainResultOut,
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

SEARCH_LOG_COMPONENT = "recipes.search"
logger = logging.getLogger(SEARCH_LOG_COMPONENT)


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


def _filters_to_explain(filters: RecipeListFilters) -> SearchExplainFiltersOut:
    return SearchExplainFiltersOut(
        tag_id=filters.tag_id,
        ingredient_queries=list(filters.ingredient_queries),
        source_name=filters.source_name.value if filters.source_name is not None else None,
        author_name=filters.author_name,
        title_recipe_id=filters.title_recipe_id,
    )


def _embedding_vector_values(vector: object | None) -> list[float]:
    if vector is None:
        return []
    if hasattr(vector, "tolist"):
        converted = vector.tolist()
        return [float(value) for value in converted]
    if not isinstance(vector, Iterable):
        raise TypeError(f"Unsupported embedding vector type: {type(vector).__name__}")
    return [float(value) for value in vector]


def _cosine_distance(left: object | None, right: list[float]) -> float:
    left_values = _embedding_vector_values(left)
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left_values, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    return 1 - (dot_product / (left_norm * right_norm))


def _l2_distance(left: object | None, right: list[float]) -> float:
    left_values = _embedding_vector_values(left)
    return sum((left_value - right_value) ** 2 for left_value, right_value in zip(left_values, right, strict=False)) ** 0.5


def _embedding_distance(left: object | None, right: list[float], distance_metric: str) -> float:
    if distance_metric == "l2":
        return _l2_distance(left, right)
    return _cosine_distance(left, right)


def _similarity_from_distance(distance: float, distance_metric: str) -> float:
    if distance_metric == "l2":
        return 1 / (1 + distance)
    return 1 - distance


def _selected_match_reasons(selected: list[SearchChipIn]) -> list[MatchReasonOut]:
    reasons: list[MatchReasonOut] = []
    for chip in selected:
        label = chip.label or chip.value or chip.id or chip.recipe_id or chip.type
        reasons.append(MatchReasonOut(type=chip.type, label=label))
    return reasons


def _cover_image(recipe: Recipe) -> RecipeImageOut | None:
    if recipe.cover_image_id is None:
        return None
    image = next((item for item in recipe.images if item.id == recipe.cover_image_id), None)
    return RecipeImageOut.model_validate(image) if image is not None else None


def _semantic_match_reason(score: float | None = None) -> MatchReasonOut:
    return MatchReasonOut(type="semantic", label="Semantic match", score=score)


def _semantic_match_reason_for_recipe(recipe: Recipe, query_embedding: list[float], distance_metric: str) -> MatchReasonOut:
    if recipe.embedding is None:
        return _semantic_match_reason()
    distance = _embedding_distance(recipe.embedding.embedding, query_embedding, distance_metric)
    return _semantic_match_reason(round(_similarity_from_distance(distance, distance_metric), 6))


def _to_search_result(recipe: Recipe, match_reasons: list[MatchReasonOut]) -> SearchResultOut:
    return SearchResultOut(
        id=recipe.id,
        title=recipe.title,
        note=recipe.note,
        cover_image=_cover_image(recipe),
        has_open_review_flags=any(flag.status == "open" for flag in recipe.review_flags),
        match_reasons=match_reasons,
    )


def _to_search_explain_result(
    recipe: Recipe,
    *,
    rank: int,
    distance: float | None,
    similarity: float | None,
    match_reasons: list[MatchReasonOut],
) -> SearchExplainResultOut:
    embedding = recipe.embedding
    return SearchExplainResultOut(
        id=recipe.id,
        title=recipe.title,
        note=recipe.note,
        cover_image=_cover_image(recipe),
        has_open_review_flags=any(flag.status == "open" for flag in recipe.review_flags),
        match_reasons=match_reasons,
        debug=SearchExplainDebugOut(
            rank=rank,
            distance=distance,
            similarity=similarity,
            embedding_status=embedding.status if embedding is not None else None,
            embedding_model=embedding.model if embedding is not None else None,
            input_hash=embedding.input_hash if embedding is not None else None,
            embedding_input_preview=build_recipe_embedding_input(recipe),
        ),
    )


def _semantic_search_recipes(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters,
    query_embedding: list[float],
    embedding_model: str,
    distance_metric: str,
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
            embedding_model=embedding_model,
            distance_metric=distance_metric,
            limit=limit_plus_one,
            offset=offset,
        )

    candidates = list_semantic_recipe_candidates(session, owner_id, filters=filters, embedding_model=embedding_model)
    ranked = sorted(
        candidates,
        key=lambda recipe: (_embedding_distance(recipe.embedding.embedding, query_embedding, distance_metric), recipe.id)
        if recipe.embedding is not None
        else (float("inf"), recipe.id),
    )
    return ranked[offset : offset + limit_plus_one]


def search_recipes(session: Session, owner_id: str, request: SearchRequestIn) -> SearchResponseOut:
    started_at = time.perf_counter()
    filters = _filters_from_selected_chips(request.selected)
    text = (request.text or "").strip()
    limit_plus_one = request.limit + 1
    distance_metric = get_settings().embedding_distance_metric
    provider_name: str | None = None
    provider_model: str | None = None

    if text:
        provider_name, provider = get_embedding_provider()
        provider_model = provider.model
        query_embedding = provider.embed(text)
        recipes = _semantic_search_recipes(
            session,
            owner_id,
            filters=filters,
            query_embedding=query_embedding,
            embedding_model=provider_model,
            distance_metric=distance_metric,
            limit_plus_one=limit_plus_one,
            offset=request.offset,
        )
        items = [
            _to_search_result(
                recipe,
                [*_selected_match_reasons(request.selected), _semantic_match_reason_for_recipe(recipe, query_embedding, distance_metric)],
            )
            for recipe in recipes[: request.limit]
        ]
    else:
        recipes = list_filtered_recipes(session, owner_id, filters=filters, limit=limit_plus_one, offset=request.offset)
        items = [
            _to_search_result(
                recipe,
                _selected_match_reasons(request.selected),
            )
            for recipe in recipes[: request.limit]
        ]

    bind_logger(
        logger,
        component=SEARCH_LOG_COMPONENT,
        ownerId=owner_id,
        textPresent=bool(text),
        selectedChipCount=len(request.selected),
        limit=request.limit,
        offset=request.offset,
        provider=provider_name,
        model=provider_model,
        distanceMetric=distance_metric,
    ).info(
        "Semantic search completed",
        returnedCount=len(items),
        durationMs=round((time.perf_counter() - started_at) * 1000),
    )

    return SearchResponseOut(
        items=items,
        limit=request.limit,
        offset=request.offset,
        has_more=len(recipes) > request.limit,
    )


def explain_search(session: Session, owner_id: str, request: SearchRequestIn) -> SearchExplainResponseOut:
    started_at = time.perf_counter()
    filters = _filters_from_selected_chips(request.selected)
    text = (request.text or "").strip()
    limit_plus_one = request.limit + 1
    distance_metric = get_settings().embedding_distance_metric
    provider_name: str | None = None
    provider_model: str | None = None
    candidate_count = 0

    if text:
        provider_name, provider = get_embedding_provider()
        provider_model = provider.model
        query_embedding = provider.embed(text)
        candidates = list_semantic_recipe_candidates(session, owner_id, filters=filters, embedding_model=provider_model)
        ranked_pairs = sorted(
            (
                (recipe, _embedding_distance(recipe.embedding.embedding, query_embedding, distance_metric))
                for recipe in candidates
                if recipe.embedding is not None
            ),
            key=lambda item: (item[1], item[0].id),
        )
        candidate_count = len(ranked_pairs)
        page_pairs = ranked_pairs[request.offset : request.offset + limit_plus_one]
        items = [
            _to_search_explain_result(
                recipe,
                rank=request.offset + index + 1,
                distance=round(distance, 6),
                similarity=round(_similarity_from_distance(distance, distance_metric), 6),
                match_reasons=[
                    *_selected_match_reasons(request.selected),
                    _semantic_match_reason(round(_similarity_from_distance(distance, distance_metric), 6)),
                ],
            )
            for index, (recipe, distance) in enumerate(page_pairs[: request.limit])
        ]
        has_more = len(page_pairs) > request.limit
    else:
        recipes = list_filtered_recipes(session, owner_id, filters=filters, limit=limit_plus_one, offset=request.offset)
        candidate_count = len(recipes)
        items = [
            _to_search_explain_result(
                recipe,
                rank=request.offset + index + 1,
                distance=None,
                similarity=None,
                match_reasons=_selected_match_reasons(request.selected),
            )
            for index, recipe in enumerate(recipes[: request.limit])
        ]
        has_more = len(recipes) > request.limit

    bind_logger(
        logger,
        component=SEARCH_LOG_COMPONENT,
        ownerId=owner_id,
        textPresent=bool(text),
        selectedChipCount=len(request.selected),
        limit=request.limit,
        offset=request.offset,
        provider=provider_name,
        model=provider_model,
        distanceMetric=distance_metric,
    ).info(
        "Semantic search explained",
        candidateCount=candidate_count,
        returnedCount=len(items),
        durationMs=round((time.perf_counter() - started_at) * 1000),
    )

    return SearchExplainResponseOut(
        text_present=bool(text),
        filters=_filters_to_explain(filters),
        provider=provider_name,
        model=provider_model,
        distance_metric=distance_metric,
        candidate_count=candidate_count,
        returned_count=len(items),
        limit=request.limit,
        offset=request.offset,
        has_more=has_more,
        snapshot_persisted=False,
        items=items,
    )


def get_embedding_input_preview(session: Session, recipe_id: str) -> EmbeddingInputPreviewOut:
    recipe = get_recipe_for_embedding_input_preview(session, recipe_id)
    if recipe is None:
        raise RecipeNotFoundError()
    return EmbeddingInputPreviewOut(
        recipe_id=recipe.id,
        input=build_recipe_embedding_input(recipe),
        input_hash=build_recipe_embedding_hash(recipe),
    )
