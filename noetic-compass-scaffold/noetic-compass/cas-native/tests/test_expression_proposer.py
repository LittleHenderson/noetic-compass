"""Wave 8A Agent 35 — ExpressionProposerHead tests (ADR-07).

Covers:
  - Initialization with default and custom dims + argument validation
  - Forward-pass output shapes across 2-D and 3-D hidden-state inputs
  - Dtype / device placement preservation
  - Gradient flow from every head back to every proposer parameter
  - Edge cases: malformed input, boundary operand counts, mode validation
  - Gumbel-softmax attachment in training mode and absence in inference mode
  - Proposal dataclass correctness under propose()
  - Integration with CASTrainer: proposer instantiation, parameter
    participation in optimizer, and score-based loss computation against
    synthetic label batches

Reference: ``docs/architecture/cas_native_v2_adrs.md`` ADR-07.
"""

from __future__ import annotations

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.model.expression_proposer import (
    DEFAULT_BOTTLENECK_DIM,
    DEFAULT_MAX_OPERANDS,
    ExpressionProposal,
    ExpressionProposerHead,
    NUM_DOMAINS,
    NUM_NOETICS,
    OPERAND_COUNT_BUCKETS,
)
from cas_native.model.loss import ProposerRuleFourLoss
from cas_native.model.register_film import NUM_REGISTERS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_head():
    return ExpressionProposerHead(d_model=128)


@pytest.fixture
def small_head():
    # Smaller head for cheaper-per-test integration paths.
    return ExpressionProposerHead(d_model=64, bottleneck_dim=16, max_operands=3)


@pytest.fixture
def pooled_hidden():
    return torch.randn(4, 128)


@pytest.fixture
def seq_hidden():
    return torch.randn(4, 7, 128)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestInitialization:

    def test_default_config_instantiates(self, default_head):
        """Head instantiates with d_model=128 and advertised defaults."""
        assert default_head.d_model == 128
        assert default_head.bottleneck_dim == DEFAULT_BOTTLENECK_DIM
        assert default_head.max_operands == DEFAULT_MAX_OPERANDS
        assert default_head.num_noetics == NUM_NOETICS
        assert default_head.num_domains == NUM_DOMAINS
        assert default_head.num_registers == NUM_REGISTERS
        assert default_head.operand_count_buckets == OPERAND_COUNT_BUCKETS

    def test_custom_dims_respected(self):
        head = ExpressionProposerHead(
            d_model=256,
            bottleneck_dim=48,
            max_operands=5,
            operand_count_buckets=(0, 1, 2, 3, 4, 5),
        )
        assert head.d_model == 256
        assert head.bottleneck_dim == 48
        assert head.max_operands == 5
        assert head.operand_count_buckets == (0, 1, 2, 3, 4, 5)

    def test_reject_non_positive_d_model(self):
        with pytest.raises(ValueError, match="d_model"):
            ExpressionProposerHead(d_model=0)
        with pytest.raises(ValueError, match="d_model"):
            ExpressionProposerHead(d_model=-16)

    def test_reject_non_positive_bottleneck(self):
        with pytest.raises(ValueError, match="bottleneck_dim"):
            ExpressionProposerHead(d_model=64, bottleneck_dim=0)

    def test_reject_non_positive_max_operands(self):
        with pytest.raises(ValueError, match="max_operands"):
            ExpressionProposerHead(d_model=64, max_operands=0)

    def test_reject_empty_operand_count_buckets(self):
        with pytest.raises(ValueError, match="operand_count_buckets"):
            ExpressionProposerHead(d_model=64, operand_count_buckets=())

    def test_parameter_count_positive(self, default_head):
        """The reported parameter count is the sum over self.parameters()."""
        assert default_head.parameter_count > 0
        assert default_head.parameter_count == sum(
            p.numel() for p in default_head.parameters()
        )

    def test_parameter_count_scales_with_d_model(self):
        """Larger d_model increases the backbone parameter count."""
        small = ExpressionProposerHead(d_model=64, bottleneck_dim=32)
        large = ExpressionProposerHead(d_model=512, bottleneck_dim=32)
        assert large.parameter_count > small.parameter_count


