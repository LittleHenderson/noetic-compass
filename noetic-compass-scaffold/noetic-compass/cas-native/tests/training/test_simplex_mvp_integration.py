"""Stage 3 integration tests for the simplex MVP trainer.

Exercises the full loss assembly together (encoder + decoder + Fisher-Rao +
slot_type + copy + phrase_bias_aux + collator-derived anchors), confirms
gradients land where expected, train_progress JSON fields are present,
and ablation modes switch loss weights correctly.

Also re-exercises the Stage 2 all-PAD/NaN fixes under the full loss
assembly — the user-named "Stage 3 should prove those remain stable once
the full loss assembly is exercised together."
"""
from __future__ import annotations

import json

import pytest
import torch

from cas_native.training.train_simplex_mvp import (
    ABLATION_OVERRIDES,
    DEFAULT_LOSS_WEIGHTS,
    SimplexTrainConfig,
    build_parser,
    compute_grad_norm,
    compute_losses,
    parse_args,
    run_integration_step,
    synthetic_records,
)


def _tiny_cfg(ablation: str = "full") -> SimplexTrainConfig:
    """Tiny CPU config for integration tests — fast enough for CI."""
    cfg = SimplexTrainConfig(
        data_path=":synthetic:",
        output_dir="/tmp/simplex_mvp_test_unused",
        epochs=1,
        batch_size=4,
        lr=1e-4,
        weight_decay=1e-4,
        grad_clip=1.0,
        device="cpu",
        smoke_test=True,
        smoke_records=4,
        d_model=32,
        encoder_n_layers=2,
        encoder_n_heads=4,
        decoder_n_layers=2,
        decoder_n_heads=4,
        ablation=ablation,
        seed=1729,
    )
    overrides = ABLATION_OVERRIDES.get(ablation, {})
    cfg.loss_weights = {**DEFAULT_LOSS_WEIGHTS, **overrides}
    return cfg


# ---------------------------------------------------------------------------
# 1. End-to-end one-step forward + backward + optim works
# ---------------------------------------------------------------------------

def test_one_step_forward_backward_runs_without_crash(tmp_path):
    cfg = _tiny_cfg()
    result = run_integration_step(
        cfg, synthetic_records(4), output_path=tmp_path / "trainer_log.jsonl",
    )
    assert result["loss_total"] > 0
    # train_progress was written
    log_path = tmp_path / "trainer_log.jsonl"
    assert log_path.exists()
    contents = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(contents) >= 1
    record = json.loads(contents[-1])
    assert record["event"] == "train_progress"


def test_loss_total_is_finite_and_positive():
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    assert torch.isfinite(torch.tensor(result["loss_total"]))
    assert result["loss_total"] > 0


# ---------------------------------------------------------------------------
# 2. Gradients exist where expected (encoder + decoder both)
# ---------------------------------------------------------------------------

def test_gradients_flow_into_encoder_and_decoder():
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    # After backward, optim.step has been called — grads were computed.
    # The norms we captured BEFORE the clip step must be positive.
    assert result["grad_norm_encoder"] > 0, "no gradient flow into encoder"
    assert result["grad_norm_decoder"] > 0, "no gradient flow into decoder"


def test_fisher_rao_loss_propagates_gradients_to_simplex_tail():
    """L_FR(simplex_trajectory, target, mask) must contribute gradients to
    the encoder tail (mirror-descent layers) when anchor mask is non-empty."""
    cfg = _tiny_cfg(ablation="lm_fr")  # only LM + FR active
    result = run_integration_step(cfg, synthetic_records(4))
    # With lm_fr ablation, slot/copy/phrase weights are zero; the only path
    # to encoder gradient is through L_LM (via cross-attn) or L_FR (via
    # simplex_trajectory). Either should produce non-zero grads on the
    # encoder tail.
    enc = result["model"].encoder
    tail_grad_norm = compute_grad_norm(enc.tail.parameters())
    assert tail_grad_norm > 0, "tail received no gradient under lm_fr ablation"


# ---------------------------------------------------------------------------
# 3. train_progress JSON fields are all present
# ---------------------------------------------------------------------------

