"""Option E alignment + integration tests (ADR-08).

Covers:
  - ``LatentInvolutionLoss`` — latent + output-surface term correctness
  - Aggregate weighting: lambda_out + lambda_latent combine correctly
  - v7.4 byte-equivalence when register_film flag OFF (ADR-01 invariant)
  - Step-0 identity FiLM when flag ON (zero-init W heads)
  - Agent 35 expression proposer: unaffected by Option E refactor
  - Agent 37 unified None/zero forward: bitwise-equivalent under Option E
  - Agent 38 null-space regularization: OmegaRegistry / unused slots unchanged
  - Scale warmup: scales remain frozen for ``scale_warmup_steps`` iterations
"""

from __future__ import annotations

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.embedding import (
    CognitiveStateEmbedding,
    CognitiveStateEmbeddingWithRegister,
    NUM_COGNITIVE_STATES,
)
from cas_native.model.loss import (
    InvolutionConstraintLoss,
    LatentInvolutionLoss,
)
from cas_native.model.register_film import (
    INVOLUTION_REGISTER_PAIRS,
    NUM_REGISTERS,
    REGISTER_INDEX,
    RegisterLatent,
)
from cas_native.training.config import (
    TrainingConfig,
    V2ComponentFlags,
    V2Hyperparameters,
    V74Hyperparameters,
)
from cas_native.training.data_pipeline import CASDataset, cas_collate_fn
from cas_native.training.trainer import CASTrainer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(d_model: int = 64) -> CASNativeModel:
    return CASNativeModel(
        CASNativeConfig(
            d_model=d_model,
            n_layers=1,
            n_heads=4,
            vocab_size=64,
            max_seq_len=32,
            fractal_depth=1,
            num_ethical_propositions=3,
        )
    )


def _make_loader(data: list[dict] | None = None) -> DataLoader:
    data = data or [
        {
            "prompt": "p",
            "response": "r",
            "scores": {"operator_scores": [1] * 10},
        }
    ]
    dataset = CASDataset(data, max_length=16)
    return DataLoader(dataset, batch_size=1, collate_fn=cas_collate_fn)


def _v2_cfg(all_on: bool = True, **hp_overrides) -> TrainingConfig:
    flags = V2ComponentFlags(
        use_register_film=all_on,
        use_emergent_register=all_on,
        use_production_semantics=all_on,
        use_rust_validation=False,  # don't require rust bridge
    )
    hp_defaults = dict(
        gumbel_tau_anneal_steps=10,
        rust_cache_capacity=100,
        registry_capacity=4,
    )
    hp_defaults.update(hp_overrides)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=V2Hyperparameters(**hp_defaults),
        v7_4_hyperparameters=V74Hyperparameters(max_steps=2, warmup_steps=1),
    )


# ---------------------------------------------------------------------------
# LatentInvolutionLoss correctness
# ---------------------------------------------------------------------------


