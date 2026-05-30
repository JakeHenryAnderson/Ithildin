"""Build local prompt packets for internal AI/source-review pressure tests."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.3/internal-ai-review-packet")


@dataclass(frozen=True)
class ReviewArea:
    slug: str
    title: str
    files: tuple[str, ...]
    claims: tuple[str, ...]


REVIEW_AREAS = (
    ReviewArea(
        slug="patch-apply",
        title="Patch Apply Approval Binding And Recovery Evidence",
        files=(
            "apps/api/src/ithildin_api/patches.py",
            "apps/api/src/ithildin_api/approvals.py",
            "apps/api/src/ithildin_api/tool_calls.py",
        ),
        claims=(
            "stored-proposal-only apply",
            "one-time approval consumption",
            "proposal/base/manifest/policy/schema/principal binding",
            "safe recovery evidence for incomplete apply attempts",
        ),
    ),
    ReviewArea(
        slug="filesystem",
        title="Filesystem Workspace And Race Semantics",
        files=(
            "apps/api/src/ithildin_api/read_tools.py",
            "apps/api/src/ithildin_api/patches.py",
            "docs/codex/filesystem-executor-contract.md",
        ),
        claims=(
            "workspace-root confinement",
            "symlink and hardlink denial",
            "UTF-8 text and size limits",
            "macOS/Linux-only local-preview platform claims",
        ),
    ),
    ReviewArea(
        slug="http-fetch",
        title="HTTP Fetch SSRF And Canonicalization",
        files=(
            "apps/api/src/ithildin_api/http_tools.py",
            "apps/api/src/ithildin_api/resources.py",
            "tests/test_http_tools.py",
        ),
        claims=(
            "GET-only exact allowlist",
            "redirect destination revalidation",
            "DNS/IP private range blocking",
            "proxy suppression and safe errors",
        ),
    ),
    ReviewArea(
        slug="signed-evidence",
        title="Signed Evidence And Audit Integrity",
        files=(
            "packages/audit-core/src/ithildin_audit_core/writer.py",
            "packages/audit-core/src/ithildin_audit_core/signing.py",
            "apps/api/src/ithildin_api/manifest_lock.py",
            "scripts/signed_evidence_demo.py",
            "tests/test_audit_writer.py",
        ),
        claims=(
            "hash-chain verification rejects invalid, missing, duplicate, and reordered events",
            "local Ed25519 signature verification",
            "digest binding for exported events and manifest lock",
            "key ID and public key consistency",
            "no external notarization claim",
        ),
    ),
    ReviewArea(
        slug="policy-parity",
        title="Policy Preview Runtime Parity",
        files=(
            "apps/api/src/ithildin_api/policy_preview.py",
            "apps/api/src/ithildin_api/tool_calls.py",
            "apps/api/src/ithildin_api/decision_evidence.py",
        ),
        claims=(
            "shared principal/resource normalization",
            "side-effect-free previews",
            "comparable decision evidence",
            "OPA/YAML boundary clarity",
        ),
    ),
    ReviewArea(
        slug="registry-fail-closed",
        title="Manifest Principal And Workspace Fail-Closed Registries",
        files=(
            "apps/api/src/ithildin_api/registry.py",
            "apps/api/src/ithildin_api/manifest_lock.py",
            "apps/api/src/ithildin_api/identity.py",
            "apps/api/src/ithildin_api/workspaces.py",
            "tests/test_tool_registry.py",
            "tests/test_identity.py",
            "tests/test_workspaces.py",
        ),
        claims=(
            "malformed trusted config fails closed",
            "duplicate IDs/names/paths are rejected",
            "disabled or unknown principals/workspaces cannot execute",
            "signed manifest lock enforcement is explicit and fail-closed",
        ),
    ),
    ReviewArea(
        slug="evidence-automation",
        title="Release Evidence Automation And Guardrails",
        files=(
            "scripts/release_evidence.py",
            "scripts/release_guardrails.py",
            "scripts/review_packet_bundle.py",
            "scripts/consolidate_review_packet.py",
            "scripts/review_packet_diff.py",
            "docs/codex/release-evidence-schema.md",
            "docs/codex/release-guardrail-expansion.md",
        ),
        claims=(
            "release evidence has a validated schema and no secret-like markers",
            "review bundles hash generated docs and artifacts",
            "packet diffs compare handoff artifacts without runtime state",
            "release guardrails catch warning, workflow, and deferred-power drift",
        ),
    ),
    ReviewArea(
        slug="mcp-ingress",
        title="MCP Ingress Thinness",
        files=(
            "apps/mcp-server/src/ithildin_mcp_server/server.py",
            "tests/test_mcp_adapter.py",
            "tests/test_mcp_integration_flow.py",
        ),
        claims=(
            "stdio adapter delegates to governed pipeline",
            "no independent policy or execution bypass",
            "MCP tool listing uses trusted visibility",
        ),
    ),
    ReviewArea(
        slug="review-console",
        title="Review Console Approval Evidence",
        files=(
            "apps/ui/src/App.tsx",
            "apps/api/src/ithildin_api/app.py",
            "docs/codex/evidence-contracts.md",
        ),
        claims=(
            "approval evidence visibility",
            "safe approve/deny API usage",
            "failure and unauthorized state clarity",
            "compact hash interpretability",
        ),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = build_internal_review_packet(args.output_dir)
    print(f"Built internal AI review packet at {output_dir}")
    return 0


def build_internal_review_packet(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for area in REVIEW_AREAS:
        output_dir.joinpath(f"{area.slug}.md").write_text(
            _area_prompt(area),
            encoding="utf-8",
        )
    output_dir.joinpath("INTERNAL_REVIEW_INDEX.md").write_text(
        _index_document(),
        encoding="utf-8",
    )
    return output_dir


def _index_document() -> str:
    prompt_list = "\n".join(f"- `{area.slug}.md` - {area.title}" for area in REVIEW_AREAS)
    return f"""# Internal AI Review Packet v2

This ignored packet prepares prompts for high-intelligence internal AI/subagent review. It is a
continuous pressure test, not an independent external audit and not permission to add new tool
powers.

This v2 packet includes v0.3-prep evidence automation, manifest/principal/workspace fail-closed
suites, audit integrity adversarial coverage, and release guardrail prompts in addition to the
original high-risk executor areas.

Use findings with `docs/codex/reviewer-finding-template.md` and update
`docs/codex/source-review-closure-matrix.md` only with clearly labeled internal-review status.

## Prompts

{prompt_list}
"""


def _area_prompt(area: ReviewArea) -> str:
    file_list = "\n".join(f"- `{file}`" for file in area.files)
    claim_list = "\n".join(f"- {claim}" for claim in area.claims)
    return f"""# Internal AI Review: {area.title}

You are performing an internal AI/source-review pressure test for Ithildin. This is not an
independent external audit. Find concrete implementation risks and cite files/functions.

## Files And Functions To Inspect

{file_list}

## Claims To Test

{claim_list}

## Required Output

- Overall judgment: ready / ready with fixes / not ready for this area.
- Findings using `docs/codex/reviewer-finding-template.md` fields.
- Blocking status for each finding.
- Tests or evidence that support the finding.
- Recommended follow-up task if a fix is needed.

Do not propose new powerful tool classes. If the issue changes the product boundary or security
architecture, recommend stopping the sprint and seeking external consultation.
"""


if __name__ == "__main__":
    raise SystemExit(main())
