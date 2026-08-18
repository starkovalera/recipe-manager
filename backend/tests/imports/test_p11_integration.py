import json
import socket
from collections.abc import Mapping, Sequence
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.imports.source_loading.remote_fetch import (
    FetchErrorCode,
    FetchTimeouts,
    RemoteFetcher,
    RemoteFetchError,
    ResolvedAddress,
)
from app.imports.source_loading.results import SecondaryResourceKind, SecondaryResourceLoadStatus
from app.imports.source_loading.url_loaders import (
    GenericUrlContentLoader,
    InstagramUrlContentLoader,
    ThreadsUrlContentLoader,
    generic as generic_loader,
    threads as threads_loader,
)
from app.imports.source_loading.url_loaders.types import LoadedRemoteVideo
from app.imports.source_loading.video_processors import generic as video_processor_module
from app.imports.source_loading.video_processors.generic import VideoProcessor

PUBLIC_V4 = "93.184.216.34"
PRIVATE_V4 = "192.168.1.20"


class DeterministicResponse:
    def __init__(
        self,
        url: str,
        *,
        content: bytes = b"",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        chunks: Sequence[bytes] | None = None,
        stream_error: BaseException | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self.url = httpx.URL(url)
        self._chunks = tuple(chunks if chunks is not None else (content,))
        self._stream_error = stream_error
        self.closed = False

    async def aiter_bytes(self, chunk_size: int | None = None):
        del chunk_size
        for chunk in self._chunks:
            yield chunk
        if self._stream_error is not None:
            raise self._stream_error

    async def aclose(self) -> None:
        self.closed = True


Route = DeterministicResponse | BaseException | list[DeterministicResponse | BaseException]


class FetchHarness:
    def __init__(
        self,
        routes: Mapping[str, Route],
        *,
        resolved: Mapping[str, Sequence[ResolvedAddress]] | None = None,
    ) -> None:
        self.routes = dict(routes)
        self.resolved = dict(resolved or {})
        self.calls: list[tuple[str, str]] = []
        self.resolution_calls: list[str] = []
        self.responses: list[DeterministicResponse] = []

    async def resolver(self, hostname: str, _port: int) -> Sequence[ResolvedAddress]:
        self.resolution_calls.append(hostname)
        return self.resolved.get(hostname, (ResolvedAddress(PUBLIC_V4, socket.AF_INET),))

    async def transport(self, validated_url, destination):
        self.calls.append((validated_url.value, destination.address))
        route = self.routes[validated_url.value]
        if isinstance(route, list):
            response_or_error = route.pop(0)
        else:
            response_or_error = route
        if isinstance(response_or_error, BaseException):
            raise response_or_error
        self.responses.append(response_or_error)
        return response_or_error

    def fetcher(self, *, timeouts: FetchTimeouts | None = None) -> RemoteFetcher:
        return RemoteFetcher(
            resolver=self.resolver,
            transport=self.transport,
            timeouts=timeouts or FetchTimeouts(3, 5, 1, 15),
        )


class CapturingLogger:
    name = "test.p11"

    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, _level: int, message: str) -> None:
        self.messages.append(message)


def install_fetcher(monkeypatch, harness: FetchHarness, *, timeouts: FetchTimeouts | None = None) -> None:
    monkeypatch.setattr(generic_loader, "_remote_fetcher", harness.fetcher(timeouts=timeouts))


def response(
    url: str,
    content: bytes = b"",
    *,
    content_type: str | None = None,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    chunks: Sequence[bytes] | None = None,
    stream_error: BaseException | None = None,
) -> DeterministicResponse:
    response_headers = dict(headers or {})
    if content_type is not None:
        response_headers["Content-Type"] = content_type
    if chunks is None and "Content-Length" not in response_headers:
        response_headers["Content-Length"] = str(len(content))
    return DeterministicResponse(
        url,
        content=content,
        status_code=status_code,
        headers=response_headers,
        chunks=chunks,
        stream_error=stream_error,
    )


def instagram_embed_html(media: dict) -> bytes:
    context = json.dumps({"gql_data": {"shortcode_media": media}})
    escaped = json.dumps(context)[1:-1]
    return f'<html><script>"contextJSON":"{escaped}"</script></html>'.encode()


def threads_page_html(payload: dict) -> bytes:
    return f'<html><script type="application/json">{json.dumps(payload)}</script></html>'.encode()


