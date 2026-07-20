from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

SqsMessage = TypeVar("SqsMessage", bound=BaseModel)


class InvalidSqsRecordError(ValueError):
    pass


def get_sqs_records(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = event.get("Records", [])
    if records is None:
        return []
    if not isinstance(records, list):
        raise InvalidSqsRecordError("Records must be a list.")
    if not all(isinstance(record, Mapping) for record in records):
        raise InvalidSqsRecordError("Each SQS record must be an object.")
    return records


def require_sqs_message_id(record: Mapping[str, Any]) -> str:
    value = record.get("messageId")
    if not isinstance(value, str) or not value.strip():
        raise InvalidSqsRecordError("SQS record requires a non-empty messageId.")
    return value.strip()


def parse_sqs_message(record: Mapping[str, Any], message_type: type[SqsMessage]) -> SqsMessage:
    body = record.get("body")
    if not isinstance(body, str):
        raise ValueError("SQS record body must be a JSON string.")
    return message_type.model_validate_json(body)
