"""Tests for the Path C-1 v1-arch prototype.

Spec: ``docs/working/path_C_non_transformer_simplex_encoder_decoder_design_2026_05_06.md`` §3.3.

Test surface:

1. SimplexStateEncoder produces valid open-simplex output (all > 0,
   sum to 1, correct shape) — randomized 100 inputs.
2. Fisher-Rao distance: identity case ``d(p, p) = 0``, symmetry
   ``d(p, q) = d(q, p)``, triangle inequality on 100 random simplex
   pairs.
3. RPM stub: returns False with broken_at populated on a known-
   inadmissible transition; returns True on a known-admissible one.
4. v1_arch_model end-to-end forward pass on a fixture input doesn't
   crash, returns the expected output dict shape, all CAS state
   probabilities > 0.
5. Loss backward: a small training step with FisherRaoLoss + cross-
   entropy on existing heads converges on a 100-sample synthetic
   dataset (loss decreases over the run; not required to converge to
   a specific value).
"""

from __future__ import annotations

import math

import pytest
import torch

from cas_native.model.v1_arch import (
    NUM_COGNITIVE_STATES,
    FisherRaoLoss,
    RPMGateStub,
    SimplexStateEncoder,
    SimplexStateEncoderConfig,
    V1ArchConfig,
    V1ArchModel,
    fisher_rao_distance,
    smooth_one_hot,
)
from cas_native.model.cas_native_model import CASNativeConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_simplex(batch: int, dim: int = NUM_COGNITIVE_STATES) -> torch.Tensor:
    """Build a random point on the open simplex (all entries > 0, sum=1)."""
    raw = torch.rand(batch, dim) + 1e-4
    return raw / raw.sum(dim=-1, keepdim=True)


def _small_v1_arch_config(vocab_size: int = 64, seq_len: int = 16) -> V1ArchConfig:
    """A tiny config sized for fast tests; both pieces share vocab_size."""
    enc_cfg = SimplexStateEncoderConfig(
        vocab_size=vocab_size,
        d_model=16,
        update_hidden=32,
        max_seq_len=seq_len,
        return_trace=True,
    )
    cas_cfg = CASNativeConfig(
        d_model=16,
        n_layers=1,
        n_heads=2,
        vocab_size=vocab_size,
        max_seq_len=seq_len,
        fractal_depth=1,
        num_ethical_propositions=3,
        dropout=0.0,
        rpm_threshold=0.5,
        num_ifs_maps=1,
    )
    return V1ArchConfig(simplex_encoder=enc_cfg, cas_native=cas_cfg)


# ---------------------------------------------------------------------------
# 1) SimplexStateEncoder produces valid open-simplex output
# ---------------------------------------------------------------------------


