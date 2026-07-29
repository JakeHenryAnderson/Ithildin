from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.enterprise_identity import (
    CallerAuthorityRejectedError,
    EnterpriseIdentityConflictError,
    EnterpriseIdentityDisabledError,
    EnterpriseIdentityError,
    EnterpriseIdentityNotFoundError,
    EnterpriseIdentityStore,
    EnterprisePrincipalType,
    OrganizationRole,
    WorkspaceRole,
    reject_caller_authority_fields,
)

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
ISSUER = "https://identity.example.test/tenant-a"


def make_store(tmp_path: Path) -> EnterpriseIdentityStore:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    counts: defaultdict[str, int] = defaultdict(int)

    def identifier(prefix: str) -> str:
        counts[prefix] += 1
        return prefix + f"{counts[prefix]:032x}"

    return EnterpriseIdentityStore(
        db_path,
        clock=lambda: NOW,
        id_factory=identifier,
    )


def provision(store: EnterpriseIdentityStore) -> tuple[str, str, str]:
    organization = store.create_organization()
    provider = store.add_provider_configuration(
        organization.organization_id,
        exact_issuer=ISSUER,
    )
    identity = store.provision_human_identity(
        organization.organization_id,
        provider.provider_configuration_id,
        exact_issuer=ISSUER,
        subject="subject-Aa-001",
    )
    return (
        organization.organization_id,
        provider.provider_configuration_id,
        identity.principal_id,
    )


