"""Verify runtime-candidate evidence before importing the API application."""

from __future__ import annotations

import logging

from runtime_candidate_bootstrap import (
    RuntimeCandidateVerificationError,
    verifier_from_environment,
)


def main() -> int:
    verifier = verifier_from_environment()
    verified_payload: dict[str, str] | None = None
    try:
        verified_payload = verifier.verify()
    except RuntimeCandidateVerificationError as exc:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).warning(
            "runtime candidate is unreviewed; trusted-host promotion remains unavailable: %s",
            exc,
        )

    import uvicorn
    from ithildin_api.app import create_app
    from ithildin_api.promotion_authority import RuntimeCandidateRecord

    candidate = (
        RuntimeCandidateRecord.model_validate(verified_payload)
        if verified_payload is not None
        else None
    )

    def reverify_candidate() -> RuntimeCandidateRecord:
        return RuntimeCandidateRecord.model_validate(verifier.verify())

    uvicorn.run(
        create_app(
            runtime_candidate=candidate,
            runtime_candidate_verifier=(
                reverify_candidate if verified_payload is not None else None
            ),
        ),
        host="0.0.0.0",
        port=8000,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
