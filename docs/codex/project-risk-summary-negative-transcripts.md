# project.risk.summary Negative Transcript Plan

Status: preimplementation negative transcript plan.

This plan lists the denial and non-leak scenarios that must be captured after a future
`project.risk.summary` implementation exists. It does not add runtime behavior.

## Required Scenarios

- traversal denied;
- absolute root denied;
- encoded ambiguity denied;
- control-character input denied;
- unknown argument denied;
- malformed `include_categories` denied;
- hidden/sensitive path skipped;
- `.git` skipped;
- .git skipped;
- symlink skipped;
- hardlink skipped;
- binary/NUL skipped;
- unsupported encoding skipped;
- oversized input skipped;
- depth limit truncation;
- item limit truncation;
- filenames suppressed;
- raw paths suppressed;
- file contents suppressed;
- dependency names suppressed;
- package names suppressed;
- CVE IDs suppressed;
- advisory IDs suppressed;
- secret names suppressed;
- secret values suppressed;
- command/script values suppressed;
- scanner output suppressed;
- vulnerability findings suppressed;
- compliance findings suppressed;
- unauthorized principal denied.

## Strict Non-Leak Phrases

- no filenames;
- no raw paths;
- no file contents;
- no dependency names;
- no package names;
- no CVE IDs;
- no advisory IDs;
- no secret names;
- no secret values;
- no environment names/values;
- no command/script values;
- no registry URLs;
- no scanner output;
- no vulnerability findings;
- no compliance findings;
- no security findings;
- no shell/Git/package-manager/CI output.

## Transcript Shape

Future transcripts should record only:

- scenario;
- command or governed-call shape without raw sensitive arguments;
- expected safe denial or safe skip;
- observed safe status/reason;
- evidence pointer.

They must not include file contents, raw paths, dependency/package names, secret-like strings, scanner
output, vulnerability findings, CI output, stack traces, or raw filesystem errors.
