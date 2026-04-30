"""Tests for CAS Transformer turn-type admissibility hooks."""

from api.notation import (
    TurnAdmissibilityContext,
    list_turn_admissibility_rules,
    turn_admissibility_artifact,
    validate_turn_admissibility,
)
from api.notation.turn_admissibility import MetaLogicRelation


def test_all_eleven_turn_rules_are_exposed():
    rules = list_turn_admissibility_rules()

    assert set(rules) == {
        "OPEN",
        "ACK",
        "MIRROR",
        "CLARIFY",
        "EMPATHIZE",
        "ANSWER",
        "PLAN",
        "REFUSE",
        "REFUSE_CLAIM",
        "REPAIR",
        "CLOSE",
    }
    assert rules["CLARIFY"]["tight"] is True
    assert rules["ANSWER"]["tight"] is True


def test_open_requires_idle_channel():
    result = validate_turn_admissibility("OPEN", {"facts": []})

    assert not result.admissible
    assert result.missing_facts == ("channel_idle",)

    valid = validate_turn_admissibility("OPEN", {"facts": ["channel_idle"]})
    assert valid.admissible
    assert "dialogue_opened" in valid.valid_effects


def test_clarify_requires_lacunarity_and_named_unfilled_slot():
    result = validate_turn_admissibility(
        "CLARIFY",
        {"facts": ["lacunarity_detected"]},
    )

    assert not result.admissible
    assert "unfilled_slot_present" in result.missing_facts
    assert any("named unfilled slot" in item for item in result.diagnostics)

    valid = validate_turn_admissibility(
        "CLARIFY",
        {
            "facts": ["lacunarity_detected"],
            "unfilled_slots": ["target_register"],
        },
    )
    assert valid.admissible
    assert valid.tight is True


def test_refuse_can_be_licensed_by_blocked_authority_relation():
    context = TurnAdmissibilityContext.from_payload(
        {
            "meta_relations": [
                ("UserRequestSet", "licenses", "SystemInstructionSet")
            ]
        }
    )

    result = validate_turn_admissibility("REFUSE", context)

    assert result.admissible
    assert "boundary_violation" in result.observed_facts
    assert "authority_violation" in result.observed_facts
    assert any("blocked authority relation" in item for item in result.diagnostics)


def test_refuse_claim_requires_evidence_gap_or_unsupported_claim_attempt():
    unsupported = validate_turn_admissibility(
        "REFUSE_CLAIM",
        {"facts": ["claim_attempted"]},
    )

    assert unsupported.admissible
    assert "evidence_gap" in unsupported.observed_facts

    supported = validate_turn_admissibility(
        "REFUSE_CLAIM",
        {
            "facts": ["claim_attempted"],
            "evidence_paths": [("EvidenceSet", "ValidatedClaimSet")],
        },
    )

    assert not supported.admissible
    assert supported.missing_facts == ("evidence_gap",)


def test_answer_requires_task_active_and_claim_supported():
    result = validate_turn_admissibility("ANSWER", {"facts": ["task_active"]})

    assert not result.admissible
    assert result.missing_facts == ("claim_supported",)

    valid = validate_turn_admissibility(
        "ANSWER",
        {"facts": ["task_active", "claim_supported"]},
    )
    assert valid.admissible
    assert "supported_response_rendered" in valid.valid_effects


def test_repair_requires_detected_prior_error():
    result = validate_turn_admissibility("REPAIR", {"facts": ["task_active"]})

    assert not result.admissible
    assert result.missing_facts == ("prior_error_detected",)

    valid = validate_turn_admissibility(
        "REPAIR",
        {"facts": ["prior_error_detected"]},
    )
    assert valid.admissible


def test_artifact_is_json_ready_and_accepts_relation_objects():
    artifact = turn_admissibility_artifact(
        "REFUSE",
        {
            "meta_relations": [
                MetaLogicRelation(
                    "UserRequestSet",
                    "licenses",
                    "SystemInstructionSet",
                )
            ]
        },
    )

    assert artifact["kind"] == "turn_admissibility"
    assert artifact["result"]["admissible"] is True
    assert "boundary_violation" in artifact["result"]["observed_facts"]


def test_unknown_turn_type_is_invalid():
    result = validate_turn_admissibility("JOKE", {"facts": ["task_active"]})

    assert not result.admissible
    assert result.diagnostics == ("unknown turn_type 'JOKE'",)