async def test_generic_loader_uses_validated_effective_url_and_preserves_submitted_source(monkeypatch) -> None:
    submitted_url = "https://submitted.example/recipe?token=secret"
    redirected_url = "https://redirected.example/final/page"
    preview_url = "https://redirected.example/assets/preview.jpg"
    html = b'<meta property="og:description" content="Soup recipe"><meta property="og:image" content="/assets/preview.jpg">'
    harness = FetchHarness(
        {
            submitted_url: response(
                submitted_url,
                status_code=302,
                headers={"Location": redirected_url, "Content-Length": "0"},
            ),
            redirected_url: response(redirected_url, html, content_type="text/html"),
            preview_url: response(preview_url, b"image", content_type="image/jpeg"),
        }
    )
    install_fetcher(monkeypatch, harness)

    loaded = await GenericUrlContentLoader().load(submitted_url, max_images=1, max_image_bytes=1000)

    assert loaded.url == submitted_url
    assert loaded.text == "Soup recipe"
    assert loaded.images[0].url == preview_url
    assert harness.calls == [
        (submitted_url, PUBLIC_V4),
        (redirected_url, PUBLIC_V4),
        (preview_url, PUBLIC_V4),
    ]
    assert all(item.closed for item in harness.responses)


async def test_generic_loader_keeps_page_text_when_hardened_fetch_blocks_preview(monkeypatch) -> None:
    submitted_url = "https://public.example/recipe"
    private_preview_url = "https://127.0.0.1/private.jpg?token=secret"
    html = f'<meta property="og:description" content="Soup recipe"><meta property="og:image" content="{private_preview_url}">'.encode()
    page = response(submitted_url, html, content_type="text/html")
    harness = FetchHarness({submitted_url: page})
    install_fetcher(monkeypatch, harness)

    loaded = await GenericUrlContentLoader().load(submitted_url, max_images=1, max_image_bytes=1000)
    result = loaded.resource_results[0]

    assert loaded.text == "Soup recipe"
    assert loaded.images == []
    assert result.kind is SecondaryResourceKind.IMAGE
    assert result.status is SecondaryResourceLoadStatus.FAILED
    assert result.error == FetchErrorCode.PRIVATE_ADDRESS.value
    assert result.to_dict()["url"] == "<redacted-url>"
    assert "token=secret" not in str(result.to_dict())
    assert page.closed


async def test_generic_loader_does_not_parse_non_success_page_responses(monkeypatch) -> None:
    page_url = "https://public.example/failure"
    page = response(
        page_url,
        b'<meta property="og:description" content="response-body-secret">',
        status_code=503,
        content_type="text/html",
    )
    harness = FetchHarness({page_url: page})
    install_fetcher(monkeypatch, harness)

    with pytest.raises(RemoteFetchError) as raised:
        await GenericUrlContentLoader().load(page_url, max_images=1, max_image_bytes=1000)

    assert raised.value.code is FetchErrorCode.UPSTREAM_STATUS
    assert "response-body-secret" not in str(raised.value)
    assert page.closed


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"", "image/jpeg"),
        (b"image", None),
        (b"image", "image/svg+xml"),
        (b"image", "application/zip"),
    ],
)
async def test_generic_loader_enforces_image_content_policy_at_integrated_seam(
    monkeypatch,
    content: bytes,
    content_type: str | None,
) -> None:
    page_url = "https://public.example/recipe"
    image_url = "https://cdn.example/preview"
    page = response(
        page_url,
        f'<meta property="og:description" content="Recipe"><meta property="og:image" content="{image_url}">'.encode(),
        content_type="text/html",
    )
    image = response(image_url, content, content_type=content_type)
    harness = FetchHarness({page_url: page, image_url: image})
    install_fetcher(monkeypatch, harness)

    loaded = await GenericUrlContentLoader().load(page_url, max_images=1, max_image_bytes=1000)

    assert loaded.text == "Recipe"
    assert loaded.images == []
    assert loaded.resource_results[0].error == FetchErrorCode.RESPONSE_TYPE_UNSUPPORTED.value
    assert page.closed
    assert image.closed


async def test_instagram_loader_falls_back_after_hardened_embed_failure(monkeypatch) -> None:
    source_url = "https://www.instagram.com/p/abc/"
    embed_url = "https://www.instagram.com/p/abc/embed/captioned/"
    fallback_image_url = "https://www.instagram.com/fallback.jpg"
    fallback_html = b'<meta property="og:description" content="Fallback caption"><meta property="og:image" content="/fallback.jpg">'
    harness = FetchHarness(
        {
            embed_url: response(embed_url, b"provider-response-secret", status_code=503, content_type="text/html"),
            source_url: response(source_url, fallback_html, content_type="text/html"),
            fallback_image_url: response(fallback_image_url, b"image", content_type="image/jpeg"),
        }
    )
    install_fetcher(monkeypatch, harness)

    loaded = await InstagramUrlContentLoader().load(source_url, max_images=1, max_image_bytes=1000)

    assert loaded.url == source_url
    assert loaded.text == "Fallback caption"
    assert loaded.images[0].url == fallback_image_url
    assert [call[0] for call in harness.calls] == [embed_url, source_url, fallback_image_url]
    assert all(item.closed for item in harness.responses)


