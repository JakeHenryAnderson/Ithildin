"""Build a reviewer-friendly ERG-010 public/security-product positioning bundle."""

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
    docs_claims_public_preview_disposition_closure_check,
    enterprise_external_review_queue_check,
    public_security_product_positioning_decision_closure_check,
    public_security_product_positioning_decision_intake_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/public-positioning-external-review")
HASH_MANIFEST = "public-positioning-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_PUBLIC_POSITIONING_EXTERNAL_REVIEW_INDEX.md",
    "01_PUBLIC_POSITIONING_EXTERNAL_REVIEW_PROMPT.md",
    "02_PUBLIC_POSITIONING_DECISION_INTAKE.md",
    "03_PUBLIC_POSITIONING_CLOSURE_GATES.md",
    "04_PUBLIC_POSITIONING_CLAIM_EVIDENCE.md",
    "05_PUBLIC_POSITIONING_REPRODUCTION_QUEUE_STATUS.md",
    "06_PUBLIC_POSITIONING_BOUNDARY_EVIDENCE.md",
    "07_PUBLIC_POSITIONING_COMMAND_EVIDENCE.md",
]


class PublicPositioningExternalReviewBundleError(RuntimeError):
    """Raised when the external-review bundle cannot be built."""


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
    except PublicPositioningExternalReviewBundleError as exc:
        print(f"public positioning external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built public positioning external-review bundle at {output_dir}")
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
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "public-positioning-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except PublicPositioningExternalReviewBundleError as exc:
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

    index = contents.get("00_PUBLIC_POSITIONING_EXTERNAL_REVIEW_INDEX.md", "")
    prompt = contents.get("01_PUBLIC_POSITIONING_EXTERNAL_REVIEW_PROMPT.md", "")
    closure = contents.get("03_PUBLIC_POSITIONING_CLOSURE_GATES.md", "")
    evidence = contents.get("07_PUBLIC_POSITIONING_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Finding namespace: `EXT-PUBLIC-POSITIONING-###`",
        "Can `ERG-010` remain blocked while claim-decision drafting is prepared",
        "Do not approve public/security-product positioning",
        "Do not approve production/security/compliance positioning",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "Tool count remains `24`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-010`",
        "does not approve public/security-product positioning",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "public-security-product-positioning-decision-closure-gate.md",
        "docs-claims-public-preview-disposition-closure-gate.md",
    ]:
        if phrase not in closure:
            failures.append(f"closure bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"public_security_product_positioning_allowed": false',
        '"production_security_compliance_positioning_allowed": false',
        '"claim_decision_record_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_010": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "public-positioning-external-review-bundle"
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
    doc_rel = "docs/codex/public-positioning-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Public Positioning External Review Bundle" not in review_index:
        failures.append("review-docs index is missing external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
    ]:
        if "public-positioning-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_010_status": "blocked",
        "recommended_next_review": "ERG-010",
        "runtime_changes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "production_security_compliance_positioning_allowed": False,
        "claim_decision_record_allowed": False,
        "new_power_classes_allowed": False,
        "new_tool_powers_allowed": False,
        "closes_erg_010": False,
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
        raise PublicPositioningExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_PUBLIC_POSITIONING_EXTERNAL_REVIEW_INDEX.md": _index(commit, dirty),
        "01_PUBLIC_POSITIONING_EXTERNAL_REVIEW_PROMPT.md": _prompt(commit),
        "02_PUBLIC_POSITIONING_DECISION_INTAKE.md": _docs_bundle(
            "Decision Intake",
            repo_root,
            ["docs/codex/public-security-product-positioning-decision-intake.md"],
        ),
        "03_PUBLIC_POSITIONING_CLOSURE_GATES.md": _docs_bundle(
            "Closure Gates",
            repo_root,
            [
                "docs/codex/public-security-product-positioning-decision-closure-gate.md",
                "docs/codex/docs-claims-public-preview-disposition-closure-gate.md",
            ],
        ),
        "04_PUBLIC_POSITIONING_CLAIM_EVIDENCE.md": _docs_bundle(
            "Claim Evidence And Current Decisions",
            repo_root,
            [
                "docs/codex/v0.8-public-preview-risk-review.md",
                "docs/codex/v0.8-final-decision-packet.md",
                "docs/codex/v1.0-rc-final-handoff.md",
                "docs/codex/v1.0-rc-readiness-gate.md",
                "docs/codex/v1.0-assurance-closure.md",
                "docs/codex/accepted-risk-register.md",
            ],
        ),
        "05_PUBLIC_POSITIONING_REPRODUCTION_QUEUE_STATUS.md": _docs_bundle(
            "Reproduction And Queue Status",
            repo_root,
            [
                "docs/codex/enterprise-external-review-queue.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
                "docs/codex/enterprise-readiness-runway.md",
                "docs/codex/post-rc-decision-register.md",
            ],
        ),
        "06_PUBLIC_POSITIONING_BOUNDARY_EVIDENCE.md": _docs_bundle(
            "Boundary Evidence And Non-Goals",
            repo_root,
            [
                "docs/codex/v1.0-rc-feature-freeze.md",
                "docs/codex/v1.0-rc-external-review-prompt.md",
                "docs/codex/public-security-product-positioning-decision-intake.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
            ],
        ),
        "07_PUBLIC_POSITIONING_COMMAND_EVIDENCE.md": _command_evidence(command_reports),
    }

    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Public Positioning External Review Bundle

Status: reviewer launch bundle for blocked `ERG-010`.

