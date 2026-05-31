# Release Evidence Schema

Ithildin release evidence is a secret-free JSON snapshot for review handoff. It is
not notarization, custody, or proof that implementation bugs do not exist. It gives
reviewers a stable map of the local-preview boundary, gate status, review-document
hashes, configured trust evidence, and deferred product boundaries.

The current schema version is `v0.3-prep-release-evidence-v1`.

## Commands

Generate evidence:

```sh
make release-evidence
```

Validate a saved evidence file:

```sh
make release-evidence-validate FILE=release-evidence.json
```

Run the release-evidence schema gate used by `make release-check`:

```sh
make release-evidence-gate
```

Direct CLI form:

```sh
uv run python scripts/release_evidence.py --validate-file release-evidence.json
```

## Stable Top-Level Keys

The v0.3-prep schema requires these top-level keys:

- `schema`
- `generated_at`
- `repo`
- `git`
- `release_check`
- `review_docs`
- `manifest_lock`
- `docs_site`
- `tools`
- `policy`
- `principals`
- `workspaces`
- `filesystem`
- `storage`
- `telemetry`
- `security`
- `audit`
- `audit_signing`
- `deferred_boundaries`

Nested fields may still evolve during preview work, but the release-evidence
validator checks the schema version, stable key set, release-check transcript
metadata, git dirty state shape, tool count/name shape, review-document digests,
filesystem support/probe shape, and obvious secret-like markers.

Task 124 promotes this validation from an optional reviewer command into an
explicit release gate. `make release-evidence-gate` generates a temporary
snapshot, validates it with the same saved-file validator reviewers use, and is
included in `make release-check`.

## Release-Check Semantics

`make release-evidence` does not run the release gate by default. The evidence
distinguishes the gate command from an attached transcript:

- `gate_executed_by_release_packet`: whether this evidence command ran
  `make release-check`.
- `gate_status`: the result of that in-command gate, or `not_run`.
- `attached_transcript_exists`: whether a release-check transcript path was
  supplied and exists.
- `attached_transcript_status`: the observed transcript status.
- `attached_transcript_commit`: the commit associated with that transcript.
- `attached_transcript_path`: the local transcript path.

Review bundles should include a passing release-check transcript from the same
commit when presenting a handoff candidate.

## Secret-Free Boundary

Release evidence must not contain private keys, admin tokens, demo sample tokens,
password-like values, or secret-like environment fragments. This check is a
guardrail, not a complete secret scanner; generated review bundles still exclude
runtime databases, audit logs, `.env`, private keys, node modules, and build
outputs separately.
