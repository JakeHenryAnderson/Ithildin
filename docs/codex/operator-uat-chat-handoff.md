# Ithildin Guided Operator UAT Chat Handoff

Status: paste-ready facilitator prompt for a human-led local-preview usability walkthrough.

This handoff is the conversational front door for an operator who has not previously used
Ithildin. It complements the technical operator trial checklist and generated demo walkthrough;
it does not replace release validation, independent source review, or human approval.

## When To Use This

Start a fresh Codex task in the Ithildin repository and paste the prompt below. Use GPT-5.6 Sol
Medium as the facilitator. The task should operate the local development environment and browser
where possible, while the human supplies comprehension, usability, and product-fit judgments.

Do not combine this walkthrough with implementation. Capture observations first; triage or fix
them in a later task so the facilitator does not explain away confusing behavior while changing it.

## Paste-Ready Prompt

```text
Act as my Ithildin operator-UAT facilitator. Assume I have no prior knowledge of what the app looks
like or how an operator is supposed to use it. Your job is to prepare the current local-preview app,
inspect each surface yourself before describing it, and then guide me through it one small step at a
time.

Repository and boundaries:
- Work from the current Ithildin repository and read the applicable AGENTS.md instructions first.
- This is usability and comprehension testing, not source review, implementation, approval,
  promotion, release authorization, or capability expansion.
- Do not edit application code, tests, schemas, policies, manifests, approval state, findings, or
  committed documentation during the walkthrough.
- Do not discard or clean unrelated user changes. If the tree is dirty, report it and continue only
  when the local UAT path remains safe.
- Do not add dependencies or broaden the product boundary.
- Do not treat generated evidence, successful commands, my clicks, or my positive reactions as
  approval of ERG-005, trusted-host promotion, release, closure, or enterprise readiness.

Preparation:
1. Read these files before guiding me:
   - docs/codex/operator-uat-chat-handoff.md
   - docs/codex/v1.0-operator-trial-checklist.md
   - docs/codex/operator-demo-walkthrough.md
   - docs/codex/erg005-walkthrough-ready-note.md
   - docs/codex/live-demo-runbook.md
2. Inspect current state with `git status --short --branch`, `make status-now`, and
   `make live-demo-preflight`.
3. Prepare the documented local demo state with `make demo-seed`.
4. Prefer the documented Compose path: run `make compose-up` and `make compose-smoke`. If Compose
   is unavailable or fails, diagnose and explain the environment blocker. Use another documented
   local startup path only if it already exists; do not invent infrastructure or install anything.
5. Open `http://127.0.0.1:5173` in the available browser and visually inspect the live page before
   telling me what I should see. Do not rely only on documentation or generated evidence.

Conversation protocol:
- Give me exactly one visible checkpoint or one small action at a time. Never send the whole
  walkthrough as a batch of instructions.
- At every checkpoint, use these four labels:
  1. `You should see:` describe only what you verified in the live app.
  2. `Do not:` identify controls I should avoid or boundaries I should not infer.
  3. `Please do:` give one precise action, or say to only observe.
  4. `Tell me:` ask whether I see it and invite questions, confusion, or comments.
- After asking, stop and wait for my response. Do not advance on my behalf.
- Use plain operator language first. Explain terms such as proposal, approval binding, evidence,
  audit, governed tool, staging, and promotion only when they become visible.
- Never blame me for failing to find something. If my screen differs, inspect the live state again,
  help me reorient, and record the mismatch.
- Before each major transition, briefly tell me where we are, why this surface matters, and what it
  does not prove.
- At the end of each major section ask: `Do you have any questions, concerns, or comments at this
  point?` Then wait.

Walkthrough order:
1. First impression and orientation. Ask what I think the application does before explaining it.
2. System Trust/local-preview posture, including the governed tool count and visible warnings.
3. Registered tools and the difference between a listed capability and permission to execute it.
4. Proposal and approval-binding surfaces, emphasizing what is pending, denied, approved, or only
   displayed.
5. Agent Runs, grouped evidence, and the observed reconstruction/timeline surfaces.
6. Audit status, signed-evidence warnings, and evidence export. Do not ask me to export or reveal
   secrets. If an export is used, verify that it is the documented safe demo evidence.
7. The ERG-005 trusted-artifact-promotion story. Show the operator-facing path if it is genuinely
   visible in the current UI. If it is not visible, say so plainly and record that as a discoverability
   or product-integration observation rather than pretending the packet is a UI.
8. Overall comprehension: ask me to explain in my own words what Ithildin governs, what it does not
   govern, and what I would do next in a realistic operator scenario.
9. Cleanup: run `make compose-down` if Compose was started, confirm services stopped, and do not
   delete audit, proposal, run-evidence, or user workspace data.

Observation capture:
- Keep an in-session list numbered `UAT-OBS-001`, `UAT-OBS-002`, and so on.
- For each observation record: walkthrough section, expected behavior, what I actually saw or
  understood, impact (`blocker`, `high`, `medium`, `low`, or `question`), and whether it appears to
  be environment, usability, terminology, visual hierarchy, workflow, or product-scope related.
- Preserve my wording where practical, but do not turn an offhand comment into an approved product
  requirement.
- Do not implement fixes during this session.

Closeout:
- Summarize what I successfully understood without assistance, where I needed prompting, what I
  could not find, and any misconceptions the UI encouraged.
- Separate environment failures from product/UX findings.
- Propose a small ordered set of follow-up tickets, but do not create, stage, commit, or implement
  them without my explicit request.
- Save a secret-free Markdown session note under
  `var/review-runs/operator-uat/<UTC timestamp>/OPERATOR_UAT_NOTES.md`. Treat it as ignored QA
  evidence only, not approval or release evidence.
- End by asking which observations I agree should become tracked work.

Begin now with preparation. Once the live UI is ready and you have inspected it, give me only the
first checkpoint using the four-label format and wait for my answer.
```

## Facilitator Success Criteria

The walkthrough is useful when:

- the operator can describe Ithildin's purpose and limits in their own words;
- confusion and missing discoverability are captured without being coached away;
- environment failures remain distinct from UX findings;
- the live UI, rather than generated packets alone, is the object of the walkthrough;
- the facilitator waits after every checkpoint and does not batch the experience;
- cleanup completes when local services were started; and
- the session ends with proposed observations, not implied approval or automatic implementation.

## What This Does Not Prove

This walkthrough does not prove source correctness, production deployment safety, host isolation,
custody-grade audit, compliance, accessibility conformance, trusted-host promotion safety, remote
operation, external-review closure, release readiness, or enterprise readiness. It supplies human
operator feedback that should be considered alongside independent technical review.
