import json
from types import SimpleNamespace

import pytest

from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult
from app.lambdas import imports as import_lambda


def sqs_record(
    *,
    message_id: object = "sqs-message-1",
    body: object = '{"importJobId": "job-1"}',
) -> dict[str, object]:
    return {
        "messageId": message_id,
        "body": body,
    }


def processing_result(
    disposition: ImportProcessingDisposition,
    *,
    job_id: str = "job-1",
) -> ImportProcessingResult:
    return ImportProcessingResult(
        import_job_id=job_id,
        disposition=disposition,
    )


@pytest.mark.parametrize("event", [{}, {"Records": None}, {"Records": []}])
def test_handler_accepts_empty_batch(event: dict) -> None:
    assert import_lambda.handler(event, None) == {"batchItemFailures": []}


@pytest.mark.parametrize(
    "disposition",
    [
        ImportProcessingDisposition.SUCCEEDED,
        ImportProcessingDisposition.NOOP,
        ImportProcessingDisposition.PERMANENT_FAILURE,
    ],
)
def test_handler_acknowledges_non_retryable_dispositions(monkeypatch, disposition: ImportProcessingDisposition) -> None:
    monkeypatch.setattr(import_lambda, "process_import_job", lambda _job_id: processing_result(disposition))

    response = import_lambda.handler({"Records": [sqs_record()]}, None)

    assert response == {"batchItemFailures": []}


def test_handler_returns_retryable_disposition_as_partial_batch_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        import_lambda,
        "process_import_job",
        lambda _job_id: processing_result(ImportProcessingDisposition.RETRYABLE_FAILURE),
    )

    response = import_lambda.handler({"Records": [sqs_record()]}, None)

    assert response == {
        "batchItemFailures": [
            {"itemIdentifier": "sqs-message-1"},
        ]
    }


def test_handler_processes_all_records_and_preserves_failure_order(monkeypatch) -> None:
    records = [
        sqs_record(message_id="message-1", body=json.dumps({"importJobId": "job-1"})),
        sqs_record(message_id="message-2", body=json.dumps({"importJobId": "job-2"})),
        sqs_record(message_id="message-3", body=json.dumps({"importJobId": "job-3"})),
        sqs_record(message_id="message-4", body=json.dumps({"importJobId": "job-4"})),
    ]
    dispositions = {
        "job-1": ImportProcessingDisposition.RETRYABLE_FAILURE,
        "job-2": ImportProcessingDisposition.SUCCEEDED,
        "job-3": ImportProcessingDisposition.RETRYABLE_FAILURE,
        "job-4": ImportProcessingDisposition.PERMANENT_FAILURE,
    }
    processed: list[str] = []

    def process(job_id: str) -> ImportProcessingResult:
        processed.append(job_id)
        return processing_result(dispositions[job_id], job_id=job_id)

    monkeypatch.setattr(import_lambda, "process_import_job", process)

    response = import_lambda.handler({"Records": records}, None)

    assert processed == ["job-1", "job-2", "job-3", "job-4"]
    assert response == {
        "batchItemFailures": [
            {"itemIdentifier": "message-1"},
            {"itemIdentifier": "message-3"},
        ]
    }


@pytest.mark.parametrize(
    "record",
    [
        sqs_record(body="{bad json"),
        sqs_record(body="[]"),
        sqs_record(body="{}"),
        sqs_record(body='{"importJobId": "   "}'),
        sqs_record(body='{"importJobId": "job-1", "sourceText": "private source"}'),
        sqs_record(body=123),
        {"messageId": "sqs-message-1"},
    ],
)
def test_handler_returns_addressable_validation_errors_as_partial_failures(record: dict[str, object]) -> None:
    response = import_lambda.handler({"Records": [record]}, None)

    assert response == {
        "batchItemFailures": [
            {"itemIdentifier": "sqs-message-1"},
        ]
    }


@pytest.mark.parametrize(
    "record",
    [
        {"body": '{"importJobId": "job-1"}'},
        sqs_record(message_id=""),
        sqs_record(message_id="   "),
        sqs_record(message_id=123),
        "not-a-record",
    ],
)
def test_handler_rejects_records_without_addressable_message_id(record: object) -> None:
    with pytest.raises(import_lambda.InvalidSqsRecordError):
        import_lambda.handler({"Records": [record]}, None)


@pytest.mark.parametrize("records", ["not-a-list", {}])
def test_handler_rejects_invalid_records_collection(records: object) -> None:
    with pytest.raises(import_lambda.InvalidSqsRecordError, match="Records must be a list"):
        import_lambda.handler({"Records": records}, None)


def test_handler_returns_unexpected_processing_exception_as_partial_failure(monkeypatch) -> None:
    def raise_unexpected(_job_id: str) -> ImportProcessingResult:
        raise RuntimeError("private service detail")

    monkeypatch.setattr(import_lambda, "process_import_job", raise_unexpected)

    response = import_lambda.handler({"Records": [sqs_record()]}, None)

    assert response == {
        "batchItemFailures": [
            {"itemIdentifier": "sqs-message-1"},
        ]
    }


def test_handler_logs_only_safe_record_metadata(monkeypatch, capsys) -> None:
    private_source = "PRIVATE SOURCE TEXT MUST NOT BE LOGGED"
    body = json.dumps(
        {
            "importJobId": "job-1",
            "sourceText": private_source,
        }
    )
    monkeypatch.setattr(
        import_lambda,
        "process_import_job",
        lambda _job_id: processing_result(ImportProcessingDisposition.SUCCEEDED),
    )

    import_lambda.handler(
        {"Records": [sqs_record(body=body)]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "request-1" in output
    assert "sqs-message-1" in output
    assert "ValidationError" in output
    assert private_source not in output
    assert body not in output


def test_handler_logs_successful_processing_metadata(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        import_lambda,
        "process_import_job",
        lambda _job_id: processing_result(ImportProcessingDisposition.SUCCEEDED),
    )

    import_lambda.handler(
        {"Records": [sqs_record()]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "request-1" in output
    assert "sqs-message-1" in output
    assert "job-1" in output
    assert "SUCCEEDED" in output
