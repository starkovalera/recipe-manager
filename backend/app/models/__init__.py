from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.access.constants import UserRole
from app.db.base import Base
from app.services.search_text import build_ingredient_search_name


def new_id() -> str:
    return str(uuid.uuid4())


class SourceName(str, enum.Enum):
    MANUAL = "MANUAL"
    INSTAGRAM = "INSTAGRAM"
    THREADS = "THREADS"
    TT = "TT"
    OTHER = "OTHER"


class SourceType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    URL = "URL"


class ImportJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SUCCEEDED_WITH_FLAGS = "succeeded_with_flags"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportJobErrorCode(str, enum.Enum):
    # High-level persisted processing failures. Import creation failures are
    # synchronous API errors and therefore never belong to a persisted job.
    IMPORT_FAILED = "IMPORT_FAILED"
    IMPORT_PROCESSING_FAILED = "IMPORT_PROCESSING_FAILED"
    IMPORT_EXTRACTION_FAILED = "IMPORT_EXTRACTION_FAILED"


class ImportEventType(str, enum.Enum):
    IMPORT_CREATED = "IMPORT_CREATED"
    IMPORT_STARTED = "IMPORT_STARTED"
    RAW_SOURCES_DOWNLOADED = "RAW_SOURCES_DOWNLOADED"
    IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED = "IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED"
    EXTRACTOR_REQUESTED = "EXTRACTOR_REQUESTED"
    EXTRACTOR_SUCCEEDED = "EXTRACTOR_SUCCEEDED"
    RECIPE_CREATED = "RECIPE_CREATED"
    IMPORT_FAILED = "IMPORT_FAILED"


class NotificationType(str, enum.Enum):
    IMPORT_STARTED = "IMPORT_STARTED"
    IMPORT_FAILED = "IMPORT_FAILED"
    IMPORT_SUCCEEDED = "IMPORT_SUCCEEDED"
    IMPORT_SUCCEEDED_WITH_FLAGS = "IMPORT_SUCCEEDED_WITH_FLAGS"


class NotificationEntityType(str, enum.Enum):
    RECIPE = "RECIPE"
    IMPORT_JOB = "IMPORT_JOB"


class ImportSourceStatus(str, enum.Enum):
    # Only READY is assigned by the current import flow. The other statuses are
    # reserved for a future per-source upload/validation/processing lifecycle.
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"


class RecipeResourceStatus(str, enum.Enum):
    USED = "used"
    IGNORED = "ignored"
    UNKNOWN = "unknown"
    DELETED = "deleted"


class RecipeResourceOrigin(str, enum.Enum):
    MANUAL = "MANUAL"
    URL = "URL"
    URL_VIDEO = "URL_VIDEO"
    GENERATED = "GENERATED"


class RecipeResourceRole(str, enum.Enum):
    SOURCE = "SOURCE"
    COVER_CANDIDATE = "COVER_CANDIDATE"


class RecipeReviewFlagStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class RecipeReviewFlagType(str, enum.Enum):
    CONTENT_WARNING = "CONTENT_WARNING"


class RecipeEmbeddingStatus(str, enum.Enum):
    STALE = "STALE"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"
    SKIPPED_DUE_TO_FLAGS = "SKIPPED_DUE_TO_FLAGS"


class RecipeEmbeddingEventType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    ENQUEUED = "ENQUEUED"
    STARTED = "STARTED"
    SKIPPED_DUE_TO_FLAGS = "SKIPPED_DUE_TO_FLAGS"
    ALREADY_READY = "ALREADY_READY"
    PROVIDER_SUCCEEDED = "PROVIDER_SUCCEEDED"
    SAVED = "SAVED"
    STALE_REQUEUED = "STALE_REQUEUED"
    FAILED = "FAILED"
    RETRY_REQUESTED = "RETRY_REQUESTED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    recipes: Mapped[list[Recipe]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    collections: Mapped[list[Collection]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    import_jobs: Mapped[list[ImportJob]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    review_flags: Mapped[list[RecipeReviewFlag]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    resources: Mapped[list[RecipeResource]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    settings: Mapped[UserSettings | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    role_assignments: Mapped[list[UserRoleAssignment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> set[UserRole]:
        return {assignment.role for assignment in self.role_assignments}


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_type: [item.value for item in enum_type]),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="role_assignments")


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    recipe_language: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped[User] = relationship(back_populates="settings")


