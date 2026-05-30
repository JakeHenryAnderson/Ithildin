# HTTP Executor Contract

This contract documents the local-preview guarantees for `http.fetch`. The tool is network-read-only:
GET only, exact allowlist only, no caller-supplied headers, no request body, no cookies, no browser
automation, no proxy inheritance, and no broad network access.

## Supported Inputs

`http.fetch` accepts only:

- `url`: a string URL using `http` or `https`.

The manifest schema rejects additional caller-supplied fields such as headers, method, body, cookie,
proxy, or timeout overrides.

## Canonicalization Sequence

Before opening a request, the executor:

1. parses the URL;
2. rejects unsupported schemes, missing hosts, fragments, credentials, malformed ports, and
   obfuscated IP notation;
3. normalizes hostnames to lowercase ASCII IDNA/punycode form and strips a trailing dot;
4. normalizes default ports out of the URL representation;
5. checks the exact allowlist against the normalized scheme, host, and port;
6. resolves the destination twice and denies DNS changes during validation;
7. rejects loopback, private, link-local, multicast, reserved, unspecified, non-global, and
   IPv4-mapped blocked destinations;
8. opens a fixed GET request with Ithildin-controlled headers only.

Redirects repeat the same parse, allowlist, DNS, and IP validation before the next request. A
redirect to an unallowlisted or private destination fails before the redirected request is opened.

## Response Bounds

The executor enforces configured timeout, redirect count, declared `Content-Length`, and actual body
byte limits. Text and JSON bodies may be returned only after bounds are checked. Response headers are
not returned wholesale.

## Safe Errors

User-facing errors are intentionally generic. Timeout, URL opener, resolver, redirect, proxy, and
response-size failures must not echo response bodies, backend stack details, proxy details, or
secrets.

## Non-Goals

`http.fetch` is not a network sandbox and does not support arbitrary HTTP methods, request bodies,
custom headers, cookies, authentication, browser automation, arbitrary proxy use, URL path-prefix
allowlists, wildcards, or broad internet access.
