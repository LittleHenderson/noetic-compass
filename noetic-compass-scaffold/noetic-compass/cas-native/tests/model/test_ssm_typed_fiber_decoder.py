"""Tests for SsmTypedFiberDecoder (Candidate D, 2026-05-12).

Verifies:
  - SSM module imports and instantiates with defaults.
  - Forward returns the same dict shape as TypedFiberDecoder.
  - Backward succeeds; no NaN in any output or loss.
  - SsmTypedFiberDecoderConfig.from_transformer_config preserves the
    shared fields.
  - Trainer --decoder-arch ssm builds an SSM decoder.
  - d1/d2/d3 ablation presets zero the same losses as b1/b2/b3.
"""
from __future__ import annotations

import torch


def _tiny_ssm_cfg():
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoderConfig
    return SsmTypedFiberDecoderConfig(
        vocab_size_english=128, d_model=32, n_heads=4, ffn_dim=64,
        n_layers=2, dropout=0.0, d_state=8, d_conv=4, expand=2,
    )


def _tiny_inputs(vocab_size=128, B=2, L_out=8, L_src=6, d_model=32):
    return {
        "decoder_input_ids": torch.randint(1, vocab_size, (B, L_out)),
        "source_hidden": torch.randn(B, L_src, d_model),
        "simplex_trajectory": torch.ones(B, L_src, 40) / 40.0,
        "src_ids": torch.randint(1, vocab_size, (B, L_src)),
        "src_token_type": torch.zeros(B, L_src, dtype=torch.int8),
        "src_padding_mask": torch.ones(B, L_src, dtype=torch.bool),
        "target_typed_positions": torch.zeros(B, L_out, dtype=torch.int8),
    }


def test_ssm_decoder_imports_and_instantiates():
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    model = SsmTypedFiberDecoder(_tiny_ssm_cfg())
    assert sum(p.numel() for p in model.parameters()) > 0


def test_ssm_decoder_forward_returns_required_keys_and_shapes():
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    model = SsmTypedFiberDecoder(_tiny_ssm_cfg())
    inp = _tiny_inputs()
    out = model(**inp)
    assert set(out.keys()) == {
        "lm_logits", "slot_type_logits", "p_copy",
        "copy_source_indices", "decoder_hidden_state",
    }
    assert out["lm_logits"].shape == (2, 8, 128)
    assert out["slot_type_logits"].shape == (2, 8, 9)
    assert out["p_copy"].shape == (2, 8, 6)
    assert out["copy_source_indices"].shape == (2, 8)
    assert out["copy_source_indices"].dtype == torch.int16
    assert out["decoder_hidden_state"].shape == (2, 8, 32)


def test_ssm_decoder_backward_no_nan():
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    model = SsmTypedFiberDecoder(_tiny_ssm_cfg())
    inp = _tiny_inputs()
    out = model(**inp)
    loss = (
        out["lm_logits"].sum()
        + out["slot_type_logits"].sum()
        + out["p_copy"].sum()
    )
    loss.backward()
    assert not torch.isnan(loss), "loss must be finite"
    # Confirm at least some parameters got nonzero grads
    grad_norms = [
        p.grad.abs().sum().item()
        for p in model.parameters() if p.grad is not None
    ]
    assert any(g > 0 for g in grad_norms), "no gradient flow"


def test_ssm_decoder_p_copy_is_normalized():
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    model = SsmTypedFiberDecoder(_tiny_ssm_cfg())
    model.eval()
    inp = _tiny_inputs()
    with torch.no_grad():
        out = model(**inp)
    # p_copy should sum to 1 across the source-position axis (or 0 when
    # every source position is masked, which doesn't happen in this fixture)
    s = out["p_copy"].sum(dim=-1)
    assert torch.allclose(s, torch.ones_like(s), atol=1e-4), s


def test_ssm_cfg_from_transformer_preserves_shared_fields():
    from cas_native.model.typed_fiber_decoder import TypedFiberDecoderConfig
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoderConfig
    tcfg = TypedFiberDecoderConfig(
        vocab_size_english=100, d_model=64, n_heads=8, ffn_dim=256,
        n_layers=4, dropout=0.1, pad_token_id=0, tie_lm_head=False,
    )
    scfg = SsmTypedFiberDecoderConfig.from_transformer_config(tcfg)
    assert scfg.vocab_size_english == 100
    assert scfg.d_model == 64
    assert scfg.n_heads == 8
    assert scfg.ffn_dim == 256
    assert scfg.n_layers == 4
    assert scfg.dropout == 0.1
    assert scfg.tie_lm_head is False


