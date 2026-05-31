# Packet Redaction Scanner

Task 127 adds `make packet-redaction-scan` as a focused handoff hygiene check for generated review
packet artifacts. It is not a complete secrets scanner and does not prove that no sensitive material
can ever appear in logs, tool outputs, screenshots, or reviewer copies. It checks the local review
bundle and consolidated packet for obvious private-key material, concrete admin-token assignments,
sample development tokens, password/secret assignments, non-text artifacts, and runtime file types
that should never be uploaded as review evidence.

## Command

```sh
make packet-redaction-scan
```

Direct form:

```sh
uv run python scripts/packet_redaction_scan.py
uv run python scripts/packet_redaction_scan.py var/review-packets/v0.2/ithildin-v0.2-review-packet-...
```

`make review-candidate` runs the scanner after `make review-packet-bundle` and
`make review-packet-consolidated`, so a handoff candidate fails closed if generated packet artifacts
contain obvious secret material or forbidden runtime files.

## Boundary

The scanner is intentionally narrow. It scans generated packet artifacts, not the entire repository
or user workstation. It complements release evidence validation, bundle exclusion rules, redaction
tests, and external/source review; it is not a substitute for any of them.
