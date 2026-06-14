# project.release.summary Fixture Plan

Status: pre-implementation fixture/test contract only.
No runtime behavior.
Future tool: `project.release.summary`.
Proposed resource type: `project_release`.
Tool count remains `21`.
Runtime implementation remains blocked until a later sprint.

This document defines future fixture coverage and negative-test expectations only. It does not add
or approve runtime behavior, tool manifests, executors, policy rules, MCP exposure, API behavior,
UI runtime behavior, or new governed tool powers.

The committed JSON fixture corpus for this contract stays aligned with the scenario list below and
is checked by `make project-release-summary-preimplementation-check`.

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

## Scenario Contract

### empty workspace / no release-shaped files

- Fixture purpose: confirm the future tool reports a clean zero-result workspace without inventing
  release posture detail.
- Safe expected labels/count categories: zero release-shaped counts, zero skipped counts, zero
  truncation flags.
- Required non-leak assertions: strict non-leak list applies; no raw file names or raw paths.
- Future test type: source-review packet.

### release config files present by coarse category only

- Fixture purpose: confirm config-like release candidates are counted only by coarse category.
- Safe expected labels/count categories: release_config counts, safe_unknown counts, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw file names.
- Future test type: executor.

### changelog/release-note shaped files counted without names or contents

- Fixture purpose: confirm changelog-like and release-note-like candidates are counted without
  names or contents.
- Safe expected labels/count categories: changelog_category counts, release_note_category counts.
- Required non-leak assertions: strict non-leak list applies; no release names; no changelog
  contents.
- Future test type: MCP.

### version-marker shaped files counted without version strings

- Fixture purpose: confirm version-marker candidates are counted without leaking semantic version
  strings.
- Safe expected labels/count categories: version_marker counts, version_marker_category counts.
- Required non-leak assertions: strict non-leak list applies; no version strings.
- Future test type: executor.

### release automation shaped files counted without commands

- Fixture purpose: confirm automation-shaped candidates are counted without exposing command
  details.
- Safe expected labels/count categories: release_automation counts, automation_category counts.
- Required non-leak assertions: strict non-leak list applies; no command/script values.
- Future test type: governed call.

### mixed safe and skipped candidates

- Fixture purpose: confirm the future tool can mix safe counts with skip accounting without losing
  the boundary.
- Safe expected labels/count categories: mixed_safe counts, mixed_skipped counts, truncation flags
  remain false unless explicitly triggered.
- Required non-leak assertions: strict non-leak list applies; no raw file names or raw paths.
- Future test type: policy parity.

### depth-limit truncation

- Fixture purpose: confirm depth-limited traversal stops cleanly and reports truncation.
- Safe expected labels/count categories: depth_truncated, max_depth_hit, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### item-limit truncation

- Fixture purpose: confirm item-limited traversal stops cleanly and reports truncation.
- Safe expected labels/count categories: item_limit_truncated, max_items_hit, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### hidden/sensitive path skipped

- Fixture purpose: confirm hidden and sensitive paths are skipped rather than surfaced.
- Safe expected labels/count categories: hidden_path_skipped, sensitive_path_skipped, skipped
  counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths; no sensitive path
  disclosure.
- Future test type: policy parity.

### .git skipped

- Fixture purpose: confirm `.git` content is always skipped.
- Safe expected labels/count categories: git_skipped, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: policy parity.

### symlink skipped

- Fixture purpose: confirm symlink targets are skipped rather than traversed.
- Safe expected labels/count categories: symlink_skipped, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### hardlink skipped

- Fixture purpose: confirm hardlinks are skipped rather than double-counted or expanded.
- Safe expected labels/count categories: hardlink_skipped, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no raw paths.
- Future test type: executor.

### binary/NUL skipped

- Fixture purpose: confirm binary and NUL-containing candidates are skipped safely.
- Safe expected labels/count categories: binary_skipped, nul_detected, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no file contents.
- Future test type: audit.

### oversized input skipped

- Fixture purpose: confirm oversized candidates are rejected or skipped without surfacing raw
  content.
- Safe expected labels/count categories: oversized_skipped, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no file contents; no raw paths.
- Future test type: executor.

### unsupported encoding skipped

- Fixture purpose: confirm unsupported encodings are skipped safely.
- Safe expected labels/count categories: encoding_skipped, skipped counts.
- Required non-leak assertions: strict non-leak list applies; no file contents.
- Future test type: audit.

### malformed config shape counted as safe unknown

- Fixture purpose: confirm malformed config-shaped input falls back to a safe unknown category.
- Safe expected labels/count categories: safe_unknown, malformed_shape, skipped counts only if the
  file is rejected.
- Required non-leak assertions: strict non-leak list applies; no package names; no dependency
  names.
- Future test type: source-review packet.

### unauthorized principal denied in future governed-call tests

- Fixture purpose: confirm governed-call authorization rejects principals that lack access.
- Safe expected labels/count categories: denied_principal, authorization_denied.
- Required non-leak assertions: strict non-leak list applies; no author/maintainer names; no email
  addresses.
- Future test type: governed call.
