"""Validate safe evidence from the Node release-artifact POC."""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-release-artifact-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    evidence = root / "evidence"
    paths = {
        "private_key": root / "keys/private.pem",
        "current_bundle": evidence / "current-bundle.json",
        "rollback_bundle": evidence / "rollback-bundle.json",
        "current": evidence / "current-verification.json",
        "rollback": evidence / "rollback-verification.json",
        "tamper": evidence / "tamper-verification.json",
        "wrong_selection": evidence / "wrong-selection-verification.json",
        "untrusted": evidence / "untrusted-key-verification.json",
        "substitution": evidence / "substituted-image-verification.json",
        "dirty": evidence / "dirty-source-result.json",
        "keys": evidence / "key-posture.json",
    }
    failures = [
        f"missing Node release-artifact POC evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, bool] = {}
    if not failures:
        documents = {
            name: _json(path) for name, path in paths.items() if name != "private_key"
        }
        current_artifact = _object(documents["current_bundle"].get("artifact"))
        rollback_artifact = _object(documents["rollback_bundle"].get("artifact"))
        current_signature = _object(documents["current_bundle"].get("signature"))
        rollback_signature = _object(documents["rollback_bundle"].get("signature"))
        current_runtime = _object(current_artifact.get("runtime"))
        current_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        private_key_text = paths["private_key"].read_text(encoding="utf-8")
        safe_text = "\n".join(
            path.read_text(encoding="utf-8") for path in evidence.glob("*.json")
        )
        runtime = {
            "current_artifact_verified": documents["current"].get("valid") is True
            and documents["current"].get("image_id") == current_artifact.get("image_id"),
            "rollback_artifact_verified": documents["rollback"].get("valid") is True
            and documents["rollback"].get("image_id") == rollback_artifact.get("image_id"),
            "rollback_selection_is_distinct": current_artifact.get("node_version") == "0.1.0"
            and rollback_artifact.get("node_version") == "0.0.9"
            and current_artifact.get("image_id") != rollback_artifact.get("image_id"),
            "artifacts_bind_exact_current_commit": current_artifact.get("source_commit")
            == current_commit
            and rollback_artifact.get("source_commit") == current_commit
            and current_artifact.get("source_dirty") is False
            and rollback_artifact.get("source_dirty") is False,
            "dedicated_key_is_consistent": current_signature.get("key_id")
            == rollback_signature.get("key_id")
            == documents["keys"].get("key_id")
            and documents["keys"].get("dedicated_release_artifact_key") is True,
            "private_key_mode_0600": stat.S_IMODE(paths["private_key"].stat().st_mode)
            == 0o600
            and documents["keys"].get("private_key_mode") == "0600",
            "closed_unprivileged_runtime_bound": current_runtime.get("user") == "10002:10002"
            and current_runtime.get("entrypoint") == ["python", "-m", "ithildin_node"]
            and current_runtime.get("exposed_ports") == [],
            "signature_tamper_denied": documents["tamper"].get("valid") is False
            and documents["tamper"].get("failure")
            == "Node release artifact signature verification failed",
            "wrong_operator_selection_denied": documents["wrong_selection"].get("valid")
            is False
            and documents["wrong_selection"].get("failure")
            == "signed Node image reference does not match selection",
            "untrusted_key_denied": documents["untrusted"].get("valid") is False
            and documents["untrusted"].get("failure")
            == "Node release signature public key mismatch",
            "mutable_tag_substitution_denied": documents["substitution"].get("valid") is False
            and documents["substitution"].get("failure")
            == "local Node image ID does not match signed artifact",
            "dirty_source_denied": documents["dirty"].get("valid") is False
            and documents["dirty"].get("dirty_source_denied") is True,
            "nonclaims_preserved": all(
                document.get("gateway_enforcement") is False
                and document.get("self_update_authority") is False
                for document in (
                    documents["current"],
                    documents["rollback"],
                    documents["tamper"],
                    documents["wrong_selection"],
                    documents["untrusted"],
                    documents["substitution"],
                    documents["dirty"],
                )
            ),
            "private_key_absent_from_safe_evidence": private_key_text not in safe_text,
        }
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    checks = {"tool_count_unchanged": tool_count == 24, **runtime}
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "local_signed_node_oci_selection_and_rollback_artifact_evidence",
        "non_claims": [
            "registry_or_image_transfer",
            "self_update_or_automatic_rollback",
            "remote_or_build_system_attestation",
            "official_supply_chain_signing_or_production_key_custody",
            "gateway_enforcement_or_runner_control",
        ],
        "tool_count": tool_count,
        "checks": checks,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node release-artifact POC evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"claim_level: {report['claim_level']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{name}: {str(passed).lower()}" for name, passed in report["checks"].items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"invalid Node release-artifact evidence: {path.name}")
    return cast(dict[str, Any], document)


def _object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("invalid Node release-artifact object")
    return cast(dict[str, Any], value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve(), args.evidence_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
