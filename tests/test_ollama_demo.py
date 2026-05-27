from __future__ import annotations

from typing import Any, cast

from scripts.ollama_demo import (
    CommandResult,
    check_ollama_status,
    mcp_server_config,
    parse_ollama_models,
)


def test_parse_ollama_models() -> None:
    output = """NAME              ID              SIZE      MODIFIED
llama3.2:latest   abc123          2.0 GB    1 day ago
qwen2.5:7b        def456          4.7 GB    2 days ago
"""

    assert parse_ollama_models(output) == ["llama3.2:latest", "qwen2.5:7b"]


def test_ollama_status_skips_when_command_fails() -> None:
    def runner(args: list[str]) -> CommandResult:
        return CommandResult(returncode=1, stdout="", stderr="not running")

    status = check_ollama_status(runner)

    assert status.available is False
    assert status.models == []
    assert "skipping" in status.message


def test_ollama_status_reports_models_when_available() -> None:
    def runner(args: list[str]) -> CommandResult:
        if args == ["--version"]:
            return CommandResult(returncode=0, stdout="ollama version 0.0.0", stderr="")
        return CommandResult(
            returncode=0,
            stdout="NAME ID SIZE MODIFIED\nllama3.2:latest abc 2GB now\n",
            stderr="",
        )

    status = check_ollama_status(runner)

    assert status.available is True
    assert status.models == ["llama3.2:latest"]
    assert "smoke passed" in status.message


def test_mcp_server_config_uses_host_stdio_command() -> None:
    config = mcp_server_config()

    servers = cast(dict[str, Any], config["mcpServers"])
    server = cast(dict[str, Any], servers["ithildin"])
    assert server["command"] == "uv"
    assert server["args"] == ["run", "python", "-m", "ithildin_mcp_server"]
