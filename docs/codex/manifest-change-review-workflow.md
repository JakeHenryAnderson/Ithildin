# Manifest Change Review Workflow

Task 136 adds a local review guard for trusted tool manifest changes. It does not add new tools,
plugin loading, remote manifest distribution, hosted signing, or external supply-chain trust.

Run:

```sh
make manifest-change-review
```

The check:

- verifies the current committed manifests against `tool-manifests.lock.json`;
- inspects uncommitted changes under `tool-manifests/` and `tool-manifests.lock.json`;
- fails if a YAML manifest changed without the lock changing;
- fails if the lock changed without an accompanying manifest change;
- fails if non-YAML files under `tool-manifests/` are part of the manifest-change review surface;
- reports the current trusted tool count and tool names without exposing secrets.

This target is included in `make release-check`, so manifest and lock drift is caught before review
packets are generated. Intentional manifest changes should be made in a dedicated checkpoint,
followed by:

```sh
make manifest-lock
make manifest-lock-check
make manifest-change-review
make release-check
```

If a future task intentionally adds a new governed tool-power class, this workflow is not enough on
its own. The capability-expansion gate still requires external/source review closure and an explicit
boundary decision before the manifest change is accepted.