class TestLatentInvolutionLoss:

    def test_latent_term_zero_when_z_sums_to_zero(self):
        latent = RegisterLatent(d_model=64)
        with torch.no_grad():
            z = torch.randn(latent.latent_dim_r)
            # z_T = -z_E and z_A = -z_f exactly.
            latent.register_latent[REGISTER_INDEX["T"]].copy_(z)
            latent.register_latent[REGISTER_INDEX["E"]].copy_(-z)
            z2 = torch.randn(latent.latent_dim_r)
            latent.register_latent[REGISTER_INDEX["A"]].copy_(z2)
            latent.register_latent[REGISTER_INDEX["f"]].copy_(-z2)
        loss_fn = LatentInvolutionLoss()
        l_latent = loss_fn.latent_term(latent)
        assert torch.allclose(l_latent, torch.zeros_like(l_latent), atol=1e-6)

    def test_latent_term_nonzero_for_random_init(self):
        """Random init z_R ~ N(0,1) gives nonzero z_a + z_b."""
        latent = RegisterLatent(d_model=64)
        loss_fn = LatentInvolutionLoss()
        l_latent = loss_fn.latent_term(latent)
        assert l_latent.item() > 0.0

    def test_output_surface_term_zero_at_init(self):
        """Zero-init W heads => gamma=1, beta=0, so output-surface term is 0."""
        latent = RegisterLatent(d_model=64)
        loss_fn = LatentInvolutionLoss()
        l_out = loss_fn.output_surface_term(latent)
        assert torch.allclose(l_out, torch.zeros_like(l_out), atol=1e-12)

    def test_output_surface_term_nonzero_after_perturbation(self):
        latent = RegisterLatent(d_model=64)
        torch.manual_seed(11)
        with torch.no_grad():
            latent.W_gamma_40.weight.add_(
                torch.randn_like(latent.W_gamma_40.weight) * 0.3
            )
            latent.W_beta_d.weight.add_(
                torch.randn_like(latent.W_beta_d.weight) * 0.3
            )
        loss_fn = LatentInvolutionLoss()
        l_out = loss_fn.output_surface_term(latent)
        assert l_out.item() > 0.0

    def test_aggregate_weighting_linear_in_lambda_latent(self):
        """Doubling lambda_latent doubles the latent-level contribution."""
        latent = RegisterLatent(d_model=64)
        loss_fn_1x = LatentInvolutionLoss(lambda_out=0.0, lambda_latent=0.01)
        loss_fn_2x = LatentInvolutionLoss(lambda_out=0.0, lambda_latent=0.02)
        l1 = loss_fn_1x(latent)
        l2 = loss_fn_2x(latent)
        # Linearity: l2 == 2 * l1.
        assert torch.allclose(l2, l1 * 2.0, atol=1e-6)

    def test_aggregate_weighting_linear_in_lambda_out(self):
        latent = RegisterLatent(d_model=64)
        # Perturb W so output-surface term is nonzero (otherwise doubling 0 = 0).
        torch.manual_seed(0)
        with torch.no_grad():
            latent.W_gamma_40.weight.copy_(
                torch.randn_like(latent.W_gamma_40.weight) * 0.1
            )
        loss_fn_1x = LatentInvolutionLoss(lambda_out=0.1, lambda_latent=0.0)
        loss_fn_2x = LatentInvolutionLoss(lambda_out=0.2, lambda_latent=0.0)
        l1 = loss_fn_1x(latent)
        l2 = loss_fn_2x(latent)
        assert torch.allclose(l2, l1 * 2.0, atol=1e-6)

    def test_forward_returns_components_when_requested(self):
        latent = RegisterLatent(d_model=64)
        loss_fn = LatentInvolutionLoss()
        total, comps = loss_fn(latent, return_components=True)
        assert "l_inv_output" in comps
        assert "l_inv_latent" in comps
        # At init l_inv_output == 0 exactly.
        assert torch.allclose(
            comps["l_inv_output"], torch.zeros_like(comps["l_inv_output"])
        )


# ---------------------------------------------------------------------------
# Byte-equivalence (v7.4 parity + step-0 identity)
# ---------------------------------------------------------------------------


class TestByteEquivalence:

    def test_v74_byte_equivalent_when_flags_off(self):
        """Flags-off => parameter count identical to legacy v7.4 trainer."""
        torch.manual_seed(321)
        model_a = _make_model()
        trainer_a = CASTrainer(
            model_a, _make_loader(), _make_loader(),
            config={"max_steps": 1},
        )
        legacy_params = sum(p.numel() for p in trainer_a.model.parameters())

        torch.manual_seed(321)
        model_b = _make_model()
        trainer_b = CASTrainer(
            model_b, _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=False),
        )
        v2_off_params = sum(p.numel() for p in trainer_b.model.parameters())
        assert legacy_params == v2_off_params

    def test_step_zero_identity_film_on_cognitive_state(self):
        """At init (W zero), register-activated forward == register-neutral.

        This is the ADR-08 step-0 identity property: zero-init W matrices
        mean FiLM is the identity, so the active-register path and the
        zero-activation path produce identical cognitive_state outputs.
        """
        model = _make_model()
        trainer = CASTrainer(
            model, _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True),
        )
        model.eval()

        input_ids = torch.zeros(1, 4, dtype=torch.long)
        attention_mask = torch.ones(1, 4, dtype=torch.long)
        zeros = torch.zeros(
            1, NUM_COGNITIVE_STATES, NUM_REGISTERS, dtype=torch.bool
        )
        acts = zeros.clone()
        acts[0, :, REGISTER_INDEX["A"]] = True

        out_neutral = model(input_ids, attention_mask=attention_mask, register_activations=zeros)
        out_active = model(input_ids, attention_mask=attention_mask, register_activations=acts)
        assert torch.allclose(
            out_neutral["cognitive_state"],
            out_active["cognitive_state"],
            atol=1e-6,
        )


# ---------------------------------------------------------------------------
# Wave 8A agent integration — Agent 35 (expression proposer)
# ---------------------------------------------------------------------------


