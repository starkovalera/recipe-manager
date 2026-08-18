"""Secure remote URL validation, streaming, and vetted-destination fetching.

This module owns the P11 Child A and Child B fetch seam. It validates every URL
and redirect, resolves every hostname before connecting, pins the TCP
connection to a validated address, and bounds the decoded response while
retaining the hostname for HTTP Host and TLS SNI.

The remaining residual assumption is that the selected direct transport and
the execution environment do not perform an unvalidated second lookup or
redirect the socket through a transparent proxy.  Production egress controls
remain required; this module makes that assumption explicit and testable.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from inspect import isawaitable
from typing import Protocol
from urllib.parse import SplitResult, urljoin, urlsplit

import anyio
import httpcore
import httpx


class FetchErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_SCHEME = "UNSUPPORTED_SCHEME"
    UNSUPPORTED_PORT = "UNSUPPORTED_PORT"
    DNS_FAILED = "DNS_FAILED"
    PRIVATE_ADDRESS = "PRIVATE_ADDRESS"
    REDIRECT_BLOCKED = "REDIRECT_BLOCKED"
    REDIRECT_LIMIT = "REDIRECT_LIMIT"
    UPSTREAM_STATUS = "UPSTREAM_STATUS"
    RESPONSE_HEADERS_INVALID = "RESPONSE_HEADERS_INVALID"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    RESPONSE_TYPE_UNSUPPORTED = "RESPONSE_TYPE_UNSUPPORTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    CANCELLED = "CANCELLED"


class RemoteFetchError(RuntimeError):
    """A fetch failure whose public representation contains only a stable code."""

    def __init__(self, code: FetchErrorCode):
        self.code = code
        super().__init__(code.value)


def stable_fetch_error_code(
    error: BaseException,
    *,
    fallback: FetchErrorCode = FetchErrorCode.NETWORK_ERROR,
) -> str:
    """Return the safe, stable diagnostic code for a fetch-boundary error."""

    if isinstance(error, RemoteFetchError):
        return error.code.value
    if isinstance(error, (httpx.TimeoutException, TimeoutError)):
        return FetchErrorCode.TIMEOUT.value
    if isinstance(error, (httpx.DecodingError, httpx.RemoteProtocolError)):
        return FetchErrorCode.RESPONSE_HEADERS_INVALID.value
    return fallback.value


@dataclass(frozen=True)
class ResolvedAddress:
    """One address returned by the resolver seam."""

    address: str
    family: int = socket.AF_UNSPEC


@dataclass(frozen=True)
class ValidatedURL:
    """Canonical HTTPS URL and the hostname used for DNS and TLS."""

    value: str
    hostname: str
    port: int = 443


@dataclass(frozen=True)
class FetchTimeouts:
    """Per-request transport budgets; operation bounds the whole fetch."""

    connect: float
    read: float
    pool: float
    operation: float

    def __post_init__(self) -> None:
        if any(value <= 0 for value in (self.connect, self.read, self.pool, self.operation)):
            raise ValueError("fetch timeouts must be positive")

    def httpx_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(connect=self.connect, read=self.read, write=self.read, pool=self.pool)


HTML_FETCH_TIMEOUTS = FetchTimeouts(connect=3.0, read=5.0, pool=1.0, operation=15.0)
VIDEO_FETCH_TIMEOUTS = FetchTimeouts(connect=5.0, read=15.0, pool=1.0, operation=90.0)
DEFAULT_HTTP_LIMITS = httpx.Limits(max_connections=4, max_keepalive_connections=0)
_MAX_STREAM_CHUNK = 64 * 1024
_SUPPORTED_CONTENT_ENCODINGS = frozenset({"identity", "gzip", "deflate", "br", "zstd"})


@dataclass(frozen=True)
class VettedDestination:
    """A globally reachable address approved for one connection attempt."""

    hostname: str
    address: str
    family: int
    port: int = 443


@dataclass(frozen=True)
class BoundedFetchResponse:
    """Decoded response data that has passed the shared fetch policy."""

    content: bytes
    headers: dict[str, str]
    final_url: str


class TransportResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    url: httpx.URL

    def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        """Yield decoded response bytes without buffering the complete body."""

    async def aclose(self) -> None:
        """Release response resources."""


Resolver = Callable[[str, int], Sequence[ResolvedAddress] | Awaitable[Sequence[ResolvedAddress]]]
DestinationTransport = Callable[
    [ValidatedURL, VettedDestination], TransportResponse | Awaitable[TransportResponse]
]

MAX_REDIRECTS = 5
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)

# ipaddress.is_global is the primary policy primitive.  These explicit
# metadata ranges are project-owned defense-in-depth for platform addresses
# that must never become import destinations.
_BLOCKED_INFRASTRUCTURE_RANGES = tuple(
    ipaddress.ip_network(value)
    for value in (
        "168.63.129.16/32",  # Azure platform virtual IP
        "169.254.169.254/32",  # AWS/GCP/Azure metadata endpoint
        "169.254.170.2/32",  # ECS task metadata endpoint
        "192.0.0.0/24",  # IETF protocol assignments, including global-looking exceptions
        "224.0.0.0/4",  # IPv4 multicast
        "fd00:ec2::254/128",  # AWS IPv6 metadata endpoint
        "ff00::/8",  # IPv6 multicast
    )
)


def _error(code: FetchErrorCode, cause: BaseException | None = None) -> RemoteFetchError:
    error = RemoteFetchError(code)
    if cause is not None:
        error.__cause__ = cause
    return error


def _parse_literal_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = hostname.rstrip(".")
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        pass

    # socket.inet_aton accepts legacy decimal/hex/octal IPv4 spellings such as
    # 2130706433 and 0177.0.0.1.  Treat those as literals before DNS can turn
    # an encoded private address into a seemingly ordinary hostname.
    if ":" not in candidate and re.fullmatch(r"[0-9a-fxob.]+", candidate, flags=re.IGNORECASE):
        try:
            return ipaddress.ip_address(socket.inet_aton(candidate))
        except (OSError, ValueError):
            pass
    return None


def _is_globally_reachable(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    mapped = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
    classification_address = mapped or address
    if any(
        blocked.version == classification_address.version and classification_address in blocked
        for blocked in _BLOCKED_INFRASTRUCTURE_RANGES
    ):
        return False
    return classification_address.is_global


def _normalize_hostname(raw_hostname: str) -> tuple[str, ipaddress.IPv4Address | ipaddress.IPv6Address | None]:
    if not raw_hostname or "%" in raw_hostname:
        raise _error(FetchErrorCode.INVALID_URL)

    literal = _parse_literal_ip(raw_hostname)
    if literal is not None:
        return str(literal), literal

    try:
        hostname = raw_hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as error:
        raise _error(FetchErrorCode.INVALID_URL, error) from error
    if not hostname or len(hostname) > 253:
        raise _error(FetchErrorCode.INVALID_URL)
    labels = hostname.split(".")
    if any(not _HOST_LABEL.fullmatch(label) for label in labels):
        raise _error(FetchErrorCode.INVALID_URL)
    return hostname, None


def _has_explicit_port(netloc: str) -> bool:
    host_port = netloc.rsplit("@", 1)[-1]
    if host_port.startswith("["):
        return "]" in host_port and host_port[host_port.find("]") + 1 :].startswith(":")
    return ":" in host_port


def validate_url(raw_url: str) -> ValidatedURL:
    """Validate and canonicalize one initial or redirect URL."""

    if not isinstance(raw_url, str) or not raw_url or any(
        character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F for character in raw_url
    ):
        raise _error(FetchErrorCode.INVALID_URL)
    try:
        parsed = urlsplit(raw_url)
    except ValueError as error:
        raise _error(FetchErrorCode.INVALID_URL, error) from error

    scheme = parsed.scheme.lower()
    if not scheme:
        raise _error(FetchErrorCode.INVALID_URL)
    if scheme != "https":
        raise _error(FetchErrorCode.UNSUPPORTED_SCHEME)
    if not parsed.netloc:
        raise _error(FetchErrorCode.INVALID_URL)
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise _error(FetchErrorCode.INVALID_URL)
    try:
        raw_hostname = parsed.hostname
        parsed_port = parsed.port
    except ValueError as error:
        raise _error(FetchErrorCode.INVALID_URL, error) from error
    if raw_hostname is None:
        raise _error(FetchErrorCode.INVALID_URL)
    if _has_explicit_port(parsed.netloc) and parsed_port is None:
        raise _error(FetchErrorCode.INVALID_URL)
    if parsed_port is not None and parsed_port != 443:
        raise _error(FetchErrorCode.UNSUPPORTED_PORT)

    hostname, literal = _normalize_hostname(raw_hostname)
    if literal is not None and not _is_globally_reachable(literal):
        raise _error(FetchErrorCode.PRIVATE_ADDRESS)

    netloc = f"[{hostname}]" if ":" in hostname else hostname
    value = SplitResult(scheme, netloc, parsed.path or "/", parsed.query, "").geturl()
    return ValidatedURL(value=value, hostname=hostname)


def _address_family(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> int:
    return socket.AF_INET6 if address.version == 6 else socket.AF_INET


async def _system_resolver(hostname: str, port: int) -> Sequence[ResolvedAddress]:
    results = await anyio.to_thread.run_sync(
        socket.getaddrinfo,
        hostname,
        port,
        socket.AF_UNSPEC,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
    )
    return tuple(
        ResolvedAddress(address=sockaddr[0], family=family)
        for family, _socktype, _proto, _canonname, sockaddr in results
        if family in (socket.AF_INET, socket.AF_INET6)
    )


async def _vetted_destination(validated: ValidatedURL, resolver: Resolver) -> VettedDestination:
    literal = _parse_literal_ip(validated.hostname)
    if literal is not None:
        return VettedDestination(
            hostname=validated.hostname,
            address=str(literal),
            family=_address_family(literal),
        )

    try:
        resolved = resolver(validated.hostname, validated.port)
        if isawaitable(resolved):
            resolved = await resolved
    except RemoteFetchError:
        raise
    except Exception as error:
        raise _error(FetchErrorCode.DNS_FAILED, error) from error
    if not resolved:
        raise _error(FetchErrorCode.DNS_FAILED)

    vetted: list[tuple[str, int]] = []
    for candidate in resolved:
        address = _parse_literal_ip(candidate.address)
        if address is None:
            raise _error(FetchErrorCode.DNS_FAILED)
        family = _address_family(address)
        if candidate.family not in (socket.AF_UNSPEC, family):
            raise _error(FetchErrorCode.DNS_FAILED)
        if not _is_globally_reachable(address):
            raise _error(FetchErrorCode.PRIVATE_ADDRESS)
        item = (str(address), family)
        if item not in vetted:
            vetted.append(item)

    if not vetted:
        raise _error(FetchErrorCode.DNS_FAILED)
    address, family = vetted[0]
    return VettedDestination(hostname=validated.hostname, address=address, family=family)


async def close_response(response: TransportResponse) -> None:
    with anyio.CancelScope(shield=True):
        try:
            await response.aclose()
        except Exception:
            # Preserve the stable policy error that caused the cleanup rather
            # than exposing a transport-specific close failure.
            pass


def _header(response: TransportResponse, name: str) -> str | None:
    wanted = name.lower()
    for key, value in response.headers.items():
        if key.lower() == wanted:
            return value
    return None


def _header_values(headers: Mapping[str, str], name: str) -> list[str]:
    get_list = getattr(headers, "get_list", None)
    if callable(get_list):
        values = [str(value) for value in get_list(name)]
    else:
        values = [str(value) for key, value in headers.items() if key.lower() == name.lower()]
    return values


def _declared_content_length(headers: Mapping[str, str]) -> int | None:
    values: list[str] = []
    for raw_value in _header_values(headers, "content-length"):
        values.extend(raw_value.split(","))
    if not values:
        return None

    parsed: list[int] = []
    for value in values:
        normalized = value.strip()
        if not re.fullmatch(r"[0-9]+", normalized):
            raise RemoteFetchError(FetchErrorCode.RESPONSE_HEADERS_INVALID)
        try:
            parsed.append(int(normalized))
        except ValueError as error:
            raise RemoteFetchError(FetchErrorCode.RESPONSE_HEADERS_INVALID) from error
    if len(set(parsed)) != 1:
        raise RemoteFetchError(FetchErrorCode.RESPONSE_HEADERS_INVALID)
    return parsed[0]


def _validate_content_encodings(headers: Mapping[str, str]) -> None:
    encodings: list[str] = []
    for raw_value in _header_values(headers, "content-encoding"):
        encodings.extend(part.strip().lower() for part in raw_value.split(","))
    if any(not encoding or encoding not in _SUPPORTED_CONTENT_ENCODINGS for encoding in encodings):
        raise RemoteFetchError(FetchErrorCode.RESPONSE_HEADERS_INVALID)


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


async def _read_bounded_response(response: TransportResponse, max_bytes: int) -> BoundedFetchResponse:
    """Read decoded response bytes without ever retaining more than limit + 1."""

    try:
        status_code = response.status_code
        headers = response.headers
        if not 200 <= status_code < 300:
            raise RemoteFetchError(FetchErrorCode.UPSTREAM_STATUS)

        declared_length = _declared_content_length(headers)
        if declared_length is not None and declared_length > max_bytes:
            raise RemoteFetchError(FetchErrorCode.RESPONSE_TOO_LARGE)
        _validate_content_encodings(headers)

        chunk_size = min(_MAX_STREAM_CHUNK, max_bytes + 1)
        content: list[bytes] = []
        content_size = 0
        try:
            stream = response.aiter_bytes(chunk_size=chunk_size)
            async for chunk in stream:
                if not isinstance(chunk, bytes):
                    raise RemoteFetchError(FetchErrorCode.NETWORK_ERROR)
                remaining = max_bytes + 1 - content_size
                if len(chunk) >= remaining:
                    content.append(chunk[:remaining])
                    raise RemoteFetchError(FetchErrorCode.RESPONSE_TOO_LARGE)
                content.append(chunk)
                content_size += len(chunk)
        except RemoteFetchError:
            raise
        except (httpx.DecodingError, httpx.RemoteProtocolError) as error:
            raise RemoteFetchError(FetchErrorCode.RESPONSE_HEADERS_INVALID) from error
        except Exception as error:
            raise RemoteFetchError(FetchErrorCode.NETWORK_ERROR) from error

        return BoundedFetchResponse(
            content=b"".join(content),
            headers=_normalized_headers(headers),
            final_url=str(response.url),
        )
    finally:
        await close_response(response)


class _ScopedHTTPXResponse:
    """Keep the HTTPX client alive until the streaming response is closed."""

    def __init__(self, response: httpx.Response, client: httpx.AsyncClient) -> None:
        self._response = response
        self._client = client
        self._closed = False

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> httpx.Headers:
        return self._response.headers

    @property
    def url(self) -> httpx.URL:
        return self._response.url

    async def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        iterator = self._response.aiter_bytes(chunk_size=chunk_size)
        async for chunk in iterator:
            yield chunk

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._response.aclose()
        finally:
            await self._client.aclose()


class RemoteFetcher:
    """Deep fetch module behind the import URL and media fetch seam."""

    def __init__(
        self,
        *,
        resolver: Resolver = _system_resolver,
        transport: DestinationTransport | None = None,
        max_redirects: int = MAX_REDIRECTS,
        timeouts: FetchTimeouts = HTML_FETCH_TIMEOUTS,
        limits: httpx.Limits | None = None,
    ) -> None:
        if max_redirects < 0:
            raise ValueError("max_redirects must not be negative")
        self.resolver = resolver
        self.max_redirects = max_redirects
        self.timeouts = timeouts
        self.limits = limits or DEFAULT_HTTP_LIMITS
        if transport is not None:
            self.transport = transport
        else:
            async def default_transport(validated: ValidatedURL, destination: VettedDestination) -> TransportResponse:
                return await httpx_destination_request(
                    validated,
                    destination,
                    timeouts=self.timeouts,
                    limits=self.limits,
                )

            self.transport = default_transport

    async def fetch(self, raw_url: str) -> TransportResponse:
        current = validate_url(raw_url)
        visited = {current.value}
        redirect_count = 0

        while True:
            try:
                destination = await _vetted_destination(current, self.resolver)
            except RemoteFetchError as error:
                if redirect_count:
                    raise _error(FetchErrorCode.REDIRECT_BLOCKED, error) from error
                raise
            try:
                response = self.transport(current, destination)
                if isawaitable(response):
                    response = await response
            except RemoteFetchError:
                raise
            except (httpx.TimeoutException, TimeoutError) as error:
                raise _error(FetchErrorCode.TIMEOUT, error) from error
            except Exception as error:
                raise _error(FetchErrorCode.NETWORK_ERROR, error) from error

            if response.status_code not in _REDIRECT_STATUSES and not 300 <= response.status_code < 400:
                return response

            if response.status_code not in _REDIRECT_STATUSES:
                await close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED)
            location = _header(response, "location")
            if not location:
                await close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED)
            if redirect_count >= self.max_redirects:
                await close_response(response)
                raise _error(FetchErrorCode.REDIRECT_LIMIT)

            try:
                next_url = validate_url(urljoin(current.value, location))
            except Exception as error:
                await close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED, error) from error
            if next_url.value in visited:
                await close_response(response)
                raise _error(FetchErrorCode.REDIRECT_LIMIT)

            visited.add(next_url.value)
            redirect_count += 1
            await close_response(response)
            current = next_url

    async def fetch_bounded(self, raw_url: str, max_bytes: int) -> BoundedFetchResponse:
        """Fetch one response and enforce status, metadata, time, and byte limits."""

        if max_bytes < 0:
            raise ValueError("max_bytes must not be negative")
        try:
            with anyio.fail_after(self.timeouts.operation):
                response = await self.fetch(raw_url)
                return await _read_bounded_response(response, max_bytes)
        except RemoteFetchError:
            raise
        except TimeoutError as error:
            raise _error(FetchErrorCode.TIMEOUT, error) from error
        except httpx.TimeoutException as error:
            raise _error(FetchErrorCode.TIMEOUT, error) from error
        except Exception as error:
            raise _error(FetchErrorCode.NETWORK_ERROR, error) from error


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect to the vetted IP while httpcore keeps the hostname as SNI."""

    def __init__(self, destination: VettedDestination, delegate: httpcore.AsyncNetworkBackend | None = None):
        self.destination = destination
        self.delegate = delegate or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if host.rstrip(".").lower() != self.destination.hostname.rstrip(".").lower() or port != self.destination.port:
            raise httpcore.ConnectError("pinned destination mismatch")
        return await self.delegate.connect_tcp(
            self.destination.address,
            self.destination.port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("unix socket is not allowed")

    async def sleep(self, seconds: float) -> None:
        await self.delegate.sleep(seconds)


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTPX transport using a single pre-vetted TCP destination."""

    def __init__(
        self,
        destination: VettedDestination,
        *,
        network_backend: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpcore.default_ssl_context(),
            max_connections=1,
            max_keepalive_connections=0,
            keepalive_expiry=0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=_PinnedNetworkBackend(destination, delegate=network_backend),
        )


async def httpx_destination_request(
    validated: ValidatedURL,
    destination: VettedDestination,
    *,
    timeouts: FetchTimeouts = HTML_FETCH_TIMEOUTS,
    limits: httpx.Limits = DEFAULT_HTTP_LIMITS,
    network_backend: httpcore.AsyncNetworkBackend | None = None,
) -> TransportResponse:
    """Perform one GET without implicit DNS resolution or redirect following."""

    return await _httpx_destination_request_with_options(
        validated,
        destination,
        timeouts=timeouts,
        limits=limits,
        network_backend=network_backend,
    )


async def _httpx_destination_request_with_options(
    validated: ValidatedURL,
    destination: VettedDestination,
    *,
    timeouts: FetchTimeouts,
    limits: httpx.Limits,
    network_backend: httpcore.AsyncNetworkBackend | None,
) -> TransportResponse:
    client = httpx.AsyncClient(
        transport=PinnedAsyncHTTPTransport(destination, network_backend=network_backend),
        follow_redirects=False,
        trust_env=False,
        cookies={},
        timeout=timeouts.httpx_timeout(),
        limits=limits,
        headers={
            "accept": "application/activity+json,application/json,text/html,*/*",
            "user-agent": "Mozilla/5.0 recipe-importer",
        },
    )
    try:
        request = client.build_request("GET", validated.value)
        response = await client.send(request, stream=True)
    except BaseException:
        with anyio.CancelScope(shield=True):
            await client.aclose()
        raise
    return _ScopedHTTPXResponse(response, client)
