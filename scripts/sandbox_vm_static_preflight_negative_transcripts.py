"""Generate observed static sandbox/VM preflight negative transcripts."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sandbox_vm_static_preflight

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-negative")
TRANSCRIPT_NAME = "SANDBOX_VM_STATIC_PREFLIGHT_NEGATIVE_TRANSCRIPTS.md"
FIXTURE = ROOT / "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"

Mutator = Callable[[dict[str, Any]], None]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    transcript = build_transcripts(args.output_dir)
    print(f"Built sandbox/VM static preflight negative transcripts at {transcript}")
    return 0


def build_transcripts(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    seed = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [
        ("Missing Schema", "missing required section", _pop_key("schema_version")),
        (
            "Raw Mount Path",
            "raw path-shaped mount label",
            _set_nested(("mounts", "root_label"), "/Users/demo/workspace"),
        ),
        (
            "Broad Network",
            "broad network posture",
            _set_nested(("network", "broad_network_access"), True),
        ),
        (
            "Missing Warning",
            "missing not_os_isolation_proof warning",
            _remove_warning("not_os_isolation_proof"),
        ),
        (
            "Mission Control Authority",
            "Mission Control execution authority claim",
            _set_false_flag("mission_control_executes_actions", True),
        ),
        (
            "Local Model Authority",
            "local model invocation claim",
            _set_false_flag("local_model_invoked", True),
        ),
        (
            "Trusted Host Promotion",
            "trusted-host promotion claim",
            _set_false_flag("trusted_host_promotion_enabled", True),
        ),
    ]
    results = []
    for name, expected, mutator in cases:
        payload = copy.deepcopy(seed)
        mutator(payload)
        fixture_path = output_dir / (name.lower().replace(" ", "-") + ".json")
        fixture_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        report = sandbox_vm_static_preflight.build_report(fixture_path)
        fixture_path.unlink()
        results.append(
            {
                "name": name,
                "expected": expected,
                "observed_decision": report["decision"],
                "observed_valid": report["valid"],
                "safe_reasons": report["safe_reasons"],
            }
        )
    transcript = output_dir / TRANSCRIPT_NAME
    transcript.write_text(_render(results), encoding="utf-8")
    return transcript


def _render(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Sandbox/VM Static Preflight Negative Transcripts",
        "",
        "Status: observed local fixture transcripts.",
        "",
        "These transcripts are generated from temporary mutated fixture JSON files. They do not",
        "inspect a live VM/container, call Mission Control, invoke a local model, perform network",
        "access, create governed tool calls, or move artifacts.",
        "",
        "| Scenario | Expected denial | Observed valid | Observed decision | Safe reasons |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        reasons = ", ".join(result["safe_reasons"]) or "none"
        lines.append(
            "| {name} | {expected} | {valid} | {decision} | {reasons} |".format(
                name=result["name"],
                expected=result["expected"],
                valid=str(result["observed_valid"]).lower(),
                decision=result["observed_decision"],
                reasons=reasons,
            )
        )
    lines.extend(
        [
            "",
            "Output policy: no raw paths, file contents, prompts, model outputs, shell output,",
            "Docker/Kubernetes handles, network credentials, or trusted-host promotion evidence",
            "are included.",
        ]
    )
    return "\n".join(lines) + "\n"


def _pop_key(key: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.pop(key, None)

    return mutate


def _set_nested(path: tuple[str, ...], value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        current = payload
        for key in path[:-1]:
            child = current.setdefault(key, {})
            if not isinstance(child, dict):
                child = {}
                current[key] = child
            current = child
        current[path[-1]] = value

    return mutate


def _set_false_flag(flag: str, value: bool) -> Mutator:
    return _set_nested(("decision", "false_authority_flags", flag), value)


def _remove_warning(warning: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        warnings = payload.get("warnings")
        if isinstance(warnings, list):
            payload["warnings"] = [item for item in warnings if item != warning]

    return mutate


if __name__ == "__main__":
    raise SystemExit(main())
