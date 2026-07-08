import logging
from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.schemas import CoverCandidate, ExtractedRecipe, ExtractionQuality, ExtractionResult
from app.api.routes import imports as import_routes
from app.core.config import get_settings
from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.imports.jobs import (
    process_import_job,
)
from app.imports.source_loading.url_loaders.types import LoadedRemoteImage, LoadedRemoteVideo, LoadedUrlContent
from app.main import create_app
from app.models import ImportEventType, ImportJob, ImportJobStatus, Ingredient, Notification, NotificationType, Recipe
from tests.imports.runtime_overrides import (
    reset_url_content_service,
    reset_video_processor,
    set_recipe_extraction_provider,
    set_url_content_service,
    set_video_processor,
)


@pytest.fixture(autouse=True)
def reset_import_dependencies(monkeypatch):
    monkeypatch.setenv("MAX_IMPORT_TEXT_CHARS", "1000")
    monkeypatch.setenv("MAX_RECIPE_INGREDIENTS", "50")
    monkeypatch.setenv("MAX_RECIPE_INSTRUCTION_CHARS", "1000")
    monkeypatch.setenv("MAX_RECIPE_NOTE_CHARS", "500")
    monkeypatch.setenv("MAX_PARALLEL_IMPORTS_PER_CLIENT", "3")
    get_settings.cache_clear()
    set_recipe_extraction_provider(FakeRecipeExtractionProvider())
    reset_url_content_service()
    monkeypatch.setattr(import_routes, "enqueue_import_job", lambda import_job_id: None, raising=False)
    monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", lambda recipe_id: None)
    yield
    set_recipe_extraction_provider(FakeRecipeExtractionProvider())
    reset_url_content_service()
    reset_video_processor()
    get_settings.cache_clear()


def client_with_session_factory():
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
    app.state.SessionLocal = SessionLocal
    return TestClient(app), SessionLocal


def client_with_session():
    client, _ = client_with_session_factory()
    return client


def image_bytes() -> bytes:
    out = BytesIO()
    Image.new("RGB", (20, 20), color=(255, 0, 0)).save(out, format="JPEG")
    return out.getvalue()


def run_import_worker(client: TestClient, job_id: str) -> None:
    with client.app.state.SessionLocal() as session:
        process_import_job(session, job_id)


def poll_import(client: TestClient, job_id: str):
    return client.get(f"/imports/{job_id}")


def process_import_response(client: TestClient, response):
    assert response.status_code == 202
    job_id = response.json()["jobId"]
    run_import_worker(client, job_id)
    return poll_import(client, job_id)


