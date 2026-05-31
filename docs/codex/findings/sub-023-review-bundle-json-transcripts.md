# SUB-023 Review Bundle JSON Transcripts

- Finding ID: SUB-023
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/review_packet_bundle.py; build_bundle; _write_command_json
- Claim being tested: review bundle `.json` artifacts should be parseable JSON evidence, not shell command transcripts.
- Observed behavior: `release-evidence.json` and `release-packet.json` were written with command transcript wrappers, despite their `.json` names.
- Risk: Reviewers or automated validators could parse the wrong data, miss transcript context, or treat command noise as canonical evidence.
- Recommended fix: Emit raw validated JSON payloads for `.json` artifacts and write command transcript details to adjacent sidecar transcript files.
- Blocking status: later
- Disposition: fixed
- Verification notes: Review bundle generation now parses JSON command output, writes pretty raw JSON artifacts, and stores command metadata in `.transcript.txt` sidecars that are included in artifact hashes. Release-readiness tests assert the JSON artifacts and transcript sidecars are present. External/source review remains pending.
