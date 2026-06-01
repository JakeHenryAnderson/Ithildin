# SUB-070 Duplicate YAML Keys

- Finding ID: SUB-070
- Severity: medium
- Area: registry fail-closed behavior
- Affected files/functions: apps/api/src/ithildin_api/yaml_utils.py; apps/api/src/ithildin_api/registry.py; apps/api/src/ithildin_api/identity.py; apps/api/src/ithildin_api/workspaces.py; tests/test_tool_registry.py; tests/test_identity.py; tests/test_workspaces.py
- Claim being tested: Trusted YAML configuration should fail closed on duplicate mapping keys instead of accepting parser overwrite behavior.
- Observed behavior: Internal proxy review found that duplicate YAML keys were accepted before Pydantic/model validation.
- Risk: A reviewed manifest, principal, or workspace file could display one value while runtime silently used the later duplicate key.
- Recommended fix: Load trusted YAML through a safe loader that rejects duplicate keys at every mapping depth.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Tool manifests, principal registries, workspace registries, and policy parity fixtures now use a duplicate-key rejecting loader. Tests cover duplicate-key rejection across manifest/principal/workspace files. External/source review remains pending.
