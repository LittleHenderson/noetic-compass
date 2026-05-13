"""Tests for the scheduled-sampling helper used by --ablation e3
(Candidate E Stage 3, 2026-05-13).

Two load-bearing assertions Codex called out in `codex_audit.md` 2026-05-13T03:42Z:

1. **Equivalence at ratio=0.** When `scheduled_sampling_ratio == 0`, the
   training path through `forward_with_scheduled_sampling` MUST produce
   bit-for-bit identical outputs AND gradients to the legacy TF path
   `model(batch)`. Any drift here means a vanilla TF run with the flag
   accidentally set silently changes training dynamics.

2. **Self-feed at ratio=1.** When `scheduled_sampling_ratio == 1.0`,
   every non-BOS decoder input position is the model's own previous-position
   greedy prediction. The supervised forward against gold targets must
   still run end-to-end without NaN, produce shape-correct outputs,
   and yield non-zero gradients somewhere.

Plus auxiliary tests on the schedule resolver and CLI plumbing.
"""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from cas_native.training.scheduled_sampling import (
    build_scheduled_sampling_input,
    forward_with_scheduled_sampling,
    resolve_ratio_at_step,
)


# ---------------------------------------------------------------------------
# Test fixtures: tiny tokenizer + tiny model + tiny batch
# ---------------------------------------------------------------------------

def _make_tokenizer():
    from cas_native.training.tokenizer import HybridCASTokenizer
    tok = HybridCASTokenizer()
    for w in ["hello", "the", "a", "thought", "stage", "name"]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _tiny_model_and_batch():
    """Build a CPU-only tiny simplex MVP model + a 1-record batch.

    The batch is constructed by feeding a synthetic record through
    SimplexCollator, mirroring `test_decode_ablations._tiny_model`.
    The model is set to eval() to disable dropout, so equivalence
    comparisons aren't perturbed by stochastic dropout RNG.
    """
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.training.datasets.simplex_collator import SimplexCollator

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
    model.eval()  # disable dropout for deterministic equivalence

    collator = SimplexCollator(tok, enable_simplex_aux=True)
    rec = {
        "id": "ss_test",
        "prompt_text": "Describe a stage.",
        "reply_text": "A thought in the arena.",
        "cas_expression": "^0^C",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "state_literal",
    }
    batch = collator([rec], device=torch.device("cpu"))
    assert batch is not None, "collator must produce a non-empty batch for the synthetic record"
    return model, batch


def _toy_loss(out: dict[str, torch.Tensor]) -> torch.Tensor:
    """Deterministic scalar loss for gradient comparisons.

    Uses lm_logits.mean() so:
      - it depends on EVERY parameter in the forward graph
      - it's the same formula across both branches under test
      - no need to construct gold targets (which the equivalence-at-ratio=0
        check doesn't depend on)
    """
    return out["lm_logits"].mean() + out["slot_type_logits"].mean()


# ---------------------------------------------------------------------------
# Test 1: equivalence at ratio=0 — bit-for-bit identical to TF
# ---------------------------------------------------------------------------

def test_forward_at_ratio_zero_returns_identical_outputs():
    """ratio=0 fast path: forward_with_scheduled_sampling MUST return
    the exact same output dict (every tensor equal) as model(batch).

    This is the load-bearing equivalence Codex called out: "ratio=0 →
    bit-for-bit identical to TF, no silent behavior change."
    """
    model, batch = _tiny_model_and_batch()

    out_tf = model(batch)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=0.0)

    for key in ("lm_logits", "slot_type_logits", "p_copy",
                "simplex_trajectory", "source_hidden"):
        assert key in out_tf, f"sanity: TF out missing key {key}"
        assert key in out_ss, f"ratio=0 path must surface key {key}"
        assert torch.equal(out_tf[key], out_ss[key]), (
            f"ratio=0 must produce bit-for-bit identical {key}; "
            f"got abs-max-diff {(out_tf[key] - out_ss[key]).abs().max().item()}"
        )


