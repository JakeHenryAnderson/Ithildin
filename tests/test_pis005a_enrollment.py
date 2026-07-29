from __future__ import annotations

import base64
import json
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier
from ithildin_api.database import initialize_database
from ithildin_api.enterprise_identity import EnterpriseIdentityStore
from ithildin_api.enterprise_node_identity import (
    FINGERPRINT_SCHEME,
    FixtureNodeCertificateTrust,
    NodeEnrollmentClientMaterial,
    NodeEnrollmentProof,
    NodeWorkloadAuthenticationError,
    NodeWorkloadConfigurationError,
    NodeWorkloadConflictError,
    NodeWorkloadDigestKeyRing,
    NodeWorkloadIdentityStore,
    canonical_enrollment_proof_message,
    ed25519_raw_public_key_fingerprint,
    safe_validation_error_evidence,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 29, 18, 0, tzinfo=UTC)
FIXED_PUBLIC_KEY = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
FIXED_RAW_FINGERPRINT = "sha256:630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd"


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


@dataclass(frozen=True)
class FixtureCA:
    private_key: Ed25519PrivateKey
    certificate: x509.Certificate
    trust: FixtureNodeCertificateTrust


@dataclass(frozen=True)
class EnrollmentHarness:
    db_path: Path
    clock: MutableClock
    ca: FixtureCA
    store: NodeWorkloadIdentityStore
    material: NodeEnrollmentClientMaterial


class BeginObservedNodeWorkloadIdentityStore(NodeWorkloadIdentityStore):
    def __init__(
        self,
        db_path: Path,
        *,
        digest_keys: NodeWorkloadDigestKeyRing,
        certificate_trust: FixtureNodeCertificateTrust,
        clock: Callable[[], datetime],
        begin_attempted: Event,
    ) -> None:
        super().__init__(
            db_path,
            digest_keys=digest_keys,
            certificate_trust=certificate_trust,
            clock=clock,
        )
        self._begin_attempted = begin_attempted

    def _connection(self) -> sqlite3.Connection:
        connection = super()._connection()
        connection.set_trace_callback(self._observe_statement)
        return connection

    def _observe_statement(self, statement: str) -> None:
        if statement == "BEGIN IMMEDIATE":
            self._begin_attempted.set()


def test_raw_fingerprint_vector_and_noncanonical_alias_fail_closed() -> None:
    assert FINGERPRINT_SCHEME == "ed25519_raw_sha256_v1"
    assert ed25519_raw_public_key_fingerprint(FIXED_PUBLIC_KEY) == FIXED_RAW_FINGERPRINT
    alias = FIXED_PUBLIC_KEY[:-2] + "9="
    assert base64.b64decode(alias, validate=True) == base64.b64decode(
        FIXED_PUBLIC_KEY,
        validate=True,
    )
    with pytest.raises(ValueError, match="invalid Ed25519 public key"):
        ed25519_raw_public_key_fingerprint(alias)


