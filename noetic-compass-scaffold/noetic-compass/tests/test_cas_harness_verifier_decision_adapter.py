from __future__ import annotations

from copy import deepcopy

from api.services.cas_harness_verifier_decision_adapter import verifier_decision_from_packet


def _stage21_packet() -> dict:
    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": "stage21a-allow-001",
        "provenance": {
            "source_stage": "Stage 21A",
            "source_reports": [
                "stage19_verification_stack_report.json",
                "stage20_generation_readiness_report.json",
            ],
        },
        "verification": {
            "accepted": True,
            "mode": "BALANCED",
            "confidence_tier": "high",
            "mode_profile": {
                "accepted_accuracy": 0.9816,
                "coverage": 0.7173,
            },
            "suppression_reasons": [],
        },
        "generation_readiness": {
            "generation_readiness": "allow",
            "risk_score": 0.11,
            "policy_version": "stage20_v1",
            "reasons": [],
        },
    }


def _s7_f28_packet() -> dict:
    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": "s7-f28-balanced-bridge-gpt-neox-20b-20260526",
        "provenance": {"method_label": "S7-F28-BALANCED-BRIDGE"},
        "verification": {
            "explicit_verifier_decision": {
                "verdict": "FLAG_FOR_HUMAN_REVIEW",
                "confidence": 0.803571,
                "source": "S7-F28-BALANCED-BRIDGE",
                "reason": "Final ACCEPT/SUPPRESS still requires the Stage 19/20/21 verifier decision layer.",
            },
            "proof_chips": [
                {"id": "model_proof", "status": "present"},
                {"id": "cas_readout", "status": "verified"},
                {"id": "causal_proof", "status": "verified"},
                {"id": "control_proof", "status": "verified"},
                {"id": "output_proof", "status": "verified"},
                {"id": "packet_proof", "status": "present"},
            ],
        },
    }


def _stage9_40e_packet() -> dict:
    return {
        "schema_version": "cas_harness_stage9_40e_evidence_packet.v1",
        "trace_id": "trace-stage9-40e",
        "verdict": "ACCEPT",
        "verification": {
            "explicit_verifier_decision": {
                "verdict": "ACCEPT",
                "confidence": 0.91,
                "source": "stage9_40e_verifier_decision",
                "reason": "All Stage 9 40E proof chips pass.",
                "decision_scope": "stage9_40e_validation_packet",
                "coverage": {
                    "basis": "stage9_40e_validation_cases",
                    "case_count": 80,
                    "class_count": 40,
                },
            },
            "proof_chips": [
                {"id": "model_proof", "status": "present"},
                {"id": "cas_readout", "status": "verified"},
                {"id": "causal_proof", "status": "verified"},
                {"id": "control_proof", "status": "verified"},
                {"id": "output_proof", "status": "verified"},
                {"id": "packet_proof", "status": "present"},
            ],
        },
    }


def test_allow_and_accepted_maps_to_accept_with_accepted_accuracy():
    decision = verifier_decision_from_packet(_stage21_packet())

    assert decision is not None
    assert decision.verdict == "ACCEPT"
    assert decision.confidence == 0.9816
    assert decision.source == "stage19_verification_stack+stage20_generation_readiness"
    assert "allow" in decision.reason


def test_suppress_and_rejected_maps_to_suppress_with_risk_score():
    packet = _stage21_packet()
    packet["verification"]["accepted"] = False
    packet["generation_readiness"]["generation_readiness"] = "suppress"
    packet["generation_readiness"]["risk_score"] = 0.9

    decision = verifier_decision_from_packet(packet)

    assert decision is not None
    assert decision.verdict == "SUPPRESS"
    assert decision.confidence == 0.9
    assert "suppress" in decision.reason


def test_caveat_and_accepted_maps_to_human_review_with_accepted_accuracy():
    packet = _stage21_packet()
    packet["generation_readiness"]["generation_readiness"] = "caveat"

    decision = verifier_decision_from_packet(packet)

    assert decision is not None
    assert decision.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert decision.confidence == 0.9816
    assert "caveat" in decision.reason


