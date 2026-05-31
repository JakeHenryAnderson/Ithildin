from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from email.message import Message
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from ithildin_api.http_tools import (
    HTTP_FETCH_TOOL,
    HttpAllowlist,
    HttpFetchError,
    HttpFetchExecutor,
    parse_http_url,
)


class FakeResponse:
    def __init__(
        self,
        *,
        body: bytes,
        status_code: int = 200,
        content_type: str = "text/plain; charset=utf-8",
        content_length: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.body = body
        self.code = status_code
        self.headers = {"Content-Type": content_type, **(headers or {})}
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def getcode(self) -> int:
        return self.code


class RaisingReadResponse(FakeResponse):
    def __init__(self, exc: Exception) -> None:
        super().__init__(body=b"")
        self.exc = exc

    def read(self, size: int) -> bytes:
        raise self.exc


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


class PinnedFakeOpener(FakeOpener):
    def __init__(self, responses: list[object]) -> None:
        super().__init__(responses)
        self.pinned_calls: list[tuple[str, tuple[str, ...]]] = []

    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: Any,
        resolved_ips: Sequence[str],
        timeout: float = 0,
    ) -> object:
        self.pinned_calls.append((parsed_url.host, tuple(resolved_ips)))
        return self.open(fullurl, timeout=timeout)


def make_executor(
    *,
    allowlist: str = "https://example.com",
    responses: list[object] | None = None,
    resolved_ips: list[str] | None = None,
    resolver: Callable[[str, int], Sequence[str]] | None = None,
    max_response_bytes: int = 1024,
    max_redirects: int = 3,
) -> tuple[HttpFetchExecutor, PinnedFakeOpener]:
    opener = PinnedFakeOpener(responses or [FakeResponse(body=b"ok")])

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


def _http_corpus() -> dict[str, list[dict[str, Any]]]:
    corpus_path = Path(__file__).parent / "fixtures" / "http_canonicalization_corpus.json"
    return cast(
        dict[str, list[dict[str, Any]]],
        json.loads(corpus_path.read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize(
    "case",
    _http_corpus()["parse_cases"],
    ids=lambda case: str(case["id"]),
)
def test_http_url_canonicalization_corpus(case: dict[str, Any]) -> None:
    expected_error = case.get("error")
    if expected_error is not None:
        with pytest.raises(HttpFetchError, match=str(expected_error)):
            parse_http_url(str(case["url"]))
        return

    parsed = parse_http_url(str(case["url"]))
    allowlist = HttpAllowlist.from_csv(str(case["allowlist"]))

    assert parsed.normalized_url == case["normalized_url"]
    assert allowlist.allows(parsed) is case["allowed"]


@pytest.mark.parametrize(
    "case",
    _http_corpus()["fetch_denial_cases"],
    ids=lambda case: str(case["id"]),
)
def test_http_fetch_denial_corpus(case: dict[str, Any]) -> None:
    scenario = case["scenario"]
    responses: list[object] = [FakeResponse(body=b"ok")]
    resolver: Callable[[str, int], Sequence[str]]
    max_response_bytes = 1024

    if scenario == "blocked_resolution":
        resolved_ips = cast(list[str], case["resolved_ips"])

        def resolver(host: str, port: int) -> Sequence[str]:
            return resolved_ips

    elif scenario == "redirect_private":
        responses = [
            HTTPError(
                str(case["url"]),
                302,
                "Found",
                _headers(location="https://private.example/"),
                None,
            )
        ]

        def resolver(host: str, port: int) -> Sequence[str]:
            return ["127.0.0.1"] if host == "private.example" else ["93.184.216.34"]

    elif scenario == "dns_change":
        calls = 0

        def resolver(host: str, port: int) -> Sequence[str]:
            nonlocal calls
            calls += 1
            return ["93.184.216.34"] if calls == 1 else ["93.184.216.35"]

    elif scenario == "timeout":
        responses = [TimeoutError("private timeout detail")]

        def resolver(host: str, port: int) -> Sequence[str]:
            return ["93.184.216.34"]

    elif scenario == "size_limit":
        responses = [FakeResponse(body=b"too large")]

        def resolver(host: str, port: int) -> Sequence[str]:
            return ["93.184.216.34"]

        max_response_bytes = 4
    else:  # pragma: no cover - fixture validation guard
        raise AssertionError(f"unknown HTTP corpus scenario: {scenario}")

    executor, opener = make_executor(
        allowlist=str(case["allowlist"]),
        responses=responses,
        resolver=resolver,
        max_response_bytes=max_response_bytes,
    )

    with pytest.raises(HttpFetchError, match=str(case["error"])) as exc_info:
        executor.fetch(str(case["url"]))

    assert "private timeout detail" not in str(exc_info.value)
    if scenario in {"blocked_resolution", "dns_change"}:
        assert opener.requests == []


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


def test_pinned_opener_receives_validated_destination_ips() -> None:
    opener = PinnedFakeOpener([FakeResponse(body=b"ok")])
    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=0,
        resolver=lambda host, port: ["93.184.216.34", "93.184.216.35"],
        opener=opener,
    )

    result = executor.fetch("https://example.com/data")

    assert result["status_code"] == 200
    assert opener.pinned_calls == [
        ("example.com", ("93.184.216.34", "93.184.216.35"))
    ]


def test_unpinned_custom_opener_is_rejected_after_validation() -> None:
    opener = FakeOpener([FakeResponse(body=b"ok")])
    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=0,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=cast(Any, opener),
    )

    with pytest.raises(HttpFetchError, match="pinned destinations"):
        executor.fetch("https://example.com/")

    assert opener.requests == []


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


