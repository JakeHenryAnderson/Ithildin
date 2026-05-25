import importlib


def test_python_packages_import() -> None:
    package_names = [
        "ithildin_api",
        "ithildin_mcp_server",
        "ithildin_audit_core",
        "ithildin_policy_core",
        "ithildin_schemas",
        "ithildin_tool_sdk",
    ]

    for package_name in package_names:
        module = importlib.import_module(package_name)
        assert module.__version__ == "0.1.0"


def test_schema_public_exports() -> None:
    schema_package = importlib.import_module("ithildin_schemas")
    exported_names = [
        "ApprovalDecision",
        "ApprovalDecisionValue",
        "ApprovalRequest",
        "ApprovalStatus",
        "AuditEvent",
        "AuditEventType",
        "JsonObject",
        "JsonValue",
        "PolicyDecision",
        "PolicyDecisionValue",
        "PolicyInput",
        "ToolCallRequest",
        "ToolCallResult",
        "ToolManifest",
        "ToolRisk",
        "canonical_json",
        "sha256_digest",
    ]

    for exported_name in exported_names:
        assert hasattr(schema_package, exported_name)
