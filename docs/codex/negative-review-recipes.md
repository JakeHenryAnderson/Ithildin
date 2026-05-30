# Negative Review Recipes

These recipes help reviewers exercise Ithildin denial paths. They are intended for a v0.2 review
candidate for the v0.1 local-preview runtime boundary. They do not add new tools, endpoints, or
execution powers.

Use these after running:

```sh
make demo-seed
make mcp-inspector-recipes
make negative-review-transcripts
```

The exact command syntax depends on the MCP Inspector or local client being used. The important
review target is the requested tool, arguments, and expected safe denial behavior.
`make negative-review-transcripts` records local fixture observations for the same denial classes
under `var/review-packets/v0.2/negative-review-transcripts/`.

## Path Traversal Denial

- Tool: `fs.read`
- Arguments: `{"path":"../README.md","workspace_id":"default"}`
- Expected result: denied before file content is returned.
- Evidence to inspect: audit event with denial metadata, no file content, and no executor success.

## Symlink Escape Denial

- Tool: `fs.read`
- Setup: create a symlink inside the demo workspace that points outside the workspace.
- Arguments: `{"path":"demo/symlink-to-outside","workspace_id":"default"}`
- Expected result: denied as a symlink/path escape.
- Evidence to inspect: safe error reason only; no target file content.

## Stale-Base Patch Apply Denial

- Tool sequence: `fs.patch.propose`, approve `fs.patch.apply`, then mutate the target file before
  calling `fs.patch.apply` with the approval ID.
- Expected result: `fs.patch.apply` rejects the stale base hash and does not partially write.
- Evidence to inspect: approval remains single-use, failed apply audit metadata includes stale-base
  reason without echoing file contents or diff contents.

## HTTP Private Redirect Denial

- Tool: `http.fetch`
- Setup: use a controlled local test server or mocked transport that redirects an allowlisted URL to
  `http://127.0.0.1/` or another private/link-local destination.
- Arguments: `{"url":"https://example.test/redirect-to-private"}`
- Expected result: redirect destination is revalidated and denied.
- Evidence to inspect: no response body leaked from the blocked destination and safe denial metadata
  is audited.

## Unknown Principal Denial

- Tool: `fs.list`
- Principal: `{"id":"agent:not-registered","roles":["Admin"]}`
- Arguments: `{"path":".","workspace_id":"default"}`
- Expected result: trusted principal resolution ignores spoofed roles and denies unknown identity.
- Evidence to inspect: denial happens before execution; no directory listing is returned.

## Disabled Principal Denial

- Tool: `fs.list`
- Setup: use a temporary principal registry in a test or local throwaway config where the requested
  principal exists but `enabled: false`.
- Expected result: disabled principal is denied before policy evaluation or execution.
- Evidence to inspect: denial metadata identifies disabled/unknown principal state without treating
  caller-provided roles as trusted.

## Replayed Approval Denial

- Tool sequence: create a patch proposal, request approval with `fs.patch.apply`, approve once, call
  `fs.patch.apply` with the approved `approval_id`, then repeat the same call.
- Expected result: first approved apply consumes the one-time scope; replay is denied.
- Evidence to inspect: second call does not write, approval status is executed/consumed, and audit
  metadata records replay or invalid approval state safely.

## Manifest Lock Tamper Denial

- Setup: generate a lock for a temporary manifest directory, then mutate one manifest.
- Expected result: registry startup with `require_lock=true` fails closed on hash mismatch.
- Evidence to inspect: safe manifest-lock error only; no runtime registry is accepted.

## Policy Parity Mismatch Detection

- Setup: run a parity fixture that intentionally expects `deny` for an in-scope read that policy
  allows.
- Expected result: `make policy-parity` style harness reports a failed fixture case.
- Evidence to inspect: preview/runtime evidence remains comparable; the mismatch is in the
  expectation, not a runtime policy mutation.

## Patch Apply Ambiguous Diagnostics

- Setup: place a patch-apply approval in `executing` without a corresponding apply-attempt record.
- Expected result: `/patch-apply-diagnostics` reports `ambiguous` and recommends manual review.
- Evidence to inspect: diagnostics remain read-only and do not repair, roll back, or complete the
  approval.

## Review Notes

- These are negative-path recipes for reviewers, not a replacement for automated tests.
- Prefer throwaway demo workspaces and fixture servers.
- Do not use production workspaces, real secrets, or broad network allowlists for these checks.
- Keep `http.fetch` exact-allowlist and GET-only while testing denial behavior.
