from typing import Any

import pytest
from pydantic import ValidationError

from app.queueing.sqs import SqsQueuePublisher

IMPORTS_URL = "https://sqs.example.test/000/imports"
EMBEDDINGS_URL = "https://sqs.example.test/000/embeddings"
DELETION_URL = "https://sqs.example.test/000/account-deletion"


class FakeSqsClient:
    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response if response is not None else {"MessageId": "message-1"}
        self.error = error
        self.calls: list[dict[str, str]] = []

    def send_message(
        self,
        *,
        QueueUrl: str,
        MessageBody: str,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "QueueUrl": QueueUrl,
                "MessageBody": MessageBody,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def create_publisher(client: FakeSqsClient) -> SqsQueuePublisher:
    return SqsQueuePublisher(
        aws_region="eu-west-1",
        imports_queue_url=IMPORTS_URL,
        embeddings_queue_url=EMBEDDINGS_URL,
        account_deletion_queue_url=DELETION_URL,
        client=client,
    )


def test_publish_import_job_sends_id_only_body_to_imports_queue():
    client = FakeSqsClient()

    create_publisher(client).publish_import_job("job-1")

    assert client.calls == [
        {
            "QueueUrl": IMPORTS_URL,
            "MessageBody": '{"importJobId":"job-1"}',
        }
    ]


def test_publish_recipe_embedding_sends_id_only_body_to_embeddings_queue():
    client = FakeSqsClient()

    create_publisher(client).publish_recipe_embedding("recipe-1")

    assert client.calls == [
        {
            "QueueUrl": EMBEDDINGS_URL,
            "MessageBody": '{"recipeId":"recipe-1"}',
        }
    ]


def test_publish_account_deletion_sends_id_only_body_to_deletion_queue():
    client = FakeSqsClient()

    create_publisher(client).publish_account_deletion("user-1")

    assert client.calls == [
        {
            "QueueUrl": DELETION_URL,
            "MessageBody": '{"userId":"user-1"}',
        }
    ]


def test_publish_validates_and_normalizes_entity_id():
    client = FakeSqsClient()

    create_publisher(client).publish_import_job("  job-1  ")

    assert client.calls[0]["MessageBody"] == '{"importJobId":"job-1"}'


def test_publish_rejects_blank_entity_id_without_calling_sqs():
    client = FakeSqsClient()

    with pytest.raises(ValidationError):
        create_publisher(client).publish_import_job("   ")

    assert client.calls == []


def test_publish_propagates_sqs_client_errors():
    client = FakeSqsClient(error=RuntimeError("sqs unavailable"))

    with pytest.raises(RuntimeError, match="sqs unavailable"):
        create_publisher(client).publish_import_job("job-1")

    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"MessageId": ""},
        {"MessageId": "   "},
        {"MessageId": None},
    ],
)
def test_publish_requires_message_id(response: dict[str, Any]):
    client = FakeSqsClient(response=response)

    with pytest.raises(RuntimeError, match="MessageId"):
        create_publisher(client).publish_import_job("job-1")


def test_boto3_client_is_created_only_on_first_publish(monkeypatch):
    client = FakeSqsClient()
    client_calls: list[dict[str, str]] = []

    def create_client(service_name: str, *, region_name: str):
        client_calls.append(
            {
                "service_name": service_name,
                "region_name": region_name,
            }
        )
        return client

    monkeypatch.setattr("app.queueing.sqs.boto3.client", create_client)

    publisher = SqsQueuePublisher(
        aws_region="eu-west-1",
        imports_queue_url=IMPORTS_URL,
        embeddings_queue_url=EMBEDDINGS_URL,
        account_deletion_queue_url=DELETION_URL,
    )

    assert client_calls == []

    publisher.publish_import_job("job-1")
    publisher.publish_recipe_embedding("recipe-1")

    assert client_calls == [
        {
            "service_name": "sqs",
            "region_name": "eu-west-1",
        }
    ]
