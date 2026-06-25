# sandbox.artifact.write_text Fixture Plan

Status: future fixture/test contract only. No runtime behavior.

This fixture plan defines the coverage expected before `sandbox.artifact.write_text` can be
implemented for the Hello World sandbox demo. It does not add a tool manifest, executor, policy
rule, API/MCP behavior, approval/audit behavior, Mission Control runtime behavior, VM lifecycle
control, UI runtime behavior, or governed write power.

The proposed tool remains blocked until a later explicit implementation decision.

## Strict Non-Leak List

- no file contents in responses or audit metadata;
- no raw host paths;
- no prompts or chain-of-thought;
- no secrets;
- no environment names or values;
- no shell output;
- no VM logs;
- no unrelated directory listings;
- no sandbox root internals;
- no Mission Control private state;
- no production identity claims;
- no compliance claims.

## Scenario Contract

### hello world artifact creation

- Fixture purpose: prove the intended happy path can create `hello-demo/hello.txt` containing
  `Hello World` only after the future implementation gate approves the write lane.
- Safe expected labels/count categories: artifact_created, parent_created, content_sha256,
  bytes_written, approval_bound.
- Required non-leak assertions: strict non-leak list applies; no raw host paths; no file contents
  returned.
- Future test type: governed call.

### empty parent directory creation denied without approval

- Fixture purpose: confirm parent-directory creation cannot occur unless it is explicitly included
  in the approved action scope.
- Safe expected labels/count categories: requires_approval, parent_creation_denied.
- Required non-leak assertions: strict non-leak list applies.
- Future test type: approval workflow.

### traversal denied

- Fixture purpose: confirm `../` paths cannot escape the sandbox/staging root.
- Safe expected labels/count categories: denied, traversal_denied.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### absolute path denied

- Fixture purpose: confirm absolute host paths are rejected before execution.
- Safe expected labels/count categories: denied, absolute_path_denied.
- Required non-leak assertions: strict non-leak list applies; no raw host paths.
- Future test type: schema/governed call.

### encoded ambiguity denied

- Fixture purpose: confirm percent-encoded or otherwise ambiguous path forms cannot bypass
  normalization.
- Safe expected labels/count categories: denied, encoded_ambiguity_denied.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### control character denied

- Fixture purpose: confirm control characters in roots, paths, or content metadata are rejected
  safely.
- Safe expected labels/count categories: denied, control_character_denied.
- Required non-leak assertions: strict non-leak list applies.
- Future test type: schema/executor.

### hidden sensitive and git paths denied

- Fixture purpose: confirm hidden, sensitive, and `.git` paths are denied.
- Safe expected labels/count categories: denied, hidden_sensitive_denied, git_denied.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### symlink and hardlink denied

- Fixture purpose: confirm symlink and hardlink targets or ancestors cannot be written through.
- Safe expected labels/count categories: denied, symlink_denied, hardlink_denied.
- Required non-leak assertions: strict non-leak list applies; no target disclosure.
- Future test type: filesystem race harness.

### overwrite denied by default

- Fixture purpose: confirm existing artifacts are not overwritten unless explicit approval semantics
  bind the overwrite.
- Safe expected labels/count categories: denied, overwrite_requires_approval.
- Required non-leak assertions: strict non-leak list applies; no previous content disclosure.
- Future test type: approval workflow.

### replayed approval denied

- Fixture purpose: confirm a consumed approval cannot create or overwrite a second artifact.
- Safe expected labels/count categories: denied, replay_denied.
- Required non-leak assertions: strict non-leak list applies.
- Future test type: approval workflow.

### missing sandbox profile denied

- Fixture purpose: confirm writes cannot proceed without a trusted operator-managed sandbox profile.
- Safe expected labels/count categories: denied, sandbox_profile_missing.
- Required non-leak assertions: strict non-leak list applies.
- Future test type: governed call.

### host write denied without promotion

- Fixture purpose: confirm direct trusted-host writes are rejected unless a separate promotion lane is
  explicitly approved later.
- Safe expected labels/count categories: denied, promotion_required.
- Required non-leak assertions: strict non-leak list applies; no raw host paths.
- Future test type: governed call.

### oversized or unsupported content denied

- Fixture purpose: confirm size, encoding, and binary/NUL content limits are enforced before write.
- Safe expected labels/count categories: denied, content_too_large, unsupported_encoding,
  binary_nul_denied.
- Required non-leak assertions: strict non-leak list applies; no content returned.
- Future test type: executor.

### unauthorized principal denied

- Fixture purpose: confirm unknown, disabled, or underprivileged principals cannot invoke the future
  write lane.
- Safe expected labels/count categories: denied, authorization_denied.
- Required non-leak assertions: strict non-leak list applies.
- Future test type: policy parity.
