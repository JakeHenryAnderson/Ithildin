# Source Verification Notes

The source strategy text includes market and standards claims that should be verified before public release.

## Verify Before Publishing

- MCP protocol details, tool annotations, and human-in-the-loop guidance.
- AWS Bedrock AgentCore Policy positioning and architecture.
- OWASP agentic AI guidance.
- Keycloak protocol support.
- OPA policy model, bundles, and decision logs.
- Cedar and AWS Verified Permissions relationship.
- Docker Compose volume/network behavior.
- OpenTelemetry semantic conventions.
- Ollama Docker support.
- vLLM OpenAI-compatible serving.
- LiteLLM positioning.
- Apache-2.0 patent grant.
- AGPL network interaction obligations.
- Business Source License source-available status.
- Microsoft Copilot Studio governance features.
- Google Gemini Enterprise positioning.
- Cloudflare AI Gateway and Kong AI Gateway positioning.
- Okta AI agent identity positioning.
- Official MCP reference server production-readiness statements.

## Current Release Positioning

- Postgres is documented as readiness-only; SQLite is the only runtime storage backend in v0.1.
- OpenTelemetry is opt-in preview instrumentation and should not be described as production
  observability.
- Ollama support is host-side demo wiring only; Ithildin does not run, package, or proxy models.
- The static docs site is a local generated artifact, not a hosted documentation service.

## Research Rule

Keep public docs conservative unless a claim is backed by a current primary source.
