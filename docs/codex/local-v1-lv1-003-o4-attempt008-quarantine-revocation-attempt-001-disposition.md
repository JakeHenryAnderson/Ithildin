# Attempt 008 Four-Container Quarantine/Revocation Disposition

Status: **CONSUMED_FAILED_CLOSED**

Recovery `LV1-003-O4-ATTEMPT-008-QUARANTINE-REVOCATION-001` is closed at exact candidate
`cbf304512965fbd10df6b72b78777750ac4cc6d5`, tree
`654193cf9456433bcafc6da7c5dc6d2d076af54e`. Its fixed review tag remains immutable historical
evidence and must not be moved.

The first invocation failed before any Docker command because the reviewed empty-config helper
rejected the ambient macOS temporary-directory group. The authorized same-operation continuation
used an owner-only temporary root and reached only the exact project query. That query returned two
containers, while the candidate incorrectly required four, so it failed
`project_container_set_invalid` before `project-preinspection`.

Only `consumed.json` and `0001-identity-receipts-validated.json` exist in the bounded journal
sequence. Their exact sizes and SHA-256 digests are bound in the JSON disposition. No stop intent,
Docker mutation, storage alias, database mutation, audit append, evidence transition, or final
disposition occurred.

A separately bounded read-only diagnostic observed the exact reviewed API and UI containers exited.
Node and Hermes were `not_observed_in_exact_project_query_at_preinspection`; that is not a generic
container-absence, process-absence, or host-wide exclusivity claim. Their earlier status remains
`not_targeted_by_prior_recovery`.

The unrelated `uv` lock under the private receipt root is preserved outside current authority.
Cleanup, old-receipt mutation, tag movement, another resume, and retry are not authorized. Attempt
budget is zero. This closure grants no successor O4 execution, release, or UAT authority, and the
governed tool count remains 24.
