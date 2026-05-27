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


def test_policy_public_exports() -> None:
    policy_package = importlib.import_module("ithildin_policy_core")

    for exported_name in ["PolicyDocument", "PolicyError", "PolicyEvaluator", "PolicyRule"]:
        assert hasattr(policy_package, exported_name)


def test_audit_public_exports() -> None:
    audit_package = importlib.import_module("ithildin_audit_core")

    for exported_name in [
        "AuditVerificationFailure",
        "AuditVerificationResult",
        "AuditWriteError",
        "AuditWriter",
    ]:
        assert hasattr(audit_package, exported_name)


def test_mcp_public_exports() -> None:
    mcp_package = importlib.import_module("ithildin_mcp_server")

    for exported_name in ["IthildinMcpAdapter", "create_mcp_server"]:
        assert hasattr(mcp_package, exported_name)


def test_api_public_exports() -> None:
    api_package = importlib.import_module("ithildin_api")

    for exported_name in [
        "HttpFetchExecutor",
        "PatchProposalService",
        "PatchProposalStore",
        "ReadToolExecutor",
        "Settings",
        "ToolRegistry",
        "create_app",
    ]:
        assert hasattr(api_package, exported_name)
