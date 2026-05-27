"""Safe allowlisted HTTP fetch tool."""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from ithildin_schemas import JsonObject, JsonValue

HTTP_FETCH_TOOL = "http.fetch"
DEFAULT_HTTP_USER_AGENT = "Ithildin/0.1 http.fetch"
TEXTUAL_CONTENT_TYPES = (
    "application/json",
    "application/javascript",
    "application/xml",
    "application/x-yaml",
    "text/",
)


class HttpFetchError(RuntimeError):
    """Raised when an HTTP fetch must fail without leaking remote content."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ParsedHttpUrl:
    raw_url: str
    normalized_url: str
    scheme: str
    host: str
    port: int


@dataclass(frozen=True)
class HttpAllowlistEntry:
    scheme: str | None
    host: str
    port: int | None

    def matches(self, parsed_url: ParsedHttpUrl) -> bool:
        if self.scheme is not None and self.scheme != parsed_url.scheme:
            return False
        if self.host != parsed_url.host:
            return False
        if self.port is None:
            return parsed_url.port == _default_port(parsed_url.scheme)
        return self.port == parsed_url.port


@dataclass(frozen=True)
class HttpAllowlist:
    entries: tuple[HttpAllowlistEntry, ...]

    @classmethod
    def from_csv(cls, value: str) -> HttpAllowlist:
        return cls(
            tuple(
                _parse_allowlist_entry(raw_entry)
                for raw_entry in value.split(",")
                if raw_entry.strip()
            )
        )

    def allows(self, parsed_url: ParsedHttpUrl) -> bool:
        return any(entry.matches(parsed_url) for entry in self.entries)


class HttpOpener(Protocol):
    def open(self, fullurl: Request, timeout: float = ...) -> Any:
        """Open a request and return a response-like object."""


Resolver = Callable[[str, int], Sequence[str]]


class HttpHeaders(Protocol):
    def get(self, name: str, default: str | None = None) -> str | None:
        """Return one header value."""


class HttpResponse(Protocol):
    headers: HttpHeaders
    code: int | None

    def read(self, size: int) -> bytes:
        """Read response bytes."""

    def getcode(self) -> int | None:
        """Return the HTTP status code."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


