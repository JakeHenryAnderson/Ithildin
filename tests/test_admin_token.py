from __future__ import annotations

import re
import subprocess


def test_admin_token_generator_prints_env_assignment() -> None:
    completed = subprocess.run(
        ["uv", "run", "python", "scripts/admin_token.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    output = completed.stdout.strip()
    assert re.fullmatch(r"ITHILDIN_ADMIN_TOKEN=ithildin_admin_[A-Za-z0-9_-]{32,}", output)
    assert "dev-admin-token-change-me" not in output
    assert not completed.stderr


def test_admin_token_generator_rejects_too_few_random_bytes() -> None:
    completed = subprocess.run(
        ["uv", "run", "python", "scripts/admin_token.py", "--bytes", "8"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "at least 24 random bytes" in completed.stderr
