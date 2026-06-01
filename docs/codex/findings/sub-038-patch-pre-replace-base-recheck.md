# SUB-038 Patch Pre-Replace Base Recheck

- Finding ID: SUB-038
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/patches.py; _atomic_write_text; _verify_target_base_hash; PatchProposalService.apply_approved; tests/test_governed_tool_calls.py
- Claim being tested: Patch apply rejects stale-base changes that occur after apply preparation but before atomic replacement.
- Observed behavior: Internal proxy review found that _prepare_apply checked the base hash, but _atomic_write_text later only checked safe regular-file and hardlink state before os.replace. A concurrent regular-file content change between those steps could be overwritten.
- Risk: A race in the remaining pre-replace window could overwrite a changed file without stale-base denial.
- Recommended fix: Re-read and hash the currently opened target immediately before replacement, using the stored base hash as the expected value.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: _atomic_write_text now verifies the opened target's current text hash against the proposal base hash before replacement. Regression coverage is tests/test_governed_tool_calls.py::test_patch_apply_rechecks_base_immediately_before_replace.
