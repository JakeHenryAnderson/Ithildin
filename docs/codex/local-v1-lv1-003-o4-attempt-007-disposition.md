# Local v1 LV1-003 O4 Attempt 007 Disposition

Status: `ATTEMPT_007_CONSUMED_PRELAUNCH_IMAGE_READABILITY_INVESTIGATION_REQUIRED_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-007` is consumed. The budget is zero, retry and automatic retry are
false, and all 19 authority fields are false. No further execution, image recovery, evidence
deletion, release, promotion, production action, or UAT action is authorized.

## Exact Attempt And Diagnostic

The attempted candidate was `a2f0338a045dd15352c77cb1841f2098013b1f86`, tree
`04a5dbe34b604c95eb5a63bbfc9610b1033bf521`. Run
`20260725T194808Z-1993a10f` used Compose project
`ithildin-local-v1-o4-1993a10f` and failed with `base_services_start_failed`.

Both base and bridge builds completed and stage `7` was reached. The API was
`service_exited_nonzero`; the UI was `service_created`. The API container-state diagnostic
reported `api_application_exit_nonzero_no_engine_error` with health `unhealthy`.

The application startup-stage diagnostic was `inconclusive`, with reason
`application_startup_stage_missing` and stage `unknown`. Marker absence means either failure before
the first checkpoint or an unusable diagnostic channel. This record does not choose between those
possibilities and does not establish a root cause.

The four exact identities were:

1. `ithildin/api-o4:1993a10f` —
   `sha256:686096ac390a1d3d169c8a146d873b08d9fde05d96a7b6ea78a40d47d6aa6b03`
2. `ithildin/ui-o4:1993a10f` —
   `sha256:8eb20fbc8457db83d7a127b630b01fb93323eedc4b4d7a745e534bd21b88a11d`
3. `ithildin/node-o4:1993a10f` —
   `sha256:1839df6ce76622b08a4dedf3abf63da4dcdcd02086ffec2683bf808fdf79c141`
4. `ithildin/hermes-node-bridge-o4:1993a10f` —
   `sha256:a0ab24b39cfc2ad24051004278c347ce86c3a1fb865724f0340e96365f6e958f`

## Cleanup And Retained Evidence

The cleanup failure list is empty and `recovery_required` is false. A separate exact-run-scoped
point-in-time postcheck observed all four references and IDs absent, exact-project containers,
volumes, and networks absent, the temporary Docker configuration removed, the Attempt 007 runtime
directory and plaintext absent, and only the prior recovery consumption receipt remaining. These
are point-in-time exact-run facts, not generic or ongoing Docker absence.

The exact owner-only `0700` receipt root is
`var/local-v1-lv1-003-o4-receipts/20260725T194808Z-1993a10f`. It retains:

- 128-byte disposition:
  `sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a`
- 7,438-byte diagnostic:
  `sha256:add06ef7d609b220e52d3ab0053a8521262d1dbc253b0d972cae83442f97cf10`
- 96,772-byte manifest:
  `sha256:73219848ccef6715ee7c1f3fb5356ecced8db36eea58bc449cf64d37e7197998`
- 664-file exact candidate snapshot

The validator preserves Attempts 002 through 007 receipts and the consumed Attempt 003 recovery
receipt. Missing, changed, extra, symlink, or special evidence fails closed.

## Exact Closure And Next Action

No future child commit or tree is stated. The closure accepts only a clean direct child of the
attempted candidate with exactly eight changed paths: Makefile, README, this JSON/Markdown pair,
the authorization JSON/Markdown pair, the validator, and its focused test.

The next action is a separately reviewed pre-launch Docker image-readability repair investigation.
It must not scrape logs or claim a proven root cause. This closure includes no producer, API,
runtime, policy, or manifest change and grants no execution authority.
