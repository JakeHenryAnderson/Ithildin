# CC-PILOT-107 Fresh-Operator UAT Handoff

Status: blocked pending exact-candidate validation and independent closure review.

The independent Sol Ultra pre-UAT review found four high-severity blockers and six medium findings.
This packet must not be used until those findings are closed, the integrated candidate is bound to
a reproducible commit, the required gates pass, and an independent closure review records that the
candidate is ready to enter UAT.

This packet is a human gate. It does not authorize release, enterprise-readiness claims, Gateway
capability expansion, approval, promotion, or trusted-host/runtime operation.

## Entry Gate

Before recruiting or briefing a participant, record:

- the candidate commit, clean working-tree result, and governed tool count;
- closure of every high finding and disposition of every medium finding from the independent
  pre-UAT review;
- passing focused tests plus `make agent-workflow-check`, `make release-check`, and
  `make review-candidate` for that exact candidate; and
- the independent Sol Ultra closure-review disposition.

If any entry item is absent or contradictory, stop. Do not begin or rehearse the UAT.

## Required Participant And Facilitator Rules

- Use an operator who did not implement or review `CC-PILOT-101` through `106`, did not participate
  in the first UAT, and has not read the Command Center design artifacts.
- Provide only the task card below and normal product-visible help.
- Do not explain Ithildin vocabulary, page purpose, topology, or next steps during the timed task.
- The facilitator may resolve only an environment failure that prevents the visible product from
  loading. Record the intervention and restart the timed task if it could have taught the workflow.
- Record direct observations separately from facilitator interpretation.

## Environment Preflight

- Confirm the browser is visible to the operator before timing starts.
- Confirm the URL is reachable and the intended seeded scenario exists.
- Confirm the credential path is available through the documented operator experience.
- Confirm local-preview and signing warnings match actual runtime state.
- Record commit, clean/dirty state, tool count, browser, viewport, zoom, demo seeding, and the
  participant role/background in non-identifying terms.
- Do not coach around a broken environment; label environment failures separately.

## Uncoached Task Card

> Open Ithildin. Find what needs your attention for the Hello World mission. Determine what the
> agent requested, what Ithildin decided and why, review the artifact when it is ready, and show the
> evidence you would hand to a technical reviewer. Stop when you believe the task is complete.

Do not provide the participant with a second checklist or the expected product distinctions.

## Pass Gate

The UAT passes only if the operator:

- completes all six scenario stages without workflow or vocabulary coaching;
- completes the task in 12 minutes or less, excluding recorded environment recovery;
- makes no unsafe or authority-confused action;
- answers at least 7 of 8 comprehension questions correctly;
- rates confidence in the next action at least 4 on a 5-point scale;
- does not need raw YAML, manifests, hashes, or audit rows for routine completion;
- can still locate technical evidence when asked; and
- validates or refutes each inferred finding `UAT-OBS-063` through `UAT-OBS-070` with a new direct
  observation.

The six required stages are: identify Attention, reconstruct the governed request and decision,
review the proposal/approval lifecycle, distinguish application from operator review/promotion,
produce the bounded evidence closeout, and locate the technical evidence requested by the
facilitator.

## Comprehension Questions

1. What was the mission trying to produce?
2. Which identity and workspace made the request?
3. What did Ithildin decide?
4. Why did the request need approval?
5. Did Command Center execute the tool?
6. What does `ready for review` mean here?
7. What does the audit-integrity status establish?
8. What does the evidence not prove?

## Required Observation Record

Record participant posture, candidate commit, clean/dirty state, tool count, environment, start/end
time, each stage outcome, wrong turns, terms misunderstood, direct participant language for
comprehension failures, errors, interventions, all eight answers, confidence score, technical-
evidence retrieval, and the disposition of every `UAT-OBS-063` through `UAT-OBS-070`. Do not record
secrets or sensitive local data. Link secret-free screenshots or evidence where available.

Label the record as human QA evidence only. It is not approval, promotion, source review, release
evidence, independent security review, or authorization for scope expansion.

## Blocking Failures

Fail the UAT rather than coach through it if the operator cannot locate the next action, cannot
explain the policy consequence, confuses proposal with approval, mistakes readiness for promotion,
or cannot distinguish Command Center from Gateway authority. The following also block acceptance:

- any critical/high trust-boundary or sensitive-data exposure issue;
- treating a registered tool as automatically permitted;
- treating proposed, approved, applied, reviewed, promoted, and released as interchangeable;
- treating local audit verification as immutable custody or host-compromise resistance;
- believing presentation lenses grant roles or permissions; or
- failure to complete any pass-gate threshold above.

## Disposition

Record one: `accepted_for_bounded_pilot`, `changes_required`, or `blocked`.
`accepted_for_bounded_pilot` is permitted only when every pass-gate item is satisfied and every
`UAT-OBS-063` through `UAT-OBS-070` has a direct disposition. Acceptance applies only to the
local-preview Command Center pilot. It does not make Ithildin production-ready, enterprise-ready,
compliance-certified, independently audited, or authorized for a new Gateway capability.

Stop the implementation lane if completing the scenario requires new governed powers, mission
orchestration, schema/API expansion, broader artifact promotion, production identity, cloud or SIEM
behavior, sandbox control, or regulated/security claims.
