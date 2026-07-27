# Enterprise E1 M5 Observed Results

Status: `E1-M5` engineering checkpoint complete. This is an exact exporter rehearsal and local
integrity receipt, not a live-site operational snapshot, origin authentication, external delivery,
release acceptance, or human UAT.

## Exact state

- Branch: `codex/enterprise-single-site-operations`
- Exporter commit: `8f010f54e12534ecc08b43433762074209d545d2`
- Evidence schema: `ithildin.enterprise-e1-operational-evidence.v1`
- Input schema: `ithildin.enterprise-e1-operations-input.v1`
- Governed tools: `24`
- Sections: `7`
- External delivery performed: `false`
- Human UAT complete: `false`

## Deterministic rehearsal

The CLI built the same explicit input twice into different new output directories:

```text
var/enterprise-e1-operations-bundle/20260727T181500Z-8f010f5-a
var/enterprise-e1-operations-bundle/20260727T181500Z-8f010f5-b
```

Both receiver-neutral ZIP archives were byte-identical:

```text
archive_sha256:
  2d88352db600b96a04f4fae90f3ea2691092e874c8381651c5805a01280a8b84
content_root_sha256:
  bce672a1f7cfa153cc82d76856c92a01e5320d50fd2b18fe5b181ff253fb1dc1
member_count: 10
section_count: 7
tool_count: 24
```

`cmp` reported equality. The offline verifier returned the same content root for the materialized
directory and the ZIP. Both builds reported zero redaction-scan findings.

The retained ignored input binds real M1-M4 engineering observations where they exist. Its
mission, fleet, approval, and audit sections explicitly say they are focused contract/interaction
evidence and set their live-site snapshot flags to `false`. The rehearsal therefore proves export
composition and deterministic verification, not current activity at a deployed site.

## Focused validation

`make enterprise-e1-evidence-check` passed:

- machine contract and static source bindings;
- seven pytest cases covering the E1 wrapper plus the existing redactor;
- byte-identical ZIP generation;
- recursive secret and local-path redaction;
- directory and ZIP verification;
- rejection of missing sections, existing outputs, content mutation, and unmanifested files;
- Ruff and strict mypy.

The following boundary gates also passed:

```text
make tool-surface-invariant-gate
make no-new-powers-guardrail
git diff --check
```

Pytest emitted only the repository's existing temporary-directory cleanup warnings after the seven
tests passed.

## Evidence limits

- SHA-256 verification proves local consistency relative to the included manifest; the manifest
  and receipt are not self-authenticating.
- The ZIP is not a signed audit export, external notarization, non-repudiation mechanism, or hosted
  custody record.
- Input collection remains an operator or existing authenticated Gateway-export responsibility;
  the wrapper does not query a Gateway, database, Node, runner, provider, host, SIEM, or receiver.
- No SIEM custody, hosted telemetry, whole-host coverage, compliance automation, production
  identity, enterprise production readiness, or human acceptance is claimed.

The exact E1 candidate will generate its own candidate-bound bundle during `E1-M6`; this M5 receipt
is implementation evidence and is not relabeled as candidate qualification.
