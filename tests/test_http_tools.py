from __future__ import annotations

from collections.abc import Callable, Sequence
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from ithildin_api.http_tools import (
    HTTP_FETCH_TOOL,
    HttpAllowlist,
    HttpFetchError,
    HttpFetchExecutor,
)


class FakeResponse:
    def __init__(
        self,
        *,
        body: bytes,
        status_code: int = 200,
        content_type: str = "text/plain; charset=utf-8",
        content_length: str | None = None,
    ) -> None:
        self.body = body
        self.code = status_code
        self.headers = {"Content-Type": content_type}
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def getcode(self) -> int:
        return self.code


class FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[Request] = []

    def open(self, fullurl: Request, timeout: float = 0) -> object:
        self.requests.append(fullurl)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_executor(
    *,
    allowlist: str = "https://example.com",
    responses: list[object] | None = None,
    resolved_ips: list[str] | None = None,
    resolver: Callable[[str, int], Sequence[str]] | None = None,
    max_response_bytes: int = 1024,
    max_redirects: int = 3,
) -> tuple[HttpFetchExecutor, FakeOpener]:
    opener = FakeOpener(responses or [FakeResponse(body=b"ok")])

    def default_resolver(host: str, port: int) -> Sequence[str]:
        return resolved_ips or ["93.184.216.34"]

    selected_resolver = resolver or default_resolver
    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv(allowlist),
        timeout_seconds=1,
        max_response_bytes=max_response_bytes,
        max_redirects=max_redirects,
        resolver=selected_resolver,
        opener=opener,
    )
    return executor, opener


def test_allowed_exact_host_fetch_returns_text_and_json() -> None:
    executor, opener = make_executor(
        responses=[
            FakeResponse(
                body=b'{"ok": true}',
                content_type="application/json; charset=utf-8",
            )
        ]
    )

    result = executor.execute(HTTP_FETCH_TOOL, {"url": "https://example.com/data"})

    assert result["status_code"] == 200
    assert result["url"] == "https://example.com/data"
    assert result["body_text"] == '{"ok": true}'
    assert result["body_json"] == {"ok": True}
    assert result["byte_count"] == 12
    assert opener.requests[0].headers["User-agent"] == "Ithildin/0.1 http.fetch"


def test_empty_allowlist_denies_without_opening_request() -> None:
    executor, opener = make_executor(allowlist="")

    with pytest.raises(HttpFetchError, match="allowlist"):
        executor.fetch("https://example.com/")

    assert opener.requests == []


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "https://user:pass@example.com/",
        "https://example.com/#fragment",
        "not-a-url",
    ],
)
def test_invalid_urls_are_denied(url: str) -> None:
    executor, opener = make_executor()

    with pytest.raises(HttpFetchError):
        executor.fetch(url)

    assert opener.requests == []


def test_scheme_mismatch_is_denied() -> None:
    executor, opener = make_executor(allowlist="https://example.com")

    with pytest.raises(HttpFetchError, match="allowlist"):
        executor.fetch("http://example.com/")

    assert opener.requests == []


def test_private_ip_resolution_is_denied() -> None:
    executor, opener = make_executor(resolved_ips=["127.0.0.1"])

    with pytest.raises(HttpFetchError, match="blocked IP"):
        executor.fetch("https://example.com/")

    assert opener.requests == []


@pytest.mark.parametrize(
    "resolved_ip",
    ["::1", "fc00::1", "fe80::1", "2001:db8::1", "169.254.169.254", "224.0.0.1"],
)
def test_blocked_ip_ranges_are_denied(resolved_ip: str) -> None:
    executor, opener = make_executor(resolved_ips=[resolved_ip])

    with pytest.raises(HttpFetchError, match="blocked IP"):
        executor.fetch("https://example.com/")

    assert opener.requests == []


