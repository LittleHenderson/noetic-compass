"""Tests for :class:`RegisterLatent` — ADR-08 Option E.

Covers:
  - Module instantiation with default + custom hyperparameters
  - Parameter count (5,442 at d=128, r=16 per ADR-08)
  - Zero-init of W output matrices at step 0 (W_gamma/beta for both surfaces)
  - Step-0 identity FiLM: gamma == 1, beta == 0 at both surfaces
  - ``apply_register_40`` / ``apply_register_d`` identity at init + None
  - Per-register divergence after W perturbation
  - Scale parameter accessibility + freeze/unfreeze semantics
  - Involution symmetry from latent level (z_T = -z_E -> gamma/beta involution)
  - Gradient flow through z_R and W output matrices
  - Diagnostic metrics shape + keys
"""

from __future__ import annotations

import pytest
import torch

from cas_native.model.register_film import (
    DEFAULT_LATENT_DIM_R,
    DEFAULT_NUM_STATES,
    DEFAULT_REGISTER_DIM,
    DEFAULT_SCALE_40,
    DEFAULT_SCALE_D,
    DEFAULT_SCALE_WARMUP_STEPS,
    NUM_REGISTERS,
    REGISTER_INDEX,
    RegisterLatent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def latent_default() -> RegisterLatent:
    """RegisterLatent at d=128, r=16 (ADR-08 spec defaults)."""
    return RegisterLatent()


@pytest.fixture
def latent_d64() -> RegisterLatent:
    """RegisterLatent at d=64, r=16 (smaller for fast tests)."""
    return RegisterLatent(d_model=64)


# ---------------------------------------------------------------------------
# Instantiation + parameter count
# ---------------------------------------------------------------------------


class TestInstantiation:

    def test_instantiation_with_defaults(self, latent_default):
        assert latent_default.d_model == DEFAULT_REGISTER_DIM
        assert latent_default.num_states == DEFAULT_NUM_STATES
        assert latent_default.num_registers == NUM_REGISTERS
        assert latent_default.latent_dim_r == DEFAULT_LATENT_DIM_R
        assert latent_default.scale_warmup_steps == DEFAULT_SCALE_WARMUP_STEPS

    def test_instantiation_with_custom_hp(self):
        latent = RegisterLatent(
            d_model=256,
            num_states=50,
            num_registers=5,
            latent_dim_r=32,
            scale_40=0.1,
            scale_d=0.05,
            scale_warmup_steps=500,
        )
        assert latent.d_model == 256
        assert latent.num_states == 50
        assert latent.num_registers == 5
        assert latent.latent_dim_r == 32
        assert float(latent.scale_40.item()) == pytest.approx(0.1)
        assert float(latent.scale_d.item()) == pytest.approx(0.05)
        assert latent.scale_warmup_steps == 500

    def test_parameter_count_5440_at_d128(self):
        """ADR-08: 5,442 parameters at d_model=128 (2 extra from scalar scales).

        Breakdown:
          register_latent : 4 * 16  = 64
          W_gamma_40      : 16 * 40 = 640
          W_beta_40       : 16 * 40 = 640
          W_gamma_d       : 16 * 128 = 2,048
          W_beta_d        : 16 * 128 = 2,048
          scale_40        : 1
          scale_d         : 1
                                    = 5,442
        """
        latent = RegisterLatent(d_model=128)
        expected = (
            4 * 16     # register_latent (z_R)
            + 16 * 40  # W_gamma_40
            + 16 * 40  # W_beta_40
            + 16 * 128 # W_gamma_d
            + 16 * 128 # W_beta_d
            + 1        # scale_40
            + 1        # scale_d
        )
        assert expected == 5442
        assert latent.num_parameters() == expected
        total = sum(p.numel() for p in latent.parameters())
        assert total == expected

    def test_parameter_count_d512(self):
        """ADR-08: at d=512 total = 17,730 (5442 - 4096 + 16384 - 2 + 2)."""
        latent = RegisterLatent(d_model=512)
        expected = (
            4 * 16
            + 16 * 40
            + 16 * 40
            + 16 * 512
            + 16 * 512
            + 1
            + 1
        )
        assert expected == 17730
        assert latent.num_parameters() == expected


# ---------------------------------------------------------------------------
# Zero-init / step-0 identity FiLM
# ---------------------------------------------------------------------------


class TestZeroInit:

    def test_W_gamma_40_zero_at_init(self, latent_default):
        assert torch.allclose(
            latent_default.W_gamma_40.weight,
            torch.zeros_like(latent_default.W_gamma_40.weight),
        )

    def test_W_beta_40_zero_at_init(self, latent_default):
        assert torch.allclose(
            latent_default.W_beta_40.weight,
            torch.zeros_like(latent_default.W_beta_40.weight),
        )

    def test_W_gamma_d_zero_at_init(self, latent_default):
        assert torch.allclose(
            latent_default.W_gamma_d.weight,
            torch.zeros_like(latent_default.W_gamma_d.weight),
        )

    def test_W_beta_d_zero_at_init(self, latent_default):
        assert torch.allclose(
            latent_default.W_beta_d.weight,
            torch.zeros_like(latent_default.W_beta_d.weight),
        )

    def test_compute_gamma_beta_40_identity_at_init(self, latent_default):
        """tanh(W@z) with zero-W = 0; so gamma=1, beta=0 exactly."""
        gamma, beta = latent_default.compute_gamma_beta_40()
        assert gamma.shape == (NUM_REGISTERS, DEFAULT_NUM_STATES)
        assert beta.shape == (NUM_REGISTERS, DEFAULT_NUM_STATES)
        assert torch.allclose(gamma, torch.ones_like(gamma), atol=1e-12)
        assert torch.allclose(beta, torch.zeros_like(beta), atol=1e-12)

    def test_compute_gamma_beta_d_identity_at_init(self, latent_default):
        gamma, beta = latent_default.compute_gamma_beta_d()
        assert gamma.shape == (NUM_REGISTERS, DEFAULT_REGISTER_DIM)
        assert beta.shape == (NUM_REGISTERS, DEFAULT_REGISTER_DIM)
        assert torch.allclose(gamma, torch.ones_like(gamma), atol=1e-12)
        assert torch.allclose(beta, torch.zeros_like(beta), atol=1e-12)


# ---------------------------------------------------------------------------
# Apply-register: identity at init + None short-circuit
# ---------------------------------------------------------------------------


class TestApplyRegister:

    def test_apply_register_40_none_returns_input(self, latent_default):
        state = torch.randn(2, 8, DEFAULT_NUM_STATES)
        out = latent_default.apply_register_40(state, None)
        assert out is state

    def test_apply_register_40_identity_at_init(self, latent_default):
        """At step-0 init (W=0), FiLM is exact identity for every register."""
        state = torch.randn(2, 8, DEFAULT_NUM_STATES)
        for r_idx in range(NUM_REGISTERS):
            out = latent_default.apply_register_40(state, r_idx)
            assert torch.allclose(out, state, atol=1e-12), (
                f"register {r_idx} should be identity at init"
            )

    def test_apply_register_d_none_returns_input(self, latent_default):
        hidden = torch.randn(2, 8, DEFAULT_REGISTER_DIM)
        out = latent_default.apply_register_d(hidden, None)
        assert out is hidden

    def test_apply_register_d_identity_at_init(self, latent_default):
        hidden = torch.randn(2, 8, DEFAULT_REGISTER_DIM)
        for r_idx in range(NUM_REGISTERS):
            out = latent_default.apply_register_d(hidden, r_idx)
            assert torch.allclose(out, hidden, atol=1e-12)

    def test_apply_register_diverges_after_W_perturbation(self, latent_default):
        """After randomizing W matrices, FiLM is no longer identity."""
        torch.manual_seed(3)
        with torch.no_grad():
            latent_default.W_gamma_40.weight.add_(
                torch.randn_like(latent_default.W_gamma_40.weight) * 0.5
            )
            latent_default.W_beta_40.weight.add_(
                torch.randn_like(latent_default.W_beta_40.weight) * 0.5
            )
        state = torch.randn(2, 8, DEFAULT_NUM_STATES)
        out = latent_default.apply_register_40(state, REGISTER_INDEX["A"])
        assert not torch.allclose(out, state, atol=1e-4)

    def test_apply_register_40_out_of_range(self, latent_default):
        state = torch.randn(2, DEFAULT_NUM_STATES)
        with pytest.raises(IndexError):
            latent_default.apply_register_40(state, NUM_REGISTERS)

    def test_apply_register_40_wrong_dim(self, latent_default):
        state = torch.randn(2, 99)
        with pytest.raises(ValueError, match="Expected last dimension"):
            latent_default.apply_register_40(state, 0)


# ---------------------------------------------------------------------------
# Scale parameters
# ---------------------------------------------------------------------------


class TestScales:

    def test_scales_are_parameters(self, latent_default):
        assert isinstance(latent_default.scale_40, torch.nn.Parameter)
        assert isinstance(latent_default.scale_d, torch.nn.Parameter)

    def test_scales_have_default_values(self, latent_default):
        assert float(latent_default.scale_40.item()) == pytest.approx(DEFAULT_SCALE_40)
        assert float(latent_default.scale_d.item()) == pytest.approx(DEFAULT_SCALE_D)

    def test_scales_frozen_by_default(self, latent_default):
        assert latent_default.scales_frozen is True
        assert latent_default.scale_40.requires_grad is False
        assert latent_default.scale_d.requires_grad is False

    def test_scales_unfreeze(self, latent_default):
        latent_default.set_scales_frozen(False)
        assert latent_default.scales_frozen is False
        assert latent_default.scale_40.requires_grad is True
        assert latent_default.scale_d.requires_grad is True

    def test_parameters_for_optimizer_excludes_frozen_scales(self, latent_default):
        """While frozen, scales are NOT in the optimizer parameter list."""
        params = latent_default.parameters_for_optimizer()
        param_ids = {id(p) for p in params}
        assert id(latent_default.scale_40) not in param_ids
        assert id(latent_default.scale_d) not in param_ids
        # But the latent table + W matrices are present.
        assert id(latent_default.register_latent) in param_ids
        assert id(latent_default.W_gamma_40.weight) in param_ids

    def test_parameters_for_optimizer_includes_unfrozen_scales(self, latent_default):
        latent_default.set_scales_frozen(False)
        params = latent_default.parameters_for_optimizer()
        param_ids = {id(p) for p in params}
        assert id(latent_default.scale_40) in param_ids
        assert id(latent_default.scale_d) in param_ids


# ---------------------------------------------------------------------------
# Involution symmetry from latent level
# ---------------------------------------------------------------------------


class TestInvolutionSymmetry:

    def test_z_T_equal_negz_E_yields_gamma_involution(self, latent_d64):
        """Exact ``z_T = -z_E`` at non-zero W heads gives gamma_T*gamma_E==1
        identity by construction (tanh is odd + W linear).

        Proof sketch: with z_T = -z_E and linear W,
            W@z_T = -W@z_E = -raw_E
        so tanh is odd => tanh(raw_T) = -tanh(raw_E). Then
            gamma_T = 1 + s*tanh_T, gamma_E = 1 + s*tanh_E = 1 - s*tanh_T.
        At s small and arbitrary tanh_T, gamma_T * gamma_E = 1 - (s*tanh_T)^2.
        For exact involution gamma_T * gamma_E = 1 we'd need s==0 OR
        tanh_T==0 (which the zero-init W gives).

        So the *exact* involution only holds when W is either zero or
        z_T = -z_E AND s -> 0. This test uses z_T = -z_E with small s, and
        asserts the involution residual is O(s^2) (first-order Taylor: the
        multiplicative gap is 1 - gamma_T*gamma_E = (s*tanh_T)^2).
        """
        # Set W nonzero so tanh is nontrivial; set z_T = -z_E.
        with torch.no_grad():
            latent_d64.W_gamma_40.weight.copy_(
                torch.randn_like(latent_d64.W_gamma_40.weight) * 0.1
            )
            latent_d64.W_beta_40.weight.copy_(
                torch.randn_like(latent_d64.W_beta_40.weight) * 0.1
            )
            z = torch.randn(latent_d64.latent_dim_r)
            latent_d64.register_latent[REGISTER_INDEX["T"]].copy_(z)
            latent_d64.register_latent[REGISTER_INDEX["E"]].copy_(-z)
        gamma, beta = latent_d64.compute_gamma_beta_40()
        gT = gamma[REGISTER_INDEX["T"]]
        gE = gamma[REGISTER_INDEX["E"]]
        # Multiplicative involution residual bounded by s^2 ~= 0.05^2 = 0.0025.
        residual = (gT * gE - 1.0).abs().max().item()
        # At s=0.05 and bounded tanh, residual <= s^2 = 0.0025.
        assert residual < 0.01

    def test_z_T_equal_negz_E_yields_beta_antisymmetry(self, latent_d64):
        """Exact ``z_T = -z_E`` gives beta_T = -beta_E exactly (tanh odd)."""
        with torch.no_grad():
            latent_d64.W_beta_40.weight.copy_(
                torch.randn_like(latent_d64.W_beta_40.weight) * 0.1
            )
            z = torch.randn(latent_d64.latent_dim_r)
            latent_d64.register_latent[REGISTER_INDEX["T"]].copy_(z)
            latent_d64.register_latent[REGISTER_INDEX["E"]].copy_(-z)
        _, beta = latent_d64.compute_gamma_beta_40()
        bT = beta[REGISTER_INDEX["T"]]
        bE = beta[REGISTER_INDEX["E"]]
        # Exact antisymmetry: beta_T = -beta_E within float tolerance.
        assert torch.allclose(bT + bE, torch.zeros_like(bT), atol=1e-6)


# ---------------------------------------------------------------------------
# Gradient flow
# ---------------------------------------------------------------------------


class TestGradientFlow:

    def test_gradient_flows_to_z_R(self, latent_d64):
        """Loss through FiLM output reaches the per-register latent z_R."""
        # Perturb W so tanh derivative is non-trivial and the chain rule
        # delivers gradient to z.
        torch.manual_seed(7)
        with torch.no_grad():
            latent_d64.W_gamma_40.weight.add_(
                torch.randn_like(latent_d64.W_gamma_40.weight) * 0.1
            )
            latent_d64.W_beta_40.weight.add_(
                torch.randn_like(latent_d64.W_beta_40.weight) * 0.1
            )
        latent_d64.zero_grad()

        state = torch.randn(2, 8, latent_d64.num_states)
        out = latent_d64.apply_register_40(state, REGISTER_INDEX["A"])
        loss = out.pow(2).sum()
        loss.backward()

        assert latent_d64.register_latent.grad is not None
        # Register A (idx 1) should receive nonzero gradient.
        grad_A = latent_d64.register_latent.grad[REGISTER_INDEX["A"]]
        assert not torch.all(grad_A == 0)

    def test_gradient_flows_to_W_matrices(self, latent_d64):
        """W_gamma_40 / W_beta_40 receive gradient through apply_register_40."""
        latent_d64.zero_grad()

        state = torch.randn(2, 8, latent_d64.num_states)
        out = latent_d64.apply_register_40(state, REGISTER_INDEX["T"])
        loss = out.pow(2).sum()
        loss.backward()

        # Even with W zero at init, tanh'(0)=1 so gradient flows through.
        assert latent_d64.W_gamma_40.weight.grad is not None
        assert latent_d64.W_beta_40.weight.grad is not None
        assert torch.any(latent_d64.W_gamma_40.weight.grad != 0)
        assert torch.any(latent_d64.W_beta_40.weight.grad != 0)


# ---------------------------------------------------------------------------
# Diagnostic metrics
# ---------------------------------------------------------------------------


class TestDiagnosticMetrics:

    def test_diagnostic_metrics_keys(self, latent_default):
        metrics = latent_default.diagnostic_metrics()
        required = {
            "z_norm",
            "gamma40_norm",
            "beta40_norm",
            "gammad_norm",
            "betad_norm",
            "scale_40_value",
            "scale_d_value",
            "scales_frozen",
        }
        assert required.issubset(metrics.keys())

    def test_diagnostic_metrics_per_register_shape(self, latent_default):
        metrics = latent_default.diagnostic_metrics()
        # Per-register norms: one value per register.
        assert metrics["z_norm"].shape == (NUM_REGISTERS,)
        assert metrics["gamma40_norm"].shape == (NUM_REGISTERS,)
        assert metrics["beta40_norm"].shape == (NUM_REGISTERS,)
        assert metrics["gammad_norm"].shape == (NUM_REGISTERS,)
        assert metrics["betad_norm"].shape == (NUM_REGISTERS,)

    def test_diagnostic_metrics_scales_frozen_true_at_init(self, latent_default):
        metrics = latent_default.diagnostic_metrics()
        assert float(metrics["scales_frozen"].item()) == 1.0
