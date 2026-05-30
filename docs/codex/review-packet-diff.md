# Review Packet Diff

`make review-packet-diff` compares two generated review packet bundle directories and prints a
secret-free artifact summary. It is intended for reviewer handoff hygiene: reviewers can see which
generated files changed between packets without diffing runtime state or local secrets.

## Command

```sh
make review-packet-diff OLD=var/review-packets/v0.2/ithildin-v0.2-review-packet-old NEW=var/review-packets/v0.2/ithildin-v0.2-review-packet-new
```

Direct JSON form:

```sh
uv run python scripts/review_packet_diff.py --old old-packet --new new-packet --json
```

## Inputs

The command prefers each packet's `artifact-hashes.json`. If that file is unavailable, it computes
SHA-256 digests for regular files in the packet directory while skipping generated dependency/cache
directories such as `.git`, `.venv`, `node_modules`, `dist`, and `__pycache__`.

The output includes:

- added artifacts;
- removed artifacts;
- changed artifacts with old/new digests and byte counts;
- unchanged artifact count.

## Boundary

This is handoff evidence only. It does not verify source-code correctness, notarize packets, or
prove that an external reviewer saw a specific artifact. It also does not include `.env`, private
keys, runtime SQLite databases, audit JSONL state, or generated UI dependency folders when used with
the normal review bundle.