def test_text_import_creates_job_and_polling_returns_recipe():
    client = client_with_session()

    created = client.post(
        "/imports",
        data={"clientImportId": "import-1", "text": "Tomato soup recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    job_id = created.json()["jobId"]
    polled = client.get(f"/imports/{job_id}")

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert polled.status_code == 200
    assert polled.json()["status"] == "queued"
    assert polled.json()["createdRecipeId"] is None

    run_import_worker(client, job_id)
    completed = poll_import(client, job_id)

    assert completed.json()["status"] == "succeeded"
    assert completed.json()["createdRecipeId"]


def test_text_import_sets_ingredient_search_name():
    client, SessionLocal = client_with_session_factory()

    created = client.post(
        "/imports",
        data={"clientImportId": "import-search-name", "text": "Tomato soup recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    completed = process_import_response(client, created)
    recipe_id = completed.json()["createdRecipeId"]

    with SessionLocal() as session:
        ingredient = session.query(Ingredient).filter_by(recipe_id=recipe_id).one()

    assert ingredient.search_name == "ingredient"


def test_text_import_sets_recipe_search_text_and_hash():
    client, SessionLocal = client_with_session_factory()

    created = client.post(
        "/imports",
        data={"clientImportId": "import-recipe-search-text", "text": "Tomato soup recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    completed = process_import_response(client, created)
    recipe_id = completed.json()["createdRecipeId"]

    with SessionLocal() as session:
        recipe = session.query(Recipe).filter_by(id=recipe_id).one()

    assert recipe.search_text is not None
    assert "imported recipe" in recipe.search_text
    assert "ingredient" in recipe.search_text
    assert recipe.search_text_hash is not None
    assert len(recipe.search_text_hash) == 64


def test_duplicate_client_import_id_returns_existing_job():
    client = client_with_session()

    first = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})
    second = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["jobId"] == first.json()["jobId"]


def test_import_records_job_events_and_notifications():
    client, SessionLocal = client_with_session_factory()

    response = client.post("/imports", data={"clientImportId": "evented", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})

    assert response.status_code == 202
    with SessionLocal() as session:
        job = session.get(ImportJob, response.json()["jobId"])
        notifications = session.query(Notification).order_by(Notification.created_at).all()

        assert [event.event_type for event in job.events] == [ImportEventType.IMPORT_CREATED]
        assert [notification.type for notification in notifications] == [NotificationType.IMPORT_STARTED]

    run_import_worker(client, response.json()["jobId"])
    with SessionLocal() as session:
        job = session.get(ImportJob, response.json()["jobId"])
        notifications = session.query(Notification).order_by(Notification.created_at).all()

        assert [event.event_type for event in job.events] == [
            ImportEventType.IMPORT_CREATED,
            ImportEventType.IMPORT_STARTED,
            ImportEventType.RAW_SOURCES_DOWNLOADED,
            ImportEventType.EXTRACTOR_REQUESTED,
            ImportEventType.EXTRACTOR_SUCCEEDED,
            ImportEventType.RECIPE_CREATED,
        ]
        assert [notification.type for notification in notifications] == [NotificationType.IMPORT_STARTED, NotificationType.IMPORT_SUCCEEDED]


def test_active_import_limit_uses_database_state():
    client, SessionLocal = client_with_session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        for index in range(2):
            session.add(
                ImportJob(
                    owner_id=user.id,
                    client_id=f"client-{index}",
                    client_import_id=f"active-{index}",
                    dedupe_key=f"active-{index}",
                    status=ImportJobStatus.QUEUED,
                )
            )
        session.commit()

    response = client.post("/imports", data={"clientImportId": "third", "text": "Recipe"}, headers={"X-Client-Id": "client-3"})

    assert response.status_code == 202

    blocked = client.post("/imports", data={"clientImportId": "fourth", "text": "Recipe"}, headers={"X-Client-Id": "client-4"})

    assert blocked.status_code == 400
    assert blocked.json()["errorCode"] == "ACTIVE_IMPORT_EXISTS"


def test_idempotency_key_returns_existing_job_for_different_client_import_id():
    client = client_with_session()

    first = client.post(
        "/imports",
        data={"clientImportId": "first", "text": "Recipe"},
        headers={"X-Client-Id": "client-1", "Idempotency-Key": "same-key"},
    )
    second = client.post(
        "/imports",
        data={"clientImportId": "second", "text": "Recipe"},
        headers={"X-Client-Id": "client-1", "Idempotency-Key": "same-key"},
    )

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["jobId"] == first.json()["jobId"]


def test_create_import_enqueues_job(monkeypatch):
    enqueued: list[str] = []
    monkeypatch.setattr(import_routes, "enqueue_import_job", enqueued.append)
    client = client_with_session()

    response = client.post("/imports", data={"clientImportId": "queued", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert enqueued == [response.json()["jobId"]]


def test_import_requires_at_least_one_source():
    client = client_with_session()

    response = client.post("/imports", data={"clientImportId": "empty"}, headers={"X-Client-Id": "client-1"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "NO_IMPORT_SOURCES"


def test_import_rejects_text_over_limit_before_job_creation():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "long-text", "text": "x" * 1001},
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TEXT_TOO_LONG"


def test_import_accepts_text_at_limit_before_job_creation():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "limit-text", "text": "x" * 1000},
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 202


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


def test_import_rejects_invalid_image_payload_before_job_creation():
    client, SessionLocal = client_with_session_factory()

    response = client.post(
        "/imports",
        data={"clientImportId": "invalid-image-upload"},
        files=[("files", ("recipe.jpg", b"not-real-image", "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_FILE_TYPE"
    with SessionLocal() as session:
        assert session.query(ImportJob).count() == 0


def test_image_attachment_import_creates_image_source():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "image-import"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
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


class FakeVideoRegistry:
    def __init__(self):
        self.max_images_seen: int | None = None

    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        self.max_images_seen = max_images
        return LoadedUrlContent(
            url=url,
            author_name="url_author",
            text="URL recipe text",
            images=[],
            videos=[
                LoadedRemoteVideo(
                    url=f"{url}/video.mp4",
                    poster_url=f"{url}/poster.jpg",
                    position=0,
                    original_name="video.mp4",
                )
            ],
        )


class FailingRegistry:
    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        raise RuntimeError("secondary source failed")


class FakeVideoProcessor:
    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes, max_video_bytes):
        return {
            "poster_images": [
                LoadedRemoteImage(
                    bytes=image_bytes(),
                    mime_type="image/jpeg",
                    original_name="poster-video.mp4.jpg",
                    url=videos[0].poster_url,
                    position=videos[0].position,
                )
            ],
            "transcript_text": "Video 1 transcript:\nMix batter and bake.",
        }


def test_url_images_use_remaining_capacity_after_attachments():
    client = client_with_session()
    registry = FakeRegistry()
    set_url_content_service(registry)

    response = client.post(
        "/imports",
        data={"clientImportId": "mixed", "url": "https://example.com/recipe"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert registry.max_images_seen == 9
    sources = detail.json()["sources"]
    assert [(source["type"], source["source"], source["parentResourceId"]) for source in sources] == [
        ("IMAGE", "MANUAL", None),
        ("URL", "MANUAL", None),
        ("TEXT", "URL", sources[1]["id"]),
        ("IMAGE", "URL", sources[1]["id"]),
    ]


def test_url_video_poster_and_transcript_are_passed_to_ai_sources():
    client = client_with_session()
    provider = CapturingProvider()
    set_url_content_service(FakeVideoRegistry())
    set_video_processor(FakeVideoProcessor())
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "video-url", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert [(source.type, source.text, source.original_name) for source in provider.sources] == [
        ("TEXT", "URL recipe text", None),
        ("TEXT", "Video 1 transcript:\nMix batter and bake.", None),
        ("IMAGE", None, "poster-video.mp4.jpg"),
    ]
    assert all(source.id for source in provider.sources)


def test_url_video_transcript_survives_when_image_capacity_is_full():
    client = client_with_session()
    provider = CapturingProvider()
    set_url_content_service(FakeVideoRegistry())
    set_video_processor(FakeVideoProcessor())
    set_recipe_extraction_provider(provider)
    files = [("files", (f"recipe-{index}.jpg", image_bytes(), "image/jpeg")) for index in range(10)]

    response = client.post(
        "/imports",
        data={"clientImportId": "video-url-full-capacity", "url": "https://example.com/recipe"},
        files=files,
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert [source.type for source in provider.sources].count("IMAGE") == 10
    assert any(source.type == "TEXT" and source.text == "Video 1 transcript:\nMix batter and bake." for source in provider.sources)


def test_url_secondary_resource_failure_fails_job_with_processing_error():
    client, SessionLocal = client_with_session_factory()
    set_url_content_service(FailingRegistry())

    response = client.post(
        "/imports",
        data={"clientImportId": "url-secondary-failure", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errorCode"] == "IMPORT_PROCESSING_FAILED"
    assert response.json()["errorMessage"] == "SECONDARY_RESOURCE_UPLOADING_FAILED"
    with SessionLocal() as session:
        job = session.get(ImportJob, response.json()["jobId"])
        assert [event.event_type for event in job.events] == [
            ImportEventType.IMPORT_CREATED,
            ImportEventType.IMPORT_STARTED,
            ImportEventType.IMPORT_FAILED,
        ]
        failed_payload = job.events[-1].payload
        assert failed_payload["error"] == {
            "import_job_code": "IMPORT_PROCESSING_FAILED",
            "code": "SECONDARY_RESOURCE_UPLOADING_FAILED",
            "message": "Import processing failed due to secondary resource uploading issue.",
        }
        assert failed_payload["resource_type"] == "URL"
        assert failed_payload["url"] == "https://example.com/recipe"


class CapturingProvider(FakeRecipeExtractionProvider):
    def __init__(self):
        self.sources = []

    async def extract(self, sources, *, language: str, tags: str):
        self.sources = sources
        return await super().extract(sources, language=language, tags=tags)


class TaggingProvider(FakeRecipeExtractionProvider):
    def __init__(self):
        self.language: str | None = None
        self.tags: str | None = None

    async def extract(self, sources, *, language: str, tags: str):
        self.language = language
        self.tags = tags
        result = await super().extract(sources, language=language, tags=tags)
        assert result.recipe is not None
        result.recipe.tags = ["десерт", "unknown-tag", "АЭРОГРИЛЬ", "десерт", " аэроГРИЛЬ "]
        return result


def test_import_passes_user_language_and_active_tags_to_ai_and_attaches_known_tags(caplog):
    client = client_with_session()
    provider = TaggingProvider()
    set_recipe_extraction_provider(provider)
    caplog.set_level(logging.INFO, logger="recipes.import")

    response = client.post(
        "/imports",
        data={"clientImportId": "ai-tags", "text": "Recipe text"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert provider.language == "ru"
    assert provider.tags is not None
    assert "десерт" in provider.tags
    assert "аэрогриль" in provider.tags
    assert [tag["name"] for tag in detail.json()["tags"]] == ["аэрогриль", "десерт"]
    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "AI tags processed" in joined_logs
    assert '"component": "recipes.import"' in joined_logs
    assert '"returned_count": 5' in joined_logs
    assert '"duplicate_count": 2' in joined_logs
    assert '"valid_count": 2' in joined_logs
    assert '"valid_tags": ["десерт", "аэрогриль"]' in joined_logs
    assert '"invalid_count": 1' in joined_logs
    assert '"invalid_tags": ["unknown-tag"]' in joined_logs


def test_ai_receives_short_request_source_ids_without_persisting_source_refs():
    client = client_with_session()
    provider = CapturingProvider()
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "short-ai-ids", "text": "Recipe text"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert [source.id for source in provider.sources] == ["source_1", "source_2"]
    assert all("sourceRef" not in source for source in detail.json()["sources"])


def test_url_author_name_is_passed_to_ai_sources():
    client = client_with_session()
    registry = FakeRegistry()
    provider = CapturingProvider()
    set_url_content_service(registry)
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "url-author", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert all(source.type != "URL" for source in provider.sources)
    assert detail.json()["authorName"] == "url_author"


def test_threads_url_import_sets_recipe_source_name():
    client = client_with_session()
    set_url_content_service(FakeRegistry())

    response = client.post(
        "/imports",
        data={"clientImportId": "threads-url", "url": "https://www.threads.com/@cook/post/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "THREADS"


def test_instagram_url_import_sets_recipe_source_name():
    client = client_with_session()
    set_url_content_service(FakeRegistry())

    response = client.post(
        "/imports",
        data={"clientImportId": "instagram-url", "url": "https://www.instagram.com/p/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "INSTAGRAM"


class ManualPrimaryUrlIgnoredProvider:
    async def extract(self, sources, *, language: str, tags: str):
        manual_text = next(source for source in sources if source.type == "TEXT" and source.text == "Manual recipe text")
        ignored_refs = [source.id for source in sources if source.id != manual_text.id]
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Manual primary recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=True,
                    primary_source_refs=[manual_text.id],
                    ignored_source_refs=ignored_refs,
                ),
            )
        )


def test_source_name_uses_unignored_primary_sources_after_ai_assessment():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(ManualPrimaryUrlIgnoredProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "manual-primary-url-ignored", "text": "Manual recipe text", "url": "https://www.instagram.com/p/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "MANUAL"
    assert next(source for source in detail.json()["sources"] if source["type"] == "URL")["status"] == "ignored"


class AllSourcesIgnoredProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Ignored source recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=True,
                    primary_source_refs=[],
                    ignored_source_refs=[source.id for source in sources],
                ),
            )
        )


def test_source_name_falls_back_to_other_when_only_url_primary_is_ignored():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(AllSourcesIgnoredProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "ignored-instagram", "url": "https://www.instagram.com/p/abc"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["sourceName"] == "OTHER"
    assert next(source for source in detail.json()["sources"] if source["type"] == "URL")["status"] == "ignored"


def test_mixed_sources_match_reference_ai_source_order_and_refs():
    client = client_with_session()
    registry = FakeRegistry()
    provider = CapturingProvider()
    set_url_content_service(registry)
    set_recipe_extraction_provider(provider)

    response = client.post(
        "/imports",
        data={"clientImportId": "mixed-source-order", "text": "Manual recipe text", "url": "https://example.com/recipe"},
        files=[("files", ("first.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert [(source.type, source.text, source.original_name) for source in provider.sources] == [
        ("IMAGE", None, "first.jpg"),
        ("TEXT", "Manual recipe text", None),
        ("TEXT", "URL recipe text", None),
        ("IMAGE", None, "remote.jpg"),
    ]
    assert all(source.id for source in provider.sources)


class LowConfidenceProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Low confidence recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0,
                    has_conflicts=False,
                    has_ignored=False,
                    primary_source_refs=[],
                    ignored_source_refs=[],
                ),
            )
        )


class TooManyIngredientsProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Too many ingredients",
                ingredients=[{"name": f"Ingredient {index}"} for index in range(51)],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=False,
                    primary_source_refs=[sources[0].id],
                    ignored_source_refs=[],
                ),
            )
        )


class TooLongInstructionsProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Too long instructions",
                ingredients=[{"name": "Ingredient"}],
                instructions=["x" * 1001],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=False,
                    primary_source_refs=[sources[0].id],
                    ignored_source_refs=[],
                ),
            )
        )


class SourceAssessmentProvider:
    async def extract(self, sources, *, language: str, tags: str):
        refs = {source.type: source.id for source in sources}
        image_ids = [source.id for source in sources if source.type == "IMAGE"]
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Assessed recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=True,
                    has_ignored=True,
                    primary_source_refs=[image_ids[0], refs["TEXT"]],
                    ignored_source_refs=[image_ids[1]],
                ),
            )
        )


class SourceIdPrefixedAssessmentProvider:
    async def extract(self, sources, *, language: str, tags: str):
        image_ids = [source.id for source in sources if source.type == "IMAGE"]
        text_id = next(source.id for source in sources if source.type == "TEXT")
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Prefixed refs recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.95,
                    has_conflicts=False,
                    has_ignored=True,
                    primary_source_refs=[f"sourceId={text_id}", f"sourceId={image_ids[0]}"],
                    ignored_source_refs=[f"sourceId={image_ids[1]}"],
                ),
            )
        )


def test_ai_quality_refs_set_recipe_source_statuses_after_normalization():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(SourceAssessmentProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "source-statuses", "url": "https://example.com/recipe"},
        files=[("files", ("first.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    sources = detail.json()["sources"]
    manual_image = next(source for source in sources if source["type"] == "IMAGE" and source["source"] == "MANUAL")
    url_parent = next(source for source in sources if source["type"] == "URL")
    url_text = next(source for source in sources if source["type"] == "TEXT" and source["source"] == "URL")
    url_image = next(source for source in sources if source["type"] == "IMAGE" and source["source"] == "URL")
    assert manual_image["status"] == "used"
    assert url_text["status"] == "used"
    assert url_image["status"] == "ignored"
    assert url_parent["status"] == "used"


def test_ai_quality_refs_with_source_id_prefix_set_recipe_source_statuses():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(SourceIdPrefixedAssessmentProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "source-id-prefixed-statuses", "url": "https://example.com/recipe"},
        files=[("files", ("first.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    sources = detail.json()["sources"]
    assert next(source for source in sources if source["type"] == "URL")["status"] == "used"
    assert next(source for source in sources if source["type"] == "TEXT" and source["source"] == "URL")["status"] == "used"


def test_import_fails_when_ai_returns_too_many_ingredients():
    client = client_with_session()
    set_recipe_extraction_provider(TooManyIngredientsProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "too-many-ingredients", "text": "Recipe text"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errorCode"] == "IMPORT_EXTRACTION_FAILED"
    assert response.json()["errorMessage"] == "RECIPE_TOO_LONG"


def test_import_fails_when_ai_returns_too_long_instructions():
    client = client_with_session()
    set_recipe_extraction_provider(TooLongInstructionsProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "too-long-instructions", "text": "Recipe text"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errorCode"] == "IMPORT_EXTRACTION_FAILED"
    assert response.json()["errorMessage"] == "RECIPE_TOO_LONG"


def test_low_confidence_import_fails_and_cleans_uploaded_files():
    client = client_with_session()
    set_recipe_extraction_provider(LowConfidenceProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "low-confidence"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errorCode"] == "IMPORT_EXTRACTION_FAILED"
    assert response.json()["errorMessage"] == "NOT_A_RECIPE"


class CoverCandidateProvider:
    async def extract(self, sources, *, language: str, tags: str):
        image_ref = next(source.id for source in sources if source.type == "IMAGE")
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Cover recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=False,
                    primary_source_refs=[image_ref],
                    ignored_source_refs=[],
                ),
                cover_candidate=CoverCandidate(source_ref=image_ref, confidence=0.9),
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
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert detail.json()["coverImage"]["id"] is not None
    generated_resources = [source for source in detail.json()["sources"] if source["source"] == "GENERATED"]
    assert generated_resources[0]["role"] == "COVER_CANDIDATE"
    assert generated_resources[0]["imageId"] == detail.json()["coverImage"]["id"]
    assert any(option["image"] and option["image"]["id"] == detail.json()["coverImage"]["id"] for option in detail.json()["coverOptions"])


class WarningFlagProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Warning recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.7,
                    has_conflicts=True,
                    has_ignored=True,
                    primary_source_refs=[sources[0].id],
                    ignored_source_refs=[],
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
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded_with_flags"
    flags = detail.json()["reviewFlags"]
    assert len(flags) == 1
    assert flags[0]["type"] == "CONTENT_WARNING"
    assert flags[0]["reasonCode"] == "CONTENT_CONFLICT"
    assert flags[0]["details"]["reasons"] == ["CONTENT_CONFLICT", "LOW_CONFIDENCE"]


class ChildIgnoredWithoutPrimaryIgnoredProvider:
    async def extract(self, sources, *, language: str, tags: str):
        text_source = next(source for source in sources if source.type == "TEXT")
        image_source = next(source for source in sources if source.type == "IMAGE")
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Child ignored recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=True,
                    primary_source_refs=[text_source.id],
                    ignored_source_refs=[image_source.id],
                ),
            )
        )


class PrimaryIgnoredProvider:
    async def extract(self, sources, *, language: str, tags: str):
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Primary ignored recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    has_conflicts=False,
                    has_ignored=True,
                    primary_source_refs=[],
                    ignored_source_refs=[source.id for source in sources],
                ),
            )
        )


def test_child_ignored_does_not_create_warning_when_primary_url_is_used():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(ChildIgnoredWithoutPrimaryIgnoredProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "child-ignored", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert next(source for source in detail.json()["sources"] if source["type"] == "URL")["status"] == "used"
    assert detail.json()["reviewFlags"] == []


def test_single_url_ignored_primary_url_does_not_create_warning_flag():
    client = client_with_session()
    set_url_content_service(FakeRegistry())
    set_recipe_extraction_provider(PrimaryIgnoredProvider())

    response = client.post(
        "/imports",
        data={"clientImportId": "primary-ignored", "url": "https://example.com/recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    url_parent = next(source for source in detail.json()["sources"] if source["type"] == "URL")
    assert url_parent["status"] == "ignored"
    assert detail.json()["reviewFlags"] == []


def test_import_logs_lifecycle_without_image_payloads(caplog):
    client = client_with_session()
    caplog.set_level(logging.INFO, logger="recipes.import")

    response = client.post(
        "/imports",
        data={"clientImportId": "logged"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    response = process_import_response(client, response)

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    joined = "\n".join(messages)
    assert "Import job was created" in joined
    assert "AI extraction quality" in joined
    assert "Import recipe created" in joined
    assert '"component": "recipes.import"' in joined
    assert "data:image" not in joined
    assert "base64" not in joined
