# Local v1 LV1-007 O2 Disposition

Status: `O2_COMPLETE_O8_CANDIDATE_WORK_IN_PROGRESS_NO_RELEASE_OR_UAT_AUTHORITY`

Exact evidence candidate `d873b9b5ac51a0374b612627b3b0b88d248e6895`, tree
`10da9ae74114cfe23f84d0497c4e721587392447`, passed the bounded real-agent rehearsal and its
separately invoked candidate-bound checker. This closes only the real-agent connection outcome
`O2` and moves `O8` and `LV1-007` into candidate work.

## Operator-visible result

One pinned operator-managed Hermes implementation used the existing local stdio MCP surface in
three fixed single-purpose turns:

1. one in-scope `fs.read` was allowed and completed;
2. one out-of-scope `fs.read` was denied before execution; and
3. one synthetic `sandbox.artifact.write_text` request required approval, created exactly one
   version-2 pending approval, and produced no write execution lifecycle.

Gateway policy, execution, approval, and audit evidence is authoritative. Hermes process exits
remain runner observations, and Ollama remains a model-provider dependency observation. The
evidence does not claim a persistent Hermes identity, user identity, host sandbox, or inability for
Hermes to act outside Ithildin.

## Evidence and review posture

The sole passing report is mode `0600`, 2,100 bytes, and bound by digest
`sha256:f2e3a6753bdf96156f229fe42009255dab5b14270fdfcceb04f5074405925614`.
No raw run, request, approval, container, session, or environment identity is recorded here. The
candidate-bound checker returned `valid: true`; it found only the report in the confined evidence
directory and confirmed exact candidate commit, tree, and parent.

All seven required Gateway observations passed. The audit chain contained seven valid events,
exactly one approval event was observed, and all three runner turns returned zero. The harness
removed every exact container, the exact candidate image, extracted source tree, copied analysis
evidence, and private runtime state before retaining the success report.

One existing Sol-high reviewer was reused; no xhigh or Ultra reviewer was used. Initial candidate
`b8a7bddcd1eb0a864d776c8e15e0d4c763d276b6` received `NO-GO` with one Medium because set
deduplication did not fully prove exact-one approval evidence. Exact candidate `d873b9b5ac51a0374b612627b3b0b88d248e6895`
closed that finding by requiring raw event counts, exact request-to-approval linkage, nonempty
identities, and exact equality with the sole version-2 pending approval row. Final review returned
`GO` with zero Critical, High, Medium, or Low findings.

## Closure and limits

This closes `O2`; it does not complete `O8` or `LV1-007`. The Local-v1 candidate gate and the final
independent candidate review have not yet run. Human UAT has not started, and release acceptance is
false.

The governed tool count remains 24. Ithildin and Hermes received no Docker socket or arbitrary host
control. All runtime, release, promotion, production, external-system, credential-custody, and UAT
authorities remain false.
