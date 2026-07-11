from app.imports.job_context import ImportJobContext
from app.models import ImportJob, ImportJobSource, ImportJobStatus, ImportSourceStatus, SourceType, User, UserSettings


def test_import_job_context_captures_job_fields_and_sources() -> None:
    job = ImportJob(
        id="job-1",
        owner_id="owner-1",
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="dedupe-1",
        status=ImportJobStatus.RUNNING,
        attempt_count=2,
    )
    job.owner = User(id="owner-1", email="owner@example.com", settings=UserSettings(recipe_language="ru"))
    job.sources = [
        ImportJobSource(
            id="source-1",
            type=SourceType.IMAGE,
            status=ImportSourceStatus.READY,
            image_storage_key="uploads/image.jpg",
            original_name="image.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            position=0,
        ),
        ImportJobSource(
            id="source-2",
            type=SourceType.TEXT,
            status=ImportSourceStatus.READY,
            text="Recipe text",
            position=1,
        ),
    ]

    context = ImportJobContext.from_job(job)

    assert context.id == "job-1"
    assert context.owner_id == "owner-1"
    assert context.recipe_language == "ru"
    assert context.attempt_count == 2
    assert context.primary_storage_keys == ["uploads/image.jpg"]
    assert not context.is_single_url_import
    assert [source.id for source in context.sources] == ["source-1", "source-2"]


def test_import_job_context_to_dict_excludes_sources() -> None:
    job = ImportJob(
        id="job-1",
        owner_id="owner-1",
        client_id="client-1",
        client_import_id="import-1",
        dedupe_key="dedupe-1",
        status=ImportJobStatus.QUEUED,
    )
    job.owner = User(id="owner-1", email="owner@example.com", settings=UserSettings(recipe_language="ru"))
    job.sources = [ImportJobSource(id="source-1", type=SourceType.URL, status=ImportSourceStatus.READY, url="https://example.com", position=0)]

    payload = ImportJobContext.from_job(job).to_dict()

    assert payload["id"] == "job-1"
    assert payload["status"] == "queued"
    assert payload["attempt_count"] == 0
    assert "sources" not in payload
