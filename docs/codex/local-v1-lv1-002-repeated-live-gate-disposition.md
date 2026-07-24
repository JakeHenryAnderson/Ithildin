# LV1-002 Repeated Live-Gate Disposition

Status: `STOP — repeated-gate condition reached`

- Local-v1 milestone: `LV1-002`
- Release outcome: `O3`
- Final attempted candidate: `f1fd02821706af691c0c933457f9fb6e5ce05af5`
- Milestone status: `in_progress`
- Outcome status: `not_started`
- Runtime authority: `false`
- Release, promotion, production identity/storage, and UAT authority: `false`
- Fourth live attempt in this recovery sprint: `not_authorized`

This record is a failure and cleanup disposition. It does not complete authenticated Node
onboarding, authorize another live attempt, or qualify a Local-v1 candidate.

## Why Work Stopped

The deliberate `make local-v1-node-journey` gate failed three candidate executions in this
recovery sequence:

| Attempt | Exact candidate | Safe failure | Mutation boundary | Disposition |
| --- | --- | --- | --- | --- |
| 1 | `7e7bfdd6912266638944dc415f32eda23d4b0fd5` | Python module import failed before the journey preflight. | No Docker command or local service mutation. | Repaired by exact-reviewed module entrypoint commit `3a041dfb4a4bc676069fa6e2cc9e144077c6143d`. |
| 2 | `3a041dfb4a4bc676069fa6e2cc9e144077c6143d` | `compose_configuration_invalid` | Local daemon selection and isolated state creation occurred; no image build, container start, or enrollment. | Safe failure report recorded; isolated state cleanup completed. Repaired by exact-reviewed isolated Compose-plugin commit `f1fd02821706af691c0c933457f9fb6e5ce05af5`. |
| 3 | `f1fd02821706af691c0c933457f9fb6e5ce05af5` | `compose_stack_health_timeout` | Exact preflight passed; run-specific API/UI images were built and the isolated stack start was attempted. No enrollment code was issued and no Node remote contact occurred. | Safe failure report recorded; exact project resources, volumes, images, and ignored runtime state were removed. |

A sandbox-only `local_port_8000_unavailable` result between attempts 1 and 2 is excluded from this
count: the application sandbox denied the localhost bind probe, and the same preflight passed when
the already approved local-only command ran outside that sandbox.

Repository instructions require the manager to stop when the same gate fails three times. No raw
container logs were opened, no fourth attempt was made, and the health timeout was not guessed into
a product claim.

## Retained Safe Evidence

Attempt 2:

- JSON: `var/local-v1-node-journey/20260724T111246Z-3dfe3835/local-v1-node-journey.json`
- JSON SHA-256: `d91a2035a8a21a9e9430301c79d8518bd869408c4efaa16d34ffa4c4a94095d9`
- Markdown: `var/local-v1-node-journey/20260724T111246Z-3dfe3835/local-v1-node-journey.md`
- Markdown SHA-256: `5a4777e34879bba24d2b30bbeadd6f697ea822366586a418a70beb109e5db7ed`

Attempt 3:

- JSON: `var/local-v1-node-journey/20260724T135621Z-19fdfa5f/local-v1-node-journey.json`
- JSON SHA-256: `d32b02802c29ab9140990eed092caa04cc3f99919b5bcb1504ea3f2f6f535c5f`
- Markdown: `var/local-v1-node-journey/20260724T135621Z-19fdfa5f/local-v1-node-journey.md`
- Markdown SHA-256: `964b273f7434630baf27940ebeb0a00b00389a88747a4a9911ea357eed679d39`

These ignored reports contain stable failure codes, redacted observations, cleanup results,
all-false authority fields, and explicit nonclaims. They are not successful evidence and the
success-only checker must reject them.

## Cleanup Verification

The attempt-3 report records:

- `compose_down_succeeded: true`
- `volumes_removed: true`
- `images_removed: true`
- `resources_absent: true`
- `runtime_state_removed: true`
- `recovery_required: false`

Independent read-only Docker queries after the failed command returned no exact
`ithildin-local-v1-node-19fdfa5f` containers, volumes, network, API/UI images, or
`ithildin/node-journey:19fdfa5f` image. The ignored runtime directory is empty. No Node identity was
created, so no revocation or ambiguous-enrollment recovery is required.

## Resume Boundary

A fresh, explicitly resumed LV1-002 recovery task should:

1. treat `compose_stack_health_timeout` as unresolved rather than infer an API or UI cause;
2. add the smallest secret-safe, component-specific health/exit diagnostic that does not expose raw
   container logs, environment, credentials, request bodies, or host metadata;
3. validate and independently review that diagnostic change against an exact clean candidate;
4. authorize at most one new live retry in that fresh recovery task; and
5. stop again on a Critical/High finding, unsafe diagnostic requirement, ambiguous cleanup, or the
   fresh task's repeated-gate rule.

The fresh task must preserve the fixed 24-tool surface, no arbitrary host control, local Unix
Docker-only execution, isolated credentials and state, server-derived Node identity, and the
separation between Gateway truth, Node connectivity, runner reports, and model-provider state.
