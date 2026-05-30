# Principal and Workspace Registry Fail-Closed Suite

Task 106 expands v0.3-prep coverage for local trusted principal and workspace registries. These
registries are local-preview attribution and scoping configuration, not production identity or
tenant isolation.

## Principal Registry Coverage

`tests/test_identity.py` now checks that principal registry loading fails closed for:

- missing strict registries;
- invalid YAML;
- non-mapping YAML documents;
- non-string top-level keys;
- duplicate principal IDs;
- invalid role names;
- malformed principal IDs;
- principal ID/type mismatch;
- extra fields;
- non-object metadata;
- disabled principals used for active work;
- unknown principal lookups.

## Workspace Registry Coverage

`tests/test_workspaces.py` now checks that workspace registry loading or resolution fails closed for:

- missing strict registries;
- invalid YAML;
- non-mapping YAML documents;
- non-string top-level keys;
- invalid schema and extra fields;
- non-object metadata;
- duplicate workspace IDs;
- malformed workspace IDs;
- traversal roots;
- missing default workspace;
- disabled default workspace;
- disabled named workspace resolution;
- unknown workspace use through the read executor.

## Boundary

The suite does not add OIDC, SAML, SCIM, production sessions, multi-tenant stores, remote MCP, or
strong host isolation. It confirms that local registry evidence is explicit, parseable, and
fail-closed before governed calls rely on it.