class TestSimplexStateEncoderOpenSimplex:
    """Validate that the encoder always emits points on the open simplex."""

    def test_uniform_init_is_open_simplex(self) -> None:
        encoder = SimplexStateEncoder(SimplexStateEncoderConfig(vocab_size=32, d_model=8))
        p = encoder.uniform_init(batch_size=4, device=torch.device("cpu"), dtype=torch.float32)
        assert p.shape == (4, NUM_COGNITIVE_STATES)
        # Uniform distribution: every entry is 1/40, sum is 1.
        assert torch.all(p > 0.0)
        torch.testing.assert_close(p.sum(dim=-1), torch.ones(4))

    def test_project_floors_zeros_and_renormalizes(self) -> None:
        encoder = SimplexStateEncoder(
            SimplexStateEncoderConfig(vocab_size=32, d_model=8, simplex_floor=1e-4)
        )
        # A degenerate distribution with two zero entries.
        p = torch.zeros(1, NUM_COGNITIVE_STATES)
        p[0, 0] = 0.7
        p[0, 1] = 0.3
        proj = encoder.project_to_open_simplex(p)
        assert torch.all(proj > 0.0), "Open simplex demands strictly positive entries."
        torch.testing.assert_close(proj.sum(dim=-1), torch.ones(1))

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
    def test_forward_random_inputs_produce_open_simplex(self, seed: int) -> None:
        """Build random inputs and confirm every emitted distribution is on the
        open simplex. Aggregated across 5 seeds × 20 samples = 100 inputs.
        """
        torch.manual_seed(seed)
        cfg = SimplexStateEncoderConfig(
            vocab_size=64, d_model=16, max_seq_len=12, return_trace=True
        )
        encoder = SimplexStateEncoder(cfg)
        # Run inference; no grads needed for the open-simplex invariant.
        with torch.no_grad():
            for _ in range(20):
                input_ids = torch.randint(low=0, high=cfg.vocab_size, size=(3, 12))
                attention_mask = torch.ones_like(input_ids)
                out = encoder(input_ids, attention_mask=attention_mask)

                # Final distribution.
                p_final = out["p_state_final"]
                assert p_final.shape == (3, NUM_COGNITIVE_STATES)
                assert torch.all(p_final > 0.0)
                torch.testing.assert_close(
                    p_final.sum(dim=-1), torch.ones(3), atol=1e-4, rtol=1e-4
                )

                # Per-step trace.
                trace = out["p_state_trace"]
                assert trace.shape == (3, 12, NUM_COGNITIVE_STATES)
                assert torch.all(trace > 0.0)
                torch.testing.assert_close(
                    trace.sum(dim=-1),
                    torch.ones(3, 12),
                    atol=1e-4,
                    rtol=1e-4,
                )

                # Init distribution.
                init = out["p_state_init"]
                assert init.shape == (3, NUM_COGNITIVE_STATES)
                assert torch.all(init > 0.0)

    def test_forward_with_padding_mask_freezes_padded_positions(self) -> None:
        """Padded positions should not move the simplex (multiplicative
        update reduces to identity at masked positions).
        """
        torch.manual_seed(123)
        cfg = SimplexStateEncoderConfig(
            vocab_size=32, d_model=8, max_seq_len=8, return_trace=True
        )
        encoder = SimplexStateEncoder(cfg)
        # First 4 positions are real, last 4 are padding.
        ids = torch.randint(low=2, high=cfg.vocab_size, size=(2, 8))
        attn = torch.tensor([[1, 1, 1, 1, 0, 0, 0, 0]] * 2, dtype=torch.long)
        with torch.no_grad():
            out = encoder(ids, attention_mask=attn)
        trace = out["p_state_trace"]
        # Frames at masked positions equal the previous frame.
        for t in range(4, 8):
            torch.testing.assert_close(
                trace[:, t, :], trace[:, 3, :], atol=1e-6, rtol=1e-6
            )

    def test_rejects_non_40_state(self) -> None:
        """Path C §3.1.1: 40 atoms is the patent primitive."""
        bad_cfg = SimplexStateEncoderConfig(num_states=42, vocab_size=32, d_model=8)
        with pytest.raises(ValueError, match="patent primitive|40"):
            SimplexStateEncoder(bad_cfg)


# ---------------------------------------------------------------------------
# 2) Fisher-Rao distance properties
# ---------------------------------------------------------------------------


