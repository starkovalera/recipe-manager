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


def test_create_cover_image_accepts_pixel_crop_from_ai(tmp_path: Path):
    storage = LocalStorageService(tmp_path / "uploads")
    source_path = tmp_path / "source.jpg"
    image = Image.new("RGB", (100, 80), color=(200, 20, 20))
    image.save(source_path, format="JPEG")
    source = storage.save(source_path.read_bytes(), "source.jpg", "image/jpeg")

    cover = create_cover_image(storage, source.storage_key, crop={"x": 10, "y": 20, "width": 40, "height": 30})

    with Image.open(tmp_path / "uploads" / cover.storage_key) as cover_image:
        assert cover_image.size == (40, 30)


def test_create_cover_image_falls_back_to_full_image_for_invalid_crop(tmp_path: Path):
    storage = LocalStorageService(tmp_path / "uploads")
    source = storage.save(jpeg_bytes(tmp_path / "source.jpg"), "source.jpg", "image/jpeg")

    cover = create_cover_image(storage, source.storage_key, crop={"x": 0, "y": 130, "width": 1, "height": 1})

    with Image.open(tmp_path / "uploads" / cover.storage_key) as cover_image:
        assert cover_image.size == (80, 40)


def test_create_cover_image_auto_crops_largest_embedded_photo(tmp_path: Path):
    storage = LocalStorageService(tmp_path / "uploads")
    source_path = tmp_path / "screenshot.png"
    image = Image.new("RGB", (400, 800), color=(5, 5, 5))
    food = Image.new("RGB", (240, 170), color=(213, 106, 54))
    sidebar = Image.new("RGB", (100, 170), color=(185, 214, 234))
    image.paste(food, (24, 120))
    image.paste(sidebar, (282, 120))
    image.save(source_path, format="PNG")
    source = storage.save(source_path.read_bytes(), "screenshot.png", "image/png")

    cover = create_cover_image(
        storage,
        source.storage_key,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
        auto_crop_full_image=True,
    )

    with Image.open(tmp_path / "uploads" / cover.storage_key) as cover_image:
        assert 230 <= cover_image.width <= 260
        assert 160 <= cover_image.height <= 190
