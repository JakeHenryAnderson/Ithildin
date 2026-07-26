# Attempt 008 Port Release Attempt 001 Disposition

Status: `CONSUMED_FAILED_BEFORE_DOCKER_COMMAND`

Attempt 001, recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-001`, was the exact
candidate at commit `1e57990b82d3c912bf158e0b06cbfb0ca417bb33`, tree
`b5fffdcc0b91f7d798763a0f1381fe78831ca22a`. It failed with
the observed failure code `sealed_directory_invalid`. The failure phase and cause are diagnosed
from the code path and host behavior: the private sealed-copy directory check rejected the
`/private/tmp` child because it inherited group `wheel` rather than the process effective group
`staff`.

The budget is zero, the attempt is consumed, execution availability is false, and retry authority
is false. The receipt outcome directly records both actions as `not_attempted`, empty before and
after projections, and empty port observations. From that default outcome and the journal containing
only the final disposition intent, the closure derives that no Docker command was executed, no
target container inspection or mutation occurred, and no point-in-time port observation occurred.
The lack of a leftover sealed directory is a separate operator post-failure filesystem observation.

The owner-only Attempt 001 evidence is bound exactly:

- `consumed.json`: 913 bytes,
  `sha256:ba871180cad089f4a325060167ea5bf6fa800010a0f12562b63d00e32ea7de49`
- `journal/0001-disposition-intent.json`: 666 bytes,
  `sha256:a8f8bbbc670d68392d0376d14a1754a81d9d556fa155699a95006f3d368a1ec3`
- `disposition.json`: 1172 bytes,
  `sha256:e87493b5e5aa2ff596180371bdb6ebb68172790cf4f769176af269a47b3098b1`

Attempt 002, recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-002`, requires its own separately
reviewed authority and is not a retry of Attempt 001. This disposition does not grant that
authority and does not authorize any Docker action, inspection, mutation, port observation,
release, promotion, or UAT. Attempt 001 exercised only retained-receipt validation and private
receipt writing. The granted narrow authority is recorded separately from exercised authority:
exact project inspection, exact API/UI stop, and point-in-time port observation were granted but
not exercised, and every forbidden target power remained both ungranted and unexercised. The
governed tool count remains 24. Release and UAT remain false.
