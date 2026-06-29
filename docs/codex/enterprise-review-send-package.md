# Enterprise Review Send Package

Status: generated operator package index for the current enterprise send set.

Current governed tool count: `24`.

Generate:

```sh
make enterprise-review-send-package
```

Validate:

```sh
make enterprise-review-send-package-check
```

The generated package index is written under:

```text
var/review-packets/v3/enterprise-review-send-package/
```

## Purpose

This package is a compact operator index over the current `ERG-003` and `ERG-002` send artifacts.
It points to the lane prompt, lane-local `ATTACHMENT_MANIFEST.md`, lane hash manifest, raw-response
placeholder, submission prompt, send receipt template, and response inbox. It does not copy or
replace the underlying review packets; those remain under the dual-review outbox.

The package exists to reduce operator send mistakes. It should be generated after:

```sh
make enterprise-review-send-refresh
```

or directly with:

```sh
make enterprise-review-send-package
```

For a local operator record scaffold after package generation, run:

```sh
make enterprise-review-send-session-record
```

That record ties the current package hashes, lane prompts, raw-response paths, and operator fill-in
fields together without recording review or closing lanes.

## Current Send Set

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/import planning review.

Each lane must be sent as a separate review request. Keep the lane-local attachment manifest and
hash manifest with the sent packet.

## Boundary

This package does not record external review, does not normalize responses, does not write response
files, does not mutate findings, does not close `ERG-003` or `ERG-002`, and does not approve
runtime behavior.

It does not approve Mission Control runtime behavior, live VM/container inspection, local model
invocation, sandbox orchestration, trusted-host promotion, SIEM adapters, compliance automation,
public/security-product positioning, new governed tool powers, production identity, runtime
Postgres, hosted telemetry, or remote MCP.
