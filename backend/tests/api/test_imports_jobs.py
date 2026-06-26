from collections.abc import Generator
import logging

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from PIL import Image
from io import BytesIO

import pytest
from app.db.base import Base
from app.db.session import get_session
from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.schemas import CoverCandidate, ExtractedRecipe, ExtractionQuality, ExtractionResult
from app.imports.jobs import (
    DefaultUrlContentRegistry,
    reset_recipe_extraction_provider,
    set_recipe_extraction_provider,
    set_url_content_loader_registry,
)
from app.imports.url_loaders.types import LoadedRemoteImage, LoadedUrlContent
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_import_dependencies():
    set_recipe_extraction_provider(FakeRecipeExtractionProvider())
    set_url_content_loader_registry(DefaultUrlContentRegistry())
    yield
    set_recipe_extraction_provider(FakeRecipeExtractionProvider())
    set_url_content_loader_registry(DefaultUrlContentRegistry())


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def image_bytes() -> bytes:
    out = BytesIO()
    Image.new("RGB", (20, 20), color=(255, 0, 0)).save(out, format="JPEG")
    return out.getvalue()


def test_text_import_creates_job_and_polling_returns_recipe():
    client = client_with_session()

    created = client.post(
        "/imports",
        data={"clientImportId": "import-1", "text": "Tomato soup recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    job_id = created.json()["jobId"]
    polled = client.get(f"/imports/{job_id}")

    assert created.status_code == 200
    assert created.json()["status"] in {"pending", "processing", "succeeded"}
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["createdRecipeId"]


def test_duplicate_client_import_id_returns_existing_job():
    client = client_with_session()

    first = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})
    second = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["jobId"] == first.json()["jobId"]


def test_import_requires_at_least_one_source():
    client = client_with_session()

    response = client.post("/imports", data={"clientImportId": "empty"}, headers={"X-Client-Id": "client-1"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "NOT_A_RECIPE"


def test_import_rejects_text_over_limit_before_job_creation():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "long-text", "text": "x" * 501},
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TEXT_TOO_LONG"


def test_import_rejects_too_many_files_before_processing():
    client = client_with_session()
    files = [("files", (f"{index}.jpg", b"not-real-image", "image/jpeg")) for index in range(11)]

    response = client.post(
        "/imports",
        data={"clientImportId": "too-many"},
        files=files,
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TOO_MANY_FILES"


def test_import_rejects_unsupported_file_type():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "bad-file"},
        files=[("files", ("recipe.txt", b"hello", "text/plain"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_FILE_TYPE"


def test_image_attachment_import_creates_image_source():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "image-import"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert detail.json()["sources"][0]["type"] == "IMAGE"
    assert detail.json()["sources"][0]["status"] == "used"


class FakeRegistry:
    def __init__(self):
        self.max_images_seen: int | None = None

    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        self.max_images_seen = max_images
        return LoadedUrlContent(
            url=url,
            text="URL recipe text",
            images=[
                LoadedRemoteImage(bytes=image_bytes(), mime_type="image/jpeg", original_name="remote.jpg", url=f"{url}/remote.jpg", position=0)
            ][:max_images],
        )


def test_url_images_use_remaining_capacity_after_attachments():
    client = client_with_session()
    registry = FakeRegistry()
    set_url_content_loader_registry(registry)

    response = client.post(
        "/imports",
        data={"clientImportId": "mixed", "url": "https://example.com/recipe"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert registry.max_images_seen == 9
    assert [source["type"] for source in detail.json()["sources"]] == ["IMAGE", "URL", "IMAGE"]


class LowConfidenceProvider:
    async def extract(self, sources):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Low confidence recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0,
                    hasConflicts=False,
                    hasIgnored=False,
                    primarySourceRefs=[],
                    ignoredSourceRefs=[],
                ),
            )
        )


def test_low_confidence_import_fails_and_cleans_uploaded_files():
    client = client_with_session()
    set_recipe_extraction_provider(LowConfidenceProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "low-confidence"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errorCode"] == "NOT_A_RECIPE"


class CoverCandidateProvider:
    async def extract(self, sources):
        image_ref = next(source.sourceRef for source in sources if source.type == "IMAGE")
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Cover recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    hasConflicts=False,
                    hasIgnored=False,
                    primarySourceRefs=[f"image:{image_ref}"],
                    ignoredSourceRefs=[],
                ),
                coverCandidate=CoverCandidate(sourceRef=f"image:{image_ref}", sourcePosition=0),
            )
        )


def test_cover_candidate_creates_cover_image():
    client = client_with_session()
    set_recipe_extraction_provider(CoverCandidateProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "cover"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["coverImage"]["role"] == "COVER"
    assert detail.json()["images"][0]["role"] == "SOURCE"


def test_import_logs_lifecycle_without_image_payloads(caplog):
    client = client_with_session()
    caplog.set_level(logging.INFO, logger="recipes.import")

    response = client.post(
        "/imports",
        data={"clientImportId": "logged"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    joined = "\n".join(messages)
    assert "[recipes.import] Import job created" in joined
    assert "[recipes.import] AI extraction quality" in joined
    assert "[recipes.import] Import job succeeded" in joined
    assert "data:image" not in joined
    assert "base64" not in joined
