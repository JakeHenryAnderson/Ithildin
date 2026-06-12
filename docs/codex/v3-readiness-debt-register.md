# v3 Readiness Debt Register

Status: planning and hardening register. This register does not add runtime behavior.

The v3 direction is a local-first governed developer-tool gateway with a small family of bounded
read-only local metadata capabilities, stable review machinery, and no new powerful tool classes
without explicit review.

## Current Position

- Local-preview runtime boundary remains `v0.1 local-preview`.
- Tool count is `14`.
- `git.show.commit_metadata`, `git.show.ref_summary`, `project.manifest.summary`, and
  `project.dependency.summary` are the approved bounded read-only metadata runtime capability
  additions.
- `make read-only-project-intelligence` records the consolidated four-tool project intelligence
  slice.
- `make next-capability-readiness` records that the next candidate is
  `project.structure.summary`, design-only selected, and any further implementation remains blocked
  until a fresh implementation plan, source-review handoff, and explicit decision are recorded.
- Public/security-product positioning remains blocked.
- Broader capability expansion remains blocked.

## Debt That Blocks Public/Security-Product Positioning

| ID | Area | Status | Revisit Criteria |
| --- | --- | --- | --- |
| `V3-DEBT-001` | Production identity | accepted deferred | Real identity/OIDC/SAML/RBAC plan and source review. |
| `V3-DEBT-002` | Durable audit custody | accepted deferred | External anchoring, custody model, or signed release-evidence trust-root decision. |
| `V3-DEBT-003` | Runtime storage | accepted deferred | Postgres/runtime storage implementation and migration semantics reviewed. |
| `V3-DEBT-004` | Hosted/remote MCP | accepted deferred | Remote transport auth, CSRF/CORS/session model, and deployment review. |

## Debt That Blocks New Powerful Tool Classes

| ID | Area | Status | Revisit Criteria |
| --- | --- | --- | --- |
| `V3-DEBT-005` | Shell/Docker/Kubernetes/browser powers | blocked | Product-risk decision plus external/human security review. |
| `V3-DEBT-006` | Arbitrary HTTP | blocked | New network threat model, SSRF review, method/header/body policy, and external review. |
| `V3-DEBT-007` | Broad filesystem writes | blocked | Workspace write model, rollback/recovery model, approval semantics, and external review. |
| `V3-DEBT-008` | Plugin SDK/marketplace | blocked | Manifest signing, executor contract stability, review process, and trust-root decision. |

## Debt That Should Be Paid Before More Read-Only Metadata Tools

| ID | Area | Status | Revisit Criteria |
| --- | --- | --- | --- |
| `V3-DEBT-009` | Shared metadata privacy policy | addressed | [Metadata Privacy Policy](metadata-privacy-policy.md) is now the default contract. |
| `V3-DEBT-010` | Reusable read-only capability checklist | addressed | [Read-Only Metadata Capability Checklist](read-only-metadata-capability-checklist.md) is now the planning gate. |
| `V3-DEBT-011` | Source-review bundle consistency | addressed | [Read-Only Capability Source Review Template](read-only-capability-source-review-template.md) defines the preferred handoff shape. |
| `V3-DEBT-012` | Capability family contract | addressed | [Read-Only Local Metadata Capability Contract](read-only-local-metadata-contract.md) defines the capability floor. |

## Current Recommendation

The current four-tool read-only project intelligence slice is consolidated. The next design-only
candidate is `project.structure.summary`, recorded in
[v3 project.structure.summary Selection](v3-project-structure-summary-selection.md) and
[Capability Proposal: project.structure.summary](capability-proposals/project-structure-summary.md).
Its implementation-planning packet is
[Implementation-Planning Packet: project.structure.summary](capability-implementation-plans/project-structure-summary.md).
Implementation remains blocked until it first passes `make next-capability-readiness`, the shared
contract, privacy policy, checklist, implementation gate, source-review packet, internal review,
and release checks.

Do not expand into new powerful tool classes until the blocked debt rows above are explicitly
dispositioned.