def test_exact_identity_key_uses_random_principal_and_safe_audit_reference(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    organization_id, provider_id, principal_id = provision(store)

    resolved = store.resolve_identity(
        organization_id,
        provider_id,
        exact_issuer=ISSUER,
        subject="subject-Aa-001",
    )
    audit = resolved.safe_audit_metadata(outcome="allowed", reason_code="identity_resolved")

    assert principal_id.startswith("prn_")
    assert len(principal_id) == 36
    assert resolved.principal_type is EnterprisePrincipalType.HUMAN
    assert resolved.identity_generation == 1
    assert resolved.identity_audit_id.startswith("iaud_")
    serialized = json.dumps(audit, sort_keys=True)
    assert "subject-Aa-001" not in serialized
    assert ISSUER not in serialized
    assert "claims" not in serialized
    assert "credential" not in serialized
    assert set(audit) == {
        "identity_audit_id",
        "principal_id",
        "principal_type",
        "organization_id",
        "provider_configuration_id",
        "identity_generation",
        "outcome",
        "reason_code",
    }


@pytest.mark.parametrize(
    "different_issuer",
    [
        "https://identity.example.test/tenant-a/",
        "https://IDENTITY.example.test/tenant-a",
    ],
)
def test_equivalent_looking_issuer_is_not_normalized_into_authority(
    tmp_path: Path,
    different_issuer: str,
) -> None:
    store = make_store(tmp_path)
    organization_id, provider_id, _ = provision(store)

    with pytest.raises(EnterpriseIdentityNotFoundError, match="mapping not found"):
        store.resolve_identity(
            organization_id,
            provider_id,
            exact_issuer=different_issuer,
            subject="subject-Aa-001",
        )


def test_immutable_identity_key_cannot_be_remapped(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    organization_id, provider_id, principal_id = provision(store)

    with pytest.raises(EnterpriseIdentityConflictError, match="already exists"):
        store.provision_human_identity(
            organization_id,
            provider_id,
            exact_issuer=ISSUER,
            subject="subject-Aa-001",
        )

    with sqlite3.connect(store.db_path) as connection:
        rows = connection.execute(
            "SELECT principal_id FROM identity_bindings"
        ).fetchall()
    assert rows == [(principal_id,)]


def test_malformed_issuer_or_subject_fails_before_persistence(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    organization = store.create_organization()

    for issuer in (
        "http://identity.example.test",
        "https://user@identity.example.test",
        "https://identity.example.test?tenant=a",
        " https://identity.example.test",
    ):
        with pytest.raises(EnterpriseIdentityError, match="issuer is malformed"):
            store.add_provider_configuration(
                organization.organization_id,
                exact_issuer=issuer,
            )

    provider = store.add_provider_configuration(
        organization.organization_id,
        exact_issuer=ISSUER,
    )
    with pytest.raises(EnterpriseIdentityError, match="subject is malformed"):
        store.provision_human_identity(
            organization.organization_id,
            provider.provider_configuration_id,
            exact_issuer=ISSUER,
            subject="subject\ninjected",
        )


def test_caller_authority_fields_are_rejected_recursively() -> None:
    reject_caller_authority_fields(
        {
            "resource": {"artifact_id": "artifact-1"},
            "filters": [{"status": "pending"}],
        }
    )

    for payload in (
        {"principal_id": "prn_spoofed"},
        {"request": {"workspace-id": "other"}},
        {"filters": [{"role": "organization_admin"}]},
        {"generation": {"membership_generation": 99}},
    ):
        with pytest.raises(CallerAuthorityRejectedError, match="authority field"):
            reject_caller_authority_fields(payload)


def test_membership_generation_is_server_owned_and_workspace_global(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    organization_id, _, principal_id = provision(store)
    first_generation = store.set_organization_membership(
        organization_id,
        principal_id,
        roles={OrganizationRole.MEMBER, OrganizationRole.APPROVER},
    )
    store.create_workspace(organization_id, "alpha")
    store.create_workspace(organization_id, "beta")
    alpha_generation = store.set_workspace_membership(
        organization_id,
        "alpha",
        principal_id,
        roles={WorkspaceRole.CONTRIBUTOR},
    )
    beta_generation = store.set_workspace_membership(
        organization_id,
        "beta",
        principal_id,
        roles={WorkspaceRole.READER, WorkspaceRole.APPROVER},
    )

    alpha = store.current_authority_state(principal_id, organization_id, "alpha")
    beta = store.current_authority_state(principal_id, organization_id, "beta")

    assert first_generation == 1
    assert alpha_generation == 2
    assert beta_generation == 3
    assert alpha.membership_generation == 3
    assert beta.membership_generation == 3
    assert alpha.organization_roles == (
        OrganizationRole.APPROVER,
        OrganizationRole.MEMBER,
    )
    assert beta.workspace_roles == (
        WorkspaceRole.APPROVER,
        WorkspaceRole.READER,
    )


def test_membership_change_invalidates_prior_generation_and_lists_only_current_org(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    organization_id, _, principal_id = provision(store)
    store.set_organization_membership(
        organization_id,
        principal_id,
        roles={OrganizationRole.MEMBER},
    )
    for workspace in ("alpha", "beta"):
        store.create_workspace(organization_id, workspace)
        store.set_workspace_membership(
            organization_id,
            workspace,
            principal_id,
            roles={WorkspaceRole.READER},
        )
    before = store.current_authority_state(principal_id, organization_id, "alpha")
    generation = store.set_workspace_membership(
        organization_id,
        "alpha",
        principal_id,
        roles={WorkspaceRole.CONTRIBUTOR},
    )
    after = store.current_authority_state(principal_id, organization_id, "alpha")
    listed = store.list_workspace_memberships(principal_id, organization_id)

    assert generation == before.membership_generation + 1
    assert after.membership_generation == generation
    assert [(item.organization_id, item.workspace_id) for item in listed] == [
        (organization_id, "alpha"),
        (organization_id, "beta"),
    ]
    assert all(item.membership_generation == generation for item in listed)


def test_human_cannot_receive_cross_organization_membership(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    _, _, principal_id = provision(store)
    other = store.create_organization()

    with pytest.raises(EnterpriseIdentityConflictError, match="does not match"):
        store.set_organization_membership(
            other.organization_id,
            principal_id,
            roles={OrganizationRole.MEMBER},
        )


def test_disable_increments_identity_generation_and_fails_closed(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    organization_id, provider_id, principal_id = provision(store)
    store.set_organization_membership(
        organization_id,
        principal_id,
        roles={OrganizationRole.MEMBER},
    )
    store.create_workspace(organization_id, "alpha")
    store.set_workspace_membership(
        organization_id,
        "alpha",
        principal_id,
        roles={WorkspaceRole.READER},
    )

    generation = store.set_principal_enabled(principal_id, enabled=False)

    assert generation == 2
    with pytest.raises(EnterpriseIdentityDisabledError, match="disabled"):
        store.resolve_identity(
            organization_id,
            provider_id,
            exact_issuer=ISSUER,
            subject="subject-Aa-001",
        )
    with pytest.raises(EnterpriseIdentityDisabledError, match="disabled"):
        store.current_authority_state(principal_id, organization_id, "alpha")


def test_node_and_service_principals_are_distinct_from_humans(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    node = store.create_nonhuman_principal(EnterprisePrincipalType.NODE)
    service = store.create_nonhuman_principal(EnterprisePrincipalType.SERVICE)

    assert node.principal_type is EnterprisePrincipalType.NODE
    assert service.principal_type is EnterprisePrincipalType.SERVICE
    with pytest.raises(EnterpriseIdentityError, match="require an exact external"):
        store.create_nonhuman_principal(EnterprisePrincipalType.HUMAN)
