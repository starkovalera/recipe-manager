from unittest.mock import Mock

from app.core.config import AppEnv, Settings
from app.core.infrastructure import StorageProvider
from app.media.access.runtime import get_download_access_provider
from app.media.access.s3 import S3DownloadAccessProvider


def test_download_access_provider_passes_custom_s3_endpoint(monkeypatch) -> None:
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        storage_provider=StorageProvider.S3,
        aws_region="us-east-1",
        aws_endpoint_url_s3="http://s3.localhost.localstack.cloud:4566",
        s3_user_media_bucket_name="recipe-manager-local-user-media",
        s3_system_artifacts_bucket_name="recipe-manager-local-system-artifacts",
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )
    provider_factory = Mock(return_value=Mock(spec=S3DownloadAccessProvider))
    monkeypatch.setattr("app.media.access.runtime.S3DownloadAccessProvider", provider_factory)

    get_download_access_provider(settings)

    provider_factory.assert_called_once_with(
        bucket_name="recipe-manager-local-user-media",
        region_name="us-east-1",
        endpoint_url="http://s3.localhost.localstack.cloud:4566",
    )