async def test_threads_loader_retains_caption_and_redacts_blocked_image_diagnostics(monkeypatch) -> None:
    source_url = "https://www.threads.com/@chef/post/abc?utm_source=secret"
    normalized_url = "https://www.threads.com/@chef/post/abc"
    private_image_url = "https://127.0.0.1/private.jpg?token=secret"
    payload = {
        "postID": "root-pk",
        "data": {
            "edges": [
                {
                    "node": {
                        "thread_items": [
                            {
                                "post": {
                                    "pk": "root-pk",
                                    "code": "abc",
                                    "user": {"id": "u1", "username": "chef"},
                                    "caption": {"text": "Recipe caption"},
                                    "image_versions2": {
                                        "candidates": [{"url": private_image_url, "width": 800, "height": 800}]
                                    },
                                }
                            }
                        ]
                    }
                }
            ]
        },
    }
    page = response(normalized_url, threads_page_html(payload), content_type="text/html")
    harness = FetchHarness({normalized_url: page})
    log_capture = CapturingLogger()
    install_fetcher(monkeypatch, harness)
    monkeypatch.setattr(threads_loader, "logger", log_capture)
    monkeypatch.setenv("RECIPES_STDOUT_LOGS", "false")

    loaded = await ThreadsUrlContentLoader().load(source_url, max_images=1, max_image_bytes=1000)
    result = loaded.resource_results[0]

    assert loaded.text == "Recipe caption"
    assert loaded.images == []
    assert result.kind is SecondaryResourceKind.IMAGE
    assert result.status is SecondaryResourceLoadStatus.FAILED
    assert result.error == FetchErrorCode.PRIVATE_ADDRESS.value
    assert result.to_dict()["url"] == "<redacted-url>"
    log_text = "\n".join(log_capture.messages)
    assert "PRIVATE_ADDRESS" in log_text
    assert "token=secret" not in log_text
    assert "response-body-secret" not in log_text
    assert page.closed


class FakeTranscriptionClient:
    class Audio:
        class Transcriptions:
            def create(self, **_kwargs):
                raise AssertionError("transcription must not run after a failed fetch")

        transcriptions = Transcriptions()

    audio = Audio()


class SuccessfulTranscriptionClient:
    class Audio:
        class Transcriptions:
            def create(self, **_kwargs):
                return SimpleNamespace(text="transcript")

        transcriptions = Transcriptions()

    audio = Audio()


async def test_video_processor_keeps_poster_when_hardened_video_fetch_fails(monkeypatch) -> None:
    poster_url = "https://cdn.example/poster.jpg"
    video_url = "https://cdn.example/video.mp4"
    poster = response(poster_url, b"poster", content_type="image/jpeg")
    failed_video = response(video_url, b"response-body-secret", status_code=503, content_type="video/mp4")
    harness = FetchHarness({poster_url: poster, video_url: failed_video})
    log_capture = CapturingLogger()
    install_fetcher(monkeypatch, harness)
    monkeypatch.setattr(video_processor_module, "logger", log_capture)
    monkeypatch.setenv("RECIPES_STDOUT_LOGS", "false")

    result = await VideoProcessor(
        settings=Settings(openai_api_key="test-key"),
        client=FakeTranscriptionClient(),
    ).prepare_first_pass_video_sources(
        videos=[LoadedRemoteVideo(url=video_url, poster_url=poster_url, position=0, original_name="video.mp4")],
        max_image_bytes=1000,
        max_video_bytes=1000,
    )

    assert len(result.poster_images) == 1
    assert result.transcript_text is None
    assert [(item.kind, item.status, item.error) for item in result.resource_results] == [
        (SecondaryResourceKind.VIDEO_POSTER, SecondaryResourceLoadStatus.LOADED, None),
        (SecondaryResourceKind.VIDEO_TRANSCRIPT, SecondaryResourceLoadStatus.FAILED, FetchErrorCode.UPSTREAM_STATUS.value),
    ]
    log_text = "\n".join(log_capture.messages)
    assert "response-body-secret" not in log_text
    assert video_url not in log_text
    assert all(item.closed for item in harness.responses)


