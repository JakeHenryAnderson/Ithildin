from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_mcp_inspector_recipe_helper_emits_stdio_config() -> None:
    completed = subprocess.run(
        ["uv", "run", "python", "scripts/mcp_inspector_recipes.py", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["server"] == {
        "command": "uv",
        "args": ["run", "python", "-m", "ithildin_mcp_server"],
        "cwd": Path.cwd().resolve().as_posix(),
    }
    assert "fs.patch.apply with proposal_id returns approval_required" in payload["recipes"]
    assert payload["docs"] == "docs/codex/mcp-inspector-recipes.md"


def test_mcp_inspector_recipe_helper_fails_outside_repo(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(Path.cwd() / "scripts/mcp_inspector_recipes.py"),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "must be run from the Ithildin repo root" in completed.stderr
