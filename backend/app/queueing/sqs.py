import boto3

from app.queueing.messages import (
    AccountDeletionQueueMessage,
    ImportJobQueueMessage,
    RecipeEmbeddingQueueMessage,
)
from app.queueing.types import SqsClient


class SqsQueuePublisher:
    def __init__(
        self,
        *,
        aws_region: str,
        imports_queue_url: str,
        embeddings_queue_url: str,
        account_deletion_queue_url: str,
        client: SqsClient | None = None,
    ) -> None:
        self._aws_region = aws_region
        self._imports_queue_url = imports_queue_url
        self._embeddings_queue_url = embeddings_queue_url
        self._account_deletion_queue_url = account_deletion_queue_url
        self._client = client

    def _get_client(self) -> SqsClient:
        if self._client is None:
            self._client = boto3.client(
                "sqs",
                region_name=self._aws_region,
            )
        return self._client

    def _send(self, *, queue_url: str, message_body: str) -> None:
        response = self._get_client().send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
        )
        message_id = response.get("MessageId")
        if not isinstance(message_id, str) or not message_id.strip():
            raise RuntimeError("SQS SendMessage response did not include MessageId.")

    def publish_import_job(self, import_job_id: str) -> None:
        message = ImportJobQueueMessage(import_job_id=import_job_id)
        self._send(
            queue_url=self._imports_queue_url,
            message_body=message.model_dump_json(by_alias=True),
        )

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        message = RecipeEmbeddingQueueMessage(recipe_id=recipe_id)
        self._send(
            queue_url=self._embeddings_queue_url,
            message_body=message.model_dump_json(by_alias=True),
        )

    def publish_account_deletion(self, user_id: str) -> None:
        message = AccountDeletionQueueMessage(user_id=user_id)
        self._send(
            queue_url=self._account_deletion_queue_url,
            message_body=message.model_dump_json(by_alias=True),
        )
