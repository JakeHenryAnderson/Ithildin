# Enterprise E1-M1 Single-Site Deployment Observed Results

Status: `E1-O1` and `E1-M1` complete as an engineering deployment checkpoint. This is observed
single-site lifecycle evidence, not an E1 release candidate, reviewed runtime authorization,
production readiness, release acceptance, promotion, or human UAT.

## Exact run

- Rehearsal command: `make enterprise-e1-single-site-rehearsal`
- Source commit: `1300f2d046f0f255c6a1a5206f0a9d318f36d24a`
- Source tree: `0d9b600f575ff45c839f9507e9ab252deb0e950b`
- Deployment version: `1.0.0-e1.0f27777da96e721a`
- Run ID: `20260727T173947Z-0f27777da96e721a`
- Local safe receipt:
  `var/enterprise-e1-single-site/20260727T173947Z-0f27777da96e721a/enterprise-e1-single-site-rehearsal.json`
- Receipt SHA-256:
  `2e823dec188880f473f7bdd4227d80cd90037bc9132895f1a707172b8c94a782`
- Observed Docker daemon version: `29.5.3`

The ignored receipt is retained only on the engineering host. The script and tests are the
reproducible repository-owned evidence path; this document binds the exact observed run without
committing private runtime state.

## Observations

The isolated fixed Compose profile built and started exactly the Gateway API and Command Center
UI. Both images reported the selected deployment version and exact source commit through OCI
labels. Both published ports were loopback-only. The API health endpoint and Command Center root
were reachable.

The authenticated Gateway status probe reported exactly `24` governed tools, SQLite as the runtime
backend, and runtime-candidate posture `unreviewed_local`. The latter was deliberate: E1-M1 used
read-only empty-object sentinels to demonstrate unavailable reviewed-candidate evidence and
verified that the launcher did not upgrade that posture. E1-M6 remains the only route to a
reviewed exact E1 runtime candidate.

After the explicit shutdown, the exact Compose project contained no containers. The state
snapshot contained two regular files, including `gateway/db/ithildin.sqlite3`, with manifest digest
`sha256:a147165dfeb57c801611124c7f339e56523c405e8b1f01b962f92080d754a431`.
No audit event had occurred, so an audit log was not present; this checkpoint does not use absence
as audit-export evidence.

The script then removed both unique images and all synthetic private state, token material, and
sentinels. A post-run Docker query found no matching E1 containers or images. It retained only the
secret-free receipt.

## Boundary result

- Ithildin received no Docker lifecycle authority or Docker socket.
- No optional Node, model provider, runtime PostgreSQL, arbitrary network allowlist, production
  identity, or hosted telemetry was included.
- Node connectivity, runner state, and model-provider state remained explicitly unknown or outside
  E1-M1.
- The run touched no ambient user data and authorized no new governed power.
- The passing rehearsal does not prove upgrade/recovery, fleet configuration, cockpit usability,
  unified evidence export, candidate qualification, independent review, or human UAT. Those remain
  ordered E1-M2 through E1-M6 work.

## Checkpoint disposition

`E1-O1` is complete because the repository now contains a reproducible, versioned non-development
single-site profile, closed preflight, authenticated health/status probe, bounded shutdown
workflow, static gate, isolated lifecycle rehearsal, and exact observed lifecycle evidence.
E1-M3 may reuse this deployment substrate, but its upgrade and recovery outcome remains separate
and incomplete. The next action is `E1-M2`.