def test_constrain_and_rejected_maps_to_human_review_with_risk_score():
    packet = _stage21_packet()
    packet["verification"]["accepted"] = False
    packet["generation_readiness"]["generation_readiness"] = "constrain"
    packet["generation_readiness"]["risk_score"] = 0.67

    decision = verifier_decision_from_packet(packet)

    assert decision is not None
    assert decision.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert decision.confidence == 0.67
    assert "constrain" in decision.reason


def test_generic_evidence_packet_schema_does_not_create_verifier_decision():
    packet = _stage21_packet()
    packet["schema_version"] = "evidence_packet.v1"

    assert verifier_decision_from_packet(packet) is None


def test_missing_stage19_or_stage20_source_does_not_create_verifier_decision():
    packet = _stage21_packet()
    packet["provenance"]["source_reports"] = ["stage19_verification_stack_report.json"]

    assert verifier_decision_from_packet(packet) is None


def test_missing_numeric_confidence_does_not_create_verifier_decision():
    packet = _stage21_packet()
    packet["verification"]["mode_profile"].pop("accepted_accuracy")

    assert verifier_decision_from_packet(packet) is None


def test_out_of_range_confidence_does_not_create_verifier_decision():
    packet = _stage21_packet()
    packet["verification"]["mode_profile"]["accepted_accuracy"] = 1.2

    assert verifier_decision_from_packet(packet) is None


def test_s7_f28_packet_maps_only_to_human_review():
    decision = verifier_decision_from_packet(_s7_f28_packet())

    assert decision is not None
    assert decision.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert decision.confidence == 0.803571
    assert decision.source == "S7-F28-BALANCED-BRIDGE"
    assert "Stage 19/20/21" in decision.reason


def test_s7_f28_packet_never_upgrades_to_accept():
    packet = _s7_f28_packet()
    packet["verification"]["explicit_verifier_decision"]["verdict"] = "ACCEPT"

    assert verifier_decision_from_packet(packet) is None


def test_s7_f28_packet_requires_pass_ready_proof_chips():
    packet = _s7_f28_packet()
    packet["verification"]["proof_chips"][3]["status"] = "missing"

    assert verifier_decision_from_packet(packet) is None


def test_stage9_40e_packet_can_pass_through_explicit_accept():
    decision = verifier_decision_from_packet(_stage9_40e_packet())

    assert decision is not None
    assert decision.verdict == "ACCEPT"
    assert decision.confidence == 0.91
    assert decision.source == "stage9_40e_verifier_decision"
    assert decision.decision_scope == "stage9_40e_validation_packet"
    assert decision.coverage == {
        "basis": "stage9_40e_validation_cases",
        "case_count": 80,
        "class_count": 40,
    }


def test_stage9_40e_packet_blocks_accept_when_packet_verdict_does_not_match():
    packet = _stage9_40e_packet()
    packet["verdict"] = "FLAG_FOR_HUMAN_REVIEW"

    assert verifier_decision_from_packet(packet) is None


def test_stage9_40e_packet_requires_pass_ready_proof_chips():
    packet = _stage9_40e_packet()
    packet["verification"]["proof_chips"][4]["status"] = "missing"

    assert verifier_decision_from_packet(packet) is None


def test_stage9_40e_packet_requires_core_chips_verified_not_merely_present():
    packet = _stage9_40e_packet()
    packet["verification"]["proof_chips"][3]["status"] = "present"

    assert verifier_decision_from_packet(packet) is None


def test_stage9_40e_packet_blocks_invalid_confidence():
    packet = _stage9_40e_packet()
    packet["verification"]["explicit_verifier_decision"]["confidence"] = 1.2

    assert verifier_decision_from_packet(packet) is None


def test_adapter_does_not_mutate_packet():
    packet = _stage21_packet()
    before = deepcopy(packet)

    verifier_decision_from_packet(packet)

    assert packet == before