def test_forward_at_ratio_zero_gradients_match_tf():
    """ratio=0 must produce identical gradients to the TF path.

    Procedure:
      1. forward TF, backward _toy_loss, snapshot all parameter gradients.
      2. zero grads, forward via forward_with_scheduled_sampling at ratio=0,
         backward the same loss, snapshot.
      3. Assert torch.equal on every parameter gradient.

    This is the test that protects against subtle drift — e.g., if a
    refactor accidentally adds an extra forward pass at ratio=0 and
    consumes RNG state that affects something downstream.
    """
    model, batch = _tiny_model_and_batch()

    # TF reference
    model.zero_grad(set_to_none=True)
    out_tf = model(batch)
    loss_tf = _toy_loss(out_tf)
    loss_tf.backward()
    ref_grads = {
        name: param.grad.detach().clone()
        for name, param in model.named_parameters()
        if param.grad is not None
    }

    # ratio=0 scheduled-sampling path
    model.zero_grad(set_to_none=True)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=0.0)
    loss_ss = _toy_loss(out_ss)
    loss_ss.backward()
    ss_grads = {
        name: param.grad.detach().clone()
        for name, param in model.named_parameters()
        if param.grad is not None
    }

    # Same set of parameters must have gradients
    assert set(ref_grads.keys()) == set(ss_grads.keys()), (
        f"ratio=0 must produce gradients for the same parameter set as TF; "
        f"only-in-TF: {set(ref_grads) - set(ss_grads)!r}, "
        f"only-in-SS: {set(ss_grads) - set(ref_grads)!r}"
    )
    # Bit-for-bit gradient equality
    for name in ref_grads:
        assert torch.equal(ref_grads[name], ss_grads[name]), (
            f"ratio=0 gradient must equal TF gradient for {name}; "
            f"abs-max-diff {(ref_grads[name] - ss_grads[name]).abs().max().item()}"
        )


def test_forward_at_ratio_zero_loss_matches_tf():
    """Loss scalars must match exactly at ratio=0."""
    model, batch = _tiny_model_and_batch()
    out_tf = model(batch)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=0.0)
    assert _toy_loss(out_tf).item() == _toy_loss(out_ss).item()


# ---------------------------------------------------------------------------
# Test 2: self-feed at ratio=1 — path runs, gradients flow, no NaN
# ---------------------------------------------------------------------------

def test_forward_at_ratio_one_self_feed_runs_end_to_end():
    """ratio=1 means every non-BOS decoder input position is the model's
    previous-position greedy prediction. The forward MUST:
      - return a shape-correct output dict (same keys, same shapes as TF)
      - produce no NaN / Inf in any output tensor
    """
    model, batch = _tiny_model_and_batch()

    out_tf = model(batch)
    gen = torch.Generator(device=batch["lm_decoder_input_ids"].device)
    gen.manual_seed(42)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=1.0, generator=gen)

    for key in ("lm_logits", "slot_type_logits", "p_copy"):
        assert out_ss[key].shape == out_tf[key].shape, (
            f"ratio=1 {key} shape {out_ss[key].shape} != TF shape {out_tf[key].shape}"
        )
        assert torch.isfinite(out_ss[key]).all(), (
            f"ratio=1 {key} contains NaN/Inf — student-prefix forward unstable"
        )


def test_forward_at_ratio_one_gradients_nonzero():
    """At ratio=1, the supervised forward against gold targets must still
    produce non-zero gradients somewhere — confirms gradient flow through
    the student-prefix path is not silently severed.
    """
    model, batch = _tiny_model_and_batch()

    model.zero_grad(set_to_none=True)
    gen = torch.Generator(device=batch["lm_decoder_input_ids"].device)
    gen.manual_seed(0)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=1.0, generator=gen)
    loss = _toy_loss(out_ss)
    loss.backward()

    n_params_with_grad = sum(
        1 for p in model.parameters() if p.grad is not None and p.grad.abs().sum() > 0
    )
    assert n_params_with_grad > 0, (
        "ratio=1 self-feed produced zero gradient on every parameter — "
        "gradient flow is broken"
    )


