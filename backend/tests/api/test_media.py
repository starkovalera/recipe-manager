from fastapi.testclient import TestClient

from app.api.routes import media as media_routes
from app.main import create_app
from app.storage.constants import StorageLocation
from app.storage.local import LocalStorageService


def test_media_serves_nested_local_keys(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    nested = upload_dir / "recipes" / "media" / "owner-1" / "recipe-1"
    nested.mkdir(parents=True)
    (nested / "image.jpg").write_bytes(b"nested-image")
    storage = LocalStorageService(
        location_to_locator={
            StorageLocation.USER_MEDIA: upload_dir,
            StorageLocation.SYSTEM_ARTIFACTS: tmp_path / "system-artifacts",
        }
    )
    monkeypatch.setattr(media_routes, "get_storage_service", lambda: storage)

    response = TestClient(create_app()).get("/media/recipes/media/owner-1/recipe-1/image.jpg")

    assert response.status_code == 200
    assert response.content == b"nested-image"


def test_s3_media_access_fails_closed_without_reading_storage(monkeypatch):
    class S3StorageStub:
        def read(self, *_args):
            raise AssertionError("S3 media route must not read objects before P10")

    monkeypatch.setattr(media_routes, "get_storage_service", S3StorageStub)

    response = TestClient(create_app()).get("/media/recipes/media/owner/recipe/image.jpg")

    assert response.status_code == 503
    assert response.json() == {
        "errorCode": "MEDIA_ACCESS_NOT_AVAILABLE",
        "message": "Media access is temporarily unavailable.",
    }
