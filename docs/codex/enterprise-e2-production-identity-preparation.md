# Enterprise E2 Production Identity Preparation

Status: preparation complete; implementation not authorized.

This is a parallel, non-mutating preparation lane based on the pushed E1 handoff commit
`9df7a04cec197fd4953de692793a32e69c107b49`. It does not modify or supersede the frozen E1
candidate `02e39d57a6d38a14d959bb88a32da79fe34e4e13`, its tree, its gate, its independent review,
or its human-UAT packet.

The machine-readable preparation boundary is
[`enterprise-e2-preparation-contract.json`](enterprise-e2-preparation-contract.json). Validate the
lane from the repository root:

```sh
make enterprise-e2-preparation-check
```

## Reconciliation decision

Ithildin already has a reviewed production identity and storage architecture. E2 reuses
[`production-identity-storage-architecture.md`](production-identity-storage-architecture.md) and
[`production-identity-storage-pis-001-threat-model-and-dependency-decision.md`](production-identity-storage-pis-001-threat-model-and-dependency-decision.md)
as standing authority. It does not create a competing OIDC, session, organization, workspace,
Node-identity, or storage design.

The current PIS route remains at
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
The reviewed PIS authority record contains two proposal-level permissions for an external operator:
target selection and signed environment-receipt collection. Neither is an effective operational
collection action. E2 does not select a target, inspect credentials, load a driver, consume a DSN
or binding key, connect, migrate, start a service, or fabricate a receipt.

Production identity, enterprise RBAC, remote administration, runtime PostgreSQL, and live OIDC
remain unauthorized.

## Future identity work-package sequence

The future identity entry gate remains `PIS-004`. These work packages are planning structure, not
implementation tickets or authorization:

1. **`E2-ID-001` — Provider-neutral identity-domain and authority contract.** Freeze exact issuer
   and subject identity, random Ithildin principal IDs, server-owned organization/workspace
   membership, identity and membership generations, recent-auth semantics, safe audit fields, and
   caller-field rejection. Reuse the existing PIS threat model without choosing a provider.
2. **`E2-ID-002` — Server-owned preauthentication and opaque-session state.** Specify atomic
   one-use preauthentication transactions, keyed session-handle digests, idle/absolute expiry,
   rotation, CSRF/origin checks, revocation, and break-glass restrictions. No browser custody of
   long-lived tokens and no framework-signed client session as authority.
3. **`E2-ID-003` — Fixture-backed OIDC adapter and provider conformance.** Consider the already
   deferred Authlib recommendation only through a fresh dependency gate. Start with captured,
   synthetic discovery/JWK/token fixtures, exact issuer checks, clock injection, redirect and
   algorithm denial, replay tests, and bounded network-policy design. No live IdP connection at
   entry.
4. **`E2-ID-004` — Organization and workspace membership authorization.** Bind authorization to
   server-derived principal, organization, workspace, role membership generation, session,
   authentication method, and policy generation. IdP group or role claims remain attributes until
   separately reconciled; service and Node roles cannot approve as humans.
5. **`E2-ID-005` — Command Center sign-in, revocation, and break-glass UX.** Add only after the
   domain, session, adapter, and authorization contracts are reviewed. Preserve Gateway authority,
   make expiry/revocation comprehensible, distinguish ordinary and recent authentication, and keep
   break glass loopback-only, time-bounded, separately attributed, and unable to approve or execute
   governed work.

Each package requires its own entry decision, implementation gate, focused negative tests,
compatibility and rollback analysis, exact-candidate review, and honest evidence limits. E1 UAT
findings may reorder or reshape the Command Center package, but they do not weaken identity
protocol invariants.

## Entry questions that must be answered later

- Is the existing PIS sequencing deliberately continued through its external-input wait, or is a
  separately authorized planning-only identity gate allowed to proceed without routing around it?
- Which exact issuer/provider configurations are in scope, and what external client-credential
  custody exists?
- What organization/workspace role vocabulary and separation-of-duty classes are approved?
- Which session idle, absolute, recent-auth, JWK-cache, and clock-skew limits are supportable?
- What loopback-only break-glass recovery functions are necessary, and which mutations remain
  forbidden?
- Which captured provider fixtures and conformance environments can be used without production
  identities or credentials?
- What SQLite-to-future-storage compatibility is required before session and membership state can
  become authoritative?

Until those questions receive a separate entry decision, there is no production-identity
implementation lane.

## Safe work completed now

E2 adds one deterministic, synthetic, single-organization fixture generator for the current E1
cockpit semantics. It can exercise larger mission, fleet, configuration, version, approval,
evidence, and Attention collections without creating human identities or runtime records. See
[`enterprise-e2-scale-fixture.md`](enterprise-e2-scale-fixture.md).

The fixture is test-only and not runtime-importable. Its counts are useful for regression
construction, not a supported-scale or performance claim.

## Frozen boundaries and stop line

The governed tool count remains exactly `24`. This lane adds no API, schema, migration, dependency,
IdP endpoint, session store, credential, role, executor, MCP behavior, or Command Center runtime
behavior. It does not modify `apps/`, `packages/`, `db/`, manifests, policy, or the E1 handoff
artifacts.

The next action is
`continue_e1_human_uat_and_existing_pis_external_input_wait_before_separate_e2_entry_decision`.
Human UAT, production identity, enterprise RBAC, runtime PostgreSQL, production readiness, release,
and promotion all remain false.
