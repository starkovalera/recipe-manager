from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from app.core.errors import MediaAccessNotAvailableError
from app.media.access.constants import DownloadAccessMode, MediaReferenceType
from app.media.access.local import LocalDownloadAccessProvider
from app.media.access.s3 import S3DownloadAccessProvider
from app.media.access.types import AuthorizedMedia, MediaReference, MediaReferenceUnavailableError
from app.storage.constants import StorageLocation


def authorized_media() -> AuthorizedMedia:
    return AuthorizedMedia(
        reference=MediaReference(MediaReferenceType.RECIPE_IMAGE, "image-1"),
        location=StorageLocation.USER_MEDIA,
        storage_key="recipes/media/owner-1/recipe-1/image.jpg",
        content_type="image/jpeg",
    )


def test_s3_provider_generates_exact_presigned_get_without_head_and_utc_expiry() -> None:
    client = Mock()
    client.generate_presigned_url.return_value = "https://signed.invalid/object?signature=secret"
    now = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)
    provider = S3DownloadAccessProvider(
        bucket_name="user-media",
        region_name="eu-west-1",
        client=client,
        clock=lambda: now,
    )

    grant = provider.create_grant(authorized_media())

    client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "user-media", "Key": "recipes/media/owner-1/recipe-1/image.jpg"},
        ExpiresIn=60,
    )
    assert not client.head_object.called
    assert grant.access_mode is DownloadAccessMode.DIRECT
    assert grant.expires_at == datetime(2026, 7, 24, 10, 1, tzinfo=timezone.utc)


def test_s3_provider_maps_sdk_failure_to_stable_operational_error() -> None:
    client = Mock()
    client.generate_presigned_url.side_effect = ClientError({"Error": {"Code": "Denied"}}, "GetObject")
    provider = S3DownloadAccessProvider(bucket_name="user-media", region_name="eu-west-1", client=client)
    with pytest.raises(MediaAccessNotAvailableError):
        provider.create_grant(authorized_media())


def test_s3_provider_constructs_and_reuses_client_lazily(monkeypatch) -> None:
    client = Mock()
    client.generate_presigned_url.return_value = "https://signed.invalid/object"
    client_factory = Mock(return_value=client)
    monkeypatch.setattr("app.media.access.s3.boto3.client", client_factory)
    provider = S3DownloadAccessProvider(bucket_name="user-media", region_name="eu-west-1")

    provider.create_grant(authorized_media())
    provider.create_grant(authorized_media())

    client_factory.assert_called_once_with("s3", region_name="eu-west-1")
    assert client.generate_presigned_url.call_count == 2


def test_s3_provider_does_not_log_presigned_url(caplog) -> None:
    signed_url = "https://signed.invalid/object?signature=secret"
    client = Mock()
    client.generate_presigned_url.return_value = signed_url
    provider = S3DownloadAccessProvider(bucket_name="user-media", region_name="eu-west-1", client=client)

    provider.create_grant(authorized_media())

    assert signed_url not in caplog.text


def test_local_provider_returns_authenticated_domain_route_and_safe_path(tmp_path: Path) -> None:
    storage = Mock()
    storage.path_for_response.return_value = tmp_path / "image.jpg"
    storage.is_safe_key.return_value = True
    (tmp_path / "image.jpg").write_bytes(b"image")
    provider = LocalDownloadAccessProvider(storage)

    grant = provider.create_grant(authorized_media())
    path = provider.get_local_path(authorized_media())

    assert grant.url == "/media/recipe_image/image-1"
    assert grant.access_mode is DownloadAccessMode.AUTHENTICATED_FETCH
    assert grant.expires_at is None
    assert path == tmp_path / "image.jpg"
    storage.path_for_response.assert_called_once_with(StorageLocation.USER_MEDIA, authorized_media().storage_key)


def test_local_provider_rejects_unsafe_storage_key() -> None:
    storage = Mock()
    storage.is_safe_key.return_value = False
    provider = LocalDownloadAccessProvider(storage)

    with pytest.raises(MediaReferenceUnavailableError):
        provider.create_grant(authorized_media())

    storage.path_for_response.assert_not_called()
