# project.release.summary Negative Transcript Plan

Status: future negative-transcript plan only.
No runtime behavior.

This plan defines the future negative transcript coverage for `project.release.summary`. It does
not add runtime behavior, a tool manifest, an executor, policy rules, API/MCP behavior, UI
runtime behavior, approval/audit logic, or new governed tool powers.

## Strict Non-Leak List

- no release names;
- no version strings;
- no changelog contents;
- no tag names;
- no branch names;
- no raw file names;
- no raw paths;
- no file contents;
- no package names;
- no dependency names;
- no author/maintainer names;
- no email addresses;
- no command/script values;
- no environment names/values;
- no registry URLs;
- no shell/Git/package-manager/CI output.

## Future Scenarios

### traversal denied

- expected safe status: denied;
- expected safe reason label: traversal_denied;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: executor test.

### absolute root denied

- expected safe status: denied;
- expected safe reason label: absolute_root_denied;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: governed call.

### hidden/sensitive path skipped

- expected safe status: skipped;
- expected safe reason label: hidden_sensitive_skipped;
- required non-leak assertions: strict non-leak list applies; no raw file names; no raw paths;
- future evidence source: policy parity.

### .git skipped

- expected safe status: skipped;
- expected safe reason label: git_skipped;
- required non-leak assertions: strict non-leak list applies; no raw file names; no raw paths;
- future evidence source: policy parity.

### symlink skipped

- expected safe status: skipped;
- expected safe reason label: symlink_skipped;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: executor test.

### hardlink skipped

- expected safe status: skipped;
- expected safe reason label: hardlink_skipped;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: executor test.

### binary/NUL skipped

- expected safe status: skipped;
- expected safe reason label: binary_nul_skipped;
- required non-leak assertions: strict non-leak list applies; no file contents;
- future evidence source: audit.

### unsupported encoding skipped

- expected safe status: skipped;
- expected safe reason label: unsupported_encoding_skipped;
- required non-leak assertions: strict non-leak list applies; no file contents;
- future evidence source: audit.

### depth limit truncation

- expected safe status: truncated;
- expected safe reason label: depth_limit_truncated;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: executor test.

### item limit truncation

- expected safe status: truncated;
- expected safe reason label: item_limit_truncated;
- required non-leak assertions: strict non-leak list applies; no raw paths;
- future evidence source: executor test.

### release names suppressed

- expected safe status: suppressed;
- expected safe reason label: release_name_suppressed;
- required non-leak assertions: strict non-leak list applies; no release names;
- future evidence source: generated negative transcript.

### version strings suppressed

- expected safe status: suppressed;
- expected safe reason label: version_string_suppressed;
- required non-leak assertions: strict non-leak list applies; no version strings;
- future evidence source: generated negative transcript.

### changelog contents suppressed

- expected safe status: suppressed;
- expected safe reason label: changelog_contents_suppressed;
- required non-leak assertions: strict non-leak list applies; no changelog contents;
- future evidence source: generated negative transcript.

### tag names suppressed

- expected safe status: suppressed;
- expected safe reason label: tag_name_suppressed;
- required non-leak assertions: strict non-leak list applies; no tag names;
- future evidence source: generated negative transcript.

### branch names suppressed

- expected safe status: suppressed;
- expected safe reason label: branch_name_suppressed;
- required non-leak assertions: strict non-leak list applies; no branch names;
- future evidence source: generated negative transcript.

### command/script values suppressed

- expected safe status: suppressed;
- expected safe reason label: command_script_value_suppressed;
- required non-leak assertions: strict non-leak list applies; no command/script values;
- future evidence source: generated negative transcript.

### unauthorized principal denied

- expected safe status: denied;
- expected safe reason label: unauthorized_principal_denied;
- required non-leak assertions: strict non-leak list applies; no author/maintainer names; no
  email addresses;
- future evidence source: MCP or audit.
