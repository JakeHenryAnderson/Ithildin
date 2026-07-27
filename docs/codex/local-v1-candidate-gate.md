# Ithildin Local v1.0 Candidate Gate Record

## Exact binding

```text
candidate_commit=ab4162d8f4b6d3f45a68f33316f4b765a45765db
candidate_tree=25be9f049ca3ff3ccf6721100944e36baa0c3b05
candidate_tree_clean=true
local_v1_candidate_gate_returncode=0
```

The authoritative command was:

```sh
make local-v1-candidate-check
```

The raw local transcript was captured outside the repository with SHA-256
`4ab59b0de8ccfe1138e8239d42826b860d015fbb70017032d8f3e7e10c65942d`. This durable record contains
the bounded, non-sensitive result needed to bind candidate qualification without publishing
temporary paths or private run identifiers.

## Observed result

The gate passed against the exact clean candidate. Its fixed inventory included:

- the Local v1 completion, golden-path, milestone, tool-surface, and no-new-powers contracts;
- policy, approval, audit, redaction, migration, filesystem, evidence, determinism, adversarial, and
  runtime-trust checks;
- the current digest-bound O2 evidence and Mission Command focused gates;
- `1,428` candidate-scoped Python regression tests;
- Ruff and strict mypy for `75` shipped Python source files, `14` active Local v1 validators, and
  `4` active Mission Command validators;
- `66` UI tests, TypeScript checking, the production UI build, documentation generation, and the
  agent-workflow check.

The only warnings were the previously known non-failing pytest temporary-directory cleanup warnings
from closed LV1-003 receipt fixtures.

## Authority limits

This passing gate is candidate evidence only. It does not complete human UAT and does not authorize
release, promotion, production use, runtime execution, credential custody, a new governed tool, or
a new governed power. The governed tool count remains `24`.
