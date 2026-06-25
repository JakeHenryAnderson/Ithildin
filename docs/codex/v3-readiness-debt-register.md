# v3 Readiness Debt Register

Status: planning and hardening register. This register does not add runtime behavior.

The v3 direction is a local-first governed developer-tool gateway with a small family of bounded
read-only local metadata capabilities, stable review machinery, and no new powerful tool classes
without explicit review.

## Current Position

- Local-preview runtime boundary remains `v0.1 local-preview`.
- Tool count is `24`.
- `git.show.commit_metadata`, `git.show.ref_summary`, `git.show.tag_metadata`,
  `project.manifest.summary`, `project.dependency.summary`, `project.structure.summary`,
  `project.test.summary`, `project.docs.summary`, `project.language.summary`,
  `project.config.summary`, `project.ci.summary`, `project.release.summary`, and
  `project.risk.summary` are the approved bounded read-only metadata runtime capability additions.
- `make read-only-project-intelligence` records the consolidated thirteen-tool project intelligence
  slice.
- `make next-capability-readiness` records that no next implementation candidate is selected.
- `make project-risk-summary-implementation-gate` records the implemented limited read-only
  boundary.
- `make project-risk-summary-review-handoff-check` records the source-review handoff, and
  `make project-risk-summary-source-review-bundle` packages the implemented source-review
  packet.
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

The current thirteen-tool read-only project intelligence slice is consolidated. The most recent
candidate is `project.risk.summary`, recorded in
[v3 project.risk.summary Selection](v3-project-risk-summary-selection.md) and
[Capability Proposal: project.risk.summary](capability-proposals/project-risk-summary.md).
Its implementation-planning packet is
[Implementation-Planning Packet: project.risk.summary](capability-implementation-plans/project-risk-summary.md).
Its implementation decision is
[project.risk.summary Implementation](v3-project-risk-summary-implementation.md)
and `make project-risk-summary-implementation-gate` validates the approved limited read-only
boundary. Its fixture/test contract is
[project.risk.summary Fixture Plan](project-risk-summary-fixture-plan.md) and is checked with
`make project-risk-summary-preimplementation-check`. It has advanced through design-only selection,
planning, implementation, and review handoff. Its source-review handoff is
[v3 project.risk.summary Source Review Handoff](v3-project-risk-summary-source-review.md) and is
checked with `make project-risk-summary-review-handoff-check`. Its source-review bundle is generated
by `make project-risk-summary-source-review-bundle`.

No next selected candidate is recorded. Future read-only metadata work must start from a fresh
selection, proposal, implementation plan, explicit implementation decision, fixture/negative
transcript coverage, and source-review handoff. `project.risk.summary` is risk-signal count metadata
only, not vulnerability scanning, dependency analysis, compliance automation, security assurance,
scanner execution, registry/network access, shell execution, or a new governed power class.

Do not expand into new powerful tool classes until the blocked debt rows above are explicitly
dispositioned.
