# Command Center Terminology and Operator-State Contract

Status: design contract for operator-facing language and presentation states. It does not rename
runtime fields, change schemas, add stored states, or alter policy, approval, execution, artifact,
audit, signing, or export semantics.

## Contract Rules

1. Use a plain-language label and consequence first.
2. Preserve the exact machine identifier in technical detail, logs, search, exports, and APIs.
3. Never use a capability class such as `read`, `write`, or `network` as if it were severity.
4. Never infer effective permission from tool registration.
5. Never collapse proposal, approval, application, artifact, review, and evidence states.
6. Presentation-derived summaries must be deterministic and traceable to authoritative records.
7. If a backend state has no honest plain-language mapping, show `Unknown` or `Unavailable` with a
   safe explanation; do not invent success.
8. Do not use color alone. Pair every visual treatment with a label and consequence.
9. `Trusted`, `secure`, `verified`, `signed`, `complete`, and `ready` must always name the object and
   scope to which the word applies.

## Attention and Consequence Vocabulary

| Operator label | Meaning | Consequence |
| --- | --- | --- |
| Action required | A current authoritative record allows or requires an operator decision. | The mission or artifact cannot advance through that reviewed step until action or expiry. |
| Review ready | Sufficient safe evidence exists for the named review task. | A human may inspect it; nothing is implied about approval, application, promotion, or release. |
| Blocked | An existing denial, failed-closed state, missing prerequisite, or unavailable dependency prevents the next step. | Show the exact blocked step and safe recovery or escalation path. |
| Warning | A limitation affects interpretation or handoff but does not necessarily block the current task. | Show what is affected and whether action is optional or required. |
| No action needed | The current recorded state requires no operator decision. | Provide outcome and optional evidence; do not imply global safety. |
| Unknown | Ithildin cannot substantiate the summary from current authoritative records. | Do not offer a success action; direct the user to diagnostics or technical detail. |

## System Trust

`System Trust` should be presented as **Local system posture** unless a future reviewed definition
establishes a broader trust claim.

| Current or machine term | Operator-facing label | Plain-language meaning | Technical detail retained |
| --- | --- | --- | --- |
| `Policy Hash` | Policy version fingerprint | Identifies the exact policy content used for decisions; it does not say the policy is good or approved. | Full hash, algorithm, source/version metadata. |
| `Audit Head` | Audit log integrity checkpoint | Identifies the latest verified point in the local audit hash chain. | Full event/hash, verification time, chain diagnostics. |
| `Principals 7/7 required` | Configured identities ready: 7 of 7 | All identities required by this local configuration were loaded. It does not mean production identity or enterprise RBAC is present. | Principal IDs, source configuration, validation diagnostics. |
| `Filesystem: macOS` | Host compatibility profile: macOS | The current local compatibility profile is for macOS. Implementation must verify the source field before using this label. | Original field/value and compatibility diagnostics. |
| `Patch Limit` | Maximum proposed change size | The bounded size limit applied to a patch proposal; it is not an operating-system or application update. | Exact units, configured value, enforcement source. |
| manifest fingerprint | Tool definition fingerprint | Identifies the reviewed tool definition used for this request. | Full manifest hash, tool version, lock entry. |
| authentication missing | Sign-in required | The admin session is not authenticated, independent of local-preview restrictions. | Safe auth error and retry guidance; never credentials. |
| local preview | Local-preview limitation | The current environment is for local evaluation and does not establish production readiness. | Profile name and applicable warnings. |

Do not show a single green `System Trust` state that implies the whole system is safe. Summarize each
posture dimension separately and lead with exceptions affecting the current task.

## Tools, Permission, and Risk

Use a human-facing capability name first, followed by the machine name in technical detail or a
secondary label.

