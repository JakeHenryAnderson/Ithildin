# E2-ID-005 Command Center Identity UX Next-Ticket Contract

Status: blocked; no implementation authority.

Parent decision: `PIS-004A`.

Work package: `E2-ID-005`.

The authoritative Enterprise E1 completion contract records
`human_uat_complete: false` and `next_action: stop_for_human_uat`. This ticket therefore records a
future entry and acceptance boundary only. It does not authorize a sign-in route, browser session,
cookie, live identity-provider connection, revocation control, break-glass control, Command Center
UI, credential custody, release, or promotion.

## Required entry inputs

Do not start implementation until a separate entry decision:

1. binds the exact PIS-004A candidate and independent-review disposition;
2. consumes the actual E1 human-UAT findings without representing them as release acceptance;
3. identifies the local-preview user journeys and accessibility findings that E2-ID-005 must
   address;
4. freezes whether any provider remains synthetic or a separately reviewed provider connection is
   authorized;
5. freezes browser transport, session-cookie, origin, CSRF, expiry, revocation, and recovery
   semantics without moving authority into presentation state;
6. records compatibility and rollback for the existing local bearer-admin path; and
7. preserves the exact 24-tool surface and the standing PIS-003 external-input wait.

Any live provider, client registration, client secret, signing key, discovery/JWK network fetch,
remote administration, production identity, or hosted trust requires its own explicit authority.
E2-ID-005 may not infer that authority from PIS-004A or from a future E1 UAT PASS.

## Bounded future scope

If the prerequisites are satisfied, a later ticket may propose a default-off, loopback-only
Command Center experience for:

- initiating and completing a server-owned sign-in transaction;
- clearly showing ordinary versus recent authentication, idle and absolute expiry, rotation, and
  revocation;
- revoking the current session or an explicitly selected server-owned session family;
- explaining fail-closed states without exposing raw subject, claims, tokens, session handles,
  CSRF values, or customer metadata; and
- a separately attributed recovery path that remains loopback-only, time-bounded, unable to
  self-approve, and unable to approve or execute governed work.

The Gateway and server-side identity, membership, session, authorization, approval, and policy
state remain authoritative. Browser state is projection and user input only.

## Future acceptance contract

Automated acceptance must prove, at minimum:

- the feature is absent or disabled by default and existing bearer-admin behavior is unchanged;
- all callback, origin, redirect, state, nonce, PKCE, session, CSRF, expiry, rotation, revocation,
  and generation checks fail closed;
- no browser field can supply a principal, organization, workspace, role, generation, approval
  class, or effect authority;
- revocation and recovery races have one authoritative server-side outcome;
- Node and service principals cannot enter a human sign-in or approval path;
- recovery authentication cannot satisfy sensitive approval or governed-effect requirements;
- every UI state has keyboard, focus, error, expiry, and recovery coverage appropriate to the E1
  findings;
- safe audit contains only random local references, coarse reason codes, generations, and
  timestamps; and
- focused tests, compatibility tests, production UI build, and applicable repository gates pass
  on one clean exact candidate.

Human UAT remains a separate required gate. Automated tests, screenshots, a clean candidate, and a
human UAT PASS do not by themselves establish production identity, release acceptance, credential
authority, or production promotion.

## Stop conditions

Stop and return to a new entry decision if implementation would require a live provider,
production credentials, remote access, new governed tools, browser-held authority, general-purpose
HTTP, a weakened local-admin baseline, or any change to the standing PIS route.
