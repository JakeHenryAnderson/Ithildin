from __future__ import annotations

import base64
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from threading import Barrier, Event

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.enterprise_node_identity import (
    NodeRequestVerificationSnapshot,
    NodeWorkloadAuthenticationError,
    NodeWorkloadBinding,
    NodeWorkloadDigestKeyRing,
    NodeWorkloadIdentityStore,
    NodeWorkloadRequestEnvelope,
    canonical_node_workload_request_message,
    request_body_digest,
    safe_validation_error_evidence,
)
from pydantic import ValidationError
from test_pis005a_enrollment import (
    NOW,
    EnrollmentHarness,
    _begin_observed_store,
    _database_artifact_bytes,
    _fixture_ca,
    _harness,
    _leaf_certificate,
    _proof,
    _second_store,
    _signature,
)


@dataclass(frozen=True)
class BoundHarness:
    enrollment: EnrollmentHarness
    binding: NodeWorkloadBinding
    certificate_der: bytes
    application_key: Ed25519PrivateKey


def test_request_verification_is_snapshot_only_durable_and_secret_safe(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="1" * 32, body=b"request-body-canary")

    snapshot = harness.enrollment.store.verify_request(envelope)

    assert isinstance(snapshot, NodeRequestVerificationSnapshot)
    assert snapshot.effect_authority is False
    assert snapshot.live_transport_verified is False
    assert snapshot.nonce_outcome == "consumed"
    assert snapshot.reason_code == "fixture_request_valid"
    assert snapshot.request_digest == request_body_digest(envelope.request_body)
    safe_text = repr(envelope) + repr(snapshot.safe_evidence())
    assert "request-body-canary" not in safe_text
    assert envelope.application_signature not in safe_text
    assert envelope.nonce not in safe_text
    with pytest.raises(NodeWorkloadAuthenticationError, match="already consumed"):
        _second_store(harness.enrollment).verify_request(envelope)

    database_bytes = _database_artifact_bytes(harness.enrollment.db_path)
    assert envelope.request_body not in database_bytes
    assert harness.certificate_der not in database_bytes
    assert base64.b64decode(envelope.application_signature) not in database_bytes
    with sqlite3.connect(harness.enrollment.db_path) as connection:
        nonce_row = connection.execute(
            """
            SELECT nonce_digest, request_digest, deployment_generation,
                   identity_generation, certificate_generation,
                   application_key_generation, configuration_generation
            FROM node_workload_request_nonces
            """
        ).fetchone()
    assert nonce_row is not None
    assert nonce_row[0].startswith("sha256:")
    assert nonce_row[1] == snapshot.request_digest
    assert nonce_row[2:] == (1, 1, 1, 1, 1)


@pytest.mark.parametrize(
    "generation_field",
    [
        "deployment_generation",
        "identity_generation",
        "certificate_generation",
        "application_key_generation",
        "configuration_generation",
    ],
)
def test_request_rejects_each_stale_generation(
    tmp_path: Path,
    generation_field: str,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="2" * 32)
    stale = envelope.model_copy(update={generation_field: getattr(envelope, generation_field) + 1})
    with pytest.raises(NodeWorkloadAuthenticationError, match="generation is stale"):
        harness.enrollment.store.verify_request(stale)


