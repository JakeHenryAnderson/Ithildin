# v3 project.structure.summary Internal Review

Status: internal local-preview review. This document does not add runtime behavior, approve broader
capability expansion, or replace external/source review.

## Review Result

`project.structure.summary` is locally reviewed for the bounded read-only project-intelligence lane.
No critical, high, medium, low, or informational implementation findings were recorded in this pass.

Disposition: ready for external/source disposition as one count-only, workspace-confined,
read-only metadata capability. Public/security-product positioning and broader capability expansion
remain blocked.

Finding namespace reserved for this pass: `INT-PSS-###`.

## Source And Evidence Inspected

- Manifest: `tool-manifests/project-structure-summary.yaml`.
- Executor/resource path: `apps/api/src/ithildin_api/read_tools.py`.
- Governed call audit path: `apps/api/src/ithildin_api/tool_calls.py`.
- Policy parity fixture: `policies/tests/parity.yaml`.
- MCP/governed exposure tests: `tests/test_mcp_adapter.py`,
  `tests/test_governed_tool_calls.py`, and `tests/test_policy_parity.py`.
- Focused source-review bundle: `make project-structure-summary-source-review-bundle`.

## Claims Checked

- The tool is `risk: read`, category `project`, and exposed only through the governed pipeline.
- Inputs are bounded to `workspace_id`, `root`, `max_depth`, `limit`, and
  `include_categories`, with unknown arguments rejected.
- Output is structural counts, allowlisted labels, skipped counts, limit/truncation evidence, and
  output-policy booleans only.
- Output and audit metadata exclude file contents, raw recursive listings, raw file names, raw
  sensitive paths, stable path IDs, dependency names, package names, script values,
  package-manager output, registry/network data, raw filesystem errors, and shell behavior.
- Policy preview/runtime parity uses resource type `project_structure`.

## Verification Commands

```bash
uv run pytest tests/test_read_tools.py tests/test_governed_tool_calls.py \
  tests/test_mcp_adapter.py tests/test_policy_parity.py tests/test_tool_registry.py -q
make project-structure-summary-implementation-gate
make project-structure-summary-source-review-bundle
```

## Follow-Up Queue

- No immediate remediation tasks were opened by this internal pass.
- External/source review may still record `EXT-PSS-###` findings before the lane is treated as
  externally closed.
