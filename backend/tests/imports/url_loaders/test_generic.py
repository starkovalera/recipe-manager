import pytest

from app.imports.source_loading.remote_fetch import FetchErrorCode, RemoteFetchError
from app.imports.source_loading.types import SecondaryResourceKind, SecondaryResourceLoadStatus
from app.imports.source_loading.url_loaders import GenericUrlContentLoader


class FakeResponse:
    def __init__(self, content: bytes, content_type: str, final_url: str = ""):
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.final_url = final_url


async def fake_fetch(url: str, max_bytes: int) -> FakeResponse:
    if url.endswith("image.jpg"):
        return FakeResponse(b"image-bytes", "image/jpeg")
    html = b"""
    <html>
      <head>
        <meta property="og:description" content="Soup recipe caption">
        <meta property="og:image" content="https://example.com/image.jpg">
      </head>
      <body><h1>Soup</h1><p>Boil water.</p></body>
    </html>
    """
    return FakeResponse(html, "text/html")


async def test_generic_loader_extracts_text_and_preview_image():
    loader = GenericUrlContentLoader(fetch=fake_fetch)

    loaded = await loader.load("https://example.com/recipe", max_images=1, max_image_bytes=1000)

    assert loaded.text.startswith("Soup recipe caption")
    assert loaded.images[0].url == "https://example.com/image.jpg"
    assert loaded.images[0].mime_type == "image/jpeg"


async def test_generic_loader_does_not_download_images_when_capacity_is_zero():
    calls: list[str] = []

    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        calls.append(url)
        return await fake_fetch(url, max_bytes)

    loader = GenericUrlContentLoader(fetch=fetch)

    loaded = await loader.load("https://example.com/recipe", max_images=0, max_image_bytes=1000)

    assert loaded.images == []
    assert calls == ["https://example.com/recipe"]


async def test_generic_loader_reports_preview_failure_and_keeps_text():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.endswith("image.jpg"):
            raise RuntimeError("image unavailable")
        return await fake_fetch(url, max_bytes)

    loaded = await GenericUrlContentLoader(fetch=fetch).load(
        "https://example.com/recipe",
        max_images=1,
        max_image_bytes=1000,
    )

    assert loaded.text == "Soup recipe caption"
    assert loaded.images == []
    assert len(loaded.resource_results) == 1
    assert loaded.resource_results[0].kind == SecondaryResourceKind.IMAGE
    assert loaded.resource_results[0].status == SecondaryResourceLoadStatus.FAILED


async def test_generic_loader_resolves_preview_against_effective_url_without_changing_source_url():
    calls: list[str] = []

    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        calls.append(url)
        if url == "https://redirected.example/assets/preview.jpg":
            return FakeResponse(b"image-bytes", "IMAGE/JPEG; charset=binary")
        html = b'<meta property="og:image" content="/assets/preview.jpg">'
        return FakeResponse(html, "text/html", final_url="https://redirected.example/final/page")

    submitted_url = "https://submitted.example/recipe?token=secret"
    loaded = await GenericUrlContentLoader(fetch=fetch).load(submitted_url, max_images=1, max_image_bytes=1000)

    assert calls == [submitted_url, "https://redirected.example/assets/preview.jpg"]
    assert loaded.url == submitted_url
    assert loaded.images[0].url == "https://redirected.example/assets/preview.jpg"
    assert loaded.images[0].mime_type == "image/jpeg"


@pytest.mark.parametrize(
    ("fetch_error", "expected_code"),
    [
        (RemoteFetchError(FetchErrorCode.TIMEOUT), FetchErrorCode.TIMEOUT.value),
        (RuntimeError("private response details"), FetchErrorCode.NETWORK_ERROR.value),
    ],
)
async def test_generic_loader_records_stable_preview_failure_codes(fetch_error: Exception, expected_code: str):
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.endswith("image.jpg"):
            raise fetch_error
        return await fake_fetch(url, max_bytes)

    loaded = await GenericUrlContentLoader(fetch=fetch).load(
        "https://example.com/recipe",
        max_images=1,
        max_image_bytes=1000,
    )

    assert loaded.resource_results[0].error == expected_code


async def test_generic_loader_rejects_unsupported_page_content_type():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        return FakeResponse(b"binary", "application/octet-stream")

    with pytest.raises(RemoteFetchError) as raised:
        await GenericUrlContentLoader(fetch=fetch).load("https://example.com/recipe", max_images=0, max_image_bytes=1000)

    assert raised.value.code is FetchErrorCode.RESPONSE_TYPE_UNSUPPORTED
