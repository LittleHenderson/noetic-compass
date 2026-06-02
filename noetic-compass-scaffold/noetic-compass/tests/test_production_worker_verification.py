"""Tests for the design-stage worker-verification stub (workstream 01).

Import-isolated: imports ONLY from ``api.services.production.worker_verification``. Exercises
the honesty-critical behaviors from the blueprint —

* the stub NEVER returns ``WORKER_EVIDENCE_VERIFIED`` (a stub is a stub);
* ``promote_chip`` returns ``"verified"`` ONLY when a fully-attested receipt clears every §4
  blocker, and each missing input (is_real_model, determinism, probe-hash, weights identity,
  signature) INDEPENDENTLY keeps the chip at ``"present"``;
* ``reverify`` re-hashes the evidence and catches a tampered payload;
* only the four strict chips are ever promotable; model_proof/packet_proof stay ``"present"``;
* the content hash uses the canonical-JSON discipline (stable, order-independent).

None of this touches the live app, the fleet executor, or the worker script.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from api.services.production.worker_verification import (
    InMemoryWorkerVerifier,
    ReproducibilityManifest,
    WeightsAttestation,
    WorkerAttestation,
    WorkerEvidenceReceipt,
    WorkerVerificationError,
    WorkerVerifier,
    build_worker_fragment_ref,
    content_sha256_over_evidence,
)


def _verifier() -> InMemoryWorkerVerifier:
    return InMemoryWorkerVerifier()


def _fully_attested_receipt(**overrides) -> WorkerEvidenceReceipt:
    """A receipt that, by default, clears every promotion blocker.

    Individual tests override one field to prove that single gap blocks promotion. This is the
    only honest path to a "verified" chip — and it requires the real-worker work (determinism,
    hashes, signature, is_real_model) the stub itself cannot perform.
    """
    base = dict(
        status="WORKER_EVIDENCE_VERIFIED",
        content_sha256="a" * 64,
        is_real_model=True,
        reproducibility=ReproducibilityManifest(
            seed=7,
            torch_dtype="bfloat16",
            deterministic_algorithms=True,
            torch_version="2.4.0",
            transformers_version="4.44.0",
            accelerator="NVIDIA A100-80GB",
            cuda_version="12.4",
            worker_commit_sha="deadbeefcafe",
        ),
        weights=WeightsAttestation(
            model_id="EleutherAI/pythia-160m",
            resolved_revision_commit="1234abcd",
            model_weights_sha256="b" * 64,
            probe_weights_sha256="c" * 64,
            probe_weights_hash_verified=True,
        ),
        worker=WorkerAttestation(
            worker_id="worker-1",
            instance_id="i-abc",
            image_digest="sha256:img",
            hardware_attestation="nitro-token",
        ),
        fragment_ref="cas-fragment://a/j/w/s/sha256:" + "a" * 64,
        signature="sig-over-canonical-receipt",
    )
    base.update(overrides)
    return WorkerEvidenceReceipt(**base)


# --- Protocol conformance ----------------------------------------------------


def test_stub_satisfies_worker_verifier_protocol():
    assert isinstance(_verifier(), WorkerVerifier)


# --- The stub fabricates nothing ---------------------------------------------


def test_stub_attest_never_returns_verified_even_for_real_model():
    evidence = {
        "is_real_model": True,
        "model_id": "EleutherAI/pythia-160m",
        "audit_id": "audit-1",
        "job_id": "job-1",
        "worker_id": "worker-1",
        "shard_id": "shard-1",
        "activation_summary": [{"scenario_id": "s1", "layers": []}],
    }
    receipt = _verifier().attest(evidence)

    # A stub did not pin determinism / load weights / sign -> it must NOT claim VERIFIED.
    assert receipt.status == "WORKER_EVIDENCE_DECLARED"
    assert receipt.is_verified is False
    assert receipt.signature is None
    assert receipt.reproducibility.is_pinned is False
    assert receipt.weights.probe_weights_hash_verified is False
    assert receipt.reasons  # it says WHY it cannot verify


def test_stub_attest_records_real_model_flag_and_fragment_ref():
    evidence = {
        "is_real_model": True,
        "audit_id": "audit-9",
        "job_id": "job-9",
        "worker_id": "worker-9",
        "shard_id": "shard-9",
    }
    receipt = _verifier().attest(evidence)
    assert receipt.is_real_model is True
    assert receipt.content_sha256 == content_sha256_over_evidence(evidence)
    assert receipt.fragment_ref == build_worker_fragment_ref(
        audit_id="audit-9", job_id="job-9", worker_id="worker-9", shard_id="shard-9",
        digest=receipt.content_sha256,
    )


def test_stub_attest_demo_model_is_not_real():
    receipt = _verifier().attest({"is_real_model": False})
    assert receipt.is_real_model is False
    assert receipt.is_verified is False


def test_attest_rejects_non_mapping():
    with pytest.raises(WorkerVerificationError):
        _verifier().attest("not a mapping")  # type: ignore[arg-type]


# --- promote_chip: the only path to "verified", fully gated -------------------


def test_promote_chip_verified_only_when_fully_attested():
    verifier = _verifier()
    receipt = _fully_attested_receipt()
    for chip in ("cas_readout", "causal_proof", "control_proof", "output_proof"):
        assert verifier.promote_chip(chip, receipt) == "verified"


def test_non_strict_chips_never_promote():
    verifier = _verifier()
    receipt = _fully_attested_receipt()
    # model_proof and packet_proof may pass at "present"; they are never raised to "verified".
    assert verifier.promote_chip("model_proof", receipt) == "present"
    assert verifier.promote_chip("packet_proof", receipt) == "present"
    assert verifier.promote_chip("unknown_chip", receipt) == "present"


def test_missing_is_real_model_blocks_promotion():
    verifier = _verifier()
    receipt = _fully_attested_receipt(is_real_model=False)
    assert verifier.promote_chip("cas_readout", receipt) == "present"


def test_unpinned_determinism_blocks_promotion():
    verifier = _verifier()
    # dtype "auto" is not verifiable; is_pinned must be False.
    receipt = _fully_attested_receipt(
        reproducibility=ReproducibilityManifest(
            seed=7, torch_dtype="auto", deterministic_algorithms=True
        )
    )
    assert receipt.reproducibility.is_pinned is False
    assert verifier.promote_chip("causal_proof", receipt) == "present"


def test_unverified_probe_hash_blocks_promotion():
    verifier = _verifier()
    receipt = _fully_attested_receipt(
        weights=WeightsAttestation(
            model_id="m",
            resolved_revision_commit="1234abcd",
            model_weights_sha256="b" * 64,
            probe_weights_sha256="c" * 64,
            probe_weights_hash_verified=False,  # the API-tier default; worker must flip it
        )
    )
    assert verifier.promote_chip("control_proof", receipt) == "present"


def test_missing_weights_identity_blocks_promotion():
    verifier = _verifier()
    receipt = _fully_attested_receipt(
        weights=WeightsAttestation(
            model_id="m",
            resolved_revision_commit=None,
            model_weights_sha256=None,  # neither commit nor digest -> no identity
            probe_weights_sha256="c" * 64,
            probe_weights_hash_verified=True,
        )
    )
    assert receipt.weights.has_weights_identity is False
    assert verifier.promote_chip("output_proof", receipt) == "present"


def test_unsigned_manifest_blocks_promotion():
    verifier = _verifier()
    receipt = _fully_attested_receipt(signature=None)
    assert verifier.promote_chip("cas_readout", receipt) == "present"


def test_missing_content_hash_blocks_promotion():
    verifier = _verifier()
    receipt = _fully_attested_receipt(content_sha256="")
    assert verifier.promote_chip("cas_readout", receipt) == "present"


# --- reverify: tamper-evidence over the evidence bytes ------------------------


def test_reverify_matches_untampered_evidence():
    verifier = _verifier()
    evidence = {"is_real_model": True, "activation_summary": [{"scenario_id": "s1"}]}
    receipt = verifier.attest(evidence)
    assert verifier.reverify(receipt, evidence) is True


def test_reverify_detects_tampered_evidence():
    verifier = _verifier()
    evidence = {"is_real_model": True, "activation_summary": [{"scenario_id": "s1"}]}
    receipt = verifier.attest(evidence)

    tampered = dict(evidence)
    tampered["activation_summary"] = [{"scenario_id": "s1-EDITED"}]
    assert verifier.reverify(receipt, tampered) is False


# --- content hash discipline -------------------------------------------------


def test_content_hash_is_canonical_and_order_independent():
    a = {"x": 1, "y": 2, "is_real_model": True}
    b = {"y": 2, "is_real_model": True, "x": 1}  # same content, different key order
    assert content_sha256_over_evidence(a) == content_sha256_over_evidence(b)

    expected = hashlib.sha256(
        json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    assert content_sha256_over_evidence(a) == expected


def test_receipt_to_dict_is_self_describing():
    receipt = _fully_attested_receipt()
    payload = receipt.to_dict()
    assert payload["status"] == "WORKER_EVIDENCE_VERIFIED"
    assert payload["schema_version"] == "cas_harness_worker_evidence_receipt.v1"
    assert payload["reproducibility"]["is_pinned"] is True
    assert payload["weights"]["probe_weights_hash_verified"] is True
    assert payload["weights"]["has_weights_identity"] is True
    assert payload["worker"]["worker_id"] == "worker-1"
