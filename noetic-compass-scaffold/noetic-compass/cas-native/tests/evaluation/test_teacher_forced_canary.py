"""Tests for diagnostic-infra piece 2: teacher-forced canary evaluator.

Per user 2026-05-11. CPU-only, tiny model + tiny synthetic tokenizer.
Verifies the TF eval produces correctly-shaped per-record fields and the
summary aggregates.
"""
from __future__ import annotations

import pytest
import torch

from cas_native.evaluation.stage7_canary_pack import canary_pack
from cas_native.evaluation.teacher_forced_canary import (
    _has_phrase_loop,
    teacher_forced_canary_pack,
    teacher_forced_record,
)
from cas_native.training.tokenizer import HybridCASTokenizer


def _make_tokenizer():
    tok = HybridCASTokenizer()
    for w in ["hello", "world", "thought", "cognitive", "thinking",
              "expression", "the", "is", "valid", "stage", "name", "a",
              "in", "with", "and", "of"]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _tiny_simplex_mvp():
    """Tiny end-to-end model wrapper. Mirrors run_cpu_smoke's factory."""
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    cfg = SimplexTrainConfig(
        data_path="x", output_dir="y",
        d_model=32, encoder_n_layers=2, encoder_n_heads=4,
        decoder_n_layers=2, decoder_n_heads=4,
        batch_size=2,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    tok = _make_tokenizer()
    vocab_size = int(tok.vocab_size)
    model = build_simplex_mvp_model(
        cfg, vocab_size=vocab_size, vocab_size_english=vocab_size,
    )
    return model, tok, cfg


# ---------------------------------------------------------------------------
# Phrase-loop helper
# ---------------------------------------------------------------------------

def test_has_phrase_loop_clean():
    found, n = _has_phrase_loop("This is a normal English sentence.")
    assert not found


def test_has_phrase_loop_simple_repeat():
    found, n = _has_phrase_loop("the the the the cat")
    assert found
    assert n >= 3


# ---------------------------------------------------------------------------
# TF eval — shape contract
# ---------------------------------------------------------------------------

def test_teacher_forced_record_returns_complete_dict():
    """Every field of the TfCanaryResult must be populated."""
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)

    rec = {
        "id": "test_001",
        "prompt_text": "Describe this state.",
        "reply_text": "A thought in cognitive thinking.",
        "cas_expression": "^0^C_{F4}",
        "v1mix_grammar_category_or_error_class": "state_literal",
        "v1mix_task_type": "cas_to_english",
    }
    result = teacher_forced_record(
        model, rec, collator, tok, device=torch.device("cpu"),
    )
    assert result.record_id == "test_001"
    assert result.category == "state_literal"
    assert result.task == "cas_to_english"
    assert result.target_len_tokens > 0
    assert torch.isfinite(torch.tensor(result.loss_lm))
    assert torch.isfinite(torch.tensor(result.loss_slot_type))
    assert 0.0 <= result.argmax_top1_acc <= 1.0
    assert isinstance(result.argmax_text, str)
    assert result.canonical_stage_vars_in_target == 0
    assert result.canonical_stage_vars_in_argmax >= 0


def test_teacher_forced_record_detects_canonical_stage_vars():
    """A target reply containing 'stageA0_5_0296' must register as 1."""
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)

    rec = {
        "id": "test_rpm",
        "prompt_text": "Explain.",
        "reply_text": "Let stageA0_5_0296 name a thought, stageD3_2_0049 a feeling.",
        "cas_expression": "let stageA0_5_0296 = ^0^P",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
        "v1mix_task_type": "cas_to_english",
    }
    result = teacher_forced_record(
        model, rec, collator, tok, device=torch.device("cpu"),
    )
    assert result.canonical_stage_vars_in_target == 2


# ---------------------------------------------------------------------------
# Pack-level summary
# ---------------------------------------------------------------------------

def test_canary_pack_summary_fields_present():
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    result = teacher_forced_canary_pack(
        model, canary_pack(), collator, tok, device=torch.device("cpu"),
    )
    assert result["n"] > 0
    s = result["summary"]
    expected = {
        "mean_loss_lm",
        "mean_argmax_top1_acc",
        "n_records_with_argmax_loop",
        "canonical_stage_vars_in_targets",
        "canonical_stage_vars_in_argmax",
        "canonical_recovery_rate",
        "mean_loss_copy_at_valid",
        "records_with_valid_copy",
    }
    missing = expected - set(s.keys())
    assert not missing, f"summary missing fields: {missing}"


def test_canary_pack_preserves_record_count():
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    pack = canary_pack()
    result = teacher_forced_canary_pack(
        model, pack, collator, tok, device=torch.device("cpu"),
    )
    assert len(result["per_record"]) == len(pack)


def test_canary_targets_contain_canonical_stage_vars():
    """Two of the canary records carry canonical stage var identifiers
    in their target text. The TF eval should detect these."""
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    result = teacher_forced_canary_pack(
        model, canary_pack(), collator, tok, device=torch.device("cpu"),
    )
    assert result["summary"]["canonical_stage_vars_in_targets"] >= 2


# ---------------------------------------------------------------------------
# Model eval mode restored
# ---------------------------------------------------------------------------

def test_model_train_mode_restored_after_eval():
    """The TF eval must NOT leave the model in eval mode after it returns,
    so a caller mid-training-loop can continue without losing dropout."""
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok, _ = _tiny_simplex_mvp()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    model.train()
    assert model.training
    _ = teacher_forced_canary_pack(
        model, canary_pack()[:2], collator, tok, device=torch.device("cpu"),
    )
    assert model.training, "TF eval left model in eval mode"
