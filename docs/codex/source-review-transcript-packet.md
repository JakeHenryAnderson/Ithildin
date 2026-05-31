# Source Review Transcript Packet

Task 171 adds `make source-review-transcript-packet`, which generates an ignored packet skeleton under
`var/review-packets/v0.5/source-review-transcripts/`.

The packet is for external/source review notes. It does not close external review, does not approve
capability expansion, and does not change runtime behavior.

## Command

```bash
make source-review-transcript-packet
uv run python scripts/source_review_transcript_packet.py --check
```

## Contents

The generated packet records SHA-256 hashes for the runbook, source-file inspection packet, subsystem
checklists, finding template, and closure matrix. It provides blank transcript sections for:

- patch apply;
- filesystem;
- HTTP fetch;
- signed evidence, policy, MCP, and review console.

Completed reviewer transcripts should be treated as review input. Findings still need structured intake
through [reviewer-finding-template.md](reviewer-finding-template.md) and closure updates in
[source-review-closure-matrix.md](source-review-closure-matrix.md).
