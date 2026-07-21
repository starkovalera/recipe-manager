import json
from types import SimpleNamespace

import pytest

from app.lambdas import account_deletion as account_deletion_lambda
from app.lambdas.sqs import InvalidSqsRecordError
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import AccountDeletionProcessingResult


def sqs_record(
    *,
    message_id: object = "sqs-message-1",
    body: object = '{"userId":"user-1"}',
) -> dict[str, object]:
    return {"messageId": message_id, "body": body}


def processing_result(
    disposition: AccountDeletionProcessingDisposition,
    *,
    user_id: str = "user-1",
    failed_storage_key_count: int = 0,
) -> AccountDeletionProcessingResult:
    return AccountDeletionProcessingResult(
        user_id=user_id,
        disposition=disposition,
        failed_storage_key_count=failed_storage_key_count,
    )


@pytest.mark.parametrize("event", [{}, {"Records": None}, {"Records": []}])
def test_empty_batch_returns_no_failures(event: dict) -> None:
    assert account_deletion_lambda.handler(event, None) == {"batchItemFailures": []}


@pytest.mark.parametrize(
    "disposition",
    [
        AccountDeletionProcessingDisposition.COMPLETED,
        AccountDeletionProcessingDisposition.NOOP,
    ],
)
def test_completed_record_is_acknowledged(monkeypatch, disposition: AccountDeletionProcessingDisposition) -> None:
    monkeypatch.setattr(
        account_deletion_lambda,
        "process_account_deletion",
        lambda _user_id: processing_result(disposition),
    )

    assert account_deletion_lambda.handler({"Records": [sqs_record()]}, None) == {"batchItemFailures": []}


@pytest.mark.parametrize(
    "disposition",
    [
        AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
        AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
    ],
)
def test_retryable_record_is_failed(monkeypatch, disposition: AccountDeletionProcessingDisposition) -> None:
    monkeypatch.setattr(
        account_deletion_lambda,
        "process_account_deletion",
        lambda _user_id: processing_result(disposition),
    )

    assert account_deletion_lambda.handler({"Records": [sqs_record()]}, None) == {
        "batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]
    }


@pytest.mark.parametrize(
    "record",
    [
        sqs_record(body="{bad json"),
        sqs_record(body="[]"),
        sqs_record(body="{}"),
        sqs_record(body='{"userId":"   "}'),
        sqs_record(body='{"userId":"user-1","email":"private@example.test"}'),
        sqs_record(body=123),
        {"messageId": "sqs-message-1"},
    ],
)
def test_invalid_addressable_record_is_failed(record: dict[str, object]) -> None:
    assert account_deletion_lambda.handler({"Records": [record]}, None) == {"batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]}


@pytest.mark.parametrize(
    "record",
    [
        {"body": '{"userId":"user-1"}'},
        sqs_record(message_id=""),
        sqs_record(message_id="   "),
        sqs_record(message_id=123),
        "not-a-record",
    ],
)
def test_missing_message_id_fails_invocation(record: object) -> None:
    with pytest.raises(InvalidSqsRecordError):
        account_deletion_lambda.handler({"Records": [record]}, None)


def test_multiple_records_return_exact_partial_failures(monkeypatch) -> None:
    dispositions = {
        "user-completed": AccountDeletionProcessingDisposition.COMPLETED,
        "user-waiting": AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
        "user-failed": AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
        "user-noop": AccountDeletionProcessingDisposition.NOOP,
    }
    records = [
        sqs_record(message_id="message-completed", body=json.dumps({"userId": "user-completed"})),
        sqs_record(message_id="message-waiting", body=json.dumps({"userId": "user-waiting"})),
        sqs_record(message_id="message-failed", body=json.dumps({"userId": "user-failed"})),
        sqs_record(message_id="message-noop", body=json.dumps({"userId": "user-noop"})),
    ]
    monkeypatch.setattr(
        account_deletion_lambda,
        "process_account_deletion",
        lambda user_id: processing_result(dispositions[user_id], user_id=user_id),
    )

    assert account_deletion_lambda.handler({"Records": records}, None) == {
        "batchItemFailures": [
            {"itemIdentifier": "message-waiting"},
            {"itemIdentifier": "message-failed"},
        ]
    }


def test_unexpected_service_exception_is_failed(monkeypatch) -> None:
    def raise_unexpected(_user_id: str) -> AccountDeletionProcessingResult:
        raise RuntimeError("private service detail")

    monkeypatch.setattr(account_deletion_lambda, "process_account_deletion", raise_unexpected)

    assert account_deletion_lambda.handler({"Records": [sqs_record()]}, None) == {
        "batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]
    }


def test_logs_only_safe_processing_metadata(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        account_deletion_lambda,
        "process_account_deletion",
        lambda _user_id: processing_result(
            AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
            failed_storage_key_count=2,
        ),
    )

    account_deletion_lambda.handler(
        {"Records": [sqs_record()]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "request-1" in output
    assert "sqs-message-1" in output
    assert "user-1" in output
    assert "RETRYABLE_FAILURE" in output
    assert '"failed_storage_key_count": 2' in output
    assert "private@example.test" not in output
    assert "user_clerk_private" not in output
    assert "Bearer private-token" not in output
    assert '{"userId":"user-1"}' not in output


def test_rejected_sensitive_fields_are_not_logged(capsys) -> None:
    body = json.dumps(
        {
            "userId": "user-1",
            "email": "private@example.test",
            "authUserId": "user_clerk_private",
            "authorization": "Bearer private-token",
        }
    )

    account_deletion_lambda.handler(
        {"Records": [sqs_record(body=body)]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "ValidationError" in output
    assert "private@example.test" not in output
    assert "user_clerk_private" not in output
    assert "Bearer private-token" not in output
    assert body not in output
