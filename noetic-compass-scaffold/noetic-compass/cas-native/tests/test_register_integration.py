"""Tests for Phenomenological Register integration via FiLM (ADR-01).

Covers:
  - RegisterFiLM parameter budget (1,024 params at d=128)
  - Identity-at-init and register_idx=None backward-compat fast path
  - CognitiveStateEmbeddingWithRegister register-neutral equality to base
  - Register-dependent output divergence after gamma/beta perturbation
  - InvolutionConstraintLoss formula correctness across all 4 terms
  - Lambda scaling and gradient flow through register parameters
"""

import pytest
import torch

from cas_native.model.embedding import (
    CognitiveStateEmbedding,
    CognitiveStateEmbeddingWithRegister,
    NUM_COGNITIVE_STATES,
)
from cas_native.model.loss import InvolutionConstraintLoss
from cas_native.model.register_film import (
    DEFAULT_REGISTER_DIM,
    INVOLUTION_REGISTER_PAIRS,
    NUM_REGISTERS,
    REGISTER_INDEX,
    RegisterFiLM,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def register_film():
    """Default RegisterFiLM at d_model=128 (ADR-01 spec)."""
    return RegisterFiLM(d_model=DEFAULT_REGISTER_DIM)


@pytest.fixture
def sample_state():
    """Sample state tensor of shape (batch=2, seq=10, d_model=128)."""
    return torch.randn(2, 10, DEFAULT_REGISTER_DIM)


@pytest.fixture
def embedding_with_register():
    """CognitiveStateEmbeddingWithRegister at d_model=64."""
    return CognitiveStateEmbeddingWithRegister(d_model=64)


@pytest.fixture
def sample_input():
    """Sample token embeddings of shape (batch=2, seq=10, d_model=64)."""
    return torch.randn(2, 10, 64)


# ---------------------------------------------------------------------------
# RegisterFiLM core tests
# ---------------------------------------------------------------------------


class TestRegisterFiLM:

    def test_parameter_count_is_1024(self, register_film):
        """ADR-01: 4 registers x 2 x 128 = 1,024 parameters exactly."""
        assert register_film.num_parameters() == 1024
        # Sanity: confirm via sum over self.parameters() too.
        assert sum(p.numel() for p in register_film.parameters()) == 1024

    def test_parameter_shapes(self, register_film):
        """gamma and beta each have shape (4, 128)."""
        assert register_film.gamma.shape == (NUM_REGISTERS, DEFAULT_REGISTER_DIM)
        assert register_film.beta.shape == (NUM_REGISTERS, DEFAULT_REGISTER_DIM)

    def test_identity_init_gamma_ones(self, register_film):
        """gamma initializes to ones (identity multiplier)."""
        assert torch.allclose(
            register_film.gamma, torch.ones_like(register_film.gamma)
        )

    def test_identity_init_beta_zeros(self, register_film):
        """beta initializes to zeros (identity offset)."""
        assert torch.allclose(
            register_film.beta, torch.zeros_like(register_film.beta)
        )

    def test_identity_behavior_at_init_all_registers(self, register_film, sample_state):
        """At init, apply_register returns state * 1 + 0 = state for every idx."""
        for register_idx in range(NUM_REGISTERS):
            out = register_film.apply_register(sample_state, register_idx)
            assert torch.allclose(out, sample_state, atol=1e-7), (
                f"register_idx={register_idx} should be identity at init"
            )

    def test_register_idx_none_returns_unchanged_state(self, register_film, sample_state):
        """register_idx=None short-circuits and returns the exact input tensor."""
        out = register_film.apply_register(sample_state, None)
        # Should be the same tensor object (no computation performed).
        assert out is sample_state

    def test_register_idx_none_after_perturbation_still_unchanged(
        self, register_film, sample_state
    ):
        """register_idx=None remains neutral even after gamma/beta perturbation."""
        with torch.no_grad():
            register_film.gamma.add_(torch.randn_like(register_film.gamma))
            register_film.beta.add_(torch.randn_like(register_film.beta))
        out = register_film.apply_register(sample_state, None)
        assert out is sample_state

    def test_register_mapping_authoritative(self):
        """Register index mapping matches CAS v7.5 Clarification 8 (lowercase f)."""
        assert REGISTER_INDEX == {"T": 0, "A": 1, "f": 2, "E": 3}

    def test_involution_pairs_are_T_E_and_A_f(self):
        """Involution pair registry lists (T,E) and (A,f) per ADR-01."""
        t_e = (REGISTER_INDEX["T"], REGISTER_INDEX["E"])
        a_f = (REGISTER_INDEX["A"], REGISTER_INDEX["f"])
        pairs = list(INVOLUTION_REGISTER_PAIRS)
        assert t_e in pairs and a_f in pairs
        assert len(pairs) == 2

    def test_apply_register_after_perturbation_changes_output(
        self, register_film, sample_state
    ):
        """After perturbing gamma/beta, register modulation produces non-identity output."""
        torch.manual_seed(7)
        with torch.no_grad():
            register_film.gamma.add_(torch.randn_like(register_film.gamma) * 0.5)
            register_film.beta.add_(torch.randn_like(register_film.beta) * 0.5)
        out = register_film.apply_register(sample_state, REGISTER_INDEX["A"])
        assert not torch.allclose(out, sample_state, atol=1e-4)

    def test_apply_register_out_of_range_raises(self, register_film, sample_state):
        """Out-of-range register_idx raises IndexError."""
        with pytest.raises(IndexError):
            register_film.apply_register(sample_state, 4)
        with pytest.raises(IndexError):
            register_film.apply_register(sample_state, -1)

    def test_apply_register_wrong_dim_raises(self, register_film):
        """State with mismatched last dim raises ValueError."""
        bad_state = torch.randn(2, 10, 64)
        with pytest.raises(ValueError, match="Expected last dimension"):
            register_film.apply_register(bad_state, 0)

    def test_gradient_flow_through_gamma_and_beta(self, register_film, sample_state):
        """Backward pass populates gamma and beta gradients when register is applied."""
        register_film.zero_grad()
        # Perturb so gradient is non-trivial (at init gamma grad would be non-zero
        # only through the multiplicative path, beta grad is state-independent).
        out = register_film.apply_register(sample_state, REGISTER_INDEX["T"])
        loss = out.sum()
        loss.backward()
        assert register_film.gamma.grad is not None
        assert register_film.beta.grad is not None
        # The register we used (T, idx 0) should have nonzero gradient.
        assert not torch.all(register_film.gamma.grad[REGISTER_INDEX["T"]] == 0)
        assert not torch.all(register_film.beta.grad[REGISTER_INDEX["T"]] == 0)

    def test_gradient_flow_none_path_no_grad_on_params(self, register_film):
        """register_idx=None should not accumulate gradient on gamma/beta.

        The state carries requires_grad=True so the graph is non-empty upstream;
        the FiLM fast-path must nevertheless bypass gamma/beta entirely.
        """
        register_film.zero_grad()
        state = torch.randn(2, 10, DEFAULT_REGISTER_DIM, requires_grad=True)
        out = register_film.apply_register(state, None)
        # Fast-path contract: identical object, no computation.
        assert out is state
        loss = out.sum()
        loss.backward()
        # Gradient flows back to the input state, but not to FiLM parameters.
        assert state.grad is not None
        assert register_film.gamma.grad is None or torch.all(
            register_film.gamma.grad == 0
        )
        assert register_film.beta.grad is None or torch.all(
            register_film.beta.grad == 0
        )


# ---------------------------------------------------------------------------
# CognitiveStateEmbeddingWithRegister integration tests
# ---------------------------------------------------------------------------


class TestCognitiveStateEmbeddingWithRegister:

    def test_output_shape_register_neutral(
        self, embedding_with_register, sample_input
    ):
        """Output shape is (batch, seq, 40) in register-neutral mode."""
        out = embedding_with_register(sample_input, register_idx=None)
        assert out.shape == (2, 10, NUM_COGNITIVE_STATES)

    def test_output_shape_with_register(self, embedding_with_register, sample_input):
        """Output shape is (batch, seq, 40) when a register is specified."""
        out = embedding_with_register(sample_input, register_idx=REGISTER_INDEX["f"])
        assert out.shape == (2, 10, NUM_COGNITIVE_STATES)

    def test_simplex_constraint_preserved_register_neutral(
        self, embedding_with_register, sample_input
    ):
        """Output lies on the open simplex in register-neutral mode."""
        out = embedding_with_register(sample_input, register_idx=None)
        assert (out > 0).all()
        sums = out.sum(dim=-1)
        assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)

    def test_simplex_constraint_preserved_with_register(
        self, embedding_with_register, sample_input
    ):
        """Output lies on the open simplex in every register mode."""
        for idx in range(NUM_REGISTERS):
            out = embedding_with_register(sample_input, register_idx=idx)
            assert (out > 0).all(), f"positivity failed for idx={idx}"
            sums = out.sum(dim=-1)
            assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), (
                f"sum-to-one failed for idx={idx}"
            )

    def test_register_neutral_matches_base_embedding_exactly(self):
        """v7.4 backward-compat: register_idx=None output == base CognitiveStateEmbedding."""
        torch.manual_seed(123)
        wrapped = CognitiveStateEmbeddingWithRegister(d_model=64)
        x = torch.randn(2, 10, 64)

        # Base reference: share weights with wrapped.base (the wrapper delegates).
        base_out = wrapped.base(x)
        wrapped_out = wrapped(x, register_idx=None)
        assert torch.allclose(wrapped_out, base_out, atol=1e-7)

    def test_register_neutral_matches_any_register_at_init(
        self, embedding_with_register, sample_input
    ):
        """At init (identity FiLM), all register modes collapse to the same output."""
        neutral = embedding_with_register(sample_input, register_idx=None)
        for idx in range(NUM_REGISTERS):
            modulated = embedding_with_register(sample_input, register_idx=idx)
            assert torch.allclose(modulated, neutral, atol=1e-6), (
                f"idx={idx} should equal neutral output at init (identity FiLM)"
            )

    def test_register_changes_output_after_perturbation(
        self, embedding_with_register, sample_input
    ):
        """After training-like perturbation, different registers give different outputs."""
        torch.manual_seed(11)
        film = embedding_with_register.register_film
        with torch.no_grad():
            film.gamma.add_(torch.randn_like(film.gamma) * 0.3)
            film.beta.add_(torch.randn_like(film.beta) * 0.3)

        out_T = embedding_with_register(sample_input, register_idx=REGISTER_INDEX["T"])
        out_A = embedding_with_register(sample_input, register_idx=REGISTER_INDEX["A"])
        out_f = embedding_with_register(sample_input, register_idx=REGISTER_INDEX["f"])
        out_E = embedding_with_register(sample_input, register_idx=REGISTER_INDEX["E"])

        assert not torch.allclose(out_T, out_A, atol=1e-4)
        assert not torch.allclose(out_T, out_f, atol=1e-4)
        assert not torch.allclose(out_T, out_E, atol=1e-4)
        assert not torch.allclose(out_A, out_f, atol=1e-4)

    def test_wrapped_parameter_count_includes_film(self):
        """Total parameter count = base + 1,024 (FiLM at register_dim=40)."""
        wrapped = CognitiveStateEmbeddingWithRegister(d_model=64)
        base = CognitiveStateEmbedding(d_model=64)
        expected_film_params = NUM_REGISTERS * 2 * NUM_COGNITIVE_STATES  # 4*2*40 = 320
        base_count = sum(p.numel() for p in base.parameters())
        wrapped_count = sum(p.numel() for p in wrapped.parameters())
        assert wrapped_count == base_count + expected_film_params


