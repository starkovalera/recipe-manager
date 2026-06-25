from pathlib import Path

from PIL import Image

from app.media.images import create_cover_image, image_to_data_url, validate_image_upload
from app.storage.local import LocalStorageService


def jpeg_bytes(path: Path) -> bytes:
    image = Image.new("RGB", (80, 40), color=(200, 20, 20))
    image.save(path, format="JPEG")
    return path.read_bytes()


def test_validate_image_upload_accepts_jpeg(tmp_path: Path):
    data = jpeg_bytes(tmp_path / "source.jpg")

    result = validate_image_upload(data, "image/jpeg", "source.jpg")

    assert result.mime_type == "image/jpeg"
    assert result.original_name == "source.jpg"


def test_image_to_data_url_encodes_bytes():
    assert image_to_data_url(b"abc", "image/png") == "data:image/png;base64,YWJj"


def test_create_cover_image_saves_derivative_without_mutating_source(tmp_path: Path):
    storage = LocalStorageService(tmp_path / "uploads")
    source = storage.save(jpeg_bytes(tmp_path / "source.jpg"), "source.jpg", "image/jpeg")

    cover = create_cover_image(storage, source.storage_key, crop={"x": 0, "y": 0, "width": 0.5, "height": 1})

    assert cover.storage_key != source.storage_key
    assert cover.mime_type == "image/jpeg"
    assert storage.read(source.storage_key) != storage.read(cover.storage_key)
