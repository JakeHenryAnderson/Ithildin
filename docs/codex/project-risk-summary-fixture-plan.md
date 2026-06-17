# project.risk.summary Fixture Plan

Status: preimplementation fixture contract.

This fixture plan defines the future regression coverage expected before `project.risk.summary`
runtime code is added. The future tool must stay count-only and label-only. It must not expose the
raw evidence behind the counts.

## Required Scenarios

- empty workspace / no risk-shaped files;
- coarse risk signal files present by category only;
- security config shaped files counted without names or contents;
- secrets-adjacent shaped files counted without secret names or values;
- dependency risk shaped files counted without dependency or package names;
- CI/deploy risk shaped files counted without workflow names or command values;
- mixed safe and skipped candidates;
- depth-limit truncation;
- item-limit truncation;
- category filter limits output categories;
- hidden/sensitive path skipped;
- `.git` skipped;
- .git skipped;
- symlink skipped;
- hardlink skipped;
- binary/NUL skipped;
- oversized input skipped;
- unsupported encoding skipped;
- malformed config shape counted as safe unknown;
- unauthorized principal denied in future governed-call tests.

## Strict Non-Leak List

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

## Future Fixture Shape

Future fixture cases should record only safe expectations:

- fixture ID;
- scenario label;
- future test type;
- safe expected labels;
- expected skipped-count categories;
- non-leak assertions.

The fixtures must be local temp-dir fixtures only. They must not require shell execution, package
manager execution, scanners, network access, Docker, Kubernetes, browser automation, registry access,
or real secrets.
