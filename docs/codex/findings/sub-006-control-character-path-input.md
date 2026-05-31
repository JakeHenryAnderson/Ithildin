# SUB-006 Control Character Path Input

- Finding ID: SUB-006
- Severity: medium
- Area: filesystem path input validation
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; _reject_ambiguous_path_input; FilesystemReadTools.resolve_existing_path
- Claim being tested: ambiguous path input fails closed with safe `ReadToolError` messages.
- Observed behavior: NUL bytes and other C0/DEL control characters were not explicitly rejected before path construction and filesystem calls.
- Risk: Some malformed paths could escape as raw platform exceptions or create confusing review/audit behavior instead of consistent safe denials.
- Recommended fix: Reject NUL, C0 controls, and DEL in the shared path ambiguity check.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `_reject_ambiguous_path_input` now rejects control characters before `Path` construction and tests cover NUL, newline, and DEL path inputs. External/source review remains pending.
