# External Review Recheck Loop

Task 205 documents the recheck loop.

1. Send the focused lane packet.
2. Normalize the external response.
3. Convert findings into structured records.
4. Fix or disposition findings.
5. Run focused tests plus `make release-check`.
6. Send a minimal recheck packet if the reviewer needs to confirm the fix.
7. Update the closure matrix only after source-level or packet-and-source evidence exists.

External/source review closure is incomplete, capability expansion is no-go, public/security-product
positioning is no-go, and no new governed tool powers may be added during the loop.
