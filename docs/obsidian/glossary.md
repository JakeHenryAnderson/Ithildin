---
title: Glossary
tags: [ithildin, glossary]
---

# Glossary

## Agent

An AI-driven client that proposes tool calls. In Ithildin, agents are untrusted principals.

## Approval

A one-time human authorization bound to an exact request hash, resource, tool, and expiry.

## Audit Evidence

Structured records that reconstruct proposed action, policy decision, approval state, execution result, and relevant hashes.

## Gateway

The trusted MCP/API boundary that authenticates requests and routes them through validation, policy, approval, execution, and audit.

## Manifest

A trusted local description of a tool, including risk, schemas, sandbox requirements, and approval requirements.

## Policy

Deterministic authorization logic that returns `allow`, `deny`, or `require_approval`.

## Tool

A constrained operation exposed to an AI agent, such as `fs.read` or `git.diff`.

