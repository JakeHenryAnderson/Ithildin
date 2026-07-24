from __future__ import annotations

import getpass
import io
import json
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml
from ithildin_api.node_configuration import generate_node_configuration_signing_keypair
from ithildin_node import __main__ as cli_module
from ithildin_node import client as node_client_module
from ithildin_node.client import NodeClientError, NodeState, NodeStateReservation
from ithildin_schemas import JsonObject
from test_node_client import RecordingNodeClient

from scripts import node_configuration_signing as signing_cli


def _enroll_arguments(state_path: Path) -> list[str]:
    return [
        "ithildin-node",
        "enroll",
        "--state",
        str(state_path),
        "--enrollment-code-stdin",
    ]


def test_enroll_cli_accepts_one_stdin_line_and_never_emits_or_persists_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdin_code = "stdin-only-secret-code"
    environment_secret = "environment-secret-must-be-ignored"
    client = RecordingNodeClient()
    state_path = tmp_path / "node" / "state.json"
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{stdin_code}\n"))
    monkeypatch.setenv("ITHILDIN_NODE_ENROLLMENT_CODE", environment_secret)
    monkeypatch.setattr(cli_module, "NodeClient", lambda _url: client)

    assert cli_module.main() == 0

    captured = capsys.readouterr()
    state_text = state_path.read_text(encoding="utf-8")
    assert client.requests[0][1]["enrollment_code"] == stdin_code
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    for secret in (stdin_code, environment_secret):
        assert secret not in captured.out
        assert secret not in captured.err
        assert secret not in state_text


@pytest.mark.parametrize(
    "stdin_text",
    [
        "",
        "\n",
        "code\nsecond\n",
        "code\n\n",
        "   \n",
        "\tcode\n",
        " code\n",
        "code \n",
    ],
)
def test_enroll_cli_requires_exactly_one_nonempty_stdin_line(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stdin_text: str,
) -> None:
    monkeypatch.setattr(sys, "argv", _enroll_arguments(tmp_path / "state.json"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("invalid stdin must fail before client construction"),
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    assert not (tmp_path / "state.json").exists()


@pytest.mark.parametrize("prompt_value", ["", "   ", "\tcode", " code", "code "])
def test_enroll_cli_rejects_empty_or_whitespace_affected_prompt_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prompt_value: str,
) -> None:
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ithildin-node", "enroll", "--state", str(state_path)],
    )
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: prompt_value)
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("invalid prompt input must fail before client construction"),
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    assert not state_path.exists()


def test_enroll_cli_rejects_preexisting_state_before_reading_code_or_using_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("operator-owned-existing-state", encoding="utf-8")
    secret = "must-not-be-consumed"
    stdin = io.StringIO(f"{secret}\n")
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("existing state must fail before client construction"),
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    captured = capsys.readouterr()
    assert stdin.tell() == 0
    assert state_path.read_text(encoding="utf-8") == "operator-owned-existing-state"
    assert secret not in captured.out
    assert secret not in captured.err


@pytest.mark.parametrize("path_kind", ["directory", "symlink", "broken_symlink"])
def test_enroll_cli_rejects_non_regular_existing_destination_before_reading_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path_kind: str,
) -> None:
    state_path = tmp_path / "state.json"
    if path_kind == "directory":
        state_path.mkdir()
    else:
        target = tmp_path / ("target.json" if path_kind == "symlink" else "missing.json")
        if path_kind == "symlink":
            target.write_text("operator-owned-target", encoding="utf-8")
        state_path.symlink_to(target)
    stdin = io.StringIO("must-not-be-consumed\n")
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("existing destination must fail before client construction"),
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    assert stdin.tell() == 0
    if path_kind == "directory":
        assert state_path.is_dir()
    else:
        assert state_path.is_symlink()


def test_enroll_cli_rejects_unwritable_destination_before_reading_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "unwritable" / "state.json"
    state_path.parent.mkdir()
    stdin = io.StringIO("must-not-be-consumed\n")
    original_open = os.open

    def reject_state_open(path: str | os.PathLike[str], flags: int, mode: int = 0o777) -> int:
        if Path(path) == state_path:
            raise PermissionError("simulated unwritable parent")
        return original_open(path, flags, mode)

    monkeypatch.setattr("ithildin_node.client.os.open", reject_state_open)
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("unwritable destination must fail before client construction"),
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    assert stdin.tell() == 0
    assert not state_path.exists()


def test_enroll_cli_detects_replaced_reservation_before_remote_contact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    intruder_content = "operator-owned-race-winner"

    class ReplacingStdin(io.StringIO):
        def read(self, size: int | None = -1) -> str:
            state_path.unlink()
            state_path.write_text(intruder_content, encoding="utf-8")
            return super().read(size)

    client = RecordingNodeClient()
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", ReplacingStdin("valid-code\n"))
    monkeypatch.setattr(cli_module, "NodeClient", lambda _url: client)

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    assert client.requests == []
    assert state_path.read_text(encoding="utf-8") == intruder_content


def test_enroll_cli_holds_exclusive_reservation_through_remote_enrollment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    client = RecordingNodeClient()
    original_enroll = client.enroll

    def enroll_with_collision_check(**kwargs: str) -> NodeState:
        with pytest.raises(NodeClientError, match="already exists"):
            NodeStateReservation.acquire(state_path)
        return original_enroll(**kwargs)

    monkeypatch.setattr(client, "enroll", enroll_with_collision_check)
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("valid-code\n"))
    monkeypatch.setattr(cli_module, "NodeClient", lambda _url: client)

    assert cli_module.main() == 0

    loaded = NodeState.load(state_path)
    assert loaded.node_id == "node_" + ("1" * 32)
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


