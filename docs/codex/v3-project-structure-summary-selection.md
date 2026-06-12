# v3 project.structure.summary Selection

Status: design-only candidate selection. This document records `project.structure.summary` as the
next proposed read-only metadata candidate after the consolidated four-tool project intelligence
slice.

The selection does not add a tool manifest, does not add an executor, does not add policy rules,
does not add MCP exposure, does not add API behavior, does not add UI behavior, and does not add
runtime behavior.

## Candidate Matrix

| Candidate | Value | Main Risk | Decision |
| --- | --- | --- | --- |
| `project.structure.summary` | Helps an agent orient around repository shape before choosing existing read tools. | Directory and filename metadata can reveal sensitive project structure. | Selected for design-only proposal with redaction and count-first output. |
| `git.show.tag_metadata` | Complements local Git metadata. | Annotated tag messages can contain untrusted text or secrets. | Defer until tag-message policy is stronger. |
| `git.show.commit_file_summary` | Helps understand a commit's touched areas. | Changed file names can leak sensitive paths and imply code ownership. | Defer until path-name privacy policy is stronger. |
| `project.lockfile.summary` | Could provide dependency posture counts. | Lockfile parsing can drift toward package inventory, SBOM, license, or vulnerability claims. | Defer. |
| `project.test.summary` | Useful operator signal. | Test framework discovery can imply file contents, scripts, command execution, or package-manager behavior. | Defer. |

## Selection Rationale

`project.structure.summary` is the lowest-risk useful continuation of read-only project
intelligence because it can reuse the existing workspace, path, hidden/sensitive denial, symlink,
hardlink, size-limit, and safe-error contracts while exposing only bounded structural counts.

The proposed capability is not a code-search engine and not a filesystem listing replacement. It
must not return arbitrary recursive listings or file contents. Its value comes from answering small
orientation questions such as "does this workspace look like a Python app, a TypeScript app, or a
mixed project?" without disclosing raw source.

## Boundary

- Tool count remains `15`.
- Implementation remains blocked.
- Broader capability expansion remains blocked.
- New powerful tool classes remain blocked.
- The candidate is structure-summary metadata only.
- The future proposal must preserve no file contents, no raw recursive listing, no package-manager
  execution, no shell, no dependency names, no package script values, no registry or network access,
  and no broad filesystem writes.
- A future implementation requires an explicit implementation decision.

## Required Gates

Run:

```bash
make project-structure-summary-proposal-check
make project-structure-summary-design-review-packet
```

The packet asks for design review only. A later implementation sprint would still need an explicit
implementation-planning packet, implementation decision, source-review handoff, policy fixtures,
negative transcripts, audit evidence, and release gates.
