from app.core.config import Settings, get_settings
from app.core.infrastructure import QueueProvider
from app.queueing.dramatiq import DramatiqQueuePublisher
from app.queueing.sqs import SqsQueuePublisher
from app.queueing.types import QueuePublisher

_queue_publisher: QueuePublisher | None = None


def create_queue_publisher(settings: Settings) -> QueuePublisher:
    if settings.queue_provider is QueueProvider.DRAMATIQ:
        return DramatiqQueuePublisher()
    if settings.queue_provider is QueueProvider.SQS:
        if (
            settings.aws_region is None
            or settings.sqs_imports_queue_url is None
            or settings.sqs_embeddings_queue_url is None
            or settings.sqs_account_deletion_queue_url is None
        ):
            raise RuntimeError("SQS queue publisher settings are incomplete.")
        return SqsQueuePublisher(
            aws_region=settings.aws_region,
            imports_queue_url=settings.sqs_imports_queue_url,
            embeddings_queue_url=settings.sqs_embeddings_queue_url,
            account_deletion_queue_url=settings.sqs_account_deletion_queue_url,
        )
    raise RuntimeError("Queue provider is not configured.")


def get_queue_publisher() -> QueuePublisher:
    global _queue_publisher

    if _queue_publisher is None:
        _queue_publisher = create_queue_publisher(get_settings())
    return _queue_publisher
