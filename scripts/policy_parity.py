"""Run policy preview/runtime parity fixtures."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from ithildin_api.policy_parity import (
    DEFAULT_POLICY_PARITY_TESTS_PATH,
    PolicyParityError,
    run_policy_parity,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--tests-path", type=Path, default=DEFAULT_POLICY_PARITY_TESTS_PATH)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON results")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    try:
        if args.work_dir is None:
            with tempfile.TemporaryDirectory(prefix="ithildin-policy-parity-") as tmp:
                run = run_policy_parity(
                    repo_root=repo_root,
                    work_dir=Path(tmp),
                    tests_path=args.tests_path,
                )
        else:
            run = run_policy_parity(
                repo_root=repo_root,
                work_dir=args.work_dir,
                tests_path=args.tests_path,
            )
    except PolicyParityError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, sort_keys=True, indent=2))
        else:
            print(f"policy parity error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(run.as_dict(), sort_keys=True, indent=2))
    else:
        print(f"Policy parity: {run.passed}/{len(run.cases)} passed")
        for result in run.cases:
            if not result.passed:
                print(f"- {result.id}: {'; '.join(result.failures)}", file=sys.stderr)
    return 0 if run.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