def test_enroll_cli_retains_safe_recovery_marker_after_ambiguous_remote_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "state.json"
    code = "ambiguous-secret-code"
    client = RecordingNodeClient()

    def ambiguous_failure(**_kwargs: str) -> NodeState:
        raise NodeClientError("simulated Gateway response loss")

    monkeypatch.setattr(client, "enroll", ambiguous_failure)
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{code}\n"))
    monkeypatch.setattr(cli_module, "NodeClient", lambda _url: client)

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    marker_text = state_path.read_text(encoding="utf-8")
    marker = json.loads(marker_text)
    assert marker["status"] == "recovery_required"
    assert marker["remote_enrollment_outcome"] == "unknown"
    assert marker["contains_enrollment_code"] is False
    assert marker["contains_private_key"] is False
    assert code not in marker_text
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600

    retry_stdin = io.StringIO("retry-must-not-be-consumed\n")
    monkeypatch.setattr(sys, "stdin", retry_stdin)
    monkeypatch.setattr(
        cli_module,
        "NodeClient",
        lambda _url: pytest.fail("blind retry must fail before client construction"),
    )
    with pytest.raises(SystemExit, match="2"):
        cli_module.main()
    assert retry_stdin.tell() == 0

    monkeypatch.setattr(
        sys,
        "argv",
        ["ithildin-node", "status", "--state", str(state_path)],
    )
    assert cli_module.main() == 0
    captured = capsys.readouterr()
    assert '"status": "recovery_required"' in captured.out
    assert code not in captured.out
    assert code not in captured.err


def test_enroll_cli_retains_recovery_marker_when_finalization_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    code = "finalization-secret-code"
    client = RecordingNodeClient()
    original_write_reserved_json = node_client_module._write_reserved_json

    def fail_state_write(
        descriptor: int,
        document: JsonObject,
        *,
        label: str,
    ) -> None:
        if label == "Node state":
            raise NodeClientError("simulated finalization failure")
        original_write_reserved_json(descriptor, document, label=label)

    monkeypatch.setattr(node_client_module, "_write_reserved_json", fail_state_write)
    monkeypatch.setattr(sys, "argv", _enroll_arguments(state_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{code}\n"))
    monkeypatch.setattr(cli_module, "NodeClient", lambda _url: client)

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    marker_text = state_path.read_text(encoding="utf-8")
    marker = json.loads(marker_text)
    assert len(client.requests) == 1
    assert marker["status"] == "recovery_required"
    assert code not in marker_text


def test_enroll_cli_has_no_code_argument_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ithildin-node",
            "enroll",
            "--state",
            str(tmp_path / "state.json"),
            "--enrollment-code",
        ],
    )

    with pytest.raises(SystemExit, match="2"):
        cli_module.main()

    captured = capsys.readouterr()
    assert "--enrollment-code" in captured.err
    assert not (tmp_path / "state.json").exists()


def test_configuration_signer_ready_check_fails_when_operator_has_not_initialized_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_path = tmp_path / "node-configuration-private.pem"
    public_path = tmp_path / "node-configuration-public.pem"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "node_configuration_signing.py",
            "status",
            "--private-key",
            str(private_path),
            "--public-key",
            str(public_path),
            "--require-configured",
        ],
    )

    assert signing_cli.main() == 1

    result = capsys.readouterr()
    assert '"configured": false' in result.out
    assert "not initialized" in result.out
    assert not private_path.exists()
    assert not public_path.exists()


def test_configuration_signer_ready_check_accepts_operator_initialized_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_path = tmp_path / "node-configuration-private.pem"
    public_path = tmp_path / "node-configuration-public.pem"
    generate_node_configuration_signing_keypair(private_path, public_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "node_configuration_signing.py",
            "status",
            "--private-key",
            str(private_path),
            "--public-key",
            str(public_path),
            "--require-configured",
        ],
    )

    assert signing_cli.main() == 0

    result = capsys.readouterr()
    assert '"configured": true' in result.out
    assert '"valid": true' in result.out
    assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_path.stat().st_mode) == 0o644


def test_fixed_compose_onboarding_commands_preserve_stdin_only_secret_and_node_sandbox() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    compose = yaml.safe_load(Path("deploy/docker-compose.yml").read_text(encoding="utf-8"))
    node_service = compose["services"]["ithildin-node"]

    enroll_target = makefile.partition("node-service-enroll:")[2].partition("\n\n")[0]
    assert "--profile node run --rm -T --no-deps ithildin-node enroll" in enroll_target
    assert "--enrollment-code-stdin" in enroll_target
    assert "ONE_TIME_CODE" not in enroll_target
    assert "ENROLLMENT_CODE" not in enroll_target
    assert "node-service-status:" in makefile
    assert "node-service-up:" in makefile
    assert "node-service-stop:" in makefile
    assert "node-service-logs:" not in makefile
    assert "environment" not in node_service
    assert "ports" not in node_service
    assert "cap_add" not in node_service
    assert "privileged" not in node_service
    assert "network_mode" not in node_service
    assert "pid" not in node_service
    assert "/var/run/docker.sock" not in str(node_service)
    assert node_service["volumes"] == ["ithildin-node-state:/var/lib/ithildin-node"]
    assert node_service["cap_drop"] == ["ALL"]
    assert node_service["read_only"] is True
    assert node_service["security_opt"] == ["no-new-privileges:true"]