class Recipe(TimestampMixin, Base):
    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    servings: Mapped[int | None] = mapped_column(Integer)
    cook_time_minutes: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[list[str]] = mapped_column(JSON, default=list)
    nutrition_estimate: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String)
    source_name: Mapped[SourceName] = mapped_column(Enum(SourceName), default=SourceName.MANUAL, nullable=False)
    search_text: Mapped[str | None] = mapped_column(Text)
    search_text_hash: Mapped[str | None] = mapped_column(String)
    cover_image_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "recipe_images.id",
            name="fk_recipes_cover_image_id_recipe_images",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
    )

    owner: Mapped[User] = relationship(back_populates="recipes")
    ingredients: Mapped[list[Ingredient]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    images: Mapped[list[RecipeImage]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        foreign_keys="RecipeImage.recipe_id",
    )
    cover_image: Mapped[RecipeImage | None] = relationship(
        foreign_keys=[cover_image_id],
        post_update=True,
    )
    resources: Mapped[list[RecipeResource]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    review_flags: Mapped[list[RecipeReviewFlag]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(secondary="recipe_tags", back_populates="recipes")
    collections: Mapped[list[Collection]] = relationship(secondary="recipe_collections", back_populates="recipes")
    import_jobs: Mapped[list[ImportJob]] = relationship(back_populates="created_recipe")
    embedding: Mapped[RecipeEmbedding | None] = relationship(back_populates="recipe", cascade="all, delete-orphan", uselist=False)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    search_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[str | None] = mapped_column(String)
    unit: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


@event.listens_for(Ingredient, "before_insert")
@event.listens_for(Ingredient, "before_update")
def _set_ingredient_search_name(mapper: Any, connection: Any, target: Ingredient) -> None:
    target.search_name = build_ingredient_search_name(target.name)


class RecipeImage(Base):
    __tablename__ = "recipe_images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str | None] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    recipe: Mapped[Recipe | None] = relationship(back_populates="images", foreign_keys=[recipe_id])
    resource: Mapped[RecipeResource | None] = relationship(back_populates="image")


class RecipeResource(TimestampMixin, Base):
    __tablename__ = "recipe_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_resource_id: Mapped[str | None] = mapped_column(ForeignKey("recipe_resources.id", ondelete="NO ACTION"))
    type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source: Mapped[RecipeResourceOrigin] = mapped_column(Enum(RecipeResourceOrigin), nullable=False)
    role: Mapped[RecipeResourceRole] = mapped_column(Enum(RecipeResourceRole), default=RecipeResourceRole.SOURCE, nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("recipe_images.id", ondelete="NO ACTION"), unique=True)
    text: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RecipeResourceStatus] = mapped_column(
        Enum(RecipeResourceStatus),
        default=RecipeResourceStatus.UNKNOWN,
        nullable=False,
    )
    assessment_reason: Mapped[str | None] = mapped_column(Text)
    assessment_confidence: Mapped[float | None] = mapped_column(Float)

    recipe: Mapped[Recipe] = relationship(back_populates="resources")
    owner: Mapped[User] = relationship(back_populates="resources")
    image: Mapped[RecipeImage | None] = relationship(back_populates="resource")
    parent: Mapped[RecipeResource | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[RecipeResource]] = relationship(back_populates="parent")


class RecipeReviewFlag(TimestampMixin, Base):
    __tablename__ = "recipe_review_flags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[RecipeReviewFlagType] = mapped_column(
        Enum(RecipeReviewFlagType),
        default=RecipeReviewFlagType.CONTENT_WARNING,
        nullable=False,
    )
    status: Mapped[RecipeReviewFlagStatus] = mapped_column(
        Enum(RecipeReviewFlagStatus),
        default=RecipeReviewFlagStatus.OPEN,
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recipe: Mapped[Recipe] = relationship(back_populates="review_flags")
    owner: Mapped[User] = relationship(back_populates="review_flags")


class RecipeEmbedding(TimestampMixin, Base):
    __tablename__ = "recipe_embeddings"

    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536).with_variant(JSON(), "sqlite"))
    model: Mapped[str] = mapped_column(String, nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String)
    status: Mapped[RecipeEmbeddingStatus] = mapped_column(
        Enum(RecipeEmbeddingStatus, name="recipe_embedding_status"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recipe: Mapped[Recipe] = relationship(back_populates="embedding")
    events: Mapped[list[RecipeEmbeddingEvent]] = relationship(back_populates="embedding", cascade="all, delete-orphan")


class RecipeEmbeddingEvent(Base):
    __tablename__ = "embedding_events"
    __table_args__ = (
        Index("ix_embedding_events_recipe_created_at", "recipe_id", "created_at"),
        Index("ix_embedding_events_owner_created_at", "owner_id", "created_at"),
        Index("ix_embedding_events_type_created_at", "event_type", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipe_embeddings.recipe_id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[RecipeEmbeddingEventType] = mapped_column(
        Enum(RecipeEmbeddingEventType, name="recipe_embedding_event_type"),
        nullable=False,
    )
    status_after: Mapped[RecipeEmbeddingStatus | None] = mapped_column(
        Enum(RecipeEmbeddingStatus, name="recipe_embedding_status"),
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    embedding: Mapped[RecipeEmbedding] = relationship(back_populates="events")
    owner: Mapped[User] = relationship()


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="tags")
    recipes: Mapped[list[Recipe]] = relationship(secondary="recipe_tags", back_populates="tags")


class RecipeTag(Base):
    __tablename__ = "recipe_tags"

    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Collection(TimestampMixin, Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    owner: Mapped[User] = relationship(back_populates="collections")
    recipes: Mapped[list[Recipe]] = relationship(secondary="recipe_collections", back_populates="collections")


class RecipeCollection(Base):
    __tablename__ = "recipe_collections"

    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "client_import_id"),
        Index("ix_import_jobs_owner_dedupe_key", "owner_id", "dedupe_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    client_import_id: Mapped[str | None] = mapped_column(String)
    dedupe_key: Mapped[str | None] = mapped_column(String)
    status: Mapped[ImportJobStatus] = mapped_column(Enum(ImportJobStatus), default=ImportJobStatus.QUEUED, nullable=False)
    error_code: Mapped[ImportJobErrorCode | None] = mapped_column(Enum(ImportJobErrorCode))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_recipe_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "recipes.id",
            name="fk_import_jobs_created_recipe_id_recipes",
            ondelete="SET NULL",
        )
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    owner: Mapped[User] = relationship(back_populates="import_jobs")
    created_recipe: Mapped[Recipe | None] = relationship(back_populates="import_jobs")
    sources: Mapped[list[ImportJobSource]] = relationship(back_populates="import_job", cascade="all, delete-orphan")
    events: Mapped[list[JobEvent]] = relationship(back_populates="import_job", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "client_id": self.client_id,
            "client_import_id": self.client_import_id,
            "dedupe_key": self.dedupe_key,
            "status": self.status.value,
            "error_code": self.error_code.value if self.error_code else None,
            "error_message": self.error_message,
            "created_recipe_id": self.created_recipe_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "attempt_count": self.attempt_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def set_failed(self, error_code: ImportJobErrorCode, error_message: str | None) -> None:
        self.status = ImportJobStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.finished_at = datetime.now(timezone.utc)

    def set_running(self) -> None:
        self.status = ImportJobStatus.RUNNING
        self.attempt_count += 1
        self.error_code = None
        self.error_message = None
        self.created_recipe_id = None
        self.finished_at = None
        self.started_at = datetime.now(timezone.utc)

    def set_recipe_created(self, recipe_id: str, status: ImportJobStatus = ImportJobStatus.SUCCEEDED) -> None:
        self.created_recipe_id = recipe_id
        self.status = status
        self.finished_at = datetime.now(timezone.utc)


class ImportJobSource(TimestampMixin, Base):
    __tablename__ = "import_job_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    import_job_id: Mapped[str] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    status: Mapped[ImportSourceStatus] = mapped_column(
        Enum(ImportSourceStatus),
        default=ImportSourceStatus.PENDING,
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(String)
    image_storage_key: Mapped[str | None] = mapped_column(String)
    original_name: Mapped[str | None] = mapped_column(String)
    mime_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    # Reserved for a future per-source failure lifecycle. The current import
    # flow does not assign source-level error codes/messages; failures are
    # stored on ImportJob.
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    import_job: Mapped[ImportJob] = relationship(back_populates="sources")


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    import_job_id: Mapped[str] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[ImportEventType] = mapped_column(Enum(ImportEventType), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    import_job: Mapped[ImportJob] = relationship(back_populates="events")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    status: Mapped[str] = mapped_column(String, default="unread", nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[NotificationEntityType | None] = mapped_column(Enum(NotificationEntityType))
    entity_id: Mapped[str | None] = mapped_column(String)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="notifications")
