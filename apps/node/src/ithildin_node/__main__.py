"""Command-line entry point for the local-preview Ithildin Node client."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from ithildin_node.client import (
    NodeClient,
    NodeClientError,
    NodeState,
    StoredNodeConfiguration,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    enroll = subparsers.add_parser("enroll")
    _common(enroll)
    enroll.add_argument("--state", type=Path, required=True)
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
    status = subparsers.add_parser("status")
    status.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "status":
            print(json.dumps(NodeState.load(args.state).safe_summary(), indent=2, sort_keys=True))
            return 0
        client = NodeClient(args.api_url)
        if args.command == "enroll":
            code = getpass.getpass("One-time enrollment code: ")
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
