"""Build a reviewer-response kit for the blocked public-positioning lane."""

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
)

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/public-security-product-positioning-response-kit"
)
HASH_MANIFEST = "public-security-product-positioning-response-kit-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_INDEX.md",
    "01_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_INTAKE_GUIDE.md",
    "02_PUBLIC_SECURITY_PRODUCT_POSITIONING_NORMALIZED_RESPONSE_EXAMPLES.md",
    "03_PUBLIC_SECURITY_PRODUCT_POSITIONING_CLOSURE_TRIAGE_COMMANDS.md",
    "04_PUBLIC_SECURITY_PRODUCT_POSITIONING_QUEUE_AND_BOUNDARY_STATUS.md",
    "05_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_EVIDENCE.md",
]


class PublicSecurityProductPositioningResponseKitError(RuntimeError):
    """Raised when the public-positioning response kit cannot be built."""


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
    except PublicSecurityProductPositioningResponseKitError as exc:
        print(f"public positioning response kit failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built public positioning response kit at {output_dir}")
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
        output_dir = Path(tmp) / "public-security-product-positioning-response-kit"
        try:
            build_kit(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except PublicSecurityProductPositioningResponseKitError as exc:
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
        failures.append("response kit missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")

    index = contents.get("00_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_INDEX.md", "")
    guide = contents.get("01_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_INTAKE_GUIDE.md", "")
    examples = contents.get(
        "02_PUBLIC_SECURITY_PRODUCT_POSITIONING_NORMALIZED_RESPONSE_EXAMPLES.md", ""
    )
    commands = contents.get("03_PUBLIC_SECURITY_PRODUCT_POSITIONING_CLOSURE_TRIAGE_COMMANDS.md", "")
    boundary = contents.get(
        "04_PUBLIC_SECURITY_PRODUCT_POSITIONING_QUEUE_AND_BOUNDARY_STATUS.md", ""
    )
    evidence = contents.get("05_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "What This Kit Does Not Prove",
        "does not close `ERG-010`",
        "does not approve public/security-product positioning",
        "does not approve a claim-decision record",
    ]:
        if phrase not in index:
            failures.append(f"response kit index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-PUBLIC-POSITIONING-###`",
        "var/review-runs/public-security-product-positioning/normalized-response.json",
        "public-security-product-positioning-decision-intake.md",
        "Only a later committed claim-decision record may move `ERG-010`",
    ]:
        if phrase not in guide:
            failures.append(f"response intake guide is missing phrase: {phrase}")
    for phrase in [
        '"response_type": "ithildin.external_review.normalized_response"',
        '"area": "public-security-product-positioning"',
        '"source_access": "source-level"',
        '"source_access": "packet-only"',
        '"disposition_outcome": "ready_for_claim_decision_record"',
        '"closes_external_review": false',
    ]:
        if phrase not in examples:
            failures.append(f"normalized response examples are missing phrase: {phrase}")
    for phrase in [
        "make public-security-product-positioning-decision-closure-check",
        "make public-positioning-external-review-bundle-check",
        "make docs-claims-public-preview-disposition-closure-check",
        "make review-run-manifest-refresh",
        "make release-check",
        "make review-candidate",
    ]:
        if phrase not in commands:
            failures.append(f"closure/triage commands are missing phrase: {phrase}")
    for phrase in [
        "`ERG-010`",
        "public/security-product positioning",
        "production/security/compliance positioning",
        "sandbox guarantee language",
        "EDR/MDM claims",
        "SIEM custody claims",
        "compliance claims",
        "trusted-host promotion",
        "new governed tool powers",
    ]:
        if phrase not in boundary:
            failures.append(f"boundary status is missing phrase: {phrase}")
    for phrase in [
        '"response_kit_boundary"',
        '"runtime_changes_allowed": false',
        '"claim_decision_record_allowed": false',
        '"public_security_product_positioning_allowed": false',
        '"production_security_compliance_positioning_allowed": false',
        '"broader_public_distribution_allowed": false',
        '"sandbox_claims_allowed": false',
        '"edr_mdm_claims_allowed": false',
        '"siem_custody_claims_allowed": false',
        '"compliance_claims_allowed": false',
        '"production_identity_allowed": false',
        '"runtime_postgres_allowed": false',
        '"remote_mcp_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"new_power_classes_allowed": false',
        '"erg_010_closed": false',
        '"decision_closure_check"',
        '"closure_ready": false',
    ]:
        if phrase not in evidence:
            failures.append(f"response kit evidence is missing phrase: {phrase}")

    target = "public-security-product-positioning-response-kit"
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
    doc_rel = "docs/codex/public-security-product-positioning-response-kit.md"
    if doc_rel not in docs_site:
        failures.append("response kit doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("response kit doc is missing from review docs")
    if "Public Security Product Positioning Response Kit" not in review_index:
        failures.append("review-docs index is missing public positioning response kit entry")
    if f"make {target}" not in readme:
        failures.append("README is missing public positioning response kit command")
    for text, source in [
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
    ]:
        if "public-security-product-positioning-response-kit" not in text:
            failures.append(f"{source} is missing public positioning response kit pointer")

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
        "claim_decision_record_allowed": False,
        "public_security_product_positioning_allowed": False,
        "production_security_compliance_positioning_allowed": False,
        "broader_public_distribution_allowed": False,
        "production_deployment_ready_wording_allowed": False,
        "sandbox_claims_allowed": False,
        "edr_mdm_claims_allowed": False,
        "siem_custody_claims_allowed": False,
        "compliance_claims_allowed": False,
        "compliance_automation_allowed": False,
        "legal_advice_allowed": False,
        "automated_certification_allowed": False,
        "regulatory_grade_audit_claims_allowed": False,
        "custody_grade_audit_claims_allowed": False,
        "tamper_proof_logging_claims_allowed": False,
        "audit_immutability_claims_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "hosted_mcp_allowed": False,
        "remote_mcp_allowed": False,
        "managed_model_serving_allowed": False,
        "support_deployment_incident_claims_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_mapping_runtime_allowed": False,
        "new_power_classes_allowed": False,
        "new_tool_powers_allowed": False,
        "erg_010_closed": False,
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
        raise PublicSecurityProductPositioningResponseKitError(
            "working tree is dirty; commit before public positioning response-kit handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_INDEX.md": _index(commit, dirty),
        "01_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_INTAKE_GUIDE.md": _intake_guide(),
        "02_PUBLIC_SECURITY_PRODUCT_POSITIONING_NORMALIZED_RESPONSE_EXAMPLES.md": _examples(),
        "03_PUBLIC_SECURITY_PRODUCT_POSITIONING_CLOSURE_TRIAGE_COMMANDS.md": _commands(),
        "04_PUBLIC_SECURITY_PRODUCT_POSITIONING_QUEUE_AND_BOUNDARY_STATUS.md": _docs_bundle(
            "Queue And Boundary Status",
            repo_root,
            [
                "docs/codex/enterprise-external-review-queue.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
                "docs/codex/public-security-product-positioning-decision-intake.md",
                "docs/codex/public-security-product-positioning-decision-closure-gate.md",
                "docs/codex/public-positioning-external-review-bundle.md",
                "docs/codex/docs-claims-public-preview-disposition-closure-gate.md",
                "docs/codex/post-rc-decision-register.md",
            ],
        ),
        "05_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_EVIDENCE.md": _command_evidence(
            command_reports
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    boundary = (
        "This response kit does not prove external review happened, does not close `ERG-010`, "
        "does not approve a claim-decision record, and does not approve public/security-product "
        "positioning. It does not approve production/security/compliance positioning, broader "
        "public distribution, production deployment readiness, sandbox guarantee language, "
        "EDR/MDM claims, SIEM custody claims, compliance claims, compliance automation, legal "
        "advice, automated certification, regulatory-grade audit claims, custody-grade audit "
        "claims, tamper-proof logging, audit immutability claims, production identity, enterprise "
        "RBAC, runtime Postgres, hosted telemetry, hosted MCP, remote MCP, managed model serving, "
        "support/deployment/update/incident-response claims, sandbox orchestration, local model "
        "invocation, trusted-host promotion, SIEM adapter behavior, compliance mapping runtime "
        "behavior, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad "
        "filesystem writes, plugin SDK behavior, or new governed tool powers."
    )
    return f"""# Public Security Product Positioning Response Kit

Status: response-intake kit for blocked `ERG-010` after public/security-product claim review.

Reviewed commit for kit generation: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-010` status: `blocked`.

## Reading Order

1. `01_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_INTAKE_GUIDE.md`
2. `02_PUBLIC_SECURITY_PRODUCT_POSITIONING_NORMALIZED_RESPONSE_EXAMPLES.md`
3. `03_PUBLIC_SECURITY_PRODUCT_POSITIONING_CLOSURE_TRIAGE_COMMANDS.md`
4. `04_PUBLIC_SECURITY_PRODUCT_POSITIONING_QUEUE_AND_BOUNDARY_STATUS.md`
5. `05_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_EVIDENCE.md`
6. `public-security-product-positioning-response-kit-artifact-hashes.json`

## What This Kit Does Not Prove

{boundary}
"""


def _intake_guide() -> str:
    return """# Response Intake Guide

Finding namespace: `EXT-PUBLIC-POSITIONING-###`

Reviewed area for normalization: `public-security-product-positioning`

Response target:

```text
var/review-runs/public-security-product-positioning/normalized-response.json
```

Start from:

- `public-security-product-positioning-decision-intake.md`
- `public-security-product-positioning-decision-closure-gate.md`
- `public-positioning-external-review-bundle.md`
- `docs-claims-public-preview-disposition-closure-gate.md`
- `enterprise-external-review-queue.md`
- `enterprise-readiness-gap-matrix.md`

Only a later committed claim-decision record may move `ERG-010`, and only after the closure gate
reports `closure_ready: true`. A favorable normalized response may support preparing that separate
record. It must not approve public/security-product positioning, production/security/compliance
positioning, broader public distribution, production deployment readiness, sandbox guarantee
language, EDR/MDM claims, SIEM custody claims, compliance claims, compliance automation, legal
advice, automated certification, production identity, runtime Postgres, hosted telemetry, remote
MCP, sandbox orchestration, trusted-host promotion, compliance mapping runtime behavior, or new
governed tool powers.
"""


def _examples() -> str:
    favorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "public-security-product-positioning",
        "source_access": "source-level",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": True,
        "mutates_findings": False,
        "closes_external_review": False,
        "disposition_outcome": "ready_for_claim_decision_record",
        "findings": [],
    }
    unfavorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "public-security-product-positioning",
        "source_access": "packet-only",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": False,
        "mutates_findings": False,
        "closes_external_review": False,
        "disposition_outcome": "keep_public_positioning_blocked",
        "findings": [
            {
                "finding_id": "EXT-PUBLIC-POSITIONING-001",
                "severity": "high",
                "area": "public-security-product-positioning",
                "affected_files_functions": (
                    "docs/codex/public-security-product-positioning-decision-intake.md"
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
make public-security-product-positioning-decision-closure-check
make public-positioning-external-review-bundle-check
make docs-claims-public-preview-disposition-closure-check
make enterprise-external-review-queue-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

If and only if the closure gate reports `closure_ready: true`, perform a separate committed
claim-decision record while keeping public/security-product positioning blocked until that record is
reviewed and accepted, then run:

```sh
make review-run-manifest-refresh
make release-check
make review-candidate
```

If the response is absent, malformed, docs-only, packet-only, missing the allowed disposition
outcome, critical/high, or attempts to close external review directly, keep `ERG-010` as `blocked`.
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
            "claim_decision_record_allowed": False,
            "public_security_product_positioning_allowed": False,
            "production_security_compliance_positioning_allowed": False,
            "broader_public_distribution_allowed": False,
            "production_deployment_ready_wording_allowed": False,
            "sandbox_claims_allowed": False,
            "edr_mdm_claims_allowed": False,
            "siem_custody_claims_allowed": False,
            "compliance_claims_allowed": False,
            "compliance_automation_allowed": False,
            "legal_advice_allowed": False,
            "automated_certification_allowed": False,
            "regulatory_grade_audit_claims_allowed": False,
            "custody_grade_audit_claims_allowed": False,
            "tamper_proof_logging_claims_allowed": False,
            "audit_immutability_claims_allowed": False,
            "production_identity_allowed": False,
            "enterprise_rbac_allowed": False,
            "runtime_postgres_allowed": False,
            "hosted_telemetry_allowed": False,
            "hosted_mcp_allowed": False,
            "remote_mcp_allowed": False,
            "managed_model_serving_allowed": False,
            "support_deployment_incident_claims_allowed": False,
            "sandbox_orchestration_allowed": False,
            "local_model_invocation_allowed": False,
            "trusted_host_promotion_allowed": False,
            "siem_adapter_allowed": False,
            "compliance_mapping_runtime_allowed": False,
            "new_power_classes_allowed": False,
            "new_tool_powers_allowed": False,
            "erg_010_closed": False,
        },
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
            raise PublicSecurityProductPositioningResponseKitError(
                f"command failed while building kit: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "public-security-product-positioning-decision-closure-check"],
        ["make", "public-positioning-external-review-bundle-check"],
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
        raise PublicSecurityProductPositioningResponseKitError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin public/security-product positioning response kit check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_010_status: {report['erg_010_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"claim_decision_record_allowed: {str(report['claim_decision_record_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "production_security_compliance_positioning_allowed: "
        f"{str(report['production_security_compliance_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"new_tool_powers_allowed: {str(report['new_tool_powers_allowed']).lower()}",
        f"erg_010_closed: {str(report['erg_010_closed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
