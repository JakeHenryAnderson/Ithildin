# HTTP Fetch Source Review Checklist

Task 161 creates the source-review checklist for `http.fetch`, Ithildin's only governed network
tool. Use it with [source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[http-executor-contract.md](http-executor-contract.md).

## Files And Functions

Inspect:

- `apps/api/src/ithildin_api/http_tools.py`
  - `HttpFetchExecutor.fetch`
  - `HttpFetchExecutor._ensure_allowed_destination`
  - `HttpFetchExecutor._validated_resolution`
  - `HttpFetchExecutor._open_response`
  - `HttpFetchExecutor._result_from_response`
  - `parse_http_url`
  - `http_resource_from_url`
  - `_parse_allowlist_entry`
  - `_normalize_host`
  - `_looks_like_obfuscated_ip`
  - `_reject_url_control_or_space`
  - `_resolve_host`
  - `_is_blocked_ip`
  - `_read_bounded`
  - `_default_port`
  - `_netloc`
- `apps/api/src/ithildin_api/resources.py`
- `apps/api/src/ithildin_api/policy_preview.py`
- `apps/api/src/ithildin_api/tool_calls.py`
- `tests/fixtures/http_canonicalization_corpus.json`
- `tests/test_http_tools.py`

## Claims To Test

- `http.fetch` accepts only `url`; no caller-supplied method, headers, cookies, body, proxy config,
  or credential material.
- Only `http` and `https` schemes are accepted.
- Credentials, fragments, whitespace/control characters, malformed hosts, encoded/obfuscated IPs,
  and unsupported ports fail closed.
- Allowlist matching is exact across scheme, normalized host, and explicit/default port semantics.
- IDNA/punycode and trailing-dot behavior cannot bypass allowlist checks.
- DNS resolution is validated before opening a connection and pinned into the opener.
- Loopback, private, link-local, multicast, unspecified, reserved, IPv4-mapped IPv6, and other
  non-global destinations are blocked.
- Every redirect destination is re-parsed, allowlist-checked, resolved, and IP-validated.
- Proxy environment variables are not inherited by the default transport.
- Timeout, redirect limit, content length, and body-size failures return safe errors without leaking
  response bodies, stack traces, internal resolver details, or proxy details.
- Policy preview constructs network resources consistently with runtime governed calls.

## Evidence Commands

```sh
uv run pytest tests/test_http_tools.py tests/test_security_regressions.py
uv run pytest tests/test_governed_tool_calls.py tests/test_mcp_adapter.py
make release-check
```

## Finding Prompts

For every issue, record:

- the URL form, redirect, DNS behavior, or allowlist case being tested;
- whether the request could reach an unallowlisted or non-global destination;
- whether the issue affects preview/runtime parity or audit evidence;
- whether safe errors leak response body content, headers, DNS internals, stack traces, or secrets;
- whether the fix requires changing the exact-allowlist GET-only boundary.

## Non-Goals

This checklist does not authorize arbitrary methods, caller headers, request bodies, cookies,
browser automation, broad network access, proxy configuration, remote MCP, or network sandbox claims.
