# Sandbox/VM Live POC Runtime Descriptor-Only Negative Transcripts

Status: generated local denial-transcript evidence for the implemented `ERG-004` descriptor-only
runtime slice.

Current governed tool count: `24`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts
```

The generated transcript is written under:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-negative/
```

This artifact records deterministic, secret-free denial observations for malformed or
authority-expanding sandbox descriptor payloads. It strengthens the descriptor-only source-review
handoff without changing runtime behavior.

## Covered Scenarios

The transcript generator mutates in-memory descriptor fixtures and records only scenario names,
expected denial classes, observed status, and safe reason labels for:

- unknown descriptor fields;
- forbidden lifecycle-control authority claims;
- forbidden live-inspection authority claims;
- forbidden Mission Control runtime-authority claims;
- forbidden trusted-host-promotion claims;
- raw/path-shaped mount labels;
- parent-directory traversal markers in labels;
- control characters in labels;
- malformed VM profile hashes;
- malformed packet hashes.

## Non-Effects

The generator does not call governed tools, start or inspect VMs/containers, invoke local models,
call Mission Control, write host artifacts, perform network access, record external review,
normalize reviewer responses, close `ERG-004`, or approve new runtime behavior.

## Output Policy

The generated transcript must contain only safe labels and denial summaries. It must not include raw
descriptor payloads, file contents, prompts, model responses, command lines, shell output, raw paths,
environment values, registry URLs, dependency names, package scripts, secrets, or VM/container
handles.

## Source-Review Use

The `ERG-004` descriptor-only source-review bundle includes this generated transcript as supporting
evidence. External/source reviewers should still inspect the implementation directly and use the
`EXT-LIVE-DESC-###` finding namespace.

This artifact does not close `ERG-004`; it only improves local evidence for the descriptor-only
runtime source-review lane.
