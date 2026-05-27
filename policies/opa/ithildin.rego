package ithildin

default decision := {
  "decision": "deny",
  "reason": "no matching OPA policy rule",
  "policy_version": "opa-demo-v1",
  "matched_rules": [],
  "obligations": {"audit_level": "full"},
}

decision := {
  "decision": "deny",
  "reason": "dangerous tool prefix denied",
  "policy_version": "opa-demo-v1",
  "matched_rules": ["deny_dangerous_tool_prefix"],
  "obligations": {"audit_level": "full"},
} {
  startswith(input.tool.name, "shell.")
}

decision := {
  "decision": "require_approval",
  "reason": "writes require approval",
  "policy_version": "opa-demo-v1",
  "matched_rules": ["require_write_approval"],
  "obligations": {"audit_level": "full", "approval_required": true},
} {
  input.tool.risk == "write"
}

decision := {
  "decision": "allow",
  "reason": "in-scope read allowed",
  "policy_version": "opa-demo-v1",
  "matched_rules": ["allow_in_scope_read"],
  "obligations": {"audit_level": "full"},
} {
  input.tool.risk == "read"
  input.resource.in_scope == true
}
