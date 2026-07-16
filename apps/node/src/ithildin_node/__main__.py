"""Command-line entry point for the local-preview Ithildin Node client."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from ithildin_node.client import NodeClient, NodeClientError, NodeState


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    enroll = subparsers.add_parser("enroll")
    _common(enroll)
    enroll.add_argument("--state", type=Path, required=True)
    heartbeat = subparsers.add_parser("heartbeat")
    _common(heartbeat)
    heartbeat.add_argument("--state", type=Path, required=True)
    heartbeat.add_argument("--configuration-digest", required=True)
    heartbeat.add_argument("--mission-id")
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
        result = client.heartbeat(
            state,
            node_version=args.node_version,
            runner_adapter=args.runner_adapter,
            deployment_topology=args.deployment_topology,
            configuration_digest=args.configuration_digest,
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
