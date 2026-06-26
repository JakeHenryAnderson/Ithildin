"""Build a reviewer-response kit for the planning-only compliance mapping lane."""

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
    compliance_mapping_disposition_closure_check,
    compliance_mapping_external_response_intake_check,
    compliance_mapping_response_dry_run,
    enterprise_external_review_queue_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/compliance-mapping-response-kit")
HASH_MANIFEST = "compliance-mapping-response-kit-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_COMPLIANCE_MAPPING_RESPONSE_KIT_INDEX.md",
    "01_COMPLIANCE_MAPPING_RESPONSE_INTAKE_GUIDE.md",
    "02_COMPLIANCE_MAPPING_NORMALIZED_RESPONSE_EXAMPLES.md",
    "03_COMPLIANCE_MAPPING_CLOSURE_TRIAGE_COMMANDS.md",
    "04_COMPLIANCE_MAPPING_QUEUE_AND_BOUNDARY_STATUS.md",
    "05_COMPLIANCE_MAPPING_RESPONSE_KIT_EVIDENCE.md",
]


class ComplianceMappingResponseKitError(RuntimeError):
    """Raised when the compliance mapping response kit cannot be built."""


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
        output_dir = build_kit(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except ComplianceMappingResponseKitError as exc:
        print(f"compliance mapping response kit failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built compliance mapping response kit at {output_dir}")
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
        output_dir = Path(tmp) / "compliance-mapping-response-kit"
        try:
            build_kit(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except ComplianceMappingResponseKitError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            artifact_hashes_match_files = False
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            artifact_hashes_match_files = _artifact_hashes_match_files(
                output_dir=output_dir,
                hashes=hashes,
            )
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8") for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append("response kit missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if not artifact_hashes_match_files:
        failures.append("artifact hashes do not match generated markdown files")

    index = contents.get("00_COMPLIANCE_MAPPING_RESPONSE_KIT_INDEX.md", "")
    guide = contents.get("01_COMPLIANCE_MAPPING_RESPONSE_INTAKE_GUIDE.md", "")
    examples = contents.get("02_COMPLIANCE_MAPPING_NORMALIZED_RESPONSE_EXAMPLES.md", "")
    commands = contents.get("03_COMPLIANCE_MAPPING_CLOSURE_TRIAGE_COMMANDS.md", "")
    boundary = contents.get("04_COMPLIANCE_MAPPING_QUEUE_AND_BOUNDARY_STATUS.md", "")
    evidence = contents.get("05_COMPLIANCE_MAPPING_RESPONSE_KIT_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "What This Kit Does Not Prove",
        "does not close `ERG-009`",
        "does not approve compliance mapping runtime behavior",
        "does not approve implementation planning",
    ]:
        if phrase not in index:
            failures.append(f"response kit index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-COMPLIANCE-MAPPING-###`",
        "var/review-runs/compliance-mapping/normalized-response.json",
        "compliance-mapping-external-response-intake.md",
        "Only a later committed triage update may move `ERG-009`",
    ]:
        if phrase not in guide:
            failures.append(f"response intake guide is missing phrase: {phrase}")
    for phrase in [
        '"response_type": "ithildin.external_review.normalized_response"',
        '"area": "compliance-mapping"',
        '"source_access": "source-level"',
        '"source_access": "packet-only"',
        '"disposition_outcome": "continue_architecture_planning"',
        '"closes_external_review": false',
    ]:
        if phrase not in examples:
            failures.append(f"normalized response examples are missing phrase: {phrase}")
    for phrase in [
        "make compliance-mapping-disposition-closure-check",
        "make compliance-mapping-response-dry-run",
        "make compliance-mapping-external-response-intake-check",
        "make review-run-manifest-refresh",
        "make release-check",
        "make review-candidate",
    ]:
        if phrase not in commands:
            failures.append(f"closure/triage commands are missing phrase: {phrase}")
    for phrase in [
        "`ERG-009`",
        "compliance mapping runtime behavior",
        "compliance automation",
        "legal advice",
        "automated certification",
        "regulated-industry compliance claims",
        "custody-grade audit claims",
    ]:
        if phrase not in boundary:
            failures.append(f"boundary status is missing phrase: {phrase}")
    for phrase in [
        '"response_kit_boundary"',
        '"runtime_changes_allowed": false',
        '"implementation_planning_allowed": false',
        '"compliance_mapping_runtime_allowed": false',
        '"compliance_automation_allowed": false',
        '"legal_advice_allowed": false',
        '"automated_certification_allowed": false',
        '"regulated_industry_compliance_claims_allowed": false',
        '"custody_grade_audit_claims_allowed": false',
        '"production_identity_allowed": false',
        '"runtime_postgres_allowed": false',
        '"erg_009_closed": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"response kit evidence is missing phrase: {phrase}")

    target = "compliance-mapping-response-kit"
    check_target = f"{target}-check"
    for make_target in [f"{target}:", f"{check_target}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    release_check_additive = f"release-check: {check_target}"
    if check_target not in release_check_body and release_check_additive not in makefile:
        failures.append(f"{check_target} missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(f"{target} missing from review-candidate")
    if check_target not in release_guardrails:
        failures.append(f"release guardrails do not require {check_target}")
    if f"$(MAKE) {target}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {target}")
    doc_rel = "docs/codex/compliance-mapping-response-kit.md"
    if doc_rel not in docs_site:
        failures.append("response kit doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("response kit doc is missing from review docs")
    if "Compliance Mapping Response Kit" not in review_index:
        failures.append(
            "review-docs index is missing compliance mapping response kit entry"
        )
    if f"make {target}" not in readme:
        failures.append("README is missing compliance mapping response kit command")
    for text, source in [
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
    ]:
        if "compliance-mapping-response-kit" not in text:
            failures.append(f"{source} is missing compliance mapping response kit pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "tool_count": 24,
        "erg_009_status": "planning_only",
        "recommended_next_review": "ERG-009",
        "runtime_changes_allowed": False,
        "implementation_planning_allowed": False,
        "architecture_planning_after_favorable_disposition_allowed": True,
        "compliance_mapping_runtime_allowed": False,
        "compliance_automation_allowed": False,
        "legal_advice_allowed": False,
        "automated_certification_allowed": False,
        "regulated_industry_compliance_claims_allowed": False,
        "custody_grade_audit_claims_allowed": False,
        "external_notarization_allowed": False,
        "immutable_storage_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "siem_adapter_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "hosted_control_plane_allowed": False,
        "remote_mcp_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "new_power_classes_allowed": False,
        "erg_009_closed": False,
    }


def build_kit(
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
        raise ComplianceMappingResponseKitError(
            "working tree is dirty; commit before compliance mapping response-kit handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_COMPLIANCE_MAPPING_RESPONSE_KIT_INDEX.md": _index(commit, dirty),
        "01_COMPLIANCE_MAPPING_RESPONSE_INTAKE_GUIDE.md": _intake_guide(),
        "02_COMPLIANCE_MAPPING_NORMALIZED_RESPONSE_EXAMPLES.md": _examples(),
        "03_COMPLIANCE_MAPPING_CLOSURE_TRIAGE_COMMANDS.md": _commands(),
        "04_COMPLIANCE_MAPPING_QUEUE_AND_BOUNDARY_STATUS.md": _docs_bundle(
            "Queue And Boundary Status",
            repo_root,
            [
                "docs/codex/enterprise-external-review-queue.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
                "docs/codex/compliance-mapping-disposition-packet.md",
                "docs/codex/compliance-mapping-disposition-closure-gate.md",
                "docs/codex/compliance-mapping-response-dry-run.md",
                "docs/codex/post-rc-decision-register.md",
            ],
        ),
        "05_COMPLIANCE_MAPPING_RESPONSE_KIT_EVIDENCE.md": _command_evidence(
            command_reports
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    boundary = (
        "This response kit does not prove external review happened, does not close `ERG-009`, "
        "does not approve implementation planning, and does not approve compliance mapping runtime "
        "behavior. It does not approve compliance automation, legal advice, automated "
        "certification, regulated-industry compliance claims, custody-grade audit claims, external "
        "notarization, immutable storage, production identity, runtime Postgres, SIEM adapter "
        "behavior, hosted telemetry, remote delivery, sandbox orchestration, local model "
        "invocation, trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, "
        "arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, "
        "or public/security-product positioning."
    )
    return f"""# Compliance Mapping Response Kit

Status: response-intake kit for planning-only `ERG-009` after external/source
disposition review.

Reviewed commit for kit generation: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-009` status: `planning_only`.

## Reading Order

1. `01_COMPLIANCE_MAPPING_RESPONSE_INTAKE_GUIDE.md`
2. `02_COMPLIANCE_MAPPING_NORMALIZED_RESPONSE_EXAMPLES.md`
3. `03_COMPLIANCE_MAPPING_CLOSURE_TRIAGE_COMMANDS.md`
4. `04_COMPLIANCE_MAPPING_QUEUE_AND_BOUNDARY_STATUS.md`
5. `05_COMPLIANCE_MAPPING_RESPONSE_KIT_EVIDENCE.md`
6. `compliance-mapping-response-kit-artifact-hashes.json`

## What This Kit Does Not Prove

{boundary}
"""


def _intake_guide() -> str:
    return """# Response Intake Guide

Finding namespace: `EXT-COMPLIANCE-MAPPING-###`

Reviewed area for normalization: `compliance-mapping`

Response target:

```text
var/review-runs/compliance-mapping/normalized-response.json
```

Start from:

- `compliance-mapping-external-response-intake.md`
- `compliance-mapping-disposition-closure-gate.md`
- `compliance-mapping-response-dry-run.md`
- `compliance-mapping-disposition-packet.md`
- `compliance-mapping-external-review-bundle.md`
- `compliance-mapping-architecture.md`

Only a later committed triage update may move `ERG-009`, and only after the closure
gate reports `closure_ready: true`. A favorable normalized response may support continued
architecture planning. It must not approve implementation planning, runtime implementation,
compliance mapping runtime behavior, compliance automation, legal advice, automated certification,
regulated-industry compliance claims, custody-grade audit claims, SIEM adapter behavior, Mission
Control runtime behavior, local model invocation, or sandbox orchestration.
"""


def _examples() -> str:
    favorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "compliance-mapping",
        "source_access": "source-level",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": True,
        "mutates_findings": False,
        "closes_external_review": False,
        "disposition_outcome": "continue_architecture_planning",
        "findings": [],
    }
    unfavorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "compliance-mapping",
        "source_access": "packet-only",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": False,
        "mutates_findings": False,
        "closes_external_review": False,
        "disposition_outcome": "block_runtime_implementation",
        "findings": [
            {
                "finding_id": "EXT-COMPLIANCE-MAPPING-001",
                "severity": "high",
                "area": "compliance-mapping",
                "affected_files_functions": (
                    "docs/codex/compliance-mapping-architecture.md"
                ),
                "blocking_status": "blocking",
                "disposition": "open",
                "recommended_fix": "example unfavorable response",
            }
        ],
    }
    return (
        "# Normalized Response Examples\n\n"
        "These are shape examples only. Replace reviewer, packet, hash, and finding values with "
        "real evidence before using the response path.\n\n"
        "## Favorable Shape\n\n"
        "```json\n"
        f"{json.dumps(favorable, indent=2, sort_keys=True)}\n"
        "```\n\n"
        "## Unfavorable Shape\n\n"
        "```json\n"
        f"{json.dumps(unfavorable, indent=2, sort_keys=True)}\n"
        "```\n"
    )


def _commands() -> str:
    return """# Closure And Triage Commands

Run these commands after placing real normalized response evidence under the ignored response path:

```sh
make compliance-mapping-external-response-intake-check
make compliance-mapping-disposition-closure-check
make compliance-mapping-response-dry-run
make compliance-mapping-disposition-packet-check
make compliance-mapping-external-review-bundle-check
make enterprise-external-review-queue-check
```

If and only if the closure gate reports `closure_ready: true`, perform a separate committed triage
update while keeping runtime compliance mapping behavior blocked, then run:

```sh
make review-run-manifest-refresh
make release-check
make review-candidate
```

If the response is absent, malformed, packet-only, docs-only, missing the allowed disposition
outcome, critical/high, or attempts to close external review directly, keep `ERG-009` as
`planning_only`.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel in rel_paths:
        content = (repo_root / rel).read_text(encoding="utf-8")
        parts.append(f"\n## {rel}\n\n```markdown\n{content}\n```\n")
    return "".join(parts)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> dict[str, Any]:
    reports: dict[str, Any] = {
        "response_kit_boundary": {
            "runtime_changes_allowed": False,
            "implementation_planning_allowed": False,
            "architecture_planning_after_favorable_disposition_allowed": True,
            "compliance_mapping_runtime_allowed": False,
            "compliance_automation_allowed": False,
            "legal_advice_allowed": False,
            "automated_certification_allowed": False,
            "regulated_industry_compliance_claims_allowed": False,
            "custody_grade_audit_claims_allowed": False,
            "external_notarization_allowed": False,
            "immutable_storage_allowed": False,
            "production_identity_allowed": False,
            "runtime_postgres_allowed": False,
            "siem_adapter_allowed": False,
            "hosted_telemetry_allowed": False,
            "remote_delivery_allowed": False,
            "hosted_control_plane_allowed": False,
            "remote_mcp_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "sandbox_orchestration_allowed": False,
            "new_power_classes_allowed": False,
            "erg_009_closed": False,
        },
        "external_response_intake_check": (
            compliance_mapping_external_response_intake_check.build_report(repo_root)
        ),
        "disposition_closure_check": (
            compliance_mapping_disposition_closure_check.build_report(repo_root)
        ),
        "response_dry_run": compliance_mapping_response_dry_run.run_dry_run(repo_root),
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
    return f"# Response Kit Evidence\n\n```json\n{payload}\n```\n"


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
            raise ComplianceMappingResponseKitError(
                f"command failed while building response kit: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "compliance-mapping-external-response-intake-check"],
        ["make", "compliance-mapping-disposition-closure-check"],
        ["make", "compliance-mapping-response-dry-run"],
        ["make", "compliance-mapping-disposition-packet-check"],
        ["make", "compliance-mapping-external-review-bundle-check"],
        ["make", "enterprise-external-review-queue-check"],
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


def _artifact_hashes_match_files(*, output_dir: Path, hashes: dict[str, Any]) -> bool:
    artifacts = hashes.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for entry in artifacts:
        if not isinstance(entry, dict):
            return False
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(path, str):
            return False
        if not isinstance(sha256, str) or not sha256.startswith("sha256:"):
            return False
        if not isinstance(byte_count, int) or byte_count <= 0:
            return False
        artifact_path = output_dir / path
        if not artifact_path.exists() or not artifact_path.is_file():
            return False
        data = artifact_path.read_bytes()
        if sha256 != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
        if byte_count != len(data):
            return False
    return True


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise ComplianceMappingResponseKitError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin compliance mapping response kit check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_009_status: {report['erg_009_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        "architecture_planning_after_favorable_disposition_allowed: "
        f"{str(report['architecture_planning_after_favorable_disposition_allowed']).lower()}",
        "compliance_mapping_runtime_allowed: "
        f"{str(report['compliance_mapping_runtime_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"legal_advice_allowed: {str(report['legal_advice_allowed']).lower()}",
        "automated_certification_allowed: "
        f"{str(report['automated_certification_allowed']).lower()}",
        "regulated_industry_compliance_claims_allowed: "
        f"{str(report['regulated_industry_compliance_claims_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        f"external_notarization_allowed: {str(report['external_notarization_allowed']).lower()}",
        f"immutable_storage_allowed: {str(report['immutable_storage_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"erg_009_closed: {str(report['erg_009_closed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
