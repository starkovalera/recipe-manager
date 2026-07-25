import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from app.media.access.constants import DownloadAccessMode, MediaReferenceType
from app.media.access.s3 import S3DownloadAccessProvider
from app.media.access.types import AuthorizedMedia, MediaReference
from app.storage.constants import StorageLocation
from app.storage.s3 import S3StorageService

LOCALSTACK_ENDPOINT_URL = os.getenv(
    "LOCALSTACK_S3_ENDPOINT_URL",
    "http://s3.localhost.localstack.cloud:4566",
)
LOCALSTACK_REGION = "us-east-1"
USER_MEDIA_BUCKET = "recipe-manager-local-user-media"
SYSTEM_ARTIFACTS_BUCKET = "recipe-manager-local-system-artifacts"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LOCALSTACK_INTEGRATION") != "1",
    reason="Set RUN_LOCALSTACK_INTEGRATION=1 to run LocalStack S3 integration tests.",
)


@dataclass(frozen=True)
class IntegrationStorageContext:
    storage_key: str

    def build_storage_key(self, *, original_name: str, mime_type: str) -> str:
        return self.storage_key


@pytest.fixture
def storage() -> S3StorageService:
    return S3StorageService(
        location_to_locator={
            StorageLocation.USER_MEDIA: USER_MEDIA_BUCKET,
            StorageLocation.SYSTEM_ARTIFACTS: SYSTEM_ARTIFACTS_BUCKET,
        },
        region_name=LOCALSTACK_REGION,
        endpoint_url=LOCALSTACK_ENDPOINT_URL,
    )


def test_localstack_storage_round_trip_and_listing(storage: S3StorageService) -> None:
    storage_key = f"integration/localstack/{uuid4()}.png"
    content = b"localstack-round-trip"

    try:
        saved = storage.save(
            StorageLocation.USER_MEDIA,
            content,
            "image.png",
            "image/png",
            context=IntegrationStorageContext(storage_key),
        )

        page = storage.list_objects(
            StorageLocation.USER_MEDIA,
            prefix="integration/localstack/",
            limit=100,
        )

        assert saved.storage_key == storage_key
        assert storage.read(StorageLocation.USER_MEDIA, storage_key) == content
        assert storage_key in {item.storage_key for item in page.objects}
    finally:
        storage.delete(StorageLocation.USER_MEDIA, storage_key)


def test_localstack_presigned_grant_returns_bytes_directly(storage: S3StorageService) -> None:
    storage_key = f"integration/localstack/{uuid4()}.jpg"
    content = b"localstack-presigned-content"
    storage.save(
        StorageLocation.USER_MEDIA,
        content,
        "image.jpg",
        "image/jpeg",
        context=IntegrationStorageContext(storage_key),
    )
    provider = S3DownloadAccessProvider(
        bucket_name=USER_MEDIA_BUCKET,
        region_name=LOCALSTACK_REGION,
        endpoint_url=LOCALSTACK_ENDPOINT_URL,
    )
    media = AuthorizedMedia(
        reference=MediaReference(MediaReferenceType.RECIPE_IMAGE, "localstack-image"),
        location=StorageLocation.USER_MEDIA,
        storage_key=storage_key,
        content_type="image/jpeg",
    )

    try:
        before = datetime.now(timezone.utc)
        grant = provider.create_grant(media)
        response = httpx.get(grant.url, trust_env=False)

        assert grant.access_mode is DownloadAccessMode.DIRECT
        assert grant.expires_at is not None
        assert 55 <= (grant.expires_at - before).total_seconds() <= 65
        assert response.status_code == 200
        assert response.content == content
        assert response.headers["content-type"] == "image/jpeg"
    finally:
        storage.delete(StorageLocation.USER_MEDIA, storage_key)


def test_localstack_missing_object_gets_grant_without_preflight_lookup() -> None:
    provider = S3DownloadAccessProvider(
        bucket_name=USER_MEDIA_BUCKET,
        region_name=LOCALSTACK_REGION,
        endpoint_url=LOCALSTACK_ENDPOINT_URL,
    )
    media = AuthorizedMedia(
        reference=MediaReference(MediaReferenceType.RECIPE_IMAGE, "missing-localstack-image"),
        location=StorageLocation.USER_MEDIA,
        storage_key=f"integration/localstack/missing-{uuid4()}.jpg",
        content_type="image/jpeg",
    )

    grant = provider.create_grant(media)
    response = httpx.get(grant.url, trust_env=False)

    assert grant.access_mode is DownloadAccessMode.DIRECT
    assert response.status_code == 404


def test_localstack_expired_grant_is_rejected(storage: S3StorageService, monkeypatch) -> None:
    monkeypatch.setattr("app.media.access.s3.PRESIGNED_MEDIA_TTL_SECONDS", 5)
    storage_key = f"integration/localstack/{uuid4()}.jpg"
    storage.save(
        StorageLocation.USER_MEDIA,
        b"expiring-content",
        "image.jpg",
        "image/jpeg",
        context=IntegrationStorageContext(storage_key),
    )
    provider = S3DownloadAccessProvider(
        bucket_name=USER_MEDIA_BUCKET,
        region_name=LOCALSTACK_REGION,
        endpoint_url=LOCALSTACK_ENDPOINT_URL,
    )
    media = AuthorizedMedia(
        reference=MediaReference(MediaReferenceType.RECIPE_IMAGE, "expiring-localstack-image"),
        location=StorageLocation.USER_MEDIA,
        storage_key=storage_key,
        content_type="image/jpeg",
    )

    try:
        grant = provider.create_grant(media)
        assert httpx.get(grant.url, trust_env=False).status_code == 200

        time.sleep(6)

        assert httpx.get(grant.url, trust_env=False).status_code == 403
    finally:
        storage.delete(StorageLocation.USER_MEDIA, storage_key)
