# Local Prompt Triage

Status: implemented as a host-side helper.

Switchboard's useful lesson is not the hosted classifier. The useful lesson is that a request can be
summarized into a small difficulty packet before model selection. Ithildin can use that pattern
locally without proxying prompts, collecting ChatGPT credentials, or sending snippets to a hosted
router.

## Local Boundary

`scripts/local_prompt_triage.py` classifies operator-supplied task text with deterministic local
heuristics. It does not call an LLM. It also does not:

- open a network connection;
- proxy Codex, Claude, Ollama, or MCP traffic;
- mutate model configuration;
- grant new governed tool powers.

The output is advisory. It can help an operator decide whether to keep work on a small local model,
split a request, trim context, or reserve a stronger/manual review pass.

## Signals

The helper estimates:

- rough input tokens from local text length;
- file references;
- exact/mechanical work;
- tests and regression work;
- runtime errors and stack traces;
- security, auth, billing, database, infra, CI, deployment, policy, or redaction-sensitive domains;
- multi-file, multi-step, and large-context requests.

Difficulty is reported on a 1-5 scale. Recommendations are:

- `local_small`: bounded or mechanical tasks that are reasonable for a small local model or no model;
- `standard`: routine work that should fit normal review;
- `split_or_strong`: broad work that should be split or sent to a stronger model;
- `strong_review`: risk-sensitive work that deserves a stronger model, human review, or both.

## Usage

```sh
uv run python scripts/local_prompt_triage.py --text "Reply with exactly: ok"
uv run python scripts/local_prompt_triage.py --file docs/codex/v0.8-roadmap-prompt.md --json
```

## Fit For Ithildin

This improves local projects by adding a privacy-preserving preflight step for demo prompts,
review-packet prompts, and local-model experiments. It also preserves the existing local-model demo
boundary: Ithildin remains a governed tool gateway, not a model router or prompt proxy.
