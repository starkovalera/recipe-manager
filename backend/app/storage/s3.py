from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError, StorageOperationError
from app.storage.types import StorageLocator, StorageObjectInfo, StorageObjectPage, StorageSaveContext, StoredFile


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
        context: StorageSaveContext,
    ) -> StoredFile:
        storage_key = context.build_storage_key(original_name=original_name, mime_type=mime_type)
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

    def list_objects(
        self,
        location: StorageLocation,
        *,
        prefix: str,
        limit: int,
        cursor: str | None = None,
    ) -> StorageObjectPage:
        if not 1 <= limit <= 1000:
            raise ValueError("Storage listing limit must be between 1 and 1000.")
        posix_prefix = PurePosixPath(prefix or ".")
        windows_prefix = PureWindowsPath(prefix or ".")
        if posix_prefix.is_absolute() or windows_prefix.is_absolute() or ".." in posix_prefix.parts or ".." in windows_prefix.parts:
            raise ValueError("Storage listing prefix must be a safe relative prefix.")

        request = {
            "Bucket": self._bucket_for(location),
            "Prefix": prefix,
            "MaxKeys": limit,
        }
        if cursor is not None:
            request["ContinuationToken"] = cursor
        try:
            response = self._get_client().list_objects_v2(**request)
        except (BotoCoreError, ClientError) as error:
            raise StorageOperationError("S3 storage listing failed.") from error

        try:
            contents = response.get("Contents", [])
            if not isinstance(contents, list):
                raise TypeError
            objects = []
            for item in contents:
                storage_key = item["Key"]
                size_bytes = item["Size"]
                last_modified_at = item["LastModified"]
                if not isinstance(storage_key, str) or not isinstance(size_bytes, int) or not isinstance(last_modified_at, datetime):
                    raise TypeError
                if last_modified_at.tzinfo is None:
                    last_modified_at = last_modified_at.replace(tzinfo=timezone.utc)
                objects.append(
                    StorageObjectInfo(
                        storage_key=storage_key,
                        size_bytes=size_bytes,
                        last_modified_at=last_modified_at.astimezone(timezone.utc),
                    )
                )
            next_cursor = response.get("NextContinuationToken")
            if next_cursor is not None and not isinstance(next_cursor, str):
                raise TypeError
        except (KeyError, TypeError) as error:
            raise StorageOperationError("S3 storage listing response is invalid.") from error

        return StorageObjectPage(objects=tuple(objects), next_cursor=next_cursor)
