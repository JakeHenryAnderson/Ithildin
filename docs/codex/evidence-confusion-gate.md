# Evidence-Confusion Gate v2

Task 155 adds `make evidence-confusion-gate` so release and review docs keep local trust evidence
separate from stronger claims Ithildin does not make.

## Command

```sh
make evidence-confusion-gate
uv run python scripts/evidence_confusion_gate.py --json
```

## Boundary Checked

The gate verifies that signed-audit-export and signed-manifest-lock docs keep these facts visible:

- audit export and manifest-lock signatures are local Ed25519 evidence only;
- runtime signing may be unconfigured by default;
- the signed-evidence demo uses ignored non-production fixture keys;
- locally signed evidence is not external notarization, hosted custody, official supply-chain
  signing, production key management, tamper-proof storage, or immutable custody.

The gate is included in `make release-check`. A future release that changes evidence semantics must
update the evidence contracts, release evidence schema, review packet, and external review prompt
instead of silently weakening this wording.