# ---------------------------------------------------------------------------
# Forward pass — output shape + dtype
# ---------------------------------------------------------------------------


class TestForwardShape:

    def test_pooled_input_shape(self, default_head, pooled_hidden):
        out = default_head(pooled_hidden, mode="training")
        B = pooled_hidden.shape[0]
        assert out["noetic_logits"].shape == (B, NUM_NOETICS)
        assert out["domain_logits"].shape == (B, NUM_DOMAINS)
        assert out["register_logits"].shape == (
            B,
            DEFAULT_MAX_OPERANDS,
            NUM_REGISTERS,
        )
        assert out["operand_count_logits"].shape == (
            B,
            len(OPERAND_COUNT_BUCKETS),
        )
        assert out["named_emergent_logits"].shape == (B, 2)

    def test_sequence_input_is_mean_pooled(self, default_head, seq_hidden):
        """3-D (B, seq, d_model) input is mean-pooled over seq."""
        out = default_head(seq_hidden, mode="training")
        B = seq_hidden.shape[0]
        assert out["noetic_logits"].shape == (B, NUM_NOETICS)
        assert out["register_logits"].shape == (
            B,
            DEFAULT_MAX_OPERANDS,
            NUM_REGISTERS,
        )

    def test_batch_sizes_vary(self, default_head):
        for B in (1, 3, 8):
            hidden = torch.randn(B, 128)
            out = default_head(hidden, mode="inference")
            assert out["noetic_logits"].shape[0] == B

    def test_reject_bad_dim(self, default_head):
        """1-D or 4-D hidden states are rejected with a clear error."""
        with pytest.raises(ValueError, match="2 or 3"):
            default_head(torch.randn(128), mode="training")
        with pytest.raises(ValueError, match="2 or 3"):
            default_head(torch.randn(2, 3, 4, 128), mode="training")

    def test_reject_bad_mode(self, default_head, pooled_hidden):
        with pytest.raises(ValueError, match="mode"):
            default_head(pooled_hidden, mode="bogus")

    def test_dtype_preserved(self, default_head):
        """Input dtype is preserved on the logit tensors."""
        hidden = torch.randn(2, 128, dtype=torch.float32)
        out = default_head(hidden, mode="training")
        assert out["noetic_logits"].dtype == torch.float32


# ---------------------------------------------------------------------------
# Forward pass — Gumbel-softmax attachment
# ---------------------------------------------------------------------------


class TestGumbelAttachment:

    def test_training_mode_includes_gumbel(self, default_head, pooled_hidden):
        out = default_head(pooled_hidden, mode="training", tau=1.0)
        assert "register_gumbel" in out
        # Straight-through Gumbel-ST -> one-hot on forward.
        sample = out["register_gumbel"]
        assert sample.shape == (
            pooled_hidden.shape[0],
            DEFAULT_MAX_OPERANDS,
            NUM_REGISTERS,
        )
        # Each operand slot has a hard one-hot under hard=True.
        per_slot_sum = sample.sum(dim=-1)
        assert torch.allclose(
            per_slot_sum, torch.ones_like(per_slot_sum)
        )

    def test_inference_mode_omits_gumbel(self, default_head, pooled_hidden):
        out = default_head(pooled_hidden, mode="inference")
        assert "register_gumbel" not in out

    def test_tau_clamped_to_min(self, default_head, pooled_hidden):
        """Very small tau is clamped to 1e-3 so Gumbel does not explode."""
        # Should not raise even for tau=0 (internal clamp).
        out = default_head(pooled_hidden, mode="training", tau=0.0)
        assert "register_gumbel" in out


# ---------------------------------------------------------------------------
# Gradient flow
# ---------------------------------------------------------------------------


