from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.media.access.constants import DownloadAccessMode, MediaReferenceType
from app.media.access.service import MediaAccessService
from app.media.access.types import DownloadGrant
from app.models import (
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    Recipe,
    RecipeImage,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceStatus,
    RecipeStatus,
    SourceType,
    User,
)
from app.schemas.media import MediaReferenceIn


class GrantProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def create_grant(self, media):
        self.calls.append(media.reference.id)
        return DownloadGrant(
            url=f"https://media.invalid/{media.reference.id}",
            expires_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
            content_type=media.content_type,
            access_mode=DownloadAccessMode.DIRECT,
        )

    def get_local_path(self, media):
        raise AssertionError("not used")


def build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed(session) -> None:
    owner = User(id="owner-1", email="owner@example.test")
    foreign = User(id="owner-2", email="foreign@example.test")
    active = Recipe(id="recipe-1", owner=owner, title="Active", status=RecipeStatus.ACTIVE)
    pending = Recipe(id="recipe-2", owner=owner, title="Pending", status=RecipeStatus.DELETION_PENDING)
    active_image = RecipeImage(
        id="image-1",
        recipe=active,
        storage_key="recipes/media/owner-1/recipe-1/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    foreign_image = RecipeImage(
        id="image-2",
        recipe=Recipe(id="recipe-3", owner=foreign, title="Foreign"),
        storage_key="recipes/media/owner-2/recipe-3/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    pending_image = RecipeImage(
        id="image-3",
        recipe=pending,
        storage_key="recipes/media/owner-1/recipe-2/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    detached = RecipeImage(
        id="image-4",
        recipe=None,
        storage_key="recipes/media/owner-1/recipe-1/detached.jpg",
        original_name="detached.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=1,
    )
    resource = RecipeResource(
        recipe=active,
        owner=owner,
        type=SourceType.IMAGE,
        source=RecipeResourceOrigin.MANUAL,
        status=RecipeResourceStatus.DELETED,
        image=active_image,
    )
    failed = ImportJob(id="job-1", owner=owner, client_id="client-1", status=ImportJobStatus.FAILED)
    cleaned = ImportJob(id="job-2", owner=owner, client_id="client-2", status=ImportJobStatus.FAILED_ARTIFACTS_REMOVED)
    foreign_job = ImportJob(id="job-3", owner=foreign, client_id="client-3", status=ImportJobStatus.FAILED)
    source = ImportJobSource(
        id="source-1",
        import_job=failed,
        type=SourceType.IMAGE,
        image_storage_key="imports/source/owner-1/job-1/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    cleaned_source = ImportJobSource(
        id="source-2",
        import_job=cleaned,
        type=SourceType.IMAGE,
        image_storage_key="imports/source/owner-1/job-2/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    foreign_source = ImportJobSource(
        id="source-3",
        import_job=foreign_job,
        type=SourceType.IMAGE,
        image_storage_key="imports/source/owner-2/job-3/image.jpg",
        original_name="image.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=0,
    )
    text_source = ImportJobSource(id="source-4", import_job=failed, type=SourceType.TEXT, text="recipe", position=1)
    missing_key_source = ImportJobSource(
        id="source-5",
        import_job=failed,
        type=SourceType.IMAGE,
        original_name="missing.jpg",
        mime_type="image/jpeg",
        size_bytes=1,
        position=2,
    )
    session.add_all(
        [
            owner,
            foreign,
            active,
            pending,
            active_image,
            foreign_image,
            pending_image,
            detached,
            resource,
            failed,
            cleaned,
            foreign_job,
            source,
            cleaned_source,
            foreign_source,
            text_source,
            missing_key_source,
        ]
    )
    session.commit()


def test_service_preserves_order_duplicates_partial_success_and_batches_queries() -> None:
    session = build_session()
    seed(session)
    provider = GrantProvider()
    query_count = 0

    @event.listens_for(session.bind, "before_cursor_execute")
    def count_queries(*_args):
        nonlocal query_count
        query_count += 1

    references = [
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-1"),
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="missing"),
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-1"),
        MediaReferenceIn(type=MediaReferenceType.IMPORT_SOURCE_IMAGE, id="source-1"),
    ]

    result = MediaAccessService(session, provider).create_grants("owner-1", references)

    assert [item.id for item in result] == ["image-1", "missing", "image-1", "source-1"]
    assert result[0].grant == result[2].grant
    assert result[1].error.code == "MEDIA_NOT_FOUND"
    assert result[3].grant is not None
    assert provider.calls == ["image-1", "source-1"]
    assert query_count == 2


def test_service_normalizes_foreign_and_lifecycle_ineligible_media_to_not_found() -> None:
    session = build_session()
    seed(session)
    provider = GrantProvider()
    references = [
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-2"),
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-3"),
        MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-4"),
        MediaReferenceIn(type=MediaReferenceType.IMPORT_SOURCE_IMAGE, id="source-2"),
        MediaReferenceIn(type=MediaReferenceType.IMPORT_SOURCE_IMAGE, id="source-3"),
        MediaReferenceIn(type=MediaReferenceType.IMPORT_SOURCE_IMAGE, id="source-4"),
        MediaReferenceIn(type=MediaReferenceType.IMPORT_SOURCE_IMAGE, id="source-5"),
    ]

    result = MediaAccessService(session, provider).create_grants("owner-1", references)

    assert all(item.error.code == "MEDIA_NOT_FOUND" for item in result)
    assert provider.calls == []


def test_recipe_resource_status_does_not_block_recipe_image_access() -> None:
    session = build_session()
    seed(session)
    result = MediaAccessService(session, GrantProvider()).create_grants(
        "owner-1", [MediaReferenceIn(type=MediaReferenceType.RECIPE_IMAGE, id="image-1")]
    )
    assert result[0].grant is not None
