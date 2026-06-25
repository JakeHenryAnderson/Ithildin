# sandbox.artifact.write_text Negative Transcript Plan

Status: implemented observed-transcript plan.

This plan defines the denial transcripts expected for the implemented bounded local-preview
`sandbox.artifact.write_text` tool. Observed local fixture transcripts are generated with:

```sh
make sandbox-artifact-write-text-negative-transcripts
```

The transcript generator exercises temporary workspaces through the governed service path. It does
not add Mission Control behavior, VM lifecycle control, host promotion, shell execution, broad
filesystem writes, or a production/security-product claim.

## Strict Non-Leak List

- no file contents;
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

## Observed Scenarios

### traversal denied

- expected safe status: denied;
- expected safe reason label: traversal_denied;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- evidence source: governed service fixture and executor test.

### absolute path denied

- expected safe status: denied;
- expected safe reason label: absolute_path_denied;
- required non-leak assertions: strict non-leak list applies; no raw host paths;
- evidence source: governed service fixture.

### encoded ambiguity denied

- expected safe status: denied;
- expected safe reason label: encoded_ambiguity_denied;
- required non-leak assertions: strict non-leak list applies;
- evidence source: governed service fixture and executor test.

### hidden sensitive and git paths denied

- expected safe status: denied;
- expected safe reason label: hidden_sensitive_or_git_denied;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- evidence source: governed service fixture and executor test.

### symlink and hardlink denied

- expected safe status: denied;
- expected safe reason label: link_denied;
- required non-leak assertions: strict non-leak list applies; no target disclosure;
- evidence source: governed service fixture and filesystem tests.

### overwrite denied by default

- expected safe status: denied;
- expected safe reason label: overwrite_requires_approval;
- required non-leak assertions: strict non-leak list applies; no previous content;
- evidence source: governed service approval workflow fixture.

### replayed approval denied

- expected safe status: denied;
- expected safe reason label: replay_denied;
- required non-leak assertions: strict non-leak list applies;
- evidence source: governed service approval workflow fixture.

### missing sandbox profile denied

- expected safe status: denied;
- expected safe reason label: sandbox_profile_missing;
- required non-leak assertions: strict non-leak list applies;
- future evidence source: governed call.

### host write denied without promotion

- expected safe status: denied;
- expected safe reason label: promotion_required;
- required non-leak assertions: strict non-leak list applies; no raw host paths;
- future evidence source: governed call.

### oversized or unsupported content denied

- expected safe status: denied;
- expected safe reason label: content_rejected;
- required non-leak assertions: strict non-leak list applies; no content returned;
- future evidence source: executor test.

### unauthorized principal denied

- expected safe status: denied;
- expected safe reason label: authorization_denied;
- required non-leak assertions: strict non-leak list applies;
- future evidence source: policy parity.

### Mission Control metadata cannot substitute for Ithildin execution

- expected safe status: denied;
- expected safe reason label: metadata_only_not_execution_evidence;
- required non-leak assertions: strict non-leak list applies;
- future evidence source: review packet transcript.
