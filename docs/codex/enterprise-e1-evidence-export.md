# Enterprise E1 Operational Evidence Export

Status: `E1-M5` bounded export contract. This export composes already-available operational
observations. It does not collect new host activity, deliver to an external receiver, or become an
authorization input.

## Bundle

An operator prepares one input JSON document using schema
`ithildin.enterprise-e1-operations-input.v1`. It binds an exact candidate commit, a non-secret site
label, a caller-supplied UTC observation time, the fixed 24-tool count, and exactly seven JSON
objects:

1. deployment identity;
2. configuration versioning;
3. recovery and upgrade/rollback observations;
4. mission state;
5. fleet posture;
6. approvals; and
7. audit evidence.

The exporter recursively applies the existing Ithildin secret-pattern redactor plus a closed set
of receiver-neutral local-metadata keys. It writes canonical section JSON, a redaction/exclusion
manifest, a plain-language README, and a SHA-256 file manifest. It then creates a lexicographically
ordered, uncompressed ZIP with fixed member timestamps and modes. The directory and ZIP contain
no receiver name, delivery address, custody state, or host-specific archive metadata.

The input is an export-ready snapshot supplied by the operator or an existing authenticated
Gateway export path. This tool does not query the Gateway, inspect a host, read a database, request
credentials, or discover evidence outside its explicit input.

## Build and verify

```sh
uv run python scripts/enterprise_e1_operations_bundle.py build \
  --input /absolute/path/to/e1-operations-input.json \
  --output-dir /absolute/path/to/new/e1-operations-bundle

uv run python scripts/enterprise_e1_operations_bundle.py verify \
  --bundle /absolute/path/to/e1-operations-bundle

uv run python scripts/enterprise_e1_operations_bundle.py verify \
  --bundle /absolute/path/to/e1-operations-bundle.zip
```

Build fails closed if the input schema, commit, UTC time, site label, tool count, section set, or
section object shape is invalid; if either output target already exists; or if redaction scanning
finds forbidden runtime material. Verification rejects missing, extra, renamed, non-UTF-8, unsafe,
or digest-mismatched members. An archive SHA-256 receipt is written beside the ZIP.

The manifest proves only local content consistency relative to the manifest being checked. Because
the manifest and receipt can be replaced together, they are not origin authentication, a local
signature, external notarization, hosted custody, or non-repudiation. Existing signed audit
exports may be represented as bounded observations inside the audit section, but their independent
verification contract is not broadened by this wrapper.

## Nonclaims

The bundle does not claim SIEM custody, hosted telemetry, external notarization, whole-host
coverage, compliance automation, production identity, enterprise production readiness, or human
UAT completion. It contains no model chain of thought or provider-internal state. Activity outside
Ithildin remains outside the export.

## Validation

```sh
make enterprise-e1-evidence-check
```

The focused gate checks the machine contract, deterministic archive behavior, recursive redaction,
offline directory/archive verification, failure cases, the fixed 24-tool boundary, and static
source bindings. Tests and generated bundles remain evidence only.