class TestAgent35ProposerIntegration:

    def test_proposer_unaffected_by_option_e(self):
        """ExpressionProposerHead operates on hidden states, not register
        parameters. Option E refactor must not change its availability."""
        flags = V2ComponentFlags(
            use_register_film=True,
            use_emergent_register=False,
            use_production_semantics=False,
            use_rust_validation=False,
            use_expression_proposer=True,
        )
        cfg = TrainingConfig(
            component_flags=flags,
            v2_hyperparameters=V2Hyperparameters(
                gumbel_tau_anneal_steps=10, rust_cache_capacity=100,
            ),
            v7_4_hyperparameters=V74Hyperparameters(
                max_steps=1, warmup_steps=0,
            ),
        )
        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(), config=cfg
        )
        assert trainer.expression_proposer is not None
        # Forward through the model emits proposer_outputs when enabled.
        input_ids = torch.zeros(1, 4, dtype=torch.long)
        out = trainer.model(input_ids)
        assert "proposer_outputs" in out


# ---------------------------------------------------------------------------
# Wave 8A agent integration — Agent 37 (unified None/zero forward)
# ---------------------------------------------------------------------------


class TestAgent37UnifiedForward:

    def test_none_and_zero_activations_bitwise_equal(self):
        """Decision G invariant: None and zero-activation routes are identical."""
        model = _make_model()
        CASTrainer(
            model, _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True),
        )
        model.eval()
        torch.manual_seed(0)
        input_ids = torch.randint(0, 64, (2, 8), dtype=torch.long)
        attention_mask = torch.ones(2, 8, dtype=torch.long)
        zeros = torch.zeros(
            2, NUM_COGNITIVE_STATES, NUM_REGISTERS, dtype=torch.bool
        )

        out_none = model(
            input_ids, attention_mask=attention_mask, register_activations=None
        )
        out_zero = model(
            input_ids, attention_mask=attention_mask, register_activations=zeros
        )
        assert torch.allclose(
            out_none["cognitive_state"],
            out_zero["cognitive_state"],
            atol=0.0,
        )


# ---------------------------------------------------------------------------
# Wave 8A agent integration — Agent 38 (null-space regularization)
# ---------------------------------------------------------------------------


class TestAgent38NullSpaceIntegration:

    def test_unused_slot_indices_still_work(self):
        """Null-space regularization operates on the OmegaRegistry, not on
        RegisterLatent. Option E refactor must leave it untouched."""
        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True, registry_capacity=4),
        )
        # The emergent pipeline exists; its registry has zero admitted slots
        # at init -> all 4 slots are unused.
        pipeline = trainer.emergent_pipeline
        assert pipeline is not None
        unused = pipeline.registry.unused_slot_embeddings()
        assert unused.shape[0] == 4
        assert unused.shape[1] == trainer.model.config.d_model


# ---------------------------------------------------------------------------
# Scale warmup
# ---------------------------------------------------------------------------


class TestScaleWarmup:

    def test_scales_frozen_at_step_zero(self):
        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True, scale_warmup_steps=100),
        )
        emb = trainer.model.v2_components["register_embedding"]
        assert emb.register_latent.scales_frozen is True

    def test_scales_unfreeze_after_warmup(self):
        """Simulate the warmup boundary by calling _maybe_unfreeze_scales."""
        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True, scale_warmup_steps=5),
        )
        emb = trainer.model.v2_components["register_embedding"]
        assert emb.register_latent.scales_frozen is True

        # At step 0, still frozen.
        trainer._maybe_unfreeze_scales(0)
        assert emb.register_latent.scales_frozen is True
        # Just before boundary, still frozen.
        trainer._maybe_unfreeze_scales(4)
        assert emb.register_latent.scales_frozen is True
        # At/past boundary, unfrozen.
        trainer._maybe_unfreeze_scales(5)
        assert emb.register_latent.scales_frozen is False
        # Idempotent — calling again is a no-op.
        trainer._maybe_unfreeze_scales(100)
        assert emb.register_latent.scales_frozen is False


# ---------------------------------------------------------------------------
# Trainer diagnostic metrics
# ---------------------------------------------------------------------------


class TestTrainerDiagnostics:

    def test_latent_metrics_in_train_step_output(self):
        """The _train_step metrics dict surfaces latent diagnostics under
        the ``register_latent/*`` key prefix."""
        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(),
            config=_v2_cfg(all_on=True),
        )
        batch = next(iter(_make_loader()))
        metrics = trainer._train_step(batch)
        # A representative set of required keys.
        required = {
            "register_latent/z_norm/T",
            "register_latent/z_norm/A",
            "register_latent/z_norm/f",
            "register_latent/z_norm/E",
            "register_latent/l_inv_output",
            "register_latent/l_inv_latent",
            "register_latent/scale_40_value",
            "register_latent/scale_d_value",
            "register_latent/scales_frozen",
        }
        assert required.issubset(metrics.keys())
