from collections.abc import Mapping
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError, StorageOperationError
from app.storage.keys import build_storage_key
from app.storage.types import StorageLocator, StorageWriteContext, StoredFile


def _read_response_body(body: Any) -> bytes:
    try:
        content = body.read()
    except Exception as error:
        try:
            body.close()
        except Exception:
            pass
        raise StorageOperationError("S3 storage read failed.") from error
    try:
        body.close()
    except Exception as error:
        raise StorageOperationError("S3 storage response close failed.") from error
    return content


class S3StorageService(StorageService):
    def __init__(
        self,
        *,
        location_to_locator: Mapping[StorageLocation, StorageLocator],
        region_name: str,
        client: Any | None = None,
    ) -> None:
        if not region_name.strip():
            raise StorageConfigurationError("S3 storage requires a nonblank region name.")

        buckets: dict[StorageLocation, str] = {}
        for location in StorageLocation:
            locator = location_to_locator.get(location)
            if locator is None:
                raise StorageConfigurationError(f"Storage location {location.value} is not configured.")
            if not isinstance(locator, str) or not locator.strip():
                raise StorageConfigurationError(f"S3 storage location {location.value} requires a bucket name.")
            buckets[location] = locator

        self._buckets = buckets
        self._region_name = region_name.strip()
        self._client = client

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client("s3", region_name=self._region_name)
        return self._client

    def _bucket_for(self, location: StorageLocation) -> str:
        bucket = self._buckets.get(location)
        if bucket is None:
            raise StorageConfigurationError(f"Storage location {location.value} is not configured.")
        return bucket

    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageWriteContext,
    ) -> StoredFile:
        storage_key = build_storage_key(context, mime_type=mime_type)
        try:
            self._get_client().put_object(
                Bucket=self._bucket_for(location),
                Key=storage_key,
                Body=content,
                ContentType=mime_type,
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageOperationError("S3 storage write failed.") from error
        return StoredFile(
            storage_key=storage_key,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(content),
        )

    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        try:
            response = self._get_client().get_object(
                Bucket=self._bucket_for(location),
                Key=storage_key,
            )
        except ClientError as error:
            error_code = str(error.response.get("Error", {}).get("Code", ""))
            status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in {"NoSuchKey", "NotFound", "404"} or status_code == 404:
                raise StorageObjectNotFoundError("Storage object was not found.") from error
            raise StorageOperationError("S3 storage read failed.") from error
        except BotoCoreError as error:
            raise StorageOperationError("S3 storage read failed.") from error

        try:
            body = response["Body"]
        except (KeyError, TypeError) as error:
            raise StorageOperationError("S3 storage response body is missing.") from error
        return _read_response_body(body)

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        try:
            self._get_client().delete_object(
                Bucket=self._bucket_for(location),
                Key=storage_key,
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageOperationError("S3 storage delete failed.") from error