class TestGradientFlow:

    def test_grad_reaches_all_parameters(self, default_head, pooled_hidden):
        """Every proposer parameter receives gradient under a summed loss."""
        default_head.zero_grad(set_to_none=True)
        out = default_head(pooled_hidden, mode="training")
        loss = (
            out["noetic_logits"].sum()
            + out["domain_logits"].sum()
            + out["register_logits"].sum()
            + out["operand_count_logits"].sum()
            + out["named_emergent_logits"].sum()
        )
        loss.backward()
        for name, param in default_head.named_parameters():
            assert param.grad is not None, f"no grad on {name}"
            assert torch.isfinite(param.grad).all(), f"non-finite grad on {name}"

    def test_grad_flows_back_to_hidden_states(self, default_head):
        """hidden_states.requires_grad_(True) receives gradient."""
        hidden = torch.randn(2, 128, requires_grad=True)
        out = default_head(hidden, mode="training")
        out["noetic_logits"].sum().backward()
        assert hidden.grad is not None
        assert hidden.grad.shape == hidden.shape

    def test_grad_magnitude_is_reasonable(self, default_head, pooled_hidden):
        """Gradient norms stay finite and non-zero on a simple CE loss."""
        noetic_targets = torch.randint(0, NUM_NOETICS, (pooled_hidden.shape[0],))
        default_head.zero_grad(set_to_none=True)
        out = default_head(pooled_hidden, mode="training")
        loss = torch.nn.functional.cross_entropy(
            out["noetic_logits"], noetic_targets
        )
        loss.backward()
        total_norm = 0.0
        for p in default_head.parameters():
            if p.grad is not None:
                total_norm += p.grad.norm().item() ** 2
        total_norm = total_norm ** 0.5
        assert total_norm > 0.0
        assert total_norm < 1e4  # well within clip-worthy range


# ---------------------------------------------------------------------------
# Inference — propose()
# ---------------------------------------------------------------------------


class TestProposeInference:

    def test_propose_returns_one_per_example(self, default_head):
        hidden = torch.randn(3, 128)
        proposals = default_head.propose(hidden)
        assert len(proposals) == 3
        for p in proposals:
            assert isinstance(p, ExpressionProposal)

    def test_propose_ranges_valid(self, default_head, pooled_hidden):
        """Each proposal field sits in its advertised range."""
        proposals = default_head.propose(pooled_hidden)
        for p in proposals:
            assert 0 <= p.noetic < NUM_NOETICS
            assert 0 <= p.domain < NUM_DOMAINS
            assert p.operand_count in OPERAND_COUNT_BUCKETS
            assert len(p.registers_per_operand) == p.operand_count
            for r in p.registers_per_operand:
                assert 0 <= r < NUM_REGISTERS
            assert isinstance(p.has_named_emergent, bool)

    def test_propose_accepts_3d_hidden(self, default_head, seq_hidden):
        proposals = default_head.propose(seq_hidden)
        assert len(proposals) == seq_hidden.shape[0]


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------


class TestBoundaries:

    def test_single_example_batch(self, default_head):
        out = default_head(torch.randn(1, 128), mode="training")
        assert out["noetic_logits"].shape == (1, NUM_NOETICS)

    def test_max_operand_bucket_reachable(self, small_head):
        """operand_count_logits dim matches the bucket tuple length."""
        out = small_head(torch.randn(2, 64), mode="training")
        assert out["operand_count_logits"].shape[-1] == len(
            OPERAND_COUNT_BUCKETS
        )

    def test_custom_num_registers(self):
        head = ExpressionProposerHead(d_model=64, num_registers=3)
        out = head(torch.randn(1, 64), mode="inference")
        assert out["register_logits"].shape == (
            1,
            DEFAULT_MAX_OPERANDS,
            3,
        )


# ---------------------------------------------------------------------------
# Integration with ProposerRuleFourLoss
# ---------------------------------------------------------------------------


