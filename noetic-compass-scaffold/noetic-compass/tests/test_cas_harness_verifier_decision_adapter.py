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


def test_adapter_does_not_mutate_packet():
    packet = _stage21_packet()
    before = deepcopy(packet)

    verifier_decision_from_packet(packet)

    assert packet == before
