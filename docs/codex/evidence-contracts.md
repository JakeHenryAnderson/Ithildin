# Evidence Contracts

This guide describes the local-preview evidence fields Ithildin expects operators and review tools
to read. These contracts are for local evidence review. They are not production identity,
not external notarization, and not tamper-proof custody.

## Audit Events

Audit events are stored in SQLite and exported as hash-chained JSONL. Every event includes:

- `event_id`, `timestamp`, `event_type`, and `request_id`;
- `principal`, `tool_name`, optional `resource`, optional `decision`, and `input_hash`;
- `policy_version`, `matched_rules`, and metadata when a policy decision is involved;
- `prev_event_hash` and `event_hash`.

Verification recomputes each event hash from stored payload JSON and checks that every
`prev_event_hash` links to the prior event hash. Empty logs are valid with the genesis hash.
Diagnostics explain failures but never repair or rewrite evidence.

## Policy Decision Evidence

Policy evaluation metadata is emitted in audit events and mirrored in successful policy previews.
The stable evidence fields are:

- `decision`, `reason`, `matched_rules`, and `obligation_keys`;
- `policy_engine`, `policy_hash`, `policy_version`, and `policy_document_version`;
- `tool_name`, `tool_version`, `tool_risk`, and `manifest_hash`;
- `resource_type` and `resource_in_scope`;
- `principal_id`, `principal_roles`, and `session_id`.

Policy preview remains read-only. It does not create approvals, write audit events, or execute tools.
Invalid previews and pre-policy denials may report `decision_evidence: null` because no policy
evaluation was performed.

## Approval Binding Evidence

Patch apply approvals bind to the stored proposal and current governance inputs. The review console
surfaces the important one-time scope fields:

- proposal ID/hash, target path, workspace ID, and base file hash;
- manifest hash/version and tool input schema hash;
- policy engine/hash/version/document version and matched rules;
- requesting principal, request hash, expiry, and approval scope hash.

Apply must consume an approved one-time scope and reject replay, stale base content, policy drift,
manifest drift, proposal mismatch, wrong tool, expired approval, or principal mismatch.

## Redaction Summaries

Redaction is best-effort leak reduction, not a security boundary. Execution audit metadata can
include:

- `redaction_applied`;
- `redaction_count`;
- `redaction_paths`.

The review console shows counts and safe JSON paths only. It must not expose original redacted
values. `/system/status` reports baseline redaction enablement and extra local redaction counts
without exposing the configured patterns or secrets.

## Signed Evidence

Signed audit exports and signed manifest locks use local Ed25519 keys when configured. Verification
requires a trusted local public key file; embedded public keys are evidence payload fields, not trust
roots.

- Signed audit export bundles bind export metadata, event JSONL digest, public key metadata, key ID,
  algorithm, and signature.
- Signed manifest lock bundles bind the canonical manifest lock digest, public key metadata, key ID,
  algorithm, and signature.

These signatures prove that a local key signed the bundle content. They do not provide hosted
notarization, external timestamping, custody-grade retention, or official supply-chain signing.

## Contract Versioning

Evidence contracts use explicit local-preview format versions where a bundle or API payload may be
consumed offline:

- audit JSONL export metadata uses `format_version: "1"`;
- signed audit export bundles use `format_version: "1"`;
- signed manifest lock bundles use `format_version: "1"`;
- manifest locks use `version: "1"`;
- review packet artifacts include schema-like metadata through release evidence and artifact hashes.

Stable v0.3-prep evidence fields are fields documented in this file and used by release-readiness
tests, policy fixtures, signed evidence verification, or review packet generation. Additive fields
may be introduced when they are secret-free and do not weaken an existing check. Renaming, removing,
or changing the meaning of a stable field requires a new format version or an explicit compatibility
note in the relevant review packet.

Preview-only evidence fields may appear in UI summaries, diagnostics, and review helper outputs.
They should remain secret-free, but downstream tools must not treat them as durable contract fields
unless they are promoted into this document and covered by tests.
