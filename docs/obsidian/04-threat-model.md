---
title: Threat Model
tags: [ithildin, security, threat-model]
---

# Threat Model

## Primary Assets

| Asset | Risk |
| --- | --- |
| Local files and repositories | Unauthorized read, modification, deletion, exfiltration. |
| Credentials and secrets | Leakage through prompts, logs, tool output, or network calls. |
| Policies | Tampering, overly broad grants, stale policy use. |
| Audit logs | Deletion, alteration, sensitive data exposure. |
| Approval records | Forged approvals, approval replay, broad approvals. |
| Tool manifests | Malicious or inaccurate tool descriptions. |
| Endpoint runtime | Container escape, privilege escalation, Docker socket abuse. |
| Model context | Prompt injection, data poisoning, indirect instruction attacks. |

## Threat Actors

| Actor | Assumption |
| --- | --- |
| LLM/agent | Not malicious by intent, but unsafe, suggestible, and non-authoritative. |
| User | Usually legitimate, but may be careless or approval-fatigued. |
| Malicious local process | May call local APIs, steal tokens, or abuse localhost services. |
| Malicious MCP/tool package | May lie about behavior or run arbitrary code. |
| Remote attacker | May exploit SSRF, DNS rebinding, weak auth, or exposed local ports. |
| Insider/admin | May create unsafe policies or suppress logs. |

## High-Priority Threats

1. Prompt injection causing unsafe tool calls.
2. Legitimate tool invoked with dangerous arguments.
3. Over-privileged agent identity.
4. Direct bypass around Ithildin.
5. Malicious or compromised tool plugin.
6. SSRF through HTTP fetch tools.
7. Path traversal through file tools.
8. Approval fatigue.
9. Audit log tampering or sensitive log leakage.
10. Local MCP server compromise.

## MVP Security Tests

- `../../` path traversal.
- symlink escape from workspace to sensitive paths.
- HTTP access to localhost, private IPs, and link-local metadata endpoints.
- approval replay for modified requests.
- manifest tampering.
- oversized inputs.
- log injection using newlines/control characters.

## v0.4 Local-Preview Refresh

- v0.4 remains review closure, evidence maturity, diagnostics, and hardening over the same v0.1
  local-preview runtime boundary.
- macOS and Linux are the only filesystem security-supported local-preview profiles.
- Windows/WSL, external notarization, production identity, remote MCP, runtime Postgres, hosted
  telemetry, shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, broad writes, and
  plugin SDKs remain out of scope.
- The current reviewer handoff should include the v0.4 threat refresh, source-review closure matrix,
  executor contracts, negative transcripts, and review-candidate evidence.
