"""Create a focused ERG-004 runtime descriptor-only response inbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_runtime_descriptor_only_source_review_bundle

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md"
)
DOC_NAME = "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md"
DEFAULT_OUTPUT_DIR = Path(
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox"
)
INDEX_NAME = "ERG004_RUNTIME_DESCRIPTOR_ONLY_RESPONSE_INBOX.md"
CHEATSHEET_NAME = "ERG004_RUNTIME_DESCRIPTOR_ONLY_CHEATSHEET.md"
JSON_NAME = "erg004-runtime-descriptor-only-response-inbox.json"
HASH_NAME = "erg004-runtime-descriptor-only-response-inbox-artifact-hashes.json"
RAW_NAME = "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md"
AREA = "sandbox-vm-live-poc-runtime-descriptor-only"
FINDING_NAMESPACE = "EXT-LIVE-DESC-###"
NORMALIZED_PATH = (
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only/"
    "normalized-response.json"
)
REVIEW_PACKET = (
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review"
)


class SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(RuntimeError):
    """Raised when the focused descriptor-only response inbox is invalid."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_inbox(ROOT, args.output_dir)
    except SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError as exc:
        print(f"ERG-004 runtime descriptor-only response inbox failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built ERG-004 runtime descriptor-only response inbox at {output_dir}")
    return 0


