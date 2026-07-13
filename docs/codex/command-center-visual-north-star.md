# Command Center Visual North Star

Status: selected design reference and implementation contract.

The selected reference is
[`command-center-template.png`](../reference-images/command-center-north-star/selected/command-center-template.png).
It is a presentation target, not evidence that the pictured runtime powers or states exist.

## Selection

Three image-generated concepts were compared against five criteria.

| Candidate | Operator comprehension | Enterprise credibility | Accessibility potential | Buildability | Authority honesty | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 01 Attention dashboard | Strong immediate next action; weaker multi-item triage | Strong | Strong | Strong | Needs tighter workspace/isolation wording | Retain as Attention-card reference |
| 02 Mission workbench | Best single-mission explanation and lifecycle | Strong | Strong if density is reduced responsively | Medium | Best explicit isolation caveat | Retain as Workbench-detail reference |
| 03 Exception queue + detail | Best scalable collection/detail pattern across all menus | Strongest | Strongest keyboard and hierarchy potential | Strongest reuse across current data | Strong with explicit reported/operator-managed labels | **Selected** |

Candidate 03 is the global template because it turns every primary destination into the same
predictable operator grammar: prioritized collection, selected operational story, bounded next
action, lifecycle/context, and progressively disclosed technical evidence. Candidate 02 remains a
secondary reference for the Missions detail surface. Generated references are design inputs; the
implemented product must use runtime-backed states and the terminology contract.

## Reusable Menu Template

Every primary destination follows this order:

1. **Purpose header** — what the area answers, current local-preview posture, and honest authority
   boundary.
2. **Prioritized collection** — actionable or recently relevant records, ordered without invented
   risk scoring.
3. **Selected story** — plain-language consequence, requesting identity, workspace, governed
   capability, and current state.
4. **Bounded next action** — review before mutation; no blind approval or implied execution.
5. **Lifecycle or context** — observed Gateway facts remain distinct from operator actions.
6. **Supporting evidence** — artifacts, evidence, and technical identifiers use progressive
   disclosure.

## Menu Purposes

| Destination | Operator question | Primary collection | Selected story | Supporting detail |
| --- | --- | --- | --- | --- |
| Attention | What needs a decision now? | approvals, failures, recovery, proposals | consequence and next action | source record and timing |
| Missions | What happened in this agent run? | governed runs | mission objective and reconstructed lifecycle | correlated evidence and export |
| Artifacts | What was produced and where can it move? | proposals and governed artifacts | content/change review and lifecycle | binding, destination, hashes |
| Approvals | What bounded action am I authorizing? | pending approvals | exact one-time scope and validity | policy reason and binding evidence |
| Evidence | What can I reconstruct and hand off? | run and audit evidence | closeout posture and limitations | technical records and export |
| Administration | How are policy and local trust configured? | posture, tools, policy utilities | present state and consequence | specialist controls and raw detail |

## Visual Contract

- Persistent dark navigation uses icons, destination names, and plain-language purpose subtitles.
- Content uses a dark, restrained enterprise palette with teal reserved for verified/observed state,
  amber for operator attention, and red for actual denial/failure.
- The primary path must remain understandable without YAML, manifests, hashes, or raw audit rows.
- Responsive layouts collapse collection/detail panes without hiding the selected record or its
  next action.
- Visible focus, semantic headings, landmarks, skip navigation, and reduced-motion behavior remain
  required.

## Authority Contract

- Command Center presents and reviews governed records; Gateway mediates, authorizes, executes,
  and records according to the implemented boundary.
- Identity is reported/request context unless stronger runtime evidence says otherwise.
- Workspaces are operator-managed. Ithildin does not claim to create or attest OS isolation.
- A registered tool is not automatically permitted.
- Ready for review is not promoted, released, or trusted-host accepted.
- Local audit verification is tamper-evident local evidence, not immutable custody.
- Presentation lenses do not grant roles, permissions, or Gateway authority.

## Source References

- `candidates/01-attention-dashboard.png` — exception-first summary treatment.
- `candidates/02-mission-workbench.png` — mission lifecycle and context treatment.
- `candidates/03-exception-queue-detail.png` — selected global template.

