"""Tests for diagnostic infra piece 4 — decode-time ablations.

Per user 2026-05-11. CPU-only, tiny model. Verifies all four ablation
modes return shape-correct outputs and the phrase_bias_disabled mode
correctly restores ``phrase_bias_alpha`` after the context exits.
"""
from __future__ import annotations

import torch

from cas_native.evaluation.decode_ablations import (
    ABLATION_MODES,
    _build_copy_id_mask,
    _phrase_bias_disabled,
    run_decode_ablations_one,
    run_decode_ablations_pack,
)
from cas_native.evaluation.stage7_canary_pack import canary_pack
from cas_native.training.tokenizer import HybridCASTokenizer


def _make_tokenizer():
    tok = HybridCASTokenizer()
    for w in ["hello", "the", "a", "thought", "expression"]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _tiny_model():
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
    model = build_simplex_mvp_model(
        cfg, vocab_size=int(tok.vocab_size),
        vocab_size_english=int(tok.vocab_size),
    )
    return model, tok


# ---------------------------------------------------------------------------
# Phrase-bias context manager
# ---------------------------------------------------------------------------

def test_phrase_bias_disabled_context_zeros_alpha_then_restores():
    model, _ = _tiny_model()
    decoder = model.decoder
    original = decoder.phrase_bias_alpha.data.clone()
    assert original.abs().sum() > 0, "phrase_bias_alpha must be non-zero at init"

    with _phrase_bias_disabled(decoder):
        assert decoder.phrase_bias_alpha.item() == 0.0

    # Restored
    assert torch.equal(decoder.phrase_bias_alpha.data, original)


def test_phrase_bias_disabled_handles_missing_attribute():
    """A model without phrase_bias_alpha must not raise."""
    class _NoAttr:
        pass
    with _phrase_bias_disabled(_NoAttr()):
        pass  # should be a no-op, no exception


# ---------------------------------------------------------------------------
# Copy-id mask
# ---------------------------------------------------------------------------

def test_build_copy_id_mask_includes_domain_letters():
    """The mask should include ids for ^P/^C/^E/^O if they're in vocab."""
    tok = _make_tokenizer()
    masked = _build_copy_id_mask(tok)
    # The HybridCASTokenizer reserved tokens include ^P, ^C, ^E, ^O.
    # Resolve their ids via the word2id map.
    for s in ("^P", "^C", "^E", "^O"):
        if s in tok.word2id:
            assert int(tok.word2id[s]) in masked, f"{s} not in copy mask"


def test_build_copy_id_mask_includes_register_letters():
    tok = _make_tokenizer()
    masked = _build_copy_id_mask(tok)
    for s in ("|T", "|A", "|f", "|E"):
        if s in tok.word2id:
            assert int(tok.word2id[s]) in masked, f"{s} not in copy mask"


def test_build_copy_id_mask_excludes_plain_english():
    tok = _make_tokenizer()
    masked = _build_copy_id_mask(tok)
    for s in ("the", "a", "thought"):
        if s in tok.word2id:
            assert int(tok.word2id[s]) not in masked, f"{s} wrongly masked"


# ---------------------------------------------------------------------------
# Single-record ablation run
# ---------------------------------------------------------------------------

def test_run_decode_ablations_one_returns_all_modes():
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok = _tiny_model()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    rec = {
        "id": "test",
        "prompt_text": "Describe.",
        "reply_text": "A thought in the arena.",
        "cas_expression": "^0^C",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "state_literal",
    }
    out = run_decode_ablations_one(
        model, rec, collator, tok, device=torch.device("cpu"), max_new_tokens=8,
    )
    for mode in ABLATION_MODES:
        assert mode in out, f"missing mode {mode}"
        # Each mode produces a dict with text + n_tokens_generated
        assert "text" in out[mode] or "error" in out[mode]


def test_decoder_phrase_bias_alpha_restored_after_run():
    """After running all 4 ablations, decoder.phrase_bias_alpha must
    equal its pre-run value (regression: a stale 0.0 would corrupt the
    next forward pass)."""
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok = _tiny_model()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    pre = model.decoder.phrase_bias_alpha.data.clone()
    rec = {
        "id": "test",
        "prompt_text": "x",
        "reply_text": "y",
        "cas_expression": "z",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "binary_composition",
    }
    _ = run_decode_ablations_one(
        model, rec, collator, tok, device=torch.device("cpu"), max_new_tokens=4,
    )
    post = model.decoder.phrase_bias_alpha.data
    assert torch.equal(pre, post), (
        "decoder.phrase_bias_alpha leaked after ablation context"
    )


# ---------------------------------------------------------------------------
# Pack-level ablation
# ---------------------------------------------------------------------------

def test_run_decode_ablations_pack_summary_shape():
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok = _tiny_model()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    # Use a smaller subset for speed
    pack = canary_pack()[:3]
    out = run_decode_ablations_pack(
        model, pack, collator, tok,
        device=torch.device("cpu"), max_new_tokens=4,
    )
    assert set(out["modes"]) == set(ABLATION_MODES)
    for mode in ABLATION_MODES:
        verdict = out["summary_by_mode"][mode]
        assert verdict.get("verdict") in ("clean", "warn", "kill")
        assert verdict.get("n") == 3
    assert len(out["per_record"]) == 3


def test_model_train_mode_restored_after_pack_ablation():
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    model, tok = _tiny_model()
    collator = SimplexCollator(tok, enable_simplex_aux=True)
    model.train()
    _ = run_decode_ablations_pack(
        model, canary_pack()[:2], collator, tok,
        device=torch.device("cpu"), max_new_tokens=4,
    )
    assert model.training, "ablation harness left model in eval mode"
