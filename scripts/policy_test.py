"""Run offline policy decision fixtures against the YAML policy evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ithildin_api.policy_testing import PolicyTestError, run_policy_tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-path", type=Path, default=Path("policies/default.yaml"))
    parser.add_argument("--tests-path", type=Path, default=Path("policies/tests/default.yaml"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON results")
    args = parser.parse_args()

    try:
        run = run_policy_tests(policy_path=args.policy_path, tests_path=args.tests_path)
    except PolicyTestError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, sort_keys=True, indent=2))
        else:
            print(f"policy test error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(run.as_dict(), sort_keys=True, indent=2))
    else:
        print(f"Policy tests: {run.passed}/{len(run.cases)} passed")
        for result in run.cases:
            if not result.passed:
                print(f"- {result.id}: {'; '.join(result.failures)}", file=sys.stderr)
    return 0 if run.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