@pytest.mark.parametrize(
    ("content_type", "expected_status"),
    [
        (None, SecondaryResourceLoadStatus.LOADED),
        ("application/octet-stream", SecondaryResourceLoadStatus.LOADED),
        ("video/mp4", SecondaryResourceLoadStatus.LOADED),
        ("application/zip", SecondaryResourceLoadStatus.FAILED),
    ],
)
async def test_video_processor_applies_provider_compatible_content_policy(
    monkeypatch,
    content_type: str | None,
    expected_status: SecondaryResourceLoadStatus,
) -> None:
    video_url = "https://cdn.example/video.mp4"
    video = response(video_url, b"video", content_type=content_type)
    harness = FetchHarness({video_url: video})
    install_fetcher(monkeypatch, harness)

    result = await VideoProcessor(
        settings=Settings(openai_api_key="test-key"),
        client=SuccessfulTranscriptionClient(),
    ).prepare_first_pass_video_sources(
        videos=[LoadedRemoteVideo(url=video_url, poster_url=None, position=0, original_name="video.mp4")],
        max_image_bytes=1000,
        max_video_bytes=1000,
    )

    transcript_result = result.resource_results[1]
    assert transcript_result.status is expected_status
    if expected_status is SecondaryResourceLoadStatus.LOADED:
        assert transcript_result.error is None
        assert result.transcript_text == "Video 1 transcript:\ntranscript"
    else:
        assert transcript_result.error == FetchErrorCode.RESPONSE_TYPE_UNSUPPORTED.value
        assert result.transcript_text is None
    assert video.closed


@pytest.mark.parametrize(
    ("raw_url", "expected_code"),
    [
        ("", FetchErrorCode.INVALID_URL),
        ("//public.example/path", FetchErrorCode.INVALID_URL),
        ("file:///etc/passwd", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("gopher://public.example/", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("data:text/plain,secret", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("ftp://public.example/file", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("http://public.example/", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("https://user:pass@public.example/", FetchErrorCode.INVALID_URL),
        ("https://public.example/path#secret", FetchErrorCode.INVALID_URL),
        ("https://public.example:8443/", FetchErrorCode.UNSUPPORTED_PORT),
        ("https://bad..example/", FetchErrorCode.INVALID_URL),
        ("https://0.0.0.0/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://169.254.1.1/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://127.0.0.1/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://[::]/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://[fd00::1]/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://private.example/", FetchErrorCode.PRIVATE_ADDRESS),
        ("https://mixed.example/", FetchErrorCode.PRIVATE_ADDRESS),
    ],
)
async def test_integrated_fetch_rejects_adversarial_request_urls(raw_url: str, expected_code: FetchErrorCode) -> None:
    harness = FetchHarness(
        {},
        resolved={
            "private.example": (ResolvedAddress(PRIVATE_V4, socket.AF_INET),),
            "mixed.example": (
                ResolvedAddress(PUBLIC_V4, socket.AF_INET),
                ResolvedAddress(PRIVATE_V4, socket.AF_INET),
            )
        },
    )

    with pytest.raises(RemoteFetchError) as raised:
        await harness.fetcher().fetch_bounded(raw_url, max_bytes=128)

    assert raised.value.code is expected_code
    assert harness.calls == []


@pytest.mark.parametrize(
    "location",
    [
        "http://public.example/insecure",
        "https://public.example:8443/port",
        "https://user:pass@public.example/private",
        "https://127.0.0.1/metadata",
        "https://[invalid",
    ],
)
async def test_integrated_fetch_revalidates_every_redirect_target(location: str) -> None:
    start_url = "https://public.example/start"
    first_response = response(start_url, status_code=302, headers={"Location": location, "Content-Length": "0"})
    harness = FetchHarness({start_url: first_response})

    with pytest.raises(RemoteFetchError) as raised:
        await harness.fetcher().fetch_bounded(start_url, max_bytes=128)

    assert raised.value.code is FetchErrorCode.REDIRECT_BLOCKED
    assert harness.calls == [(start_url, PUBLIC_V4)]
    assert first_response.closed


@pytest.mark.parametrize(
    "timeout_error",
    [
        httpx.ConnectTimeout("connect secret"),
        httpx.PoolTimeout("pool secret"),
    ],
)
async def test_integrated_fetch_maps_connection_timeouts_without_retry(timeout_error: httpx.TimeoutException) -> None:
    url = "https://public.example/timeout"
    harness = FetchHarness({url: timeout_error})

    with pytest.raises(RemoteFetchError) as raised:
        await harness.fetcher().fetch_bounded(url, max_bytes=128)

    assert raised.value.code is FetchErrorCode.TIMEOUT
    assert len(harness.calls) == 1
    assert "connect secret" not in str(raised.value)
    assert "pool secret" not in str(raised.value)


async def test_integrated_fetch_maps_read_timeout_and_closes_response(monkeypatch) -> None:
    url = "https://public.example/slow"
    slow_response = response(
        url,
        chunks=(b"partial",),
        headers={"Content-Length": "7"},
        stream_error=httpx.ReadTimeout("response-body-secret"),
    )
    harness = FetchHarness({url: slow_response})
    install_fetcher(monkeypatch, harness)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch(url, max_bytes=128)

    assert raised.value.code is FetchErrorCode.TIMEOUT
    assert slow_response.closed
    assert harness.calls == [(url, PUBLIC_V4)]
    assert "response-body-secret" not in str(raised.value)
