# Local v1 LV1-003 O4 Enrollment-Output Projection Repair Exact Review

Status: `GO`

Date: 2026-07-25

## Rejected Candidate Lineage

The first reviewed candidate was commit
`dd96e47adba2baf49b890d821098e326bad93f84`, tree
`9e57f240ac65ffad38a66387648836bd1afdc489`. Independent read-only review
recorded one Medium finding (`M1`). That candidate left subprocess output in
Python text mode, which could normalize line endings before the closed
enrollment projection parser and could raise an unclassified decoding error for
invalid UTF-8. The rejected candidate is not authorized for execution.

## Final Exact Candidate

- Commit: `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685`
- Tree: `4dacc4015a51d61b29dc3e089900b2e12ab1d7b6`
- Parent commit: `6fcea4cad23c051abfbf09227948328975ccf724`
- `apps/node/src/ithildin_node/__main__.py`:
  `sha256:b7b3e9988f9351b25f24cf000f424bce1390cbb6be3010c41dce767987ac358d`
- `docs/codex/local-v1-lv1-003-o4-producer-contract.md`:
  `sha256:e972cf112ca0bc659f889cc50d2902d9d68137724e3f4d508bcc8e149d4af18b`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:cd5be3b081afda05a93ef29013a8d67bbac683d0f4118b77111939396c490bd4`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:299fe6d8c5dbf1de2ebcdef1f745223d460b649312ad693a34bf7133a82c59d7`
- `tests/test_node_cli.py`:
  `sha256:8446ca4b6328d395cb93018ff765961a1ba81b9a5e2e7f5b690f712306abd100`

The final candidate changes exactly those five paths.

## Final Review Result

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-commit disposition is `GO`. The final candidate resolves the rejected
candidate's `M1`; that finding remains durable review lineage and is not
retroactively cleared on the rejected commit.

## Reviewed Trust Contract

The Node enrollment command emits a closed canonical projection containing exactly
three string fields: `node_id`, `principal_id`, and `workspace_id`. The principal
is derived from the server-assigned Node identity: `principal_id` must equal
`agent:node.{node_id}`. It does not emit the previous `private_key_present` field
or any private key, enrollment code, token, credential, prompt, provider output,
or arbitrary runtime state. The producer accepts only that exact canonical
projection with one LF terminator and continues to reject forbidden output,
extra fields, wrong types, a principal that is not derived from `node_id`, CRLF,
oversized output, invalid UTF-8, and any nonzero subprocess result.

The final candidate captures subprocess input and output as bytes, performs
strict UTF-8 encoding and decoding, and maps encoding or decoding failure to
closed producer error codes without reflecting rejected bytes. Existing
diagnostic, image-probe, cleanup, recovery, retention, and evidence semantics
remain closed. The repair does not revoke or reconcile the ambiguous Attempt 008
enrollment, delete evidence, claim cleanup or Docker-resource absence, add a
governed tool or power, or broaden arbitrary host, shell, process, filesystem,
network, provider, or Docker-socket product authority.

## Evidence Limits

The repair tests and exact-candidate review are evidence only. They do not prove
that the retained Attempt 008 enrollment was absent or revoked, that its
containers, volumes, networks, images, runtime material, or credentials are
absent, or that a future attempt will succeed. They do not execute a producer,
inspect retained runtime material, grant release or UAT authority, or authorize
automatic retry, cleanup, reconciliation, credential custody, or evidence
deletion.

## Authority

This review permits preparation of a separate exact Attempt 009 one-shot
execution authorization only. Attempt 009 must be a new isolated attempt with a
producer-generated fresh run ID, Compose project, suffix, runtime root, receipt
root, and evidence path. It is not a retry, cleanup, revocation, or
reconciliation of Attempt 008. The preflight must fail closed before live work
when required ports or runtime prerequisites are unavailable.

This review does not execute Attempt 009, authorize automatic retry, reopen
Attempts 001 through 008 or the consumed Attempt 003 image recovery, authorize
evidence deletion, grant arbitrary host control or a new governed tool or
power, or authorize release, promotion, production, credential custody, or UAT.