def test_redirect_destination_is_revalidated() -> None:
    redirect = HTTPError(
        "https://example.com/",
        302,
        "Found",
        _headers(location="https://private.example/"),
        None,
    )

    def redirect_resolver(host: str, port: int) -> Sequence[str]:
        if host == "private.example":
            return ["127.0.0.1"]
        return ["93.184.216.34"]

    executor, opener = make_executor(
        allowlist="https://example.com,https://private.example",
        responses=[redirect],
        resolver=redirect_resolver,
    )

    with pytest.raises(HttpFetchError, match="blocked IP"):
        executor.fetch("https://example.com/")

    assert len(opener.requests) == 1


def test_dns_rebinding_style_resolution_change_is_denied() -> None:
    calls = 0

    def changing_resolver(host: str, port: int) -> Sequence[str]:
        nonlocal calls
        calls += 1
        return ["93.184.216.34"] if calls == 1 else ["93.184.216.35"]

    executor, opener = make_executor(resolver=changing_resolver)

    with pytest.raises(HttpFetchError, match="DNS resolution changed"):
        executor.fetch("https://example.com/")

    assert opener.requests == []


def test_redirect_limit_is_enforced() -> None:
    redirect = HTTPError(
        "https://example.com/",
        302,
        "Found",
        _headers(location="https://example.com/next"),
        None,
    )
    executor, _ = make_executor(responses=[redirect], max_redirects=0)

    with pytest.raises(HttpFetchError, match="redirect limit"):
        executor.fetch("https://example.com/")


def test_response_byte_limit_is_enforced() -> None:
    executor, _ = make_executor(
        responses=[FakeResponse(body=b"too large", content_length="9")],
        max_response_bytes=4,
    )

    with pytest.raises(HttpFetchError, match="byte limit"):
        executor.fetch("https://example.com/")


def test_response_byte_limit_is_enforced_without_content_length() -> None:
    executor, _ = make_executor(
        responses=[FakeResponse(body=b"too large")],
        max_response_bytes=4,
    )

    with pytest.raises(HttpFetchError, match="byte limit"):
        executor.fetch("https://example.com/")


def test_timeout_and_url_errors_return_safe_error() -> None:
    executor, _ = make_executor(responses=[URLError("secret backend detail")])

    with pytest.raises(HttpFetchError, match="HTTP fetch failed safely") as exc_info:
        executor.fetch("https://example.com/")

    assert "secret backend detail" not in str(exc_info.value)


def test_obfuscated_ipv4_hosts_are_rejected() -> None:
    with pytest.raises(HttpFetchError, match="unsupported IP notation"):
        HttpAllowlist.from_csv("2130706433")
    with pytest.raises(HttpFetchError, match="unsupported IP notation"):
        HttpAllowlist.from_csv("0177.0.0.1")


def test_idna_hosts_match_exact_punycode_allowlist() -> None:
    seen_hosts: list[str] = []

    def resolver(host: str, port: int) -> Sequence[str]:
        seen_hosts.append(host)
        return ["93.184.216.34"]

    executor, _ = make_executor(
        allowlist="https://xn--bcher-kva.example",
        resolver=resolver,
    )

    result = executor.fetch("https://bücher.example/path")

    assert result["url"] == "https://xn--bcher-kva.example/path"
    assert seen_hosts == ["xn--bcher-kva.example", "xn--bcher-kva.example"]


def test_extra_headers_are_rejected_by_manifest_schema(tmp_path: Path) -> None:
    from ithildin_api.registry import ToolRegistry

    tmp_path.joinpath("http-fetch.yaml").write_text(
        """
name: http.fetch
version: 1.0.0
title: Fetch
risk: network
category: network
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["url"]
  properties:
    url:
      type: string
""",
        encoding="utf-8",
    )
    manifest = ToolRegistry.load(tmp_path).get_tool("http.fetch").manifest

    assert manifest.input_schema["additionalProperties"] is False


def _headers(*, location: str) -> Message:
    headers = Message()
    headers["Location"] = location
    return headers
