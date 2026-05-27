"""Host-side Ollama demo helpers for Ithildin local preview."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class OllamaStatus:
    available: bool
    models: list[str]
    message: str


Runner = Callable[[list[str]], CommandResult]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["smoke", "local-demo"])
    args = parser.parse_args()

    status = check_ollama_status()
    if args.command == "smoke":
        print(status.message)
        return

    print(status.message)
    print()
    print("MCP client command:")
    print("  uv run python -m ithildin_mcp_server")
    print()
    print("Example MCP server config:")
    print(json.dumps(mcp_server_config(), indent=2, sort_keys=True))
    if status.models:
        print()
        print(f"Suggested local model: {status.models[0]}")
    print()
    print("Ithildin does not proxy model traffic or manage Ollama in this preview.")


def check_ollama_status(runner: Runner | None = None) -> OllamaStatus:
    if runner is None and shutil.which("ollama") is None:
        return OllamaStatus(
            available=False,
            models=[],
            message="Ollama is not installed or not on PATH; skipping local model smoke.",
        )

    command_runner = runner or _run_ollama
    version = command_runner(["--version"])
    if version.returncode != 0:
        return OllamaStatus(
            available=False,
            models=[],
            message="Ollama is not responding; skipping local model smoke.",
        )

    listed = command_runner(["list"])
    if listed.returncode != 0:
        return OllamaStatus(
            available=True,
            models=[],
            message="Ollama is installed but models could not be listed; skipping model demo.",
        )

    models = parse_ollama_models(listed.stdout)
    if not models:
        return OllamaStatus(
            available=True,
            models=[],
            message="Ollama is installed but no local models are available; skipping model demo.",
        )

    return OllamaStatus(
        available=True,
        models=models,
        message=f"Ollama smoke passed with {len(models)} local model(s): {', '.join(models)}",
    )


def parse_ollama_models(output: str) -> list[str]:
    models: list[str] = []
    for line in output.splitlines()[1:]:
        columns = line.split()
        if columns:
            models.append(columns[0])
    return models


def mcp_server_config() -> dict[str, object]:
    return {
        "mcpServers": {
            "ithildin": {
                "command": "uv",
                "args": ["run", "python", "-m", "ithildin_mcp_server"],
                "env": {
                    "ITHILDIN_ADMIN_TOKEN": "dev-admin-token-change-me",
                    "ITHILDIN_WORKSPACE_ROOT": "workspaces",
                },
            }
        }
    }


def _run_ollama(args: list[str]) -> CommandResult:
    completed = subprocess.run(
        ["ollama", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


if __name__ == "__main__":
    main()
