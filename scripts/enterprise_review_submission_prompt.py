"""Build operator paste prompts for the current enterprise review send set."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_review_send_manifest, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-submission-prompt.md"
DOC_NAME = "enterprise-review-submission-prompt.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-submission-prompt")
PROMPT_NAME = "ENTERPRISE_REVIEW_SUBMISSION_PROMPT.md"
JSON_NAME = "enterprise-review-submission-prompt.json"
HASH_NAME = "enterprise-review-submission-prompt-artifact-hashes.json"
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "live_vm_inspection_allowed": False,
    "local_model_invocation_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
    "new_power_classes_allowed": False,
}


class EnterpriseReviewSubmissionPromptError(RuntimeError):
    """Raised when the submission prompt cannot be built or validated."""


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
        output_dir = build_prompt(ROOT, args.output_dir)
    except EnterpriseReviewSubmissionPromptError as exc:
        print(f"enterprise review submission prompt failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review submission prompt at {output_dir}")
    return 0


def build_prompt(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_dir = enterprise_review_send_manifest.build_manifest(
        repo_root, enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR
    )
    manifest_payload = json.loads(
        (manifest_dir / enterprise_review_send_manifest.JSON_NAME).read_text(
            encoding="utf-8"
        )
    )
    payload = _prompt_payload(repo_root=repo_root, manifest_payload=manifest_payload)

    (output_dir / PROMPT_NAME).write_text(_render_prompt(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_prompt(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSubmissionPromptError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    send_manifest_doc = _read(repo_root / "docs/codex/enterprise-review-send-manifest.md")
    outbox_doc = _read(repo_root / "docs/codex/enterprise-dual-review-outbox.md")
    submission_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    prompt_text = _read(output_dir / PROMPT_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise review submission prompt hashes are not valid JSON")
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}

    for phrase in [
        "Status: generated operator paste prompt for current enterprise external-review packets.",
        "make enterprise-review-submission-prompt",
        "make enterprise-review-submission-prompt-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not record external review",
        "does not close either lane",
    ]:
        if phrase not in submission_doc:
            failures.append(f"submission prompt doc is missing phrase: {phrase}")
    for phrase in [
        "Enterprise Review Submission Prompt",
        "Use separate review threads",
        "Response intake after review",
        "ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
        "make enterprise-dual-response-inbox",
        "ERG-003",
        "ERG-002",
        "Finding namespace",
        "Attach every file",
        "records_external_review: `false`",
        "closes_erg_003: `false`",
        "closes_erg_002: `false`",
        "Do not approve runtime implementation",
    ]:
        if phrase not in prompt_text:
            failures.append(f"generated submission prompt is missing phrase: {phrase}")
    for phrase in [
        '"prompt_type": "ithildin.enterprise_review_submission_prompt"',
        '"recommended_gaps": [',
        '"ERG-003"',
        '"ERG-002"',
        '"response_inbox": {',
        '"cheat_sheet"',
        '"make enterprise-dual-response-inbox"',
        '"records_external_review": false',
        '"normalizes_responses": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
    ]:
        if phrase not in json_text:
            failures.append(f"submission prompt JSON is missing phrase: {phrase}")

    expected_artifacts = {PROMPT_NAME, JSON_NAME}
    missing_artifacts = sorted(expected_artifacts - hashed_paths)
    if missing_artifacts:
        failures.append(
            "submission prompt hash manifest is missing artifacts: "
            + ", ".join(missing_artifacts)
        )
    if HASH_NAME in hashed_paths:
        failures.append("submission prompt hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("submission prompt artifact hashes do not match files")

    required_wiring = {
        "Make target": "enterprise-review-submission-prompt:",
        "Check target": "enterprise-review-submission-prompt-check:",
        "Release check": "enterprise-review-submission-prompt-check",
        "Review candidate": "$(MAKE) enterprise-review-submission-prompt",
        "README command": "make enterprise-review-submission-prompt",
        "Send manifest pointer": "enterprise-review-submission-prompt",
        "Outbox pointer": "enterprise-review-submission-prompt",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-review-submission-prompt-check",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-submission-prompt")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-submission-prompt-check")
    if required_wiring["Release check"] not in release_check_body:
        failures.append("enterprise-review-submission-prompt-check is missing from release-check")
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-review-submission-prompt is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise review submission prompt command")
    if required_wiring["Send manifest pointer"] not in send_manifest_doc:
        failures.append("enterprise review send manifest doc is missing submission prompt pointer")
    if required_wiring["Outbox pointer"] not in outbox_doc:
        failures.append("enterprise dual-review outbox doc is missing submission prompt pointer")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise review submission prompt is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise review submission prompt is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise review submission prompt")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise review submission prompt")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "submission_prompt_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(
            output_dir, hash_manifest
        ),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review submission prompt check",
        f"valid: {str(report['valid']).lower()}",
        f"submission_prompt_doc: {report['submission_prompt_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _prompt_payload(*, repo_root: Path, manifest_payload: dict[str, Any]) -> dict[str, Any]:
    send_set = []
    for packet in manifest_payload["send_set"]:
        send_set.append(
            {
                "gap": packet["gap"],
                "name": packet["name"],
                "finding_namespace": packet["finding_namespace"],
                "attachment_dir": f"{manifest_payload['outbox_dir']}/{packet['outbox_dir']}",
                "prompt_file": f"{manifest_payload['outbox_dir']}/{packet['prompt']}",
                "copied_file_count": packet["copied_file_count"],
                "response_kit": packet["response_kit"],
                "dry_run": packet["dry_run"],
                "closure_gate": packet["closure_gate"],
            }
        )
    return {
        "schema_version": "1",
        "prompt_type": "ithildin.enterprise_review_submission_prompt",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "send_set": send_set,
        "source_manifest": {
            "path": (
                "var/review-packets/v3/enterprise-review-send-manifest/"
                "enterprise-review-send-manifest.json"
            ),
            "outbox_hash_manifest": manifest_payload["outbox_hash_manifest"]["path"],
        },
        "response_inbox": {
            "command": "make enterprise-dual-response-inbox",
            "check_command": "make enterprise-dual-response-inbox-check",
            "path": "var/review-runs/enterprise-dual-response-inbox",
            "cheat_sheet": (
                "var/review-runs/enterprise-dual-response-inbox/"
                "ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md"
            ),
        },
        "blocked_boundaries": BOUNDARY_FLAGS,
    }


def _render_prompt(payload: dict[str, Any]) -> str:
    sections = "\n\n".join(_render_lane(packet) for packet in payload["send_set"])
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Review Submission Prompt

Status: generated operator paste prompt for current enterprise external-review packets.

Reviewed commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Use separate review threads

Send each lane as a separate review request. Attach every file in that lane's attachment directory.
Do not merge `ERG-003` and `ERG-002` into one reviewer answer unless the reviewer explicitly
returns separate findings, namespaces, and dispositions for each lane.

{sections}

## Response intake after review

After reviewer responses arrive, build the ignored local response inbox:

```sh
{payload['response_inbox']['command']}
{payload['response_inbox']['check_command']}
```

Then open:

```text
{payload['response_inbox']['cheat_sheet']}
```

Paste each unmodified reviewer response into the matching raw-response placeholder named in that
cheat sheet, then run the lane-specific normalization, dry-run, and closure-gate commands from the
cheat sheet. The response inbox remains an ignored local review-run artifact.

## Boundary

Do not approve runtime implementation, Mission Control runtime behavior, live VM/container
inspection, local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapters,
compliance automation, public/security-product positioning, new governed tool powers, production
identity, runtime Postgres, hosted telemetry, or remote MCP.

{blocked}

This prompt does not record external review, does not normalize responses, and does not close
either lane. The response inbox and cheat sheet only make the post-response handling path explicit.
"""


def _render_lane(packet: dict[str, Any]) -> str:
    return f"""## {packet['gap']}: {packet['name']}

Attachment directory:

```text
{packet['attachment_dir']}
```

Attach every file in that directory. Expected file count: `{packet['copied_file_count']}`.

Paste the reviewer prompt from:

```text
{packet['prompt_file']}
```

Finding namespace: `{packet['finding_namespace']}`

After response:

```sh
{packet['dry_run']}
{packet['closure_gate']}
```

Response kit: `{packet['response_kit']}`
"""


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewSubmissionPromptError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        artifacts.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
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


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())
