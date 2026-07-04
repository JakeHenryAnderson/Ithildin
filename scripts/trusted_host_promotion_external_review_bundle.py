"""Build a reviewer-friendly ERG-005 trusted-host promotion launch bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_external_review_queue_check,
    trusted_host_promotion_disposition_closure_check,
    trusted_host_promotion_disposition_packet,
    trusted_host_promotion_external_response_intake_check,
    trusted_host_promotion_response_dry_run,
    trusted_host_promotion_source_review_packet,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/trusted-host-promotion-external-review")
HASH_MANIFEST = "trusted-host-promotion-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_INDEX.md",
    "01_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_PROMPT.md",
    "02_TRUSTED_HOST_PROMOTION_SOURCE_PACKET.md",
    "03_TRUSTED_HOST_PROMOTION_DISPOSITION_PACKET.md",
    "04_TRUSTED_HOST_PROMOTION_CONTRACTS.md",
    "05_TRUSTED_HOST_PROMOTION_FIXTURES_NEGATIVES.md",
    "06_TRUSTED_HOST_PROMOTION_RESPONSE_CLOSURE_DRY_RUN.md",
    "07_TRUSTED_HOST_PROMOTION_REPRODUCTION_QUEUE_STATUS.md",
    "08_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md",
]


class TrustedHostPromotionExternalReviewBundleError(RuntimeError):
    """Raised when the launch bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd().resolve())
            print(render_check_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except TrustedHostPromotionExternalReviewBundleError as exc:
        print(f"trusted-host promotion external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built trusted-host promotion external-review bundle at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "trusted-host-promotion-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except TrustedHostPromotionExternalReviewBundleError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8") for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append("external-review bundle missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")

    prompt = contents.get("01_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_PROMPT.md", "")
    index = contents.get("00_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_INDEX.md", "")
    evidence = contents.get("08_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md", "")
    response = contents.get("06_TRUSTED_HOST_PROMOTION_RESPONSE_CLOSURE_DRY_RUN.md", "")
    reproduction = contents.get("07_TRUSTED_HOST_PROMOTION_REPRODUCTION_QUEUE_STATUS.md", "")

    for phrase in [
        "Finding namespace: `EXT-TRUSTED-HOST-###`",
        "Can `ERG-005` continue design-only planning",
        "Do not approve trusted-host promotion",
        "Do not approve direct host writes",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "Tool count remains `24`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-005`",
        "does not approve trusted-host promotion",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "trusted-host-promotion-external-response-intake.md",
        "trusted-host-promotion-disposition-closure-gate.md",
        "trusted-host-promotion-response-dry-run.md",
    ]:
        if phrase not in response:
            failures.append(f"response/closure/dry-run bundle is missing phrase: {phrase}")
    for phrase in [
        "enterprise-external-review-queue.md",
        "trusted-host-promotion-source-review.md",
        "trusted-host-promotion-disposition-packet.md",
        "post-rc-decision-register.md",
    ]:
        if phrase not in reproduction:
            failures.append(f"reproduction/queue bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"direct_host_writes_allowed": false',
        '"overwrite_delete_move_allowed": false',
        '"automatic_promotion_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"siem_adapter_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_005": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "trusted-host-promotion-external-review-bundle"
    check_target = f"{target}-check"
    for make_target in [f"{target}:", f"{check_target}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    if check_target not in release_check_body and f"release-check: {check_target}" not in makefile:
        failures.append(f"{check_target} missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(f"{target} missing from review-candidate")
    if check_target not in release_guardrails:
        failures.append(f"release guardrails do not require {check_target}")
    if f"$(MAKE) {target}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {target}")
    doc_rel = "docs/codex/trusted-host-promotion-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Trusted-Host Promotion External Review Bundle" not in review_index:
        failures.append("review-docs index is missing external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
    ]:
        if "trusted-host-promotion-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_005_status": "blocked",
        "recommended_next_review": "ERG-005",
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "promotion_without_hash_binding_allowed": False,
        "promotion_without_approval_evidence_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_005": False,
    }


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise TrustedHostPromotionExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        source_dir = tmp_root / "source-review"
        disposition_dir = tmp_root / "disposition"
        trusted_host_promotion_source_review_packet.build_packet(
            repo_root=repo_root,
            output_dir=source_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        trusted_host_promotion_disposition_packet.build_packet(
            repo_root=repo_root,
            output_dir=disposition_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        command_reports = _build_command_reports(repo_root, run_commands=run_commands)

        files = {
            "00_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_INDEX.md": _index(commit, dirty),
            "01_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_PROMPT.md": _prompt(commit),
            "02_TRUSTED_HOST_PROMOTION_SOURCE_PACKET.md": _packet_bundle(
                "Source Review Packet Contents", source_dir
            ),
            "03_TRUSTED_HOST_PROMOTION_DISPOSITION_PACKET.md": _packet_bundle(
                "Disposition Packet Contents", disposition_dir
            ),
            "04_TRUSTED_HOST_PROMOTION_CONTRACTS.md": _docs_bundle(
                "Promotion Contracts And State Model",
                repo_root,
                [
                    "docs/codex/sandbox-promotion-evidence-contract.md",
                    "docs/codex/trusted-host-descriptor-contract.md",
                    "docs/codex/trusted-host-promotion-decision-intake.md",
                    "docs/codex/trusted-host-promotion-state-machine.md",
                    "docs/codex/trusted-host-promotion-zone-contract.md",
                    "docs/codex/trusted-host-promotion-implementation-plan.md",
                    "docs/codex/trusted-host-promotion-source-review.md",
                    "docs/codex/v3-trusted-host-promotion-internal-review.md",
                ],
            ),
            "05_TRUSTED_HOST_PROMOTION_FIXTURES_NEGATIVES.md": _docs_bundle(
                "Fixtures, Negative Cases, And Observed Sandbox Evidence",
                repo_root,
                [
                    "docs/codex/trusted-host-promotion-negative-fixtures.md",
                    "docs/codex/sandbox-artifact-observed-demo.md",
                    "docs/codex/hello-world-sandbox-observed-demo.md",
                    "docs/codex/hello-world-mission-control-handoff.md",
                ],
            ),
            "06_TRUSTED_HOST_PROMOTION_RESPONSE_CLOSURE_DRY_RUN.md": _docs_bundle(
                "Response Intake, Closure Gate, And Dry Run",
                repo_root,
                [
                    "docs/codex/trusted-host-promotion-external-response-intake.md",
                    "docs/codex/trusted-host-promotion-disposition-closure-gate.md",
                    "docs/codex/trusted-host-promotion-response-dry-run.md",
                ],
            ),
            "07_TRUSTED_HOST_PROMOTION_REPRODUCTION_QUEUE_STATUS.md": _docs_bundle(
                "Reproduction And Queue Status",
                repo_root,
                [
                    "docs/codex/trusted-host-promotion-source-review.md",
                    "docs/codex/trusted-host-promotion-disposition-packet.md",
                    "docs/codex/enterprise-external-review-queue.md",
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/enterprise-readiness-runway.md",
                    "docs/codex/post-rc-decision-register.md",
                ],
            ),
            "08_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md": _command_evidence(
                command_reports
            ),
        }

    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Trusted-Host Promotion External Review Bundle

Status: reviewer launch bundle for `ERG-005`.

Reviewed commit: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Current `ERG-005` status before reviewer disposition: `blocked`.

Recommended next review: `ERG-005` trusted-host promotion design-only disposition.

## Reading Order

1. `01_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_PROMPT.md`
2. `02_TRUSTED_HOST_PROMOTION_SOURCE_PACKET.md`
3. `03_TRUSTED_HOST_PROMOTION_DISPOSITION_PACKET.md`
4. `04_TRUSTED_HOST_PROMOTION_CONTRACTS.md`
5. `05_TRUSTED_HOST_PROMOTION_FIXTURES_NEGATIVES.md`
6. `06_TRUSTED_HOST_PROMOTION_RESPONSE_CLOSURE_DRY_RUN.md`
7. `07_TRUSTED_HOST_PROMOTION_REPRODUCTION_QUEUE_STATUS.md`
8. `08_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md`
9. `trusted-host-promotion-external-review-artifact-hashes.json`

## What This Bundle Does Not Prove

This bundle does not prove that external review has happened, does not close `ERG-005`, and does
not approve trusted-host promotion, direct host writes, overwrite/delete/move behavior, broad
archive extraction, automatic promotion, Mission Control runtime behavior, local model invocation,
VM/container lifecycle management, sandbox orchestration, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, public/security-product
positioning, or any new governed tool power.

This bundle does not approve trusted-host promotion.
"""


def _prompt(commit: str) -> str:
    return f"""# Trusted-Host Promotion External Review Prompt

You are reviewing Ithildin as an external/source reviewer for `ERG-005` only: the trusted-host
promotion design-only lane.

Reviewed commit: `{commit}`

Finding namespace: `EXT-TRUSTED-HOST-###`

## Scope

Review the attached source-review packet, disposition packet, descriptor contract, promotion
contracts, state machine, zone contract, implementation-plan skeleton, negative fixtures, observed
sandbox evidence pointers, external response intake, closure gate, dry-run evidence, queue status,
and command evidence.

Please answer:

1. Did you inspect the trusted-host promotion source packet and disposition packet?
2. Are source/staging/approved/evidence zone labels precise enough and non-authoritative?
3. Does the trusted host descriptor contract keep host posture evidence operator-reviewed,
   secret-free, descriptor-only, and unable to authorize host control?
4. Does the implementation-plan skeleton require exact artifact hash binding, approval binding,
   one-time scope evidence, policy/manifest evidence, conflict handling, stale evidence denial,
   replay denial, and path-escape denial before any future implementation could be considered?
5. Are the negative fixtures strong enough for unsafe labels, path escape, overwrite/delete/move,
   automatic promotion, broad archive extraction, sensitive payloads, and product-boundary
   overclaims?
6. Does the lane preserve Ithildin as the only policy, approval, execution, and audit authority?
7. Are there any critical/high findings?
8. Can `ERG-005` continue design-only planning while runtime implementation remains blocked?

Do not approve trusted-host promotion. Do not approve direct host writes. Do not approve
overwrite/delete/move behavior. Do not approve broad archive extraction. Do not approve automatic
promotion. Do not approve Mission Control runtime behavior. Do not approve local model invocation.
Do not approve sandbox orchestration. Do not approve SIEM adapters. Do not approve
public/security-product positioning.

Use this finding namespace for actionable findings: `EXT-TRUSTED-HOST-###`.

For each finding, include severity, area, affected files/functions, blocking status, disposition,
and recommended fix.
"""


def _packet_bundle(title: str, packet_dir: Path) -> str:
    parts = [f"# {title}\n"]
    for path in sorted(packet_dir.iterdir()):
        if path.suffix.lower() not in {".md", ".json"}:
            continue
        content = path.read_text(encoding="utf-8")
        parts.append(f"\n## {path.name}\n\n```{_fence_lang(path)}\n{content}\n```\n")
    return "".join(parts)


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel in rel_paths:
        path = repo_root / rel
        content = path.read_text(encoding="utf-8")
        parts.append(f"\n## {rel}\n\n```{_fence_lang(path)}\n{content}\n```\n")
    return "".join(parts)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> dict[str, Any]:
    reports: dict[str, Any] = {
        "source_review_packet_check": (
            trusted_host_promotion_source_review_packet.build_check_report(repo_root)
        ),
        "disposition_packet_check": trusted_host_promotion_disposition_packet.build_check_report(
            repo_root
        ),
        "external_response_intake_check": (
            trusted_host_promotion_external_response_intake_check.build_report(repo_root)
        ),
        "closure_gate_check": trusted_host_promotion_disposition_closure_check.build_report(
            repo_root
        ),
        "response_dry_run": trusted_host_promotion_response_dry_run.run_dry_run(repo_root),
        "enterprise_external_review_queue_check": (
            enterprise_external_review_queue_check.build_report(repo_root)
        ),
    }
    reports["shell_commands"] = (
        _run_shell_commands(repo_root)
        if run_commands
        else [
            {
                "command": " ".join(command),
                "returncode": 0,
                "stdout_tail": "command execution skipped for fixture/test packet generation",
                "stderr_tail": "",
            }
            for command in _shell_commands()
        ]
    )
    return reports


def _command_evidence(reports: dict[str, Any]) -> str:
    payload = json.dumps(reports, indent=2, sort_keys=True)
    return f"# Command Evidence\n\n```json\n{payload}\n```\n"


def _run_shell_commands(repo_root: Path) -> list[dict[str, Any]]:
    commands = _shell_commands()
    results: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        results.append(
            {
                "command": " ".join(command),
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-2000:],
            }
        )
        if completed.returncode != 0:
            raise TrustedHostPromotionExternalReviewBundleError(
                f"command failed while building bundle: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "trusted-host-promotion-source-review-packet-check"],
        ["make", "trusted-host-promotion-disposition-packet-check"],
        ["make", "trusted-host-promotion-external-response-intake-check"],
        ["make", "trusted-host-promotion-disposition-closure-check"],
        ["make", "trusted-host-promotion-response-dry-run"],
        ["make", "enterprise-external-review-queue-check"],
        ["make", "no-new-powers-guardrail"],
        ["make", "tool-surface-invariant-gate"],
    ]


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    (output_dir / HASH_MANIFEST).write_text(
        json.dumps({"artifacts": artifacts}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise TrustedHostPromotionExternalReviewBundleError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _fence_lang(path: Path) -> str:
    return "json" if path.suffix.lower() == ".json" else "markdown"


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "promotion_without_hash_binding_allowed: "
        f"{str(report['promotion_without_hash_binding_allowed']).lower()}",
        "promotion_without_approval_evidence_allowed: "
        f"{str(report['promotion_without_approval_evidence_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
