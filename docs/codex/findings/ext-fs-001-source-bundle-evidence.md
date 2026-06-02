# EXT-FS-001 Source Bundle Evidence

- Finding ID: EXT-FS-001
- Severity: medium
- Area: filesystem
- Affected files/functions: scripts/filesystem_source_review_bundle.py; apps/api/src/ithildin_api/read_tools.py; apps/api/src/ithildin_api/workspaces.py; apps/api/src/ithildin_api/filesystem_contract.py; apps/api/src/ithildin_api/patches.py; apps/api/src/ithildin_api/app.py; scripts/filesystem_contract_check.py; tests/test_read_tools.py; tests/test_patch_proposals.py; tests/test_security_regressions.py; tests/test_workspaces.py; tests/test_filesystem_contract_check.py
- Claim being tested: filesystem/platform external source-review closure requires actual source, focused tests, contract docs, command evidence, and artifact hashes rather than internal summaries alone.
- Observed behavior: GPT 5.5 Pro initially found the filesystem/platform lane ready for source review but not closeable because the consolidated packet included dispatch and internal summary evidence without attaching the implementation/test source bundle.
- Risk: Closing the filesystem/platform lane from packet summaries alone would conflate internal assurance with external source-level review and could overstate closure.
- Recommended fix: Generate and attach a focused filesystem/platform source-review bundle containing source files, focused tests, contract docs, filesystem-contract-check output, `/system/status.filesystem` evidence, and artifact hashes.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `make filesystem-source-review-bundle` now builds the focused filesystem/platform source/test/evidence handoff under ignored `var/review-packets/v0.7/filesystem-source-review/`. GPT 5.5 Pro source-level review of that bundle at commit `48b2a5f5ee3b173953780d03ae3985a0a64df104` found `EXT-FS-001` closed, recorded no new implementation findings, and said the filesystem/platform lane can close for the v0.1 local-preview boundary. The normalized response is stored under ignored `var/review-runs/v0.7/filesystem/normalized-response.json`; focused filesystem tests and `make release-check` pass.
