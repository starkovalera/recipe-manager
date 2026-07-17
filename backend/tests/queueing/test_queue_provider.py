import pytest

from app.core.config import AppEnv, Settings
from app.core.infrastructure import QueueProvider, StorageProvider
from app.queueing import provider as provider_module
from app.queueing.dramatiq import DramatiqQueuePublisher


def test_create_queue_publisher_returns_dramatiq_adapter():
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )

    publisher = provider_module.create_queue_publisher(settings)

    assert isinstance(publisher, DramatiqQueuePublisher)


def test_create_queue_publisher_rejects_unimplemented_sqs():
    settings = Settings(
        app_env=AppEnv.PROD,
        database_url="postgresql+psycopg://user:pass@db.example.test/app",
        queue_provider=QueueProvider.SQS,
        storage_provider=StorageProvider.S3,
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )

    with pytest.raises(RuntimeError, match="SQS"):
        provider_module.create_queue_publisher(settings)


def test_get_queue_publisher_reuses_created_publisher(monkeypatch):
    publisher = DramatiqQueuePublisher()
    factory_calls: list[object] = []
    settings = object()

    monkeypatch.setattr(provider_module, "_queue_publisher", None)
    monkeypatch.setattr(provider_module, "get_settings", lambda: settings)

    def create_publisher(received_settings):
        factory_calls.append(received_settings)
        return publisher

    monkeypatch.setattr(provider_module, "create_queue_publisher", create_publisher)

    first = provider_module.get_queue_publisher()
    second = provider_module.get_queue_publisher()

    assert first is publisher
    assert second is publisher
    assert factory_calls == [settings]
