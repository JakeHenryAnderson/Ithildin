# Enterprise E1-M3 Upgrade and Recovery Observed Results

Status: `E1-O3` and `E1-M3` complete as a bounded engineering checkpoint.

Both live-local legs ran against exact clean commit
`cd56a8ad1ef2f7b3509dc0beb8f51a2f9d8bb8d9`.

## Container operations leg

- Report:
  `var/local-v1-operations/20260727T175329Z-f70b1fa0f6d96f364290bf371ccab095/local-v1-operations.json`
- Independent report check: valid.
- Observed: fresh private state, exact candidate image build, Gateway health, Command Center HTTP,
  authenticated `24`-tool inventory, clean stop, manifest-equal backup, injected API exit `23`,
  unavailable failed endpoint, manifest-equal restore, owner-only restored files, recovered API/UI,
  exact project cleanup, and unique image removal.

## Gateway and optional-Node continuity leg

- Evidence root:
  `var/local-v1-failure-recovery/20260727T175500Z-e1a30001`
- Independent evidence check: valid.
- Candidate tree: `b439d6883344d38499cc10543a017ad8a4919d07`.
- Observed: Gateway restart continuity, replay rejection, partition fail-closed behavior,
  revocation, configuration drift, stale rollback conflict, stale acknowledgment rejection, fresh
  signed manual rollback, `stored_not_enforced`, runner-reported state only, and unknown
  model-provider state.

The container backup intentionally excludes optional Node state. The second leg proves the
continuity and fail-closed semantics used after a Gateway restart; it does not authorize automatic
Node-volume restoration. Ambiguous Node identity/configuration remains revoke-and-re-enroll.

## Boundary

This evidence does not prove every future upgrade failure, whole-host recovery, disaster recovery,
credential restoration, automatic rollback, HA, production durability, runner enforcement,
provider success, release acceptance, or UAT. The next ordered checkpoint is `E1-M4`.
