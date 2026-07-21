import logging
from collections.abc import Mapping
from typing import Any

from app.core.logging import bind_logger
from app.embeddings.constants import EmbeddingProcessingDisposition
from app.embeddings.processing import process_recipe_embedding
from app.lambdas.sqs import (
    PartialBatchResponse,
    get_aws_request_id,
    require_body,
    require_message_id,
    require_records,
)
from app.queueing.messages import RecipeEmbeddingQueueMessage

logger = bind_logger(logging.getLogger(__name__), component="recipes.lambda.embedding")

RETRYABLE_DISPOSITIONS = {
    EmbeddingProcessingDisposition.BUSY,
    EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
}


def _process_record(
    record: Mapping[str, Any],
    *,
    aws_request_id: str | None,
) -> tuple[str, bool]:
    message_id = require_message_id(record)
    recipe_id: str | None = None

    try:
        message = RecipeEmbeddingQueueMessage.model_validate_json(require_body(record))
        recipe_id = message.recipe_id
        result = process_recipe_embedding(recipe_id)
    except Exception as error:
        logger.error(
            "Embedding Lambda record processing failed.",
            aws_request_id=aws_request_id,
            sqs_message_id=message_id,
            recipe_id=recipe_id,
            error_type=type(error).__name__,
        )
        return message_id, False

    logger.info(
        "Embedding Lambda record processed.",
        aws_request_id=aws_request_id,
        sqs_message_id=message_id,
        recipe_id=recipe_id,
        disposition=result.disposition.value,
    )
    return message_id, result.disposition not in RETRYABLE_DISPOSITIONS


def handler(
    event: dict[str, Any],
    context: object,
) -> PartialBatchResponse:
    records = require_records(event)
    aws_request_id = get_aws_request_id(context)
    failures = []

    for record in records:
        message_id, succeeded = _process_record(
            record,
            aws_request_id=aws_request_id,
        )
        if not succeeded:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
