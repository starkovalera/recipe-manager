from collections.abc import Mapping
from typing import Any, TypedDict


class BatchItemFailure(TypedDict):
    itemIdentifier: str


class PartialBatchResponse(TypedDict):
    batchItemFailures: list[BatchItemFailure]


class InvalidSqsRecordError(ValueError):
    pass


def require_records(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = event.get("Records", [])
    if records is None:
        return []
    if not isinstance(records, list):
        raise InvalidSqsRecordError("Records must be a list.")
    if not all(isinstance(record, Mapping) for record in records):
        raise InvalidSqsRecordError("Each SQS record must be an object.")
    return records


def require_message_id(record: Mapping[str, Any]) -> str:
    value = record.get("messageId")
    if not isinstance(value, str) or not value.strip():
        raise InvalidSqsRecordError("SQS record requires a non-empty messageId.")
    return value.strip()


def require_body(record: Mapping[str, Any]) -> str:
    body = record.get("body")
    if not isinstance(body, str):
        raise ValueError("SQS record body must be a JSON string.")
    return body


def get_aws_request_id(context: object) -> str | None:
    value = getattr(context, "aws_request_id", None)
    return value if isinstance(value, str) else None
