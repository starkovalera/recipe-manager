from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingStatus, Tag
from app.recipes.filters import RecipeListFilters
from app.recipes.queries import apply_recipe_list_filters

EmbeddingDistanceMetric = str


def list_active_tag_suggestion_rows(session: Session, owner_id: str) -> list[Tag]:
    return session.scalars(
        select(Tag)
        .where(Tag.owner_id == owner_id, Tag.deleted_at.is_(None))
        .order_by(Tag.name, Tag.id)
    ).all()


def list_recipe_suggestion_rows(session: Session, owner_id: str) -> list[Recipe]:
    return session.scalars(
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .order_by(Recipe.title, Recipe.id)
    ).all()


def base_search_query(owner_id: str, filters: RecipeListFilters) -> Select[tuple[Recipe]]:
    query = (
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .options(selectinload(Recipe.cover_image), selectinload(Recipe.ingredients), selectinload(Recipe.review_flags))
    )
    return apply_recipe_list_filters(query, filters)


def list_filtered_recipes(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters,
    limit: int,
    offset: int,
) -> list[Recipe]:
    query = base_search_query(owner_id, filters).order_by(Recipe.created_at.desc(), Recipe.id)
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def list_semantic_recipe_candidates(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters,
    embedding_model: str,
) -> list[Recipe]:
    query = (
        base_search_query(owner_id, filters)
        .join(RecipeEmbedding, RecipeEmbedding.recipe_id == Recipe.id)
        .where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.READY.value,
            RecipeEmbedding.model == embedding_model,
            RecipeEmbedding.embedding.is_not(None),
        )
        .options(selectinload(Recipe.embedding))
    )
    return list(session.scalars(query).all())


def list_semantic_recipes_by_pgvector(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters,
    query_embedding: list[float],
    embedding_model: str,
    distance_metric: EmbeddingDistanceMetric,
    limit: int,
    offset: int,
) -> list[Recipe]:
    if distance_metric == "l2":
        distance = RecipeEmbedding.embedding.l2_distance(query_embedding)
    else:
        distance = RecipeEmbedding.embedding.cosine_distance(query_embedding)
    query = (
        base_search_query(owner_id, filters)
        .join(RecipeEmbedding, RecipeEmbedding.recipe_id == Recipe.id)
        .where(
            RecipeEmbedding.status == RecipeEmbeddingStatus.READY.value,
            RecipeEmbedding.model == embedding_model,
            RecipeEmbedding.embedding.is_not(None),
        )
        .options(selectinload(Recipe.embedding))
        .order_by(distance, Recipe.id)
    )
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)
