"""Validate Ithildin's adversarial corpus manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("tests/fixtures/adversarial_corpus_manifest.json")
VALID_STATUSES = {"implemented", "planned", "deferred"}


class AdversarialCorpusError(RuntimeError):
    """Raised when the adversarial corpus manifest is invalid."""


@dataclass(frozen=True)
class CorpusSummary:
    version: str
    count: int
    implemented: int
    ids: tuple[str, ...]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    summary = validate_manifest(args.manifest)
    if args.json_output:
        print(
            json.dumps(
                {
                    "version": summary.version,
                    "count": summary.count,
                    "implemented": summary.implemented,
                    "ids": list(summary.ids),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            "Adversarial corpus manifest passed: "
            f"{summary.implemented}/{summary.count} implemented"
        )
        for corpus_id in summary.ids:
            print(f"- {corpus_id}")
    return 0


def validate_manifest(manifest_path: Path = DEFAULT_MANIFEST) -> CorpusSummary:
    if not manifest_path.exists():
        raise AdversarialCorpusError(f"corpus manifest is missing: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdversarialCorpusError(f"corpus manifest is invalid JSON: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise AdversarialCorpusError("corpus manifest must be a JSON object")
    version = _required_string(payload, "version")
    corpora = payload.get("corpora")
    if not isinstance(corpora, list) or not corpora:
        raise AdversarialCorpusError("corpus manifest requires a non-empty corpora list")

    seen: set[str] = set()
    ids: list[str] = []
    implemented = 0
    for index, raw_entry in enumerate(corpora):
        if not isinstance(raw_entry, dict):
            raise AdversarialCorpusError(f"corpus entry {index} must be an object")
        corpus_id = _required_string(raw_entry, "id")
        if corpus_id in seen:
            raise AdversarialCorpusError(f"duplicate corpus id: {corpus_id}")
        seen.add(corpus_id)
        ids.append(corpus_id)
        _required_string(raw_entry, "area")
        artifact = Path(_required_string(raw_entry, "artifact"))
        if artifact.is_absolute() or ".." in artifact.parts:
            raise AdversarialCorpusError(f"corpus artifact path is not repo-relative: {artifact}")
        if not artifact.exists():
            raise AdversarialCorpusError(f"corpus artifact is missing: {artifact}")
        _required_string(raw_entry, "command")
        status = _required_string(raw_entry, "status")
        if status not in VALID_STATUSES:
            raise AdversarialCorpusError(f"unknown corpus status for {corpus_id}: {status}")
        categories = raw_entry.get("categories")
        if (
            not isinstance(categories, list)
            or not categories
            or not all(isinstance(category, str) and category for category in categories)
        ):
            raise AdversarialCorpusError(f"corpus {corpus_id} requires string categories")
        if len(set(categories)) != len(categories):
            raise AdversarialCorpusError(f"corpus {corpus_id} has duplicate categories")
        if status == "implemented":
            implemented += 1

    return CorpusSummary(
        version=version,
        count=len(corpora),
        implemented=implemented,
        ids=tuple(ids),
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AdversarialCorpusError(f"corpus manifest requires string field: {key}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
