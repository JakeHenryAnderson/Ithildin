# EXT-TRUSTED-HOST-RUNTIME-003 Source Object Race

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-003
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: apps/api/src/ithildin_api/trusted_host_promotions.py; _read_source_artifact; apps/api/src/ithildin_api/read_tools.py; FilesystemReadTools.read_file_bytes
- Claim being tested: Source validation and artifact bytes must come from the same no-follow regular single-link file object.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found separate pathname inspection followed by Path.read_bytes, leaving object replacement possible between validation and read.
- Risk: A source path could change after validation and cause bytes from a symlink, hardlink, or different filesystem object to be staged.
- Recommended fix: Traverse directories with no-follow descriptors, open the final leaf without following links, and use fstat and read on that same descriptor.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: _read_source_artifact now delegates to the existing descriptor-bound FilesystemReadTools.read_file_bytes helper, which validates regular-file type, single-link count, size, and reads from the same opened descriptor. Focused tests and observed negative transcripts cover symlink, hardlink, and directory inputs. Exact-candidate independent re-review remains required.
