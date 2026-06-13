# XH-GITTAG-001 Git Tag Metadata Parser Negative Coverage

- Finding ID: XH-GITTAG-001
- Severity: low
- Area: git tag metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `_parse_tag_metadata_output`; tests/test_read_tools.py `test_git_tag_metadata_parser_rejects_ambiguous_or_malformed_rows`; tests/test_read_tools.py `test_git_tag_metadata_skips_annotated_non_commit_tag_targets`; tests/test_read_tools.py `test_git_tag_metadata_git_output_is_bounded`
- Claim being tested: `git.show.tag_metadata` should fail closed for ambiguous or malformed tag metadata and keep Git output bounded.
- Observed behavior: Internal High review found the implementation had fail-closed parser and output-budget branches, but focused tests did not directly exercise casefold ambiguity, malformed rows, unsupported namespaces, annotated non-commit tags, or the configured read-limit failure path.
- Risk: Future parser or subprocess-output drift could remove important fail-closed behavior without a focused regression tripwire.
- Recommended fix: Fixed by adding direct parser tests for ambiguous casefolded tag names, bad field counts, unsupported namespaces, an annotated non-commit tag target, and bounded Git output failure.
- Blocking status: later
- Disposition: fixed
- Verification notes: `test_git_tag_metadata_parser_rejects_ambiguous_or_malformed_rows`, `test_git_tag_metadata_skips_annotated_non_commit_tag_targets`, and `test_git_tag_metadata_git_output_is_bounded` cover the added negative paths.
