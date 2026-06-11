"""Local-only task triage inspired by model-router difficulty packets.

This script deliberately does not call a model, proxy prompts, or send data over the network. It
turns operator-supplied text into a small difficulty/risk summary that can help decide whether to
keep a task local, split it, trim context, or reserve a stronger external review pass.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

FILE_PATTERN = re.compile(
    r"\b[\w./-]+\.(?:py|ts|tsx|js|jsx|md|json|ya?ml|toml|rego|sql|sh|css|html)\b"
)

EXACT_PATTERNS = (
    re.compile(r"\b(reply|respond|print|say) with exactly\b", re.IGNORECASE),
    re.compile(r"\b(fix typo|rename|format|prettier|black|ruff format)\b", re.IGNORECASE),
)
TEST_PATTERNS = (
    re.compile(r"\b(test|pytest|vitest|unit test|regression|failing check)\b", re.IGNORECASE),
)
ERROR_PATTERNS = (
    re.compile(
        r"\b(traceback|stack trace|exception|typeerror|valueerror|runtimeerror)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(failed|failure|crash|panic|segfault|500)\b", re.IGNORECASE),
)
RISK_PATTERNS = (
    re.compile(r"\b(auth|token|secret|password|credential|jwt|oauth|session)\b", re.IGNORECASE),
    re.compile(r"\b(billing|payment|stripe|invoice|customer data)\b", re.IGNORECASE),
    re.compile(r"\b(database|migration|schema|sql|postgres|sqlite)\b", re.IGNORECASE),
    re.compile(r"\b(deploy|production|kubernetes|terraform|docker|infra|ci)\b", re.IGNORECASE),
    re.compile(r"\b(security|sandbox|policy|permission|rbac|allowlist|redaction)\b", re.IGNORECASE),
)
MULTI_STEP_PATTERN = re.compile(
    r"\b(then|after that|also|and then|end to end|full|comprehensive|across)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PromptTriage:
    difficulty: int
    estimated_tokens: int
    file_count: int
    signals: dict[str, bool]
    recommendation: str
    rationale: tuple[str, ...]


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def triage_prompt(text: str) -> PromptTriage:
    normalized = text.strip()
    files = set(FILE_PATTERN.findall(normalized))
    estimated = estimate_tokens(normalized)
    signals = {
        "exact_or_mechanical": any(pattern.search(normalized) for pattern in EXACT_PATTERNS),
        "tests": any(pattern.search(normalized) for pattern in TEST_PATTERNS),
        "error_or_stack": any(pattern.search(normalized) for pattern in ERROR_PATTERNS),
        "risk_domain": any(pattern.search(normalized) for pattern in RISK_PATTERNS),
        "multi_file": len(files) > 1,
        "multi_step": bool(MULTI_STEP_PATTERN.search(normalized)),
        "large_context": estimated >= 8_000,
    }

    score = 1
    rationale: list[str] = []
    if signals["exact_or_mechanical"]:
        rationale.append("mechanical or exact-output task")
    if signals["tests"]:
        score += 1
        rationale.append("mentions tests or regression work")
    if signals["error_or_stack"]:
        score += 1
        rationale.append("mentions failures, exceptions, or stack traces")
    if signals["multi_file"]:
        score += 1
        rationale.append("mentions multiple files")
    if signals["multi_step"]:
        score += 1
        rationale.append("multi-step request")
    if signals["risk_domain"]:
        score += 1
        rationale.append("security, auth, data, infra, or release-sensitive domain")
    if signals["large_context"]:
        score += 1
        rationale.append("large supplied context")
    if not rationale:
        rationale.append("bounded single-request task")

    difficulty = max(1, min(5, score))
    if difficulty <= 2:
        recommendation = "local_small"
    elif difficulty == 3:
        recommendation = "standard"
    elif signals["risk_domain"]:
        recommendation = "strong_review"
    else:
        recommendation = "split_or_strong"

    return PromptTriage(
        difficulty=difficulty,
        estimated_tokens=estimated,
        file_count=len(files),
        signals=signals,
        recommendation=recommendation,
        rationale=tuple(rationale),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="task text to classify locally")
    source.add_argument("--file", type=Path, help="read task text from a local file")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    text = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
    result = triage_prompt(text)
    payload = asdict(result)
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local prompt triage: "
            f"difficulty={result.difficulty} recommendation={result.recommendation}"
        )
        print(
            f"Estimated input tokens: {result.estimated_tokens}; "
            f"files mentioned: {result.file_count}"
        )
        for reason in result.rationale:
            print(f"- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
