# Reviewer Artifact Manifest v2

Task 172 adds `make reviewer-artifact-manifest`, which writes a machine-readable v0.5 artifact inventory
under ignored `var/review-packets/v0.5/`.

The manifest records:

- committed review-document hashes;
- required handoff commands;
- expected generated review artifacts;
- explicit statements about what the artifact set does not prove.

## Command

```bash
make reviewer-artifact-manifest
uv run python scripts/reviewer_artifact_manifest.py --check
```

This is a packaging inventory only. It does not close external/source review, approve capability
expansion, or add runtime behavior.
