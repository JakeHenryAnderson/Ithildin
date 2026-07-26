# Attempt 008 API/UI Port-Release Authorization

Status: `CONSUMED_CLOSED_COMPLETED`

Recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-002` completed successfully on execution
candidate commit `66b4c1ca66a142466a2b487941488c072c1ec4d0`, tree
`63bf4b6060a8e3082d1b5fdbeb2437f1b7236dcf`. This closure candidate must be that
candidate's clean, single-parent immediate child with the exact seven-path allowlist. The execution
candidate binding remains historical and is not rebound to the closure commit.
Attempt 002 completed successfully.

Attempt 001, recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-001`, is closed separately by
[its exact disposition](local-v1-lv1-003-o4-attempt008-port-release-attempt-001-disposition.md).
It consumed its budget after `sealed_directory_invalid` before any Docker command, target
inspection, mutation, or port observation. Attempt 002 is a separate authority, not a retry of
Attempt 001, and derives no authority from that consumed disposition.

The Attempt 002 budget is zero and consumed. Retry and automatic retry are false, and execution
availability is false. The immutable owner-only consumption receipt was created with `O_EXCL`
before Docker access; the persistent cross-process claim is false. Static candidate validity is
separate from execution availability: this valid
consumed lane remains a valid static candidate with budget zero. Any receipt drift fails closed and
cannot reopen execution; an invalid nonempty lane remains `presumed_consumed_unknown`.

All five narrow granted authorities were exercised: retained-receipt validation, exact-project
container inspection, exact API/UI stop, point-in-time port-release observation, and private receipt
writing. No false authority was exercised. No successor O4 authority exists.

## Closed narrow authority

The only authority granted to the completed attempt was retained-receipt validation, exact-project
container inspection, exact API/UI stop, point-in-time port-release observation, and private
receipt writing. The sealed
inspection projection exposes only container ID, exact image ID, exact project/service labels,
running/status state, and published-port mappings.

Git is invoked only as the reviewed root-owned `/usr/bin/git`. The reviewed Docker source is never
executed. It is located at `/Applications/Docker.app/Contents/Resources/bin/docker` and reached by
the fixed `/usr/local/bin/docker` alias. Its reviewed size is `41043648` bytes and its required
digest is
`sha256:f3f8d9217542c530d26070b6a1f498452f717eb61d5839ef38f9a0f5d48c2b05`.
The implementation opens that source through a descriptor, copies it into a cryptographically
random private 0700 directory using an exclusive leaf, revalidates source metadata, size, and digest,
then executes only the sealed 0500 copy. Parent, directory, and file descriptors remain anchored for
the executor lifetime, and the sealed leaf is revalidated before and after every command. Cleanup is
required after use: successful cleanup removes the sealed leaf and private directory, while cleanup
failure is terminal and fails the run. Docker child PATH inheritance is false; a hostile ambient
`PATH` cannot select an executable.

For the sealed child directory and executable leaf, owner and mode are the permission boundary:
stable effective-UID ownership and exact 0700 or 0500 mode. The inherited gid is recorded and revalidated across the
descriptor and path views, but it is not permission-bearing and need not equal the process effective
group. This narrow correction reflects macOS `/private/tmp` group inheritance. It does not weaken
the separate group requirements for receipt directories or the reviewed Git/Docker source
executable identities.

The private evidence lane is repository-descriptor anchored. Its append-only journal used owner-only
`O_EXCL` leaves with file and directory `fsync`: complete pre-inspection precedes mutation, each
stop has durable intent and result/post-observation evidence when possible, and final projections
and individual point-in-time bind observations are recorded. Termination after durable intent
remains explicitly ambiguous rather than being reported as a completed stop.
Journal payloads are closed, events are unique, and only legal transition prefixes are valid. A
final disposition-intent is the last journal leaf and crosslinks the exact status, failure, outcome,
actions, before/after projections, preservation, and port observations. A disposition leaf is valid
only when it exactly equals the journal-derived disposition. A failure before pre-inspection may
contain only the exact default outcome. Missing disposition after a durable final intent remains
consumed evidence and never reopens retry authority.

Every receipt leaf read compares device, inode, size, modification time, change time, owner, group,
and mode across the path-before, opened descriptor, post-read descriptor, and path-after views.
Replacement and in-place same-size mutation therefore fail closed.

The only mutation targets were the unique exact Attempt 008 API and UI containers. Node and Hermes
are never stop targets. Node, Hermes, volumes, networks, images, and retained runtime and evidence
are recorded only as `not_targeted_by_recovery`; no observed-unchanged or absence claim is inferred.
Ambiguous enrollment posture and lack of a revocation claim remain explicit.
The exact run is `20260726T001909Z-d801f37b`, project
`ithildin-local-v1-o4-d801f37b`. API must retain
`127.0.0.1:8000->8000/tcp`; UI must retain `127.0.0.1:5173->8080/tcp`. The JSON authorization
binds all four full image IDs.

Container, volume, network, image, runtime, or evidence deletion; Node revocation; Node/Hermes stop;
Compose; project down; generic process or port-owner discovery; generic Docker queries; provider or
credential access; new governed power or tool; release, promotion, and UAT remain false. The tool
count remains 24.

Successful simultaneous loopback binds establish point-in-time port availability only. They make
no claim about future availability or a generic port owner, and do not complete full project
cleanup or confirm Node revocation.

## Entrypoints

`make local-v1-lv1-003-o4-attempt008-port-release-check` is fake-only and non-live.

`make local-v1-lv1-003-o4-attempt008-port-release-run` is retained as a closed operator entrypoint.
It now refuses before consumption, socket discovery, sealed executable creation, or any Docker
action because the budget is consumed and execution availability is false. This closure record is
evidence only. Release and UAT remain false.
