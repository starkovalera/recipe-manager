from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import media as media_routes
from app.core.errors import MediaAccessNotAvailableError
from app.db import session as session_module
from app.db.base import Base
from app.db.session import get_session
from app.local.users import ensure_default_user
from app.main import create_app
from app.media.access.constants import DownloadAccessMode
from app.media.access.types import AuthorizedMedia, DownloadGrant
from app.models import Recipe, RecipeImage, RecipeStatus, User
from app.storage.constants import StorageLocation
from app.storage.local import LocalStorageService
from tests.api.support import install_local_user_override


class LocalAccessProvider:
    def __init__(self, storage: LocalStorageService) -> None:
        self.storage = storage

    def create_grant(self, media: AuthorizedMedia) -> DownloadGrant:
        return DownloadGrant(
            url=f"/media/{media.reference.type.value}/{media.reference.id}",
            expires_at=None,
            content_type=media.content_type,
            access_mode=DownloadAccessMode.AUTHENTICATED_FETCH,
        )

    def get_local_path(self, media: AuthorizedMedia):
        return self.storage.path_for_response(media.location, media.storage_key)


class UnavailableAccessProvider:
    def create_grant(self, _media: AuthorizedMedia) -> DownloadGrant:
        raise MediaAccessNotAvailableError()

    def get_local_path(self, _media: AuthorizedMedia):
        raise MediaAccessNotAvailableError()


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session_module.SessionLocal = session_factory

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    install_local_user_override(app, session_factory)
    return TestClient(app), session_factory


def seed_images(session_factory, storage: LocalStorageService) -> tuple[str, str]:
    with session_factory() as session:
        owner = ensure_default_user(session)
        foreign = User(id="foreign-user", email="foreign@example.test")
        recipe = Recipe(owner=owner, title="Soup", status=RecipeStatus.ACTIVE)
        foreign_recipe = Recipe(owner=foreign, title="Foreign", status=RecipeStatus.ACTIVE)
        image = RecipeImage(
            recipe=recipe,
            storage_key="recipes/media/local-user/recipe-1/image.jpg",
            original_name="image.jpg",
            mime_type="image/jpeg",
            size_bytes=12,
            position=0,
        )
        foreign_image = RecipeImage(
            recipe=foreign_recipe,
            storage_key="recipes/media/foreign-user/recipe-2/image.jpg",
            original_name="image.jpg",
            mime_type="image/jpeg",
            size_bytes=7,
            position=0,
        )
        session.add_all([recipe, foreign_recipe])
        session.flush()
        image_id = image.id
        foreign_image_id = foreign_image.id
        session.commit()
    image_path = storage.path_for_response(StorageLocation.USER_MEDIA, "recipes/media/local-user/recipe-1/image.jpg")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"nested-image")
    return image_id, foreign_image_id


def test_media_access_and_local_get_use_stable_ids(tmp_path, monkeypatch) -> None:
    client, session_factory = client_with_session()
    storage = LocalStorageService(
        location_to_locator={
            StorageLocation.USER_MEDIA: tmp_path / "uploads",
            StorageLocation.SYSTEM_ARTIFACTS: tmp_path / "system-artifacts",
        }
    )
    image_id, foreign_image_id = seed_images(session_factory, storage)
    monkeypatch.setattr(media_routes, "get_download_access_provider", lambda: LocalAccessProvider(storage))

    response = client.post(
        "/media/access",
        json={
            "items": [
                {"type": "recipe_image", "id": image_id},
                {"type": "recipe_image", "id": foreign_image_id},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["grant"] == {
        "url": f"/media/recipe_image/{image_id}",
        "expiresAt": None,
        "contentType": "image/jpeg",
        "accessMode": "authenticated_fetch",
    }
    assert response.json()["items"][1]["error"]["code"] == "MEDIA_NOT_FOUND"

    media_response = client.get(f"/media/recipe_image/{image_id}")
    assert media_response.status_code == 200
    assert media_response.content == b"nested-image"
    assert media_response.headers["content-type"] == "image/jpeg"

    assert client.get(f"/media/recipe_image/{foreign_image_id}").status_code == 404
    assert client.get("/media/recipe_image/missing").status_code == 404


def test_provider_wide_failure_returns_503(monkeypatch) -> None:
    client, session_factory = client_with_session()
    with session_factory() as session:
        owner = ensure_default_user(session)
        recipe = Recipe(owner=owner, title="Soup")
        image = RecipeImage(
            recipe=recipe,
            storage_key="recipes/media/local-user/recipe-1/image.jpg",
            original_name="image.jpg",
            mime_type="image/jpeg",
            size_bytes=1,
            position=0,
        )
        session.add(recipe)
        session.flush()
        image_id = image.id
        session.commit()
    monkeypatch.setattr(media_routes, "get_download_access_provider", UnavailableAccessProvider)

    response = client.post("/media/access", json={"items": [{"type": "recipe_image", "id": image_id}]})

    assert response.status_code == 503
    assert response.json() == {
        "errorCode": "MEDIA_ACCESS_NOT_AVAILABLE",
        "message": "Media access is temporarily unavailable.",
    }


def test_media_access_requires_authentication() -> None:
    response = TestClient(create_app()).post(
        "/media/access",
        json={"items": [{"type": "recipe_image", "id": "image-1"}]},
    )

    assert response.status_code == 401
