"""Validate public-preview documentation and deployment guardrails."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_docs_site import DEFAULT_DOCS
from scripts.review_docs import REVIEW_DOCS

ROOT = Path(__file__).resolve().parents[1]

WARNING_PHRASES = [
    "local-preview mediation layer",
    "not a sandbox",
    "trusted computing base",
    "tamper-evident local evidence",
    "Redaction is best-effort",
    "SQLite is the only v0.1 runtime storage backend",
]

FORBIDDEN_CLAIMS = [
    "secure sandbox",
    "prevents compromise",
    "production-ready",
    "enterprise identity",
    "tamper-proof audit",
    "immutable audit",
    "compliance-grade audit",
    "safe arbitrary tool use",
    "network sandbox",
    "remote MCP gateway",
]

FORBIDDEN_CLAIM_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex",
    ROOT / "docs/obsidian",
    ROOT / "docs/research",
]

THREAT_MODEL_LINKED_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex/local-preview-release.md",
    ROOT / "docs/codex/v0.1-local-preview-checklist.md",
    ROOT / "docs/codex/v0.1-public-preview-release-notes.md",
]
REQUIRED_RELEASE_CHECK_FRAGMENTS = [
    "manifest-lock-check",
    "release-guardrails",
    "release-evidence-gate",
    "reviewer-findings-check",
    "external-findings-intake-dry-run",
    "review-findings-summary",
    "review-run-manifest-check",
    "filesystem-contract-check",
    "tool-surface-invariant-gate",
    "evidence-confusion-gate",
    "external-review-closure-gate",
    "determinism-check",
    "adversarial-corpus-check",
    "resource-limit-check",
    "demo-scenario-pack",
    "policy-test",
    "policy-parity",
    "test",
    "lint",
    "typecheck",
    "docs-site",
]
REQUIRED_REVIEW_CANDIDATE_STEPS = [
    "$(MAKE) release-check",
    "$(MAKE) filesystem-contract-check",
    "$(MAKE) signed-evidence-demo",
    "$(MAKE) signed-evidence-demo-verify",
    "$(MAKE) negative-review-transcripts",
    "$(MAKE) review-packet-bundle",
    "$(MAKE) review-packet-consolidated",
    "$(MAKE) packet-redaction-scan",
    "$(MAKE) docs-site",
]
REQUIRED_V03_DONE_TASKS = [f"{task:03d}" for task in range(101, 113)]
REQUIRED_V04_DONE_TASKS = [f"{task:03d}" for task in range(113, 152)]
REQUIRED_V04_METADATA_TASKS = [f"{task:03d}" for task in range(123, 152)]
V04_PLANNED_RANGE = "none"
DEFERRED_TOOL_POWER_MARKERS = [
    "shell",
    "docker",
    "kubernetes",
    "browser",
]


def main() -> None:
    failures: list[str] = []
    failures.extend(_check_warning_labels())
    failures.extend(_check_forbidden_claims())
    failures.extend(_check_threat_model_links())
    failures.extend(_check_compose_boundaries())
    failures.extend(_check_review_docs_present())
    failures.extend(_check_release_targets())
    failures.extend(_check_deferred_tool_powers_absent_from_manifests())
    failures.extend(_check_v03_wave5_status())
    failures.extend(_check_v04_horizontal_gate_status())
    failures.extend(_check_closure_matrix_v3())

    if failures:
        for failure in failures:
            print(f"release guardrail failed: {failure}", file=sys.stderr)
        raise SystemExit(1)

    print("Release guardrails passed.")


def _check_warning_labels() -> list[str]:
    release_notes = (ROOT / "docs/codex/v0.1-public-preview-release-notes.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{release_notes}"
    return [
        f"missing warning label: {phrase}"
        for phrase in WARNING_PHRASES
        if phrase not in combined
    ]


def _check_forbidden_claims() -> list[str]:
    failures: list[str] = []
    for path in _markdown_paths(FORBIDDEN_CLAIM_DOCS):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            lowered_line = line.lower()
            for phrase in FORBIDDEN_CLAIMS:
                if phrase in lowered_line and not _is_allowed_claim_context(lines, index):
                    failures.append(
                        f"{path.relative_to(ROOT)}:{index + 1} uses forbidden claim {phrase!r}"
                    )
    return failures


def _markdown_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            result.append(path)
        elif path.is_dir():
            result.extend(sorted(path.rglob("*.md")))
    return result


def _is_allowed_claim_context(lines: list[str], index: int) -> bool:
    start = max(0, index - 3)
    context = " ".join(lines[start : index + 2]).lower()
    allowed_markers = (
        "not ",
        "non-goal",
        "non-goals",
        "deferred",
        "avoid",
        "forbidden",
        "must not",
        "does not",
        "do-not-add",
        "warning",
        "review prompt",
        "reviewer focus",
        "should be avoided",
    )
    return any(marker in context for marker in allowed_markers)


def _check_threat_model_links() -> list[str]:
    failures: list[str] = []
    for path in THREAT_MODEL_LINKED_DOCS:
        text = path.read_text(encoding="utf-8")
        if "threat-model-and-non-goals.md" not in text:
            failures.append(f"{path.relative_to(ROOT)} does not link the threat model")
    return failures


def _check_compose_boundaries() -> list[str]:
    compose_path = ROOT / "deploy/docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    failures: list[str] = []
    if "docker.sock" in compose_text:
        failures.append("Compose must not mount the Docker socket")
    for service_name, service in compose.get("services", {}).items():
        for port in service.get("ports", []):
            if not str(port).startswith("127.0.0.1:"):
                failures.append(f"{service_name} exposes non-loopback port {port}")
        if service.get("privileged"):
            failures.append(f"{service_name} must not run privileged")
    return failures


def _check_review_docs_present() -> list[str]:
    failures: list[str] = []
    for doc in sorted(set(REVIEW_DOCS + DEFAULT_DOCS)):
        path = ROOT / doc
        if not path.exists():
            failures.append(f"required review/doc-site document is missing: {doc}")
    return failures


def _check_release_targets() -> list[str]:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    failures: list[str] = []
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    for fragment in REQUIRED_RELEASE_CHECK_FRAGMENTS:
        if fragment not in release_check_body:
            failures.append(f"release-check does not include {fragment}")
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    previous_index = -1
    for step in REQUIRED_REVIEW_CANDIDATE_STEPS:
        index = review_candidate_body.find(step)
        if index == -1:
            failures.append(f"review-candidate does not include {step}")
            continue
        if index < previous_index:
            failures.append(f"review-candidate step is out of order: {step}")
        previous_index = index
    for target in [
        "release-evidence-validate:",
        "release-evidence-gate:",
        "review-packet-diff:",
        "review-packet-diff-gate:",
        "packet-redaction-scan:",
        "reviewer-findings-check:",
        "review-findings-summary:",
        "review-run-manifest-check:",
    ]:
        if target not in makefile:
            failures.append(f"Makefile is missing {target}")
    return failures


def _check_v04_horizontal_gate_status() -> list[str]:
    failures: list[str] = []
    manifest = yaml.safe_load(
        (ROOT / "docs/codex/v0.4-milestone-manifest.json").read_text(encoding="utf-8")
    )
    backlog = (ROOT / "docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    if manifest.get("completed_range") != "113-151":
        failures.append("v0.4 manifest completed_range is not 113-151")
    if manifest.get("planned_range") != V04_PLANNED_RANGE:
        failures.append(f"v0.4 manifest planned_range is not {V04_PLANNED_RANGE}")
    if "make release-evidence-gate" not in manifest.get("after_each_wave_required_commands", []):
        failures.append("v0.4 manifest does not require release-evidence-gate after each wave")
    diff_gate_command = (
        "make review-packet-diff-gate OLD=<prior checkpoint> NEW=<current checkpoint>"
    )
    if diff_gate_command not in manifest.get("after_each_wave_required_commands", []):
        failures.append("v0.4 manifest does not require review-packet-diff-gate after each wave")
    milestones = {
        str(milestone.get("id")): milestone
        for milestone in manifest.get("milestones", [])
        if isinstance(milestone, dict)
    }
    for task_id in REQUIRED_V04_DONE_TASKS:
        milestone = milestones.get(task_id)
        if milestone is None:
            failures.append(f"v0.4 manifest missing Task {task_id}")
            continue
        if milestone.get("status") != "done":
            failures.append(f"Task {task_id} is not marked done in v0.4 manifest")
        marker = f"| {task_id} - "
        matching_lines = [line for line in backlog.splitlines() if line.startswith(marker)]
        if not matching_lines:
            failures.append(f"implementation backlog missing Task {task_id}")
        elif "| Done |" not in matching_lines[0]:
            failures.append(f"Task {task_id} is not marked Done in implementation backlog")
    for task_id in REQUIRED_V04_METADATA_TASKS:
        milestone = milestones.get(task_id)
        if milestone is None:
            continue
        if milestone.get("deferred_boundary_must_remain_unchanged") is not True:
            failures.append(f"Task {task_id} does not preserve deferred boundary metadata")
    return failures


def _check_deferred_tool_powers_absent_from_manifests() -> list[str]:
    failures: list[str] = []
    for manifest_path in sorted((ROOT / "tool-manifests").glob("*.y*ml")):
        text = manifest_path.read_text(encoding="utf-8").lower()
        for marker in DEFERRED_TOOL_POWER_MARKERS:
            if marker in text:
                failures.append(
                    f"{manifest_path.relative_to(ROOT)} appears to reference deferred "
                    f"tool power {marker!r}"
                )
    return failures


def _check_v03_wave5_status() -> list[str]:
    backlog = (ROOT / "docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    failures: list[str] = []
    for task_id in REQUIRED_V03_DONE_TASKS:
        marker = f"| {task_id} - "
        matching_lines = [line for line in backlog.splitlines() if line.startswith(marker)]
        if not matching_lines:
            failures.append(f"implementation backlog missing Task {task_id}")
            continue
        if "| Done |" not in matching_lines[0]:
            failures.append(f"Task {task_id} is not marked Done in implementation backlog")
    return failures


def _check_closure_matrix_v3() -> list[str]:
    text = (ROOT / "docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    failures: list[str] = []
    required_states = [
        "not_started",
        "internal_reviewed",
        "external_pending",
        "external_reviewed",
        "blocked",
        "fixed_pending_verify",
        "closed_local_preview",
        "accepted_deferred",
    ]
    if "## v3 Closure State" not in text:
        failures.append("source review closure matrix is missing v3 closure state")
    for state in required_states:
        if state not in text:
            failures.append(f"source review closure matrix is missing state: {state}")
    for line in text.splitlines():
        if not line.startswith("|") or "closed_local_preview" not in line:
            continue
        columns = [column.strip().lower() for column in line.strip("|").split("|")]
        if any(column in {"critical", "high"} for column in columns):
            failures.append("closed_local_preview row has open critical/high severity")
    return failures


if __name__ == "__main__":
    main()