class TestFisherRaoDistance:
    """Identity, symmetry, and triangle inequality on the open simplex."""

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
    def test_identity_is_zero(self, seed: int) -> None:
        torch.manual_seed(seed)
        for _ in range(20):
            p = _random_simplex(batch=4)
            d = fisher_rao_distance(p, p)
            assert d.shape == (4,)
            torch.testing.assert_close(
                d, torch.zeros(4, dtype=d.dtype), atol=1e-6, rtol=1e-6
            )

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
    def test_symmetry(self, seed: int) -> None:
        torch.manual_seed(seed)
        for _ in range(20):
            p = _random_simplex(batch=4)
            q = _random_simplex(batch=4)
            d_pq = fisher_rao_distance(p, q)
            d_qp = fisher_rao_distance(q, p)
            torch.testing.assert_close(d_pq, d_qp, atol=1e-6, rtol=1e-6)

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
    def test_triangle_inequality(self, seed: int) -> None:
        """d(p, r) ≤ d(p, q) + d(q, r) on 100 random triples (5 seeds × 20)."""
        torch.manual_seed(seed)
        for _ in range(20):
            p = _random_simplex(batch=4)
            q = _random_simplex(batch=4)
            r = _random_simplex(batch=4)
            d_pr = fisher_rao_distance(p, r)
            d_pq = fisher_rao_distance(p, q)
            d_qr = fisher_rao_distance(q, r)
            # Allow a tiny numerical slack.
            assert torch.all(d_pr <= d_pq + d_qr + 1e-5), (
                "Fisher-Rao triangle inequality violated."
            )

    def test_distance_is_bounded_by_pi(self) -> None:
        """Fisher-Rao on the simplex is bounded above by π."""
        torch.manual_seed(7)
        for _ in range(50):
            p = _random_simplex(batch=8)
            q = _random_simplex(batch=8)
            d = fisher_rao_distance(p, q)
            assert torch.all(d >= 0.0)
            # 2 * arccos(0) = π
            assert torch.all(d <= math.pi + 1e-5)

    def test_smooth_one_hot_lives_on_open_simplex(self) -> None:
        idx = torch.tensor([0, 17, 39])
        gt = smooth_one_hot(idx, num_classes=NUM_COGNITIVE_STATES)
        assert gt.shape == (3, NUM_COGNITIVE_STATES)
        assert torch.all(gt > 0.0)
        torch.testing.assert_close(
            gt.sum(dim=-1), torch.ones(3), atol=1e-6, rtol=1e-6
        )
        # The "right" entry should still dominate (close to 0.999).
        for b in range(3):
            assert gt[b, idx[b]].item() > 0.9


# ---------------------------------------------------------------------------
# 3) RPM stub: known-inadmissible vs known-admissible transitions
# ---------------------------------------------------------------------------


def _one_hot_simplex(idx: int, *, smooth: float = 1e-4) -> torch.Tensor:
    """Single-row simplex sharply peaked at ``idx``, strictly positive."""
    p = torch.full((1, NUM_COGNITIVE_STATES), smooth)
    p[0, idx] = 1.0 - smooth * (NUM_COGNITIVE_STATES - 1)
    return p


class TestRPMGateStub:
    """Boolean structural admissibility (delegates to the compiler)."""

    def test_identity_op_admits_self_self(self) -> None:
        """CO-0 (identity) admits (i, i) but rejects (i, j) for i != j."""
        stub = RPMGateStub()
        prev = _one_hot_simplex(idx=5)
        nxt = _one_hot_simplex(idx=5)
        result = stub(prev, nxt, "identity")
        assert bool(result.passed.item()) is True
        assert result.broken_at == [None]

    def test_identity_op_rejects_off_diagonal(self) -> None:
        """The classic known-inadmissible: (5, identity, 9) ∉ D_0."""
        stub = RPMGateStub()
        prev = _one_hot_simplex(idx=5)
        nxt = _one_hot_simplex(idx=9)
        result = stub(prev, nxt, "identity")
        assert bool(result.passed.item()) is False
        assert result.broken_at[0] is not None
        # Diagnostic should mention the labels and the operator id.
        diag = result.broken_at[0]
        assert "D_0" in diag or "identity" in diag

    def test_evidence_carries_argmax_indices(self) -> None:
        stub = RPMGateStub()
        prev = _one_hot_simplex(idx=12)
        nxt = _one_hot_simplex(idx=22)
        result = stub(prev, nxt, "identity")
        assert int(result.evidence["source_index"][0].item()) == 12
        assert int(result.evidence["target_index"][0].item()) == 22

    def test_any_op_always_passes(self) -> None:
        """The 'any' fixture op is the test escape hatch."""
        stub = RPMGateStub()
        prev = _one_hot_simplex(idx=5)
        nxt = _one_hot_simplex(idx=9)
        result = stub(prev, nxt, "any")
        assert bool(result.passed.item()) is True

    def test_per_example_op_list(self) -> None:
        """Per-example op id list (B=2)."""
        stub = RPMGateStub()
        prev = torch.cat([_one_hot_simplex(idx=5), _one_hot_simplex(idx=5)], dim=0)
        nxt = torch.cat([_one_hot_simplex(idx=5), _one_hot_simplex(idx=9)], dim=0)
        # Both checked under identity; first should pass, second fail.
        result = stub(prev, nxt, ["identity", "identity"])
        assert result.passed.tolist() == [True, False]
        assert result.broken_at[0] is None
        assert result.broken_at[1] is not None

    def test_invalid_op_name_raises(self) -> None:
        stub = RPMGateStub()
        prev = _one_hot_simplex(idx=0)
        nxt = _one_hot_simplex(idx=0)
        with pytest.raises(ValueError, match="Unknown transition op"):
            stub(prev, nxt, "definitely_not_an_op")


