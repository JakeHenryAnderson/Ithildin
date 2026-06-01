"""Generate focused v0.6 external-review dispatch packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/api",
    "apps/mcp-server",
    "tool-manifests.lock.json",
)


@dataclass(frozen=True)
class DispatchArea:
    slug: str
    title: str
    finding_namespace: str
    closure_rows: tuple[str, ...]
    source_files: tuple[str, ...]
    review_docs: tuple[str, ...]
    commands: tuple[str, ...]
    prompt: str


DISPATCH_AREAS: tuple[DispatchArea, ...] = (
    DispatchArea(
        slug="patch-apply",
        title="Patch Apply External Review Packet",
        finding_namespace="EXT-PA-###",
        closure_rows=("Patch apply", "Patch apply source review checklist"),
        source_files=(
            "apps/api/src/ithildin_api/patches.py",
            "apps/api/src/ithildin_api/approvals.py",
            "apps/api/src/ithildin_api/tool_calls.py",
        ),
        review_docs=(
            "docs/codex/patch-apply-source-review-checklist.md",
            "docs/codex/patch-apply-state-machine.md",
            "docs/codex/filesystem-executor-contract.md",
            "docs/codex/source-file-inspection-packet.md",
        ),
        commands=(
            "uv run pytest tests/test_patch_proposals.py "
            "tests/test_approval_workflow.py tests/test_governed_tool_calls.py "
            "tests/test_security_regressions.py",
            "make release-check",
        ),
        prompt=(
            "Review the stored-proposal-only patch apply flow, approval binding, replay "
            "denial, stale-base checks, incomplete-apply diagnostics, and safe audit metadata."
        ),
    ),
    DispatchArea(
        slug="filesystem",
        title="Filesystem and Platform External Review Packet",
        finding_namespace="EXT-FS-###",
        closure_rows=("Filesystem", "CI/platform claims", "Filesystem source review checklist"),
        source_files=(
            "apps/api/src/ithildin_api/read_tools.py",
            "apps/api/src/ithildin_api/workspaces.py",
            "apps/api/src/ithildin_api/patches.py",
        ),
        review_docs=(
            "docs/codex/filesystem-source-review-checklist.md",
            "docs/codex/filesystem-executor-contract.md",
            "docs/codex/ci-platform-plan.md",
        ),
        commands=(
            "make filesystem-contract-check",
            "uv run pytest tests/test_read_tools.py tests/test_patch_proposals.py "
            "tests/test_security_regressions.py",
            "make release-check",
        ),
        prompt=(
            "Review workspace confinement, path resolution, symlink/hardlink denial, "
            "platform claims, race assumptions, and Windows/WSL unsupported status."
        ),
    ),
    DispatchArea(
        slug="http-fetch",
        title="HTTP Fetch External Review Packet",
        finding_namespace="EXT-HTTP-###",
        closure_rows=("HTTP fetch", "HTTP fetch source review checklist"),
        source_files=("apps/api/src/ithildin_api/http_tools.py",),
        review_docs=(
            "docs/codex/http-fetch-source-review-checklist.md",
            "docs/codex/http-executor-contract.md",
            "docs/codex/findings/sub-001-http-fetch-dns-pinning.md",
            "docs/codex/findings/sub-007-http-response-processing-safe-errors.md",
            "docs/codex/findings/sub-008-http-explicit-port-normalization.md",
            "docs/codex/findings/sub-009-http-audit-query-redaction.md",
            "docs/codex/findings/sub-040-http-malformed-url-resource-redaction.md",
            "docs/codex/findings/sub-041-http-preview-schema-resource-order.md",
            "docs/codex/findings/sub-042-http-raw-unicode-url-safe-error.md",
            "docs/codex/findings/sub-043-http-json-parser-safe-errors.md",
            "docs/codex/findings/sub-044-http-dispatch-finding-coverage.md",
            "docs/codex/findings/sub-045-http-closure-traceability.md",
            "docs/codex/findings/sub-046-http-lane-result-summary.md",
            "docs/codex/findings/sub-047-http-contract-link-drift.md",
        ),
        commands=(
            "uv run pytest tests/test_http_tools.py tests/test_governed_tool_calls.py",
            "make release-check",
        ),
        prompt=(
            "Review URL canonicalization, exact allowlist semantics, DNS/IP validation, "
            "redirect revalidation, proxy suppression, and safe errors."
        ),
    ),
    DispatchArea(
        slug="signed-evidence",
        title="Audit and Signed Evidence External Review Packet",
        finding_namespace="EXT-SE-###",
        closure_rows=(
            "Signed evidence",
            "Audit integrity",
            "Signed evidence source review checklist",
        ),
        source_files=(
            "packages/audit-core/src/ithildin_audit_core/",
            "apps/api/src/ithildin_api/audit_routes.py",
            "apps/api/src/ithildin_api/manifest_lock.py",
        ),
        review_docs=(
            "docs/codex/signed-evidence-source-review-checklist.md",
            "docs/codex/signed-audit-exports.md",
            "docs/codex/signed-manifest-locks.md",
            "docs/codex/audit-integrity-adversarial-suite.md",
        ),
        commands=(
            "make signed-evidence-demo",
            "make signed-evidence-demo-verify",
            "uv run pytest tests/test_audit_writer.py tests/test_signed_evidence_demo.py",
            "make release-check",
        ),
        prompt=(
            "Review local hash-chain verification, signed export digest binding, "
            "manifest-lock signature verification, key identity, and local-only trust-root "
            "wording."
        ),
    ),
    DispatchArea(
        slug="policy-registry",
        title="Policy and Registry External Review Packet",
        finding_namespace="EXT-PR-###",
        closure_rows=(
            "Policy parity",
            "Registry fail-closed",
            "Policy parity source review checklist",
        ),
        source_files=(
            "apps/api/src/ithildin_api/policy.py",
            "apps/api/src/ithildin_api/policy_preview.py",
            "apps/api/src/ithildin_api/registry.py",
            "apps/api/src/ithildin_api/identity.py",
            "apps/api/src/ithildin_api/workspaces.py",
        ),
        review_docs=(
            "docs/codex/policy-parity-source-review-checklist.md",
            "docs/codex/policy-parity-harness.md",
            "docs/codex/registry-fail-closed-suite.md",
            "docs/codex/opa-parity-decision.md",
        ),
        commands=("make policy-test", "make policy-parity", "make release-check"),
        prompt=(
            "Review principal/resource normalization, policy preview/runtime parity, "
            "OPA/YAML boundary, and manifest/principal/workspace fail-closed behavior."
        ),
    ),
    DispatchArea(
        slug="mcp-ingress",
        title="MCP Ingress External Review Packet",
        finding_namespace="EXT-MCP-###",
        closure_rows=("MCP ingress", "MCP ingress source review checklist"),
        source_files=("apps/mcp-server/src/ithildin_mcp_server/",),
        review_docs=(
            "docs/codex/mcp-ingress-source-review-checklist.md",
            "docs/codex/mcp-ingress-bypass-audit.md",
            "docs/codex/mcp-inspector-recipes.md",
        ),
        commands=(
            "uv run pytest tests/test_mcp_adapter.py tests/test_mcp_integration_flow.py",
            "make release-check",
        ),
        prompt=(
            "Review that stdio MCP list/call handlers remain thin adapters into the "
            "governed pipeline with no local policy or executor bypass."
        ),
    ),
    DispatchArea(
        slug="review-console",
        title="Review Console External Review Packet",
        finding_namespace="EXT-UI-###",
        closure_rows=(
            "Local admin auth",
            "Review console evidence",
            "Review console source review checklist",
        ),
        source_files=("apps/ui/src/App.tsx", "apps/api/src/ithildin_api/app.py"),
        review_docs=(
            "docs/codex/review-console-source-review-checklist.md",
            "docs/codex/review-console-assurance.md",
            "docs/codex/local-auth-boundary.md",
        ),
        commands=(
            "npm run typecheck --prefix apps/ui",
            "npm run build --prefix apps/ui",
            "make release-check",
        ),
        prompt=(
            "Review approval evidence visibility, unauthorized/failure states, "
            "local-preview warnings, and absence of hidden mutation controls."
        ),
    ),
    DispatchArea(
        slug="release-automation",
        title="Release and Evidence Automation External Review Packet",
        finding_namespace="EXT-REL-###",
        closure_rows=(
            "Release evidence",
            "Negative denial evidence",
            "Adversarial corpora",
            "Resource limits",
            "Redaction evidence",
            "Demo scenarios",
            "Documentation IA",
            "Threat model refresh",
            "v0.4 packet generator",
            "External review intake v2",
            "v0.4 external packet",
            "v0.5 roadmap",
            "Capability expansion gate",
            "Tool-surface invariant gate",
            "Evidence-confusion gate",
            "External-review closure gate",
            "Source review runbook v2",
            "Source file inspection packet",
            "External findings intake dry run",
            "Closure matrix evidence sync",
            "Accepted risk register",
            "Capability decision report",
            "No-new-powers guardrail",
            "Source review transcript packet",
            "Reviewer artifact manifest",
            "External response intake template",
            "Review packet source pointers",
            "v0.5 threat model delta",
            "v0.5 review candidate command",
            "v0.5 consolidated packet update",
            "v0.5 external review prompt",
            "v0.5 boundary decision draft",
            "v0.5 handoff packet",
            "v0.6 boundary charter",
            "v0.6 external reviewer assignment matrix",
        ),
        source_files=("scripts/", "docs/codex/"),
        review_docs=(
            "docs/codex/v0.6-boundary-charter.md",
            "docs/codex/v0.6-external-review-assignment-matrix.md",
            "docs/codex/source-review-runbook-v2.md",
            "docs/codex/review-packet-source-pointers.md",
            "docs/codex/accepted-risk-register.md",
            "docs/codex/capability-decision-report.md",
        ),
        commands=(
            "make v05-review-candidate",
            "make packet-redaction-scan",
            "make release-check",
        ),
        prompt=(
            "Review release evidence, packet hashing, redaction scanning, no-new-powers "
            "gates, external-review closure gates, and capability-decision blocking behavior."
        ),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="var/review-packets/v0.6/dispatch")
    parser.add_argument("--json", action="store_true", help="emit JSON summary")
    args = parser.parse_args()

    try:
        summary = build_dispatch_packets(Path.cwd().resolve(), Path(args.output_root))
    except RuntimeError as exc:
        print(f"external review dispatch packet generation failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(summary, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(f"Built v0.6 external review dispatch packets at {summary['output_root']}")
        print(f"packet_count: {summary['packet_count']}")
        print(f"manifest: {summary['manifest_path']}")
    return 0


def build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    missing = [marker for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise RuntimeError("must be run from Ithildin repo root; missing " + ", ".join(missing))

    output_root.mkdir(parents=True, exist_ok=True)
    commit = _git(["rev-parse", "HEAD"])
    dirty = bool(_git(["status", "--short"]))
    packets: list[dict[str, Any]] = []

    for area in DISPATCH_AREAS:
        filename = f"{area.slug}.md"
        path = output_root / filename
        payload = _render_packet_payload(area, commit, dirty)
        payload_sha256 = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        path.write_text(
            _render_packet(area, commit, dirty, payload_sha256),
            encoding="utf-8",
        )
        metadata = _artifact_metadata(path, output_root)
        metadata["payload_sha256"] = payload_sha256
        packets.append(metadata)

    index_path = output_root / "INDEX.md"
    index_path.write_text(_render_index(commit, dirty, packets), encoding="utf-8")
    manifest = {
        "packet_type": "ithildin.v0.6.external_review_dispatch_packets",
        "format_version": "1",
        "repo_root": repo_root.as_posix(),
        "commit": commit,
        "dirty": dirty,
        "packet_count": len(packets),
        "packets": [_artifact_metadata(index_path, output_root), *packets],
        "does_not_prove": [
            "production readiness",
            "external source review closure",
            "capability expansion approval",
            "broader public/security-product readiness",
        ],
    }
    manifest_path = output_root / "dispatch-packet-hashes.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "output_root": output_root.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "packet_count": len(packets),
        "commit": commit,
        "dirty": dirty,
        "packets": manifest["packets"],
    }


def _render_packet(area: DispatchArea, commit: str, dirty: bool, payload_sha256: str) -> str:
    payload = _render_packet_payload(area, commit, dirty)
    hash_section = "\n".join(
        [
            "## Hash Evidence",
            "",
            f"- Dispatch packet payload SHA-256: `{payload_sha256}`.",
            "- This digest covers the packet payload without this `Hash Evidence` section.",
            "- The whole-file artifact SHA-256 is recorded in `dispatch-packet-hashes.json`.",
            "",
        ]
    )
    return payload.replace("## Review Prompt\n", f"{hash_section}## Review Prompt\n")


def _render_packet_payload(area: DispatchArea, commit: str, dirty: bool) -> str:
    internal_findings = _internal_finding_ids(area.review_docs)
    return "\n".join(
        [
            f"# {area.title}",
            "",
            "This is a focused v0.6 source-review dispatch packet for Ithildin. It is a",
            "review aid,",
            "not a source-review result and not a closure record.",
            "",
            "## Boundary",
            "",
            "- Runtime boundary: v0.1 local-preview.",
            f"- Reviewed commit candidate: `{commit}`.",
            f"- Dirty at generation: `{str(dirty).lower()}`.",
            "- No new governed tool powers are approved by this packet.",
            "- This packet does not prove production readiness, external-review closure,",
            "  public-preview",
            "  readiness, or capability-expansion approval.",
            "",
            "## Review Prompt",
            "",
            area.prompt,
            "",
            "## Closure Rows Covered",
            "",
            *[f"- {row}" for row in area.closure_rows],
            "",
            "## Source Files / Functions To Inspect",
            "",
            *[f"- `{source}`" for source in area.source_files],
            "",
            "## Review Documents",
            "",
            *[f"- [{doc}]({doc})" for doc in area.review_docs],
            "",
            *(
                [
                    "## Relevant Internal Findings",
                    "",
                    *[f"- {finding_id}" for finding_id in internal_findings],
                    "",
                ]
                if internal_findings
                else []
            ),
            "## Expected Commands",
            "",
            "Required minimum commands:",
            "",
            *[f"- `{command}`" for command in area.commands],
            "",
            "## Required Response Shape",
            "",
            "- reviewer identity and reviewer type;",
            "- source access level: source-level, packet-and-source, packet-only, or docs-only;",
            "- reviewed commit and dispatch packet hash;",
            f"- findings using the `{area.finding_namespace}` convention;",
            "- explicit blocker status for critical/high findings;",
            "- clear distinction between documentation risk and implementation risk.",
            "",
            "## Source Access Closure Rule",
            "",
            "- `source-level` or `packet-and-source` review may support implementation-row",
            "  closure.",
            "- `packet-only` review may support packet/documentation rows only.",
            "- `docs-only` review may support wording/navigation rows only.",
            "- Any closure based on less than source-level access must record the limitation.",
            "",
        ]
    )


def _internal_finding_ids(review_docs: tuple[str, ...]) -> list[str]:
    finding_ids: list[str] = []
    for doc in review_docs:
        name = Path(doc).name
        if not name.startswith("sub-"):
            continue
        parts = name.split("-", maxsplit=2)
        if len(parts) >= 2 and parts[1].isdigit():
            finding_ids.append(f"SUB-{parts[1]}")
    return finding_ids


def _render_index(commit: str, dirty: bool, packets: list[dict[str, Any]]) -> str:
    lines = [
        "# v0.6 External Review Dispatch Packet Index",
        "",
        f"- commit: `{commit}`",
        f"- dirty at generation: `{str(dirty).lower()}`",
        "- current review layer: v0.6 external-review execution dispatch.",
        "- historical note: some generated bundle paths still contain v0.2/v0.5 names; those are",
        "  archival/tooling names, not the current review status.",
        "- packet purpose: focused external/source review dispatch, not review closure.",
        "- what this does not prove: production readiness, external review closure, capability",
        "  expansion approval, broader public/security-product readiness.",
        "",
        "## Packets",
        "",
    ]
    lines.extend(
        f"- [{packet['path']}]({packet['path']}) `{packet['sha256']}` `{packet['bytes']} bytes`"
        for packet in packets
    )
    lines.append("")
    return "\n".join(lines)


def _artifact_metadata(path: Path, root: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
