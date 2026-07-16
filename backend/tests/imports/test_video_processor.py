import pytest

from app.core.config import Settings
from app.imports.source_loading.types import SecondaryResourceKind, SecondaryResourceLoadStatus
from app.imports.source_loading.url_loaders.types import FetchResponse, LoadedRemoteVideo
from app.imports.source_loading.video_processors.generic import VideoProcessor


class FailingTranscriptions:
    def create(self, **_kwargs):
        raise RuntimeError("Audio file processing failed")


class FailingTranscriptionClient:
    class Audio:
        transcriptions = FailingTranscriptions()

    audio = Audio()


@pytest.mark.anyio
async def test_video_processor_reports_transcription_failure_and_keeps_poster():
    async def fetch(url: str, _max_bytes: int) -> FetchResponse:
        if "poster" in url:
            return FetchResponse(content=b"poster", headers={"content-type": "image/jpeg"})
        return FetchResponse(content=b"video", headers={"content-type": "video/mp4"})

    processor = VideoProcessor(
        settings=Settings(openai_api_key="test-key"),
        fetch=fetch,
        client=FailingTranscriptionClient(),
    )

    result = await processor.prepare_first_pass_video_sources(
        videos=[
            LoadedRemoteVideo(
                url="https://cdn.example/video.mp4",
                poster_url="https://cdn.example/poster.jpg",
                position=0,
                original_name="video.mp4",
            )
        ],
        max_image_bytes=1000,
        max_video_bytes=1000,
    )

    assert len(result.poster_images) == 1
    assert result.transcript_text is None
    assert [(item.kind, item.status) for item in result.resource_results] == [
        (SecondaryResourceKind.VIDEO_POSTER, SecondaryResourceLoadStatus.LOADED),
        (SecondaryResourceKind.VIDEO_TRANSCRIPT, SecondaryResourceLoadStatus.FAILED),
    ]
    assert result.resource_results[1].error == "RuntimeError('Audio file processing failed')"
