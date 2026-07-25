# Local-v1 LV1-003 O4 Application Startup-Stage Diagnostic Exact Review

Status: `GO`

Date: 2026-07-25

## Exact Candidate

- Commit: `cce80b5cc71e9387237d18b588d294c39351a362`
- Tree: `4701443cd266cd86d6654a295f6277caddc117f2`
- `apps/api/src/ithildin_api/app.py`:
  `sha256:be8ad59f62dc71180e327ad044c481a4c916cbc42d043bfd88d749d4fbf30730`
- `apps/api/verified_launch.py`:
  `sha256:9c7a71bcc9c4643e203a578486b04ea392df1985b99b0da06a89973b20a96408`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:76f74c3c2b75ae8b320c5c12c3087b51a714ec1f9230a373a3d9335e9df0aca0`
- `tests/test_api_service.py`:
  `sha256:4c74e040294ccf216436bd729ab5f84536912d7cd17d5a3d587a57c7c5a69d2c`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:d7f0df7e818c43d83abe42b4e1c5d9d97e4fa05d8a7ef64927549a511d9f3a45`
- `tests/test_runtime_candidate_bootstrap.py`:
  `sha256:68cdceb283d5968ede0d589d46b96e0a9319bffd83a037105320ec4a21139896`

Independent GPT-5.6 Sol xhigh read-only review found Critical: 0, High: 0, Medium: 0,
Low: 0. The exact-commit disposition is `GO`.

## Reviewed Contract

The application emits only one of these 12 closed startup stages:

1. `launcher_entered`
2. `runtime_candidate_verification_entered`
3. `application_import_entered`
4. `application_factory_entered`
5. `server_run_entered`
6. `lifespan_configuration_entered`
7. `lifespan_persistence_entered`
8. `lifespan_governance_entered`
9. `lifespan_services_entered`
10. `startup_ready`
11. `shutdown_entered`
12. `shutdown_complete`

The API-owned marker is canonical ASCII JSON with exactly `record_type`, `schema_version`, and
`stage`. It is written through an owner-matching `0700` no-follow directory, an exclusive `0600`
temporary file, file synchronization, atomic replacement, and directory synchronization. Marker
write failure is best-effort and cannot change application behavior.

The producer may read the marker only after Compose `up` fails, the existing service diagnostic
classifies the API as `service_exited_nonzero`, and the existing container-state diagnostic
completes with `api_application_exit_nonzero_no_engine_error`. The read is exact-owner,
descriptor-anchored, no-follow, regular-file-only, and limited to 256 bytes. It accepts only the
canonical three-field schema and one of the 12 closed stages. Durable failure evidence retains
only `collection_status`, `collection_reason_code`, and normalized `last_emitted_stage`; missing or
unsafe input yields closed `unknown`.

The diagnostic does not scrape or persist logs, exceptions, tracebacks, error messages, raw
application output, environment, mounts, configuration, commands, credentials, prompts,
provider/model content, tool results, arbitrary paths, or dynamic stage values. A stage localizes
the last successful marker only; it does not establish a root cause or prove that the next attempt
will succeed. Primary failure, cleanup classification, recovery behavior, and the 24-tool governed
surface remain unchanged.

## Validation Evidence

The exact candidate passed 389 focused tests, Ruff, strict mypy, the no-new-powers gate, the exact
24-tool invariant, and the agent-workflow check. These checks are review evidence only; they do not
authorize execution, release, promotion, production, or UAT.

## Authority

This review permits preparation of a separate exact Attempt 007 one-shot execution authorization
only. It does not execute Attempt 007, authorize retry or automatic retry, reopen Attempts 001
through 006 or the consumed image recovery, authorize evidence deletion, or grant credential
custody, arbitrary host/process/shell authority, general Docker-socket product power, new tools or
powers, release, promotion, production, or UAT authority.
