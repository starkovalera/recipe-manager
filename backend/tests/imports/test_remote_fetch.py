import asyncio
import gzip
import socket

import httpcore
import httpx
import pytest

import app.imports.source_loading.url_loaders.generic as generic_loader
from app.imports.source_loading.remote_fetch import (
    HTML_FETCH_TIMEOUTS,
    VIDEO_FETCH_TIMEOUTS,
    FetchErrorCode,
    FetchTimeouts,
    PinnedAsyncHTTPTransport,
    RemoteFetcher,
    RemoteFetchError,
    ResolvedAddress,
    VettedDestination,
    httpx_destination_request,
    validate_url,
)

PUBLIC_V4 = "93.184.216.34"
PUBLIC_V6 = "2001:4860:4860::8888"
PRIVATE_V4 = "192.168.1.20"


def response(url: str, status_code: int = 200, *, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        headers=headers,
        content=b"ok",
        request=httpx.Request("GET", url),
    )


@pytest.mark.parametrize(
    ("raw_url", "code"),
    [
        ("", FetchErrorCode.INVALID_URL),
        ("example.test/path", FetchErrorCode.INVALID_URL),
        ("//example.test/path", FetchErrorCode.INVALID_URL),
        ("https://user:pass@example.test/path", FetchErrorCode.INVALID_URL),
        ("https://example.test/path#secret", FetchErrorCode.INVALID_URL),
        ("https://example.test:8443/path", FetchErrorCode.UNSUPPORTED_PORT),
        ("https://example.test:bad/path", FetchErrorCode.INVALID_URL),
        ("https://bad_host.test/path", FetchErrorCode.INVALID_URL),
        ("file:///etc/passwd", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("gopher://example.test/", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("data:text/plain,secret", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("ftp://example.test/file", FetchErrorCode.UNSUPPORTED_SCHEME),
        ("http://example.test/path", FetchErrorCode.UNSUPPORTED_SCHEME),
    ],
)
def test_validate_url_rejects_unsafe_input(raw_url: str, code: FetchErrorCode):
    with pytest.raises(RemoteFetchError) as raised:
        validate_url(raw_url)

    assert raised.value.code == code
    if raw_url:
        assert raw_url not in str(raised.value)


@pytest.mark.parametrize(
    "raw_url",
    [
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://[::ffff:127.0.0.1]/",
        "https://2130706433/",
        "https://0x7f000001/",
        "https://169.254.169.254/",
        "https://100.64.0.1/",
        "https://192.0.0.9/",
        "https://224.0.0.1/",
        "https://[ff02::1]/",
    ],
)
def test_validate_url_rejects_private_literal_and_encoded_addresses(raw_url: str):
    with pytest.raises(RemoteFetchError) as raised:
        validate_url(raw_url)

    assert raised.value.code == FetchErrorCode.PRIVATE_ADDRESS


def test_validate_url_normalizes_https_host_and_empty_fragment():
    validated = validate_url("HTTPS://Example.test:443/recipe?source=1#")

    assert validated.value == "https://example.test/recipe?source=1"
    assert validated.hostname == "example.test"
    assert validated.port == 443


@pytest.mark.parametrize("raw_url", [f"https://{PUBLIC_V4}/", f"https://[{PUBLIC_V6}]/"])
def test_validate_url_accepts_global_ip_literals(raw_url: str):
    assert validate_url(raw_url).value.startswith("https://")


@pytest.mark.asyncio
async def test_dns_requires_every_answer_to_be_globally_reachable():
    async def resolver(_hostname: str, _port: int):
        return (
            ResolvedAddress(PUBLIC_V4, socket.AF_INET),
            ResolvedAddress(PRIVATE_V4, socket.AF_INET),
        )

    async def transport(_url, _destination):
        raise AssertionError("blocked DNS result must not reach transport")

    with pytest.raises(RemoteFetchError) as raised:
        await RemoteFetcher(resolver=resolver, transport=transport).fetch("https://example.test/")

    assert raised.value.code == FetchErrorCode.PRIVATE_ADDRESS


@pytest.mark.asyncio
async def test_dns_empty_or_unusable_answers_are_stable_failures():
    async def empty_resolver(_hostname: str, _port: int):
        return ()

    async def invalid_resolver(_hostname: str, _port: int):
        return (ResolvedAddress("not-an-ip", socket.AF_INET),)

    for resolver in (empty_resolver, invalid_resolver):
        with pytest.raises(RemoteFetchError) as raised:
            await RemoteFetcher(resolver=resolver, transport=lambda *_: None).fetch("https://example.test/")
        assert raised.value.code == FetchErrorCode.DNS_FAILED


@pytest.mark.asyncio
async def test_relative_redirects_are_revalidated_and_use_vetted_destinations():
    resolved_hosts: list[str] = []
    connected: list[tuple[str, str]] = []

    async def resolver(hostname: str, _port: int):
        resolved_hosts.append(hostname)
        return (ResolvedAddress(PUBLIC_V4, socket.AF_INET),)

    async def transport(url, destination):
        connected.append((url.hostname, destination.address))
        if url.value == "https://example.test/start":
            return response(url.value, 302, headers={"Location": "/next"})
        return response(url.value)

    final = await RemoteFetcher(resolver=resolver, transport=transport).fetch("https://example.test/start")
    await final.aclose()

    assert resolved_hosts == ["example.test", "example.test"]
    assert connected == [("example.test", PUBLIC_V4), ("example.test", PUBLIC_V4)]
    assert str(final.url) == "https://example.test/next"


@pytest.mark.asyncio
async def test_redirect_to_private_destination_is_blocked_before_connection():
    async def resolver(hostname: str, _port: int):
        address = PRIVATE_V4 if hostname == "internal.test" else PUBLIC_V4
        return (ResolvedAddress(address, socket.AF_INET),)

    connected: list[str] = []

    async def transport(url, destination):
        connected.append(destination.address)
        return response(url.value, 302, headers={"Location": "https://internal.test/metadata"})

    with pytest.raises(RemoteFetchError) as raised:
        await RemoteFetcher(resolver=resolver, transport=transport).fetch("https://example.test/")

    assert raised.value.code == FetchErrorCode.REDIRECT_BLOCKED
    assert connected == [PUBLIC_V4]


@pytest.mark.asyncio
async def test_redirect_loops_and_more_than_five_redirects_are_rejected():
    async def resolver(_hostname: str, _port: int):
        return (ResolvedAddress(PUBLIC_V4, socket.AF_INET),)

    async def loop_transport(url, _destination):
        return response(url.value, 302, headers={"Location": "/start"})

    with pytest.raises(RemoteFetchError) as loop_error:
        await RemoteFetcher(resolver=resolver, transport=loop_transport).fetch("https://example.test/start")
    assert loop_error.value.code == FetchErrorCode.REDIRECT_LIMIT

    count = 0

    async def long_transport(url, _destination):
        nonlocal count
        count += 1
        return response(url.value, 302, headers={"Location": f"/hop-{count}"})

    with pytest.raises(RemoteFetchError) as limit_error:
        await RemoteFetcher(resolver=resolver, transport=long_transport).fetch("https://example.test/start")
    assert limit_error.value.code == FetchErrorCode.REDIRECT_LIMIT
    assert count == 6


@pytest.mark.asyncio
async def test_redirect_status_without_location_and_unsupported_status_are_blocked():
    async def resolver(_hostname: str, _port: int):
        return (ResolvedAddress(PUBLIC_V4, socket.AF_INET),)

    async def missing_location(url, _destination):
        return response(url.value, 301)

    async def unsupported_status(url, _destination):
        return response(url.value, 300, headers={"Location": "/next"})

    for transport in (missing_location, unsupported_status):
        with pytest.raises(RemoteFetchError) as raised:
            await RemoteFetcher(resolver=resolver, transport=transport).fetch("https://example.test/")
        assert raised.value.code == FetchErrorCode.REDIRECT_BLOCKED


@pytest.mark.asyncio
async def test_default_fetch_adapter_returns_final_url_and_preserves_stable_status_errors(monkeypatch):
    async def resolver(_hostname: str, _port: int):
        return (ResolvedAddress(PUBLIC_V4, socket.AF_INET),)

    async def transport(url, _destination):
        if url.value.endswith("/start"):
            return response(url.value, 302, headers={"Location": "/final"})
        return response(url.value, 200)

    monkeypatch.setattr(generic_loader, "_remote_fetcher", RemoteFetcher(resolver=resolver, transport=transport))

    fetched = await generic_loader.httpx_fetch("https://example.test/start", max_bytes=2)

    assert fetched.content == b"ok"
    assert fetched.final_url == "https://example.test/final"

    async def failed_transport(url, _destination):
        return response(url.value, 503)

    monkeypatch.setattr(generic_loader, "_remote_fetcher", RemoteFetcher(resolver=resolver, transport=failed_transport))
    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/failure", max_bytes=100)
    assert raised.value.code == FetchErrorCode.UPSTREAM_STATUS
    assert str(raised.value) == FetchErrorCode.UPSTREAM_STATUS.value


class RecordingStream(httpcore.AsyncNetworkStream):
    def __init__(self):
        self.sni_hostname: str | None = None
        self.writes: list[bytes] = []
        self.closed = False
        self._chunks = [
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nok"
        ]

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        del max_bytes, timeout
        return self._chunks.pop(0) if self._chunks else b""

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        del timeout
        self.writes.append(buffer)

    async def aclose(self) -> None:
        self.closed = True

    async def start_tls(self, ssl_context, server_hostname: str | None = None, timeout: float | None = None):
        del ssl_context, timeout
        self.sni_hostname = server_hostname
        return self


class RecordingBackend(httpcore.AsyncNetworkBackend):
    def __init__(self):
        self.calls: list[tuple[str, int]] = []
        self.stream = RecordingStream()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        del timeout, local_address, socket_options
        self.calls.append((host, port))
        return self.stream

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise AssertionError(f"unexpected unix socket: {path}")

    async def sleep(self, seconds: float) -> None:
        del seconds


class StreamingResponse:
    def __init__(
        self,
        url: str,
        chunks: list[bytes],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        wait_after_first_chunk: float | None = None,
    ):
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self.url = httpx.URL(url)
        self.chunks = chunks
        self.read_bytes = 0
        self.closed = False
        self.wait_after_first_chunk = wait_after_first_chunk

    async def aiter_bytes(self, chunk_size: int | None = None):
        del chunk_size
        for index, chunk in enumerate(self.chunks):
            self.read_bytes += len(chunk)
            yield chunk
            if index == 0 and self.wait_after_first_chunk is not None:
                await asyncio.sleep(self.wait_after_first_chunk)

    async def aclose(self) -> None:
        self.closed = True


TEST_FETCH_TIMEOUTS = FetchTimeouts(3, 5, 1, 15)


def streaming_fetcher(monkeypatch, response: StreamingResponse, *, timeouts: FetchTimeouts = TEST_FETCH_TIMEOUTS):
    async def resolver(_hostname: str, _port: int):
        return (ResolvedAddress(PUBLIC_V4, socket.AF_INET),)

    async def transport(_url, _destination):
        return response

    monkeypatch.setattr(
        generic_loader,
        "_remote_fetcher",
        RemoteFetcher(resolver=resolver, transport=transport, timeouts=timeouts),
    )


@pytest.mark.asyncio
async def test_actual_connection_uses_vetted_ip_and_original_hostname_for_tls_and_host():
    backend = RecordingBackend()
    destination = VettedDestination(
        hostname="example.test",
        address=PUBLIC_V4,
        family=socket.AF_INET,
    )
    transport = PinnedAsyncHTTPTransport(destination, network_backend=backend)

    async with httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=False) as client:
        fetched = await client.get("https://example.test/recipe")

    assert fetched.content == b"ok"
    assert backend.calls == [(PUBLIC_V4, 443)]
    assert backend.stream.sni_hostname == "example.test"
    assert b"Host: example.test" in b"".join(backend.stream.writes)
    assert backend.stream.closed


@pytest.mark.asyncio
async def test_scoped_httpx_response_streams_before_closing_its_client():
    backend = RecordingBackend()
    destination = VettedDestination(
        hostname="example.test",
        address=PUBLIC_V4,
        family=socket.AF_INET,
    )

    response = await httpx_destination_request(
        validate_url("https://example.test/recipe"),
        destination,
        network_backend=backend,
    )
    assert [chunk async for chunk in response.aiter_bytes(chunk_size=2)] == [b"ok"]
    await response.aclose()

    assert backend.stream.closed


def test_fetch_timeout_profiles_match_p11_budgets():
    assert (HTML_FETCH_TIMEOUTS.connect, HTML_FETCH_TIMEOUTS.read, HTML_FETCH_TIMEOUTS.pool, HTML_FETCH_TIMEOUTS.operation) == (
        3.0,
        5.0,
        1.0,
        15.0,
    )
    assert (VIDEO_FETCH_TIMEOUTS.connect, VIDEO_FETCH_TIMEOUTS.read, VIDEO_FETCH_TIMEOUTS.pool, VIDEO_FETCH_TIMEOUTS.operation) == (
        5.0,
        15.0,
        1.0,
        90.0,
    )


@pytest.mark.asyncio
async def test_bounded_fetch_accepts_at_limit_and_rejects_the_first_extra_decoded_byte(monkeypatch):
    at_limit = StreamingResponse("https://example.test/at-limit", [b"abc"], headers={"Content-Length": "3"})
    streaming_fetcher(monkeypatch, at_limit)

    fetched = await generic_loader.httpx_fetch("https://example.test/at-limit", max_bytes=3)

    assert fetched.content == b"abc"
    assert at_limit.read_bytes == 3
    assert at_limit.closed

    over_limit = StreamingResponse("https://example.test/over-limit", [b"abcd"], headers={"Content-Length": "4"})
    streaming_fetcher(monkeypatch, over_limit)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/over-limit", max_bytes=3)

    assert raised.value.code == FetchErrorCode.RESPONSE_TOO_LARGE
    assert over_limit.read_bytes == 0
    assert over_limit.closed

    lying_length = StreamingResponse("https://example.test/lying", [b"abcd"], headers={"Content-Length": "2"})
    streaming_fetcher(monkeypatch, lying_length)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/lying", max_bytes=3)

    assert raised.value.code == FetchErrorCode.RESPONSE_TOO_LARGE
    assert lying_length.read_bytes == 4
    assert lying_length.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_length",
    ["invalid", "-1", "2,3"],
)
async def test_bounded_fetch_rejects_invalid_or_conflicting_content_length(monkeypatch, content_length: str):
    response_to_read = StreamingResponse(
        "https://example.test/headers",
        [b"ok"],
        headers={"Content-Length": content_length},
    )
    streaming_fetcher(monkeypatch, response_to_read)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/headers", max_bytes=10)

    assert raised.value.code == FetchErrorCode.RESPONSE_HEADERS_INVALID
    assert response_to_read.read_bytes == 0
    assert response_to_read.closed


@pytest.mark.asyncio
async def test_bounded_fetch_handles_unknown_length_and_supported_encoding_without_truncation(monkeypatch):
    response_to_read = StreamingResponse(
        "https://example.test/chunked",
        [b"ab", b"c"],
        headers={"Transfer-Encoding": "chunked", "Content-Encoding": "gzip"},
    )
    streaming_fetcher(monkeypatch, response_to_read)

    fetched = await generic_loader.httpx_fetch("https://example.test/chunked", max_bytes=3)

    assert fetched.content == b"abc"
    assert fetched.headers["content-encoding"] == "gzip"
    assert response_to_read.closed


@pytest.mark.asyncio
async def test_bounded_fetch_applies_limit_to_decoded_compressed_bytes(monkeypatch):
    compressed_response = httpx.Response(
        200,
        headers={"Content-Encoding": "gzip"},
        content=gzip.compress(b"abcd"),
        request=httpx.Request("GET", "https://example.test/compressed"),
    )
    streaming_fetcher(monkeypatch, compressed_response)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/compressed", max_bytes=3)

    assert raised.value.code == FetchErrorCode.RESPONSE_TOO_LARGE
    assert compressed_response.is_closed


@pytest.mark.asyncio
async def test_bounded_fetch_rejects_unknown_content_encoding_before_reading(monkeypatch):
    response_to_read = StreamingResponse(
        "https://example.test/encoded",
        [b"secret"],
        headers={"Content-Encoding": "x-custom"},
    )
    streaming_fetcher(monkeypatch, response_to_read)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/encoded", max_bytes=100)

    assert raised.value.code == FetchErrorCode.RESPONSE_HEADERS_INVALID
    assert response_to_read.read_bytes == 0
    assert response_to_read.closed


@pytest.mark.asyncio
async def test_bounded_fetch_maps_non_success_status_and_closes_response(monkeypatch):
    response_to_read = StreamingResponse("https://example.test/failure", [b"error"], status_code=503)
    streaming_fetcher(monkeypatch, response_to_read)

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/failure", max_bytes=100)

    assert raised.value.code == FetchErrorCode.UPSTREAM_STATUS
    assert response_to_read.read_bytes == 0
    assert response_to_read.closed


@pytest.mark.asyncio
async def test_bounded_fetch_maps_wall_clock_timeout_and_closes_stream(monkeypatch):
    response_to_read = StreamingResponse(
        "https://example.test/slow",
        [b"a", b"b"],
        wait_after_first_chunk=1,
    )
    streaming_fetcher(monkeypatch, response_to_read, timeouts=FetchTimeouts(3, 5, 1, 0.01))

    with pytest.raises(RemoteFetchError) as raised:
        await generic_loader.httpx_fetch("https://example.test/slow", max_bytes=100)

    assert raised.value.code == FetchErrorCode.TIMEOUT
    assert response_to_read.closed


@pytest.mark.asyncio
async def test_bounded_fetch_preserves_cancellation_after_cleanup(monkeypatch):
    started = asyncio.Event()

    class CancellableResponse(StreamingResponse):
        async def aiter_bytes(self, chunk_size: int | None = None):
            del chunk_size
            started.set()
            await asyncio.sleep(10)
            yield b"never"

    response_to_read = CancellableResponse("https://example.test/cancel", [])
    streaming_fetcher(monkeypatch, response_to_read)
    task = asyncio.create_task(generic_loader.httpx_fetch("https://example.test/cancel", max_bytes=100))

    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert response_to_read.closed
