"""Synthetic full handoff tests, not evidence of a learned or reusable skill."""
from copy import deepcopy

import pytest

from cas_meta3 import learned_handoff as handoff
from cas_meta3 import learned_package as packages
from cas_meta3 import learning_evidence as evidence
from test_learned_package import fixture as package_fixture, arguments
from test_learning_evidence import Fixture


def fixture():
    stored = Fixture()
    stored.source = packages.META2_SOURCE_SHA
    for item in (stored.manifest, stored.inspection, stored.audit):
        item["source_sha"] = stored.source
    inputs = stored.inputs()
    proof = evidence.bind_learning_evidence(**inputs)
    candidate = package_fixture()
    candidate["program"] = deepcopy(stored.action["program"])
    candidate["binding"] = stored.action["binding"]
    candidate["io"]["input"]["slot"] = candidate["binding"]
    candidate["io"]["output"]["producer_cjt_id"] = "C"
    for field in ("source_program_sha256", "policy_source_sha256",
                  "policy_checkpoint_sha256", "producer_source_sha"):
        candidate["provenance"][field] = proof[field]
    candidate["provenance"]["producer_evidence_sha256"] = proof["receipt_sha256"]
    del inputs["expected_action"]
    return candidate, {**arguments(candidate), **inputs}


def test_full_reader_and_package_handoff_remains_unqualified_and_detached():
    candidate, inputs = fixture()
    before = deepcopy((candidate, inputs))
    result = handoff.prepare_reuse_candidate(candidate, **inputs)
    assert (candidate, inputs) == before
    assert result["package"] == candidate and result["package"] is not candidate
    assert result["status"] == "READY_FOR_FRESH_REUSE_TESTS"
    assert result["learning_provenance_bound"] is True
    assert result["qualification_status"] == "UNQUALIFIED"
    assert result["package"]["provenance"]["verification_status"] == "UNVERIFIED"
    assert result["package_admission"]["provenance_verified"] is False
    assert result["learning_evidence"]["observed_correct_gain"] == 2
    assert not any(result[k] for k in ("promotion_granted", "execution_performed",
        "storage_performed", "fresh_native_reuse_tested", "retention_tested",
        "rollback_tested", "parent_evidence_verified"))
    assert result["receipt_sha256"] == evidence.digest({k: v for k, v in result.items() if k != "receipt_sha256"})


@pytest.mark.parametrize("field", ["policy_source_sha256", "policy_checkpoint_sha256", "producer_source_sha", "producer_evidence_sha256"])
def test_rehashed_package_cannot_claim_another_producer(field):
    candidate, inputs = fixture()
    candidate["provenance"][field] = "d" * (40 if field == "producer_source_sha" else 64)
    inputs["expected_digest"] = packages.package_digest(candidate)
    with pytest.raises(handoff.HandoffError, match="LEARNING_"):
        handoff.prepare_reuse_candidate(candidate, **inputs)


@pytest.mark.parametrize("change", ["binding", "program"])
def test_rehashed_valid_package_must_match_the_sealed_learned_action(change):
    candidate, inputs = fixture()
    if change == "binding":
        candidate["binding"] = candidate["io"]["input"]["slot"] = 1
    else:
        candidate["program"]["procedures"]["main"]["return"] = "v0"
        candidate["io"]["output"]["producer_cjt_id"] = "A"
        candidate["provenance"]["source_program_sha256"] = packages.package_digest(candidate["program"])
    inputs["expected_digest"] = packages.package_digest(candidate)
    with pytest.raises(evidence.LearningEvidenceError, match="PACKAGE_ACTION_NOT_SEALED_PREDICTION"):
        handoff.prepare_reuse_candidate(candidate, **inputs)


@pytest.mark.parametrize("field", ["inspection_bytes", "stored_audit_bytes", "index_bytes", "predictions_bytes", "checkpoints_bytes"])
def test_package_digest_does_not_replace_external_audit_binding(field):
    candidate, inputs = fixture()
    inputs[field] += b" "
    with pytest.raises(evidence.LearningEvidenceError):
        handoff.prepare_reuse_candidate(candidate, **inputs)


@pytest.mark.parametrize("key,value", [
    ("case_index", 71), ("arm", "rule"), ("arm", "cas_untrained"),
    ("minimum_correct_gain", 3), ("expected_inspection_sha256", "d" * 64),
    ("expected_stored_audit_sha256", "d" * 64),
])
def test_external_scope_and_learning_requirements_are_not_weakened(key, value):
    candidate, inputs = fixture()
    inputs[key] = value
    with pytest.raises(evidence.LearningEvidenceError):
        handoff.prepare_reuse_candidate(candidate, **inputs)


def test_different_registered_learning_source_is_not_silently_accepted():
    candidate, inputs = fixture()
    inputs["trusted_source_sha"] = "d" * 40
    with pytest.raises(handoff.HandoffError, match="UNSUPPORTED_LEARNING_SOURCE"):
        handoff.prepare_reuse_candidate(candidate, **inputs)


def test_native_permission_scope_still_applies():
    candidate, inputs = fixture()
    inputs["permitted_cjts"] = ["A", "B"]
    with pytest.raises(packages.PackageError, match="CALLER_CJT_SCOPE_DENIED"):
        handoff.prepare_reuse_candidate(candidate, **inputs)


def test_parent_lineage_is_not_inferred_from_a_successful_learning_audit():
    candidate, inputs = fixture()
    inputs["expected_version"] = 2
    inputs["expected_parent_digest"] = "f" * 64
    with pytest.raises(packages.PackageError, match="CALLER_LINEAGE_MISMATCH"):
        handoff.prepare_reuse_candidate(candidate, **inputs)