def build_inbox(repo_root: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    _validate_repo_root(repo_root)
    bundle_report = (
        sandbox_vm_live_poc_runtime_descriptor_only_source_review_bundle.build_check_report(
            repo_root
        )
    )
    if bundle_report.get("valid") is not True:
        raise SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(
            "runtime descriptor-only source-review bundle is not valid"
        )
    if bundle_report.get("runtime_changes_allowed") is not False:
        raise SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(
            "runtime descriptor-only source-review unexpectedly allows runtime changes"
        )
    if bundle_report.get("closes_erg_004") is not False:
        raise SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(
            "runtime descriptor-only source-review unexpectedly closes ERG-004"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = _payload(repo_root, output_dir)
    (output_dir / INDEX_NAME).write_text(_render_index(payload), encoding="utf-8")
    (output_dir / CHEATSHEET_NAME).write_text(
        _render_cheatsheet(payload), encoding="utf-8"
    )
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / RAW_NAME).write_text(_render_raw_placeholder(payload), encoding="utf-8")
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_inbox(repo_root, DEFAULT_OUTPUT_DIR)
    except SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    intake_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md"
    )
    dry_run_doc = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md"
    )
    matrix_doc = _read(repo_root / "docs/codex/enterprise-response-command-matrix.md")
    inbox_doc = _read(repo_root / DOC_REL)
    index_text = _read(output_dir / INDEX_NAME)
    cheatsheet_text = _read(output_dir / CHEATSHEET_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)
    raw_text = _read(output_dir / RAW_NAME)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    try:
        payload = json.loads(json_text) if json_text else {}
    except json.JSONDecodeError:
        payload = {}
        failures.append("ERG-004 runtime descriptor-only response inbox JSON is invalid")
    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("ERG-004 runtime descriptor-only hash manifest is invalid")

    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    expected_paths = {INDEX_NAME, CHEATSHEET_NAME, JSON_NAME, RAW_NAME}
    missing_hashes = sorted(expected_paths - hashed_paths)
    if missing_hashes:
        failures.append(
            "ERG-004 runtime descriptor-only inbox hash manifest is missing: "
            + ", ".join(missing_hashes)
        )
    if HASH_NAME in hashed_paths:
        failures.append("ERG-004 runtime descriptor-only hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("ERG-004 runtime descriptor-only artifact hashes do not match")

    for phrase in [
        "Status: generated response inbox for the active ERG-004 runtime descriptor-only review.",
        "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox",
        "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
        FINDING_NAMESPACE,
        AREA,
        RAW_NAME,
        "does not normalize responses",
        "does not record external review",
        "does not close `ERG-004`",
        "does not approve descriptor-only local preview disposition",
    ]:
        if phrase not in inbox_doc:
            failures.append(f"ERG-004 runtime descriptor-only inbox doc is missing: {phrase}")

    for phrase in [
        "ERG-004 Descriptor-Only Response Inbox",
        RAW_NAME,
        CHEATSHEET_NAME,
        FINDING_NAMESPACE,
        "uv run python scripts/external_response_normalize.py",
        "--area sandbox-vm-live-poc-runtime-descriptor-only",
        "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
        "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
        "runtime_changes_allowed: `false`",
        "closes_erg_004: `false`",
    ]:
        if phrase not in index_text:
            failures.append(f"generated ERG-004 runtime descriptor-only inbox is missing: {phrase}")
    for phrase in [
        "ERG-004 Descriptor-Only Cheat Sheet",
        RAW_NAME,
        "Reviewed packet hash:",
        "uv run python scripts/external_response_normalize.py",
        NORMALIZED_PATH,
        "does not normalize responses",
        "does not close `ERG-004`",
    ]:
        if phrase not in cheatsheet_text:
            failures.append(f"ERG-004 runtime descriptor-only cheat sheet is missing: {phrase}")
    for phrase in [
        '"inbox_type": "ithildin.erg004_runtime_descriptor_only_response_inbox"',
        '"gap": "ERG-004"',
        f'"normalization_area": "{AREA}"',
        '"normalizes_responses": false',
        '"external_review_recorded": false',
        '"closes_erg_004": false',
    ]:
        if phrase not in json_text:
            failures.append(f"ERG-004 runtime descriptor-only JSON is missing: {phrase}")
    for phrase in [
        "Paste the real EXT-LIVE-DESC reviewer response here.",
        "Finding namespace: EXT-LIVE-DESC-###",
        "Do not paste secrets, keys, prompts, model outputs, or file contents",
    ]:
        if phrase not in raw_text:
            failures.append(f"ERG-004 runtime descriptor-only raw placeholder is missing: {phrase}")

    if payload.get("gap") != "ERG-004":
        failures.append("ERG-004 runtime descriptor-only payload gap drifted")
    if payload.get("normalization_area") != AREA:
        failures.append("ERG-004 runtime descriptor-only normalization area drifted")
    if payload.get("finding_namespace") != FINDING_NAMESPACE:
        failures.append("ERG-004 runtime descriptor-only finding namespace drifted")
    if not str(payload.get("reviewed_packet_hash", "")).startswith("sha256:"):
        failures.append("ERG-004 runtime descriptor-only packet hash is missing")
    if payload.get("descriptor_only_source_disposition_allowed_now") is not False:
        failures.append(
            "ERG-004 runtime descriptor-only payload allows source disposition now"
        )
    if payload.get("runtime_changes_allowed") is not False:
        failures.append("ERG-004 runtime descriptor-only payload allows runtime changes")

    if "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox:" not in makefile:
        failures.append("Make target is missing: runtime descriptor-only response inbox")
    if "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check:" not in makefile:
        failures.append("Make target is missing: runtime descriptor-only response inbox check")
    if (
        "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check"
        not in release_check_body
        and (
            "release-check: sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check"
            not in makefile
        )
    ):
        failures.append("runtime descriptor-only response inbox check missing from release-check")
    if "$(MAKE) sandbox-vm-live-poc-runtime-descriptor-only-response-inbox" not in (
        review_candidate_body
    ):
        failures.append("runtime descriptor-only response inbox missing from review-candidate")
    if "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox" not in readme:
        failures.append("README is missing runtime descriptor-only response inbox command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime descriptor-only response inbox doc")
    if DOC_REL not in docs_site:
        failures.append("runtime descriptor-only response inbox missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime descriptor-only response inbox missing from review docs")
    if DOC_NAME not in review_index:
        failures.append("review docs index missing runtime descriptor-only response inbox")
    if "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check" not in (
        release_guardrails
    ):
        failures.append("release guardrails missing runtime descriptor-only response inbox")
    for label, content in [
        ("response intake", intake_doc),
        ("response dry run", dry_run_doc),
        ("enterprise response command matrix", matrix_doc),
    ]:
        if "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox" not in content:
            failures.append(f"{label} missing runtime descriptor-only response inbox pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "inbox_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "gap": "ERG-004",
        "tool_count": 24,
        "normalization_area": AREA,
        "finding_namespace": FINDING_NAMESPACE,
        "raw_response_file": RAW_NAME,
        "reviewed_packet_path": REVIEW_PACKET,
        "reviewed_packet_hash": payload.get("reviewed_packet_hash", ""),
        "normalizes_responses": False,
        "writes_response_files": False,
        "external_review_recorded": False,
        "mutates_findings": False,
        "closes_erg_004": False,
        "runtime_changes_allowed": False,
        "descriptor_only_source_disposition_allowed_now": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 runtime descriptor-only response inbox",
        f"valid: {str(report['valid']).lower()}",
        f"inbox_doc: {report['inbox_doc']}",
        f"output_dir: {report['output_dir']}",
        f"gap: {report['gap']}",
        f"tool_count: {report['tool_count']}",
        f"normalization_area: {report['normalization_area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"raw_response_file: {report['raw_response_file']}",
        f"reviewed_packet_path: {report['reviewed_packet_path']}",
        f"reviewed_packet_hash: {report['reviewed_packet_hash']}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "descriptor_only_source_disposition_allowed_now: "
        f"{str(report['descriptor_only_source_disposition_allowed_now']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _payload(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    raw_path = output_dir / RAW_NAME
    reviewed_packet_hash = _packet_hash(repo_root / REVIEW_PACKET)
    normalizer = (
        "uv run python scripts/external_response_normalize.py "
        f"{raw_path.as_posix()} "
        '--reviewer "REVIEWER NAME" '
        '--reviewer-type "ai_external" '
        "--source-access packet-and-source "
        '--reviewed-commit "$(git rev-parse HEAD)" '
        f'--reviewed-packet-hash "{reviewed_packet_hash}" '
        f"--area {AREA} "
        f"--output {NORMALIZED_PATH}"
    )
    return {
        "schema_version": "1",
        "inbox_type": "ithildin.erg004_runtime_descriptor_only_response_inbox",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "gap": "ERG-004",
        "status": "descriptor_only_runtime_implemented_source_review_pending",
        "output_dir": output_dir.as_posix(),
        "raw_response_path": raw_path.as_posix(),
        "raw_response_file": RAW_NAME,
        "normalization_area": AREA,
        "finding_namespace": FINDING_NAMESPACE,
        "reviewed_packet_path": REVIEW_PACKET,
        "reviewed_packet_hash": reviewed_packet_hash,
        "normalizer_command": normalizer,
        "normalized_response_path": NORMALIZED_PATH,
        "dry_run": "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
        "response_application_preflight": (
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check"
        ),
        "allowed_intake_outcomes": [
            "approve_descriptor_only_local_preview_disposition",
            "revise_before_descriptor_only_disposition",
            "block_descriptor_only_disposition",
        ],
        "blocked_boundaries": {
            "normalizes_responses": False,
            "writes_response_files": False,
            "external_review_recorded": False,
            "mutates_findings": False,
            "closes_erg_004": False,
            "runtime_changes_allowed": False,
            "descriptor_only_source_disposition_allowed_now": False,
            "live_vm_inspection_allowed": False,
            "vm_container_lifecycle_allowed": False,
            "sandbox_orchestration_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "trusted_host_promotion_allowed": False,
            "host_writes_allowed": False,
            "network_expansion_allowed": False,
            "api_mcp_profile_loading_allowed": False,
            "new_power_classes_allowed": False,
            "public_security_product_positioning_allowed": False,
        },
        "normalizes_responses": False,
        "writes_response_files": False,
        "external_review_recorded": False,
        "mutates_findings": False,
        "closes_erg_004": False,
        "runtime_changes_allowed": False,
        "descriptor_only_source_disposition_allowed_now": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "new_power_classes_allowed": False,
    }


def _render_index(payload: dict[str, Any]) -> str:
    return f"""# ERG-004 Descriptor-Only Response Inbox

Status: generated response inbox for the active ERG-004 runtime descriptor-only review.

This inbox gives the active `EXT-LIVE-DESC-###` review path an exact raw-response placeholder,
reviewed packet hash, and normalization command. It does not normalize responses, does not write
normalized response files, does not record external review, does not mutate findings, does not close
`ERG-004`, and does not approve descriptor-only local preview disposition.

- Tool count: `{payload['tool_count']}`
- Current ERG-004 status: `{payload['status']}`
- Raw response placeholder: `{payload['raw_response_path']}`
- Cheat sheet: `{CHEATSHEET_NAME}`
- Finding namespace: `{payload['finding_namespace']}`
- Normalization area: `{payload['normalization_area']}`
- Reviewed packet: `{payload['reviewed_packet_path']}`
- Reviewed packet hash: `{payload['reviewed_packet_hash']}`

## Operator Commands

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox
{payload['normalizer_command']}
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```

## Boundaries

- runtime_changes_allowed: `false`
- descriptor_only_source_disposition_allowed_now: `false`
- live_vm_inspection_allowed: `false`
- sandbox_orchestration_allowed: `false`
- mission_control_runtime_allowed: `false`
- local_model_invocation_allowed: `false`
- new_power_classes_allowed: `false`
- closes_erg_004: `false`
"""


def _render_cheatsheet(payload: dict[str, Any]) -> str:
    return f"""# ERG-004 Descriptor-Only Cheat Sheet

Paste a real `EXT-LIVE-DESC-###` reviewer response into:

```text
{payload['raw_response_path']}
```

Reviewed packet hash: `{payload['reviewed_packet_hash']}`

Normalize with:

```sh
{payload['normalizer_command']}
```

Then run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```

This cheat sheet does not normalize responses, does not close `ERG-004`, and does not approve
descriptor-only local preview disposition.
"""


def _render_raw_placeholder(payload: dict[str, Any]) -> str:
    return f"""# Raw ERG-004 Descriptor-Only Reviewer Response

Paste the real EXT-LIVE-DESC reviewer response here.

Finding namespace: {FINDING_NAMESPACE}
Reviewed packet: {payload['reviewed_packet_path']}
Reviewed packet hash: {payload['reviewed_packet_hash']}
Reviewed commit: {payload['commit']}

Do not paste secrets, keys, prompts, model outputs, or file contents into this placeholder.
Leave this placeholder text intact until a real reviewer response is available.
"""


def _packet_hash(path: Path) -> str:
    if not path.exists():
        raise SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(
            f"review packet path is missing: {path}"
        )
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    else:
        for child in sorted(path.rglob("*")):
            if child.is_file():
                digest.update(child.relative_to(path).as_posix().encode("utf-8"))
                digest.update(b"\0")
                digest.update(child.read_bytes())
                digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        artifacts.append(
            {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    return {
        "schema_version": "1",
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_manifest_self_hashed": False,
    }


def _artifact_hashes_match_files(output_dir: Path, hashes: dict[str, Any]) -> bool:
    for artifact in hashes.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != hashlib.sha256(data).hexdigest():
            return False
    return True


def _validate_repo_root(repo_root: Path) -> None:
    for marker in [
        Path("pyproject.toml"),
        Path("Makefile"),
        Path("apps/api"),
        Path("apps/mcp-server"),
        Path("tool-manifests.lock.json"),
    ]:
        if not (repo_root / marker).exists():
            raise SandboxVmLivePocRuntimeDescriptorOnlyResponseInboxError(
                f"not an Ithildin repo root; missing {marker}"
            )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