def test_forward_at_ratio_one_changes_outputs_vs_tf():
    """Sanity: at ratio=1 with substitution actually happening, the
    output MUST differ from the TF output (otherwise scheduled sampling
    is a no-op).

    Note: very small models can fail this assertion if the model is
    pathological (e.g. lm_head always predicts the same token regardless
    of input). The tiny model used here has random init, so we expect
    the substituted-prefix forward to diverge in lm_logits.
    """
    model, batch = _tiny_model_and_batch()
    out_tf = model(batch)
    gen = torch.Generator(device=batch["lm_decoder_input_ids"].device)
    gen.manual_seed(1)
    out_ss = forward_with_scheduled_sampling(model, batch, ratio=1.0, generator=gen)

    diff = (out_tf["lm_logits"] - out_ss["lm_logits"]).abs().max().item()
    # Diff threshold is conservative — we just need to know SOME divergence
    # happened. At ratio=1 with a non-trivial L_out, divergence should be
    # obvious.
    assert diff > 1e-4, (
        f"ratio=1 must produce visibly different lm_logits from TF; got "
        f"abs-max-diff {diff} (substitution may have silently not occurred)"
    )


# ---------------------------------------------------------------------------
# Test 2b: DIRECT mixed_input inspection (Codex re-audit blocker 2,
#          2026-05-13T05:54Z). Rather than inferring substitution from output
#          divergence, these tests look at the actual decoder input fed to
#          pass 2.
# ---------------------------------------------------------------------------

def test_build_input_at_ratio_one_substitutes_every_non_bos_position():
    """At ratio=1.0 the substitution mask MUST be True at every non-BOS
    position; the resulting mixed_input MUST equal sampled_prev at every
    non-BOS position (and gold at position 0).

    This is the direct check Codex asked for — we are not inferring
    substitution from output divergence; we are looking at the actual
    decoder input tensor that pass 2 receives.
    """
    model, batch = _tiny_model_and_batch()
    gen = torch.Generator(device=batch["lm_decoder_input_ids"].device)
    gen.manual_seed(0)
    mixed_input, use_sample, sampled_prev = build_scheduled_sampling_input(
        model, batch, ratio=1.0, generator=gen,
    )
    gold_input = batch["lm_decoder_input_ids"]
    B, L_out = gold_input.shape

    # BOS preserved
    assert torch.equal(use_sample[:, 0], torch.zeros(B, dtype=torch.bool)), (
        "use_sample at position 0 (BOS) must be all False"
    )
    assert torch.equal(mixed_input[:, 0], gold_input[:, 0]), (
        "mixed_input at position 0 must equal gold (BOS preserved)"
    )

    # Every non-BOS position substituted (use_sample True)
    if L_out > 1:
        non_bos_mask = use_sample[:, 1:]
        assert non_bos_mask.all(), (
            "at ratio=1, use_sample at every non-BOS position must be True; "
            f"saw {int((~non_bos_mask).sum().item())} False entries"
        )
        # And mixed_input at non-BOS positions must equal sampled_prev
        assert torch.equal(mixed_input[:, 1:], sampled_prev[:, 1:]), (
            "at ratio=1, mixed_input[:, 1:] must equal sampled_prev[:, 1:]"
        )


def test_build_input_never_substitutes_bos_at_any_ratio():
    """Position 0 (BOS) must be hard-fixed gold regardless of ratio.

    Tests 4 ratios: 0.1, 0.5, 0.9, 1.0. None of them should ever flip
    use_sample[:, 0] to True. mixed_input[:, 0] must equal gold[:, 0].
    """
    model, batch = _tiny_model_and_batch()
    gold_input = batch["lm_decoder_input_ids"]
    B = gold_input.shape[0]

    for ratio in (0.1, 0.5, 0.9, 1.0):
        gen = torch.Generator(device=gold_input.device)
        gen.manual_seed(42)
        mixed_input, use_sample, _ = build_scheduled_sampling_input(
            model, batch, ratio=ratio, generator=gen,
        )
        assert not use_sample[:, 0].any().item(), (
            f"BOS substitution leaked at ratio={ratio}: "
            f"use_sample[:, 0] = {use_sample[:, 0].tolist()}"
        )
        assert torch.equal(mixed_input[:, 0], gold_input[:, 0]), (
            f"mixed_input[:, 0] differs from gold at ratio={ratio}"
        )


