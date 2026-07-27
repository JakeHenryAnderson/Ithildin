# Enterprise E1 Human UAT Packet

Status: ready for a genuine human operator; unexecuted. Stop the implementation lane here.

This packet tests the exact E1 candidate with synthetic local data at one trusted site. It does not
authorize production credentials, production identity, runtime PostgreSQL, hosted operation,
release acceptance, production promotion, or any external-system action.

## Qualified candidate

- Commit: `02e39d57a6d38a14d959bb88a32da79fe34e4e13`
- Tree: `9850b6cbd40742d67388527de802961ddef306bd`
- Dedicated candidate gate: `PASS`
- Independent review: `GO`; Critical `0`, High `0`, Medium `0`, Low `0`
- Human UAT complete: `false`
- Enterprise production ready: `false`
- Local v1 release accepted: `false`

Read
[`enterprise-e1-candidate-gate.md`](enterprise-e1-candidate-gate.md),
[`enterprise-e1-independent-review.md`](enterprise-e1-independent-review.md), and
[`enterprise-e1-human-uat-record-template.md`](enterprise-e1-human-uat-record-template.md) before
starting.

## Operator prerequisites and stop conditions

Use a technical operator on a local engineering host with Git, Python 3.12 and `uv`, Node/npm,
Docker with Compose, and a supported browser. Use synthetic, non-sensitive data only. Do not install
the optional `pis3` dependency or provide a target, credentials, DSN, signing key, production
identity, or production data.

Abort and record `ABORTED` if candidate identity, checkout cleanliness, ownership, source/data
separation, ports, backup identity, runtime posture, cleanup target, or trust-source meaning is
ambiguous. Abort on a secret exposure, symlink or unsafe-mode rejection, accessibility blocker,
unexpected external connection, unrecognized container/resource, or any request to broaden
Ithildin's governed powers. Preserve ambiguous state and evidence; do not improvise destructive
cleanup.

## 1. Create an exact isolated checkout and record

Choose a new owner-controlled temporary root and add the exact detached worktree:

```sh
E1_UAT_ROOT="$(mktemp -d /tmp/ithildin-e1-uat.XXXXXX)"
git worktree add --detach "$E1_UAT_ROOT/repo" \
  02e39d57a6d38a14d959bb88a32da79fe34e4e13
cd "$E1_UAT_ROOT/repo"
test "$(git rev-parse HEAD)" = \
  02e39d57a6d38a14d959bb88a32da79fe34e4e13
test "$(git rev-parse HEAD^{tree})" = \
  9850b6cbd40742d67388527de802961ddef306bd
test -z "$(git status --porcelain=v1)"
uv sync --group dev
npm ci --prefix apps/ui
```

Copy the UAT record template outside the checkout and record the candidate, tree, date/timezone,
operator, host, Docker/Compose, browser, and any assistive technology. Do not put secrets or raw
local identifiers in the record.

## 2. Prepare the owner-only single-site environment

Follow [`deploy/single-site/README.md`](../../deploy/single-site/README.md). Copy
`deploy/single-site/env.example` outside the repository, replace every placeholder, and set mode
`0600`. Use:

- the exact commit above as `ITHILDIN_E1_SOURCE_REVISION`;
- unique unprivileged loopback API and UI ports;
- an absolute owner-only data root outside both repository and worktree;
- a random local admin token of at least 32 characters that is never printed or recorded;
- the operator's UID/GID; and
- `ITHILDIN_E1_EXPECTED_RUNTIME_POSTURE=unreviewed_local` with two separate owner-controlled,
  read-only empty-object sentinel files unless separately reviewed runtime inventory and detached
  authorization records exist for this exact candidate.

Do not relabel the E1 gate or independent review as runtime-candidate authorization. Run:

```sh
make enterprise-e1-single-site-bootstrap E1_ENV_FILE=/absolute/path/ithildin-e1.env
make enterprise-e1-single-site-config E1_ENV_FILE=/absolute/path/ithildin-e1.env
make enterprise-e1-single-site-up E1_ENV_FILE=/absolute/path/ithildin-e1.env
make enterprise-e1-single-site-health E1_ENV_FILE=/absolute/path/ithildin-e1.env
```

