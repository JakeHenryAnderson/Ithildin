"""Generate the governed artifact transfer lab packet through Stage 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/governed-artifact-transfer-lab")
FIXTURE = Path("tests/fixtures/governed_artifact_transfer/article.txt")
HASH_MANIFEST = "artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
BOUNDARIES = [
    "stage_1_part_2_mission_control_metadata_only",
    "stage_2_simulated_sandbox_only",
    "no_service_startup",
    "no_governed_tool_calls",
    "no_new_governed_tools",
    "no_shell_execution",
    "no_external_network",
    "no_broad_filesystem_writes",
    "no_production_security_claims",
]


class GovernedArtifactTransferLabError(RuntimeError):
    """Raised when the governed artifact transfer lab cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = build_lab(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            fixture=args.fixture,
            allow_dirty=args.allow_dirty,
        )
    except GovernedArtifactTransferLabError as exc:
        print(f"governed artifact transfer lab failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built governed artifact transfer lab at {output_dir}")
    return 0


def build_lab(
    *,
    repo_root: Path,
    output_dir: Path,
    fixture: Path = FIXTURE,
    allow_dirty: bool = False,
) -> Path:
    _require_project_root(repo_root)
    fixture_path = _resolve_fixture(repo_root, fixture)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise GovernedArtifactTransferLabError(
            "working tree is dirty; commit before governed artifact transfer handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    staging_dir = output_dir / "staging"
    evidence_dir = output_dir / "evidence"
    mission_control_dir = output_dir / "mission-control-handoff"
    simulated_sandbox_dir = output_dir / "simulated-sandbox"
    host_source_dir = simulated_sandbox_dir / "host-source"
    sandbox_working_dir = simulated_sandbox_dir / "sandbox-working-copy"
    sandbox_output_dir = simulated_sandbox_dir / "sandbox-output"
    host_staging_dir = simulated_sandbox_dir / "host-staging"
    staging_dir.mkdir()
    evidence_dir.mkdir()
    mission_control_dir.mkdir()
    host_source_dir.mkdir(parents=True)
    sandbox_working_dir.mkdir(parents=True)
    sandbox_output_dir.mkdir(parents=True)
    host_staging_dir.mkdir(parents=True)

    source_text = fixture_path.read_text(encoding="utf-8")
    summary = _summarize(source_text)
    summary_path = staging_dir / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    source_hash = _sha256(fixture_path)
    summary_hash = _sha256(summary_path)
    manifest = {
        "schema_version": "1",
        "lab": "governed-artifact-transfer-stage-1-part-1",
        "status": "ithildin_only_known_good",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 23,
        "mission_control_integration": False,
        "vm_or_sandbox": False,
        "service_startup_performed": False,
        "governed_tool_calls_performed": False,
        "promotion_required_for_trusted_write": True,
        "source": {
            "path_label": "fixture://governed-artifact-transfer/article.txt",
            "sha256": source_hash,
            "bytes": fixture_path.stat().st_size,
        },
        "output": {
            "path_label": "staging/summary.md",
            "sha256": summary_hash,
            "bytes": summary_path.stat().st_size,
        },
        "evidence_sources": [
            "source_hash",
            "output_hash",
            "deterministic_summary_transcript",
            "lab_manifest",
            "artifact_hash_manifest",
        ],
        "boundaries": BOUNDARIES,
        "next_stage": "Stage 1 Part 2 may attach Mission Control mission/evidence metadata.",
    }
    _write_json(evidence_dir / "manifest.json", manifest)

    handoff = _mission_control_handoff(manifest)
    _write_json(mission_control_dir / "mission-control-handoff.json", handoff)
    (mission_control_dir / "MISSION_CONTROL_HANDOFF.md").write_text(
        _mission_control_handoff_markdown(handoff).rstrip() + "\n",
        encoding="utf-8",
    )

    host_source = host_source_dir / "article.txt"
    sandbox_copy = sandbox_working_dir / "article.txt"
    sandbox_summary = sandbox_output_dir / "summary.md"
    returned_summary = host_staging_dir / "summary.md"
    shutil.copyfile(fixture_path, host_source)
    shutil.copyfile(host_source, sandbox_copy)
    sandbox_text = sandbox_copy.read_text(encoding="utf-8")
    sandbox_summary.write_text(_summarize(sandbox_text), encoding="utf-8")
    shutil.copyfile(sandbox_summary, returned_summary)
    stage2_manifest = _stage2_manifest(
        commit=commit,
        dirty=dirty,
        host_source=host_source,
        sandbox_copy=sandbox_copy,
        sandbox_summary=sandbox_summary,
        returned_summary=returned_summary,
        stage1_manifest=manifest,
    )
    _write_json(evidence_dir / "stage2-simulated-sandbox-manifest.json", stage2_manifest)

    files = {
        "STAGE_1_LAB_INDEX.md": _index(manifest),
        "STAGE_1_LAB_TRANSCRIPT.md": _transcript(manifest, source_text),
        "STAGE_1_PART_2_MISSION_CONTROL_NOTES.md": _part_two_notes(),
        "STAGE_2_SIMULATED_SANDBOX_TRANSFER.md": _stage2_markdown(stage2_manifest),
        "STAGE_2_REAL_VM_READINESS_PLAN.md": _real_vm_readiness_plan(),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _summarize(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0].removeprefix("# ").strip() if lines else "Untitled"
    body = " ".join(line for line in lines if not line.startswith("# "))
    sentences = [part.strip() for part in body.replace("\n", " ").split(".") if part.strip()]
    words = [word.strip(" ,;:()[]").lower() for word in body.split() if word.strip(" ,;:()[]")]
    summary_sentences = sentences[:3]
    bullets = "\n".join(f"- {sentence}." for sentence in summary_sentences)
    return f"""# Staged Summary

Source label: `fixture://governed-artifact-transfer/article.txt`

## Deterministic Summary

{bullets}

## Safe Metadata

- title_label: `{title}`
- word_count: `{len(words)}`
- sentence_count: `{len(sentences)}`
- generation_mode: `deterministic_fixture_summary`
- mission_control_integration: `false`
- vm_or_sandbox: `false`
- output_policy: `no_source_contents_beyond_short_summary`
"""


def _index(manifest: dict[str, Any]) -> str:
    return f"""# Governed Artifact Transfer Stage 1 Lab

This packet is the Ithildin-only known-good baseline for the governed artifact transfer lab. It
does not use Mission Control, a VM, a sandbox, service startup, or live governed tool calls.

## Status

- Lab: `{manifest["lab"]}`
- Commit: `{manifest["commit"]}`
- Dirty at generation: `{str(manifest["dirty"]).lower()}`
- Tool count: `{manifest["tool_count"]}`
- Mission Control integration: `false`
- VM or sandbox: `false`
- Source SHA-256: `{manifest["source"]["sha256"]}`
- Output SHA-256: `{manifest["output"]["sha256"]}`

## Reading Order

1. `STAGE_1_LAB_INDEX.md`
2. `STAGE_1_LAB_TRANSCRIPT.md`
3. `staging/summary.md`
4. `evidence/manifest.json`
5. `artifact-hashes.json`
6. `mission-control-handoff/mission-control-handoff.json`
7. `mission-control-handoff/MISSION_CONTROL_HANDOFF.md`
8. `STAGE_1_PART_2_MISSION_CONTROL_NOTES.md`
9. `STAGE_2_SIMULATED_SANDBOX_TRANSFER.md`
10. `evidence/stage2-simulated-sandbox-manifest.json`
11. `STAGE_2_REAL_VM_READINESS_PLAN.md`

## Boundary

This is deterministic lab evidence only. Mission Control participation is represented as handoff
metadata, and Stage 2 uses a generated simulated sandbox directory. It does not add governed tools,
executors, policy rules, API/MCP behavior, Mission Control runtime behavior, VM lifecycle control,
sandbox orchestration, SIEM adapters, compliance automation, or public/security-product claims.
"""


def _transcript(manifest: dict[str, Any], source_text: str) -> str:
    return f"""# Stage 1 Lab Transcript

## Scenario

An operator places a harmless article-style text fixture into the known-good lab input set. The lab
builds a deterministic staged summary and records source/output hashes for later comparison with
Mission Control and VM/sandbox evidence.

## Observed Evidence

- source_label: `{manifest["source"]["path_label"]}`
- source_sha256: `{manifest["source"]["sha256"]}`
- output_label: `{manifest["output"]["path_label"]}`
- output_sha256: `{manifest["output"]["sha256"]}`
- evidence_manifest: `evidence/manifest.json`
- artifact_hash_manifest: `artifact-hashes.json`

## Source Fixture Metadata

- source_bytes: `{manifest["source"]["bytes"]}`
- source_line_count: `{len(source_text.splitlines())}`

## Notes

This transcript intentionally omits live model prompts, regulated data, file contents, shell output,
service logs, and Mission Control state. Part 2 can add a Mission Control mission record around the
same fixture and compare evidence without changing the Ithildin-only baseline.
"""


def _part_two_notes() -> str:
    return """# Stage 1 Part 2 Mission Control Notes

Part 2 should keep this generated Ithildin-only packet as the known-good baseline and add Mission
Control as an operator-facing layer around the same harmless fixture.

Expected additions:

- Mission Control mission ID or manual mission note.
- Operator intent: summarize the fixture into staging.
- Evidence attachment pointing to this packet's source/output hashes.
- No VM/sandbox yet.
- No new Ithildin governed tools.
- No broad writes, shell execution, or production/security-product claims.
"""


def _mission_control_handoff(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "handoff_type": "mission_control_metadata_wrapper",
        "mission_id": "mc-demo-governed-artifact-transfer-stage1",
        "operator_intent": "Summarize the harmless local fixture and attach Ithildin evidence.",
        "ithildin_packet_path": DEFAULT_OUTPUT_DIR.as_posix(),
        "source_artifact_label": manifest["source"]["path_label"],
        "source_sha256": manifest["source"]["sha256"],
        "output_artifact_label": manifest["output"]["path_label"],
        "output_sha256": manifest["output"]["sha256"],
        "review_status": "pending_operator_review",
        "promotion_status": "not_promoted",
        "mission_control_integration": "metadata_only",
        "vm_or_sandbox": False,
        "trusted_authority": {
            "mission_control": "operator_intent_and_dashboard_context",
            "ithildin": "governed_gateway_and_evidence_packet",
        },
        "evidence_attachments": [
            "STAGE_1_LAB_INDEX.md",
            "evidence/manifest.json",
            "artifact-hashes.json",
            "staging/summary.md",
        ],
        "must_not_claim": [
            "Mission Control executed or governed the tool call",
            "Ithildin started or controlled Mission Control",
            "VM or sandbox isolation was used in Stage 1",
            "production compliance or security-product approval",
        ],
    }


def _mission_control_handoff_markdown(handoff: dict[str, Any]) -> str:
    return f"""# Mission Control Handoff

This handoff lets Mission Control display operator intent and attach Ithildin evidence without
becoming Ithildin's policy, executor, or audit authority.

## Mission Metadata

- mission_id: `{handoff["mission_id"]}`
- operator_intent: `{handoff["operator_intent"]}`
- review_status: `{handoff["review_status"]}`
- promotion_status: `{handoff["promotion_status"]}`
- source_sha256: `{handoff["source_sha256"]}`
- output_sha256: `{handoff["output_sha256"]}`
- mission_control_integration: `metadata_only`
- vm_or_sandbox: `false`

## Display Guidance

Mission Control should show the intent, source/output hash comparison, evidence attachments, and
promotion status. It should not claim it executed the governed action, replaced Ithildin policy, or
provided VM isolation.
"""


def _stage2_manifest(
    *,
    commit: str,
    dirty: bool,
    host_source: Path,
    sandbox_copy: Path,
    sandbox_summary: Path,
    returned_summary: Path,
    stage1_manifest: dict[str, Any],
) -> dict[str, Any]:
    host_source_hash = _sha256(host_source)
    sandbox_copy_hash = _sha256(sandbox_copy)
    sandbox_summary_hash = _sha256(sandbox_summary)
    returned_summary_hash = _sha256(returned_summary)
    return {
        "schema_version": "1",
        "lab": "governed-artifact-transfer-stage-2-simulated-sandbox",
        "status": "simulated_sandbox_transfer_complete",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 23,
        "mission_control_integration": "metadata_only",
        "vm_or_sandbox": "simulated_directory_only",
        "real_vm_or_container_started": False,
        "sandbox_lifecycle_control": False,
        "service_startup_performed": False,
        "governed_tool_calls_performed": False,
        "host_source": {
            "path_label": "simulated-sandbox/host-source/article.txt",
            "sha256": host_source_hash,
            "bytes": host_source.stat().st_size,
        },
        "sandbox_copy": {
            "sandbox_id": "simulated-local-directory-sandbox",
            "path_label": "simulated-sandbox/sandbox-working-copy/article.txt",
            "sha256": sandbox_copy_hash,
            "bytes": sandbox_copy.stat().st_size,
        },
        "sandbox_output": {
            "path_label": "simulated-sandbox/sandbox-output/summary.md",
            "sha256": sandbox_summary_hash,
            "bytes": sandbox_summary.stat().st_size,
        },
        "returned_staging_output": {
            "path_label": "simulated-sandbox/host-staging/summary.md",
            "sha256": returned_summary_hash,
            "bytes": returned_summary.stat().st_size,
        },
        "checks": {
            "host_source_matches_sandbox_copy": host_source_hash == sandbox_copy_hash,
            "sandbox_output_matches_returned_staging": (
                sandbox_summary_hash == returned_summary_hash
            ),
            "stage1_source_matches_host_source": stage1_manifest["source"]["sha256"]
            == host_source_hash,
            "stage1_output_matches_stage2_returned_output": stage1_manifest["output"]["sha256"]
            == returned_summary_hash,
        },
        "approval": {
            "promotion_approval_required": True,
            "promotion_approval_id": "manual-demo-approval-required",
            "auto_promotion_performed": False,
        },
        "boundaries": BOUNDARIES,
        "next_stage": (
            "A real VM implementation requires an explicit future implementation decision."
        ),
    }


def _stage2_markdown(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    return f"""# Stage 2 Simulated Sandbox Transfer

Stage 2 proves the artifact-transfer evidence shape with generated directories only. It does not
start a VM, container, Docker daemon, shell, model process, or Mission Control runtime.

## Evidence

- host_source_sha256: `{manifest["host_source"]["sha256"]}`
- sandbox_copy_sha256: `{manifest["sandbox_copy"]["sha256"]}`
- sandbox_output_sha256: `{manifest["sandbox_output"]["sha256"]}`
- returned_staging_sha256: `{manifest["returned_staging_output"]["sha256"]}`
- sandbox_id: `{manifest["sandbox_copy"]["sandbox_id"]}`
- promotion_approval_required: `true`
- auto_promotion_performed: `false`

## Checks

- host_source_matches_sandbox_copy: `{str(checks["host_source_matches_sandbox_copy"]).lower()}`
- sandbox_output_matches_returned_staging:
  `{str(checks["sandbox_output_matches_returned_staging"]).lower()}`
- stage1_source_matches_host_source: `{str(checks["stage1_source_matches_host_source"]).lower()}`
- stage1_output_matches_stage2_returned_output:
  `{str(checks["stage1_output_matches_stage2_returned_output"]).lower()}`

## Boundary

This is a deterministic fixture simulation. It is useful for forensic shape and operator workflow
review, but it is not VM isolation, sandbox orchestration, SIEM custody, compliance automation, or
production security approval.
"""


def _real_vm_readiness_plan() -> str:
    return """# Stage 2 Real VM Readiness Plan

Status: design/readiness only. No real VM, container, shell, Docker socket, Kubernetes integration,
browser automation, remote MCP hosting, or sandbox lifecycle API is implemented by this lab.

## Future Preconditions

- Operator selects and starts a local VM or sandbox outside Ithildin.
- Mission Control records operator intent and the sandbox/workspace label.
- Ithildin mediates only approved artifact-transfer actions through already reviewed tools or a
  future explicitly approved capability.
- Host source hash, sandbox copy hash, sandbox output hash, returned staging hash, and promotion
  approval evidence are all recorded.

## Stop Conditions

- The design requires Ithildin to run shell commands or control VM/container lifecycle.
- The design requires broad writes, deletes, chmod, archive extraction, Docker socket access, or
  Kubernetes access.
- The design implies compliance automation, production security control, or OS isolation proof.
- The design cannot keep source, sandbox copy, output, and promotion evidence secret-free.
"""


def _hashes(output_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_MANIFEST:
            continue
        entries.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {"schema_version": "1", "artifacts": entries}


def _resolve_fixture(repo_root: Path, fixture: Path) -> Path:
    path = fixture if fixture.is_absolute() else repo_root / fixture
    if not path.exists():
        raise GovernedArtifactTransferLabError(f"fixture does not exist: {fixture}")
    if not path.is_file():
        raise GovernedArtifactTransferLabError(f"fixture is not a file: {fixture}")
    return path


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise GovernedArtifactTransferLabError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
