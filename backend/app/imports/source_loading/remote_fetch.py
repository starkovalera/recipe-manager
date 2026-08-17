"""Secure remote URL validation and vetted-destination fetching.

This module owns the P11 Child A seam.  It validates every URL and redirect,
resolves every hostname before connecting, and pins the TCP connection to a
validated address while retaining the hostname for HTTP Host and TLS SNI.

The remaining residual assumption is that the selected direct transport and
the execution environment do not perform an unvalidated second lookup or
redirect the socket through a transparent proxy.  Production egress controls
remain required; this module makes that assumption explicit and testable.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
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
class VettedDestination:
    """A globally reachable address approved for one connection attempt."""

    hostname: str
    address: str
    family: int
    port: int = 443


class TransportResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    url: httpx.URL

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


async def _close_response(response: TransportResponse) -> None:
    try:
        await response.aclose()
    except Exception:
        # Preserve the stable policy error that caused the cleanup rather than
        # exposing a transport-specific close failure.
        pass


def _header(response: TransportResponse, name: str) -> str | None:
    wanted = name.lower()
    for key, value in response.headers.items():
        if key.lower() == wanted:
            return value
    return None


class RemoteFetcher:
    """Deep fetch module behind the import URL and media fetch seam."""

    def __init__(
        self,
        *,
        resolver: Resolver = _system_resolver,
        transport: DestinationTransport | None = None,
        max_redirects: int = MAX_REDIRECTS,
    ) -> None:
        if max_redirects < 0:
            raise ValueError("max_redirects must not be negative")
        self.resolver = resolver
        self.transport = transport or httpx_destination_request
        self.max_redirects = max_redirects

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
            except Exception as error:
                raise _error(FetchErrorCode.NETWORK_ERROR, error) from error

            if response.status_code not in _REDIRECT_STATUSES and not 300 <= response.status_code < 400:
                return response

            if response.status_code not in _REDIRECT_STATUSES:
                await _close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED)
            location = _header(response, "location")
            if not location:
                await _close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED)
            if redirect_count >= self.max_redirects:
                await _close_response(response)
                raise _error(FetchErrorCode.REDIRECT_LIMIT)

            try:
                next_url = validate_url(urljoin(current.value, location))
            except Exception as error:
                await _close_response(response)
                raise _error(FetchErrorCode.REDIRECT_BLOCKED, error) from error
            if next_url.value in visited:
                await _close_response(response)
                raise _error(FetchErrorCode.REDIRECT_LIMIT)

            visited.add(next_url.value)
            redirect_count += 1
            await _close_response(response)
            current = next_url


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


async def httpx_destination_request(validated: ValidatedURL, destination: VettedDestination) -> TransportResponse:
    """Perform one GET without allowing HTTPX to resolve or redirect implicitly."""

    async with httpx.AsyncClient(
        transport=PinnedAsyncHTTPTransport(destination),
        follow_redirects=False,
        trust_env=False,
        cookies={},
        timeout=httpx.Timeout(10.0),
        headers={
            "accept": "application/activity+json,application/json,text/html,*/*",
            "user-agent": "Mozilla/5.0 recipe-importer",
        },
    ) as client:
        return await client.get(validated.value)
