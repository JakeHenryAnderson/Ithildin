# Local v1 LV1-003 O4 Image-Readability Repair Exact Review

Status: `GO`

Date: 2026-07-25

## Exact Candidate

- Commit: `7cc1da575074895a7210c5f15a34ae136f4f932a`
- Tree: `b448eb922619e59af74275cf1070deb33b6813ef`
- Parent commit: `fbd2da4f26b24c9b1aa7fad4336eb99c5ccf9491`
- `deploy/Dockerfile.api`:
  `sha256:b0fba85ea070c8d2100d79b69db202f2a2ef35adae4e2497c3f0fe320341744a`
- `deploy/Dockerfile.node`:
  `sha256:28f989781bcfce6373a6eff8d13e68334f742c528c35c42a7463fcf01edadd21`
- `deploy/Dockerfile.ui`:
  `sha256:e562a3721c9750b747820f79b77c6d554be1d096d1f6a4dd0d371d83ce1aaa0a`
- `deploy/hermes-node-bridge/Dockerfile`:
  `sha256:82d992e42fa471cea5bbbd92c28d593e17368561f4442ed518cf53b148c6ca5d`
- `tests/test_container_image_runtime_readability.py`:
  `sha256:43295b57b2d7e368c5f6e735e812bc61349687aa84ee05b788a559fad9aab056`

The candidate changes exactly those five paths.

## Review Result

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-commit disposition is `GO`.

## Reviewed Trust Contract

The repair normalizes image content for runtime readability and traversal only. Its broad
normalization is limited to `a+rX`, which cannot add write permission. The UI configuration is
normalized to `0444`; the Hermes scratch directory alone is assigned to runtime UID/GID
`10000:10000` and mode `0700`. No other numeric or symbolic write-broadening mode and no other
`chown` target is allowed.

The API and Node final images run as exact non-root identities `10001:10001` and `10002:10002`.
The Hermes final stage returns to exact non-root identity `10000:10000` after its bounded
root-owned setup. The unprivileged Nginx final image receives no user override. All image-build
readability checks use valid unary `test -x`, `test -r`, or the single bounded Hermes scratch
`test -w`, each with exactly one operand.

The repair changes no Compose file, producer, runtime snapshot behavior, command vocabulary,
policy, manifest, governed tool, or governed power. The tests reject grouped unary operands,
write-broadening chmod modes, chmod after the final runtime user, unexpected ownership changes,
root final users, direct unnormalized UI copies, Compose changes, and snapshot assumptions.

## Validation Evidence

The exact candidate passed 190 focused tests, Ruff, strict mypy, the exact 24-tool invariant, the
no-new-powers gate, and the agent-workflow check. These checks and this review are evidence only;
they do not execute Attempt 008 or authorize release, promotion, production, credential custody,
or UAT.

## Authority

This review permits preparation of a separate exact Attempt 008 one-shot execution authorization
only. It does not execute Attempt 008, authorize retry or automatic retry, reopen Attempts 001
through 007 or the consumed image recovery, authorize evidence deletion, grant arbitrary host,
process, shell, or general Docker-socket product power, add a governed tool or power, or authorize
release, promotion, production, credential custody, or UAT.
