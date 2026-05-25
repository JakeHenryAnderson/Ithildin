"""Run the Ithildin MCP stdio server."""

from __future__ import annotations

import anyio

from ithildin_mcp_server.server import run_stdio_server


def main() -> None:
    anyio.run(run_stdio_server)


if __name__ == "__main__":
    main()
