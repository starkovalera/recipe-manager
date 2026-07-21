import json
from types import SimpleNamespace

import pytest

from app.embeddings.constants import EmbeddingProcessingDisposition
from app.embeddings.outcomes import EmbeddingProcessingResult
from app.lambdas import embeddings as embedding_lambda
from app.lambdas.sqs import InvalidSqsRecordError


def sqs_record(
    *,
    message_id: object = "sqs-message-1",
    body: object = '{"recipeId":"recipe-1"}',
) -> dict[str, object]:
    return {"messageId": message_id, "body": body}


def processing_result(
    disposition: EmbeddingProcessingDisposition,
    *,
    recipe_id: str = "recipe-1",
) -> EmbeddingProcessingResult:
    return EmbeddingProcessingResult(recipe_id=recipe_id, disposition=disposition)


@pytest.mark.parametrize("event", [{}, {"Records": None}, {"Records": []}])
def test_handler_accepts_empty_batch(event: dict) -> None:
    assert embedding_lambda.handler(event, None) == {"batchItemFailures": []}


@pytest.mark.parametrize(
    "disposition",
    [
        EmbeddingProcessingDisposition.SUCCEEDED,
        EmbeddingProcessingDisposition.NOOP,
        EmbeddingProcessingDisposition.REQUEUED,
    ],
)
def test_handler_acknowledges_completed_dispositions(monkeypatch, disposition: EmbeddingProcessingDisposition) -> None:
    monkeypatch.setattr(
        embedding_lambda,
        "process_recipe_embedding",
        lambda _recipe_id: processing_result(disposition),
    )

    assert embedding_lambda.handler({"Records": [sqs_record()]}, None) == {"batchItemFailures": []}


@pytest.mark.parametrize(
    "disposition",
    [
        EmbeddingProcessingDisposition.BUSY,
        EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
    ],
)
def test_handler_returns_retryable_dispositions_as_partial_failures(
    monkeypatch,
    disposition: EmbeddingProcessingDisposition,
) -> None:
    monkeypatch.setattr(
        embedding_lambda,
        "process_recipe_embedding",
        lambda _recipe_id: processing_result(disposition),
    )

    assert embedding_lambda.handler({"Records": [sqs_record()]}, None) == {"batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]}


def test_handler_processes_every_record_and_preserves_failure_order(monkeypatch) -> None:
    records = [
        sqs_record(message_id="message-1", body=json.dumps({"recipeId": "recipe-1"})),
        sqs_record(message_id="message-2", body=json.dumps({"recipeId": "recipe-2"})),
        sqs_record(message_id="message-3", body=json.dumps({"recipeId": "recipe-3"})),
        sqs_record(message_id="message-4", body=json.dumps({"recipeId": "recipe-4"})),
    ]
    dispositions = {
        "recipe-1": EmbeddingProcessingDisposition.BUSY,
        "recipe-2": EmbeddingProcessingDisposition.SUCCEEDED,
        "recipe-3": EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
        "recipe-4": EmbeddingProcessingDisposition.REQUEUED,
    }
    processed: list[str] = []

    def process(recipe_id: str) -> EmbeddingProcessingResult:
        processed.append(recipe_id)
        return processing_result(dispositions[recipe_id], recipe_id=recipe_id)

    monkeypatch.setattr(embedding_lambda, "process_recipe_embedding", process)

    response = embedding_lambda.handler({"Records": records}, None)

    assert processed == ["recipe-1", "recipe-2", "recipe-3", "recipe-4"]
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
        sqs_record(body='{"recipeId":"   "}'),
        sqs_record(body='{"recipeId":"recipe-1","input":"private"}'),
        sqs_record(body=123),
        {"messageId": "sqs-message-1"},
    ],
)
def test_handler_returns_addressable_validation_errors_as_partial_failures(record: dict[str, object]) -> None:
    assert embedding_lambda.handler({"Records": [record]}, None) == {"batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]}


@pytest.mark.parametrize(
    "record",
    [
        {"body": '{"recipeId":"recipe-1"}'},
        sqs_record(message_id=""),
        sqs_record(message_id="   "),
        sqs_record(message_id=123),
        "not-a-record",
    ],
)
def test_handler_rejects_records_without_addressable_message_id(record: object) -> None:
    with pytest.raises(InvalidSqsRecordError):
        embedding_lambda.handler({"Records": [record]}, None)


@pytest.mark.parametrize("records", ["not-a-list", {}])
def test_handler_rejects_invalid_records_collection(records: object) -> None:
    with pytest.raises(InvalidSqsRecordError, match="Records must be a list"):
        embedding_lambda.handler({"Records": records}, None)


def test_handler_returns_unexpected_processing_exception_as_partial_failure(monkeypatch) -> None:
    def raise_unexpected(_recipe_id: str) -> EmbeddingProcessingResult:
        raise RuntimeError("private provider detail")

    monkeypatch.setattr(embedding_lambda, "process_recipe_embedding", raise_unexpected)

    assert embedding_lambda.handler({"Records": [sqs_record()]}, None) == {"batchItemFailures": [{"itemIdentifier": "sqs-message-1"}]}


def test_handler_logs_only_safe_record_metadata(monkeypatch, capsys) -> None:
    private_input = "PRIVATE EMBEDDING INPUT MUST NOT BE LOGGED"
    body = json.dumps({"recipeId": "recipe-1", "input": private_input})
    monkeypatch.setattr(
        embedding_lambda,
        "process_recipe_embedding",
        lambda _recipe_id: processing_result(EmbeddingProcessingDisposition.SUCCEEDED),
    )

    embedding_lambda.handler(
        {"Records": [sqs_record(body=body)]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "request-1" in output
    assert "sqs-message-1" in output
    assert "ValidationError" in output
    assert private_input not in output
    assert body not in output


def test_handler_logs_successful_processing_metadata(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        embedding_lambda,
        "process_recipe_embedding",
        lambda _recipe_id: processing_result(EmbeddingProcessingDisposition.SUCCEEDED),
    )

    embedding_lambda.handler(
        {"Records": [sqs_record()]},
        SimpleNamespace(aws_request_id="request-1"),
    )

    output = capsys.readouterr().out
    assert "request-1" in output
    assert "sqs-message-1" in output
    assert "recipe-1" in output
    assert "SUCCEEDED" in output
    assert "recipes.lambda.embedding" in output
