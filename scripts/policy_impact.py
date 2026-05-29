"""Compare a candidate YAML policy against committed policy fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.policy_impact import PolicyImpactError, PolicyImpactService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-path", type=Path, default=Path("policies/default.yaml"))
    parser.add_argument("--tests-path", type=Path, default=Path("policies/tests/default.yaml"))
    parser.add_argument("--candidate-path", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON results")
    args = parser.parse_args()

    service = PolicyImpactService(
        current_policy_path=args.policy_path,
        tests_path=args.tests_path,
    )
    try:
        result = service.preview_candidate_path(args.candidate_path)
    except PolicyImpactError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"policy impact error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        current = result["current"]
        candidate = result["candidate"]
        changed_cases = result["changed_cases"]
        print(
            "Policy impact: "
            f"current {current['passed']}/{current['case_count']} passed, "
            f"candidate {candidate['passed']}/{candidate['case_count']} passed, "
            f"{len(changed_cases)} changed cases"
        )
        for changed in changed_cases:
            print(f"- {changed['id']}: {', '.join(changed['changes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
