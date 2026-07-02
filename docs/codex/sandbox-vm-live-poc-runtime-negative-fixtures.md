# Sandbox/VM Live POC Runtime Negative Fixtures

Status: design-only negative fixture plan for the future `ERG-004` descriptor/correlation slice.

Current governed tool count: `24`.

This plan defines the negative cases a later implementation must turn into tests and transcripts.
It does not add a runtime validator, API endpoint, MCP behavior, UI behavior, persisted state, or
governed tool power.

## Descriptor Shape Failures

A future implementation must reject:

- missing required fields;
- unknown top-level fields;
- wrong schema version;
- malformed IDs, hashes, timestamps, booleans, or enum values;
- stale or mismatched `vm_profile_hash`;
- mismatched `sandbox_profile_id`;
- missing `run_id`;
- mismatched `workspace_id`, `principal_id`, or `run_id`;
- unsafe `mount_root_label`;
- unexpected `network_posture_label`;
- `promotion_status` other than `not_promoted`.

## Correlation Failures

A future implementation must reject or mark review-required:

- missing Agent Run correlation;
- missing approval correlation where approval-gated action is represented;
- missing audit correlation;
- missing signed-export correlation where a signed export is represented;
- stale audit head hash;
- mismatched signed export hash;
- mismatched Mission Control display packet hash;
- cleanup transcript hash mismatch;
- missing or mismatched `failure_transcript_hash`;
- packet hash mismatch.

## Forbidden Authority Attempts

A future implementation must reject any descriptor or status evidence that claims:

- VM/container lifecycle management by Ithildin;
- live VM/container inspection by Ithildin;
- local model invocation by Ithildin;
- Mission Control execution, approval, policy, or audit authority;
- trusted-host promotion;
- host writes or artifact promotion;
- arbitrary network expansion;
- API/MCP profile loading;
- shell execution;
- Docker socket access;
- Kubernetes access;
- browser automation;
- broad filesystem writes;
- new governed tool powers.

## Leakage Failures

A future implementation must reject or redact evidence that includes:

- raw secrets, tokens, credentials, or private key material;
- prompt text or model response text;
- file contents;
- diffs;
- raw cleanup or failure transcript text;
- raw host paths or VM paths;
- directory listings;
- dependency names;
- package script names or values;
- command lines or shell output;
- response bodies;
- registry URLs;
- environment variable names or values.

## Required Transcript Shape

Negative transcripts must be secret-free and include only:

- scenario ID;
- safe scenario label;
- expected denial or review-required outcome;
- observed safe reason labels;
- descriptor hash;
- relevant correlation IDs or short hashes;
- false authority flags;
- output policy summary.