| Machine name example | Human-facing name | Capability class | Permission statement |
| --- | --- | --- | --- |
| `fs.list` | List workspace items | Read | Registered; effective permission depends on identity, workspace, request, and policy. |
| `fs.patch.propose` | Propose workspace changes | Propose change | Creates a proposal under existing rules; it does not apply the change. |
| `sandbox.artifact.write_text` | Create a sandbox artifact | Write artifact | Requires the recorded policy/approval path for the exact request. |
| `http.fetch` | Fetch an approved web resource | Network read | Registration does not mean every destination is reachable or permitted. |

Show these dimensions separately:

| Dimension | Examples | Question answered |
| --- | --- | --- |
| Capability class | Read, propose change, write artifact, network read | What kind of effect can this tool have? |
| Effective availability | Available, approval required, denied, unavailable, unknown | Can this identity make this request in this context? |
| Decision | Allowed, denied, approval required | What did policy decide for this request? |
| Attention severity | Action required, blocked, warning, informational | How urgently does the operator need to respond? |
| Operational consequence | No change, request held, action applied, action failed | What happened or will happen next? |

Never color a network capability green merely because it is registered or read-only. Never label a
write as inherently `high risk` without naming the policy outcome and operational consequence.

## Identities and Workspaces

| Machine term | Operator-facing label | Meaning |
| --- | --- | --- |
| principal | Requesting identity | The configured identity under which Ithildin evaluates the request. |
| `principal_id` | Identity ID | Stable machine identifier used in policy, audit, API, and search. |
| principal type | Identity type | The configured class of the requesting identity; not proof of a human or production account. |
| workspace | Governed workspace | The configured resource boundary associated with the mediated request. |
| `workspace_id` such as `default` | Workspace ID | Stable machine label; it must never appear as an unlabeled value. |
| session | Agent/client session | Correlation label supplied or derived by the current run model; not proof that Ithildin controls the process. |
| Agent Run | Mediated run record | Diagnostic grouping of Ithildin-mediated calls; not an orchestrated job. |

When a human-facing name is unavailable, show a type label plus the short machine ID, for example
`Requesting identity: agent:mcp-local`. Do not fabricate organization, owner, or person names.

## Request Decision Language

Rename the generic primary-dashboard `Policy Preview` concept to **Request decision preflight** when
it is shown in context. Its explanation is:

> Test how the current policy would evaluate this proposed tool request. This does not execute the
> tool, create an approval, or change policy.

Rename `Policy Impact` to **Candidate policy impact** for the specialist administration route. Its
explanation is:

> Compare a candidate policy with the current policy against reviewed test cases. This does not
> apply the candidate policy or authorize implementation.

Inputs should be labeled `Tool request`, `Request details`, `Requesting identity`, and `Workspace`.
Raw tool names, arguments, and YAML remain available to policy administrators and reviewers.

## Proposal, Approval, Application, Artifact, and Evidence Lifecycle

The operator-facing lifecycle is a linked set of records, not one status bar:

```text
request observed
  -> change or artifact proposed
  -> approval not required | approval requested
  -> approved | denied | expired | superseded
  -> application not started | executing | executed | failed
  -> artifact unavailable | ready for review
  -> review recorded, if an existing authoritative state supports it
  -> evidence available | export created | locally signed
```

Each step must identify its authoritative record. Missing steps remain `Not available` rather than
being inferred as successful.

| Machine/current term | Operator-facing label | Meaning and next action |
| --- | --- | --- |
| patch proposal / artifact proposal | Proposed change / Proposed artifact action | A bounded change has been described. It is not approved or applied. Show who or what can review it next. |
| `created` or `pending` approval | Approval requested | A human decision is required for the exact bound request. Show scope and expiry. |
| `approved` | Approved; awaiting application | Existing approval is recorded. Do not imply execution has occurred. |
| `denied` | Denied | The request may not proceed under this approval record. Show reason when safe. |
| `expired` | Approval expired | The approval can no longer authorize execution. Show the reviewed restart path, if any. |
| `superseded` | Replaced by a newer request | This record is no longer current. Link the replacement when authoritative. |
| `executing` | Applying approved action | Gateway has started the bound action. Command Center is observing it. |
| `executed` | Applied | Gateway recorded successful execution. This does not mean artifact review or promotion is complete. |
| `failed` | Application failed | The action did not complete successfully. Show diagnostics and safe next step. |
| `recovery_required` | Recovery review required | Diagnostics require operator or technical review before continuing. |
| `not_promoted` | Not promoted | The artifact has not moved into a broader trusted or approved-output zone. |
| ready artifact | Ready for review | The named artifact review can begin; no approval, promotion, publication, or release is implied. |

