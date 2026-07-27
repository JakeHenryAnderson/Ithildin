"""Build and verify a deterministic, redacted Enterprise E1 operations bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.redaction import RedactionService
from ithildin_schemas import JsonObject

from scripts.packet_redaction_scan import (
    FORBIDDEN_CONTENT_PATTERNS,
    FORBIDDEN_SUFFIXES,
    scan_packet_paths,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/codex/enterprise-e1-evidence-contract.json"
MANIFEST_NAME = "manifest.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
SAFE_SITE_LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class OperationsBundleError(RuntimeError):
    """Raised when bundle construction or verification cannot fail closed."""


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _contract(root: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            (root / CONTRACT_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperationsBundleError(f"evidence contract unavailable: {exc}") from exc
    if not isinstance(value, dict):
        raise OperationsBundleError("evidence contract must be an object")
    return value


def _load_input(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperationsBundleError(f"operations input unavailable: {exc}") from exc
    if not isinstance(value, dict):
        raise OperationsBundleError("operations input must be an object")
    expected_top = {
        "schema_version",
        "candidate_commit",
        "generated_at",
        "site_label",
        "tool_count",
        "sections",
    }
    if set(value) != expected_top:
        raise OperationsBundleError("operations input fields are not exact")
    if value.get("schema_version") != contract.get("input_schema_version"):
        raise OperationsBundleError("operations input schema version is unsupported")
    candidate_commit = value.get("candidate_commit")
    if not isinstance(candidate_commit, str) or not COMMIT_PATTERN.fullmatch(
        candidate_commit
    ):
        raise OperationsBundleError("candidate commit must be 40 lowercase hex characters")
    generated_at = value.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.endswith("Z"):
        raise OperationsBundleError("generated_at must be an explicit UTC RFC3339 value")
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationsBundleError("generated_at is not valid RFC3339") from exc
    site_label = value.get("site_label")
    if not isinstance(site_label, str) or not SAFE_SITE_LABEL.fullmatch(site_label):
        raise OperationsBundleError("site_label is not a safe receiver-neutral label")
    if value.get("tool_count") != contract.get("tool_count"):
        raise OperationsBundleError("operations input does not preserve 24 tools")
    sections = value.get("sections")
    required_sections = contract.get("required_sections")
    if not isinstance(sections, dict) or list(sections) != required_sections:
        raise OperationsBundleError("operations sections are not exact and ordered")
    if any(not isinstance(section, dict) for section in sections.values()):
        raise OperationsBundleError("every operations section must be an object")
    return value


def _redacted_artifacts(
    value: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, bytes]:
    redaction = cast(dict[str, Any], contract["redaction"])
    redactor = RedactionService(
        extra_keys=set(cast(list[str], redaction["receiver_neutral_local_metadata_keys"]))
    )
    artifacts: dict[str, bytes] = {}
    redacted_paths: dict[str, list[str]] = {}
    sections = cast(dict[str, JsonObject], value["sections"])
    for section_name, section in sections.items():
        result = redactor.redact(section)
        artifacts[f"sections/{section_name}.json"] = _canonical_json(result.value)
        redacted_paths[section_name] = list(result.summary.paths)
    artifacts["redaction-manifest.json"] = _canonical_json(
        {
            "schema_version": contract["schema_version"],
            "redaction_applied": True,
            "redacted_path_count": sum(len(paths) for paths in redacted_paths.values()),
            "redacted_paths_by_section": redacted_paths,
            "excluded_categories": redaction["excluded_categories"],
            "receiver_neutral_local_metadata_keys": redaction[
                "receiver_neutral_local_metadata_keys"
            ],
        }
    )
    artifacts["README.md"] = _readme(value, contract).encode()
    return artifacts


def _readme(value: dict[str, Any], contract: dict[str, Any]) -> str:
    sections = cast(list[str], contract["required_sections"])
    nonclaims = cast(list[str], contract["nonclaims"])
    lines = [
        "# Ithildin Enterprise E1 Operational Evidence Bundle",
        "",
        f"- Schema: `{contract['schema_version']}`",
        f"- Candidate commit: `{value['candidate_commit']}`",
        f"- Observation time: `{value['generated_at']}`",
        f"- Site label: `{value['site_label']}`",
        f"- Governed tools: `{value['tool_count']}`",
        "",
        "## Sections",
        "",
        *[f"- `{section}`" for section in sections],
        "",
        "## Verification boundary",
        "",
        "Run the repository's Enterprise E1 bundle verifier against this directory or ZIP.",
        "SHA-256 checks establish local content consistency relative to this manifest only.",
        "The bundle is receiver-neutral and performs no external delivery.",
        "",
        "## Nonclaims",
        "",
        *[f"- No claim of {nonclaim}." for nonclaim in nonclaims],
        "",
    ]
    return "\n".join(lines)


def _manifest(
    value: dict[str, Any],
    contract: dict[str, Any],
    artifacts: dict[str, bytes],
) -> bytes:
    files = [
        {
            "path": path,
            "sha256": _sha256(content),
            "bytes": len(content),
        }
        for path, content in sorted(artifacts.items())
    ]
    root_input = "".join(
        f"{entry['path']}\0{entry['sha256']}\0{entry['bytes']}\n" for entry in files
    ).encode()
    return _canonical_json(
        {
            "schema_version": contract["schema_version"],
            "candidate_commit": value["candidate_commit"],
            "generated_at": value["generated_at"],
            "site_label": value["site_label"],
            "tool_count": value["tool_count"],
            "section_count": len(contract["required_sections"]),
            "files": files,
            "content_root_sha256": _sha256(root_input),
            "verification_scope": "local_content_integrity_only",
            "manifest_self_authentication_claimed": False,
            "external_notarization_claimed": False,
        }
    )


def build_bundle(
    *,
    root: Path,
    input_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    contract = _contract(root)
    value = _load_input(input_path, contract)
    archive_path = output_dir.parent / f"{output_dir.name}.zip"
    receipt_path = output_dir.parent / f"{output_dir.name}.zip.sha256"
    for target in (output_dir, archive_path, receipt_path):
        if target.exists() or target.is_symlink():
            raise OperationsBundleError(f"output target already exists: {target}")

    staging = output_dir.parent / f".{output_dir.name}.tmp-{uuid.uuid4().hex}"
    try:
        staging.mkdir(parents=False, mode=0o700)
        artifacts = _redacted_artifacts(value, contract)
        artifacts[MANIFEST_NAME] = _manifest(value, contract, artifacts)
        for relative, content in sorted(artifacts.items()):
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o600)
        scan = scan_packet_paths([staging])
        if scan.findings:
            reasons = ", ".join(f"{item.path}: {item.reason}" for item in scan.findings)
            raise OperationsBundleError(f"redaction scan failed: {reasons}")
        _verify_contents(
            {path: content for path, content in sorted(artifacts.items())},
            contract,
        )
        _write_archive(archive_path, artifacts)
        archive_sha256 = _sha256(archive_path.read_bytes())
        receipt_path.write_text(
            f"{archive_sha256}  {archive_path.name}\n", encoding="utf-8"
        )
        receipt_path.chmod(0o600)
        staging.replace(output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if archive_path.exists():
            archive_path.unlink()
        if receipt_path.exists():
            receipt_path.unlink()
        raise
    return {
        "valid": True,
        "output_dir": output_dir.as_posix(),
        "archive": archive_path.as_posix(),
        "archive_sha256": archive_sha256,
        "receipt": receipt_path.as_posix(),
        "candidate_commit": value["candidate_commit"],
        "section_count": len(contract["required_sections"]),
        "tool_count": value["tool_count"],
        "redaction_findings": 0,
        "external_delivery_performed": False,
        "human_uat_complete": False,
    }


def _write_archive(path: Path, artifacts: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(artifacts.items()):
            info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, content)


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and name == path.as_posix()
    )


def _scan_content(name: str, content: bytes) -> None:
    path = PurePosixPath(name)
    if path.name == ".env" or path.suffix in FORBIDDEN_SUFFIXES:
        raise OperationsBundleError(f"forbidden runtime member: {name}")
    try:
        text = content.decode()
    except UnicodeDecodeError as exc:
        raise OperationsBundleError(f"non-text bundle member: {name}") from exc
    for reason, pattern in FORBIDDEN_CONTENT_PATTERNS.items():
        if pattern.search(text):
            raise OperationsBundleError(f"forbidden content in {name}: {reason}")


def _verify_contents(
    contents: dict[str, bytes],
    contract: dict[str, Any],
) -> dict[str, Any]:
    if MANIFEST_NAME not in contents:
        raise OperationsBundleError("bundle manifest is missing")
    try:
        manifest = json.loads(contents[MANIFEST_NAME].decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperationsBundleError("bundle manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise OperationsBundleError("bundle manifest must be an object")
    if manifest.get("schema_version") != contract.get("schema_version"):
        raise OperationsBundleError("bundle schema is unsupported")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise OperationsBundleError("bundle file inventory is unavailable")
    expected_names = {MANIFEST_NAME}
    root_lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise OperationsBundleError("bundle file inventory entry is invalid")
        name = entry["path"]
        if not isinstance(name, str) or not _safe_member(name):
            raise OperationsBundleError("bundle file inventory contains an unsafe path")
        if name in expected_names:
            raise OperationsBundleError("bundle file inventory contains a duplicate")
        expected_names.add(name)
        content = contents.get(name)
        if content is None:
            raise OperationsBundleError(f"bundle member is missing: {name}")
        if entry["bytes"] != len(content) or entry["sha256"] != _sha256(content):
            raise OperationsBundleError(f"bundle member digest mismatch: {name}")
        root_lines.append(f"{name}\0{entry['sha256']}\0{entry['bytes']}\n")
    if set(contents) != expected_names:
        raise OperationsBundleError("bundle contains unmanifested members")
    required = set(cast(list[str], contract["required_artifacts"])) | {MANIFEST_NAME}
    if set(contents) != required:
        raise OperationsBundleError("bundle artifact set is not exact")
    root_digest = _sha256("".join(root_lines).encode())
    if manifest.get("content_root_sha256") != root_digest:
        raise OperationsBundleError("bundle content-root digest mismatch")
    if manifest.get("tool_count") != 24 or manifest.get("section_count") != 7:
        raise OperationsBundleError("bundle boundary counts are invalid")
    for name, content in contents.items():
        if not _safe_member(name):
            raise OperationsBundleError(f"unsafe bundle member: {name}")
        _scan_content(name, content)
    return {
        "valid": True,
        "candidate_commit": manifest.get("candidate_commit"),
        "tool_count": manifest.get("tool_count"),
        "section_count": manifest.get("section_count"),
        "content_root_sha256": root_digest,
        "member_count": len(contents),
        "local_content_integrity_only": True,
        "external_notarization_claimed": False,
        "human_uat_complete": False,
    }


def verify_bundle(*, root: Path, bundle: Path) -> dict[str, Any]:
    contract = _contract(root)
    if bundle.is_dir():
        contents: dict[str, bytes] = {}
        for path in sorted(bundle.rglob("*")):
            if path.is_symlink():
                raise OperationsBundleError("bundle directory contains a symlink")
            if path.is_file():
                contents[path.relative_to(bundle).as_posix()] = path.read_bytes()
        scan = scan_packet_paths([bundle])
        if scan.findings:
            raise OperationsBundleError("bundle directory failed redaction scan")
        return _verify_contents(contents, contract)
    if bundle.is_file() and bundle.suffix == ".zip":
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            if names != sorted(names) or len(names) != len(set(names)):
                raise OperationsBundleError(
                    "bundle archive members are not unique and ordered"
                )
            contents = {}
            for info in archive.infolist():
                if (
                    not _safe_member(info.filename)
                    or info.date_time != ZIP_TIMESTAMP
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.file_size > 10_000_000
                ):
                    raise OperationsBundleError(
                        f"bundle archive member is unsafe: {info.filename}"
                    )
                contents[info.filename] = archive.read(info)
        return _verify_contents(contents, contract)
    raise OperationsBundleError("bundle must be a directory or .zip file")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            report = build_bundle(
                root=ROOT,
                input_path=args.input.resolve(),
                output_dir=args.output_dir.resolve(),
            )
        else:
            report = verify_bundle(root=ROOT, bundle=args.bundle.resolve())
    except OperationsBundleError as exc:
        print(f"Enterprise E1 operations bundle failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
