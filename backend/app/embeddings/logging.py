import logging

from app.core.logging import BoundLogger, bind_logger
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT

logger = logging.getLogger(EMBEDDING_LOG_COMPONENT)


def bind_embedding_logger(
    *,
    recipe_id: str,
    owner_id: str,
    provider_name: str | None = None,
    model: str | None = None,
    input_hash: str | None = None,
) -> BoundLogger:
    context = {
        "component": EMBEDDING_LOG_COMPONENT,
        "recipe_id": recipe_id,
        "owner_id": owner_id,
    }
    if provider_name is not None:
        context["provider_name"] = provider_name
    if model is not None:
        context["model"] = model
    if input_hash is not None:
        context["input_hash"] = input_hash
    return bind_logger(logger, **context)
