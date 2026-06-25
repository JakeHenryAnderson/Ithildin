# v3 project.config.summary Selection

Status: design-only candidate selection. This document records `project.config.summary` as the
next bounded read-only project-intelligence candidate after `project.language.summary`.

This selection does not add a manifest, executor, policy rule, MCP exposure, API behavior, UI
behavior, or runtime behavior. Implementation remains blocked until the proposal, implementation
plan, explicit implementation decision, source-review handoff, and release gates are recorded.

## Candidate Review

| Candidate | Value | Primary risk | Decision |
| --- | --- | --- | --- |
| `project.config.summary` | Helps an agent orient around local configuration posture before choosing existing read tools. | Config filenames and values can expose secrets, private services, or deployment intent. | Selected for count-only proposal with config contents and raw names suppressed. |
| `project.assets.summary` | Useful for UI/game repos. | Asset filenames can expose product names, users, or proprietary media. | Defer. |
| `project.build.summary` | Useful operational metadata. | Can drift into package-manager/script inspection. | Defer until config posture boundary is reviewed. |

`project.config.summary` is the lowest-risk useful continuation of the read-only project
intelligence lane because it can provide category counts without reading or returning config
contents, config values, package scripts, environment variables, dependency names, or raw paths.

## Decision

- selected candidate: `project.config.summary`;
- scope: design-only proposal;
- tool count remains `24`;
- implementation remains blocked;
- broader capability expansion remains blocked.

Run:

```bash
make project-config-summary-proposal-check
```
