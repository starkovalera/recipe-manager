import pytest
from pydantic import ValidationError

from app.lambdas.sqs import InvalidSqsRecordError, get_sqs_records, parse_sqs_message, require_sqs_message_id
from app.queueing.messages import ImportJobQueueMessage


def test_get_sqs_records_accepts_missing_none_and_empty_records() -> None:
    assert get_sqs_records({}) == []
    assert get_sqs_records({"Records": None}) == []
    assert get_sqs_records({"Records": []}) == []


@pytest.mark.parametrize("records", ["not-a-list", {}])
def test_get_sqs_records_rejects_invalid_collection(records: object) -> None:
    with pytest.raises(InvalidSqsRecordError, match="Records must be a list"):
        get_sqs_records({"Records": records})


def test_get_sqs_records_rejects_non_object_record() -> None:
    with pytest.raises(InvalidSqsRecordError, match="Each SQS record must be an object"):
        get_sqs_records({"Records": ["not-a-record"]})


@pytest.mark.parametrize("message_id", [None, "", "   ", 123])
def test_require_sqs_message_id_rejects_missing_or_invalid_value(message_id: object) -> None:
    record = {} if message_id is None else {"messageId": message_id}
    with pytest.raises(InvalidSqsRecordError, match="non-empty messageId"):
        require_sqs_message_id(record)


def test_require_sqs_message_id_strips_whitespace() -> None:
    assert require_sqs_message_id({"messageId": " message-1 "}) == "message-1"


def test_parse_sqs_message_validates_existing_queue_contract() -> None:
    message = parse_sqs_message(
        {"body": '{"importJobId":"job-1"}'},
        ImportJobQueueMessage,
    )
    assert message == ImportJobQueueMessage(import_job_id="job-1")


@pytest.mark.parametrize("body", [None, 123])
def test_parse_sqs_message_requires_string_body(body: object) -> None:
    record = {} if body is None else {"body": body}
    with pytest.raises(ValueError, match="body must be a JSON string"):
        parse_sqs_message(record, ImportJobQueueMessage)


@pytest.mark.parametrize("body", ["{bad json", "[]", "{}", '{"importJobId":"job-1","extra":true}'])
def test_parse_sqs_message_preserves_pydantic_validation(body: str) -> None:
    with pytest.raises(ValidationError):
        parse_sqs_message({"body": body}, ImportJobQueueMessage)
