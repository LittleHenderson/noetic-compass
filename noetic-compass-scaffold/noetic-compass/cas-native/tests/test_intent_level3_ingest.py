from pathlib import Path

import pytest

from cas_native.intent import (
    build_candidate_expressions,
    intent_from_level3_record,
    load_level3_intents,
)


def test_level3_ingest_keeps_answer_out_of_model_input():
    record = {
        "id": "l3-test",
        "source_level2_id": "level2-test",
        "bucket": "v76_production",
        "cas_expression": "Theta(Omega_focus) = 0.6*^1^C_{F2}|A + 0.4*^7^P_{F4}|T -> Omega_focus",
        "user_prompt": (
            "families: production recipe; production target Omega_focus; "
            "recipe coefficients: 0.6 times Noetic ^1; domain C; drive F2; "
            "register |A / 0.4 times Noetic ^7; domain P; drive F4; register |T"
        ),
        "assistant_response": (
            "The exact answer is Theta(Omega_focus) = 0.6*^1^C_{F2}|A "
            "+ 0.4*^7^P_{F4}|T -> Omega_focus"
        ),
        "tags": ["level3", "has_production"],
        "provenance": {"seed": 42},
    }

    intent = intent_from_level3_record(record)

    assert intent.model_input_text() == record["user_prompt"]
    assert "Theta(Omega_focus)" not in intent.model_input_text()
    assert intent.expression_family == "production"
    assert intent.transition_kind == "production"
    assert intent.production is not None
    assert intent.production.omega_target == "Omega_focus"
    assert [ingredient.coefficient for ingredient in intent.production.ingredients] == [0.6, 0.4]
    assert [state.to_cas() for state in intent.axis.states] == [
        "^1^C_{F2}|A",
        "^7^P_{F4}|T",
    ]
    assert build_candidate_expressions(intent)[0] == record["cas_expression"]
    assert intent.validate() == []


def test_level3_ingest_maps_meta_logic_product():
    record = {
        "id": "l3-product",
        "bucket": "meta_logic",
        "cas_expression": "Product(Noetics, Domains)",
        "user_prompt": "families: meta logic; carriers: Noetics and Domains; relation: product",
        "assistant_response": "The exact answer is Product(Noetics, Domains).",
    }

    intent = intent_from_level3_record(record)

    assert intent.expression_family == "meta_logic"
    assert intent.meta_logic is not None
    assert intent.meta_logic.relations == ("product",)
    assert intent.meta_logic.carriers == ("Noetics", "Domains")
    assert intent.model_input_text() == record["user_prompt"]
    assert "Product(Noetics, Domains)" not in intent.model_input_text()
    assert intent.validate() == []


def test_level3_ingest_tolerates_mojibake_omega_records():
    record = {
        "id": "l3-mojibake",
        "bucket": "v77_omega",
        "cas_expression": "(^4_{F2}|E Ã— ^4_{F7}|A) = ^4|Î©_attunement",
        "user_prompt": "named emergent target: Î©_attunement; states: Noetic ^4; drive F2; register |E",
    }

    intent = intent_from_level3_record(record)

    assert intent.omega_targets == ("Omega_attunement",)
    assert intent.register_intent.mode == "integration"
    assert intent.register_intent.omega_target == "Omega_attunement"
    assert intent.validate() == []


def test_level3_ingest_loads_heldout_sample_if_present():
    path = Path("cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl")
    if not path.exists():
        pytest.skip("held-out Level 3 eval file not present")

    intents = load_level3_intents(path, limit=20)

    assert len(intents) == 20
    assert all(intent.model_input_text() == intent.user_prompt for intent in intents)
    assert all(not intent.validate() for intent in intents)
