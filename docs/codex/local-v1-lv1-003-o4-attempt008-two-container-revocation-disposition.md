# Attempt 008 Exact Two-Container Revocation Disposition

Status: **COMPLETED**

Recovery `LV1-003-O4-ATTEMPT-008-TWO-CONTAINER-REVOCATION-001` completed from exact reviewed
candidate `7b24e50fc9bc663a906f8d17e3f8b57be1bb7744`, tree
`8397d87962e870c546e1fff68658b3d9ae994175`. Fixed tag
`ithildin/lv1-003-o4-attempt008-two-container-revocation-reviewed` resolves to that commit and
tree. Independent Sol xhigh review returned `GO` with zero Critical, High, Medium, or Low findings.

The standalone command ran once in a sanitized environment with offline, frozen dependency
resolution:

```sh
make local-v1-lv1-003-o4-attempt008-two-container-revocation-run
```

It returned zero and printed only:

```text
attempt008_two_container_revocation_status: completed
```

The exact Compose-project query observed only the public-disposition-bound API and UI container
identities. Both retained their reviewed images, were exited, and had empty port maps before,
during, and after the bounded storage transition. No Docker mutation or container stop occurred.
Node and Hermes remain described only as
`not_observed_in_exact_project_query_at_preinspection`, with their historical classification
`not_targeted_by_prior_recovery`. This is not a generic absence, process-absence, or host-wide
storage-exclusivity claim.

The descriptor-bound transition changed the privately reconciled Node from `enrolled/complete` to
`revoked/pending`, appended the one deterministic existing-semantics `node.revoked` audit event,
and then marked the Node `revoked/complete` after a clean SQLite/JSONL audit lifecycle. The
terminal disposition records `node_status=revoked` and `node_evidence_status=complete`. The
database and audit aliases remain retained; no cleanup or evidence deletion occurred.

The private receipt root is
`var/local-v1-lv1-003-o4-reconciliation-receipts/attempt-008-two-container-revocation-001`.
It is owner-only `0700`; consumption, all eleven journal leaves, and `disposition.json` are `0600`.
The retained hard-link aliases are non-writable by group or other. Exact sizes and SHA-256 digests
for every bound leaf and both aliases are recorded in the paired JSON disposition. No raw Node ID
was printed or copied into this tracked disposition.

The operation is terminal. Attempt budget and retry authority are zero, same-operation resume is
closed, and the reviewed tag must not move. Cleanup, successor O4 execution, release, and UAT
remain false. The governed tool count remains exactly 24.
