from pathlib import Path

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError, StorageOperationError
from app.storage.s3 import S3StorageService
from app.storage.types import StorageWriteContext


class RecordingBody:
    def __init__(self, content: bytes = b"content", error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.read_called = False
        self.closed = False

    def read(self) -> bytes:
        self.read_called = True
        if self.error is not None:
            raise self.error
        return self.content

    def close(self) -> None:
        self.closed = True


class RecordingClient:
    def __init__(self) -> None:
        self.put_calls: list[dict] = []
        self.get_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.body = RecordingBody()
        self.error: Exception | None = None

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"ETag": "ignored"}

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"Body": self.body}

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {}


def build_storage(client=None) -> S3StorageService:
    return S3StorageService(
        location_to_locator={StorageLocation.USER_MEDIA: "recipe-manager-test-user-media"},
        region_name="eu-west-1",
        client=client,
    )


def test_s3_storage_validates_bucket_and_region() -> None:
    with pytest.raises(StorageConfigurationError, match="USER_MEDIA"):
        S3StorageService(location_to_locator={}, region_name="eu-west-1")
    with pytest.raises(StorageConfigurationError, match="bucket"):
        S3StorageService(
            location_to_locator={StorageLocation.USER_MEDIA: Path("uploads")},
            region_name="eu-west-1",
        )
    with pytest.raises(StorageConfigurationError, match="bucket"):
        S3StorageService(location_to_locator={StorageLocation.USER_MEDIA: "   "}, region_name="eu-west-1")
    with pytest.raises(StorageConfigurationError, match="region"):
        S3StorageService(
            location_to_locator={StorageLocation.USER_MEDIA: "recipe-manager-test-user-media"},
            region_name="   ",
        )


def test_s3_client_is_created_lazily_once(monkeypatch) -> None:
    client = RecordingClient()
    calls: list[dict] = []

    def create_client(service_name: str, **kwargs):
        calls.append({"service_name": service_name, **kwargs})
        return client

    monkeypatch.setattr("app.storage.s3.boto3.client", create_client)
    storage = build_storage()
    assert calls == []

    storage.delete(StorageLocation.USER_MEDIA, "legacy.jpg")
    storage.delete(StorageLocation.USER_MEDIA, "legacy.jpg")

    assert calls == [{"service_name": "s3", "region_name": "eu-west-1"}]


def test_injected_s3_client_bypasses_boto3(monkeypatch) -> None:
    client = RecordingClient()
    monkeypatch.setattr("app.storage.s3.boto3.client", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))

    build_storage(client).delete(StorageLocation.USER_MEDIA, "legacy.jpg")

    assert client.delete_calls == [{"Bucket": "recipe-manager-test-user-media", "Key": "legacy.jpg"}]


def test_s3_save_uses_exact_put_object_request() -> None:
    client = RecordingClient()
    storage = build_storage(client)
    context = StorageWriteContext(
        owner_id="owner-1",
        purpose=StoragePurpose.IMPORT_SOURCE,
        entity_id="job-1",
    )

    saved = storage.save(
        StorageLocation.USER_MEDIA,
        b"image",
        "original.png",
        "image/png",
        context=context,
    )

    assert client.put_calls == [
        {
            "Bucket": "recipe-manager-test-user-media",
            "Key": saved.storage_key,
            "Body": b"image",
            "ContentType": "image/png",
        }
    ]
    assert saved.storage_key.startswith("imports/source/owner-1/job-1/")
    assert saved.original_name == "original.png"
    assert saved.mime_type == "image/png"
    assert saved.size_bytes == 5


def test_s3_read_returns_bytes_and_closes_body() -> None:
    client = RecordingClient()
    storage = build_storage(client)

    result = storage.read(StorageLocation.USER_MEDIA, "recipes/media/owner/recipe/key.jpg")

    assert result == b"content"
    assert client.get_calls == [{"Bucket": "recipe-manager-test-user-media", "Key": "recipes/media/owner/recipe/key.jpg"}]
    assert client.body.read_called is True
    assert client.body.closed is True


def test_s3_read_closes_body_when_stream_read_fails() -> None:
    client = RecordingClient()
    client.body = RecordingBody(error=OSError("stream failed"))

    with pytest.raises(StorageOperationError, match="read failed"):
        build_storage(client).read(StorageLocation.USER_MEDIA, "key")

    assert client.body.closed is True


@pytest.mark.parametrize("code", ["NoSuchKey", "NotFound", "404"])
def test_s3_missing_read_maps_to_storage_not_found(code: str) -> None:
    client = RecordingClient()
    client.error = ClientError(
        {"Error": {"Code": code, "Message": "provider detail"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
        "GetObject",
    )

    with pytest.raises(StorageObjectNotFoundError, match="not found") as captured:
        build_storage(client).read(StorageLocation.USER_MEDIA, "missing")

    assert "provider detail" not in str(captured.value)


@pytest.mark.parametrize(
    "error",
    [
        ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "provider detail"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
            "Operation",
        ),
        EndpointConnectionError(endpoint_url="https://s3.example.test"),
    ],
)
def test_s3_provider_failures_map_to_storage_operation_error(error: Exception) -> None:
    client = RecordingClient()
    client.error = error
    storage = build_storage(client)
    context = StorageWriteContext("owner-1", StoragePurpose.TEMPORARY, "operation-1")

    with pytest.raises(StorageOperationError):
        storage.save(StorageLocation.USER_MEDIA, b"x", "x.bin", "application/octet-stream", context=context)
    with pytest.raises(StorageOperationError):
        storage.read(StorageLocation.USER_MEDIA, "key")
    with pytest.raises(StorageOperationError):
        storage.delete(StorageLocation.USER_MEDIA, "key")


def test_s3_delete_uses_exact_request_without_head() -> None:
    client = RecordingClient()

    build_storage(client).delete(StorageLocation.USER_MEDIA, "missing-is-success")

    assert client.delete_calls == [
        {"Bucket": "recipe-manager-test-user-media", "Key": "missing-is-success"},
    ]
    assert not hasattr(client, "head_calls")
