from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors import MediaAccessNotAvailableError
from app.media.access.constants import PRESIGNED_MEDIA_TTL_SECONDS, DownloadAccessMode
from app.media.access.types import AuthorizedMedia, DownloadGrant


class S3DownloadAccessProvider:
    def __init__(
        self,
        *,
        bucket_name: str,
        region_name: str,
        endpoint_url: str | None = None,
        client: Any | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._client = client
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get_client(self):
        if self._client is None:
            client_options = {"region_name": self._region_name}
            if self._endpoint_url is not None:
                client_options["endpoint_url"] = self._endpoint_url
            self._client = boto3.client("s3", **client_options)
        return self._client

    def create_grant(self, media: AuthorizedMedia) -> DownloadGrant:
        try:
            url = self._get_client().generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket_name, "Key": media.storage_key},
                ExpiresIn=PRESIGNED_MEDIA_TTL_SECONDS,
            )
        except (BotoCoreError, ClientError) as error:
            raise MediaAccessNotAvailableError() from error
        signed_at = self._clock().astimezone(timezone.utc)
        return DownloadGrant(
            url=url,
            expires_at=signed_at + timedelta(seconds=PRESIGNED_MEDIA_TTL_SECONDS),
            content_type=media.content_type,
            access_mode=DownloadAccessMode.DIRECT,
        )

    def get_local_path(self, media: AuthorizedMedia) -> Path:
        raise MediaAccessNotAvailableError()
