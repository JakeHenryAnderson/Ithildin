# Command Center Run-Evidence Digest Verification Feasibility Map

Status: approved bounded browser-side verification using the existing evidence response.

Current governed tool count: `24`.

## Integrity Gap

The run evidence endpoint already returns SHA-256 values for its `run`, `timeline`, `approvals`, and
`patch_diagnostics` sections. Command Center previously displayed those values but did not recompute
them. An operator therefore could not distinguish a matching response from a malformed or altered
response whose section content no longer agreed with its supplied digests.

## Existing Contract

No new API or field is required. The existing response supplies:

- `evidence_hashes.run_sha256` for `run`;
- `evidence_hashes.timeline_sha256` for `timeline`;
- `evidence_hashes.approvals_sha256` for `approvals`;
- `evidence_hashes.patch_diagnostics_sha256` for `patch_diagnostics`.

The Gateway produces these with UTF-8 SHA-256 over deterministic JSON: recursively sorted object
keys, compact separators, original array order, and unescaped Unicode. Command Center can reproduce
that transform with browser-native `TextEncoder` and Web Crypto.

## Frozen UI States

- `Verifying locally`: recomputation is in progress.
- `4 of 4 section digests match`: all four required values exactly match.
- `Mismatch - do not rely on snapshot`: a required digest is absent, malformed, or different; the
  exact affected section names are shown and export reliance is blocked in operator copy.
- `Unavailable`: browser Web Crypto cannot perform the comparison; supplied digests remain visible
  but are explicitly not locally checked.

The `Export Run Evidence` action verifies the exact newly fetched response before creating a browser
download. Mismatch, malformed JSON, wrong run identity, or unavailable local hashing fails closed
without creating an object URL or initiating a download.

The check is response-local. It never repairs content, writes evidence, contacts the Node, mutates a
run, or decides which source is historically correct.

## Non-Claims

A matching digest proves only internal consistency between four response sections and their
supplied values in the current browser session. It is not a signature, independent attestation,
trusted timestamp, download receipt, later-custody proof, audit-chain verification, endpoint
completeness, or proof of off-Gateway activity. It adds no endpoint, schema, storage, governed tool,
runner control, Node authority, SIEM adapter, production identity, or compliance claim.