def test_train_progress_json_has_required_fields(tmp_path):
    cfg = _tiny_cfg()
    _ = run_integration_step(
        cfg, synthetic_records(4), output_path=tmp_path / "log.jsonl",
    )
    line = (tmp_path / "log.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]
    rec = json.loads(line)
    required = {
        "event",
        "epoch", "batch", "batches_per_epoch", "global_step",
        "elapsed_sec", "batches_per_sec", "eta_epoch_min", "lr_now",
        "grad_norm_encoder", "grad_norm_decoder",
        # Loss parts (5 individual + total)
        "loss_total", "loss_lm", "loss_fr", "loss_slot_type", "loss_copy",
        "loss_phrase_bias_aux",
        # Fisher-Rao telemetry
        "loss_fr_mean_d", "loss_fr_anchor_count", "loss_fr_pct_within_eps",
        # Simplex telemetry
        "simplex_entropy_mean", "simplex_min_p",
        # Interference monitor
        "fr_lm_ratio",
        # Ablation diagnostic
        "ablation", "loss_weights_active",
    }
    missing = required - set(rec.keys())
    assert not missing, f"train_progress JSON missing fields: {missing}"


def test_train_progress_loss_values_finite():
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    for name, val in result["loss_parts"].items():
        assert torch.isfinite(torch.tensor(val)), f"{name} is non-finite: {val}"


# ---------------------------------------------------------------------------
# 4. Ablation modes switch losses correctly
# ---------------------------------------------------------------------------

def test_ablation_full_keeps_all_weights():
    cfg = _tiny_cfg(ablation="full")
    assert cfg.loss_weights == DEFAULT_LOSS_WEIGHTS


@pytest.mark.parametrize(
    "ablation, zeroed_keys",
    [
        ("lm_fr",      ("slot_type", "copy", "phrase_bias_aux")),
        ("lm_slot",    ("fr",        "copy", "phrase_bias_aux")),
        ("lm_fr_slot", ("copy",      "phrase_bias_aux")),
    ],
)
def test_ablation_zeros_correct_weights(ablation, zeroed_keys):
    cfg = _tiny_cfg(ablation=ablation)
    for key in zeroed_keys:
        assert cfg.loss_weights[key] == 0.0, f"{ablation} should zero {key}"
    # LM is always live in every ablation
    assert cfg.loss_weights["lm"] > 0


def test_lm_fr_ablation_total_loss_reflects_zeros(tmp_path):
    """Under lm_fr, the (weighted) slot/copy/phrase contributions must be 0.
    L_total must equal w_lm·L_LM + w_fr·L_FR exactly."""
    cfg = _tiny_cfg(ablation="lm_fr")
    result = run_integration_step(
        cfg, synthetic_records(4), output_path=tmp_path / "log.jsonl",
    )
    parts = result["loss_parts"]
    # Sanity: weights match
    w = cfg.loss_weights
    assert w["slot_type"] == 0 and w["copy"] == 0 and w["phrase_bias_aux"] == 0
    expected = w["lm"] * parts["loss_lm"] + w["fr"] * parts["loss_fr"]
    # Floating-point tolerance; the parts are detached fp32 scalars.
    assert abs(parts["loss_total"] - expected) < 1e-3, (
        f"lm_fr total {parts['loss_total']} != w_lm·LM + w_fr·FR = {expected}"
    )


# ---------------------------------------------------------------------------
# 5. CLI argument parser exposes ablation + smoke flags
# ---------------------------------------------------------------------------

def test_cli_parser_exposes_ablation_choices():
    parser = build_parser()
    args = parser.parse_args([
        "--data-path", "x", "--output-dir", "y", "--ablation", "lm_slot",
    ])
    assert args.ablation == "lm_slot"


def test_cli_parser_rejects_unknown_ablation():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "--data-path", "x", "--output-dir", "y", "--ablation", "bogus",
        ])


def test_parse_args_applies_ablation_overrides():
    cfg = parse_args([
        "--data-path", "x", "--output-dir", "y", "--ablation", "lm_fr",
    ])
    assert cfg.loss_weights["slot_type"] == 0.0
    assert cfg.loss_weights["copy"] == 0.0
    assert cfg.loss_weights["lm"] == 1.0
    assert cfg.loss_weights["fr"] == 1.0


# ---------------------------------------------------------------------------
# 6. Stage 2 all-PAD/NaN fixes remain stable under the full loss assembly
# ---------------------------------------------------------------------------

def test_all_pad_cas_prefix_does_not_produce_nan_total_loss():
    """Re-exercise the Stage 2 fail-closed contract under the full 5-term
    loss assembly: a batch whose source CAS is entirely PAD must produce a
    finite total loss (so the trainer never halts on a corpus edge case)."""
    cfg = _tiny_cfg()
    # Build a record whose cas_expression is empty so cas_prefix_ids is
    # length-0 — the all-PAD source case.
    records = synthetic_records(4)
    for r in records:
        r["cas_expression"] = ""
    result = run_integration_step(cfg, records)
    assert torch.isfinite(torch.tensor(result["loss_total"])), (
        "all-empty CAS records produced NaN/Inf total loss"
    )
    for k, v in result["loss_parts"].items():
        assert torch.isfinite(torch.tensor(v)), f"{k} non-finite under all-PAD"


def test_malformed_cas_does_not_halt_integration_step():
    """Records with malformed cas_expression must not raise from the
    integration step — collator emits zero anchors, FR loss contributes
    nothing, LM still trains. User-named 'malformed source gives zero/empty
    aux labels without crashing'."""
    cfg = _tiny_cfg()
    records = synthetic_records(4)
    records[0]["cas_expression"] = "!!! malformed garbage @@@"
    records[1]["cas_expression"] = ""
    result = run_integration_step(cfg, records)
    assert result["loss_total"] > 0
    assert result["grad_norm_encoder"] > 0 or result["grad_norm_decoder"] > 0


def test_simplex_min_p_stays_above_zero_under_full_loss():
    """Architecture invariant: even after a real backward + optim step, the
    simplex must remain strictly positive. The mirror-descent + ε-floor
    contract is the load-bearing safety property."""
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    assert result["fr_metrics"]["simplex_min_p"] > 0


def test_anchor_count_positive_for_synthetic_records():
    """Anchor mask must fire on the synthetic Stage 3 records — otherwise
    L_FR contributes 0 and we can't tell if the FR path is plumbed."""
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    assert result["fr_metrics"]["loss_fr_anchor_count"] > 0


# ---------------------------------------------------------------------------
# 7. Loss decomposition matches manual reassembly (defends against
#    bookkeeping bugs in compute_losses)
# ---------------------------------------------------------------------------

def test_loss_total_equals_weighted_sum_of_parts():
    cfg = _tiny_cfg()
    result = run_integration_step(cfg, synthetic_records(4))
    parts = result["loss_parts"]
    w = cfg.loss_weights
    expected = (
        w["lm"] * parts["loss_lm"]
        + w["fr"] * parts["loss_fr"]
        + w["slot_type"] * parts["loss_slot_type"]
        + w["copy"] * parts["loss_copy"]
        + w["phrase_bias_aux"] * parts["loss_phrase_bias_aux"]
    )
    assert abs(parts["loss_total"] - expected) < 1e-3
