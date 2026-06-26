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
            author_name="url_author",
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


class CapturingProvider(FakeRecipeExtractionProvider):
    def __init__(self):
        self.sources = []

    async def extract(self, sources):
        self.sources = sources
        return await super().extract(sources)


def test_url_author_name_is_passed_to_ai_sources():
    client = client_with_session()
    registry = FakeRegistry()
    provider = CapturingProvider()
    set_url_content_loader_registry(registry)
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "url-author", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 200
    url_source = next(source for source in provider.sources if source.type == "URL")
    assert url_source.authorName == "url_author"


def test_threads_url_import_sets_recipe_source_name():
    client = client_with_session()
    set_url_content_loader_registry(FakeRegistry())

    response = client.post(
        "/imports",
        data={"clientImportId": "threads-url", "url": "https://www.threads.com/@cook/post/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "THREADS"


def test_instagram_url_import_sets_recipe_source_name():
    client = client_with_session()
    set_url_content_loader_registry(FakeRegistry())

    response = client.post(
        "/imports",
        data={"clientImportId": "instagram-url", "url": "https://www.instagram.com/p/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "INSTAGRAM"


def test_mixed_sources_match_reference_ai_source_order_and_refs():
    client = client_with_session()
    registry = FakeRegistry()
    provider = CapturingProvider()
    set_url_content_loader_registry(registry)
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "mixed-source-order", "text": "Manual recipe text", "url": "https://example.com/recipe"},
        files=[("files", ("first.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 200
    assert [(source.type, source.sourceRef, source.position) for source in provider.sources] == [
        ("IMAGE", "source_0", 0),
        ("TEXT", None, 1),
        ("URL", None, 2),
        ("IMAGE", "url_slide_0", 3),
    ]


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


class SourceAssessmentProvider:
    async def extract(self, sources):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Assessed recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    hasConflicts=True,
                    hasIgnored=True,
                    primarySourceRefs=["source_0", "https://example.com/recipe"],
                    ignoredSourceRefs=["url_slide_0"],
                ),
            )
        )


def test_ai_quality_refs_set_recipe_source_statuses_after_normalization():
    client = client_with_session()
    set_url_content_loader_registry(FakeRegistry())
    set_recipe_extraction_provider(SourceAssessmentProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "source-statuses", "url": "https://example.com/recipe"},
        files=[("files", ("first.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    statuses = {source["sourceRef"]: source["status"] for source in detail.json()["sources"]}
    assert statuses["image:source_0"] == "used"
    assert statuses["url:1"] == "used"
    assert statuses["image:url_slide_0"] == "ignored"


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


class WarningFlagProvider:
    async def extract(self, sources):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Warning recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.7,
                    hasConflicts=True,
                    hasIgnored=True,
                    primarySourceRefs=["text:0"],
                    ignoredSourceRefs=[],
                ),
            )
        )


def test_warning_flag_reasons_match_reference_import_rules():
    client = client_with_session()
    set_recipe_extraction_provider(WarningFlagProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "warning-flag", "text": "Recipe text"},
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    flags = detail.json()["reviewFlags"]
    assert len(flags) == 1
    assert flags[0]["type"] == "CONTENT_WARNING"
    assert flags[0]["reasonCode"] == "CONTENT_CONFLICT"
    assert flags[0]["details"]["reasons"] == ["CONTENT_CONFLICT", "IGNORED_SOURCES", "LOW_CONFIDENCE"]


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
