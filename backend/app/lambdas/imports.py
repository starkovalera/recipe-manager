import logging
from collections.abc import Mapping
from typing import Any, TypedDict

from app.core.logging import bind_logger
from app.imports.jobs import process_import_job
from app.imports.outcomes import ImportProcessingDisposition
from app.queueing.messages import ImportJobQueueMessage

logger = bind_logger(logging.getLogger(__name__), component="recipes.lambda.import")


class BatchItemFailure(TypedDict):
    itemIdentifier: str


class PartialBatchResponse(TypedDict):
    batchItemFailures: list[BatchItemFailure]


class InvalidSqsRecordError(ValueError):
    pass


def _require_message_id(record: Mapping[str, Any]) -> str:
    value = record.get("messageId")
    if not isinstance(value, str) or not value.strip():
        raise InvalidSqsRecordError("SQS record requires a non-empty messageId.")
    return value.strip()


def _parse_message(record: Mapping[str, Any]) -> ImportJobQueueMessage:
    body = record.get("body")
    if not isinstance(body, str):
        raise ValueError("SQS record body must be a JSON string.")
    return ImportJobQueueMessage.model_validate_json(body)


def _process_record(
    record: Mapping[str, Any],
    *,
    aws_request_id: str | None,
) -> tuple[str, bool]:
    message_id = _require_message_id(record)
    import_job_id: str | None = None

    try:
        message = _parse_message(record)
        import_job_id = message.import_job_id
        result = process_import_job(import_job_id)
    except Exception as error:
        logger.error(
            "Import Lambda record processing failed.",
            aws_request_id=aws_request_id,
            sqs_message_id=message_id,
            import_job_id=import_job_id,
            error_type=type(error).__name__,
        )
        return message_id, False

    failed = result.disposition is ImportProcessingDisposition.RETRYABLE_FAILURE
    logger.info(
        "Import Lambda record processed.",
        aws_request_id=aws_request_id,
        sqs_message_id=message_id,
        import_job_id=import_job_id,
        disposition=result.disposition.value,
    )
    return message_id, not failed


def handler(
    event: dict[str, Any],
    context: object,
) -> PartialBatchResponse:
    records = event.get("Records", [])
    if records is None:
        records = []
    if not isinstance(records, list):
        raise InvalidSqsRecordError("Records must be a list.")

    aws_request_id = getattr(context, "aws_request_id", None)
    failures: list[BatchItemFailure] = []

    for record in records:
        if not isinstance(record, Mapping):
            raise InvalidSqsRecordError("Each SQS record must be an object.")
        message_id, succeeded = _process_record(
            record,
            aws_request_id=aws_request_id,
        )
        if not succeeded:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
