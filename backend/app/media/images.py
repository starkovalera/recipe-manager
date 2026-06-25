import base64
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from app.storage.base import StoredFile, StorageService

SUPPORTED_IMAGE_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


@dataclass(frozen=True)
class ValidatedImage:
    content: bytes
    mime_type: str
    original_name: str


def validate_image_upload(content: bytes, mime_type: str, original_name: str) -> ValidatedImage:
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {mime_type}")
    with Image.open(BytesIO(content)) as image:
        image.verify()
    return ValidatedImage(content=content, mime_type=mime_type, original_name=original_name)


def image_to_data_url(content: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _crop_box(width: int, height: int, crop: dict[str, float] | None) -> tuple[int, int, int, int]:
    if not crop:
        return (0, 0, width, height)
    left = max(0, min(width, int(width * crop.get("x", 0))))
    top = max(0, min(height, int(height * crop.get("y", 0))))
    right = max(left + 1, min(width, int(width * (crop.get("x", 0) + crop.get("width", 1)))))
    bottom = max(top + 1, min(height, int(height * (crop.get("y", 0) + crop.get("height", 1)))))
    return (left, top, right, bottom)


def create_cover_image(storage: StorageService, source_storage_key: str, crop: dict[str, float] | None = None) -> StoredFile:
    source_bytes = storage.read(source_storage_key)
    with Image.open(BytesIO(source_bytes)) as source:
        image = source.convert("RGB")
        cropped = image.crop(_crop_box(image.width, image.height, crop))
        cropped.thumbnail((1200, 1200))
        output = BytesIO()
        cropped.save(output, format="JPEG", quality=88)
    return storage.save(output.getvalue(), "cover.jpg", "image/jpeg")
