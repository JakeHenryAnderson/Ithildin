# Reviewer Artifact Manifest v2

Task 172 added `make reviewer-artifact-manifest`. It now writes a machine-readable inventory for
the current v1.0 local-preview RC packet, the current enterprise handoff packets, and historical
review automation artifacts under ignored `var/review-packets/`.

The manifest records:

- committed review-document hashes;
- required handoff commands;
- expected generated review artifacts;
- missing generated artifacts, if any;
- explicit statements about what the artifact set does not prove.

## Command

```bash
make reviewer-artifact-manifest
uv run python scripts/reviewer_artifact_manifest.py --check
```

This is a packaging inventory only. It does not close external/source review, approve capability
expansion, approve enterprise runtime behavior, or add runtime behavior.