class HttpFetchExecutor:
    def __init__(
        self,
        *,
        allowlist: HttpAllowlist,
        timeout_seconds: float,
        max_response_bytes: int,
        max_redirects: int,
        resolver: Resolver | None = None,
        opener: HttpOpener | None = None,
    ) -> None:
        self.allowlist = allowlist
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.resolver = resolver or _resolve_host
        self.opener = opener or build_opener(ProxyHandler({}), _NoRedirectHandler)

    @classmethod
    def from_settings(
        cls,
        *,
        http_allowlist: str,
        timeout_seconds: float,
        max_response_bytes: int,
        max_redirects: int,
    ) -> HttpFetchExecutor:
        return cls(
            allowlist=HttpAllowlist.from_csv(http_allowlist),
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
            max_redirects=max_redirects,
        )

    def supports(self, tool_name: str) -> bool:
        return tool_name == HTTP_FETCH_TOOL

    def execute(self, tool_name: str, arguments: JsonObject) -> JsonObject:
        if tool_name != HTTP_FETCH_TOOL:
            raise HttpFetchError("unsupported HTTP tool")
        url = _string_arg(arguments, "url")
        return self.fetch(url)

    def fetch(self, url: str) -> JsonObject:
        current = parse_http_url(url)
        redirect_chain: list[JsonValue] = []

        for _ in range(self.max_redirects + 1):
            self._ensure_allowed_destination(current)
            request = Request(
                current.normalized_url,
                headers={
                    "Accept": (
                        "text/plain, application/json, application/xml, "
                        "text/*;q=0.9, */*;q=0.1"
                    ),
                    "User-Agent": DEFAULT_HTTP_USER_AGENT,
                },
                method="GET",
            )
            try:
                response = cast(
                    HttpResponse,
                    self.opener.open(request, timeout=self.timeout_seconds),
                )
            except HTTPError as exc:
                if _is_redirect(exc.code):
                    location = exc.headers.get("Location")
                    if not location:
                        raise HttpFetchError("redirect response is missing a location") from exc
                    next_url = parse_http_url(urljoin(current.normalized_url, location))
                    redirect_chain.append(
                        {
                            "from": current.normalized_url,
                            "to": next_url.normalized_url,
                            "status_code": exc.code,
                        }
                    )
                    if len(redirect_chain) > self.max_redirects:
                        raise HttpFetchError("redirect limit exceeded") from exc
                    current = next_url
                    continue
                return self._result_from_response(cast(HttpResponse, exc), current, redirect_chain)
            except (TimeoutError, OSError, URLError) as exc:
                raise HttpFetchError("HTTP fetch failed safely") from exc

            return self._result_from_response(response, current, redirect_chain)

        raise HttpFetchError("redirect limit exceeded")

    def _ensure_allowed_destination(self, parsed_url: ParsedHttpUrl) -> None:
        if not self.allowlist.allows(parsed_url):
            raise HttpFetchError("URL is not in the HTTP allowlist")

        first_resolution = self._validated_resolution(parsed_url)
        second_resolution = self._validated_resolution(parsed_url)
        if first_resolution != second_resolution:
            raise HttpFetchError("destination DNS resolution changed during validation")

    def _validated_resolution(self, parsed_url: ParsedHttpUrl) -> frozenset[str]:
        resolved_ips = self.resolver(parsed_url.host, parsed_url.port)
        if not resolved_ips:
            raise HttpFetchError("destination host could not be resolved")

        validated: set[str] = set()
        for resolved_ip in resolved_ips:
            ip_address = ipaddress.ip_address(resolved_ip)
            if _is_blocked_ip(ip_address):
                raise HttpFetchError("destination resolves to a blocked IP range")
            validated.add(ip_address.compressed)
        return frozenset(validated)

    def _result_from_response(
        self,
        response: HttpResponse,
        parsed_url: ParsedHttpUrl,
        redirect_chain: list[JsonValue],
    ) -> JsonObject:
        headers = response.headers
        content_length = headers.get("Content-Length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError as exc:
                raise HttpFetchError("response content length was invalid") from exc
            if declared_length > self.max_response_bytes:
                raise HttpFetchError("response exceeds configured byte limit")

        body = _read_bounded(response, self.max_response_bytes)
        content_type = headers.get("Content-Type") or ""
        result: JsonObject = {
            "url": parsed_url.normalized_url,
            "status_code": response.code or _call_no_arg(response, "getcode"),
            "content_type": content_type,
            "byte_count": len(body),
            "redirect_chain": redirect_chain,
            "truncated": False,
        }
        if _is_textual_content_type(content_type):
            body_text = body.decode(_charset_from_content_type(content_type), errors="replace")
            result["body_text"] = body_text
            if "json" in content_type.lower():
                try:
                    result["body_json"] = json.loads(body_text)
                except json.JSONDecodeError:
                    pass
        return result


def parse_http_url(url: str) -> ParsedHttpUrl:
    if not url:
        raise HttpFetchError("url must not be empty")
    try:
        split = urlsplit(url)
    except ValueError as exc:
        raise HttpFetchError("url is malformed") from exc
    if split.scheme not in {"http", "https"}:
        raise HttpFetchError("only http and https URLs are supported")
    if split.username or split.password:
        raise HttpFetchError("URL credentials are not allowed")
    if split.fragment:
        raise HttpFetchError("URL fragments are not allowed")
    if not split.hostname:
        raise HttpFetchError("URL host is required")

    host = _normalize_host(split.hostname)
    port = split.port or _default_port(split.scheme)
    normalized = SplitResult(
        scheme=split.scheme,
        netloc=_netloc(host, port, split.scheme),
        path=split.path or "/",
        query=split.query,
        fragment="",
    )
    return ParsedHttpUrl(
        raw_url=url,
        normalized_url=urlunsplit(normalized),
        scheme=split.scheme,
        host=host,
        port=port,
    )


def http_resource_from_url(url: str, allowlist: HttpAllowlist) -> JsonObject:
    try:
        parsed_url = parse_http_url(url)
    except HttpFetchError as exc:
        return {
            "type": "network",
            "in_scope": False,
            "risk": "network",
            "url": url,
            "reason": exc.reason,
        }
    return {
        "type": "network",
        "in_scope": allowlist.allows(parsed_url),
        "risk": "network",
        "url": parsed_url.normalized_url,
        "scheme": parsed_url.scheme,
        "host": parsed_url.host,
    }


def _parse_allowlist_entry(raw_entry: str) -> HttpAllowlistEntry:
    entry = raw_entry.strip()
    if "://" in entry:
        split = urlsplit(entry)
        if split.scheme not in {"http", "https"} or not split.hostname:
            raise ValueError(f"invalid HTTP allowlist entry: {raw_entry}")
        if split.username or split.password or split.query or split.fragment:
            raise ValueError(f"invalid HTTP allowlist entry: {raw_entry}")
        if split.path not in {"", "/"}:
            raise ValueError(f"invalid HTTP allowlist entry: {raw_entry}")
        return HttpAllowlistEntry(
            scheme=split.scheme,
            host=_normalize_host(split.hostname),
            port=split.port or _default_port(split.scheme),
        )

    if "/" in entry or "?" in entry or "#" in entry:
        raise ValueError(f"invalid HTTP allowlist entry: {raw_entry}")

    host = entry
    port: int | None = None
    if entry.count(":") == 1:
        maybe_host, maybe_port = entry.rsplit(":", 1)
        if maybe_port.isdigit():
            host = maybe_host
            port = int(maybe_port)
    return HttpAllowlistEntry(scheme=None, host=_normalize_host(host), port=port)


def _normalize_host(host: str) -> str:
    stripped = host.rstrip(".").lower()
    if not stripped:
        raise HttpFetchError("host must not be empty")
    if _looks_like_obfuscated_ip(stripped):
        raise HttpFetchError("host uses unsupported IP notation")
    try:
        return ipaddress.ip_address(stripped).compressed
    except ValueError:
        return stripped.encode("idna").decode("ascii")


def _looks_like_obfuscated_ip(host: str) -> bool:
    if host.startswith("0x") or host.isdecimal():
        return True
    parts = host.split(".")
    if 1 < len(parts) <= 4 and all(part for part in parts):
        numericish = all(
            part.isdecimal() or part.startswith("0x") or (part.startswith("0") and len(part) > 1)
            for part in parts
        )
        if numericish:
            try:
                ipaddress.ip_address(host)
                return False
            except ValueError:
                return True
    return False


def _resolve_host(host: str, port: int) -> Sequence[str]:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise HttpFetchError("destination host could not be resolved") from exc
    resolved: set[str] = set()
    for address in addresses:
        host_address = address[4][0]
        if isinstance(host_address, str):
            resolved.add(host_address)
    return tuple(resolved)


def _is_blocked_ip(ip_address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        not ip_address.is_global
        or ip_address.is_loopback
        or ip_address.is_private
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_reserved
        or ip_address.is_unspecified
    )


def _read_bounded(response: HttpResponse, max_response_bytes: int) -> bytes:
    body = _call_read(response, max_response_bytes + 1)
    if len(body) > max_response_bytes:
        raise HttpFetchError("response exceeds configured byte limit")
    return body


def _call_read(response: HttpResponse, size: int) -> bytes:
    body = response.read(size)
    if not isinstance(body, bytes):
        raise HttpFetchError("HTTP response body was not bytes")
    return body


def _call_no_arg(response: HttpResponse, method_name: str) -> int:
    if method_name != "getcode":
        raise HttpFetchError("HTTP response status was invalid")
    value = response.getcode()
    if value is None:
        raise HttpFetchError("HTTP response status was invalid")
    return value


def _string_arg(arguments: JsonObject, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str):
        raise HttpFetchError(f"{name} must be a string")
    return value


def _default_port(scheme: str) -> int:
    if scheme == "https":
        return 443
    return 80


def _netloc(host: str, port: int, scheme: str) -> str:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    default_port = _default_port(scheme)
    if port == default_port:
        return host
    return f"{host}:{port}"


def _is_redirect(status_code: int) -> bool:
    return status_code in {301, 302, 303, 307, 308}


def _is_textual_content_type(content_type: str) -> bool:
    lowered = content_type.lower()
    return any(lowered.startswith(item) or item in lowered for item in TEXTUAL_CONTENT_TYPES)


def _charset_from_content_type(content_type: str) -> str:
    for part in content_type.split(";"):
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset" and value:
            return value
    return "utf-8"
