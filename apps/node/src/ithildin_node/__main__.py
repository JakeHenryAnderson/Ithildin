"""Command-line entry point for the local-preview Ithildin Node client."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from threading import Event

from ithildin_node.client import (
    NodeClient,
    NodeClientError,
    NodeState,
    StoredNodeConfiguration,
)
from ithildin_node.service import install_signal_handlers, run_service


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    enroll = subparsers.add_parser("enroll")
    _common(enroll)
    enroll.add_argument("--state", type=Path, required=True)
    enroll.add_argument(
        "--enrollment-code-stdin",
        action="store_true",
        help="read the one-time enrollment code from stdin instead of a terminal prompt",
    )
    heartbeat = subparsers.add_parser("heartbeat")
    _common(heartbeat)
    heartbeat.add_argument("--state", type=Path, required=True)
    heartbeat.add_argument("--configuration-digest")
    heartbeat.add_argument("--configuration", type=Path)
    heartbeat.add_argument("--mission-id")
    configuration_pull = subparsers.add_parser("configuration-pull")
    configuration_pull.add_argument("--api-url", default="http://127.0.0.1:8000")
    configuration_pull.add_argument("--state", type=Path, required=True)
    configuration_pull.add_argument("--output", type=Path, required=True)
    configuration_trust_stage = subparsers.add_parser("configuration-trust-stage")
    configuration_trust_stage.add_argument("--api-url", default="http://127.0.0.1:8000")
    configuration_trust_stage.add_argument("--state", type=Path, required=True)
    identity_key_rotate = subparsers.add_parser("identity-key-rotate")
    identity_key_rotate.add_argument("--api-url", default="http://127.0.0.1:8000")
    identity_key_rotate.add_argument("--state", type=Path, required=True)
    status = subparsers.add_parser("status")
    status.add_argument("--state", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--configuration", type=Path, required=True)
    run.add_argument("--node-version", default="0.1.0")
    run.add_argument("--runner-adapter", default="hermes")
    run.add_argument(
        "--deployment-topology",
        choices=("local_process", "docker_sidecar", "server_service"),
        default="docker_sidecar",
    )
    run.add_argument("--max-cycles", type=int)
    run.add_argument("--retry-initial-seconds", type=int, default=5)
    run.add_argument("--retry-max-seconds", type=int, default=60)
    args = parser.parse_args()
    try:
        if args.command == "status":
            print(json.dumps(NodeState.load(args.state).safe_summary(), indent=2, sort_keys=True))
            return 0
        if args.command == "run":
            stop_event = Event()
            install_signal_handlers(stop_event)
            return run_service(
                state_path=args.state,
                configuration_path=args.configuration,
                node_version=args.node_version,
                runner_adapter=args.runner_adapter,
                deployment_topology=args.deployment_topology,
                max_cycles=args.max_cycles,
                retry_initial_seconds=args.retry_initial_seconds,
                retry_max_seconds=args.retry_max_seconds,
                stop_event=stop_event,
            )
        client = NodeClient(args.api_url)
        if args.command == "enroll":
            code = (
                sys.stdin.readline().rstrip("\r\n")
                if args.enrollment_code_stdin
                else getpass.getpass("One-time enrollment code: ")
            )
            if not code:
                parser.error("one-time enrollment code is required")
            state = client.enroll(
                enrollment_code=code,
                node_version=args.node_version,
                runner_adapter=args.runner_adapter,
                deployment_topology=args.deployment_topology,
            )
            state.write_new(args.state)
            print(json.dumps(state.safe_summary(), indent=2, sort_keys=True))
            return 0
        state = NodeState.load(args.state)
        if args.command == "identity-key-rotate":
            if state.pending_identity_rotation_id is None:
                state = client.stage_identity_key_rotation(state)
                state.write_atomic(args.state)
            try:
                rotated = client.activate_identity_key_rotation(state)
            except NodeClientError as activation_error:
                try:
                    rotated = client.recover_identity_key_rotation(state)
                except NodeClientError:
                    if not state.pending_identity_rotation_expired():
                        raise activation_error from None
                    state = client.replace_expired_identity_key_rotation(state)
                    state.write_atomic(args.state)
                    rotated = client.activate_identity_key_rotation(state)
            rotated.write_atomic(args.state)
            print(json.dumps(rotated.safe_summary(), indent=2, sort_keys=True))
            return 0
        if args.command == "configuration-trust-stage":
            staged = client.stage_configuration_trust(state)
            staged.state.write_atomic(args.state)
            acknowledgment = client.acknowledge_configuration_trust(staged.state)
            print(
                json.dumps(
                    {
                        **staged.state.safe_summary(),
                        "gateway_acknowledgment_status": acknowledgment.get(
                            "acknowledgment_status"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "configuration-pull":
            known_generation = None
            if args.output.exists():
                known_generation = StoredNodeConfiguration.load(args.output).generation
            pulled = client.pull_configuration_with_state(
                state,
                known_generation=known_generation,
            )
            pulled.configuration.write_atomic(args.output)
            if pulled.state != state:
                pulled.state.write_atomic(args.state)
            acknowledgment = client.acknowledge_configuration(
                pulled.state, pulled.configuration
            )
            print(
                json.dumps(
                    {
                        **pulled.configuration.safe_summary(),
                        "configuration_verification_trust": pulled.verification_trust,
                        "configuration_trust_promoted": pulled.trust_promoted,
                        "gateway_configuration_state": acknowledgment.get(
                            "configuration_state"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        configuration_digest = args.configuration_digest
        if args.configuration is not None:
            stored = StoredNodeConfiguration.load(args.configuration)
            if configuration_digest is not None:
                parser.error("use only one of --configuration or --configuration-digest")
            configuration_digest = stored.configuration_digest
        if configuration_digest is None:
            parser.error("heartbeat requires --configuration or --configuration-digest")
        result = client.heartbeat(
            state,
            node_version=args.node_version,
            runner_adapter=args.runner_adapter,
            deployment_topology=args.deployment_topology,
            configuration_digest=configuration_digest,
            mission_id=args.mission_id,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except NodeClientError as exc:
        parser.error(str(exc))
    return 2


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--node-version", default="0.1.0")
    parser.add_argument("--runner-adapter", default="hermes")
    parser.add_argument(
        "--deployment-topology",
        choices=("local_process", "docker_sidecar", "server_service"),
        default="docker_sidecar",
    )


if __name__ == "__main__":
    raise SystemExit(main())
