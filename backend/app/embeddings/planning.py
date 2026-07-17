from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.embeddings.events import add_embedding_event
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.logging import bind_embedding_logger
from app.embeddings.queries import get_or_create_recipe_embedding
from app.embeddings.runtime import get_embedding_provider
from app.models import (
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeReviewFlagStatus,
)
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import schedule_outbox_message


@dataclass(frozen=True)
class EmbeddingPlan:
    embedding: RecipeEmbedding
    outbox_message_id: str | None


def prepare_recipe_embedding(
    session: Session,
    recipe: Recipe,
    *,
    force: bool = False,
) -> EmbeddingPlan:
    provider_name, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    embedding_input = build_recipe_embedding_input(recipe)
    log = bind_embedding_logger(
        recipe_id=recipe.id,
        owner_id=recipe.owner_id,
        provider_name=provider_name,
        model=provider.model,
        input_hash=embedding_input.input_hash,
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
        log.info("Embedding skipped due to open review flags")
        return EmbeddingPlan(embedding=embedding, outbox_message_id=None)

    if (
        not force
        and embedding.status == RecipeEmbeddingStatus.READY
        and embedding.input_hash == embedding_input.input_hash
        and embedding.model == provider.model
    ):
        log.info("Embedding already ready")
        return EmbeddingPlan(embedding=embedding, outbox_message_id=None)

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
    outbox_message = schedule_outbox_message(
        session,
        QueueMessageType.RECIPE_EMBEDDING,
        recipe.id,
    )
    log.info("Embedding task planned", force=force)
    return EmbeddingPlan(
        embedding=embedding,
        outbox_message_id=outbox_message.id,
    )
