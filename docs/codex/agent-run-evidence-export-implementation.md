# Agent Run Evidence Export Implementation

Status: approved bounded read-only implementation. Ithildin now exposes an admin-only
`GET /runs/{run_id}/evidence-export` endpoint for one secret-free Agent Run evidence bundle.

This implementation does not add MCP tools, governed tool manifests, executors, policy rules, SIEM
adapters, sandbox controls, run-control behavior, production identity, runtime Postgres, hosted
telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes,
or plugin SDK work.

## Endpoint

- `GET /runs/{run_id}/evidence-export`
- Admin bearer token required.
- `run_id` must use Ithildin's generated `run_` identifier shape.
- Unknown query parameters are rejected.
- `timeline_limit` is the only accepted query parameter.

## Bundle Shape

The response includes:

- `schema_version`;
- `export_id`;
- `exported_at`;
- `run`;
- `timeline`;
- `approvals`;
- `patch_diagnostics`;
- `signed_export_references`;
- `evidence_hashes`;
- `redaction_summary`;
- `warnings`.

The endpoint uses existing Agent Run records, correlated audit timeline events, approval records,
and patch apply diagnostics. Missing correlations are represented as warnings rather than
fabricated evidence.

## Secret-Free Boundary

The export excludes prompts, model output, model reasoning, raw tool arguments, file contents,
diffs, response bodies, secrets, bearer tokens, cookies, package script values, dependency names,
raw sensitive paths, private key material, local environment files, runtime SQLite database content,
and raw audit JSONL payloads.

Path-like values are omitted or represented as hashes where useful for local review. The endpoint
does not return raw audit `resource` objects.

## Non-Claims

This endpoint supports incident reconstruction for Ithildin-mediated actions only. It is not
sandboxing, SIEM custody, external notarization, immutable evidence, compliance automation,
production security, or a view into activity outside Ithildin.

## Validation

Run:

```sh
make agent-run-evidence-export-implementation-gate
```

The gate validates endpoint wiring, tests, documentation, and no-new-powers posture.
