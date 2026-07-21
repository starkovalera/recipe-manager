from types import SimpleNamespace

import pytest

from app.lambdas.sqs import InvalidSqsRecordError, get_aws_request_id, require_body, require_message_id, require_records


def test_require_records_accepts_missing_none_and_empty_records() -> None:
    assert require_records({}) == []
    assert require_records({"Records": None}) == []
    assert require_records({"Records": []}) == []


@pytest.mark.parametrize("records", ["not-a-list", {}])
def test_require_records_rejects_invalid_collection(records: object) -> None:
    with pytest.raises(InvalidSqsRecordError, match="Records must be a list"):
        require_records({"Records": records})


def test_require_records_rejects_non_object_record() -> None:
    with pytest.raises(InvalidSqsRecordError, match="Each SQS record must be an object"):
        require_records({"Records": ["not-a-record"]})


@pytest.mark.parametrize("message_id", [None, "", "   ", 123])
def test_require_message_id_rejects_missing_or_invalid_value(message_id: object) -> None:
    record = {} if message_id is None else {"messageId": message_id}
    with pytest.raises(InvalidSqsRecordError, match="non-empty messageId"):
        require_message_id(record)


def test_require_message_id_strips_whitespace() -> None:
    assert require_message_id({"messageId": " message-1 "}) == "message-1"


def test_require_body_returns_original_string() -> None:
    assert require_body({"body": "  body with spaces  "}) == "  body with spaces  "


@pytest.mark.parametrize("body", [None, 123])
def test_require_body_requires_string_body(body: object) -> None:
    record = {} if body is None else {"body": body}
    with pytest.raises(ValueError, match="body must be a JSON string"):
        require_body(record)


def test_get_aws_request_id_handles_context_shapes() -> None:
    assert get_aws_request_id(None) is None
    assert get_aws_request_id(object()) is None
    assert get_aws_request_id(SimpleNamespace(aws_request_id=123)) is None
    assert get_aws_request_id(SimpleNamespace(aws_request_id="request-1")) == "request-1"
