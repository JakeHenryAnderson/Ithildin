# Local Auth Boundary

Task 138 records the v0.4 local admin-auth posture. It does not add production identity, sessions,
OIDC, SAML, SCIM, OAuth, multi-user authorization, remote MCP, or hosted control-plane behavior.

Ithildin local-preview admin APIs use one configured bearer token:

- credential source: `Authorization: Bearer <token>`;
- server session state: disabled;
- cookie authentication: disabled;
- browser credential/CORS cookies: disabled;
- production identity: not implemented;
- scope: single local admin token for local review-console and operator calls.

The local principal registry remains an attribution and policy-input registry for governed tool
calls. It is not human authentication. Admin bearer-token authentication remains separate from local
principal labels.

## Runtime Evidence

`GET /system/status` reports secret-free auth evidence under `security.admin_api_auth`:

- `scheme`;
- `credential_source`;
- `cookie_auth_enabled`;
- `server_sessions_enabled`;
- `production_identity`;
- `scope`.

The endpoint also reports dev-token posture, token-length warnings, local CORS origins, loopback
deployment evidence, remote MCP disabled status, storage status, telemetry status, manifest-lock
status, principal registry status, and audit head evidence.

## Regression Claims

Automated tests verify:

- missing admin credentials return `401`;
- wrong bearer tokens return `403`;
- cookies do not authenticate admin endpoints;
- wrong tokens are not echoed in error responses;
- sample dev admin token use requires the explicit demo flag and is reported as a warning;
- CORS remains local-origin only and credential sharing remains disabled.

These checks are local-preview guardrails. They are not a substitute for production identity or
remote protected-resource authorization.