If the current backend uses different exact states for a record, implementation must map them
explicitly and test the mapping. This contract does not authorize adding the illustrative states.

## Audit Integrity

| State | Operator-facing label | Meaning | Required limitation |
| --- | --- | --- | --- |
| verification passes to current head | Audit log verified to checkpoint | The local hash chain verified through the named checkpoint. | Does not prove complete capture of activity outside Ithildin or resistance to host compromise. |
| verification fails | Audit integrity problem | The local chain did not verify. | Treat affected evidence as blocked for normal handoff and show diagnostics. |
| verification unavailable or stale | Audit verification unavailable / out of date | Current verification cannot be substantiated. | Do not display a green success state. |
| no correlated events | No correlated audit evidence | No matching events were found for the selected object. | Does not prove nothing happened outside Ithildin. |

Use `audit event` for a recorded event and `audit log integrity checkpoint` for the hash-chain head.
Do not call a hash alone proof, notarization, immutability, or custody.

## Signing

| State | Operator-facing label | Meaning |
| --- | --- | --- |
| signature verified with configured local key | Local signature verified | The exported bytes verify against the configured local signing material. It is not external notarization or hosted custody. |
| signing key not configured | Local signing unavailable | The local runtime cannot create the signed form. Unsigned evidence may still be reviewed if labeled. |
| signature verification fails | Signature invalid | The signed export must not be treated as verified. |
| signature not requested | Not signed | No signature was created for this export. |

Never shorten `Local signature verified` to `Trusted` or `Secure`.

## Exports

| State | Operator-facing label | Meaning |
| --- | --- | --- |
| export not created | Export not created | Evidence remains in the current view; no bundle has been generated. |
| export created | Evidence bundle created | A bounded local bundle was generated from the selected authoritative records. |
| export incomplete | Evidence bundle has warnings | Expected sections are absent or warnings affect interpretation. |
| export signed and verified | Evidence bundle created; local signature verified | Bundle creation and local signature verification both succeeded. |
| export failed | Export failed | No successful bundle should be implied; show safe diagnostics. |

Exports must state their scope, generated time, selected mission/run, redaction posture, included
sections, warnings, and signing status. JSONL, raw audit events, full hashes, and packet manifests are
technical-reviewer detail rather than routine-operator primary content.

## Copy Prohibitions

Do not use these unqualified labels:

- `Safe`, `Secure`, `Trusted`, `Compliant`, or `Protected`;
- `System healthy` when only one subsystem was checked;
- `Approved` when only a proposal exists;
- `Complete` when only an application or export completed;
- `Promoted` for staging-only placement or review readiness;
- `Verified` without naming what was verified and by which local mechanism;
- `Identity ready` without distinguishing configured local principals from production identity;
- `Risk: network` or `Risk: read` when the value is a capability class;
- `Signed` without showing verification state and local scope.

## Contract Validation for Future UI Work

Every implementation ticket must include tests or review evidence for:

- primary label plus machine identifier drill-down;
- explicit object and consequence for every status;
- proposal/approval/application/artifact/evidence separation;
- missing, unknown, warning, denied, expired, failed, and recovery-required states;
- no color-only meaning;
- no authority, security, compliance, deployment, or custody overclaim;
- unchanged Gateway/API machine terms and unchanged governed tool count.