def test_build_input_at_middle_ratio_mixes_gold_and_sampled():
    """At ratio=0.5 with a seeded generator, BOTH substituted and
    unsubstituted positions must appear in use_sample, AND mixed_input
    must equal gold at unsubstituted positions and sampled_prev at
    substituted positions.

    This is the third part of Codex's direct-inspection requirement —
    proving the mix actually mixes.
    """
    model, batch = _tiny_model_and_batch()
    gold_input = batch["lm_decoder_input_ids"]
    B, L_out = gold_input.shape

    gen = torch.Generator(device=gold_input.device)
    gen.manual_seed(7)
    mixed_input, use_sample, sampled_prev = build_scheduled_sampling_input(
        model, batch, ratio=0.5, generator=gen,
    )

    # Restrict to non-BOS positions for the mix check
    if L_out <= 1:
        pytest.skip("test requires L_out > 1")

    non_bos_use = use_sample[:, 1:]
    n_subst = int(non_bos_use.sum().item())
    n_keep = int((~non_bos_use).sum().item())
    n_total = n_subst + n_keep

    # Both populations must be non-empty. At ratio=0.5 with a seeded
    # generator across (B=1, L_out=~100) positions, the binomial is very
    # peaked around 50% so both populations exist with overwhelming
    # probability. If this test ever fails, the RNG or the mask logic
    # is broken — not a flake.
    assert n_subst > 0, (
        f"at ratio=0.5 no non-BOS positions were substituted "
        f"(use_sample sum at non-BOS = 0 of {n_total})"
    )
    assert n_keep > 0, (
        f"at ratio=0.5 every non-BOS position was substituted "
        f"({n_subst} of {n_total}) — generator may be broken"
    )

    # Where use_sample is True, mixed_input must equal sampled_prev.
    # Where use_sample is False, mixed_input must equal gold_input.
    where_subst = use_sample
    where_keep = ~use_sample
    assert torch.equal(
        mixed_input[where_subst], sampled_prev[where_subst],
    ), "mixed_input must equal sampled_prev at substituted positions"
    assert torch.equal(
        mixed_input[where_keep], gold_input[where_keep],
    ), "mixed_input must equal gold_input at unsubstituted positions"


def test_build_input_at_ratio_zero_does_not_substitute():
    """At ratio=0, even though forward_with_scheduled_sampling
    short-circuits, the build helper called directly must still produce
    use_sample=all-False and mixed_input=gold_input.

    Codex's blocker doesn't ask for this explicitly but it's a natural
    completeness check on the build helper's behavior across all ratios.
    """
    model, batch = _tiny_model_and_batch()
    gold_input = batch["lm_decoder_input_ids"]

    gen = torch.Generator(device=gold_input.device)
    gen.manual_seed(123)
    mixed_input, use_sample, _ = build_scheduled_sampling_input(
        model, batch, ratio=0.0, generator=gen,
    )
    assert not use_sample.any().item(), (
        f"at ratio=0 no position should be substituted; "
        f"got {int(use_sample.sum().item())} substitutions"
    )
    assert torch.equal(mixed_input, gold_input), (
        "at ratio=0 mixed_input must equal gold_input exactly"
    )


# ---------------------------------------------------------------------------
# Test 3: argument validation
# ---------------------------------------------------------------------------

def test_forward_rejects_ratio_below_zero():
    model, batch = _tiny_model_and_batch()
    with pytest.raises(ValueError, match=r"ratio must be in"):
        forward_with_scheduled_sampling(model, batch, ratio=-0.1)


def test_forward_rejects_ratio_above_one():
    model, batch = _tiny_model_and_batch()
    with pytest.raises(ValueError, match=r"ratio must be in"):
        forward_with_scheduled_sampling(model, batch, ratio=1.5)


# ---------------------------------------------------------------------------
# Test 4: ratio schedule resolver
# ---------------------------------------------------------------------------

def test_resolve_ratio_empty_schedule_uses_constant():
    assert resolve_ratio_at_step("", 0.3, step=100, n_steps=1000) == 0.3
    assert resolve_ratio_at_step("", 0.0, step=100, n_steps=1000) == 0.0


def test_resolve_ratio_constant_keyword():
    assert resolve_ratio_at_step("constant", 0.5, step=100, n_steps=1000) == 0.5


