"""Tests for deterministic CAS Transformer turn generation."""

from __future__ import annotations

from cas_synthetic.generator.cas_transformer import (
    CASSurfaceRendererV0,
    CASTransformerTurnGenerator,
    TURN_TEMPLATE_BANK,
)


def test_renderer_v0_has_multiple_templates_for_every_turn_type():
    renderer = CASSurfaceRendererV0()

    assert set(TURN_TEMPLATE_BANK) == {
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
    assert all(len(templates) >= 3 for templates in TURN_TEMPLATE_BANK.values())
    assert renderer.render("CLARIFY", fields={"missing_slot": "the drive"}).surface_span


def test_generator_emits_valid_records_across_all_phase1_buckets():
    generator = CASTransformerTurnGenerator(seed=7)
    records = list(generator.iter_records(10))

    assert len(records) == 10
    assert all(record.validate() == [] for record in records)
    assert {record.provenance["bucket"] for record in records} == {
        "open_ack_close",
        "clarify_lacunarity",
        "empathetic_acknowledgment",
        "structured_answer",
        "planning_response",
        "repair_response",
        "refusal_boundary",
        "production_recipe_explanation",
        "meta_logic_nesting",
        "authority_evidence_boundary",
    }


def test_generator_is_deterministic_for_same_seed():
    first = [record.to_dict() for record in CASTransformerTurnGenerator(seed=11).iter_records(12)]
    second = [record.to_dict() for record in CASTransformerTurnGenerator(seed=11).iter_records(12)]

    assert first == second


def test_open_ack_record_serializes_trace_edges():
    record = next(CASTransformerTurnGenerator(seed=3).iter_records(1))
    payload = record.to_dict()

    assert payload["trace_edges"] == [
        {"source": "t0", "target": "t1", "relation": "depends_on"}
    ]
    assert payload["response"] == " ".join(
        node["surface_span"] for node in payload["trace"]
    )


def test_production_record_contains_typed_modifier_and_valid_recipe():
    records = list(CASTransformerTurnGenerator(seed=5).iter_records(8))
    record = records[7]
    transition = record.trace[0].transition

    assert record.provenance["bucket"] == "production_recipe_explanation"
    assert transition is not None
    assert transition.production is not None
    assert transition.production.validate() == []
    assert transition.production.modifiers[0].kind == "catalyst"
    assert transition.register_binding is not None
    assert transition.register_binding.mode == "integration"


def test_clarify_record_is_tight_and_has_lacunarity_precondition():
    records = list(CASTransformerTurnGenerator(seed=5).iter_records(2))
    record = records[1]
    node = record.trace[0]

    assert record.provenance["bucket"] == "clarify_lacunarity"
    assert node.zone == "TIGHT"
    assert "lacunarity_detected" in node.state_context.facts
    assert node.transition_diagnostics() == []


def test_generated_records_include_conditionality_perturbations():
    record = next(CASTransformerTurnGenerator(seed=13).iter_records(1))
    payload = record.to_dict()

    assert len(payload["perturbations"]) == 2
    assert {item["perturbation_type"] for item in payload["perturbations"]} == {
        "turn_type",
        "meta_logic",
    }

