# Enterprise Review Upload Staging

Status: generated upload-staging batches for the current enterprise send set.

Current governed tool count: `24`.

Run:

```sh
make enterprise-review-upload-staging
```

Validate:

```sh
make enterprise-review-upload-staging-check
```

The generated staging output is written under:

```text
var/review-packets/v3/enterprise-review-upload-staging/
```

## Purpose

The send quickstart names the files to attach for `ERG-003` and `ERG-002`. This staging layer goes
one practical step further: it copies only the manifest-listed files into upload-friendly batch
folders so the operator can attach a whole batch without manually selecting files from the larger
outbox directory.

The staging folders are derived from the generated lane-local `ATTACHMENT_MANIFEST.md` files and
preserve the existing hashes for each copied attachment. Operator-reference files such as
`ATTACHMENT_MANIFEST.md` stay in the source outbox and are not copied into the upload batches unless
they are explicitly manifest-listed.

For validation speed, the Make target may reuse the current generated enterprise review send package
when that package matches the current commit, dirty state, boundary flags, recommended gaps, and
artifact hashes. If that evidence is missing or stale, the staging script rebuilds the send package
before copying batches.

## Expected Layout

- `ERG-003/batch-1`: the static sandbox/VM preflight request, fitting a 10-attachment surface.
- `ERG-002/batch-1`: the first Mission Control display/import planning batch.
- `ERG-002/batch-2`: the second Mission Control display/import planning batch.
- `ENTERPRISE_REVIEW_UPLOAD_STAGING.md`: generated index over the batch folders.
- `enterprise-review-upload-staging.json`: machine-readable batch metadata.
- `enterprise-review-upload-staging-artifact-hashes.json`: hashes for the generated index, JSON, and
  copied attachment files.

## Boundary

This staging output does not record external review, does not normalize responses, does not write
response files, does not mutate findings, does not close `ERG-003` or `ERG-002`, and does not approve
runtime behavior. It is a local operator convenience artifact only.

It does not approve:

- live VM/container inspection;
- Mission Control runtime behavior;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter runtime behavior;
- production identity or runtime Postgres;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

## Validation

`make enterprise-review-upload-staging-check` verifies that the generated batches match the current
send package and attachment manifests, that staged file hashes match, that `ERG-003` remains a single
10-file batch, that `ERG-002` is split into two batches, and that the staging artifact is wired into
the release and review-candidate gates. It may reuse a current generated send package only when the
package evidence matches the current tree.
