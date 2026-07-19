"""Repo-reviewed, server-owned Mission Command template registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from ithildin_schemas import JsonObject, canonical_json, sha256_digest

from ithildin_api.missions import MISSION_TEMPLATE_ID

MISSION_TEMPLATE_REGISTRY_SCHEMA_VERSION = "1"

_SYNTHETIC_READ_REVIEW_PAYLOAD: JsonObject = {
    "schema_version": "1",
    "mission_template_id": MISSION_TEMPLATE_ID,
    "mission_kind": "synthetic_read_review",
    "workspace_binding": "assigned_node_workspace",
    "operations": [
        {"sequence": 1, "tool_name": "project.structure.summary"},
        {"sequence": 2, "tool_name": "project.test.summary"},
    ],
    "output_contract": {
        "status_codes_only": True,
        "artifact_digest_optional": True,
        "freeform_summary_allowed": False,
    },
    "host_control": {
        "runner_launch_allowed": False,
        "shell_allowed": False,
        "filesystem_write_allowed": False,
        "network_allowed": False,
    },
}


class MissionTemplateError(RuntimeError):
    """Raised when a mission template is unavailable or invalid."""


@dataclass(frozen=True)
class MissionTemplate:
    template_id: str
    canonical_payload_json: str
    payload_digest: str
    operation_tool_names: tuple[str, ...]

    def payload_copy(self) -> JsonObject:
        payload = json.loads(self.canonical_payload_json)
        if not isinstance(payload, dict):  # pragma: no cover - constructor invariant
            raise MissionTemplateError("mission template payload is invalid")
        return cast(JsonObject, payload)

    def safe_summary(self) -> JsonObject:
        return {
            "mission_template_id": self.template_id,
            "template_payload_digest": self.payload_digest,
            "payload_included": False,
            "freeform_objective_allowed": False,
            "runner_launch_authorized": False,
        }


class MissionTemplateRegistry:
    def __init__(self, templates: tuple[MissionTemplate, ...]) -> None:
        indexed = {template.template_id: template for template in templates}
        if len(indexed) != len(templates) or set(indexed) != {MISSION_TEMPLATE_ID}:
            raise MissionTemplateError("mission template registry is not closed")
        template = indexed[MISSION_TEMPLATE_ID]
        expected_payload_json = canonical_json(_SYNTHETIC_READ_REVIEW_PAYLOAD)
        expected_operation_tool_names = (
            "project.structure.summary",
            "project.test.summary",
        )
        if (
            template.canonical_payload_json != expected_payload_json
            or template.payload_digest != sha256_digest(_SYNTHETIC_READ_REVIEW_PAYLOAD)
            or template.operation_tool_names != expected_operation_tool_names
        ):
            raise MissionTemplateError("mission template registry definition is invalid")
        self._templates = indexed
        self.registry_generation = sha256_digest(
            {
                "schema_version": MISSION_TEMPLATE_REGISTRY_SCHEMA_VERSION,
                "templates": [
                    {
                        "mission_template_id": template.template_id,
                        "template_payload_digest": template.payload_digest,
                    }
                    for template in sorted(templates, key=lambda item: item.template_id)
                ],
            }
        )

    @classmethod
    def startup(cls) -> MissionTemplateRegistry:
        payload_json = canonical_json(_SYNTHETIC_READ_REVIEW_PAYLOAD)
        return cls(
            (
                MissionTemplate(
                    template_id=MISSION_TEMPLATE_ID,
                    canonical_payload_json=payload_json,
                    payload_digest=sha256_digest(_SYNTHETIC_READ_REVIEW_PAYLOAD),
                    operation_tool_names=("project.structure.summary", "project.test.summary"),
                ),
            )
        )

    def get(self, template_id: str) -> MissionTemplate:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise MissionTemplateError("unknown mission template") from exc

    def safe_summary(self) -> JsonObject:
        return {
            "registry_generation": self.registry_generation,
            "template_count": len(self._templates),
            "templates": [
                self._templates[template_id].safe_summary()
                for template_id in sorted(self._templates)
            ],
        }


assert _SYNTHETIC_READ_REVIEW_PAYLOAD["mission_template_id"] == MISSION_TEMPLATE_ID
