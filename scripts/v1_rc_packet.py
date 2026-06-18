"""Generate a compact ignored v1.0 RC review packet."""

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

from scripts import v1_rc_readiness_check

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "var/review-packets/v1.0/rc"
SOURCE_DOCS = [
    ("01_V1_RC_STATUS.md", ROOT / "docs/codex/v1.0-rc-status.md"),
    ("02_V1_OPERATOR_QUICKSTART.md", ROOT / "docs/codex/v1.0-operator-quickstart.md"),
    (
        "03_V1_WORKBENCH_EVIDENCE_CLOSURE.md",
        ROOT / "docs/codex/v1.0-workbench-evidence-closure.md",
    ),
    ("04_V1_ASSURANCE_CLOSURE.md", ROOT / "docs/codex/v1.0-assurance-closure.md"),
    ("05_V1_RC_READINESS_GATE.md", ROOT / "docs/codex/v1.0-rc-readiness-gate.md"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    repo_root = ROOT
    if not args.allow_dirty and _git_dirty(repo_root):
        print("v1 RC packet generation refused: working tree is dirty", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    packet = build_packet(repo_root, output_dir)
    print(f"Built v1.0 RC packet at {packet['output_dir']}")
    return 0


def build_packet(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    readiness = v1_rc_readiness_check.build_report(repo_root)
    commit = _git_commit(repo_root)
    files: list[Path] = []

    index_path = output_dir / "00_V1_RC_PACKET_INDEX.md"
    index_path.write_text(_index_markdown(commit, readiness), encoding="utf-8")
    files.append(index_path)

    for output_name, source in SOURCE_DOCS:
        destination = output_dir / output_name
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        files.append(destination)

    commands_path = output_dir / "06_V1_RC_COMMANDS.md"
    commands_path.write_text(_commands_markdown(readiness), encoding="utf-8")
    files.append(commands_path)

    hashes = _artifact_hashes(output_dir, files)
    hashes_path = output_dir / "v1-rc-artifact-hashes.json"
    hashes_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append(hashes_path)

    return {
        "output_dir": output_dir.as_posix(),
        "commit": commit,
        "artifact_count": len(files),
        "hashes": hashes,
    }


def _index_markdown(commit: str, readiness: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Ithildin v1.0 RC Packet",
            "",
            "Status: compact local-preview release-candidate handoff packet.",
            "",
            f"- Commit: `{commit}`",
            f"- Tool count: `{readiness['tool_count']}`",
            f"- Latest implemented tool: `{readiness['latest_implemented_tool']}`",
            f"- Selected capability: `{readiness['selected_capability']}`",
            f"- Pending external-review rows: `{readiness['pending_external_review_rows']}`",
            f"- Packet redaction findings: `{readiness['packet_redaction_findings']}`",
            "- Capability expansion: blocked",
            "- Public/security-product positioning: blocked",
            "",
            "## Reading Order",
            "",
            "1. `01_V1_RC_STATUS.md`",
            "2. `02_V1_OPERATOR_QUICKSTART.md`",
            "3. `03_V1_WORKBENCH_EVIDENCE_CLOSURE.md`",
            "4. `04_V1_ASSURANCE_CLOSURE.md`",
            "5. `05_V1_RC_READINESS_GATE.md`",
            "6. `06_V1_RC_COMMANDS.md`",
            "7. `v1-rc-artifact-hashes.json`",
            "",
            "This packet is local handoff evidence only. It is not production approval, external",
            "source-review closure, custody-grade audit, sandbox approval, SIEM approval, or",
            "compliance automation.",
            "",
        ]
    )


def _commands_markdown(readiness: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# v1.0 RC Commands",
            "",
            "Run these from the Ithildin repo root:",
            "",
            "```sh",
            "make v1-rc-readiness",
            "make v1-rc-packet",
            "make release-check",
            "make review-candidate",
            "```",
            "",
            "## Latest Readiness Snapshot",
            "",
            "```json",
            json.dumps(readiness, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def _artifact_hashes(output_dir: Path, files: list[Path]) -> dict[str, Any]:
    artifacts = []
    for path in files:
        if path.name == "v1-rc-artifact-hashes.json":
            continue
        content = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return {"schema_version": "1", "artifacts": artifacts}


def _git_commit(repo_root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()


def _git_dirty(repo_root: Path) -> bool:
    return bool(subprocess.check_output(["git", "status", "--short"], cwd=repo_root, text=True))


if __name__ == "__main__":
    raise SystemExit(main())
