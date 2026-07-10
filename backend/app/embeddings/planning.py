import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import bind_logger
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT, EMBEDDING_LOG_PREFIX
from app.embeddings.events import add_embedding_event
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.queries import get_or_create_recipe_embedding
from app.embeddings.runtime import get_embedding_provider
from app.models import (
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeReviewFlagStatus,
)

logger = logging.getLogger(EMBEDDING_LOG_COMPONENT)


@dataclass(frozen=True)
class EmbeddingPlan:
    embedding: RecipeEmbedding
    enqueue: bool


def prepare_recipe_embedding(
    session: Session,
    recipe: Recipe,
    *,
    force: bool = False,
) -> EmbeddingPlan:
    provider_name, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    embedding_input = build_recipe_embedding_input(recipe)
    log = bind_logger(
        logger,
        component=EMBEDDING_LOG_COMPONENT,
        recipeId=recipe.id,
        ownerId=recipe.owner_id,
        provider=provider_name,
    )

    open_flag_count = sum(1 for flag in recipe.review_flags if flag.status == RecipeReviewFlagStatus.OPEN)
    if open_flag_count:
        embedding.model = provider.model
        embedding.input_hash = embedding_input.input_hash
        embedding.status = RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS
        embedding.error_message = None
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=recipe.owner_id,
            event_type=RecipeEmbeddingEventType.SKIPPED_DUE_TO_FLAGS,
            payload={"reason": "open_review_flags", "openFlagCount": open_flag_count},
        )
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding skipped due to open review flags")
        return EmbeddingPlan(embedding=embedding, enqueue=False)

    if (
        not force
        and embedding.status == RecipeEmbeddingStatus.READY
        and embedding.input_hash == embedding_input.input_hash
        and embedding.model == provider.model
    ):
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding already ready")
        return EmbeddingPlan(embedding=embedding, enqueue=False)

    embedding.model = provider.model
    embedding.input_hash = embedding_input.input_hash
    embedding.status = RecipeEmbeddingStatus.STALE
    embedding.error_message = None
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=RecipeEmbeddingEventType.SCHEDULED,
        payload={"reason": "manual_retry" if force else "recipe_content_changed", "model": provider.model},
    )
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding task planned", force=force)
    return EmbeddingPlan(embedding=embedding, enqueue=True)
