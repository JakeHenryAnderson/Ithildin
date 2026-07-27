# Local v1 LV1-006 Operations Disposition

Status: `O1_O7_LV1_006_COMPLETE_NO_RELEASE_OR_UAT_AUTHORITY`

Exact evidence candidate `0c9fd49c2124b0d642bf07fbfa4a1aaa769dc950`, tree
`cfc4e2998e0928df419f46ed293382521c5bd32d`, passed the isolated Local-v1
operations rehearsal and its separately invoked candidate-bound checker. This closes the bounded
fresh-install and local-operations requirements in `O1`, `O7`, and `LV1-006`.

## Operator-visible result

The documented path now exercises one supported local topology from a clean exact candidate:

1. derive an immutable source tree from the recorded Git candidate;
2. initialize synthetic isolated Gateway state and configured workspaces;
3. start Gateway and Command Center on loopback-only ports and verify health plus the authenticated
   24-tool surface;
4. stop cleanly and create a private stopped backup;
5. attempt one fixed update that must fail specifically with the reviewed API exit and unavailable
   health endpoint;
6. restore into fresh directories, restart, verify health and byte-exact manifests, and verify
   owner-only restored state; and
7. remove the exact Compose project and candidate-specific images.

The optional Node and model provider are not part of this topology. Ambiguous Node state still
requires the separate revoke or re-enroll procedure.

## Evidence and review posture

The sole passing report is mode `0600`, 1,920 bytes, and bound by digest
`sha256:06e295d8243d041f17c9afbc98cd42765b35f587423f9718168102d654584d8e`.
No raw run identity is recorded here. The checker found no retained private runtime artifacts and
does not search for a latest run.

One independent Sol-high reviewer was reused across the bounded review lineage; no xhigh reviewer
was used. The initial candidate received `NO_GO` with five Medium and one Low finding. The first
repair closed those findings but left one descriptor-confinement Medium. Exact candidate
`0c9fd49c2124b0d642bf07fbfa4a1aaa769dc950` anchors every evidence-path traversal to a trusted
repository descriptor and reads the report plus sibling inventory from the same open run-directory
descriptor. Its adversarial rename/replacement regression passed, and final review returned `GO`
with zero Critical, High, Medium, or Low findings.

Eleven focused tests, Ruff, and strict mypy passed before the live run. The closure checks recorded
below bind the contract, tool-surface, no-new-powers, and workflow status to the disposition commit.

## Closure and limits

This evidence uses synthetic isolated state. It does not prove production durability, credential
custody, disaster recovery for every topology, every future upgrade failure, optional-Node
recovery, or host isolation. The fixed operator rehearsal may invoke the Docker CLI for its exact
Compose project and exact candidate-specific images; Ithildin itself receives no Docker socket,
generic container authority, or arbitrary host control.

This disposition closes only `O1`, `O7`, and `LV1-006`. It grants no new API or governed power and
keeps the governed tool count at 24. Release, promotion, production, external-system, and UAT
authority remain false. The ordered next milestone is `LV1-007`.
