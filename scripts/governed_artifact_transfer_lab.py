"""Generate the Stage 1 Ithildin-only governed artifact transfer lab packet."""

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
    "mission_control_integration=false",
    "vm_or_sandbox=false",
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
    staging_dir.mkdir()
    evidence_dir.mkdir()

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

    files = {
        "STAGE_1_LAB_INDEX.md": _index(manifest),
        "STAGE_1_LAB_TRANSCRIPT.md": _transcript(manifest, source_text),
        "STAGE_1_PART_2_MISSION_CONTROL_NOTES.md": _part_two_notes(),
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
6. `STAGE_1_PART_2_MISSION_CONTROL_NOTES.md`

## Boundary

This is deterministic lab evidence only. It does not add governed tools, executors, policy rules,
API/MCP behavior, Mission Control behavior, VM lifecycle control, sandbox orchestration, SIEM
adapters, compliance automation, or public/security-product claims.
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
