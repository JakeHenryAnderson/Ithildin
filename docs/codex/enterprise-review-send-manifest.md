# Enterprise Review Send Manifest

Status: generated send manifest for current enterprise external-review packets.

Run:

```sh
make enterprise-review-send-manifest
```

Validate:

```sh
make enterprise-review-send-manifest-check
```

The generated manifest is written under:

```text
var/review-packets/v3/enterprise-review-send-manifest/
```

## Purpose

This manifest gives the operator a single checked view of the current enterprise packets that are
ready to send. It sits above the dual-review outbox and records:

- the current recommended send set: `ERG-003` and `ERG-002`;
- the prompt and attachment count for each lane;
- the finding namespace each reviewer must use;
- the outbox artifact hash manifest;
- the post-send response kit, intake doc, dry run, and closure gate for each lane;
- blocked-boundary flags that must remain false.

This is intentionally a send manifest, not a response record. It does not record external review,
does not normalize responses, does not mutate committed findings, does not close either lane, and
does not approve runtime behavior.

## Send Set

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/importer planning review.

Generate the copied attachment set first with:

```sh
make enterprise-dual-review-outbox
```

Then generate the send manifest:

```sh
make enterprise-review-send-manifest
```

## After Sending

While waiting for responses, use:

```sh
make enterprise-dual-response-inbox
make enterprise-response-status-board
make enterprise-response-intake-drill
```

After a response arrives, follow the lane-specific response kit. The manifest points to the
response kit, intake doc, response dry run, and fail-closed closure gate for each lane. Favorable
review feedback is not enough by itself: it must be normalized, checked, dispositioned, and applied
through a later committed response-application path.

## Boundary

This manifest does not approve:

- live VM/container inspection;
- Mission Control runtime behavior;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapters;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

The current governed tool count remains `24`, and the selected capability remains `not selected`.
