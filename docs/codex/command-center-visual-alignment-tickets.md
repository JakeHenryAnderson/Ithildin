# Command Center Visual Alignment Tickets

Status: implemented visual-alignment ticket set; closure is established only by an exact-candidate
`make review-candidate` packet.

These tickets change presentation and information architecture only. They do not authorize schema,
API, policy, approval, audit, manifest, governed-tool, model-runtime, or sandbox-runtime changes.

## Implementation Disposition

| Ticket | Disposition | Evidence |
| --- | --- | --- |
| `CC-VIS-201` | implemented | `f7ec3c5` persistent purpose-led shell and responsive navigation |
| `CC-VIS-202` | implemented | `f7ec3c5` shared purpose headers and visual grammar, extended by later slices |
| `CC-VIS-203` | implemented | `4ae2185` deterministic Attention collection/detail workspace |
| `CC-VIS-204` | implemented | `3fc2184` mission list, Workbench context, lifecycle/evidence hierarchy, and authority copy |
| `CC-VIS-205` | implemented | `8223105` approval queue/detail and artifact lifecycle alignment |
| `CC-VIS-206` | implemented | `3635064` evidence limitations and progressive Administration disclosure |
| `CC-VIS-207` | implemented; exact-candidate gate required | live desktop/390px browser checks, UI accessibility/behavior suite, and `make review-candidate` |

## CC-VIS-201 — Application Shell And Navigation

Implement the persistent Command Center rail, compact product/status header, and responsive shell.

Acceptance criteria:

- all six primary destinations include icon, title, and purpose subtitle;
- Help remains available but secondary;
- navigation targets existing semantic sections and transfers keyboard focus correctly;
- local-preview/authentication state is runtime-backed and does not claim model or sandbox control;
- narrow layouts collapse to a usable horizontal/stacked navigation without horizontal page
  overflow; and
- existing skip-link, focus-visible, and reduced-motion behavior remains covered.

## CC-VIS-202 — Shared Collection/Detail Grammar

Create reusable presentation primitives for page purpose, prioritized collection, selected story,
context facts, bounded action, lifecycle, and technical disclosure.

Acceptance criteria:

- primitives consume existing view data and do not create new authority state;
- observed facts and operator actions are visibly distinct;
- empty, loading, unavailable, expired, invalid-binding, denied, failed, and completed states do not
  collapse into the same visual treatment; and
- technical fields remain reachable without dominating routine operation.

## CC-VIS-203 — Attention Workspace

Align Attention with the exception-queue/detail reference.

Acceptance criteria:

- the highest-priority deterministic record is selected without invented risk scoring;
- consequence, identity, workspace, tool, policy reason, timing, and next action are visible;
- overview never offers a blind approve action;
- opening the source focuses the exact related record; and
- no-record copy remains local-record scoped rather than a global safety claim.

## CC-VIS-204 — Mission Workbench

Align Agent Runs with the mission-detail reference and governed lifecycle.

Acceptance criteria:

- run list and selected mission remain visually connected;
- requesting identity is labeled as reported context and workspace as operator-managed;
- the lifecycle separates request observation, policy result, operator decision, execution/artifact,
  review/promotion, and evidence closeout according to evidence actually present;
- Ithildin does not claim to launch the agent or verify sandbox isolation; and
- evidence export retains its current bounded, warning-rich semantics.

## CC-VIS-205 — Artifacts And Approvals

Apply the shared collection/detail grammar to proposals, artifacts, and pending approvals.

Acceptance criteria:

- proposed, approved, applied, ready for review, promoted, and released remain distinct;
- approval actions are adjacent to valid binding evidence and disabled for invalid bindings;
- artifact destination and movement claims reflect existing evidence only; and
- stale, expired, and recovery states have clear consequences and next steps.

## CC-VIS-206 — Evidence And Administration

Apply the template to technical evidence and specialist policy/trust controls.

Acceptance criteria:

- routine operators see evidence posture and limitations before raw records;
- audit-chain status does not imply immutable custody or host-compromise resistance;
- registered tools are clearly distinct from effective request permission;
- policy preview and impact remain specialist tools connected to selected Workbench context where
  available; and
- presentation lenses remain explicitly non-authoritative.

## CC-VIS-207 — Visual, Responsive, And Accessibility Closure

Validate the integrated result against the saved references and real browser behavior.

Acceptance criteria:

- desktop and narrow-width screenshots are captured from the live seeded application;
- keyboard traversal, focus transfer, landmarks, headings, labels, status semantics, contrast, and
  reduced motion are checked;
- focused UI tests, typecheck, lint, workflow guardrails, and proportional authoritative gates pass;
- governed tool count remains 24; and
- any difference from the generated reference is documented as a data, accessibility, authority,
  or responsive correction rather than silently treated as a miss.

## Sequence

Implement `CC-VIS-201` first, then `202`. Complete `203` and `204` before `205` and `206`. Run
`207` after each meaningful slice and as the final integrated closure. One implementation owner
keeps the shared shell and primitives coherent.
