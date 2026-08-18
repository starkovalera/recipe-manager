from app.imports.source_loading.types import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)


def test_secondary_resource_load_result_keeps_structured_failure_details():
    result = SecondaryResourceLoadResult(
        kind=SecondaryResourceKind.VIDEO_TRANSCRIPT,
        status=SecondaryResourceLoadStatus.FAILED,
        position=0,
        url="https://cdn.example/video.mp4",
        original_name="video.mp4",
        error="Audio file processing failed",
    )

    assert result.kind == SecondaryResourceKind.VIDEO_TRANSCRIPT
    assert result.status == SecondaryResourceLoadStatus.FAILED
    assert result.error == "Audio file processing failed"


def test_secondary_resource_load_result_redacts_persisted_diagnostics():
    result = SecondaryResourceLoadResult(
        kind=SecondaryResourceKind.VIDEO_TRANSCRIPT,
        status=SecondaryResourceLoadStatus.FAILED,
        position=0,
        url="https://cdn.example/video.mp4?token=secret",
        original_name="video.mp4",
        error="RuntimeError('response body secret')",
    )

    assert result.to_dict() == {
        "kind": "VIDEO_TRANSCRIPT",
        "status": "FAILED",
        "position": 0,
        "url": "https://cdn.example",
        "original_name": "video.mp4",
        "error": "UNEXPECTED_ERROR",
    }
