# Sandbox/VM Live POC Runtime Descriptor Contract

Status: design-only descriptor contract for the future `ERG-004` runtime descriptor/correlation
slice.

Current governed tool count: `24`.

This contract describes the only descriptor shape that a later implementation gate may consider.
It is not a runtime interface. Ithildin does not yet accept, store, render, or act on these
descriptors.

## Descriptor Source And Trust

The descriptor is operator-supplied evidence about an operator-managed VM run. Ithildin must treat
the VM lifecycle, OS isolation, network posture, mount posture, model startup, and file transfer as
operator-managed and operator-attested. Descriptor validation may prove only that the supplied
metadata is well shaped, hash-bound, and correlated to Ithildin-mediated evidence.

Required source flags:

- `descriptor_source: operator_supplied`
- `vm_lifecycle_source: operator_managed`
- `isolation_claim_source: operator_attested`
- `network_posture_source: operator_attested`
- `mount_posture_source: operator_attested`
- `model_client_source: operator_attested`
- `ithildin_live_inspection_performed: false`
- `ithildin_lifecycle_control_performed: false`
- `mission_control_runtime_authority_used: false`
- `trusted_host_promotion_performed: false`

## Required Fields

The future descriptor must be a closed object with these required safe fields:

- `operator_intent_id`
- `principal_id`
- `workspace_id`
- `run_id`
- `sandbox_id`
- `sandbox_profile_id`
- `vm_profile_label`
- `vm_profile_hash`
- `mount_root_label`
- `workspace_mount_label`
- `network_posture_label`
- `model_client_label`
- `model_request_hash`
- `tool_call_correlation_id`
- `approval_correlation_id`
- `audit_head_hash`
- `signed_export_hash`
- `cleanup_plan_hash`
- `cleanup_transcript_hash`
- `failure_transcript_hash`
- `mission_control_display_packet_hash`
- `promotion_status: not_promoted`
- source flags listed above

## Safe Value Classes

Allowed value classes are safe labels, hashes, IDs, timestamps, booleans, and enums only.

Allowed coarse statuses:

- `prepared`
- `running_observed_by_operator`
- `completed_reported_by_operator`
- `failed_reported_by_operator`
- `cleanup_reported_by_operator`
- `recovery_required`
- `ambiguous`

Allowed network posture labels:

- `disabled`
- `loopback_only`
- `egress_blocked_by_operator`
- `operator_attested_restricted`
- `unknown_requires_review`

Allowed mount/root labels:

- `workspace_scratch`
- `operator_staging`
- `read_only_source_copy`
- `approved_output_staging`
- `unknown_requires_review`

## Correlation Requirements

A later implementation may correlate only by safe identifiers and hashes:

- descriptor `run_id` must match an existing Agent Run ID;
- descriptor `workspace_id` and `principal_id` must match the Agent Run evidence;
- approval correlation must match existing approval evidence when the run includes approval-gated
  action;
- audit head hash must match existing local audit verification evidence;
- signed export hash must match a local signed export bundle digest when supplied;
- Mission Control display packet hash must be treated as display-only evidence, not runtime
  authority.

## Forbidden Payload Content

The descriptor, validation errors, status summaries, and generated evidence must not contain:

- prompts or model responses;
- chain-of-thought or hidden reasoning;
- file contents;
- diffs;
- raw transcripts;
- raw host paths;
- raw VM paths;
- sandbox filesystem listings;
- environment variable names or values;
- secrets, tokens, credentials, private keys, or key material;
- dependency names;
- package script names or values;
- command lines or shell output;
- Docker socket paths;
- Kubernetes contexts;
- browser profiles;
- network credentials;
- registry URLs;
- arbitrary response bodies.

## Explicit Non-Claims

Descriptor validation does not prove OS isolation, VM integrity, model behavior, network posture,
mount posture, filesystem state, cleanup success, or host custody beyond the supplied operator
evidence and Ithildin-mediated correlations.