def test_request_rejects_digest_signature_timestamp_certificate_and_scope_drift(
    tmp_path: Path,
) -> None:
    digest_harness = _bound_harness(tmp_path / "digest")
    envelope = _request(digest_harness, nonce="3" * 32)
    bad_digest = envelope.model_copy(update={"declared_request_digest": "sha256:" + ("0" * 64)})
    with pytest.raises(NodeWorkloadAuthenticationError, match="body digest mismatch"):
        digest_harness.enrollment.store.verify_request(bad_digest)

    signature_harness = _bound_harness(tmp_path / "signature")
    envelope = _request(signature_harness, nonce="4" * 32)
    bad_signature = envelope.model_copy(
        update={
            "application_signature": _signature(
                Ed25519PrivateKey.generate(),
                b"wrong request",
            )
        }
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="Ed25519 proof is invalid"):
        signature_harness.enrollment.store.verify_request(bad_signature)

    timestamp_harness = _bound_harness(tmp_path / "timestamp")
    envelope = _request(
        timestamp_harness,
        nonce="5" * 32,
        request_timestamp=int(NOW.timestamp()) - 301,
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="outside the fixture window"):
        timestamp_harness.enrollment.store.verify_request(envelope)

    certificate_harness = _bound_harness(tmp_path / "certificate")
    wrong_certificate = _leaf_certificate(
        certificate_harness.enrollment.material,
        certificate_harness.enrollment.ca,
        Ed25519PrivateKey.generate(),
    )
    envelope = _request(certificate_harness, nonce="6" * 32).model_copy(
        update={"certificate_der": wrong_certificate}
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="certificate binding is stale"):
        certificate_harness.enrollment.store.verify_request(envelope)

    scope_harness = _bound_harness(tmp_path / "scope")
    with sqlite3.connect(scope_harness.enrollment.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_workspace_memberships
            SET roles_json = '["reader"]'
            WHERE principal_id = ?
            """,
            (scope_harness.binding.principal_id,),
        )
        connection.commit()
    with pytest.raises(
        NodeWorkloadAuthenticationError,
        match="principal or membership authority is invalid",
    ):
        scope_harness.enrollment.store.verify_request(_request(scope_harness, nonce="7" * 32))


def test_request_rejects_unavailable_restart_trust_anchor(tmp_path: Path) -> None:
    harness = _bound_harness(tmp_path)
    other_ca = _fixture_ca(NOW)
    wrong_trust_store = NodeWorkloadIdentityStore(
        harness.enrollment.db_path,
        digest_keys=NodeWorkloadDigestKeyRing({1: b"d" * 32}, active_generation=1),
        certificate_trust=other_ca.trust,
        clock=harness.enrollment.clock,
    )
    with pytest.raises(NodeWorkloadAuthenticationError, match="trust anchor is unavailable"):
        wrong_trust_store.verify_request(_request(harness, nonce="8" * 32))


def test_request_models_reject_noncanonical_fields_and_extra_authority(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="9" * 32)
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        NodeWorkloadRequestEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "role": "node_operator",
            }
        )
    with pytest.raises(ValidationError, match="canonical uppercase ASCII"):
        NodeWorkloadRequestEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "method": "post",
            }
        )
    with pytest.raises(ValidationError):
        NodeWorkloadRequestEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "nonce": "not-a-canonical-nonce",
            }
        )
    validation_canary = "request-body-or-signature-canary-must-not-appear"
    with pytest.raises(ValidationError) as validation:
        NodeWorkloadRequestEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "application_signature": validation_canary,
            }
        )
    assert validation_canary not in str(validation.value)
    safe_validation = safe_validation_error_evidence(
        validation.value,
        timestamp=NOW,
    )
    assert safe_validation["validation_error_count"] == 1
    assert validation_canary not in repr(safe_validation)


def test_request_timestamp_is_sampled_after_database_write_lock(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="d" * 32)
    begin_attempted = Event()
    observed = _begin_observed_store(harness.enrollment, begin_attempted)
    holder = sqlite3.connect(harness.enrollment.db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(observed.verify_request, envelope)
            assert begin_attempted.wait(timeout=5)
            harness.enrollment.clock.value = NOW + timedelta(seconds=301)
            holder.execute("COMMIT")
            with pytest.raises(
                NodeWorkloadAuthenticationError,
                match="outside the fixture window",
            ):
                future.result(timeout=5)
    finally:
        if holder.in_transaction:
            holder.execute("ROLLBACK")
        holder.close()


def test_request_certificate_expiry_is_sampled_after_database_write_lock(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    after_certificate_expiry = NOW + timedelta(hours=2)
    envelope = _request(
        harness,
        nonce="e" * 32,
        request_timestamp=int(after_certificate_expiry.timestamp()),
    )
    begin_attempted = Event()
    observed = _begin_observed_store(harness.enrollment, begin_attempted)
    holder = sqlite3.connect(harness.enrollment.db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(observed.verify_request, envelope)
            assert begin_attempted.wait(timeout=5)
            harness.enrollment.clock.value = after_certificate_expiry
            holder.execute("COMMIT")
            with pytest.raises(
                NodeWorkloadAuthenticationError,
                match="certificate validity is invalid",
            ):
                future.result(timeout=5)
    finally:
        if holder.in_transaction:
            holder.execute("ROLLBACK")
        holder.close()


def test_concurrent_request_replay_has_one_winner_and_survives_restart(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="a" * 32)
    stores = (harness.enrollment.store, _second_store(harness.enrollment))
    barrier = Barrier(2)

    def verify(store: NodeWorkloadIdentityStore) -> str:
        barrier.wait()
        try:
            store.verify_request(envelope)
        except NodeWorkloadAuthenticationError as exc:
            assert "already consumed" in str(exc)
            return "replayed"
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(verify, store) for store in stores)
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == ["accepted", "replayed"]
    with sqlite3.connect(harness.enrollment.db_path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM node_workload_request_nonces"
        ).fetchone() == (1,)
    with pytest.raises(NodeWorkloadAuthenticationError, match="already consumed"):
        _second_store(harness.enrollment).verify_request(envelope)


def test_request_revocation_race_linearizes_without_effect_authority(
    tmp_path: Path,
) -> None:
    harness = _bound_harness(tmp_path)
    envelope = _request(harness, nonce="b" * 32)
    verifier = _second_store(harness.enrollment)
    revoker = _second_store(harness.enrollment)
    barrier = Barrier(2)

    def verify() -> str:
        barrier.wait()
        try:
            snapshot = verifier.verify_request(envelope)
        except NodeWorkloadAuthenticationError:
            return "denied"
        assert snapshot.effect_authority is False
        return "snapshot_only"

    def revoke() -> str:
        barrier.wait()
        revoker.revoke_node(harness.binding.node_id, reason_code="operator_revoked")
        return "revoked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        verify_future = executor.submit(verify)
        revoke_future = executor.submit(revoke)
        outcomes = {verify_future.result(), revoke_future.result()}
    assert "revoked" in outcomes
    assert outcomes & {"denied", "snapshot_only"}
    with pytest.raises(NodeWorkloadAuthenticationError, match="not active"):
        verifier.verify_request(_request(harness, nonce="c" * 32))
    with sqlite3.connect(harness.enrollment.db_path) as connection:
        final = connection.execute(
            """
            SELECT i.status, p.enabled, om.enabled, wm.enabled
            FROM node_workload_identities AS i
            JOIN identity_principals AS p ON p.principal_id = i.principal_id
            JOIN identity_organization_memberships AS om
              ON om.principal_id = i.principal_id
            JOIN identity_workspace_memberships AS wm
              ON wm.principal_id = i.principal_id
            WHERE i.node_id = ?
            """,
            (harness.binding.node_id,),
        ).fetchone()
    assert final == ("revoked", 0, 0, 0)


def _bound_harness(tmp_path: Path) -> BoundHarness:
    enrollment = _harness(tmp_path)
    certificate_key = Ed25519PrivateKey.generate()
    application_key = Ed25519PrivateKey.generate()
    proof, certificate_der = _proof(
        enrollment,
        certificate_key=certificate_key,
        application_key=application_key,
    )
    binding = enrollment.store.complete_enrollment(proof)
    return BoundHarness(
        enrollment=enrollment,
        binding=binding,
        certificate_der=certificate_der,
        application_key=application_key,
    )


def _request(
    harness: BoundHarness,
    *,
    nonce: str,
    body: bytes = b'{"fixture":"request"}',
    request_timestamp: int | None = None,
) -> NodeWorkloadRequestEnvelope:
    timestamp = request_timestamp or int(harness.enrollment.clock().timestamp())
    digest = request_body_digest(body)
    message = canonical_node_workload_request_message(
        binding=harness.binding,
        method="POST",
        path="/fixture/node/report",
        request_timestamp=timestamp,
        nonce=nonce,
        request_digest=digest,
    )
    return NodeWorkloadRequestEnvelope(
        node_id=harness.binding.node_id,
        certificate_der=harness.certificate_der,
        method="POST",
        path="/fixture/node/report",
        request_timestamp=timestamp,
        nonce=nonce,
        declared_request_digest=digest,
        request_body=body,
        deployment_generation=harness.binding.deployment_generation,
        identity_generation=harness.binding.identity_generation,
        certificate_generation=harness.binding.certificate_generation,
        application_key_generation=harness.binding.application_key_generation,
        configuration_generation=harness.binding.configuration_generation,
        application_signature=_signature(harness.application_key, message),
    )