Record whether state ownership, secret placement, configuration rendering, authenticated 24-tool
health, Command Center reachability, and failure messages are understandable and fail-closed.

## 3. Inspect the operations cockpit

Open Command Center only on the configured loopback UI address. With keyboard and pointer as
applicable, inspect missions, Nodes/fleet, versions, configuration cohorts, Attention, approvals,
and evidence.

Confirm without implementation-agent coaching that:

1. Gateway-authoritative mission and approval state is not confused with runner-reported state.
2. Gateway-accepted Node heartbeat/connectivity is not presented as runner, host, or provider
   health.
3. Unknown model-provider state remains unknown.
4. Desired, acknowledged, stored, enforced, stale, rejected, and rollback configuration states
   remain distinct.
5. Existing governed initiation paths do not imply arbitrary host execution or Command Center
   execution authority.

Use only existing bounded synthetic workflows. Do not add or request shell, browser, process,
Docker-socket, Kubernetes, broad filesystem, or arbitrary-network capability.

## 4. Evaluate recovery guidance

Read [`enterprise-e1-recovery-contract.md`](enterprise-e1-recovery-contract.md) and run the
non-destructive focused gate:

```sh
make enterprise-e1-recovery-check
```

Assess whether clean stop, candidate-bound backup, failed-upgrade fail-closed behavior,
restore-only downgrade, optional-Node ambiguity, and exact cleanup are understandable and safe.
Do not simulate failure by corrupting or overwriting the active UAT data. If the operator elects to
run the isolated synthetic live rehearsal, use only:

```sh
make enterprise-e1-single-site-rehearsal
```

Treat it as a separate engineering observation, not proof of the active site's recovery or human
acceptance.

## 5. Build and verify a synthetic operations bundle

Copy `tests/fixtures/enterprise-e1-operations-input.json` outside the repository. Replace its
fixture candidate commit with the exact E1 commit, replace or remove intentionally sensitive
fixture values with synthetic values, and keep the schema, tool count, and seven section names
unchanged. Choose a new output path; do not reuse or precreate it.

```sh
uv run python scripts/enterprise_e1_operations_bundle.py build \
  --input /absolute/path/synthetic-e1-input.json \
  --output-dir /absolute/path/new-e1-bundle
uv run python scripts/enterprise_e1_operations_bundle.py verify \
  --bundle /absolute/path/new-e1-bundle
uv run python scripts/enterprise_e1_operations_bundle.py verify \
  --bundle /absolute/path/new-e1-bundle.zip
```

Inspect the canonical directory, ZIP, redaction manifest, and receipt. Confirm that no supplied
secret or local path appears and that the bundle does not imply whole-host coverage, SIEM custody,
hosted telemetry, external notarization, compliance automation, release acceptance, or production
readiness. If publication fails after reservation, preserve the partial final set for inspection;
the builder intentionally removes only its private staging directory.

## 6. Accessibility and constrained-layout pass

Complete the cockpit flow with keyboard-only navigation. Check visible focus, logical order,
status/error announcements, labels, and recovery from validation errors. Repeat at 200% browser
zoom and a narrow viewport without hiding required state meaning or actions. Record the exact
browser and any screen reader or other assistive technology used. A discovered blocker is a UAT
finding, not permission for an unreviewed implementation change during the session.

## 7. Shutdown, cleanup, and result

Stop only the exact configured site project:

```sh
make enterprise-e1-single-site-down E1_ENV_FILE=/absolute/path/ithildin-e1.env
```

Confirm the owner-held data, evidence, environment, and runtime records remain after shutdown.
Remove only exact synthetic resources whose ownership and candidate identity are recognized.
Retain ambiguous state and partial bundle reservations. Remove the detached worktree from the
original repository only after the exact path is confirmed.

Complete the external UAT record as `PASS`, `FAIL`, or `ABORTED`, including findings and
evidence-safe reproduction. Even a human `PASS` does not itself authorize release, production
promotion, production credentials, PIS collection, or a public security-product claim.

The PIS next action remains
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