Reviewed commit: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Current `ERG-010` status before reviewer disposition: `blocked`.

Recommended next review: `ERG-010` public/security-product positioning claim boundary review.

## Reading Order

1. `01_PUBLIC_POSITIONING_EXTERNAL_REVIEW_PROMPT.md`
2. `02_PUBLIC_POSITIONING_DECISION_INTAKE.md`
3. `03_PUBLIC_POSITIONING_CLOSURE_GATES.md`
4. `04_PUBLIC_POSITIONING_CLAIM_EVIDENCE.md`
5. `05_PUBLIC_POSITIONING_REPRODUCTION_QUEUE_STATUS.md`
6. `06_PUBLIC_POSITIONING_BOUNDARY_EVIDENCE.md`
7. `07_PUBLIC_POSITIONING_COMMAND_EVIDENCE.md`
8. `public-positioning-external-review-artifact-hashes.json`

## What This Bundle Does Not Prove

This bundle does not prove that external review has happened, does not close `ERG-010`, and does not
approve public/security-product positioning, production/security/compliance positioning, broader
public distribution, production deployment readiness, sandbox claims, EDR/MDM claims, SIEM custody
claims, compliance claims, compliance automation, legal advice, automated certification,
regulatory-grade audit claims, custody-grade audit claims, tamper-proof logging, audit immutability
claims, production identity, enterprise RBAC, runtime Postgres, hosted telemetry, hosted MCP,
remote MCP, managed model serving, support/deployment/update/incident-response claims, sandbox
orchestration, local model invocation, trusted-host promotion, SIEM adapter behavior, compliance
mapping runtime behavior, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, or any new governed tool power.

This bundle does not approve public/security-product positioning.
"""


def _prompt(commit: str) -> str:
    return f"""# Public/Security-Product Positioning External Review Prompt

You are reviewing Ithildin as an external/source reviewer for `ERG-010` only: the
public/security-product positioning and claim-boundary lane.

Reviewed commit: `{commit}`

Finding namespace: `EXT-PUBLIC-POSITIONING-###`

## Scope

Review the attached decision intake, closure gates, current public-preview decision evidence,
v1.0 RC readiness evidence, assurance closure, accepted-risk posture, enterprise queue status, and
command evidence.

Please answer:

1. Did you inspect the public/security-product positioning intake and closure gates?
2. Are the current no-go decisions for public/security-product positioning and
   production/security/compliance positioning clear and enforceable?
3. Are the required preconditions for any future claim-specific decision record complete enough?
4. Are the forbidden claim categories and allowed local-preview wording complete enough?
5. Are accepted risks, pending external-review rows, production identity/storage, SIEM, compliance
   mapping, sandbox, trusted-host promotion, support/deployment, and evidence custody dependencies
   represented without overclaiming?
6. Are there any critical/high findings?
7. Can `ERG-010` remain blocked while claim-decision drafting is prepared for future review?

Do not approve public/security-product positioning.
Do not approve production/security/compliance positioning.
Do not approve broader public distribution. Do not approve production deployment
readiness. Do not approve sandbox guarantee language. Do not approve EDR/MDM claims. Do not approve
SIEM custody claims. Do not approve compliance claims. Do not approve compliance automation. Do not
approve legal advice. Do not approve automated certification. Do not approve production identity.
Do not approve runtime Postgres. Do not approve hosted telemetry. Do not approve remote MCP. Do not
approve sandbox orchestration. Do not approve trusted-host promotion. Do not approve new governed
tool powers.

Use this finding namespace for actionable findings: `EXT-PUBLIC-POSITIONING-###`.

For each finding, include severity, area, affected files/functions, blocking status, disposition,
and recommended fix.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel in rel_paths:
        path = repo_root / rel
        content = path.read_text(encoding="utf-8")
        parts.append(f"\n## {rel}\n\n```markdown\n{content}\n```\n")
    return "".join(parts)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> dict[str, Any]:
    reports: dict[str, Any] = {
        "bundle_boundary": {
            "runtime_changes_allowed": False,
            "public_security_product_positioning_allowed": False,
            "production_security_compliance_positioning_allowed": False,
            "claim_decision_record_allowed": False,
            "new_power_classes_allowed": False,
            "new_tool_powers_allowed": False,
            "closes_erg_010": False,
        },
        "decision_intake_check": (
            public_security_product_positioning_decision_intake_check.build_report(
                repo_root
            )
        ),
        "decision_closure_check": (
            public_security_product_positioning_decision_closure_check.build_report(repo_root)
        ),
        "docs_claims_closure_check": (
            docs_claims_public_preview_disposition_closure_check.build_report(repo_root)
        ),
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
    results: list[dict[str, Any]] = []
    for command in _shell_commands():
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
            raise PublicPositioningExternalReviewBundleError(
                f"command failed while building bundle: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "public-security-product-positioning-decision-intake-check"],
        ["make", "public-security-product-positioning-decision-closure-check"],
        ["make", "docs-claims-public-preview-disposition-closure-check"],
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
        raise PublicPositioningExternalReviewBundleError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin public positioning external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_010_status: {report['erg_010_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "production_security_compliance_positioning_allowed: "
        f"{str(report['production_security_compliance_positioning_allowed']).lower()}",
        f"claim_decision_record_allowed: {str(report['claim_decision_record_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"new_tool_powers_allowed: {str(report['new_tool_powers_allowed']).lower()}",
        f"closes_erg_010: {str(report['closes_erg_010']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
