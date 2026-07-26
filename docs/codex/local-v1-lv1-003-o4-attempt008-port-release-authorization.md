# Attempt 008 API/UI Port-Release Authorization

Status: `AUTHORIZED_UNCONSUMED_EXACT_ONE_SHOT`

Recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-001` is a separate, exact, one-shot
port-release suspension for the retained Attempt 008 project. Its parent is commit
`8211ba3ee0064dcf63d5eb80060d6ae4129fa4e1`, tree
`c5bf9fd82d76e9d48fdf93c0ea624f6e696bcd39`. The candidate must be its clean,
single-parent immediate child with the exact seven-path allowlist. No future candidate commit or
tree is claimed.

The budget is one and unconsumed. Retry and automatic retry are false. The persistent cross-process
claim is false; the immutable owner-only consumption receipt is still created with `O_EXCL` before
any Docker access, and an observed failure consumes the budget permanently.
Static candidate validity is separate from execution availability: a valid consumed lane remains a
valid static candidate with budget zero. Only a valid empty or missing lane is `unconsumed` with
budget one. Any nonempty invalid or unknown lane is `presumed_consumed_unknown`, has budget zero,
and is never executable.

## Narrow authority

The only true authority is retained-receipt validation, exact-project container inspection, exact
API/UI stop, point-in-time port-release observation, and private receipt writing. The sealed
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

The private evidence lane is repository-descriptor anchored. Its append-only journal uses owner-only
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

The only mutation targets are the unique exact Attempt 008 API and UI containers. Node and Hermes
are never stop targets. Final evidence distinguishes Node/Hermes observed unchanged from resources
that were only not targeted by recovery; it never converts a no-delete/no-stop boundary into an
unobserved preservation claim. The named Node volume, project network, all four images, retained
runtime and receipts remain outside mutation authority, while ambiguous enrollment posture and lack
of a revocation claim remain explicit.
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

`make local-v1-lv1-003-o4-attempt008-port-release-run` is the separate live operator entrypoint.
It is excluded from aggregate gates and must not run until an exact-candidate review authorizes
execution. This authorization record is evidence only; it is not execution, release, or UAT.