def test_enrollment_is_atomic_digest_only_and_secret_safe(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    proof, certificate_der = _proof(
        harness,
        certificate_key=certificate_key,
        application_key=application_key,
    )

    binding = harness.store.complete_enrollment(proof)

    assert binding.status == "active"
    assert binding.node_id == harness.material.node_id
    assert binding.principal_id == harness.material.principal_id
    assert binding.certificate_key_fingerprint != binding.application_key_fingerprint
    assert binding.identity_generation == 1
    assert binding.certificate_generation == 1
    assert binding.application_key_generation == 1
    assert binding.configuration_generation == 1
    safe_text = repr(harness.material) + repr(proof) + repr(binding.safe_evidence())
    assert harness.material.enrollment_secret not in safe_text
    assert proof.application_proof_signature not in safe_text
    assert base64.b64encode(certificate_der).decode("ascii") not in safe_text
    evidence_canary = "enrollment-secret-canary-must-not-be-safe-evidence"
    with pytest.raises(TypeError):
        binding.safe_evidence(reason_code=evidence_canary)  # type: ignore[call-arg]
    with pytest.raises(ValidationError) as validation:
        NodeEnrollmentProof.model_validate(
            {
                **proof.model_dump(),
                "enrollment_secret": evidence_canary * 16,
            }
        )
    assert evidence_canary not in str(validation.value)
    safe_validation = safe_validation_error_evidence(
        validation.value,
        timestamp=NOW,
    )
    assert safe_validation == {
        "validation_error_count": 1,
        "reason_code": "fixture_input_validation_failed",
        "timestamp": NOW.isoformat(),
    }
    assert evidence_canary not in json.dumps(safe_validation)

    with sqlite3.connect(harness.db_path) as connection:
        enrollment = connection.execute(
            """
            SELECT enrollment_digest, status
            FROM node_workload_enrollment_transactions
            """
        ).fetchone()
        principal = connection.execute(
            """
            SELECT principal_type, enabled, identity_generation
            FROM identity_principals WHERE principal_id = ?
            """,
            (binding.principal_id,),
        ).fetchone()
        organization_membership = connection.execute(
            """
            SELECT enabled, membership_generation, roles_json
            FROM identity_organization_memberships
            WHERE organization_id = ? AND principal_id = ?
            """,
            (binding.organization_id, binding.principal_id),
        ).fetchone()
        workspace_membership = connection.execute(
            """
            SELECT enabled, roles_json FROM identity_workspace_memberships
            WHERE organization_id = ? AND workspace_id = ? AND principal_id = ?
            """,
            (binding.organization_id, binding.workspace_id, binding.principal_id),
        ).fetchone()
        key_rows = connection.execute(
            """
            SELECT key_role, key_generation, status
            FROM node_workload_public_keys ORDER BY key_role
            """
        ).fetchall()
    assert enrollment is not None
    assert enrollment[0].startswith("hmac-sha256:")
    assert enrollment[1] == "consumed"
    assert principal == ("node", 1, 1)
    assert organization_membership == (1, 1, '["member","node_operator"]')
    assert workspace_membership == (1, '["node"]')
    assert key_rows == [("application", 1, "active"), ("certificate", 1, "active")]

    database_bytes = _database_artifact_bytes(harness.db_path)
    for forbidden in (
        harness.material.enrollment_secret.encode(),
        certificate_der,
        base64.b64decode(proof.certificate_proof_signature),
        base64.b64decode(proof.application_proof_signature),
    ):
        assert forbidden not in database_bytes


def test_enrollment_rejects_secret_signature_key_and_replay_failures(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    proof, _ = _proof(
        harness,
        certificate_key=certificate_key,
        application_key=application_key,
    )
    wrong_secret = proof.model_copy(update={"enrollment_secret": "x" * 43})
    with pytest.raises(NodeWorkloadAuthenticationError, match="enrollment proof is invalid"):
        harness.store.complete_enrollment(wrong_secret)

    wrong_signature = proof.model_copy(
        update={
            "application_proof_signature": _signature(
                Ed25519PrivateKey.generate(),
                b"wrong message",
            )
        }
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="Ed25519 proof is invalid"):
        harness.store.complete_enrollment(wrong_signature)

    same_key_proof, _ = _proof(
        harness,
        certificate_key=certificate_key,
        application_key=certificate_key,
        allow_message_failure=True,
    )
    with pytest.raises(
        NodeWorkloadAuthenticationError,
        match="certificate and application public keys must differ",
    ):
        harness.store.complete_enrollment(same_key_proof)

    harness.store.complete_enrollment(proof)
    with pytest.raises(NodeWorkloadConflictError, match="no longer active"):
        harness.store.complete_enrollment(proof)

    alias = _public_key(application_key)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    final_index = alphabet.index(alias[-2])
    assert final_index % 4 == 0
    noncanonical = alias[:-2] + alphabet[final_index + 1] + "="
    assert base64.b64decode(noncanonical, validate=True) == base64.b64decode(
        alias,
        validate=True,
    )
    with pytest.raises(ValidationError, match="invalid Ed25519 public key"):
        NodeEnrollmentProof(
            enrollment_transaction_id=harness.material.enrollment_transaction_id,
            enrollment_secret=harness.material.enrollment_secret,
            certificate_der=proof.certificate_der,
            application_public_key=noncanonical,
            certificate_proof_signature=proof.certificate_proof_signature,
            application_proof_signature=proof.application_proof_signature,
        )


@pytest.mark.parametrize(
    "profile",
    [
        "wrong_anchor",
        "ca_leaf",
        "server_auth",
        "bad_key_usage",
        "wrong_san",
        "duplicate_san",
        "extra_san",
        "non_uri_san",
        "extra_extension",
        "not_yet_valid",
        "expired",
        "overlong",
    ],
)
def test_certificate_profile_drift_fails_closed(tmp_path: Path, profile: str) -> None:
    harness = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    signing_ca = _fixture_ca(NOW) if profile == "wrong_anchor" else harness.ca
    not_before = NOW - timedelta(minutes=1)
    not_after = NOW + timedelta(hours=1)
    if profile == "not_yet_valid":
        not_before = NOW + timedelta(minutes=1)
        not_after = NOW + timedelta(hours=1)
    elif profile == "expired":
        not_before = NOW - timedelta(hours=2)
        not_after = NOW - timedelta(minutes=1)
    elif profile == "overlong":
        not_before = NOW - timedelta(minutes=1)
        not_after = not_before + timedelta(seconds=86_401)
    certificate_der = _leaf_certificate(
        harness.material,
        signing_ca,
        certificate_key,
        ca_leaf=profile == "ca_leaf",
        server_auth=profile == "server_auth",
        bad_key_usage=profile == "bad_key_usage",
        wrong_san=profile == "wrong_san",
        duplicate_san=profile == "duplicate_san",
        extra_san=profile == "extra_san",
        non_uri_san=profile == "non_uri_san",
        extra_extension=profile == "extra_extension",
        not_before=not_before,
        not_after=not_after,
    )
    application_public_key = _public_key(application_key)
    placeholder = _signature(certificate_key, b"placeholder")
    proof = NodeEnrollmentProof(
        enrollment_transaction_id=harness.material.enrollment_transaction_id,
        enrollment_secret=harness.material.enrollment_secret,
        certificate_der=certificate_der,
        application_public_key=application_public_key,
        certificate_proof_signature=placeholder,
        application_proof_signature=_signature(application_key, b"placeholder"),
    )
    with pytest.raises(NodeWorkloadAuthenticationError):
        harness.store.complete_enrollment(proof)


def test_inner_outer_certificate_algorithm_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    valid_der = _leaf_certificate(
        harness.material,
        harness.ca,
        certificate_key,
    )
    mismatched_der = _replace_inner_signature_algorithm_and_resign(
        valid_der,
        harness.ca.private_key,
    )
    loaded = x509.load_der_x509_certificate(mismatched_der)
    assert loaded.signature_algorithm_oid.dotted_string == "1.3.101.112"
    harness.ca.private_key.public_key().verify(
        loaded.signature,
        loaded.tbs_certificate_bytes,
    )
    placeholder = _signature(certificate_key, b"placeholder")
    proof = NodeEnrollmentProof(
        enrollment_transaction_id=harness.material.enrollment_transaction_id,
        enrollment_secret=harness.material.enrollment_secret,
        certificate_der=mismatched_der,
        application_public_key=_public_key(application_key),
        certificate_proof_signature=placeholder,
        application_proof_signature=_signature(application_key, b"placeholder"),
    )

    with pytest.raises(NodeWorkloadAuthenticationError, match="AlgorithmIdentifier"):
        harness.store.complete_enrollment(proof)


def test_fixture_ca_inner_outer_algorithm_mismatch_fails_closed() -> None:
    ca = _fixture_ca(NOW)
    valid_der = ca.certificate.public_bytes(serialization.Encoding.DER)
    mismatched_der = _replace_inner_signature_algorithm_and_resign(
        valid_der,
        ca.private_key,
    )
    loaded = x509.load_der_x509_certificate(mismatched_der)
    ca.private_key.public_key().verify(
        loaded.signature,
        loaded.tbs_certificate_bytes,
    )

    with pytest.raises(ValueError, match="algorithms are not exact"):
        FixtureNodeCertificateTrust.from_der(mismatched_der)


def test_certificate_spki_algorithm_mismatch_fails_closed(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    valid_der = _leaf_certificate(
        harness.material,
        harness.ca,
        certificate_key,
    )
    mismatched_der = _replace_spki_algorithm_and_resign(
        valid_der,
        harness.ca.private_key,
    )
    proof = NodeEnrollmentProof(
        enrollment_transaction_id=harness.material.enrollment_transaction_id,
        enrollment_secret=harness.material.enrollment_secret,
        certificate_der=mismatched_der,
        application_public_key=_public_key(application_key),
        certificate_proof_signature=_signature(certificate_key, b"placeholder"),
        application_proof_signature=_signature(application_key, b"placeholder"),
    )

    with pytest.raises(NodeWorkloadAuthenticationError, match="AlgorithmIdentifier"):
        harness.store.complete_enrollment(proof)


def test_expired_and_revoked_enrollment_transactions_fail_closed(tmp_path: Path) -> None:
    expired = _harness(tmp_path / "expired")
    expired.clock.value = NOW + timedelta(seconds=901)
    expired_proof, _ = _proof(
        expired,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="not valid"):
        expired.store.complete_enrollment(expired_proof)

    revoked = _harness(tmp_path / "revoked")
    revoked_proof, _ = _proof(
        revoked,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    with sqlite3.connect(revoked.db_path) as connection:
        connection.execute(
            """
            UPDATE node_workload_enrollment_transactions
            SET status = 'revoked', terminal_at = ?
            WHERE enrollment_transaction_id = ?
            """,
            (
                NOW.isoformat(),
                revoked.material.enrollment_transaction_id,
            ),
        )
        connection.commit()
    with pytest.raises(NodeWorkloadConflictError, match="no longer active"):
        revoked.store.complete_enrollment(revoked_proof)


def test_enrollment_expiry_is_sampled_after_database_write_lock(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    begin_attempted = Event()
    observed = _begin_observed_store(harness, begin_attempted)
    holder = sqlite3.connect(harness.db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(observed.complete_enrollment, proof)
            assert begin_attempted.wait(timeout=5)
            harness.clock.value = NOW + timedelta(seconds=901)
            holder.execute("COMMIT")
            with pytest.raises(NodeWorkloadAuthenticationError, match="not valid"):
                future.result(timeout=5)
    finally:
        if holder.in_transaction:
            holder.execute("ROLLBACK")
        holder.close()


def test_enrollment_issue_window_is_sampled_after_database_write_lock(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    begin_attempted = Event()
    observed = _begin_observed_store(harness, begin_attempted)
    holder = sqlite3.connect(harness.db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    linearized_at = NOW + timedelta(minutes=30)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                observed.issue_enrollment,
                harness.material.deployment_id,
                lifetime_seconds=60,
            )
            assert begin_attempted.wait(timeout=5)
            harness.clock.value = linearized_at
            holder.execute("COMMIT")
            material = future.result(timeout=5)
    finally:
        if holder.in_transaction:
            holder.execute("ROLLBACK")
        holder.close()
    assert material.created_at == linearized_at
    assert material.expires_at == linearized_at + timedelta(seconds=60)


def test_retired_or_missing_enrollment_digest_generation_fails_closed(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            """
            UPDATE node_workload_enrollment_digest_key_generations
            SET status = 'retired', retired_at = ?
            WHERE digest_key_generation = 1
            """,
            (NOW.isoformat(),),
        )
        connection.commit()
    with pytest.raises(NodeWorkloadAuthenticationError, match="not usable"):
        harness.store.complete_enrollment(proof)

    missing_ring = NodeWorkloadIdentityStore(
        harness.db_path,
        digest_keys=NodeWorkloadDigestKeyRing(
            {2: b"2" * 32},
            active_generation=2,
        ),
        certificate_trust=harness.ca.trust,
        clock=harness.clock,
    )
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            """
            UPDATE node_workload_enrollment_digest_key_generations
            SET status = 'retained', retired_at = NULL
            WHERE digest_key_generation = 1
            """
        )
        connection.commit()
    missing_ring.initialize_fixture_foundation()
    with pytest.raises(NodeWorkloadConfigurationError, match="unavailable"):
        missing_ring.complete_enrollment(proof)


def test_concurrent_enrollment_consumption_has_one_winner_and_no_orphans(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    second_store = _second_store(harness)
    barrier = Barrier(2)

    def consume(store: NodeWorkloadIdentityStore) -> str:
        barrier.wait()
        try:
            store.complete_enrollment(proof)
        except NodeWorkloadConflictError:
            return "replayed"
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(consume, harness.store),
            executor.submit(consume, second_store),
        )
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == ["accepted", "replayed"]
    with sqlite3.connect(harness.db_path) as connection:
        counts = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "node_workload_identities",
                "node_workload_public_keys",
                "identity_principals",
                "identity_organization_memberships",
                "identity_workspace_memberships",
            )
        }
    assert counts["node_workload_identities"] == 1
    assert counts["node_workload_public_keys"] == 2
    assert counts["identity_principals"] == 1
    assert counts["identity_organization_memberships"] == 1
    assert counts["identity_workspace_memberships"] == 1


def test_revocation_is_one_way_and_replacement_rejects_all_clone_roles(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    old_certificate_key = Ed25519PrivateKey.generate()
    old_application_key = Ed25519PrivateKey.generate()
    old_proof, _ = _proof(
        harness,
        certificate_key=old_certificate_key,
        application_key=old_application_key,
    )
    old_binding = harness.store.complete_enrollment(old_proof)
    revoked = harness.store.revoke_node(
        old_binding.node_id,
        reason_code="operator_revoked",
    )
    assert revoked.identity_generation == 2
    assert revoked.certificate_generation == 2
    assert revoked.application_key_generation == 2
    assert revoked.configuration_generation == 2
    with pytest.raises(NodeWorkloadConflictError, match="not active"):
        harness.store.revoke_node(old_binding.node_id, reason_code="operator_revoked")

    replacement = harness.store.issue_replacement_enrollment(old_binding.node_id)
    clone_matrix = (
        (old_certificate_key, Ed25519PrivateKey.generate()),
        (old_application_key, Ed25519PrivateKey.generate()),
        (Ed25519PrivateKey.generate(), old_application_key),
        (Ed25519PrivateKey.generate(), old_certificate_key),
    )
    for certificate_key, application_key in clone_matrix:
        proof, _ = _proof_for_material(
            harness,
            replacement,
            certificate_key=certificate_key,
            application_key=application_key,
        )
        with pytest.raises(NodeWorkloadConflictError, match="already registered"):
            harness.store.complete_enrollment(proof)

    replacement_proof, _ = _proof_for_material(
        harness,
        replacement,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    new_binding = harness.store.complete_enrollment(replacement_proof)
    assert new_binding.node_id != old_binding.node_id
    assert new_binding.replaces_node_id == old_binding.node_id
    with sqlite3.connect(harness.db_path) as connection:
        old_state = connection.execute(
            """
            SELECT status, revocation_reason_code, replacement_node_id
            FROM node_workload_identities WHERE node_id = ?
            """,
            (old_binding.node_id,),
        ).fetchone()
        old_keys = connection.execute(
            """
            SELECT count(*) FROM node_workload_public_keys
            WHERE node_id = ? AND status = 'retired'
            """,
            (old_binding.node_id,),
        ).fetchone()
    assert old_state == ("replaced", "replacement_completed", new_binding.node_id)
    assert old_keys == (2,)


def test_expired_replacement_enrollment_is_terminalized_and_retryable(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    old_proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    old_binding = harness.store.complete_enrollment(old_proof)
    harness.store.revoke_node(old_binding.node_id, reason_code="operator_revoked")
    expired = harness.store.issue_replacement_enrollment(
        old_binding.node_id,
        lifetime_seconds=1,
    )
    with pytest.raises(NodeWorkloadConflictError, match="already active"):
        harness.store.issue_replacement_enrollment(old_binding.node_id)

    harness.clock.value = NOW + timedelta(seconds=2)
    replacement = harness.store.issue_replacement_enrollment(old_binding.node_id)

    with sqlite3.connect(harness.db_path) as connection:
        rows = connection.execute(
            """
            SELECT enrollment_transaction_id, status, terminal_at
            FROM node_workload_enrollment_transactions
            WHERE replaces_node_id = ?
            ORDER BY created_at, enrollment_transaction_id
            """,
            (old_binding.node_id,),
        ).fetchall()
    by_id = {row[0]: (row[1], row[2]) for row in rows}
    assert by_id[expired.enrollment_transaction_id][0] == "expired"
    assert by_id[expired.enrollment_transaction_id][1] is not None
    assert by_id[replacement.enrollment_transaction_id] == ("pending", None)


def test_concurrent_replacement_issue_after_expiry_has_one_winner(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    old_proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    old_binding = harness.store.complete_enrollment(old_proof)
    harness.store.revoke_node(old_binding.node_id, reason_code="operator_revoked")
    harness.store.issue_replacement_enrollment(old_binding.node_id, lifetime_seconds=1)
    harness.clock.value = NOW + timedelta(seconds=2)
    stores = (harness.store, _second_store(harness))
    barrier = Barrier(2)

    def issue(store: NodeWorkloadIdentityStore) -> str:
        barrier.wait()
        try:
            store.issue_replacement_enrollment(old_binding.node_id)
        except NodeWorkloadConflictError:
            return "conflict"
        return "issued"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(
            future.result()
            for future in (
                executor.submit(issue, stores[0]),
                executor.submit(issue, stores[1]),
            )
        )
    assert outcomes == ["conflict", "issued"]
    with sqlite3.connect(harness.db_path) as connection:
        statuses = connection.execute(
            """
            SELECT status, count(*)
            FROM node_workload_enrollment_transactions
            WHERE replaces_node_id = ?
            GROUP BY status
            """,
            (old_binding.node_id,),
        ).fetchall()
    assert dict(statuses) == {"expired": 1, "pending": 1}


def test_concurrent_revocation_increments_generations_exactly_once(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    binding = harness.store.complete_enrollment(proof)
    stores = (harness.store, _second_store(harness))
    barrier = Barrier(2)

    def revoke(store: NodeWorkloadIdentityStore) -> str:
        barrier.wait()
        try:
            store.revoke_node(binding.node_id, reason_code="operator_revoked")
        except NodeWorkloadConflictError:
            return "conflict"
        return "revoked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(revoke, store) for store in stores)
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == ["conflict", "revoked"]
    with sqlite3.connect(harness.db_path) as connection:
        identity = connection.execute(
            """
            SELECT status, identity_generation, certificate_generation,
                   application_key_generation, configuration_generation
            FROM node_workload_identities WHERE node_id = ?
            """,
            (binding.node_id,),
        ).fetchone()
        principal = connection.execute(
            """
            SELECT enabled, identity_generation FROM identity_principals
            WHERE principal_id = ?
            """,
            (binding.principal_id,),
        ).fetchone()
        membership = connection.execute(
            """
            SELECT enabled, membership_generation
            FROM identity_organization_memberships WHERE principal_id = ?
            """,
            (binding.principal_id,),
        ).fetchone()
    assert identity == ("revoked", 2, 2, 2, 2)
    assert principal == (0, 2)
    assert membership == (0, 2)


def test_revocation_timestamp_is_sampled_after_database_write_lock(
    tmp_path: Path,
) -> None:
    harness = _harness(tmp_path)
    proof, _ = _proof(
        harness,
        certificate_key=Ed25519PrivateKey.generate(),
        application_key=Ed25519PrivateKey.generate(),
    )
    binding = harness.store.complete_enrollment(proof)
    begin_attempted = Event()
    observed = _begin_observed_store(harness, begin_attempted)
    holder = sqlite3.connect(harness.db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    linearized_at = NOW + timedelta(minutes=30)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                observed.revoke_node,
                binding.node_id,
                reason_code="operator_revoked",
            )
            assert begin_attempted.wait(timeout=5)
            harness.clock.value = linearized_at
            holder.execute("COMMIT")
            snapshot = future.result(timeout=5)
    finally:
        if holder.in_transaction:
            holder.execute("ROLLBACK")
        holder.close()
    assert snapshot.timestamp == linearized_at
    with sqlite3.connect(harness.db_path) as connection:
        revoked_at = connection.execute(
            """
            SELECT revoked_at FROM node_workload_identities WHERE node_id = ?
            """,
            (binding.node_id,),
        ).fetchone()
    assert revoked_at == (linearized_at.isoformat(),)


def _harness(tmp_path: Path) -> EnrollmentHarness:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    clock = MutableClock(NOW)
    identity = EnterpriseIdentityStore(db_path, clock=clock)
    organization = identity.create_organization()
    identity.create_workspace(organization.organization_id, "fixture-workspace")
    ca = _fixture_ca(NOW)
    store = NodeWorkloadIdentityStore(
        db_path,
        digest_keys=NodeWorkloadDigestKeyRing({1: b"d" * 32}, active_generation=1),
        certificate_trust=ca.trust,
        clock=clock,
    )
    store.initialize_fixture_foundation()
    deployment = store.create_deployment(
        organization_id=organization.organization_id,
        workspace_id="fixture-workspace",
    )
    material = store.issue_enrollment(deployment.deployment_id)
    return EnrollmentHarness(
        db_path=db_path,
        clock=clock,
        ca=ca,
        store=store,
        material=material,
    )


def _second_store(harness: EnrollmentHarness) -> NodeWorkloadIdentityStore:
    return NodeWorkloadIdentityStore(
        harness.db_path,
        digest_keys=NodeWorkloadDigestKeyRing({1: b"d" * 32}, active_generation=1),
        certificate_trust=harness.ca.trust,
        clock=harness.clock,
    )


def _begin_observed_store(
    harness: EnrollmentHarness,
    begin_attempted: Event,
) -> BeginObservedNodeWorkloadIdentityStore:
    return BeginObservedNodeWorkloadIdentityStore(
        harness.db_path,
        digest_keys=NodeWorkloadDigestKeyRing({1: b"d" * 32}, active_generation=1),
        certificate_trust=harness.ca.trust,
        clock=harness.clock,
        begin_attempted=begin_attempted,
    )


def _fixture_ca(now: datetime) -> FixtureCA:
    private_key = Ed25519PrivateKey.generate()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Ithildin fixture Node CA")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, algorithm=None)
    )
    der = certificate.public_bytes(serialization.Encoding.DER)
    return FixtureCA(
        private_key=private_key,
        certificate=certificate,
        trust=FixtureNodeCertificateTrust.from_der(der),
    )


def _leaf_certificate(
    material: NodeEnrollmentClientMaterial,
    ca: FixtureCA,
    private_key: Ed25519PrivateKey,
    *,
    ca_leaf: bool = False,
    server_auth: bool = False,
    bad_key_usage: bool = False,
    wrong_san: bool = False,
    duplicate_san: bool = False,
    extra_san: bool = False,
    non_uri_san: bool = False,
    extra_extension: bool = False,
    not_before: datetime | None = None,
    not_after: datetime | None = None,
) -> bytes:
    uris = list(material.expected_san_uris)
    if wrong_san:
        uris[-1] = uris[-1] + "-wrong"
    if duplicate_san:
        uris[-1] = uris[0]
    names: list[x509.GeneralName] = [x509.UniformResourceIdentifier(uri) for uri in uris]
    if extra_san:
        names.append(x509.UniformResourceIdentifier("urn:ithildin:unknown:value"))
    if non_uri_san:
        names[-1] = x509.DNSName("fixture.invalid")
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([]))
        .issuer_name(ca.certificate.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before or NOW - timedelta(minutes=1))
        .not_valid_after(not_after or NOW + timedelta(hours=1))
        .add_extension(
            x509.BasicConstraints(ca=ca_leaf, path_length=0 if ca_leaf else None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=not bad_key_usage,
                content_commitment=False,
                key_encipherment=bad_key_usage,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH
                    if server_auth
                    else ExtendedKeyUsageOID.CLIENT_AUTH
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(names),
            critical=True,
        )
    )
    if extra_extension:
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                ObjectIdentifier("1.3.6.1.4.1.57264.99.1"),
                b"unexpected",
            ),
            critical=False,
        )
    certificate = builder.sign(ca.private_key, algorithm=None)
    return certificate.public_bytes(serialization.Encoding.DER)


def _proof(
    harness: EnrollmentHarness,
    *,
    certificate_key: Ed25519PrivateKey,
    application_key: Ed25519PrivateKey,
    allow_message_failure: bool = False,
) -> tuple[NodeEnrollmentProof, bytes]:
    return _proof_for_material(
        harness,
        harness.material,
        certificate_key=certificate_key,
        application_key=application_key,
        allow_message_failure=allow_message_failure,
    )


def _proof_for_material(
    harness: EnrollmentHarness,
    material: NodeEnrollmentClientMaterial,
    *,
    certificate_key: Ed25519PrivateKey,
    application_key: Ed25519PrivateKey,
    allow_message_failure: bool = False,
) -> tuple[NodeEnrollmentProof, bytes]:
    certificate_der = _leaf_certificate(material, harness.ca, certificate_key)
    application_public_key = _public_key(application_key)
    try:
        message = canonical_enrollment_proof_message(
            material=material,
            certificate_der=certificate_der,
            application_public_key=application_public_key,
            certificate_trust=harness.ca.trust,
            at=harness.clock(),
        )
    except NodeWorkloadAuthenticationError:
        if not allow_message_failure:
            raise
        message = b"same-key proof is rejected before signature verification"
    return (
        NodeEnrollmentProof(
            enrollment_transaction_id=material.enrollment_transaction_id,
            enrollment_secret=material.enrollment_secret,
            certificate_der=certificate_der,
            application_public_key=application_public_key,
            certificate_proof_signature=_signature(certificate_key, message),
            application_proof_signature=_signature(application_key, message),
        ),
        certificate_der,
    )


def _public_key(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def _signature(private_key: Ed25519PrivateKey, message: bytes) -> str:
    return base64.b64encode(private_key.sign(message)).decode("ascii")


def _database_artifact_bytes(db_path: Path) -> bytes:
    return b"".join(
        path.read_bytes()
        for path in (
            db_path,
            db_path.with_name(db_path.name + "-journal"),
            db_path.with_name(db_path.name + "-wal"),
            db_path.with_name(db_path.name + "-shm"),
        )
        if path.is_file()
    )


def _replace_inner_signature_algorithm_and_resign(
    certificate_der: bytes,
    signing_key: Ed25519PrivateKey,
) -> bytes:
    return _replace_algorithm_occurrence_and_resign(
        certificate_der,
        signing_key,
        occurrence=0,
    )


def _replace_spki_algorithm_and_resign(
    certificate_der: bytes,
    signing_key: Ed25519PrivateKey,
) -> bytes:
    return _replace_algorithm_occurrence_and_resign(
        certificate_der,
        signing_key,
        occurrence=1,
    )


def _replace_algorithm_occurrence_and_resign(
    certificate_der: bytes,
    signing_key: Ed25519PrivateKey,
    *,
    occurrence: int,
) -> bytes:
    ed25519_algorithm = b"\x30\x05\x06\x03\x2b\x65\x70"
    outer_tag, outer_content, outer_end = _test_der_tlv_bounds(certificate_der, 0)
    assert outer_tag == 0x30
    assert outer_end == len(certificate_der)
    tbs_tag, _, tbs_end = _test_der_tlv_bounds(certificate_der, outer_content)
    assert tbs_tag == 0x30
    algorithm_offset = outer_content
    for _ in range(occurrence + 1):
        algorithm_offset = certificate_der.find(
            ed25519_algorithm,
            algorithm_offset,
            tbs_end,
        )
        assert algorithm_offset >= 0
        if _ < occurrence:
            algorithm_offset += len(ed25519_algorithm)
    mutated = bytearray(certificate_der)
    mutated[algorithm_offset + len(ed25519_algorithm) - 1] = 0x71
    _, _, outer_algorithm_end = _test_der_tlv_bounds(mutated, tbs_end)
    signature_tag, signature_content, signature_end = _test_der_tlv_bounds(
        mutated,
        outer_algorithm_end,
    )
    assert signature_tag == 0x03
    assert signature_end == outer_end
    assert mutated[signature_content] == 0
    signature = signing_key.sign(bytes(mutated[outer_content:tbs_end]))
    assert len(signature) == signature_end - signature_content - 1
    mutated[signature_content + 1 : signature_end] = signature
    return bytes(mutated)


def _test_der_tlv_bounds(data: bytes | bytearray, offset: int) -> tuple[int, int, int]:
    tag = data[offset]
    length_octet = data[offset + 1]
    cursor = offset + 2
    if length_octet < 0x80:
        length = length_octet
    else:
        length_octets = length_octet & 0x7F
        length = int.from_bytes(data[cursor : cursor + length_octets], "big")
        cursor += length_octets
    return tag, cursor, cursor + length
