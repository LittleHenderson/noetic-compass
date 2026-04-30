"""Tests for the Step-10 backbone structured train/eval runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.model import CASNativeConfig, CASNativeModel
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.train_structured_backbone import (
    _is_heldout_eval_path,
    cas_config_from_metadata,
    checkpoint_state_dict,
    evaluate_backbone_structured_prediction,
    load_compatible_backbone_state_dict,
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


def test_config_from_checkpoint_metadata_uses_checkpoint_shape():
    records = _records()
    tokenizer = _tokenizer(records)
    payload = {
        "model_config": {
            "d_model": 32,
            "n_layers": 1,
            "n_heads": 4,
            "vocab_size": tokenizer.vocab_size,
            "max_seq_len": 64,
            "fractal_depth": 1,
            "num_ethical_propositions": 3,
            "dropout": 0.0,
            "causal_lm": True,
        }
    }

    config = cas_config_from_metadata(
        tokenizer=tokenizer,
        checkpoint_payload=payload,
        d_model=999,
        n_layers=9,
        n_heads=9,
        max_length=999,
    )

    assert config.d_model == 32
    assert config.n_layers == 1
    assert config.n_heads == 4
    assert config.vocab_size == tokenizer.vocab_size
    assert config.max_seq_len == 64
    assert config.causal_lm is True


def test_config_from_checkpoint_metadata_rejects_tokenizer_mismatch():
    records = _records()
    tokenizer = _tokenizer(records)
    payload = {
        "model_config": {
            "d_model": 32,
            "n_layers": 1,
            "n_heads": 4,
            "vocab_size": tokenizer.vocab_size + 1,
        }
    }

    with pytest.raises(ValueError, match="tokenizer vocab_size does not match"):
        cas_config_from_metadata(tokenizer=tokenizer, checkpoint_payload=payload)


def test_checkpoint_state_dict_extracts_wrapped_model_state_dict():
    model = CASNativeModel(
        CASNativeConfig(
            d_model=32,
            n_layers=1,
            n_heads=4,
            vocab_size=64,
            max_seq_len=32,
            fractal_depth=1,
            num_ethical_propositions=3,
            dropout=0.0,
        )
    )

    extracted = checkpoint_state_dict({"model_state_dict": model.state_dict()})

    assert "token_embedding.weight" in extracted


def test_load_compatible_backbone_state_dict_reports_skipped_shapes():
    target = CASNativeModel(
        CASNativeConfig(
            d_model=32,
            n_layers=1,
            n_heads=4,
            vocab_size=64,
            max_seq_len=32,
            fractal_depth=1,
            num_ethical_propositions=3,
            dropout=0.0,
        )
    )
    source = CASNativeModel(target.config)
    state = dict(source.state_dict())
    state["lm_head.weight"] = state["lm_head.weight"][:10]
    state["v2_components.extra.weight"] = state["token_embedding.weight"]

    report = load_compatible_backbone_state_dict(target, state)

    assert report["loaded"] > 0
    assert report["skipped_unknown"] == 1
    assert "lm_head.weight" in report["skipped_shape"]
