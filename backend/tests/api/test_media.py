from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_media_serves_saved_files(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "image.jpg").write_bytes(b"image-bytes")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    get_settings.cache_clear()

    response = TestClient(create_app()).get("/media/image.jpg")

    assert response.status_code == 200
    assert response.content == b"image-bytes"
    get_settings.cache_clear()


def test_media_rejects_path_traversal(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    get_settings.cache_clear()

    response = TestClient(create_app()).get("/media/../secret.txt")

    assert response.status_code in {400, 404}
    get_settings.cache_clear()
