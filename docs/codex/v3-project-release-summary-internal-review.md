# v3 project.release.summary Internal Source Review

Status: internal source-review pass complete for continued local-preview development.

This review inspected `project.release.summary` as an implemented bounded read-only metadata tool.
It does not approve public/security-product positioning, production identity, compliance claims,
new governed tool powers, or any broader capability class.

## Scope

- Manifest/schema: `tool-manifests/project-release-summary.yaml`.
- Executor/resource construction: `apps/api/src/ithildin_api/read_tools.py`.
- Governed-call/audit metadata: `apps/api/src/ithildin_api/tool_calls.py`.
- Policy parity fixture: `policies/tests/parity.yaml`.
- Direct, governed, MCP, registry, and release-readiness tests:
  `tests/test_read_tools.py`, `tests/test_governed_tool_calls.py`,
  `tests/test_mcp_adapter.py`, `tests/test_policy_parity.py`,
  `tests/test_tool_registry.py`, and `tests/test_release_readiness.py`.
- Handoff generator: `scripts/project_release_summary_source_review_bundle.py`.

## Claims Tested

- The tool remains local workspace only and read-only.
- Inputs are bounded and schema-closed: `workspace_id`, `root`, `max_depth`, `limit`, and
  `include_categories`.
- Output is count-only and label-only.
- Raw file names, raw paths, file contents, release names, version strings, changelog contents, tag
  names, branch names, command/script values, environment names/values, registry URLs, package names,
  dependency names, author/maintainer names, email addresses, Git output, CI output, legal claims,
  compliance claims, and deployment-readiness claims are suppressed.
- Policy preview/runtime evidence uses the normalized `project_release` resource.
- MCP access flows through the governed path.
- Audit metadata contains safe counts, section keys, and output-policy booleans only.
- The source-review packet gives a reviewer enough source/test/evidence material to assess the lane.

## Implementation Evidence

- The manifest is `risk: read`, `category: project`, MCP exposed as read-only, and has
  `additionalProperties: false`.
- The executor validates arguments before traversal, resolves roots through the existing
  workspace-confined filesystem path, denies absolute/traversal/ambiguous paths through shared
  helpers, skips hidden/sensitive paths, `.git` internals, symlinks, hardlinks, unsupported types,
  oversized inputs, binary/NUL content, unsupported encodings, and safe filesystem errors.
- Internal classification uses allowlisted labels only and returns counts, skipped counts,
  truncation/limit metadata, and output-policy flags.
- Focused tests assert no raw release filenames, version strings, changelog/customer text, command
  values, `.git`, `.env`, or sensitive fixture strings appear in direct, governed, or MCP outputs.
- Policy parity includes `project_release_summary_preview_matches_runtime`.
- The governed-call audit test verifies resource type and safe metadata keys.

## Finding

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| XH-RELEASE-001 | medium | project release summary | `scripts/project_release_summary_source_review_bundle.py` | should-fix | fixed | Include source and focused test bundles in the source-review handoff. |

## Residual Risk

The tool still reads candidate file bytes internally to classify release-shaped signals. The current
local-preview claim relies on bounded reads, UTF-8/text-only handling, safe errors, count-only output,
and regression tests that serialized responses and audit metadata do not include raw names, paths,
contents, version strings, or release/customer text. External/source review remains useful before
claiming anything stronger than continued local-preview use.

## Task 079+ Follow-Up Queue

- No critical or high findings were found.
- `XH-RELEASE-001` was fixed in this sprint by expanding the source-review bundle contents.
- The lane is locally reviewed for continued local-preview development only.
- The lane is not externally closed and does not unblock public/security-product positioning or new
  powerful tool classes.

## Verification

Run:

```bash
make project-release-summary-source-review-bundle
make reviewer-findings-check
make review-findings-summary
make policy-parity
make read-only-capability-inventory-gate
make tool-surface-invariant-gate
make no-new-powers-guardrail
```
