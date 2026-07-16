import base64
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from app.storage.base import StorageService, StoredFile

SUPPORTED_IMAGE_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


@dataclass(frozen=True)
class ValidatedImage:
    content: bytes
    mime_type: str
    original_name: str


def image_to_data_url(content: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((a[index] - b[index]) ** 2 for index in range(3)) ** 0.5


def _find_spans(values: list[float], threshold: float, min_length: int) -> list[tuple[int, int, float]]:
    spans: list[tuple[int, int, float]] = []
    start: int | None = None
    score = 0.0
    for index in range(len(values) + 1):
        value = values[index] if index < len(values) else 0
        if value >= threshold:
            if start is None:
                start = index
            score += value
        elif start is not None:
            if index - start >= min_length:
                spans.append((start, index, score))
            start = None
            score = 0.0
    return spans


def _detect_embedded_photo_crop(image: Image.Image) -> dict[str, float] | None:
    if image.width <= 0 or image.height <= 0:
        return None
    sample_width = 240
    sample_height = max(1, round(image.height * (sample_width / image.width)))
    sample = image.convert("RGB").resize((sample_width, sample_height))
    pixels = sample.load()
    background = pixels[0, 0]

    def different_from_background(x: int, y: int) -> bool:
        return _color_distance(pixels[x, y], background) > 55

    row_densities: list[float] = []
    for y in range(sample.height):
        count = sum(1 for x in range(sample.width) if different_from_background(x, y))
        row_densities.append(count / sample.width)
    row_spans = _find_spans(row_densities, 0.18, max(8, round(sample.height * 0.04)))
    if not row_spans:
        return None
    best_row = max(row_spans, key=lambda span: (span[1] - span[0]) * (span[2] / (span[1] - span[0])))

    col_densities: list[float] = []
    for x in range(sample.width):
        count = sum(1 for y in range(best_row[0], best_row[1]) if different_from_background(x, y))
        col_densities.append(count / (best_row[1] - best_row[0]))
    col_spans = _find_spans(col_densities, 0.18, max(8, round(sample.width * 0.12)))
    if not col_spans:
        return None
    best_col = max(col_spans, key=lambda span: (span[1] - span[0]) * (span[2] / (span[1] - span[0])))

    return {
        "x": best_col[0] / sample.width,
        "y": best_row[0] / sample.height,
        "width": (best_col[1] - best_col[0]) / sample.width,
        "height": (best_row[1] - best_row[0]) / sample.height,
    }


def _crop_box(width: int, height: int, crop: dict[str, float] | None) -> tuple[int, int, int, int]:
    if not crop:
        return (0, 0, width, height)
    x = float(crop.get("x", 0))
    y = float(crop.get("y", 0))
    crop_width = float(crop.get("width", 1))
    crop_height = float(crop.get("height", 1))
    uses_pixel_coordinates = any(abs(value) > 1 for value in (x, y, crop_width, crop_height))
    if uses_pixel_coordinates:
        left = int(max(0, min(width, x)))
        top = int(max(0, min(height, y)))
        right = int(max(0, min(width, x + crop_width)))
        bottom = int(max(0, min(height, y + crop_height)))
    else:
        left = int(max(0, min(width, width * x)))
        top = int(max(0, min(height, height * y)))
        right = int(max(0, min(width, width * (x + crop_width))))
        bottom = int(max(0, min(height, height * (y + crop_height))))
    if right <= left or bottom <= top:
        return (0, 0, width, height)
    return (left, top, right, bottom)


def create_cover_image(
    storage: StorageService,
    source_storage_key: str,
    crop: dict[str, float] | None = None,
    auto_crop_full_image: bool = False,
) -> StoredFile:
    source_bytes = storage.read(source_storage_key)
    with Image.open(BytesIO(source_bytes)) as source:
        image = source.convert("RGB")
        detected_crop = _detect_embedded_photo_crop(image) if auto_crop_full_image else None
        cropped = image.crop(_crop_box(image.width, image.height, detected_crop or crop))
        cropped.thumbnail((1200, 1200))
        output = BytesIO()
        cropped.save(output, format="JPEG", quality=88)
    return storage.save(output.getvalue(), "cover.jpg", "image/jpeg")