# ---------------------------------------------------------------------------
# InvolutionConstraintLoss tests
# ---------------------------------------------------------------------------


class TestInvolutionConstraintLoss:

    def test_default_lambda_is_point_one(self):
        """ADR-01: lambda default is 0.1."""
        loss_fn = InvolutionConstraintLoss()
        assert loss_fn.lambda_involution == 0.1

    def test_lambda_configurable(self):
        """lambda_involution is a configurable hyperparameter."""
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.5)
        assert loss_fn.lambda_involution == 0.5

    def test_loss_is_zero_at_init(self, register_film):
        """At init (gamma=1, beta=0): gamma_a*gamma_b-1=0, beta_a+beta_b=0, so loss=0."""
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.1)
        loss = loss_fn.involution_loss(register_film)
        assert torch.allclose(loss, torch.zeros_like(loss), atol=1e-12)

    def test_loss_zero_at_init_for_any_lambda(self, register_film):
        """Loss at init is zero regardless of lambda (all 4 terms vanish)."""
        for lam in [0.0, 0.1, 1.0, 10.0]:
            loss_fn = InvolutionConstraintLoss(lambda_involution=lam)
            loss = loss_fn.involution_loss(register_film)
            assert torch.allclose(loss, torch.zeros_like(loss), atol=1e-12)

    def test_loss_nonzero_after_random_perturbation(self, register_film):
        """After perturbing gamma/beta, the involution constraint is violated (loss > 0)."""
        torch.manual_seed(42)
        with torch.no_grad():
            register_film.gamma.add_(torch.randn_like(register_film.gamma) * 0.1)
            register_film.beta.add_(torch.randn_like(register_film.beta) * 0.1)
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.1)
        loss = loss_fn.involution_loss(register_film)
        assert loss.item() > 0.0

    def test_all_four_terms_present_in_formula(self):
        """Independently verify the formula includes gamma_T*gamma_E-1, beta_T+beta_E,
        gamma_A*gamma_f-1, beta_A+beta_f — each as squared L2 norm."""
        d = DEFAULT_REGISTER_DIM
        film = RegisterFiLM(d_model=d)

        # Set known, non-identity values so every term contributes.
        with torch.no_grad():
            # gamma_T = 2, gamma_E = 0.5 -> gamma_T*gamma_E = 1 -> term1 = 0
            # gamma_A = 3, gamma_f = 0.25 -> product = 0.75, (0.75-1)^2 * d = 0.0625*d
            # beta_T = +1, beta_E = -1 -> sum = 0 -> term2 = 0
            # beta_A = 2, beta_f = 5 -> sum = 7 -> (7)^2 * d = 49*d
            film.gamma.zero_()
            film.beta.zero_()
            film.gamma[REGISTER_INDEX["T"]] += 2.0
            film.gamma[REGISTER_INDEX["E"]] += 0.5
            film.gamma[REGISTER_INDEX["A"]] += 3.0
            film.gamma[REGISTER_INDEX["f"]] += 0.25
            film.beta[REGISTER_INDEX["T"]] += 1.0
            film.beta[REGISTER_INDEX["E"]] += -1.0
            film.beta[REGISTER_INDEX["A"]] += 2.0
            film.beta[REGISTER_INDEX["f"]] += 5.0

        loss_fn = InvolutionConstraintLoss(lambda_involution=1.0)
        loss = loss_fn.involution_loss(film)

        # Expected sum of squared norms:
        # term1 (T*E gamma): (1-1)^2 * d = 0
        # term2 (T+E beta):  (0)^2  * d = 0
        # term3 (A*f gamma): (0.75-1)^2 * d = 0.0625*d
        # term4 (A+f beta):  (7)^2  * d = 49*d
        expected = (0.0625 + 49.0) * d
        assert torch.allclose(loss, torch.tensor(expected, dtype=loss.dtype), atol=1e-4)

    def test_lambda_scales_loss_magnitude_linearly(self):
        """Doubling lambda doubles the loss magnitude."""
        film = RegisterFiLM(d_model=DEFAULT_REGISTER_DIM)
        torch.manual_seed(0)
        with torch.no_grad():
            film.gamma.add_(torch.randn_like(film.gamma) * 0.2)
            film.beta.add_(torch.randn_like(film.beta) * 0.2)

        loss_01 = InvolutionConstraintLoss(lambda_involution=0.1).involution_loss(film)
        loss_02 = InvolutionConstraintLoss(lambda_involution=0.2).involution_loss(film)
        # Linear scaling: loss_02 should be 2 * loss_01.
        assert torch.allclose(loss_02, loss_01 * 2.0, atol=1e-5)

    def test_accepts_gamma_beta_tuple(self):
        """Loss accepts a (gamma, beta) tensor tuple as well as a RegisterFiLM."""
        d = DEFAULT_REGISTER_DIM
        gamma = torch.ones(NUM_REGISTERS, d)
        beta = torch.zeros(NUM_REGISTERS, d)
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.1)
        loss = loss_fn.involution_loss((gamma, beta))
        assert torch.allclose(loss, torch.zeros_like(loss), atol=1e-12)

    def test_gradient_flows_to_film_parameters(self, register_film):
        """Backward through involution_loss populates gamma and beta gradients."""
        # Perturb so loss is nonzero and gradients are nontrivial.
        torch.manual_seed(3)
        with torch.no_grad():
            register_film.gamma.add_(torch.randn_like(register_film.gamma) * 0.1)
            register_film.beta.add_(torch.randn_like(register_film.beta) * 0.1)

        register_film.zero_grad()
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.1)
        loss = loss_fn.involution_loss(register_film)
        loss.backward()
        assert register_film.gamma.grad is not None
        assert register_film.beta.grad is not None
        assert not torch.all(register_film.gamma.grad == 0)
        assert not torch.all(register_film.beta.grad == 0)

    def test_forward_alias_calls_involution_loss(self, register_film):
        """nn.Module forward() delegates to involution_loss."""
        loss_fn = InvolutionConstraintLoss(lambda_involution=0.1)
        a = loss_fn(register_film)
        b = loss_fn.involution_loss(register_film)
        assert torch.allclose(a, b)


# ---------------------------------------------------------------------------
# Backward-compat guard
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:

    def test_base_embedding_unchanged(self):
        """CognitiveStateEmbedding API is preserved — no forward() signature change."""
        base = CognitiveStateEmbedding(d_model=64)
        x = torch.randn(2, 10, 64)
        out = base(x)
        assert out.shape == (2, 10, NUM_COGNITIVE_STATES)
        assert (out > 0).all()