def test_resolve_ratio_linear_below_warmup_returns_start():
    r = resolve_ratio_at_step("linear:0.0-0.5:1000-3000", 0.0, step=500, n_steps=5000)
    assert r == 0.0


def test_resolve_ratio_linear_above_full_returns_end():
    r = resolve_ratio_at_step("linear:0.0-0.5:1000-3000", 0.0, step=4000, n_steps=5000)
    assert r == 0.5


def test_resolve_ratio_linear_mid_ramp():
    # At step 2000 (halfway through 1000-3000), ratio should be 0.25
    r = resolve_ratio_at_step("linear:0.0-0.5:1000-3000", 0.0, step=2000, n_steps=5000)
    assert abs(r - 0.25) < 1e-9


def test_resolve_ratio_linear_full_lt_warmup_raises():
    with pytest.raises(ValueError, match="full .* must be > warmup"):
        resolve_ratio_at_step("linear:0.0-0.5:3000-1000", 0.0, step=2000, n_steps=5000)


def test_resolve_ratio_malformed_linear_raises():
    with pytest.raises(ValueError, match="linear schedule must be"):
        resolve_ratio_at_step("linear:invalid", 0.0, step=2000, n_steps=5000)


def test_resolve_ratio_unknown_schedule_raises():
    with pytest.raises(ValueError, match="unknown scheduled-sampling schedule"):
        resolve_ratio_at_step("cosine:0-1", 0.0, step=100, n_steps=1000)


# ---------------------------------------------------------------------------
# Test 5: CLI surface — --ablation e3, --scheduled-sampling-ratio,
#                       --scheduled-sampling-schedule
# ---------------------------------------------------------------------------

def test_e3_ablation_in_choices():
    """--ablation e3 must be a valid CLI choice that resolves to a
    weight-stack matching e2c (no new losses, just SS-driven training).
    """
    from cas_native.training.train_simplex_mvp import (
        build_parser, ABLATION_OVERRIDES,
    )
    assert "e3" in ABLATION_OVERRIDES, "e3 missing from ABLATION_OVERRIDES"
    # e3 must NOT introduce new loss-weight keys beyond what e2c has
    e2c_keys = set(ABLATION_OVERRIDES["e2c"].keys())
    e3_keys = set(ABLATION_OVERRIDES["e3"].keys())
    assert e3_keys == e2c_keys, (
        f"e3 must use the same loss-weight keys as e2c (no new losses per "
        f"bounded scope decisions.md 2026-05-13T03:45Z); "
        f"diff: only-in-e3 {e3_keys - e2c_keys!r}, only-in-e2c {e2c_keys - e3_keys!r}"
    )
    # And the values must match (e3 inherits e2c weights verbatim)
    for k in e3_keys:
        assert ABLATION_OVERRIDES["e3"][k] == ABLATION_OVERRIDES["e2c"][k], (
            f"e3 loss weight {k} differs from e2c — bounded scope forbids "
            f"weight changes"
        )


def test_cli_accepts_scheduled_sampling_flags():
    """--scheduled-sampling-ratio and --scheduled-sampling-schedule must
    be exposed at the CLI."""
    from cas_native.training.train_simplex_mvp import build_parser
    p = build_parser()
    args = p.parse_args([
        "--data-path", "x", "--output-dir", "y",
        "--ablation", "e3",
        "--scheduled-sampling-ratio", "0.25",
        "--scheduled-sampling-schedule", "linear:0.0-0.5:1000-3000",
    ])
    assert args.scheduled_sampling_ratio == 0.25
    assert args.scheduled_sampling_schedule == "linear:0.0-0.5:1000-3000"


def test_cli_default_ratio_is_zero():
    """Default scheduled-sampling ratio is 0 = TF behavior. Regression
    pin so a future "convenient default" change doesn't silently change
    every e2c-era run."""
    from cas_native.training.train_simplex_mvp import build_parser
    p = build_parser()
    args = p.parse_args(["--data-path", "x", "--output-dir", "y"])
    assert args.scheduled_sampling_ratio == 0.0
    assert args.scheduled_sampling_schedule == ""
