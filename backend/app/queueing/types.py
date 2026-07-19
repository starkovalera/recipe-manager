from typing import Any, Protocol


class SqsClient(Protocol):
    def send_message(
        self,
        *,
        QueueUrl: str,
        MessageBody: str,
    ) -> dict[str, Any]: ...


class QueuePublisher(Protocol):
    def publish_import_job(self, import_job_id: str) -> None: ...

    def publish_recipe_embedding(self, recipe_id: str) -> None: ...

    def publish_account_deletion(self, user_id: str) -> None: ...
