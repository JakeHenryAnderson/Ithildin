# E2-NODE-005 Remote Transport Next-Ticket Contract

Status: blocked; no implementation authority.

Parent decision: `PIS-005A`.

E2-NODE-005 is the smallest possible future ticket for a real TLS 1.3 and mTLS Node transport. It
is not authorized by PIS-005A, by automated test results, or by an independent review of a local
fixture-only candidate.

## Required new authority

A later entry decision must bind:

1. the exact reviewed PIS-005A commit, tree, schema fingerprint, and review disposition;
2. an exact remote ingress namespace and protocol contract that cannot expose existing local bearer
   administration;
3. a reviewed TLS 1.3 profile, server certificate identity, client-certificate validation chain,
   revocation and bounded overlap rules;
4. a selected CA/custody provider and an explicit statement of which process may request signing
   without receiving the CA private key;
5. Node private-key generation, non-exportable custody, loss, replacement, and platform support;
6. configuration/application/certificate generation reconciliation under restart and partition;
7. remote rate, size, time, replay, cancellation, and ambiguous-outcome limits;
8. external architecture and source review, negative transport tests, and an operator UAT plan; and
9. rollback/fencing that does not restore retired Node private identity.

## Still forbidden

Until that decision exists, do not add a TLS listener, certificate issuance, CA or Node private-key
custody, remote MCP, arbitrary HTTP, remote administration, hosted trust, runtime PostgreSQL,
external credentials, a new governed tool, or a production workload-identity claim.

PIS-005A may prove only deterministic local conformance and persistence behavior. It cannot prove
network confidentiality, endpoint non-exportability, deployment topology, supported scale, human
UAT, release acceptance, or production promotion.
