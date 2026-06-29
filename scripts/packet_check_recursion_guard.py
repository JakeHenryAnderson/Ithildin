"""Guard high-level packet checks against recursive report dependencies."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

RULES = [
    {
        "id": "mission_control_integration_readiness_no_enterprise_status_reports",
        "path": Path("scripts/mission_control_integration_readiness_packet.py"),
        "forbidden_script_imports": [
            "enterprise_status_export",
            "mission_control_enterprise_status_import_check",
            "mission_control_enterprise_status_fixtures",
            "mission_control_enterprise_status_acceptance_matrix_check",
            "mission_control_enterprise_status_reference_validator",
        ],
        "reason": (
            "The Mission Control integration readiness packet may bundle enterprise-status docs "
            "and command names, but must not import those report builders. They depend on "
            "enterprise status export/current-checkpoint paths that can loop back into this packet."
        ),
    },
]

REQUIRED_GUIDE_PHRASES = [
    "Packet Recursion Guard",
    "make packet-check-recursion-guard",
    "Do not nest high-level packet/status/export report builders",
]


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
    failures: list[str] = []
    rule_reports = [_check_rule(repo_root, rule) for rule in RULES]
    for rule_report in rule_reports:
        failures.extend(rule_report["failures"])

    guide = _read(repo_root / "docs/codex/validation-performance-and-gate-tiers.md")
    for phrase in REQUIRED_GUIDE_PHRASES:
        if phrase not in guide:
            failures.append(f"validation performance guide missing phrase: {phrase}")

    makefile = _read(repo_root / "Makefile")
    if "packet-check-recursion-guard:" not in makefile:
        failures.append("Makefile missing packet-check-recursion-guard target")
    quick_check_body = makefile.partition("quick-check:")[2].partition("\n\n")[0]
    if "$(MAKE) packet-check-recursion-guard" not in quick_check_body:
        failures.append("quick-check must run packet-check-recursion-guard")
    if "release-check: packet-check-recursion-guard" not in makefile:
        failures.append("release-check must include packet-check-recursion-guard")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "rule_count": len(RULES),
        "rules": rule_reports,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin packet check recursion guard",
        f"valid: {str(report['valid']).lower()}",
        f"rule_count: {report['rule_count']}",
    ]
    for rule in report["rules"]:
        lines.append(
            f"- {rule['id']}: forbidden_import_count={rule['forbidden_import_count']}"
        )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _check_rule(repo_root: Path, rule: dict[str, Any]) -> dict[str, Any]:
    path = repo_root / rule["path"]
    failures: list[str] = []
    if not path.exists():
        failures.append(f"missing guarded packet script: {rule['path']}")
        imported: set[str] = set()
    else:
        imported = _script_imports(path)
    forbidden = sorted(set(rule["forbidden_script_imports"]) & imported)
    for module in forbidden:
        failures.append(f"{rule['path']} must not import scripts.{module}: {rule['reason']}")
    return {
        "id": rule["id"],
        "path": str(rule["path"]),
        "forbidden_import_count": len(forbidden),
        "forbidden_imports": forbidden,
        "failures": failures,
    }


def _script_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "scripts":
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scripts."):
                    imported.add(alias.name.removeprefix("scripts.").split(".", 1)[0])
    return imported


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