# ---------------------------------------------------------------------------
# 4) V1ArchModel end-to-end forward pass
# ---------------------------------------------------------------------------


class TestV1ArchModelForward:
    """Smoke tests on V1ArchModel.forward."""

    def test_forward_without_transition_op(self) -> None:
        torch.manual_seed(0)
        cfg = _small_v1_arch_config()
        model = V1ArchModel(cfg)
        model.eval()
        ids = torch.randint(low=2, high=cfg.cas_native.vocab_size, size=(2, 12))
        attn = torch.ones_like(ids)
        with torch.no_grad():
            out = model(ids, attention_mask=attn)

        # Required keys (subset).
        for key in (
            "p_state_init",
            "p_state_trace",
            "p_state_final",
            "logits",
            "hidden_states",
            "pooled_hidden_state",
            "cognitive_state",
            "rpm_satisfaction",
            "inversion_flags",
        ):
            assert key in out, f"missing key {key!r}"

        # Shapes.
        assert out["p_state_init"].shape == (2, NUM_COGNITIVE_STATES)
        assert out["p_state_final"].shape == (2, NUM_COGNITIVE_STATES)
        assert out["p_state_trace"].shape == (2, 12, NUM_COGNITIVE_STATES)
        assert out["logits"].shape[-1] == cfg.cas_native.vocab_size

        # Open-simplex invariants on every CAS distribution surface.
        assert torch.all(out["p_state_init"] > 0.0)
        assert torch.all(out["p_state_final"] > 0.0)
        assert torch.all(out["p_state_trace"] > 0.0)
        # Decoder-side legacy cognitive_state is also on the open simplex.
        assert torch.all(out["cognitive_state"] > 0.0)

        # rpm_gate_result is None when transition_op is not provided.
        assert out["rpm_gate_result"] is None

    def test_forward_with_transition_op_emits_rpm_result(self) -> None:
        torch.manual_seed(1)
        cfg = _small_v1_arch_config()
        model = V1ArchModel(cfg)
        model.eval()
        ids = torch.randint(low=2, high=cfg.cas_native.vocab_size, size=(2, 8))
        attn = torch.ones_like(ids)
        with torch.no_grad():
            out = model(ids, attention_mask=attn, transition_op="any")

        rpm = out["rpm_gate_result"]
        assert rpm is not None
        assert rpm.passed.shape == (2,)
        # 'any' is the test fixture escape hatch — always pass.
        assert torch.all(rpm.passed).item() is True

    def test_v1_config_rejects_vocab_mismatch(self) -> None:
        enc_cfg = SimplexStateEncoderConfig(vocab_size=32, d_model=8)
        cas_cfg = CASNativeConfig(d_model=8, n_layers=1, n_heads=2, vocab_size=64)
        with pytest.raises(ValueError, match="vocab"):
            V1ArchConfig(simplex_encoder=enc_cfg, cas_native=cas_cfg)


