# Read-Only Metadata Capability Checklist

Status: reusable capability-prep checklist. This checklist does not add runtime behavior.

Use this checklist for every future read-only local developer metadata capability before writing a
manifest or executor.

## Proposal Gate

The proposal must include:

- capability name and intended category;
- design-only status;
- explicit no-runtime-change statement;
- input shape;
- output shape;
- privacy analysis using [Metadata Privacy Policy](metadata-privacy-policy.md);
- executor contract sketch;
- policy fixture sketch;
- audit field sketch;
- UI/review expectations;
- negative transcript sketch;
- resource limits;
- accepted-risk impact;
- no-new-powers analysis;
- internal xhigh review requirement;
- implementation remains blocked statement.

## Implementation-Planning Gate

The implementation plan must include:

- implementation-planning-only status;
- implementation state: blocked;
- future manifest sketch;
- strict input schema contract;
- strict output schema contract;
- `additionalProperties: false` at every object level;
- executor checklist;
- parser/canonicalization plan;
- privacy/redaction plan;
- policy fixture plan;
- audit evidence plan;
- UI and policy preview plan;
- negative transcript plan;
- resource limits;
- source-review and implementation-decision requirement;
- no manifest/executor/policy/API/MCP/UI/runtime behavior changes.

## Implementation Gate

Runtime implementation may begin only after the implementation plan has passed review. The
implementation checkpoint must include:

- manifest and manifest-lock update;
- executor implementation;
- policy preview/runtime resource construction;
- policy fixtures and parity evidence;
- audit evidence;
- MCP exposure evidence;
- UI/tool-list evidence if applicable;
- negative tests and transcripts;
- source-review bundle;
- internal xhigh source review;
- explicit implementation decision for that one capability.

## Stop Conditions

Stop before implementation if:

- raw sensitive metadata is returned by default;
- stable identifiers are used without a reviewed HMAC/salt/opaque-ID contract;
- schema allows unknown properties;
- executor needs shell, caller-controlled argv, caller-controlled format strings, remote access, or
  broad filesystem access;
- output includes file contents, raw diffs, patch hunks, raw stderr, credentials, or unbounded text;
- policy preview/runtime evidence cannot be made comparable;
- audit evidence would need raw sensitive values;
- internal xhigh review reports critical/high issues.
