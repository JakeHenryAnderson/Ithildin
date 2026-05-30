# Manifest Validation Suite

Task 105 expands fail-closed coverage for trusted tool manifests and manifest-lock evidence. The
suite treats `tool-manifests/` and `tool-manifests.lock.json` as trusted local configuration, but
still validates that malformed or drifted trust inputs do not start silently.

## Covered Manifest Failures

`tests/test_tool_registry.py` now covers:

- invalid YAML;
- YAML values that are not mappings;
- non-string manifest keys;
- missing required manifest fields;
- extra manifest fields;
- invalid risk enum values;
- non-object `input_schema`;
- non-object MCP metadata;
- duplicate tool names;
- ignored non-manifest files.

## Covered Manifest-Lock Failures

The same suite covers:

- missing lock files;
- invalid JSON and non-object lock payloads;
- unsupported lockfile versions;
- manifest-directory mismatch and path escape;
- missing manifests from the lock;
- stale lock entries;
- duplicate lock paths and duplicate lock names;
- malformed lock entries;
- missing lock fields;
- invalid or mismatched manifest hashes.

## Signed-Lock Boundary

Signed manifest locks remain optional by default. When enabled, startup must fail closed if manifest
lock enforcement is not active, signature configuration is incomplete, a signature is missing, the
trusted public key is absent or wrong, the key ID mismatches, the lock digest mismatches, or the
signature targets a different lock path.

This suite does not add hosted supply-chain signing or external notarization. It strengthens local
operator evidence only.