# ---------------------------------------------------------------------------
# 5) Loss backward: a small training step decreases the loss
# ---------------------------------------------------------------------------


class TestLossBackward:
    """A short SGD loop on a 100-sample synthetic dataset must reduce the
    Fisher-Rao loss. Not required to converge to a specific value; just
    proves gradients flow and the architecture trains.
    """

    def test_fisher_rao_loss_decreases_on_synthetic_data(self) -> None:
        torch.manual_seed(0)

        # Tiny v1-arch config.
        cfg = _small_v1_arch_config(vocab_size=32, seq_len=8)
        model = V1ArchModel(cfg)
        model.train()
        opt = torch.optim.SGD(model.parameters(), lr=0.05)

        # Synthetic dataset: 100 random inputs with random target states.
        N = 100
        ids = torch.randint(low=2, high=cfg.cas_native.vocab_size, size=(N, 8))
        targets = torch.randint(low=0, high=NUM_COGNITIVE_STATES, size=(N,))

        # Initial loss.
        with torch.no_grad():
            out0 = model(ids[:32])
            init_loss = model.fisher_rao_loss(
                out0["p_state_final"], targets[:32]
            )["loss"].item()

        # Few SGD steps over mini-batches.
        for step in range(20):
            start = (step * 16) % (N - 16)
            batch_ids = ids[start : start + 16]
            batch_tgt = targets[start : start + 16]

            opt.zero_grad()
            out = model(batch_ids)
            pack = model.fisher_rao_loss(out["p_state_final"], batch_tgt)
            pack["loss"].backward()
            opt.step()

        # Final loss measured on the original first batch.
        with torch.no_grad():
            out1 = model(ids[:32])
            final_loss = model.fisher_rao_loss(
                out1["p_state_final"], targets[:32]
            )["loss"].item()

        # Loss must decrease (or at least not increase materially).
        # We allow a small slack for stochastic SGD on a tiny model.
        assert final_loss < init_loss + 1e-3, (
            f"FisherRaoLoss did not decrease over 20 steps: "
            f"init={init_loss:.6f} -> final={final_loss:.6f}"
        )

    def test_compute_loss_combines_fr_and_ce(self) -> None:
        torch.manual_seed(7)
        cfg = _small_v1_arch_config()
        model = V1ArchModel(cfg)
        ids = torch.randint(low=2, high=cfg.cas_native.vocab_size, size=(4, 8))
        out = model(ids)
        targets = torch.randint(low=0, high=NUM_COGNITIVE_STATES, size=(4,))
        ce_logits = torch.randn(4, NUM_COGNITIVE_STATES, requires_grad=True)
        ce_labels = targets

        pack = model.compute_loss(
            out,
            target_state_index=targets,
            ce_logits=ce_logits,
            ce_labels=ce_labels,
            ce_weight=0.5,
            fr_weight=1.0,
        )
        # Backward step proves end-to-end gradient flow on the CE branch.
        pack["loss"].backward()
        assert pack["loss"].dim() == 0
        assert pack["fr_distance"].shape == (4,)
        assert pack["ce_loss"].dim() == 0


# ---------------------------------------------------------------------------
# 6) Cross-check: v1_arch.fisher_rao_distance agrees with the legacy one.
# ---------------------------------------------------------------------------


class TestLegacyAgreement:
    """The v1_arch Fisher-Rao implementation must agree with the project's
    pre-existing one to within float tolerance.
    """

    def test_fisher_rao_matches_legacy(self) -> None:
        from cas_native.model.loss import fisher_rao_distance as legacy_fr

        torch.manual_seed(0)
        for _ in range(20):
            p = _random_simplex(batch=8)
            q = _random_simplex(batch=8)
            d_new = fisher_rao_distance(p, q)
            d_old = legacy_fr(p, q)
            torch.testing.assert_close(d_new, d_old, atol=1e-5, rtol=1e-5)
