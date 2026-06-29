# Live Demo Environment Diagnostics

Status: optional bounded diagnostics for the local UI/API Compose demo environment.

Run:

```sh
make live-demo-environment-diagnostics
```

This command helps distinguish Ithildin readiness from local Mac/Docker/Rosetta readiness. It is
secret-free and bounded by short subprocess timeouts. It reports host platform, Python version,
Docker CLI presence, Docker Compose command status, Docker daemon status, a macOS Rosetta package
receipt hint on Apple Silicon, and whether the optional Compose demo appears ready to try.

## What It Does

- checks only local command availability and health;
- treats Docker and Rosetta readiness as optional operator environment state;
- returns safe status labels such as `ok`, `missing`, `timeout`, `error`, `installed`,
  `not_confirmed`, or `not_applicable`;
- suggests safe next actions such as using non-Compose evidence commands, restarting Docker
  Desktop, or updating macOS/Rosetta if Docker requires it.

## What It Does Not Do

This diagnostic does not start Docker Desktop. It does not start containers, stop containers, pull
images, build images, call governed tools, read secrets, change Rosetta or Docker settings, approve
live VM/container inspection, approve sandbox orchestration, or add governed tool powers.

## Normal Demo Use

Use this command when `make compose-up`, `make compose-smoke`, or `make live-demo-status` suggests
the local stack is unavailable:

```sh
make live-demo-environment-diagnostics
make live-demo-preflight
make demo-seed
make compose-up
make compose-smoke
```

If the diagnostic reports `compose_demo_ready: false`, the local-preview repo can still generate
non-Compose evidence:

```sh
make live-demo-status
make live-demo-smoke
make live-demo-evidence-summary
make demo-workbench-smoke
make review-candidate
```

## Boundary

This diagnostic is operator-environment evidence only. It does not prove OS isolation, host
compromise resistance, production security, compliance automation, SIEM custody, external
notarization, or activity outside Ithildin-mediated actions.
