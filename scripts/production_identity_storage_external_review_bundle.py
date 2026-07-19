"""Build a reviewer-friendly ERG-006/ERG-007 production identity/storage bundle."""

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
    production_identity_storage_disposition_closure_check,
    production_identity_storage_disposition_packet,
    production_identity_storage_external_response_intake_check,
    production_identity_storage_response_dry_run,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/production-identity-storage-external-review")
HASH_MANIFEST = "production-identity-storage-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_INDEX.md",
    "01_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_PROMPT.md",
    "02_PRODUCTION_IDENTITY_STORAGE_DISPOSITION_PACKET.md",
    "03_PRODUCTION_IDENTITY_STORAGE_ARCHITECTURE_CONTRACTS.md",
    "04_PRODUCTION_IDENTITY_STORAGE_RESPONSE_CLOSURE_DRY_RUN.md",
    "05_PRODUCTION_IDENTITY_STORAGE_REPRODUCTION_QUEUE_STATUS.md",
    "06_PRODUCTION_IDENTITY_STORAGE_BOUNDARY_EVIDENCE.md",
    "07_PRODUCTION_IDENTITY_STORAGE_COMMAND_EVIDENCE.md",
]


class ProductionIdentityStorageExternalReviewBundleError(RuntimeError):
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
    except ProductionIdentityStorageExternalReviewBundleError as exc:
        print(f"production identity/storage external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built production identity/storage external-review bundle at {output_dir}")
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
        output_dir = Path(tmp) / "production-identity-storage-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except ProductionIdentityStorageExternalReviewBundleError as exc:
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

    index = contents.get("00_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_INDEX.md", "")
    prompt = contents.get("01_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_PROMPT.md", "")
    response = contents.get("04_PRODUCTION_IDENTITY_STORAGE_RESPONSE_CLOSURE_DRY_RUN.md", "")
    reproduction = contents.get("05_PRODUCTION_IDENTITY_STORAGE_REPRODUCTION_QUEUE_STATUS.md", "")
    evidence = contents.get("07_PRODUCTION_IDENTITY_STORAGE_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Finding namespace: `EXT-PROD-IAM-STORAGE-###`",
        "Can `ERG-006` and `ERG-007` continue architecture planning",
        "Do not approve production identity",
        "Do not approve runtime Postgres",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "Tool count remains `24`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-006` or `ERG-007`",
        "does not approve production identity",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "production-identity-storage-external-response-intake.md",
        "production-identity-storage-disposition-closure-gate.md",
        "production-identity-storage-response-dry-run.md",
    ]:
        if phrase not in response:
            failures.append(f"response/closure/dry-run bundle is missing phrase: {phrase}")
    for phrase in [
        "enterprise-external-review-queue.md",
        "production-identity-storage-architecture.md",
        "production-identity-storage-source-review.md",
        "production-identity-storage-disposition-packet.md",
        "post-rc-decision-register.md",
    ]:
        if phrase not in reproduction:
            failures.append(f"reproduction/queue bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"production_identity_allowed": false',
        '"enterprise_rbac_allowed": false',
        '"tenant_team_authorization_allowed": false',
        '"remote_admin_allowed": false',
        '"runtime_postgres_allowed": false',
        '"database_migrations_allowed": false',
        '"backup_restore_runtime_allowed": false',
        '"retention_enforcement_allowed": false',
        '"hosted_control_plane_allowed": false',
        '"custody_grade_audit_claims_allowed": false',
        '"compliance_automation_allowed": false',
        '"siem_adapter_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_006": false',
        '"closes_erg_007": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "production-identity-storage-external-review-bundle"
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
    doc_rel = "docs/codex/production-identity-storage-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Production Identity And Storage External Review Bundle" not in review_index:
        failures.append("review-docs index is missing external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
    ]:
        if "production-identity-storage-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "recommended_next_review": "ERG-006/ERG-007",
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "tenant_team_authorization_allowed": False,
        "remote_admin_allowed": False,
        "runtime_postgres_allowed": False,
        "database_migrations_allowed": False,
        "backup_restore_runtime_allowed": False,
        "retention_enforcement_allowed": False,
        "hosted_control_plane_allowed": False,
        "custody_grade_audit_claims_allowed": False,
        "compliance_automation_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_006": False,
        "closes_erg_007": False,
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
        raise ProductionIdentityStorageExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        disposition_dir = tmp_root / "disposition"
        production_identity_storage_disposition_packet.build_packet(
            repo_root=repo_root,
            output_dir=disposition_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        command_reports = _build_command_reports(repo_root, run_commands=run_commands)

        files = {
            "00_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_INDEX.md": _index(
                commit, dirty
            ),
            "01_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_PROMPT.md": _prompt(
                commit
            ),
            "02_PRODUCTION_IDENTITY_STORAGE_DISPOSITION_PACKET.md": _packet_bundle(
                "Disposition Packet Contents", disposition_dir
            ),
            "03_PRODUCTION_IDENTITY_STORAGE_ARCHITECTURE_CONTRACTS.md": _docs_bundle(
                "Architecture Contracts And Decision Inputs",
                repo_root,
                [
                    "docs/codex/production-identity-storage-architecture.md",
                    "docs/codex/production-identity-storage-source-review.md",
                    "docs/codex/post-rc-decision-register.md",
                    "docs/codex/post-rc-decision-gate.md",
                    "docs/codex/accepted-risk-register.md",
                ],
            ),
            "04_PRODUCTION_IDENTITY_STORAGE_RESPONSE_CLOSURE_DRY_RUN.md": _docs_bundle(
                "Response Intake, Closure Gate, And Dry Run",
                repo_root,
                [
                    "docs/codex/production-identity-storage-external-response-intake.md",
                    "docs/codex/production-identity-storage-disposition-closure-gate.md",
                    "docs/codex/production-identity-storage-response-dry-run.md",
                ],
            ),
            "05_PRODUCTION_IDENTITY_STORAGE_REPRODUCTION_QUEUE_STATUS.md": _docs_bundle(
                "Reproduction And Queue Status",
                repo_root,
                [
                    "docs/codex/production-identity-storage-architecture.md",
                    "docs/codex/production-identity-storage-source-review.md",
                    "docs/codex/production-identity-storage-disposition-packet.md",
                    "docs/codex/enterprise-external-review-queue.md",
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/enterprise-readiness-runway.md",
                    "docs/codex/post-rc-decision-register.md",
                ],
            ),
            "06_PRODUCTION_IDENTITY_STORAGE_BOUNDARY_EVIDENCE.md": _docs_bundle(
                "Boundary Evidence And Non-Goals",
                repo_root,
                [
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/enterprise-readiness-runway.md",
                    "docs/codex/v1.0-rc-feature-freeze.md",
                    "docs/codex/v1.0-rc-readiness-gate.md",
                ],
            ),
            "07_PRODUCTION_IDENTITY_STORAGE_COMMAND_EVIDENCE.md": _command_evidence(
                command_reports
            ),
        }

    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Production Identity And Storage External Review Bundle

Status: reviewer launch bundle for `ERG-006` and `ERG-007`.

Reviewed commit: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Current `ERG-006` status before reviewer disposition: `planning_only`.
Current `ERG-007` status before reviewer disposition: `planning_only`.

Recommended next review: `ERG-006`/`ERG-007` production identity and durable storage architecture
disposition.

## Reading Order

1. `01_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_PROMPT.md`
2. `02_PRODUCTION_IDENTITY_STORAGE_DISPOSITION_PACKET.md`
3. `03_PRODUCTION_IDENTITY_STORAGE_ARCHITECTURE_CONTRACTS.md`
4. `04_PRODUCTION_IDENTITY_STORAGE_RESPONSE_CLOSURE_DRY_RUN.md`
5. `05_PRODUCTION_IDENTITY_STORAGE_REPRODUCTION_QUEUE_STATUS.md`
6. `06_PRODUCTION_IDENTITY_STORAGE_BOUNDARY_EVIDENCE.md`
7. `07_PRODUCTION_IDENTITY_STORAGE_COMMAND_EVIDENCE.md`
8. `production-identity-storage-external-review-artifact-hashes.json`

## What This Bundle Does Not Prove

This bundle does not prove that external review has happened, does not close `ERG-006` or `ERG-007`,
and does not approve production identity, enterprise RBAC, tenant/team authorization,
remote admin use, runtime Postgres, database migrations, backup/restore runtime behavior, retention
enforcement, hosted control plane, custody-grade audit claims, compliance automation, hosted
telemetry, remote MCP, SIEM adapter runtime behavior, sandbox orchestration, local model invocation,
trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, public/security-product positioning, or any new governed
tool power.

This bundle does not approve production identity or durable storage runtime behavior.
"""


def _prompt(commit: str) -> str:
    return f"""# Production Identity And Storage External Review Prompt

You are reviewing Ithildin as an external/source reviewer for `ERG-006` and `ERG-007` only: the
production identity and durable runtime storage architecture lane.

Reviewed commit: `{commit}`

Finding namespace: `EXT-PROD-IAM-STORAGE-###`

## Scope

Review the attached disposition packet, architecture contract, decision-register pointers, accepted
risk context, external response intake, closure gate, dry-run evidence, queue status, and command
evidence.

Please answer:

1. Did you inspect the production identity/storage disposition packet and architecture packet?
2. Are the identity provider, principal mapping, tenant/team/workspace, role, session, service
   principal, disabled-principal, and role-spoofing questions complete enough for continued
   architecture planning?
3. Are the runtime storage, SQLite migration, Postgres, transaction, backup/restore, retention,
   deletion, export, encryption, and failure-mode questions complete enough for continued
   architecture planning?
4. Are the secret-free evidence fields safe and useful for future audit attribution and incident
   reconstruction?
5. Does the lane preserve the current local-preview runtime boundary while keeping implementation
   planning and runtime implementation blocked?
6. Are there any critical/high findings?
7. Can `ERG-006` and `ERG-007` continue architecture planning while runtime implementation remains
   blocked?

Do not approve production identity. Do not approve runtime Postgres. Do not approve enterprise
RBAC. Do not approve tenant/team authorization runtime behavior. Do not approve remote admin use.
Do not approve database migrations. Do not approve backup/restore runtime behavior. Do not approve
retention enforcement. Do not approve hosted control plane. Do not approve custody-grade audit
claims. Do not approve compliance automation. Do not approve SIEM adapter runtime behavior. Do not
approve sandbox orchestration. Do not approve trusted-host promotion. Do not approve
public/security-product positioning.

Use this finding namespace for actionable findings: `EXT-PROD-IAM-STORAGE-###`.

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
        "disposition_packet_check": (
            production_identity_storage_disposition_packet.build_check_report(repo_root)
        ),
        "external_response_intake_check": (
            production_identity_storage_external_response_intake_check.build_report(repo_root)
        ),
        "closure_gate_check": production_identity_storage_disposition_closure_check.build_report(
            repo_root
        ),
        "response_dry_run": production_identity_storage_response_dry_run.run_dry_run(repo_root),
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
            raise ProductionIdentityStorageExternalReviewBundleError(
                f"command failed while building bundle: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "production-identity-storage-disposition-packet-check"],
        ["make", "production-identity-storage-external-response-intake-check"],
        ["make", "production-identity-storage-disposition-closure-check"],
        ["make", "production-identity-storage-response-dry-run"],
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
        raise ProductionIdentityStorageExternalReviewBundleError(
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
        "Ithildin production identity/storage external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_006_status: {report['erg_006_status']}",
        f"erg_007_status: {report['erg_007_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"enterprise_rbac_allowed: {str(report['enterprise_rbac_allowed']).lower()}",
        "tenant_team_authorization_allowed: "
        f"{str(report['tenant_team_authorization_allowed']).lower()}",
        f"remote_admin_allowed: {str(report['remote_admin_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"database_migrations_allowed: {str(report['database_migrations_allowed']).lower()}",
        "backup_restore_runtime_allowed: "
        f"{str(report['backup_restore_runtime_allowed']).lower()}",
        f"retention_enforcement_allowed: {str(report['retention_enforcement_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_006: {str(report['closes_erg_006']).lower()}",
        f"closes_erg_007: {str(report['closes_erg_007']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
