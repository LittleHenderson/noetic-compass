"""Tests for the Step-10 backbone structured train/eval runner."""

from __future__ import annotations

from pathlib import Path

from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.train_structured_backbone import (
    _is_heldout_eval_path,
    evaluate_backbone_structured_prediction,
    train_backbone_structured_local,
)


def _records():
    return [
        {
            "id": "v75",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 in cognitive domain with drive F4 and affective register.",
        },
        {
            "id": "v76",
            "bucket": "v76_production",
            "cas_expression": (
                "\u0398(\u03a9_focus) = 0.40*^3^P_{F2}|A + "
                "0.60*^7^O_{F5}|E \u2192 \u03a9_focus"
            ),
            "user_prompt": "Recipe target Omega focus from Noetic 3 P F2 A and Noetic 7 O F5 E.",
        },
        {
            "id": "v77",
            "bucket": "v77_omega",
            "cas_expression": "(^4_{F2}|E \u00d7 ^4_{F7}|A) = ^4|\u03a9_attunement",
            "user_prompt": "Omega attunement integrates Noetic 4 embodied F2 and analytical F7.",
        },
        {
            "id": "meta",
            "bucket": "meta_logic",
            "cas_expression": "Product(Noetics, Domains)",
            "user_prompt": "Represent the Cartesian product of Noetics and Domains.",
        },
    ]


def _tokenizer(records):
    return HybridCASTokenizer.from_texts(
        [str(record["user_prompt"]) for record in records],
        freeze=True,
    )


def test_backbone_train_eval_runner_returns_manifest():
    records = _records()
    tokenizer = _tokenizer(records)

    model, manifest = train_backbone_structured_local(
        records,
        records,
        tokenizer=tokenizer,
        d_model=32,
        n_layers=1,
        n_heads=4,
        bottleneck_dim=16,
        batch_size=2,
        epochs=1,
        lr=0.001,
        seed=17,
        max_length=32,
        progress_print=False,
        filter_eval_overlaps=False,
    )

    assert manifest["config"]["mode"] == "backbone_structured_prediction"
    assert manifest["config"]["n_train"] == 4
    assert manifest["config"]["n_eval"] == 4
    assert manifest["training"]["total_steps"] == 2
    assert manifest["eval"]["n"] == 4
    assert 0.0 <= manifest["eval"]["all_heads_exact_rate"] <= 1.0
    assert model.backbone.config.d_model == 32


def test_backbone_eval_reports_per_bucket_metrics():
    records = _records()
    tokenizer = _tokenizer(records)
    model, _manifest = train_backbone_structured_local(
        records,
        None,
        tokenizer=tokenizer,
        d_model=32,
        n_layers=1,
        n_heads=4,
        bottleneck_dim=16,
        batch_size=2,
        epochs=1,
        lr=0.001,
        seed=19,
        max_length=32,
        progress_print=False,
    )

    eval_manifest = evaluate_backbone_structured_prediction(
        model,
        records,
        tokenizer,
        batch_size=2,
        max_length=32,
    )

    assert eval_manifest["n"] == 4
    assert set(eval_manifest["by_bucket"]) == {
        "v75_register",
        "v76_production",
        "v77_omega",
        "meta_logic",
    }
    assert len(eval_manifest["samples"]) == 4


def test_heldout_training_input_guard_is_specific():
    assert _is_heldout_eval_path(Path("level3_recoverable_eval_1000.jsonl"))
    assert not _is_heldout_eval_path(Path("level3_recoverable_full.jsonl"))