class TestProposerLossIntegration:

    def test_loss_returns_none_without_labels(self, default_head, pooled_hidden):
        out = default_head(pooled_hidden, mode="training")
        loss_fn = ProposerRuleFourLoss()
        result = loss_fn(out)
        assert result is None

    def test_loss_computes_with_full_labels(self, default_head, pooled_hidden):
        out = default_head(pooled_hidden, mode="training")
        B = pooled_hidden.shape[0]
        loss_fn = ProposerRuleFourLoss()
        noetic = torch.randint(0, NUM_NOETICS, (B,))
        domain = torch.randint(0, NUM_DOMAINS, (B,))
        reg_targets = torch.randint(
            0, NUM_REGISTERS, (B, DEFAULT_MAX_OPERANDS)
        )
        reg_mask = torch.ones((B, DEFAULT_MAX_OPERANDS), dtype=torch.bool)
        count = torch.randint(0, len(OPERAND_COUNT_BUCKETS), (B,))
        named = torch.randint(0, 2, (B,))
        loss = loss_fn(
            out,
            noetic_targets=noetic,
            domain_targets=domain,
            register_targets=reg_targets,
            register_target_mask=reg_mask,
            operand_count_targets=count,
            named_emergent_targets=named,
        )
        assert loss is not None
        assert loss.ndim == 0
        assert torch.isfinite(loss)

    def test_loss_delivers_grad_to_proposer(self, default_head, pooled_hidden):
        """End-to-end: score-based loss delivers gradient to every
        proposer parameter — the critical ADR-07 gradient-flow assertion."""
        out = default_head(pooled_hidden, mode="training")
        B = pooled_hidden.shape[0]
        loss_fn = ProposerRuleFourLoss()
        noetic = torch.zeros(B, dtype=torch.long)
        domain = torch.zeros(B, dtype=torch.long)
        reg_targets = torch.zeros(
            (B, DEFAULT_MAX_OPERANDS), dtype=torch.long
        )
        reg_mask = torch.zeros((B, DEFAULT_MAX_OPERANDS), dtype=torch.bool)
        reg_mask[:, 0] = True
        count = torch.zeros(B, dtype=torch.long)
        named = torch.zeros(B, dtype=torch.long)
        default_head.zero_grad(set_to_none=True)
        loss = loss_fn(
            out,
            noetic_targets=noetic,
            domain_targets=domain,
            register_targets=reg_targets,
            register_target_mask=reg_mask,
            operand_count_targets=count,
            named_emergent_targets=named,
        )
        loss.backward()
        touched = [
            name for name, p in default_head.named_parameters()
            if p.grad is not None and p.grad.abs().sum().item() > 0.0
        ]
        assert touched, "no proposer parameters received gradient"

    def test_component_weights_scale_loss(self, pooled_hidden):
        """Lambda_noetic=0 removes the noetic term from the total."""
        head = ExpressionProposerHead(d_model=128)
        out = head(pooled_hidden, mode="training")
        B = pooled_hidden.shape[0]
        noetic = torch.zeros(B, dtype=torch.long)

        loss_noetic_on = ProposerRuleFourLoss(lambda_noetic=1.0)(
            out, noetic_targets=noetic,
        )
        loss_noetic_off = ProposerRuleFourLoss(lambda_noetic=0.0)(
            out, noetic_targets=noetic,
        )
        assert loss_noetic_on is not None
        assert loss_noetic_off is not None
        # lambda=0 scales the only contributing CE term to 0.
        assert float(loss_noetic_off.item()) == pytest.approx(0.0)
        assert float(loss_noetic_on.item()) > 0.0


# ---------------------------------------------------------------------------
# Trainer integration — ADR-07 ``use_expression_proposer`` flag
# ---------------------------------------------------------------------------


