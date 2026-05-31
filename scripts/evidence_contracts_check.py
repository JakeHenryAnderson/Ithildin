"""Validate the local-preview evidence contract index."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from ithildin_schemas import JsonObject

CONTRACT_PATH = Path("docs/codex/evidence-contracts-v2.json")
CONTRACT_DOC_PATH = Path("docs/codex/evidence-contracts.md")
EXPECTED_CONTRACT_VERSION = "v0.4-local-preview-evidence-contract-v2"
REQUIRED_CONTRACTS = {
    "audit_event",
    "audit_jsonl_export",
    "signed_audit_export",
    "signed_manifest_lock",
    "release_evidence",
    "policy_decision_evidence",
    "approval_binding_evidence",
}


class EvidenceContractError(RuntimeError):
    """Raised when the evidence contract index is inconsistent."""


def validate_contract_index(path: Path = CONTRACT_PATH) -> JsonObject:
    try:
        document = cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceContractError(f"failed to load evidence contract index: {path}") from exc

    if document.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        raise EvidenceContractError("unsupported evidence contract version")
    if document.get("runtime_boundary") != "v0.1 local-preview":
        raise EvidenceContractError("evidence contract runtime boundary changed")

    compatibility_policy = document.get("compatibility_policy")
    if not isinstance(compatibility_policy, dict):
        raise EvidenceContractError("compatibility_policy must be an object")
    if (
        compatibility_policy.get("rename_remove_or_meaning_change")
        != "requires_new_contract_version_or_explicit_compatibility_note"
    ):
        raise EvidenceContractError("compatibility policy does not protect stable fields")

    raw_contracts = document.get("contracts")
    if not isinstance(raw_contracts, list):
        raise EvidenceContractError("contracts must be a list")

    seen_ids: set[str] = set()
    for raw_contract in raw_contracts:
        if not isinstance(raw_contract, dict):
            raise EvidenceContractError("contract entries must be objects")
        contract = raw_contract
        contract_id = contract.get("id")
        if not isinstance(contract_id, str) or not contract_id:
            raise EvidenceContractError("contract id must be a non-empty string")
        if contract_id in seen_ids:
            raise EvidenceContractError(f"duplicate evidence contract id: {contract_id}")
        seen_ids.add(contract_id)

        stable_fields = contract.get("stable_fields")
        if not isinstance(stable_fields, list) or not stable_fields:
            raise EvidenceContractError(f"{contract_id} must define stable_fields")
        if any(not isinstance(field, str) or not field for field in stable_fields):
            raise EvidenceContractError(f"{contract_id} stable_fields must be strings")

        format_version_field = contract.get("format_version_field")
        if format_version_field is not None:
            if not isinstance(format_version_field, str) or not format_version_field:
                raise EvidenceContractError(
                    f"{contract_id} format_version_field must be a string or null"
                )
            if not isinstance(contract.get("format_version"), str):
                raise EvidenceContractError(
                    f"{contract_id} must define a string format_version"
                )

    missing = REQUIRED_CONTRACTS - seen_ids
    if missing:
        raise EvidenceContractError(
            "missing required evidence contracts: " + ", ".join(sorted(missing))
        )

    doc_text = CONTRACT_DOC_PATH.read_text(encoding="utf-8")
    if EXPECTED_CONTRACT_VERSION not in doc_text:
        raise EvidenceContractError("evidence contract guide does not name v2 contract")
    if CONTRACT_PATH.name not in doc_text:
        raise EvidenceContractError("evidence contract guide does not link the index")

    return document


def main() -> int:
    try:
        document = validate_contract_index()
    except EvidenceContractError as exc:
        print(f"Evidence contract validation failed: {exc}", file=sys.stderr)
        return 1

    contracts = cast(list[JsonObject], document["contracts"])
    print(
        "Evidence contracts validated: "
        f"{document['contract_version']} ({len(contracts)} contracts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
