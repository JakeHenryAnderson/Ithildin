from __future__ import annotations

import pytest
from ithildin_api.mission_templates import (
    MissionTemplate,
    MissionTemplateError,
    MissionTemplateRegistry,
)


def test_startup_template_registry_is_closed_hashed_and_payload_safe() -> None:
    registry = MissionTemplateRegistry.startup()
    template = registry.get("synthetic_read_review_v1")
    summary = registry.safe_summary()

    assert registry.registry_generation.startswith("sha256:")
    assert template.payload_digest.startswith("sha256:")
    assert summary["template_count"] == 1
    assert "operations" not in str(summary)
    templates = summary["templates"]
    assert isinstance(templates, list)
    first = templates[0]
    assert isinstance(first, dict)
    assert first["payload_included"] is False
    assert first["runner_launch_authorized"] is False
    with pytest.raises(MissionTemplateError, match="unknown mission template"):
        registry.get("caller_template")


def test_template_payload_delivery_copy_cannot_mutate_registry() -> None:
    registry = MissionTemplateRegistry.startup()
    first = registry.get("synthetic_read_review_v1").payload_copy()
    first["mission_kind"] = "tampered"

    second = registry.get("synthetic_read_review_v1").payload_copy()
    assert second["mission_kind"] == "synthetic_read_review"
    assert second["host_control"] == {
        "runner_launch_allowed": False,
        "shell_allowed": False,
        "filesystem_write_allowed": False,
        "network_allowed": False,
    }


@pytest.mark.parametrize(
    "tampered",
    (
        MissionTemplate(
            template_id="synthetic_read_review_v1",
            canonical_payload_json=MissionTemplateRegistry.startup()
            .get("synthetic_read_review_v1")
            .canonical_payload_json.replace('"network_allowed":false', '"network_allowed":true'),
            payload_digest=MissionTemplateRegistry.startup()
            .get("synthetic_read_review_v1")
            .payload_digest,
            operation_tool_names=("project.structure.summary", "project.test.summary"),
        ),
        MissionTemplate(
            template_id="synthetic_read_review_v1",
            canonical_payload_json=MissionTemplateRegistry.startup()
            .get("synthetic_read_review_v1")
            .canonical_payload_json,
            payload_digest="sha256:" + ("0" * 64),
            operation_tool_names=("project.structure.summary", "project.test.summary"),
        ),
        MissionTemplate(
            template_id="synthetic_read_review_v1",
            canonical_payload_json=MissionTemplateRegistry.startup()
            .get("synthetic_read_review_v1")
            .canonical_payload_json,
            payload_digest=MissionTemplateRegistry.startup()
            .get("synthetic_read_review_v1")
            .payload_digest,
            operation_tool_names=("project.structure.summary",),
        ),
    ),
)
def test_template_registry_rejects_inconsistent_fixed_definitions(
    tampered: MissionTemplate,
) -> None:
    with pytest.raises(MissionTemplateError, match="definition is invalid"):
        MissionTemplateRegistry((tampered,))
