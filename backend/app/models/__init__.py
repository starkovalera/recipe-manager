from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


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
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ImportSourceStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"


class RecipeImageRole(str, enum.Enum):
    SOURCE = "SOURCE"
    COVER = "COVER"


class CoverImageSource(str, enum.Enum):
    AI = "AI"
    USER = "USER"
    DEFAULT = "DEFAULT"


class RecipeSourceStatus(str, enum.Enum):
    USED = "used"
    IGNORED = "ignored"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    DELETED = "deleted"


class RecipeSourceOrigin(str, enum.Enum):
    MANUAL = "MANUAL"
    URL = "URL"
    URL_VIDEO = "URL_VIDEO"


class RecipeReviewFlagStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class RecipeReviewFlagType(str, enum.Enum):
    CONTENT_WARNING = "CONTENT_WARNING"


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
    sources: Mapped[list[RecipeSource]] = relationship(back_populates="owner", cascade="all, delete-orphan")


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
    cover_image_id: Mapped[str | None] = mapped_column(String, unique=True)
    cover_image_source: Mapped[CoverImageSource | None] = mapped_column(Enum(CoverImageSource))

    owner: Mapped[User] = relationship(back_populates="recipes")
    ingredients: Mapped[list[Ingredient]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    images: Mapped[list[RecipeImage]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        foreign_keys="RecipeImage.recipe_id",
    )
    sources: Mapped[list[RecipeSource]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    review_flags: Mapped[list[RecipeReviewFlag]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(secondary="recipe_tags", back_populates="recipes")
    collections: Mapped[list[Collection]] = relationship(secondary="recipe_collections", back_populates="recipes")
    import_jobs: Mapped[list[ImportJob]] = relationship(back_populates="created_recipe")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[str | None] = mapped_column(String)
    unit: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


class RecipeImage(Base):
    __tablename__ = "recipe_images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str | None] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    role: Mapped[RecipeImageRole] = mapped_column(Enum(RecipeImageRole), default=RecipeImageRole.SOURCE, nullable=False)
    source_image_id: Mapped[str | None] = mapped_column(ForeignKey("recipe_images.id", ondelete="NO ACTION"))
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    recipe: Mapped[Recipe | None] = relationship(back_populates="images", foreign_keys=[recipe_id])
    source_image: Mapped[RecipeImage | None] = relationship(remote_side=[id])
    sources: Mapped[list[RecipeSource]] = relationship(back_populates="image")


class RecipeSource(TimestampMixin, Base):
    __tablename__ = "recipe_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_source_id: Mapped[str | None] = mapped_column(ForeignKey("recipe_sources.id", ondelete="NO ACTION"))
    type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source: Mapped[RecipeSourceOrigin] = mapped_column(Enum(RecipeSourceOrigin), nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("recipe_images.id", ondelete="NO ACTION"))
    text: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String)
    position: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RecipeSourceStatus] = mapped_column(
        Enum(RecipeSourceStatus),
        default=RecipeSourceStatus.UNKNOWN,
        nullable=False,
    )
    assessment_reason: Mapped[str | None] = mapped_column(Text)
    assessment_confidence: Mapped[float | None] = mapped_column(Float)

    recipe: Mapped[Recipe] = relationship(back_populates="sources")
    owner: Mapped[User] = relationship(back_populates="sources")
    image: Mapped[RecipeImage | None] = relationship(back_populates="sources")
    parent: Mapped[RecipeSource | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[RecipeSource]] = relationship(back_populates="parent")


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


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

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
    __table_args__ = (UniqueConstraint("owner_id", "client_import_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    client_import_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[ImportJobStatus] = mapped_column(Enum(ImportJobStatus), default=ImportJobStatus.PENDING, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_recipe_id: Mapped[str | None] = mapped_column(ForeignKey("recipes.id", ondelete="NO ACTION"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="import_jobs")
    created_recipe: Mapped[Recipe | None] = relationship(back_populates="import_jobs")
    sources: Mapped[list[ImportJobSource]] = relationship(back_populates="import_job", cascade="all, delete-orphan")


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
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    import_job: Mapped[ImportJob] = relationship(back_populates="sources")
