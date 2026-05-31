"""Compare two generated Ithildin review packet bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "ITHILDIN_ADMIN_TOKEN=",
    "dev-admin-token-change-me",
    "password=",
    "secret=",
)


class ReviewPacketDiffError(RuntimeError):
    """Raised when packet diff input cannot be compared safely."""


@dataclass(frozen=True)
class Artifact:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class PacketDiff:
    old_packet: str
    new_packet: str
    added: list[Artifact]
    removed: list[Artifact]
    changed: list[dict[str, Artifact]]
    unchanged_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "old_packet": self.old_packet,
            "new_packet": self.new_packet,
            "added": [artifact.__dict__ for artifact in self.added],
            "removed": [artifact.__dict__ for artifact in self.removed],
            "changed": [
                {
                    "old": entry["old"].__dict__,
                    "new": entry["new"].__dict__,
                }
                for entry in self.changed
            ],
            "unchanged_count": self.unchanged_count,
        }


def validate_packet_diff_gate(diff: PacketDiff) -> None:
    """Fail closed on packet changes that can hide evidence from reviewers."""
    if diff.removed:
        removed = ", ".join(artifact.path for artifact in diff.removed)
        raise ReviewPacketDiffError(f"packet diff removed artifacts: {removed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, type=Path, help="old review packet directory")
    parser.add_argument("--new", required=True, type=Path, help="new review packet directory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="require artifact hashes and fail if comparable artifacts were removed",
    )
    args = parser.parse_args()

    try:
        diff = compare_packets(args.old, args.new, require_hashes=args.gate)
        if args.gate:
            validate_packet_diff_gate(diff)
    except ReviewPacketDiffError as exc:
        print(f"review packet diff failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(diff.as_dict(), indent=2, sort_keys=True))
    else:
        print(render_diff(diff))
        if args.gate:
            print("Review packet diff gate passed.")
    return 0


def compare_packets(
    old_packet: Path, new_packet: Path, *, require_hashes: bool = False
) -> PacketDiff:
    old_artifacts = collect_packet_artifacts(old_packet, require_hashes=require_hashes)
    new_artifacts = collect_packet_artifacts(new_packet, require_hashes=require_hashes)

    old_paths = set(old_artifacts)
    new_paths = set(new_artifacts)
    added = [new_artifacts[path] for path in sorted(new_paths - old_paths)]
    removed = [old_artifacts[path] for path in sorted(old_paths - new_paths)]
    changed = [
        {
            "old": old_artifacts[path],
            "new": new_artifacts[path],
        }
        for path in sorted(old_paths & new_paths)
        if old_artifacts[path].sha256 != new_artifacts[path].sha256
        or old_artifacts[path].bytes != new_artifacts[path].bytes
    ]
    unchanged_count = len(old_paths & new_paths) - len(changed)

    return PacketDiff(
        old_packet=old_packet.as_posix(),
        new_packet=new_packet.as_posix(),
        added=added,
        removed=removed,
        changed=changed,
        unchanged_count=unchanged_count,
    )


def collect_packet_artifacts(
    packet_dir: Path, *, require_hashes: bool = False
) -> dict[str, Artifact]:
    if not packet_dir.exists() or not packet_dir.is_dir():
        raise ReviewPacketDiffError(f"packet directory does not exist: {packet_dir}")
    hash_file = packet_dir / "artifact-hashes.json"
    if hash_file.exists():
        try:
            raw = json.loads(hash_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReviewPacketDiffError(f"invalid artifact-hashes.json: {exc}") from exc
        if not isinstance(raw, list):
            raise ReviewPacketDiffError("artifact-hashes.json must contain a list")
        artifacts = [_artifact_from_json(item) for item in raw]
    else:
        if require_hashes:
            raise ReviewPacketDiffError(
                f"packet directory missing artifact-hashes.json: {packet_dir}"
            )
        artifacts = _hash_directory(packet_dir)

    result: dict[str, Artifact] = {}
    for artifact in artifacts:
        if artifact.path in result:
            raise ReviewPacketDiffError(f"duplicate artifact path: {artifact.path}")
        result[artifact.path] = artifact
    _assert_secret_free(result)
    return result


def render_diff(diff: PacketDiff) -> str:
    lines = [
        "# Ithildin Review Packet Diff",
        "",
        f"old: `{diff.old_packet}`",
        f"new: `{diff.new_packet}`",
        "",
        f"added: `{len(diff.added)}`",
        f"removed: `{len(diff.removed)}`",
        f"changed: `{len(diff.changed)}`",
        f"unchanged: `{diff.unchanged_count}`",
        "",
    ]
    if diff.added:
        lines.extend(["## Added", ""])
        lines.extend(_artifact_lines(diff.added))
        lines.append("")
    if diff.removed:
        lines.extend(["## Removed", ""])
        lines.extend(_artifact_lines(diff.removed))
        lines.append("")
    if diff.changed:
        lines.extend(["## Changed", ""])
        for entry in diff.changed:
            old = entry["old"]
            new = entry["new"]
            lines.append(
                f"- `{old.path}` `{old.sha256}` -> `{new.sha256}` "
                f"(`{old.bytes}` -> `{new.bytes}` bytes)"
            )
        lines.append("")
    return "\n".join(lines)


def _artifact_from_json(item: object) -> Artifact:
    if not isinstance(item, dict):
        raise ReviewPacketDiffError("artifact entries must be objects")
    path = item.get("path")
    sha256 = item.get("sha256")
    byte_count = item.get("bytes")
    if not isinstance(path, str) or not path:
        raise ReviewPacketDiffError("artifact entry missing path")
    if path.startswith("/") or ".." in Path(path).parts:
        raise ReviewPacketDiffError(f"unsafe artifact path: {path}")
    if (
        not isinstance(sha256, str)
        or not sha256.startswith("sha256:")
        or len(sha256) != len("sha256:") + 64
    ):
        raise ReviewPacketDiffError(f"artifact {path} missing sha256 digest")
    hex_digest = sha256.removeprefix("sha256:")
    if any(character not in "0123456789abcdef" for character in hex_digest):
        raise ReviewPacketDiffError(f"artifact {path} has invalid sha256 digest")
    if not isinstance(byte_count, int) or byte_count < 0:
        raise ReviewPacketDiffError(f"artifact {path} missing byte count")
    return Artifact(path=path, sha256=sha256, bytes=byte_count)


def _hash_directory(packet_dir: Path) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in sorted(packet_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(packet_dir)
        if _should_skip(relative):
            continue
        content = path.read_bytes()
        artifacts.append(
            Artifact(
                path=relative.as_posix(),
                sha256="sha256:" + hashlib.sha256(content).hexdigest(),
                bytes=len(content),
            )
        )
    if not artifacts:
        raise ReviewPacketDiffError(f"packet directory has no comparable artifacts: {packet_dir}")
    return artifacts


def _artifact_lines(artifacts: list[Artifact]) -> list[str]:
    return [
        f"- `{artifact.path}` `{artifact.sha256}` `{artifact.bytes} bytes`"
        for artifact in artifacts
    ]


def _should_skip(relative: Path) -> bool:
    parts = set(relative.parts)
    return bool(
        parts
        & {
            ".git",
            ".venv",
            "node_modules",
            "dist",
            "__pycache__",
        }
    )


def _assert_secret_free(artifacts: dict[str, Artifact]) -> None:
    text = json.dumps([artifact.__dict__ for artifact in artifacts.values()], sort_keys=True)
    for marker in SECRET_MARKERS:
        if marker.lower() in text.lower():
            raise ReviewPacketDiffError(f"secret-like marker present: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
