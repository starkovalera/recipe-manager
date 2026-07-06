from __future__ import annotations

import logging
from dataclasses import dataclass, field
from io import BytesIO

from openai import OpenAI

from app.core.config import Settings, get_settings
from app.core.logging import bind_logger
from app.imports.constants import IMPORT_VIDEO_LOG_COMPONENT
from app.imports.url_loaders.generic import httpx_fetch
from app.imports.url_loaders.types import Fetch, LoadedRemoteImage, LoadedRemoteVideo

logger = logging.getLogger(IMPORT_VIDEO_LOG_COMPONENT)
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class FirstPassVideoSources:
    poster_images: list[LoadedRemoteImage] = field(default_factory=list)
    transcript_text: str | None = None


class VideoProcessor:
    def __init__(
        self,
        settings: Settings | None = None,
        fetch: Fetch = httpx_fetch,
        client: OpenAI | None = None,
    ):
        self.settings = settings or get_settings()
        self.fetch = fetch
        self.client = client

    async def _download_poster(self, video: LoadedRemoteVideo, max_image_bytes: int) -> LoadedRemoteImage | None:
        if not video.poster_url:
            return None
        response = await self.fetch(video.poster_url, max_image_bytes)
        mime_type = response.headers.get("content-type", "").split(";")[0].lower()
        if mime_type not in SUPPORTED_IMAGE_TYPES or not response.content:
            return None
        return LoadedRemoteImage(
            bytes=response.content,
            mime_type=mime_type,
            original_name=f"poster-{video.original_name}.jpg",
            url=video.poster_url,
            position=video.position,
        )

    async def _transcribe(self, video: LoadedRemoteVideo, max_video_bytes: int) -> str | None:
        api_key = self.settings.openai_api_key or ""
        client = self.client or (OpenAI(api_key=api_key) if api_key else None)
        if client is None:
            return None
        response = await self.fetch(video.url, max_video_bytes)
        if not response.content:
            return None
        file_obj = BytesIO(response.content)
        file_obj.name = video.original_name or "video.mp4"
        result = client.audio.transcriptions.create(
            model=self.settings.openai_video_transcription_model,
            file=file_obj,
        )
        text = getattr(result, "text", None)
        return text.strip() if isinstance(text, str) and text.strip() else None

    async def prepare_first_pass_video_sources(
        self,
        *,
        videos: list[LoadedRemoteVideo],
        max_image_bytes: int,
        max_video_bytes: int,
    ) -> FirstPassVideoSources:
        poster_images: list[LoadedRemoteImage] = []
        transcripts: list[str] = []

        for video in videos:
            try:
                poster = await self._download_poster(video, max_image_bytes)
            except Exception as error:
                bind_logger(logger, component=IMPORT_VIDEO_LOG_COMPONENT, video_url=video.url).error(
                    f"{IMPORT_VIDEO_LOG_COMPONENT} Video poster download failed",
                    error=repr(error),
                )
                raise
            if poster is not None:
                poster_images.append(poster)

            try:
                transcript = await self._transcribe(video, max_video_bytes)
            except Exception as error:
                bind_logger(logger, component=IMPORT_VIDEO_LOG_COMPONENT, video_url=video.url).error(
                    f"{IMPORT_VIDEO_LOG_COMPONENT} Video transcription failed",
                    error=repr(error),
                )
                raise
            if transcript:
                transcripts.append(f"Video {video.position + 1} transcript:\n{transcript}")

        return FirstPassVideoSources(
            poster_images=poster_images,
            transcript_text="\n\n".join(transcripts) if transcripts else None,
        )
