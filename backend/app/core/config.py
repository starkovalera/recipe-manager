from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.infrastructure import QueueProvider, StorageProvider

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    PROD = "PROD"
    PREVIEW = "PREVIEW"
    DEV = "DEV"
    TEST = "TEST"


def _default_database_url(app_env: AppEnv) -> str | None:
    if app_env is AppEnv.DEV:
        return "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev"
    if app_env is AppEnv.PREVIEW:
        return "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"
    if app_env is AppEnv.TEST:
        return f"sqlite:///{BACKEND_ROOT / 'storage' / 'test' / 'app.db'}"
    return None


def _default_upload_dir(app_env: AppEnv) -> Path | None:
    if app_env is AppEnv.PROD:
        return None
    return BACKEND_ROOT / "storage" / app_env.value.lower() / "uploads"


def _default_redis_url(app_env: AppEnv) -> str | None:
    if app_env is AppEnv.PROD:
        return None
    return "redis://127.0.0.1:6379/0"


def _default_queue_provider(app_env: AppEnv) -> QueueProvider | None:
    if app_env is AppEnv.PROD:
        return None
    return QueueProvider.DRAMATIQ


def _default_storage_provider(app_env: AppEnv) -> StorageProvider | None:
    if app_env is AppEnv.PROD:
        return None
    return StorageProvider.LOCAL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = AppEnv.PROD
    database_url: str | None = None
    upload_dir: Path | None = None
    queue_provider: QueueProvider | None = None
    storage_provider: StorageProvider | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )

    max_import_images: int = 10
    max_import_text_chars: int = 1000
    max_recipe_ingredients: int = 50
    max_recipe_instruction_chars: int = 1000
    max_recipe_note_chars: int = 500
    max_tags_per_user: int = 50
    recipe_language: str = "ru"
    max_upload_bytes: int = 8 * 1024 * 1024
    max_video_bytes: int = 64 * 1024 * 1024
    max_import_videos: int = 1
    import_min_confidence: float = 0
    import_warn_confidence: float = 0.75
    max_parallel_imports_per_client: int = 3
    max_import_attempts: int = Field(default=3, ge=1)
    import_task_max_retries: int = Field(default=0, ge=0)
    embedding_task_max_retries: int = Field(default=2, ge=0)
    stale_import_minutes: int = 30
    outbox_reconcile_batch_size: int = Field(default=100, ge=1, le=1000)
    maintenance_batch_size: int = Field(default=100, ge=1, le=1000)
    stale_embedding_minutes: int = Field(default=30, ge=1)
    stale_recipe_deletion_minutes: int = Field(default=60, ge=1)
    stale_account_deletion_minutes: int = Field(default=60, ge=1)
    redis_url: str | None = None
    aws_region: str | None = None
    s3_user_media_bucket_name: str | None = None
    sqs_imports_queue_url: str | None = None
    sqs_embeddings_queue_url: str | None = None
    sqs_account_deletion_queue_url: str | None = None
    account_deletion_task_max_retries: int = Field(default=2, ge=0)

    clerk_secret_key: str | None = None
    clerk_api_url: str = "https://api.clerk.com"
    clerk_webhook_signing_secret: str | None = None
    frontend_invitation_url: str = "http://127.0.0.1:5173/sign-up"
    preview_users_file: Path = BACKEND_ROOT / "config" / "preview-users.local.toml"

    ai_provider: Literal["auto", "fake", "openai"] = "auto"
    openai_api_key: str | None = None
    openai_recipe_model: str = "gpt-4.1-mini"
    openai_video_transcription_model: str = "gpt-4o-mini-transcribe"
    embedding_provider: Literal["auto", "fake", "openai"] = "auto"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_distance_metric: Literal["cosine", "l2"] = "cosine"
    enable_cover_candidate_guard: bool = False
    max_cover_fallback_candidates: int = 0
    openai_cover_validation_model: str = "gpt-4.1-mini"
    ffmpeg_path: str | None = None
    ffprobe_path: str | None = None

    @field_validator(
        "database_url",
        "upload_dir",
        "queue_provider",
        "storage_provider",
        "redis_url",
        "aws_region",
        "s3_user_media_bucket_name",
        "sqs_imports_queue_url",
        "sqs_embeddings_queue_url",
        "sqs_account_deletion_queue_url",
        mode="before",
    )
    @classmethod
    def empty_infrastructure_value_as_none(cls, value: object) -> object | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def _missing_sqs_settings(self) -> list[str]:
        required = {
            "AWS_REGION": self.aws_region,
            "SQS_IMPORTS_QUEUE_URL": self.sqs_imports_queue_url,
            "SQS_EMBEDDINGS_QUEUE_URL": self.sqs_embeddings_queue_url,
            "SQS_ACCOUNT_DELETION_QUEUE_URL": self.sqs_account_deletion_queue_url,
        }
        return [name for name, value in required.items() if not value]

    def _missing_s3_settings(self) -> list[str]:
        required = {
            "AWS_REGION": self.aws_region,
            "S3_USER_MEDIA_BUCKET_NAME": self.s3_user_media_bucket_name,
        }
        return [name for name, value in required.items() if not value]

    @model_validator(mode="after")
    def materialize_and_validate_environment_settings(self):
        self.database_url = self.database_url or _default_database_url(self.app_env)
        self.upload_dir = self.upload_dir or _default_upload_dir(self.app_env)
        self.queue_provider = self.queue_provider or _default_queue_provider(self.app_env)
        self.storage_provider = self.storage_provider or _default_storage_provider(self.app_env)
        self.redis_url = self.redis_url or _default_redis_url(self.app_env)

        if self.app_env is AppEnv.PROD:
            if not self.database_url:
                raise ValueError("DATABASE_URL is required in PROD.")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("PROD requires a PostgreSQL DATABASE_URL.")
            if self.queue_provider is not QueueProvider.SQS:
                raise ValueError("PROD requires QUEUE_PROVIDER=SQS.")
            if self.storage_provider is not StorageProvider.S3:
                raise ValueError("PROD requires STORAGE_PROVIDER=S3.")
            if self.redis_url:
                raise ValueError("REDIS_URL is not supported in PROD.")
            if self.upload_dir:
                raise ValueError("UPLOAD_DIR is not supported in PROD.")

        if self.queue_provider is QueueProvider.SQS:
            missing = self._missing_sqs_settings()
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"QUEUE_PROVIDER=SQS requires: {joined}.")

            queue_urls = {
                self.sqs_imports_queue_url,
                self.sqs_embeddings_queue_url,
                self.sqs_account_deletion_queue_url,
            }
            if len(queue_urls) != 3:
                raise ValueError("SQS queue URLs must be distinct.")

        if self.storage_provider is StorageProvider.S3:
            missing = self._missing_s3_settings()
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"STORAGE_PROVIDER=S3 requires: {joined}.")

        if self.app_env is not AppEnv.TEST and not self.clerk_secret_key:
            raise ValueError("Clerk identity configuration is required outside TEST.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
