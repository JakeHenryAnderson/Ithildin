# Enterprise Review Send Session Record

Status: generated non-authoritative send-session record scaffold.

Run:

```sh
make enterprise-review-send-session-record
```

Validate:

```sh
make enterprise-review-send-session-record-check
```

The generated record is written under:

```text
var/review-runs/enterprise-review-send-session-record/
```

## Purpose

This scaffold gives the operator a local place to record what was actually sent after the
`ERG-003` and `ERG-002` packet handoff leaves Ithildin. It ties the current enterprise send package,
package hash evidence, lane prompts, lane response landing pads, and operator fill-in fields
together without asserting that an external review has happened.

The generated record starts with sent: `false`. The operator may copy it into local notes and fill
in send timestamp, reviewer/model label, channel, and message/thread identifiers after the human
send step.

## Boundary

The send-session record does not record external review, does not normalize responses, does not
write response files, does not close `ERG-003` or `ERG-002`, and does not approve runtime behavior.
In short, it does not write response files.
It is local operator evidence only.

It must keep these flags false:

- `records_external_review`
- `normalizes_responses`
- `writes_response_files`
- `closes_erg_003`
- `closes_erg_002`
- `runtime_changes_allowed`
- `mission_control_runtime_allowed`
- `live_vm_inspection_allowed`
- `local_model_invocation_allowed`
- `sandbox_orchestration_allowed`
- `trusted_host_promotion_allowed`
- `siem_adapter_allowed`
- `compliance_automation_allowed`
- `public_security_product_positioning_allowed`
- `new_power_classes_allowed`

## Operator Flow

1. Refresh local evidence:

   ```sh
   make release-check
   make review-candidate
   ```

2. Regenerate the current enterprise send set:

   ```sh
   make enterprise-review-send-refresh
   ```

3. Generate the session record scaffold:

   ```sh
   make enterprise-review-send-session-record
   ```

4. Send the `ERG-003` and `ERG-002` review packets in separate review threads.
5. Copy the generated scaffold into local operator notes and fill in the send fields.
6. Wait for real reviewer responses.
7. Paste responses only into the ignored dual-response inbox and run:

   ```sh
   make enterprise-dual-response-inbox
   make enterprise-response-waiting-room
   make enterprise-response-paste-preflight
   make enterprise-response-intake-refresh
   ```

The current governed tool count remains `24`, and the selected capability remains `not selected`.
