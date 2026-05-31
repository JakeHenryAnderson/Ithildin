"""Scan generated review packet artifacts for secret material and unsafe runtime files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PACKET_ROOT = Path("var/review-packets/v0.2")
CONSOLIDATED_PACKET = DEFAULT_PACKET_ROOT / "GPT-5.5-Pro-consolidated"
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", "site"}
FORBIDDEN_SUFFIXES = {".env", ".pem", ".key", ".sqlite", ".sqlite3", ".jsonl"}
FORBIDDEN_CONTENT_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "admin_token_assignment": re.compile(r"(?m)^ITHILDIN_ADMIN_TOKEN=(?!\.\.\.)\S+"),
    "sample_admin_token": re.compile(r"dev-admin-token-change-me"),
    "password_assignment": re.compile(r"(?im)^(?:password|secret|api[_-]?key)=\S{8,}"),
}


class PacketRedactionScanError(RuntimeError):
    """Raised when a packet scan cannot run safely."""


@dataclass(frozen=True)
class PacketScanFinding:
    path: str
    reason: str


@dataclass(frozen=True)
class PacketScanResult:
    roots: list[str]
    scanned_files: int
    findings: list[PacketScanFinding]

    def as_dict(self) -> dict[str, Any]:
        return {
            "roots": self.roots,
            "scanned_files": self.scanned_files,
            "findings": [finding.__dict__ for finding in self.findings],
            "ok": not self.findings,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="packet directories or files to scan")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    try:
        result = scan_packet_paths(args.paths or discover_default_packet_paths(Path.cwd()))
    except PacketRedactionScanError as exc:
        print(f"packet redaction scan failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(render_scan_result(result))
    return 0 if not result.findings else 1


def discover_default_packet_paths(repo_root: Path) -> list[Path]:
    packet_root = repo_root / DEFAULT_PACKET_ROOT
    paths: list[Path] = []
    if packet_root.exists():
        bundles = sorted(
            packet_root.glob("ithildin-v0.2-review-packet-*"),
            key=lambda path: path.stat().st_mtime,
        )
        if bundles:
            paths.append(bundles[-1])
    consolidated = repo_root / CONSOLIDATED_PACKET
    if consolidated.exists():
        paths.append(consolidated)
    if not paths:
        raise PacketRedactionScanError("no generated review packet artifacts found")
    return paths


def scan_packet_paths(paths: list[Path]) -> PacketScanResult:
    files: list[Path] = []
    roots: list[str] = []
    for raw_path in paths:
        path = raw_path.resolve()
        if not path.exists():
            raise PacketRedactionScanError(f"scan path does not exist: {raw_path}")
        roots.append(path.as_posix())
        if path.is_file():
            files.append(path)
        else:
            files.extend(_iter_files(path))

    findings: list[PacketScanFinding] = []
    for path in sorted(set(files)):
        findings.extend(_scan_path(path))
    return PacketScanResult(roots=roots, scanned_files=len(set(files)), findings=findings)


def render_scan_result(result: PacketScanResult) -> str:
    lines = [
        "# Ithildin Packet Redaction Scan",
        "",
        f"roots: `{len(result.roots)}`",
        f"scanned_files: `{result.scanned_files}`",
        f"findings: `{len(result.findings)}`",
        "",
    ]
    if result.findings:
        lines.extend(["## Findings", ""])
        lines.extend(
            f"- `{finding.path}`: {finding.reason}" for finding in result.findings
        )
        lines.append("")
    else:
        lines.append("Packet redaction scan passed.")
    return "\n".join(lines)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _scan_path(path: Path) -> list[PacketScanFinding]:
    findings: list[PacketScanFinding] = []
    if path.name in {".env"} or path.suffix in FORBIDDEN_SUFFIXES:
        findings.append(PacketScanFinding(path=path.as_posix(), reason="forbidden runtime file"))
        return findings
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append(PacketScanFinding(path=path.as_posix(), reason="non-text packet artifact"))
        return findings
    for name, pattern in FORBIDDEN_CONTENT_PATTERNS.items():
        if pattern.search(content):
            findings.append(PacketScanFinding(path=path.as_posix(), reason=name))
    return findings


if __name__ == "__main__":
    raise SystemExit(main())
