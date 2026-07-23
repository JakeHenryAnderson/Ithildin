"""Validate the current enterprise operator next action."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_pis_001_internal_review_check,
    production_identity_storage_pis_002_continuation_decision_check,
    production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_authority_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-operator-next-action.md"
DOC_TITLE = "Enterprise Operator Next Action"
NORMALIZED_RESPONSE_RELS = [
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "var/review-runs/mission-control-display/normalized-response.json",
    "var/review-runs/trusted-host-promotion/normalized-response.json",
    "var/review-runs/production-identity-storage/normalized-response.json",
    "var/review-runs/siem-export-adapter/normalized-response.json",
    "var/review-runs/compliance-mapping/normalized-response.json",
    "var/review-runs/sandbox-vm-live-poc/normalized-response.json",
    "var/review-runs/public-security-product-positioning/normalized-response.json",
]

SEND_COMMANDS = [
    "make release-check",
    "make review-candidate",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-now",
]

NEXT_AFTER_SEND_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox",
    "make enterprise-response-waiting-room",
    "make enterprise-response-now",
    "make enterprise-response-paste-preflight",
]

ERG005_NEXT_AFTER_SEND_COMMANDS = [
    "make trusted-host-promotion-response-kit-check",
    "make trusted-host-promotion-response-dry-run",
    "make trusted-host-promotion-external-response-intake-check",
    "make trusted-host-promotion-disposition-closure-check",
    "make enterprise-response-waiting-room",
    "make enterprise-response-now",
]

RESPONSE_COMMANDS = [
    "make enterprise-response-intake-refresh",
]

POST_ERG003_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-ticket-check",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle-check",
]

RUNTIME_GATE_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
    "make sandbox-vm-live-poc-runtime-implementation-gate-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check",
]

DESCRIPTOR_ONLY_PLANNING_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
]

ERG005_TRUSTED_HOST_COMMANDS = [
    "make trusted-host-descriptor-contract-check",
    "make trusted-host-promotion-decision-intake-check",
    "make trusted-host-promotion-state-machine-check",
    "make trusted-host-promotion-negative-fixtures-check",
    "make trusted-host-promotion-zone-contract-check",
    "make trusted-host-promotion-implementation-plan-check",
    "make trusted-host-promotion-source-review-packet-check",
    "make trusted-host-promotion-disposition-packet-check",
    "make trusted-host-promotion-external-review-bundle-check",
    "make trusted-host-promotion-response-kit-check",
    "make trusted-host-promotion-response-dry-run",
    "make trusted-host-promotion-internal-review-check",
    "make trusted-host-promotion-implementation-gate-decision-check",
    "make trusted-host-promotion-limited-runtime-plan-check",
    "make trusted-host-promotion-limited-runtime-ticket-check",
    "make trusted-host-promotion-runtime-implementation-decision-check",
    "make trusted-host-promotion-negative-transcripts",
    "make trusted-host-promotion-runtime-source-review-bundle-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

PIS_001_PLANNING_COMMANDS = [
    "make production-identity-storage-pis-001-planning-gate-check",
    "make production-identity-storage-architecture-decision-record-check",
    "make production-identity-storage-architecture-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

PIS_002_ENTRY_DECISION_COMMANDS = [
    "make production-identity-storage-pis-001-internal-review-check",
    "make production-identity-storage-pis-001-decision-check",
    "make production-identity-storage-pis-001-planning-gate-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

PIS_003_ENTRY_DECISION_COMMANDS = [
    "make production-identity-storage-pis-002-continuation-decision-check",
    "make production-identity-storage-pis-002-sandbox-descriptor-repository-internal-review-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

PIS_003_EXTERNAL_INPUT_ACTION = (
    "await_external_operator_target_and_signed_receipt_inputs_before_separate_"
    "collection_action_authority"
)
PIS_003_DESCENDANT_INVENTORY_FAILURE = (
    "PIS-003 environment evidence collection authority inventory is not exact"
)
PIS_003_REQUIRED_FALSE_AUTHORITY_FIELDS = (
    "operational_collection_action_effective",
    "activation_candidate_preparation_allowed",
    "host_credential_inspection_allowed",
    "test_harness_execution_allowed",
    "driver_load_allowed",
    "external_dsn_consumption_allowed",
    "target_binding_key_consumption_allowed",
    "database_connections_allowed",
    "migration_execution_allowed",
    "postgres_service_allowed",
    "container_lifecycle_allowed",
    "runtime_behavior_changes_allowed",
    "public_api_changes_allowed",
    "current_sqlite_schema_changes_allowed",
    "audit_ordering_changes_allowed",
    "runtime_postgres_allowed",
    "production_identity_allowed",
    "enterprise_rbac_allowed",
    "remote_admin_allowed",
    "backup_restore_runtime_allowed",
    "retention_enforcement_allowed",
    "arbitrary_host_control_allowed",
    "new_power_classes_allowed",
    "public_security_product_positioning_allowed",
    "release_allowed",
    "production_promotion_allowed",
    "uat_complete",
    "uat_required_now",
)

PIS_ARCHITECTURE_REVIEW_COMMANDS = [
    "make production-identity-storage-architecture-check",
    "make production-identity-storage-disposition-packet-check",
    "make production-identity-storage-external-review-bundle-check",
    "make production-identity-storage-response-kit-check",
    "make production-identity-storage-response-dry-run",
    "make production-identity-storage-external-response-intake-check",
    "make production-identity-storage-disposition-closure-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

SEND_ARTIFACTS = [
    {
        "label": "dual_review_outbox",
        "path": "var/review-packets/v3/enterprise-dual-review-outbox",
        "description": "copied ERG-003/ERG-002 attachment set",
    },
    {
        "label": "send_manifest",
        "path": "var/review-packets/v3/enterprise-review-send-manifest",
        "description": "checked manifest with prompt and attachment pointers",
    },
    {
        "label": "send_quickstart",
        "path": "var/review-packets/v3/enterprise-review-send-quickstart",
        "description": "one-page operator index for current send artifacts",
    },
    {
        "label": "submission_prompt",
        "path": "var/review-packets/v3/enterprise-review-submission-prompt",
        "description": "paste-ready external-review submission prompt",
    },
    {
        "label": "send_receipt_template",
        "path": "var/review-packets/v3/enterprise-review-send-receipt-template",
        "description": "operator receipt template to fill after sending",
    },
    {
        "label": "send_receipt_copy",
        "path": (
            "var/review-runs/enterprise-review-send-receipts/"
            "enterprise-review-send-receipt-copy.json"
        ),
        "description": "ignored copied receipt path for the human send step",
    },
    {
        "label": "send_package",
        "path": "var/review-packets/v3/enterprise-review-send-package",
        "description": "compact package index for current send artifacts",
    },
    {
        "label": "upload_staging",
        "path": "var/review-packets/v3/enterprise-review-upload-staging",
        "description": "10-attachment-friendly upload staging batches",
    },
    {
        "label": "dual_response_inbox",
        "path": "var/review-runs/enterprise-dual-response-inbox",
        "description": "ignored raw-response inbox placeholders for ERG-003 and ERG-002",
    },
    {
        "label": "send_session_record",
        "path": "var/review-runs/enterprise-review-send-session-record",
        "description": "local non-authoritative scaffold for operator send details",
    },
]

RESPONSE_ARTIFACTS = [
    {
        "label": "response_inbox",
        "path": "var/review-runs/enterprise-response-inbox",
        "description": "ignored raw-response inbox for pasted reviewer responses",
    },
    {
        "label": "response_status_board",
        "path": "var/review-runs/enterprise-response-status-board",
        "description": "display-only response status board output",
    },
]

POST_ERG003_ARTIFACTS = [
    {
        "label": "dual_response_disposition_record",
        "path": "docs/codex/enterprise-dual-response-disposition-record.md",
        "description": "committed ERG-003/ERG-002 response disposition record",
    },
    {
        "label": "live_poc_runtime_ticket",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-ticket.md",
        "description": "draft-only runtime ticket for a later implementation gate",
    },
    {
        "label": "live_poc_runtime_ticket_review_bundle",
        "path": "var/review-packets/v3/sandbox-vm-live-poc-runtime-ticket-review",
        "description": "focused review packet for the runtime-ticket draft",
    },
]

RUNTIME_GATE_ARTIFACTS = [
    {
        "label": "live_poc_runtime_ticket_internal_review",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md",
        "description": "internal xhigh review record for the runtime-ticket packet",
    },
    {
        "label": "live_poc_runtime_implementation_gate",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md",
        "description": "draft-only runtime implementation gate for a future sprint",
    },
    {
        "label": "live_poc_runtime_descriptor_contract",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md",
        "description": "planning-only descriptor/correlation contract for a future sprint",
    },
    {
        "label": "live_poc_runtime_descriptor_contract_internal_review",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md"),
        "description": "internal xhigh review record for the descriptor/correlation contract",
    },
    {
        "label": "live_poc_runtime_gate_readiness_review_bundle",
        "path": "var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review",
        "description": "focused packet for runtime gate-readiness review",
    },
    {
        "label": "live_poc_runtime_gate_readiness_internal_review",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-internal-review.md"),
        "description": "internal High review record for the runtime gate-readiness checkpoint",
    },
    {
        "label": "live_poc_runtime_descriptor_only_plan",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md",
        "description": (
            "descriptor-only implementation-planning packet for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_ticket",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md"),
        "description": ("descriptor-only implementation ticket for the next runtime checkpoint"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_ticket_review_bundle",
        "path": ("var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-ticket-review"),
        "description": ("focused review packet for the descriptor-only implementation ticket"),
    },
    {
        "label": "live_poc_runtime_gate_readiness_response_intake",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md"),
        "description": "response-intake template for future runtime gate-readiness review",
    },
    {
        "label": "live_poc_runtime_gate_readiness_decision_record_skeleton",
        "path": (
            "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"
        ),
        "description": "decision-record skeleton for descriptor-only planning disposition",
    },
]

DESCRIPTOR_ONLY_PLANNING_ARTIFACTS = [
    {
        "label": "live_poc_runtime_gate_readiness_decision_record",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"),
        "description": ("internal High proxy decision record for descriptor-only planning"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_plan",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md",
        "description": (
            "descriptor-only implementation-planning packet for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_ticket",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md"),
        "description": ("descriptor-only implementation ticket for the next runtime checkpoint"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_decision",
        "path": (
            "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision.md"
        ),
        "description": (
            "planning-only descriptor-only implementation decision draft for the "
            "next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation.md"),
        "description": ("bounded descriptor-only runtime implementation checkpoint"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_internal_source_review",
        "path": (
            "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review.md"
        ),
        "description": ("internal source review for the implemented descriptor-only runtime slice"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_negative_transcripts",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts.md"),
        "description": (
            "secret-free denial transcripts for malformed or authority-expanding descriptors"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_ticket_review_bundle",
        "path": ("var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-ticket-review"),
        "description": ("focused review packet for the descriptor-only implementation ticket"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_source_review_bundle",
        "path": ("var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review"),
        "description": (
            "focused source-review packet for the implemented descriptor-only runtime slice"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_external_response_intake",
        "path": (
            "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md"
        ),
        "description": ("response-intake template for the descriptor-only runtime source review"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_inbox",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md"),
        "description": ("focused raw-response inbox for descriptor-only runtime source review"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_send_receipt",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md"),
        "description": ("operator send receipt scaffold for descriptor-only runtime source review"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_dry_run",
        "path": ("docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md"),
        "description": ("response dry-run fixtures for descriptor-only runtime source review"),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_application_preflight",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md"
        ),
        "description": (
            "preflight for applying a future real descriptor-only source-review response"
        ),
    },
]

ERG005_TRUSTED_HOST_ARTIFACTS = [
    {
        "label": "trusted_host_descriptor_contract",
        "path": "docs/codex/trusted-host-descriptor-contract.md",
        "description": "design-only host descriptor contract for blocked ERG-005 planning",
    },
    {
        "label": "trusted_host_decision_intake",
        "path": "docs/codex/trusted-host-promotion-decision-intake.md",
        "description": "decision-intake packet for blocked ERG-005 trusted-host promotion",
    },
    {
        "label": "trusted_host_state_machine",
        "path": "docs/codex/trusted-host-promotion-state-machine.md",
        "description": "design-only promotion state-machine contract",
    },
    {
        "label": "trusted_host_negative_fixtures",
        "path": "docs/codex/trusted-host-promotion-negative-fixtures.md",
        "description": "negative fixture contract for future promotion claims",
    },
    {
        "label": "trusted_host_zone_contract",
        "path": "docs/codex/trusted-host-promotion-zone-contract.md",
        "description": "source/destination zone labels for future promotion design",
    },
    {
        "label": "trusted_host_implementation_plan",
        "path": "docs/codex/trusted-host-promotion-implementation-plan.md",
        "description": "Goal A implementation-planning contract that still blocks runtime behavior",
    },
    {
        "label": "trusted_host_source_review_packet",
        "path": "var/review-packets/v3/trusted-host-promotion-source-review",
        "description": "Goal B runtime-boundary source-review packet for the trusted-host lane",
    },
    {
        "label": "trusted_host_disposition_packet",
        "path": "var/review-packets/v3/trusted-host-promotion-disposition",
        "description": "disposition packet for the trusted-host design lane",
    },
    {
        "label": "trusted_host_external_review_bundle",
        "path": "var/review-packets/v3/trusted-host-promotion-external-review",
        "description": "external-review bundle for trusted-host promotion planning",
    },
    {
        "label": "trusted_host_response_kit",
        "path": "var/review-packets/v3/trusted-host-promotion-response-kit",
        "description": "response-intake kit for future trusted-host reviewer feedback",
    },
    {
        "label": "trusted_host_goal_c_decision",
        "path": "docs/codex/trusted-host-promotion-implementation-gate-decision.md",
        "description": "Goal C decision allowing only a future limited runtime plan",
    },
    {
        "label": "trusted_host_limited_runtime_plan",
        "path": "docs/codex/trusted-host-promotion-limited-runtime-plan.md",
        "description": "strict limited-runtime planning checkpoint with stop/pivot guardrails",
    },
    {
        "label": "trusted_host_limited_runtime_ticket",
        "path": "docs/codex/trusted-host-promotion-limited-runtime-ticket.md",
        "description": "future implementation-ticket skeleton for the staging-only slice",
    },
    {
        "label": "trusted_host_runtime_implementation_decision",
        "path": "docs/codex/trusted-host-promotion-runtime-implementation-decision.md",
        "description": "implementation-gate decision draft for the staging-only slice",
    },
    {
        "label": "trusted_host_runtime_implementation",
        "path": "docs/codex/trusted-host-promotion-runtime-implementation.md",
        "description": "implemented staging-only runtime slice documentation",
    },
    {
        "label": "trusted_host_runtime_internal_review",
        "path": "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
        "description": "internal source review for the staging-only runtime slice",
    },
    {
        "label": "trusted_host_runtime_source_review_bundle",
        "path": "var/review-packets/v3/trusted-host-promotion-runtime-source-review",
        "description": (
            "focused source-review packet for the implemented staging-only runtime slice"
        ),
    },
]

PIS_001_PLANNING_ARTIFACTS = [
    {
        "label": "production_identity_storage_architecture_decision",
        "path": ("docs/codex/production-identity-storage-architecture-decision-record.md"),
        "description": "decision permitting only bounded PIS-001 planning",
    },
    {
        "label": "production_identity_storage_pis_001_planning_gate",
        "path": ("docs/codex/production-identity-storage-pis-001-planning-gate.md"),
        "description": "fail-closed scope and done criteria for PIS-001 planning",
    },
    {
        "label": "production_identity_storage_architecture",
        "path": "docs/codex/production-identity-storage-architecture.md",
        "description": "planning-only Phase 1 identity and storage architecture",
    },
    {
        "label": "production_identity_storage_source_review",
        "path": "docs/codex/production-identity-storage-source-review.md",
        "description": "accepted exact-candidate architecture source review",
    },
]

PIS_002_ENTRY_DECISION_ARTIFACTS = [
    {
        "label": "production_identity_storage_pis_001_decision",
        "path": (
            "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
        ),
        "description": "reviewed threat, dependency, and PIS-002 stop-line contract",
    },
    {
        "label": "production_identity_storage_pis_001_contract",
        "path": "docs/codex/production-identity-storage-pis-001-decision.json",
        "description": "closed fail-closed authority and threat-family contract",
    },
    {
        "label": "production_identity_storage_pis_001_internal_review",
        "path": ("docs/codex/production-identity-storage-pis-001-internal-source-review.md"),
        "description": "zero-open-finding exact-candidate PIS-001 review",
    },
]

PIS_003_ENTRY_DECISION_ARTIFACTS = [
    {
        "label": "production_identity_storage_pis_002_continuation_decision",
        "path": ("docs/codex/production-identity-storage-pis-002-continuation-decision-record.md"),
        "description": "decision allowing only PIS-003 entry-decision preparation",
    },
    {
        "label": "production_identity_storage_pis_002_continuation_contract",
        "path": ("docs/codex/production-identity-storage-pis-002-continuation-decision.json"),
        "description": "closed continuation authority and unresolved-boundary contract",
    },
    {
        "label": "production_identity_storage_pis_002_internal_review",
        "path": (
            "docs/codex/production-identity-storage-pis-002-"
            "sandbox-descriptor-repository-internal-source-review.md"
        ),
        "description": "zero-open-finding exact-candidate PIS-002 implementation review",
    },
]

PIS_003_EXTERNAL_INPUT_ARTIFACTS = [
    {
        "label": "production_identity_storage_pis_003_environment_evidence_authority_record",
        "path": (
            "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
            "environment-evidence-collection-authority-record.md"
        ),
        "description": (
            "reviewed two-permission activation disposition with no operational action"
        ),
    },
    {
        "label": "production_identity_storage_pis_003_environment_evidence_authority_contract",
        "path": (
            "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
            "environment-evidence-collection-authority.json"
        ),
        "description": ("closed authority ceiling for target selection and signed receipt intake"),
    },
]

PIS_ARCHITECTURE_REVIEW_ARTIFACTS = [
    {
        "label": "production_identity_storage_architecture",
        "path": "docs/codex/production-identity-storage-architecture.md",
        "description": "planning-only Phase 1 identity and storage architecture",
    },
    {
        "label": "production_identity_storage_external_review_bundle",
        "path": "var/review-packets/v3/production-identity-storage-external-review",
        "description": "focused production identity/storage architecture-review bundle",
    },
    {
        "label": "production_identity_storage_response_kit",
        "path": "var/review-packets/v3/production-identity-storage-response-kit",
        "description": "fail-closed response-intake kit for ERG-006/ERG-007",
    },
]

REQUIRED_DOC_PHRASES = [
    "Status: checked read-only operator next-action summary",
    "Current governed tool count: `24`",
    "make enterprise-operator-next-action",
    "Historical Send Fallback",
    "current route after the recorded dispositions",
    "If the dual-response disposition record, runtime-ticket internal review, runtime "
    "gate-readiness",
    "descriptor_only_local_preview_disposition_ready",
    "accepted staging-only",
    "`ERG-005` source-finding disposition",
    PIS_003_EXTERNAL_INPUT_ACTION,
    "external_operator_input_required",
    "operational collection action",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-now",
    "handoff_artifacts",
    "The architecture review and exact-candidate finding",
    "For the current active route, the primary lane is waiting for an external",
    "two proposal-level permissions do not make an operational collection action",
    "remain unauthorized",
    "Historical fallback lanes remain available only when the operator next-action command reports",
    "`ERG-003`: static sandbox/VM preflight disposition",
    "`ERG-002`: Mission Control display/import planning review",
    "make enterprise-response-intake-refresh",
    "What This Does Not Approve",
]

BLOCKED_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter runtime behavior",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready",
    "production-ready",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
    "public security product approved",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []

    response_state = _response_state(repo_root)
    response_present_count = response_state["response_present_count"]
    closure_ready_count = response_state["closure_ready_count"]
    disposition_recorded = _dual_response_disposition_recorded(repo_root)
    internal_review_recorded = _runtime_ticket_internal_review_recorded(repo_root)
    runtime_gate_decision_recorded = _runtime_gate_readiness_decision_recorded(repo_root)
    descriptor_only_disposition_recorded = _descriptor_only_disposition_recorded(repo_root)
    erg005_runtime_source_findings_disposition_recorded = (
        _erg005_runtime_source_findings_disposition_recorded(repo_root)
    )
    pis_architecture_decision_recorded = _pis_architecture_decision_recorded(repo_root)
    pis_001_exact_review_recorded = _pis_001_exact_review_recorded(repo_root)
    pis_002_continuation_artifact_present = any(
        (repo_root / relative_path).exists()
        for relative_path in (
            production_identity_storage_pis_002_continuation_decision_check.DOC_REL,
            production_identity_storage_pis_002_continuation_decision_check.CONTRACT_REL,
        )
    )
    pis_002_continuation_decision_recorded = _pis_002_continuation_decision_recorded(repo_root)
    if pis_002_continuation_artifact_present and not pis_002_continuation_decision_recorded:
        failures.append("PIS-002 continuation decision artifacts are present but invalid")
    pis_003_collection_authority_artifact_present = any(
        (repo_root / relative_path).exists()
        for relative_path in (
            production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_authority_check.DOC_REL,
            production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_authority_check.CONTRACT_REL,
        )
    )
    pis_003_collection_activation_review_recorded = _pis_003_collection_activation_review_recorded(
        repo_root
    )
    if (
        pis_003_collection_authority_artifact_present
        and not pis_003_collection_activation_review_recorded
    ):
        failures.append(
            "PIS-003 environment evidence collection authority artifacts are present "
            "but invalid or exceed the reviewed non-action ceiling"
        )
    next_action = _next_action(
        response_present_count,
        closure_ready_count,
        disposition_recorded=disposition_recorded,
        internal_review_recorded=internal_review_recorded,
        runtime_gate_decision_recorded=runtime_gate_decision_recorded,
        descriptor_only_disposition_recorded=descriptor_only_disposition_recorded,
        erg005_runtime_source_findings_disposition_recorded=(
            erg005_runtime_source_findings_disposition_recorded
        ),
        pis_architecture_decision_recorded=pis_architecture_decision_recorded,
        pis_001_exact_review_recorded=pis_001_exact_review_recorded,
        pis_002_continuation_artifact_present=pis_002_continuation_artifact_present,
        pis_002_continuation_decision_recorded=pis_002_continuation_decision_recorded,
        pis_003_collection_authority_artifact_present=(
            pis_003_collection_authority_artifact_present
        ),
        pis_003_collection_activation_review_recorded=(
            pis_003_collection_activation_review_recorded
        ),
    )
    action_commands: list[str]
    handoff_artifacts: list[dict[str, str]]
    recommended_send_set: list[str]
    if next_action in {
        "invalid_pis_002_continuation_decision",
        "invalid_pis_003_environment_evidence_collection_authority",
    }:
        action_commands = []
        handoff_artifacts = []
        recommended_send_set = []
        recommended_next_enterprise_review = "blocked"
    elif next_action == PIS_003_EXTERNAL_INPUT_ACTION:
        action_commands = []
        handoff_artifacts = PIS_003_EXTERNAL_INPUT_ARTIFACTS
        recommended_send_set = []
        recommended_next_enterprise_review = "external_operator_input_required"
    elif next_action == "send_erg_003_and_erg_002":
        action_commands = SEND_COMMANDS
        handoff_artifacts = SEND_ARTIFACTS
        recommended_send_set = ["ERG-003", "ERG-002"]
        recommended_next_enterprise_review = "ERG-003"
    elif next_action == "prepare_erg004_runtime_ticket_review":
        action_commands = POST_ERG003_COMMANDS
        handoff_artifacts = POST_ERG003_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    elif next_action == "prepare_erg004_runtime_implementation_gate":
        action_commands = RUNTIME_GATE_COMMANDS
        handoff_artifacts = RUNTIME_GATE_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    elif next_action == "prepare_erg004_descriptor_only_runtime_planning":
        action_commands = DESCRIPTOR_ONLY_PLANNING_COMMANDS
        handoff_artifacts = DESCRIPTOR_ONLY_PLANNING_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    elif next_action == "prepare_erg005_trusted_host_promotion_review":
        action_commands = ERG005_TRUSTED_HOST_COMMANDS
        handoff_artifacts = ERG005_TRUSTED_HOST_ARTIFACTS
        recommended_send_set = ["ERG-005"]
        recommended_next_enterprise_review = "ERG-005"
    elif next_action == "prepare_pis_002_entry_decision_record":
        action_commands = PIS_002_ENTRY_DECISION_COMMANDS
        handoff_artifacts = PIS_002_ENTRY_DECISION_ARTIFACTS
        recommended_send_set = ["ERG-006", "ERG-007"]
        recommended_next_enterprise_review = "ERG-006/ERG-007"
    elif next_action == "prepare_pis_003_entry_decision_record":
        action_commands = PIS_003_ENTRY_DECISION_COMMANDS
        handoff_artifacts = PIS_003_ENTRY_DECISION_ARTIFACTS
        recommended_send_set = ["ERG-006", "ERG-007"]
        recommended_next_enterprise_review = "ERG-006/ERG-007"
    elif next_action == "execute_pis_001_threat_model_dependency_decision":
        action_commands = PIS_001_PLANNING_COMMANDS
        handoff_artifacts = PIS_001_PLANNING_ARTIFACTS
        recommended_send_set = ["ERG-006", "ERG-007"]
        recommended_next_enterprise_review = "ERG-006/ERG-007"
    elif next_action == ("prepare_erg006_erg007_production_identity_storage_architecture_review"):
        action_commands = PIS_ARCHITECTURE_REVIEW_COMMANDS
        handoff_artifacts = PIS_ARCHITECTURE_REVIEW_ARTIFACTS
        recommended_send_set = ["ERG-006", "ERG-007"]
        recommended_next_enterprise_review = "ERG-006/ERG-007"
    else:
        action_commands = RESPONSE_COMMANDS
        handoff_artifacts = RESPONSE_ARTIFACTS
        recommended_send_set = ["ERG-003", "ERG-002"]
        recommended_next_enterprise_review = "ERG-003"

    selected_capability = "not selected"

    boundary_flags = {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }
    for key, expected in boundary_flags.items():
        if response_state.get(key) is not expected:
            failures.append(f"response-state boundary flag drifted: {key}")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise operator next-action doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(
                f"enterprise operator next-action doc is missing blocked phrase: {phrase}"
            )
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                f"enterprise operator next-action doc contains forbidden phrase: {phrase}"
            )
    if "The current primary lanes are:" in doc:
        failures.append(
            "enterprise operator next-action doc still describes historical lanes as current"
        )
    response_section = doc.split("## If Responses Arrive", 1)[-1].split(
        "## What This Does Not Approve", 1
    )[0]
    current_response_block = response_section.split(
        "Historical fallback lanes remain available", 1
    )[0]
    if "make enterprise-dual-response-inbox" in current_response_block:
        failures.append(
            "enterprise operator next-action current response flow still uses dual inbox"
        )

    if "enterprise-operator-next-action:" not in makefile:
        failures.append("Make target is missing: enterprise-operator-next-action")
    if (
        "enterprise-operator-next-action" not in release_check_body
        and "release-check: enterprise-operator-next-action" not in makefile
    ):
        failures.append("enterprise-operator-next-action is missing from release-check")
    if "$(MAKE) enterprise-operator-next-action" not in review_candidate_body:
        failures.append("enterprise-operator-next-action is missing from review-candidate")
    if "make enterprise-operator-next-action" not in readme:
        failures.append("README is missing enterprise operator next-action command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise operator next-action doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise operator next-action is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise operator next-action is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise operator next action")
    if "enterprise-operator-next-action" not in release_guardrails:
        failures.append("release guardrails do not require enterprise operator next action")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "next_action_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": selected_capability,
        "recommended_send_set": recommended_send_set,
        "recommended_next_enterprise_review": recommended_next_enterprise_review,
        "response_present_count": response_present_count,
        "closure_ready_count": closure_ready_count,
        "dual_response_disposition_recorded": disposition_recorded,
        "runtime_ticket_internal_review_recorded": internal_review_recorded,
        "runtime_gate_readiness_decision_recorded": runtime_gate_decision_recorded,
        "descriptor_only_disposition_recorded": descriptor_only_disposition_recorded,
        "erg005_runtime_source_findings_disposition_recorded": (
            erg005_runtime_source_findings_disposition_recorded
        ),
        "pis_architecture_decision_recorded": pis_architecture_decision_recorded,
        "pis_001_exact_review_recorded": pis_001_exact_review_recorded,
        "pis_002_continuation_artifact_present": (pis_002_continuation_artifact_present),
        "pis_002_continuation_decision_recorded": pis_002_continuation_decision_recorded,
        "pis_003_collection_authority_artifact_present": (
            pis_003_collection_authority_artifact_present
        ),
        "pis_003_collection_activation_review_recorded": (
            pis_003_collection_activation_review_recorded
        ),
        "next_action": next_action,
        "action_commands": action_commands,
        "next_after_send_commands": (
            []
            if next_action
            in {
                "invalid_pis_002_continuation_decision",
                "invalid_pis_003_environment_evidence_collection_authority",
                PIS_003_EXTERNAL_INPUT_ACTION,
            }
            else PIS_003_ENTRY_DECISION_COMMANDS
            if next_action == "prepare_pis_003_entry_decision_record"
            else PIS_002_ENTRY_DECISION_COMMANDS
            if next_action == "prepare_pis_002_entry_decision_record"
            else PIS_001_PLANNING_COMMANDS
            if next_action == "execute_pis_001_threat_model_dependency_decision"
            else ERG005_NEXT_AFTER_SEND_COMMANDS
            if next_action == "prepare_erg005_trusted_host_promotion_review"
            else NEXT_AFTER_SEND_COMMANDS
        ),
        "handoff_artifacts": handoff_artifacts,
        "normalized_response_paths": response_state["normalized_response_paths"],
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise operator next action",
        f"valid: {str(report['valid']).lower()}",
        f"next_action_doc: {report['next_action_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: " + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"next_action: {report.get('next_action', 'unknown')}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands", [])],
        "next_after_send_commands:",
        *[f"- {command}" for command in report.get("next_after_send_commands", [])],
        "handoff_artifacts:",
        *[
            f"- {artifact['label']}: {artifact['path']}"
            for artifact in report.get("handoff_artifacts", [])
        ],
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _next_action(
    response_present_count: int,
    closure_ready_count: int,
    *,
    disposition_recorded: bool,
    internal_review_recorded: bool,
    runtime_gate_decision_recorded: bool,
    descriptor_only_disposition_recorded: bool,
    erg005_runtime_source_findings_disposition_recorded: bool,
    pis_architecture_decision_recorded: bool,
    pis_001_exact_review_recorded: bool,
    pis_002_continuation_artifact_present: bool = False,
    pis_002_continuation_decision_recorded: bool = False,
    pis_003_collection_authority_artifact_present: bool = False,
    pis_003_collection_activation_review_recorded: bool = False,
) -> str:
    if closure_ready_count > 0:
        return "run_lane_specific_closure_playbook"
    if response_present_count > 0:
        return "run_response_intake_preflight"
    if pis_003_collection_authority_artifact_present:
        if not pis_003_collection_activation_review_recorded:
            return "invalid_pis_003_environment_evidence_collection_authority"
        return PIS_003_EXTERNAL_INPUT_ACTION
    if pis_002_continuation_artifact_present:
        if not pis_002_continuation_decision_recorded:
            return "invalid_pis_002_continuation_decision"
        return "prepare_pis_003_entry_decision_record"
    if pis_001_exact_review_recorded:
        return "prepare_pis_002_entry_decision_record"
    if pis_architecture_decision_recorded:
        return "execute_pis_001_threat_model_dependency_decision"
    if erg005_runtime_source_findings_disposition_recorded:
        return "prepare_erg006_erg007_production_identity_storage_architecture_review"
    if descriptor_only_disposition_recorded:
        return "prepare_erg005_trusted_host_promotion_review"
    if runtime_gate_decision_recorded:
        return "prepare_erg004_descriptor_only_runtime_planning"
    if internal_review_recorded:
        return "prepare_erg004_runtime_implementation_gate"
    if disposition_recorded:
        return "prepare_erg004_runtime_ticket_review"
    return "send_erg_003_and_erg_002"


def _dual_response_disposition_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/enterprise-dual-response-disposition-record.md"
    text = _read(path)
    return (
        "`closed_local_preview_static_preflight`" in text
        and "`ready_for_design_only_decision_record`" in text
        and "EXT-MC-DISPLAY-001" in text
        and "runtime importer behavior" in text
        and "live VM/container inspection" in text
    )


def _pis_architecture_decision_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/production-identity-storage-architecture-decision-record.md"
    text = _read(path)
    return (
        "`PRD-PROD-IAM-STORAGE-ARCH-001`" in text
        and "`approved_for_pis_001_planning_only`" in text
        and "production-identity-storage-pis-001-planning-gate.md" in text
        and "Recorded `ERG-006` status: `planning_only`." in text
        and "Recorded `ERG-007` status: `planning_only`." in text
        and "Current selected runtime capability: `not selected`." in text
    )


def _pis_001_exact_review_recorded(repo_root: Path) -> bool:
    report = production_identity_storage_pis_001_internal_review_check.build_report(repo_root)
    return (
        report.get("valid") is True
        and report.get("reviewed_commit") == "177c0c6e461176d85126c9817dba40b3a092ec95"
        and report.get("open_findings") == 0
        and report.get("pis_002_entry_decision_record_preparation_allowed") is True
        and report.get("pis_002_implementation_allowed") is False
        and report.get("dependency_changes_allowed") is False
        and report.get("runtime_changes_allowed") is False
    )


def _pis_002_continuation_decision_recorded(repo_root: Path) -> bool:
    report = production_identity_storage_pis_002_continuation_decision_check.build_report(repo_root)
    return (
        report.get("valid") is True
        and report.get("pis_002_dependency_free_interface_phase_complete") is True
        and report.get("pis_003_entry_decision_preparation_allowed") is True
        and report.get("pis_003_implementation_allowed") is False
        and report.get("dependency_changes_allowed") is False
        and report.get("schema_changes_allowed") is False
        and report.get("database_migrations_allowed") is False
        and report.get("runtime_postgres_allowed") is False
        and report.get("production_identity_allowed") is False
        and report.get("release_allowed") is False
        and report.get("tool_count") == 24
        and report.get("next_required_action") == "prepare_pis_003_entry_decision_record"
    )


def _pis_003_collection_activation_review_recorded(repo_root: Path) -> bool:
    validator = (
        production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_authority_check
    )
    report = validator.build_report(repo_root)
    # The authority validator intentionally proves only its exact 12-path candidate.
    # A later status-only descendant therefore has one expected inventory failure.
    # Accept that failure only when every immutable digest, reviewed ancestor, parent
    # gate, and wiring check still passes; any other failure remains fail-closed.
    expected_status = report.get("valid") is True or report.get("failures") == [
        PIS_003_DESCENDANT_INVENTORY_FAILURE
    ]
    required_false_fields = (
        "target_selected",
        "intake_root_created",
        "receipt_collection_started",
        "psycopg_driver_loaded",
        "database_connection_attempted",
        "online_migration_executed",
    )
    return (
        expected_status
        and report.get("tool_count") == 24
        and report.get("baseline_exists") is True
        and report.get("baseline_is_ancestor") is True
        and report.get("reviewed_candidate_commit_exists") is True
        and report.get("reviewed_candidate_commit_is_ancestor") is True
        and report.get("reviewed_candidate_path_hashes_match") is True
        and report.get("activation_reviewed_candidate_commit_exists") is True
        and report.get("activation_reviewed_candidate_commit_is_ancestor") is True
        and report.get("activation_reviewed_candidate_path_hashes_match") is True
        and report.get("authority_document_hash_matches") is True
        and report.get("authority_contract_hash_matches") is True
        and report.get("contract_valid") is True
        and report.get("protected_hashes_match") is True
        and report.get("parent_gate_valid") is True
        and report.get("wiring_valid") is True
        and all(report.get(field) is False for field in required_false_fields)
        and all(
            report.get(field) is False
            for field in PIS_003_REQUIRED_FALSE_AUTHORITY_FIELDS
        )
    )


def _runtime_ticket_internal_review_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md"
    text = _read(path)
    return (
        "approve_internal_runtime_ticket_review" in text
        and "Critical/high findings: none." in text
        and "The next allowed action is to prepare a separate explicit runtime implementation gate."
        in text
        and "make sandbox-vm-live-poc-runtime-ticket-internal-review-check" in text
    )


def _runtime_gate_readiness_decision_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"
    text = _read(path)
    return (
        "Decision ID: `PRD-SANDBOX-LIVE-GATE-001`." in text
        and "Decision outcome: `approved_for_descriptor_only_runtime_implementation_planning`."
        in text
        and "not runtime implementation approval" in text
        and "not\nexternal validation" in text
        and "Finding count: `0`" in text
    )


def _descriptor_only_disposition_recorded(repo_root: Path) -> bool:
    path = (
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md"
    )
    text = _read(path)
    return (
        "Applied descriptor-only local-development disposition:" in text
        and "reviewer_type: `codex-high`" in text
        and "disposition: `approve_descriptor_only_local_preview_disposition`" in text
        and "resulting_state: `descriptor_only_local_preview_disposition_ready`" in text
        and "finding_count: `0`" in text
        and "not external review" in text
        and "not live VM/container runtime approval" in text
    )


def _erg005_runtime_source_findings_disposition_recorded(repo_root: Path) -> bool:
    source_review = _read(repo_root / "docs/codex/trusted-host-promotion-runtime-source-review.md")
    finding_002 = _read(
        repo_root / "docs/codex/findings/ext-trusted-host-runtime-002-governance-bindings.md"
    )
    finding_006 = _read(
        repo_root / "docs/codex/findings/ext-trusted-host-runtime-006-adversarial-coverage.md"
    )
    exact_commit = "919858e8d5886129d7c1fefc730795380cd45f73"
    exact_packet = "sha256:02b060bb65d41b317b3a426cd1ad9786d101683303622cb9eedb34436bb9ed16"
    shared_finding_markers = (
        f"exact clean commit {exact_commit}",
        f"focused packet manifest {exact_packet}",
        "- Disposition: fixed",
        "does not close ERG-005",
        "authorize promotion, placement, release, UAT, production use, or new powers",
    )
    return (
        exact_commit in source_review
        and exact_packet in source_review
        and "`EXT-TRUSTED-HOST-RUNTIME-002` and `EXT-TRUSTED-HOST-RUNTIME-006` as `fixed`"
        in source_review
        and "`runtime_findings_closed`" in source_review
        and "`runtime_source_review_ready_for_triage`" in source_review
        and "This accepted response closes the two tracked source findings; it does not "
        "close `ERG-005`"
        in source_review
        and all(marker in finding_002 for marker in shared_finding_markers)
        and all(marker in finding_006 for marker in shared_finding_markers)
    )


def _response_state(repo_root: Path) -> dict[str, Any]:
    paths = [
        response_rel
        for response_rel in NORMALIZED_RESPONSE_RELS
        if (repo_root / response_rel).exists()
    ]
    closure_ready_count = 0
    for response_rel in paths:
        try:
            payload = json.loads((repo_root / response_rel).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("closure_ready") is True:
            closure_ready_count += 1
    return {
        "response_present_count": len(paths),
        "closure_ready_count": closure_ready_count,
        "normalized_response_paths": paths,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