def test_trainer_decoder_arch_ssm_flag_parses():
    from cas_native.training.train_simplex_mvp import parse_args
    cfg = parse_args([
        "--data-path", "x", "--output-dir", "y",
        "--decoder-arch", "ssm",
    ])
    assert cfg.decoder_arch == "ssm"


def test_trainer_decoder_arch_default_is_transformer():
    from cas_native.training.train_simplex_mvp import parse_args
    cfg = parse_args(["--data-path", "x", "--output-dir", "y"])
    assert cfg.decoder_arch == "transformer"


def test_trainer_rejects_unknown_decoder_arch():
    import pytest
    from cas_native.training.train_simplex_mvp import build_parser
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "--data-path", "x", "--output-dir", "y",
            "--decoder-arch", "bogus",
        ])


def test_ablation_presets_d1_d2_d3_mirror_b1_b2_b3():
    from cas_native.training.train_simplex_mvp import ABLATION_OVERRIDES
    assert ABLATION_OVERRIDES["d1"] == ABLATION_OVERRIDES["b1"]
    assert ABLATION_OVERRIDES["d2"] == ABLATION_OVERRIDES["b2"]
    assert ABLATION_OVERRIDES["d3"] == ABLATION_OVERRIDES["b3"]


def test_build_simplex_mvp_model_dispatches_to_ssm_decoder():
    """When --decoder-arch ssm, build_simplex_mvp_model should construct
    an SsmTypedFiberDecoder as model.decoder."""
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    cfg = SimplexTrainConfig(
        data_path="x", output_dir="y",
        d_model=32, encoder_n_layers=2, decoder_n_layers=2,
        encoder_n_heads=4, decoder_n_heads=4,
        batch_size=2,
        decoder_arch="ssm",
        ssm_d_state=8, ssm_d_conv=4, ssm_expand=2,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    model = build_simplex_mvp_model(cfg, vocab_size=128, vocab_size_english=128)
    assert isinstance(model.decoder, SsmTypedFiberDecoder)


def test_build_simplex_mvp_model_default_still_uses_transformer():
    """Backward compatibility: omitting --decoder-arch builds the
    transformer decoder, same as before Candidate D."""
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.model.typed_fiber_decoder import TypedFiberDecoder
    cfg = SimplexTrainConfig(
        data_path="x", output_dir="y",
        d_model=32, encoder_n_layers=2, decoder_n_layers=2,
        encoder_n_heads=4, decoder_n_heads=4,
        batch_size=2,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    model = build_simplex_mvp_model(cfg, vocab_size=128, vocab_size_english=128)
    assert isinstance(model.decoder, TypedFiberDecoder)


def test_ssm_decoder_causality_does_not_leak_future_into_past():
    """Causality: changing decoder_input_ids at position t should not
    change the output at positions < t. The SSM scan is sequential, so
    this is structurally guaranteed; this test pins the contract."""
    from cas_native.model.ssm_typed_fiber_decoder import SsmTypedFiberDecoder
    torch.manual_seed(42)
    model = SsmTypedFiberDecoder(_tiny_ssm_cfg())
    model.eval()
    inp_a = _tiny_inputs()
    inp_b = {k: (v.clone() if torch.is_tensor(v) else v) for k, v in inp_a.items()}
    # Perturb only the last decoder_input_ids position
    inp_b["decoder_input_ids"][:, -1] = (inp_b["decoder_input_ids"][:, -1] + 7) % 128
    with torch.no_grad():
        out_a = model(**inp_a)
        out_b = model(**inp_b)
    # Hidden states at positions 0..L-2 must be identical
    diff = (out_a["decoder_hidden_state"][:, :-1, :]
            - out_b["decoder_hidden_state"][:, :-1, :]).abs().max().item()
    assert diff < 1e-5, f"causality violation: max diff = {diff}"