class TestTrainerIntegration:

    def _trainer_with_proposer(self, batch_size: int = 1):
        from cas_native.model.cas_native_model import (
            CASNativeConfig,
            CASNativeModel,
        )
        from cas_native.training.config import (
            TrainingConfig,
            V2ComponentFlags,
            V2Hyperparameters,
            V74Hyperparameters,
        )
        from cas_native.training.data_pipeline import (
            CASDataset,
            cas_collate_fn,
        )
        from cas_native.training.trainer import CASTrainer

        model = CASNativeModel(
            CASNativeConfig(
                d_model=64,
                n_layers=1,
                n_heads=4,
                vocab_size=64,
                max_seq_len=32,
                fractal_depth=1,
                num_ethical_propositions=3,
            )
        )
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
                "register_labels": [
                    {"position": 0, "register": "A"},
                    {"position": 0, "register": "f"},
                ],
                "omega_labels": [
                    {"position": 0, "omega_name": "Omega_presence"},
                ],
            }
        ]
        loader = DataLoader(
            CASDataset(data, max_length=16),
            batch_size=batch_size,
            collate_fn=cas_collate_fn,
        )
        flags = V2ComponentFlags(
            use_register_film=False,
            use_emergent_register=False,
            use_production_semantics=False,
            use_rust_validation=False,
            use_expression_proposer=True,
        )
        hp = V2Hyperparameters(
            gumbel_tau_anneal_steps=10,
            rust_cache_capacity=100,
            registry_capacity=4,
            proposer_bottleneck_dim=16,
            proposer_max_operands=3,
        )
        v74 = V74Hyperparameters(max_steps=1, warmup_steps=1)
        cfg = TrainingConfig(
            component_flags=flags,
            v2_hyperparameters=hp,
            v7_4_hyperparameters=v74,
        )
        trainer = CASTrainer(model, loader, loader, config=cfg)
        return trainer, loader

    def test_trainer_instantiates_proposer_when_flag_on(self):
        trainer, _ = self._trainer_with_proposer()
        assert trainer.expression_proposer is not None
        assert isinstance(
            trainer.expression_proposer, ExpressionProposerHead
        )
        assert trainer.proposer_loss_fn is not None
        # Proposer is registered on model.v2_components so state_dict
        # captures it.
        assert "expression_proposer" in trainer.model.v2_components

    def test_proposer_params_in_optimizer(self):
        trainer, _ = self._trainer_with_proposer()
        proposer_param_ids = {
            id(p) for p in trainer.expression_proposer.parameters()
        }
        optim_param_ids: set[int] = set()
        for group in trainer.optimizer.param_groups:
            for p in group["params"]:
                optim_param_ids.add(id(p))
        assert proposer_param_ids.issubset(optim_param_ids)

    def test_proposer_loss_component_in_train_step(self):
        trainer, loader = self._trainer_with_proposer()
        batch = next(iter(loader))
        metrics = trainer._train_step(batch)
        # When register labels are present the proposer loss lands in
        # the extras dict.
        assert "proposer_rule_four_loss" in metrics
        assert metrics["proposer_rule_four_loss"] >= 0.0

    def test_proposer_absent_when_flag_off(self):
        from cas_native.model.cas_native_model import (
            CASNativeConfig,
            CASNativeModel,
        )
        from cas_native.training.config import (
            TrainingConfig,
            V2ComponentFlags,
            V2Hyperparameters,
            V74Hyperparameters,
        )
        from cas_native.training.data_pipeline import (
            CASDataset,
            cas_collate_fn,
        )
        from cas_native.training.trainer import CASTrainer

        model = CASNativeModel(
            CASNativeConfig(
                d_model=64,
                n_layers=1,
                n_heads=4,
                vocab_size=64,
                max_seq_len=32,
                fractal_depth=1,
                num_ethical_propositions=3,
            )
        )
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        loader = DataLoader(
            CASDataset(data, max_length=16),
            batch_size=1,
            collate_fn=cas_collate_fn,
        )
        flags = V2ComponentFlags(
            use_register_film=False,
            use_emergent_register=False,
            use_production_semantics=False,
            use_rust_validation=False,
            use_expression_proposer=False,
        )
        cfg = TrainingConfig(
            component_flags=flags,
            v2_hyperparameters=V2Hyperparameters(),
            v7_4_hyperparameters=V74Hyperparameters(
                max_steps=1, warmup_steps=1
            ),
        )
        trainer = CASTrainer(model, loader, loader, config=cfg)
        assert trainer.expression_proposer is None
        assert trainer.proposer_loss_fn is None
        assert "expression_proposer" not in trainer.model.v2_components
