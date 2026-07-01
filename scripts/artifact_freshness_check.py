"""Check whether heavyweight handoff artifacts match the current commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEND_MANIFEST_DIR = Path("var/review-packets/v3/enterprise-review-send-manifest")
SEND_MANIFEST_JSON = SEND_MANIFEST_DIR / "enterprise-review-send-manifest.json"
SEND_HASHES_JSON = SEND_MANIFEST_DIR / "enterprise-review-send-manifest-artifact-hashes.json"
V1_RC_PACKET_INDEX = Path("var/review-packets/v1.0/rc/00_V1_RC_PACKET_INDEX.md")
REVIEW_CANDIDATE_RELEASE_TRANSCRIPT = Path(
    "var/review-packets/v3/review-candidate-release-check.txt"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    send_manifest = _read_json(repo_root / SEND_MANIFEST_JSON)
    hash_manifest = _read_json(repo_root / SEND_HASHES_JSON)
    v1_packet_text = _read(repo_root / V1_RC_PACKET_INDEX)
    transcript_text = _read(repo_root / REVIEW_CANDIDATE_RELEASE_TRANSCRIPT)
    enterprise_hashes_match = _hashes_match(repo_root / SEND_MANIFEST_DIR, hash_manifest)
    v1_packet_commit = _extract_backtick_value(v1_packet_text, "- Commit:")
    transcript_commit = _extract_prefixed_value(transcript_text, "git_commit=")
    transcript_returncode = _extract_prefixed_value(transcript_text, "returncode=")
    checks = {
        "enterprise_send_manifest_exists": bool(send_manifest),
        "enterprise_send_artifact_commits_match_current": (
            send_manifest.get("commit") == commit
        ),
        "enterprise_send_artifact_payloads_clean": send_manifest.get("dirty") is False,
        "enterprise_send_artifact_hashes_match_files": enterprise_hashes_match,
        "v1_rc_packet_exists": (repo_root / V1_RC_PACKET_INDEX).exists(),
        "v1_rc_packet_commit_matches_current": v1_packet_commit == commit,
        "review_candidate_release_transcript_exists": (
            repo_root / REVIEW_CANDIDATE_RELEASE_TRANSCRIPT
        ).exists(),
        "review_candidate_release_transcript_commit_matches_current": (
            transcript_commit == commit
        ),
        "review_candidate_release_transcript_passed": transcript_returncode == "0",
    }
    stale = [name for name, value in checks.items() if value is not True]
    return {
        "schema_version": "1",
        "valid": not stale,
        "commit": commit,
        "dirty": dirty,
        "tool_count": _tool_count(repo_root),
        "technical_mvp_state": _extract_prefixed_doc_value(
            _read(repo_root / "docs/codex/v1.0-progress-assessment.md"),
            "Technical MVP state:",
        )
        or "unknown",
        "enterprise_next_action": _enterprise_next_action(send_manifest),
        "checks": checks,
        "stale_or_missing": stale,
        "refresh_commands": _refresh_commands(stale),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "records_external_review": False,
        "normalizes_responses": False,
        "closes_enterprise_lanes": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin artifact freshness check",
        f"valid: {str(report['valid']).lower()}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        "checks:",
    ]
    lines.extend(
        f"- {name}: {str(value).lower()}" for name, value in report["checks"].items()
    )
    lines.append("stale_or_missing:")
    if report["stale_or_missing"]:
        lines.extend(f"- {name}" for name in report["stale_or_missing"])
    else:
        lines.append("- none")
    if report["refresh_commands"]:
        lines.append("refresh_commands:")
        lines.extend(f"- {command}" for command in report["refresh_commands"])
    lines.extend(
        [
            "boundaries:",
            "- does not start services",
            "- does not call governed tools",
            "- does not record external review",
            "- does not replace release-check or review-candidate",
        ]
    )
    return "\n".join(lines)


def _refresh_commands(stale: list[str]) -> list[str]:
    commands: list[str] = []
    if any(name.startswith("enterprise_send_") for name in stale):
        commands.append("make enterprise-review-send-refresh")
    if any(name.startswith("review_candidate_release_transcript_") for name in stale):
        commands.append("make review-candidate-release-transcript")
    if any(name.startswith("v1_rc_packet_") for name in stale):
        commands.append("make v1-rc-packet")
    return commands


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _tool_count(repo_root: Path) -> int:
    return len(list((repo_root / "tool-manifests").glob("*.yaml")))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _hashes_match(root: Path, hash_manifest: dict[str, Any]) -> bool:
    artifacts = hash_manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return False
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return False
        relative_path = artifact.get("path")
        expected_sha = artifact.get("sha256")
        expected_bytes = artifact.get("bytes")
        if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
            return False
        path = root / relative_path
        if not path.exists() or path.is_dir():
            return False
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_sha:
            return False
        if isinstance(expected_bytes, int) and len(data) != expected_bytes:
            return False
    return True


def _extract_prefixed_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return None


def _extract_backtick_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        parts = line.split("`")
        if len(parts) >= 2:
            return parts[1]
    return None


def _extract_prefixed_doc_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix).strip(" `.")
    return None


def _enterprise_next_action(send_manifest: dict[str, Any]) -> str:
    gaps = send_manifest.get("recommended_gaps")
    if gaps == ["ERG-003", "ERG-002"]:
        return "send_erg_003_and_erg_002"
    return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
