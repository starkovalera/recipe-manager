import logging
from collections.abc import Mapping
from typing import Any

from app.core.logging import bind_logger
from app.lambdas.sqs import (
    PartialBatchResponse,
    get_aws_request_id,
    require_body,
    require_message_id,
    require_records,
)
from app.queueing.messages import AccountDeletionQueueMessage
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import process_account_deletion

logger = bind_logger(
    logging.getLogger(__name__),
    component="recipes.lambda.account_deletion",
)

RETRYABLE_DISPOSITIONS = {
    AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
    AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
}


def _process_record(
    record: Mapping[str, Any],
    *,
    aws_request_id: str | None,
) -> tuple[str, bool]:
    message_id = require_message_id(record)
    user_id: str | None = None

    try:
        message = AccountDeletionQueueMessage.model_validate_json(require_body(record))
        user_id = message.user_id
        result = process_account_deletion(user_id)
    except Exception as error:
        logger.error(
            "Account-deletion Lambda record processing failed.",
            aws_request_id=aws_request_id,
            sqs_message_id=message_id,
            user_id=user_id,
            error_type=type(error).__name__,
        )
        return message_id, False

    logger.info(
        "Account-deletion Lambda record processed.",
        aws_request_id=aws_request_id,
        sqs_message_id=message_id,
        user_id=user_id,
        disposition=result.disposition.value,
        failed_storage_key_count=result.failed_storage_key_count,
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
