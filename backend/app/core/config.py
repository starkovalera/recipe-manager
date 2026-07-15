from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    PROD = "PROD"
    PREVIEW = "PREVIEW"
    DEV = "DEV"
    TEST = "TEST"


def _default_database_url(app_env: AppEnv) -> str:
    if app_env is AppEnv.DEV:
        return "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev"
    if app_env is AppEnv.PREVIEW:
        return "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"
    return f"sqlite:///{BACKEND_ROOT / 'storage' / app_env.value.lower() / 'app.db'}"


def _default_upload_dir(app_env: AppEnv) -> Path:
    return BACKEND_ROOT / "storage" / app_env.value.lower() / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = AppEnv.PROD
    database_url: str | None = None
    upload_dir: Path | None = None
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
    stale_import_minutes: int = 30
    redis_url: str = "redis://127.0.0.1:6379/0"
    account_deletion_task_max_retries: int = Field(default=3, ge=0)

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

    @field_validator("database_url", mode="before")
    @classmethod
    def default_database_url(cls, value: str | None, info):
        if value:
            return value
        return _default_database_url(info.data.get("app_env", AppEnv.PROD))

    @field_validator("upload_dir", mode="before")
    @classmethod
    def default_upload_dir(cls, value: str | Path | None, info):
        if value:
            return Path(value)
        return _default_upload_dir(info.data.get("app_env", AppEnv.PROD))

    @model_validator(mode="after")
    def validate_clerk_identity_configuration(self):
        if self.app_env is not AppEnv.TEST and not self.clerk_secret_key:
            raise ValueError("Clerk identity configuration is required outside TEST.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