def test_invalid_port_is_denied_safely_without_opening_request() -> None:
    executor, opener = make_executor()

    with pytest.raises(HttpFetchError, match="port"):
        executor.fetch("https://example.com:99999/")

    assert opener.requests == []


@pytest.mark.parametrize("url", ["https://example.com:0/", "https://example.com:/"])
def test_zero_or_empty_explicit_ports_are_denied_without_opening_request(url: str) -> None:
    executor, opener = make_executor()

    with pytest.raises(HttpFetchError, match="port"):
        executor.fetch(url)

    assert opener.requests == []


@pytest.mark.parametrize("entry", ["https://example.com:0", "https://example.com:"])
def test_zero_or_empty_explicit_allowlist_ports_are_invalid(entry: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        HttpAllowlist.from_csv(entry)


@pytest.mark.parametrize("host", ["2130706433", "0177.0.0.1", "0x7f.0.0.1"])
def test_obfuscated_ipv4_url_hosts_are_rejected(host: str) -> None:
    executor, opener = make_executor()

    with pytest.raises(HttpFetchError, match="unsupported IP notation"):
        executor.fetch(f"https://{host}/")

    assert opener.requests == []


def test_scheme_mismatch_is_denied() -> None:
    executor, opener = make_executor(allowlist="https://example.com")

    with pytest.raises(HttpFetchError, match="allowlist"):
        executor.fetch("http://example.com/")

    assert opener.requests == []


def test_scheme_less_allowlist_host_defaults_to_https_only() -> None:
    executor, opener = make_executor(allowlist="example.com")

    result = executor.fetch("https://example.com/")

    assert result["status_code"] == 200
    with pytest.raises(HttpFetchError, match="allowlist"):
        executor.fetch("http://example.com/")
    assert len(opener.requests) == 1


def test_scheme_less_allowlist_default_ports_are_exact() -> None:
    https_executor, _ = make_executor(allowlist="example.com:443")
    http_executor, _ = make_executor(allowlist="example.com:80")

    assert https_executor.fetch("https://example.com/")["status_code"] == 200
    with pytest.raises(HttpFetchError, match="allowlist"):
        https_executor.fetch("http://example.com:443/")

    assert http_executor.fetch("http://example.com/")["status_code"] == 200
    with pytest.raises(HttpFetchError, match="allowlist"):
        http_executor.fetch("https://example.com:80/")


def test_scheme_less_allowlist_non_default_port_requires_scheme() -> None:
    with pytest.raises(ValueError, match="scheme is required"):
        HttpAllowlist.from_csv("example.com:8443")


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


def test_ipv4_mapped_ipv6_loopback_is_denied() -> None:
    executor, opener = make_executor(resolved_ips=["::ffff:127.0.0.1"])

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


def test_response_redirect_from_pinned_transport_is_revalidated() -> None:
    opener = PinnedFakeOpener(
        [
            FakeResponse(
                body=b"",
                status_code=302,
                headers={"Location": "https://private.example/"},
            )
        ]
    )

    def redirect_resolver(host: str, port: int) -> Sequence[str]:
        if host == "private.example":
            return ["127.0.0.1"]
        return ["93.184.216.34"]

    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com,https://private.example"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=redirect_resolver,
        opener=opener,
    )

    with pytest.raises(HttpFetchError, match="blocked IP"):
        executor.fetch("https://example.com/")

    assert len(opener.requests) == 1
    assert opener.pinned_calls == [("example.com", ("93.184.216.34",))]


def test_redirect_to_unallowlisted_destination_is_denied_before_second_request() -> None:
    redirect = HTTPError(
        "https://example.com/",
        302,
        "Found",
        _headers(location="https://other.example/"),
        None,
    )
    executor, opener = make_executor(responses=[redirect])

    with pytest.raises(HttpFetchError, match="allowlist"):
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


def test_body_read_errors_return_safe_error() -> None:
    executor, _ = make_executor(responses=[RaisingReadResponse(TimeoutError("secret read detail"))])

    with pytest.raises(HttpFetchError, match="HTTP fetch failed safely") as exc_info:
        executor.fetch("https://example.com/")

    assert "secret read detail" not in str(exc_info.value)


def test_unknown_response_charset_returns_safe_error() -> None:
    executor, _ = make_executor(
        responses=[
            FakeResponse(
                body=b"hello",
                content_type="text/plain; charset=secret_backend_charset",
            )
        ]
    )

    with pytest.raises(HttpFetchError, match="HTTP fetch failed safely") as exc_info:
        executor.fetch("https://example.com/")

    assert "secret_backend_charset" not in str(exc_info.value)


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


def test_default_opener_does_not_inherit_proxy_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]:
        monkeypatch.setenv(name, "http://127.0.0.1:9999")

    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=0,
        resolver=lambda host, port: ["93.184.216.34"],
    )

    opener = cast(Any, executor.opener)
    assert callable(getattr(opener, "open_pinned", None))
    assert not hasattr(opener, "handlers")


def test_trailing_dot_and_mixed_case_hosts_are_canonicalized() -> None:
    seen_hosts: list[str] = []

    def resolver(host: str, port: int) -> Sequence[str]:
        seen_hosts.append(host)
        return ["93.184.216.34"]

    executor, _ = make_executor(
        allowlist="HTTPS://EXAMPLE.COM.",
        resolver=resolver,
    )

    result = executor.fetch("https://EXAMPLE.COM./Path")

    assert result["url"] == "https://example.com/Path"
    assert seen_hosts == ["example.com", "example.com"]


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
