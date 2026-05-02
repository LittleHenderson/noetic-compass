"""Tests for structured-token paraphrase-invariance evaluation helpers."""

from __future__ import annotations

from cas_native.training.evaluate_paraphrase_invariance import (
    build_invariance_report,
    extract_recoverable_slots,
    make_paraphrase_records,
)


def test_extract_recoverable_slots_removes_wrapper_text():
    prompt = (
        "I need the CAS expression for this recoverable structure: "
        "families: state expression; states: Noetic ^2; domain C (cognitive). "
        "What notation should I use?"
    )

    slots = extract_recoverable_slots(prompt)

    assert slots.startswith("families: state expression")
    assert "What notation" not in slots


def test_make_paraphrase_records_preserves_targets_and_adds_metadata():
    records = [
        {
            "id": "r1",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Turn this formal natural-language CAS reading into the exact expression: families: state expression; states: Noetic ^2.",
        }
    ]

    paraphrases = make_paraphrase_records(records, variants_per_record=2)

    assert len(paraphrases) == 2
    assert {item["base_id"] for item in paraphrases} == {"r1"}
    assert [item["paraphrase_index"] for item in paraphrases] == [0, 1]
    assert all(item["cas_expression"] == "^2^C_{F4}|f" for item in paraphrases)
    assert all(item["id"].startswith("r1::para") for item in paraphrases)
    assert all("families:" in item["user_prompt"] for item in paraphrases)


def test_build_invariance_report_tracks_prediction_consistency():
    canonical = [
        {
            "id": "r1",
            "bucket": "v75_register",
            "all_heads_exact": True,
            "prediction": {"expression_family": "register_state", "transition_kind": "state"},
        },
        {
            "id": "r2",
            "bucket": "v77_rule_four",
            "all_heads_exact": False,
            "prediction": {"expression_family": "omega", "transition_kind": "omega_bind"},
        },
    ]
    paraphrases = [
        {
            "id": "r1::para0",
            "base_id": "r1",
            "bucket": "v75_register",
            "all_heads_exact": True,
            "prediction": {"expression_family": "register_state", "transition_kind": "state"},
        },
        {
            "id": "r2::para0",
            "base_id": "r2",
            "bucket": "v77_rule_four",
            "all_heads_exact": False,
            "prediction": {"expression_family": "rule_four", "transition_kind": "relation"},
        },
    ]

    report = build_invariance_report(canonical, paraphrases)

    assert report["n_comparable"] == 2
    assert report["all_heads_prediction_consistency_rate"] == 0.5
    assert report["canonical_exact_retention_rate"] == 1.0
    assert report["by_bucket"]["v75_register"]["all_heads_prediction_consistency_rate"] == 1.0
    assert report["by_bucket"]["v77_rule_four"]["all_heads_prediction_consistency_rate"] == 0.0
