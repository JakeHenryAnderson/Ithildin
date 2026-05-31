# Resource Limit Sanity

Task 143 adds a local-preview resource-limit sanity gate. It is an availability and evidence check,
not a performance benchmark and not production capacity planning.

Run:

```sh
make resource-limit-check
uv run python scripts/resource_limit_check.py --json
```

`make release-check` includes this gate.

The check validates that configured/default limits remain bounded for local preview:

- read byte limit;
- patch byte limit;
- HTTP response byte limit;
- HTTP timeout;
- HTTP redirect count;
- search result limit;
- git log limit;
- whether the HTTP allowlist is configured.

The gate fails if byte limits, search results, git log results, HTTP timeout, or redirect count
exceed local-preview ceilings. It reports an empty HTTP allowlist as a warning because empty
allowlist means `http.fetch` denies by default.

This does not add executor behavior, quotas, rate limiting, scheduling, hosted telemetry,
production SLOs, or broad network/filesystem powers.
