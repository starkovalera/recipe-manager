from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image

from app.core.config import get_settings
from app.core.errors import (
    FileTooLargeError,
    InvalidFileTypeError,
    NoImportSourcesError,
    TextTooLongError,
    TooManyFilesError,
)
from app.imports.constants import SUPPORTED_UPLOAD_TYPES
from app.media.images import ValidatedImage


@dataclass(frozen=True)
class ValidatedImportRequest:
    text: str | None
    url: str | None
    images: list[ValidatedImage]


def validate_import_request(
    text: str | None,
    url: str | None,
    files: list[UploadFile],
) -> ValidatedImportRequest:
    settings = get_settings()
    normalized_text = text.strip() if text else None
    normalized_url = url.strip() if url else None
    validated_images: list[ValidatedImage] = []

    if not normalized_text and not normalized_url and not files:
        raise NoImportSourcesError()
    if normalized_text and len(normalized_text) > settings.max_import_text_chars:
        raise TextTooLongError(max_length=settings.max_import_text_chars)
    if len(files) > settings.max_import_images:
        raise TooManyFilesError(max_files=settings.max_import_images)

    for upload in files:
        content_type = upload.content_type or ""
        original_filename = upload.filename or "upload"
        if content_type not in SUPPORTED_UPLOAD_TYPES:
            raise InvalidFileTypeError(content_type=content_type, filename=original_filename)

        content = upload.file.read()
        if len(content) > settings.max_upload_bytes:
            raise FileTooLargeError(max_size_bytes=settings.max_upload_bytes)
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        except (OSError, ValueError) as error:
            raise InvalidFileTypeError(
                content_type=content_type,
                filename=original_filename,
                original_error=str(error),
            ) from error
        validated_images.append(
            ValidatedImage(
                content=content,
                mime_type=content_type,
                original_name=original_filename,
            )
        )

    return ValidatedImportRequest(
        text=normalized_text,
        url=normalized_url,
        images=validated_images,
    )
