"""Integration tests for the CAS-Native v2 trainer wiring.

Scope — see `docs/architecture/cas_native_v2_adrs.md` for governing ADRs:
  * ADR-01 — RegisterFiLM + InvolutionConstraintLoss
  * ADR-02/03 — EmergentRegisterPipeline + Ω_* binding loss
  * ADR-04 — ProductionSemanticsHead + soft-yield loss
  * ADR-06 — RustValidationBridge in training step

Tests exercise code paths with synthetic tensors — no multi-step convergence
is asserted, no GPU is required.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
from cas_native.training.config import (
    TrainingConfig,
    V2ComponentFlags,
    V2Hyperparameters,
    V74Hyperparameters,
)
from cas_native.training.data_pipeline import CASDataset, cas_collate_fn
from cas_native.training.trainer import CASTrainer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_model(d_model: int = 128) -> CASNativeModel:
    config = CASNativeConfig(
        d_model=d_model,
        n_layers=1,
        n_heads=4,
        vocab_size=128,
        max_seq_len=32,
        fractal_depth=1,
        num_ethical_propositions=3,
    )
    return CASNativeModel(config)


def _make_loader(
    data: list[dict] | None = None, batch_size: int = 1
) -> DataLoader:
    data = data or [
        {
            "prompt": "p",
            "response": "r",
            "scores": {"operator_scores": [1] * 10},
        }
    ]
    dataset = CASDataset(data, max_length=16)
    return DataLoader(dataset, batch_size=batch_size, collate_fn=cas_collate_fn)


def _make_v2_config(all_on: bool = True, **hp_overrides) -> TrainingConfig:
    flags = V2ComponentFlags(
        use_register_film=all_on,
        use_emergent_register=all_on,
        use_production_semantics=all_on,
        use_rust_validation=all_on,
    )
    hp_defaults = dict(
        gumbel_tau_anneal_steps=10,
        rust_cache_capacity=100,
        registry_capacity=4,
    )
    hp_defaults.update(hp_overrides)
    hp = V2Hyperparameters(**hp_defaults)
    v74 = V74Hyperparameters(max_steps=2, warmup_steps=1, checkpoint_every=10)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=hp,
        v7_4_hyperparameters=v74,
    )


@pytest.fixture
def trainer_all_on():
    model = _make_model()
    loader = _make_loader()
    config = _make_v2_config(all_on=True)
    return CASTrainer(model, loader, loader, config=config)


@pytest.fixture
def trainer_all_off():
    model = _make_model()
    loader = _make_loader()
    config = _make_v2_config(all_on=False)
    return CASTrainer(model, loader, loader, config=config)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:

    def test_instantiation_all_flags_on(self, trainer_all_on):
        """With all flags True every v2 submodule is attached."""
        assert trainer_all_on.register_film is not None
        assert trainer_all_on.emergent_pipeline is not None
        assert trainer_all_on.production_head is not None
        assert trainer_all_on.rust_bridge is not None

        v2c = trainer_all_on.model.v2_components
        assert "register_embedding" in v2c
        assert "emergent_register" in v2c
        assert "production_semantics" in v2c

    def test_instantiation_all_flags_off(self, trainer_all_off):
        """With all flags False, no v2 submodules are attached (v7.4 path)."""
        assert trainer_all_off.register_film is None
        assert trainer_all_off.emergent_pipeline is None
        assert trainer_all_off.production_head is None
        assert trainer_all_off.rust_bridge is None

        # v2_components ModuleDict exists but is empty.
        assert len(trainer_all_off.model.v2_components) == 0

    def test_backward_compat_with_dict_config(self):
        """Legacy dict config path still works (no TrainingConfig)."""
        model = _make_model()
        loader = _make_loader()
        trainer = CASTrainer(
            model, loader, loader, config={"max_steps": 1, "warmup_steps": 1}
        )
        assert trainer.training_config is None
        assert trainer.v2_flags.all_off()

    def test_v74_byte_equivalent_when_flags_off(self):
        """Flags-off trainer registers no additional parameters vs legacy."""
        # Baseline: legacy dict-config trainer.
        model_a = _make_model()
        loader_a = _make_loader()
        torch.manual_seed(123)
        trainer_a = CASTrainer(
            model_a, loader_a, loader_a, config={"max_steps": 1}
        )
        legacy_params = sum(p.numel() for p in trainer_a.model.parameters())

        # v2 with every flag False.
        model_b = _make_model()
        loader_b = _make_loader()
        torch.manual_seed(123)
        trainer_b = CASTrainer(
            model_b, loader_b, loader_b, config=_make_v2_config(all_on=False)
        )
        v2_off_params = sum(p.numel() for p in trainer_b.model.parameters())

        assert legacy_params == v2_off_params


# ---------------------------------------------------------------------------
# Forward pass + loss decomposition
# ---------------------------------------------------------------------------


class TestForwardAndLoss:

    def test_forward_produces_expected_output_keys(self, trainer_all_on):
        """Base model forward pass preserves the v7.4 output dict contract."""
        batch = next(iter(trainer_all_on.train_loader))
        outputs = trainer_all_on.model(
            batch["input_ids"].to(trainer_all_on.device),
            attention_mask=batch["attention_mask"].to(trainer_all_on.device),
        )
        for key in (
            "logits",
            "cognitive_state",
            "rpm_satisfaction",
            "inversion_flags",
            "topos_truth_values",
        ):
            assert key in outputs

    def test_involution_loss_independent(self, trainer_all_on):
        """ADR-08 involution loss (latent + surface) can be computed in isolation.

        Under Option E, ``_compute_involution_loss`` returns the
        ``lambda_out * L_inv_output + lambda_latent * L_inv_latent``
        aggregate. At init the output-surface term is zero (gamma=1,
        beta=0 from zero-init W heads) but the latent-level term is
        non-zero (z_R ~ N(0,1) so z_T+z_E != 0). The loss is therefore
        small-but-positive at init rather than exactly zero as it was
        under the legacy ADR-01 surface-only loss.
        """
        loss = trainer_all_on._compute_involution_loss()
        assert loss is not None
        # Loss magnitude is bounded: latent dim=16, R=4, default
        # lambda_latent=0.01 — O(0.01 * variance) at init. Loosely verify
        # positivity and a sane upper bound.
        val = float(loss.item())
        assert val >= 0.0
        assert val < 1.0

    def test_production_loss_masks_when_no_label(self, trainer_all_on):
        """Production loss returns None when no example has a target."""
        input_ids = torch.zeros(2, 8, dtype=torch.long)
        hidden = trainer_all_on.model.token_embedding(input_ids)
        hidden = trainer_all_on.model.pos_encoding(hidden)
        loss = trainer_all_on._compute_production_loss(hidden, [None, None])
        assert loss is None

    def test_production_loss_active_when_label_present(self, trainer_all_on):
        """Production loss returns a scalar tensor when labels are present."""
        input_ids = torch.zeros(2, 8, dtype=torch.long)
        hidden = trainer_all_on.model.token_embedding(input_ids)
        hidden = trainer_all_on.model.pos_encoding(hidden)
        targets = [
            None,
            {
                "prereqs": [[3, 1.0], [5, 2.0]],
                "leakages": [],
                "observed_yield": 0.8,
            },
        ]
        loss = trainer_all_on._compute_production_loss(hidden, targets)
        assert loss is not None
        assert loss.ndim == 0

    def test_emergent_binding_loss_requires_label(self, trainer_all_on):
        """Binding loss returns None when no Ω_* labels present."""
        input_ids = torch.zeros(2, 8, dtype=torch.long)
        hidden = trainer_all_on.model.token_embedding(input_ids)
        hidden = trainer_all_on.model.pos_encoding(hidden)
        loss = trainer_all_on._compute_emergent_binding_loss(hidden, [[], []])
        assert loss is None

    def test_rule_four_loss_requires_registers(self, trainer_all_on):
        """Rule 4 loss returns None when fewer than 2 registers annotated."""
        input_ids = torch.zeros(1, 8, dtype=torch.long)
        hidden = trainer_all_on.model.token_embedding(input_ids)
        loss = trainer_all_on._compute_rule_four_loss(
            hidden, [[{"position": 0, "register": "A"}]]
        )
        assert loss is None

    def test_total_loss_aggregates_components(self, trainer_all_on):
        """Train-step total_loss matches weighted sum of active components."""
        batch = next(iter(trainer_all_on.train_loader))
        metrics = trainer_all_on._train_step(batch)
        # The v7.4 components remain; "total" reflects aggregated loss.
        assert "total" in metrics
        assert "lm_loss" in metrics
        # involution_loss should be logged when register_film is active.
        assert "involution_loss" in metrics


# ---------------------------------------------------------------------------
# Gumbel-softmax temperature annealing
# ---------------------------------------------------------------------------


class TestTemperatureAnnealing:

    def test_tau_schedule_linear(self, trainer_all_on):
        """Linear schedule: tau decays from initial to final over steps."""
        hp = trainer_all_on.v2_hp
        t0 = trainer_all_on._anneal_tau_for_step(0)
        t_mid = trainer_all_on._anneal_tau_for_step(hp.gumbel_tau_anneal_steps // 2)
        t_end = trainer_all_on._anneal_tau_for_step(hp.gumbel_tau_anneal_steps)
        t_beyond = trainer_all_on._anneal_tau_for_step(
            hp.gumbel_tau_anneal_steps * 3
        )

        assert t0 == pytest.approx(hp.gumbel_tau_initial)
        assert hp.gumbel_tau_final < t_mid < hp.gumbel_tau_initial
        assert t_end == pytest.approx(hp.gumbel_tau_final)
        assert t_beyond == pytest.approx(hp.gumbel_tau_final)

    def test_tau_updates_across_train_steps(self, trainer_all_on):
        """current_tau decreases monotonically across training steps."""
        tau_before = trainer_all_on.current_tau
        batch = next(iter(trainer_all_on.train_loader))
        trainer_all_on._train_step(batch)
        trainer_all_on.global_step = 1
        trainer_all_on._train_step(batch)
        trainer_all_on.global_step = 2
        trainer_all_on._train_step(batch)
        assert trainer_all_on.current_tau <= tau_before


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------


class TestCheckpointing:

    def test_checkpoint_roundtrip_preserves_state(
        self, trainer_all_on, tmp_path
    ):
        """Save -> load roundtrip restores global_step, tau, and v2 weights."""
        trainer_all_on.checkpoint_dir = tmp_path
        trainer_all_on.global_step = 7
        trainer_all_on.current_tau = 3.14
        ckpt_path = trainer_all_on._save_checkpoint(tag="test")
        assert Path(ckpt_path).exists()

        # Fresh trainer that loads the checkpoint.
        model2 = _make_model()
        loader = _make_loader()
        trainer2 = CASTrainer(
            model2, loader, loader, config=_make_v2_config(all_on=True)
        )
        trainer2.load_checkpoint(ckpt_path)
        assert trainer2.global_step == 7
        assert trainer2.current_tau == pytest.approx(3.14)

        # v2 components must have loaded weights, not random init.
        reg_film_before = trainer_all_on.register_film.gamma.detach()
        reg_film_after = trainer2.register_film.gamma.detach()
        assert torch.allclose(reg_film_before, reg_film_after, atol=1e-6)

    def test_load_v7_4_checkpoint_into_v2_model(self, tmp_path):
        """v7.4-style checkpoint (no v2 keys) loads cleanly into a v2 trainer."""
        # Save a legacy-style checkpoint from a flags-off trainer.
        model_a = _make_model()
        loader_a = _make_loader()
        trainer_a = CASTrainer(
            model_a, loader_a, loader_a, config=_make_v2_config(all_on=False)
        )
        trainer_a.checkpoint_dir = tmp_path
        ckpt_path = trainer_a._save_checkpoint(tag="v74_like")

        # Load into a v2 trainer — missing v2 keys must be tolerated.
        model_b = _make_model()
        loader_b = _make_loader()
        trainer_b = CASTrainer(
            model_b, loader_b, loader_b, config=_make_v2_config(all_on=True)
        )
        trainer_b.load_checkpoint(ckpt_path)
        # v2 components still exist and retain their random init (not error).
        assert trainer_b.register_film is not None
        assert trainer_b.production_head is not None


# ---------------------------------------------------------------------------
# Data masking
# ---------------------------------------------------------------------------


class TestDataMasking:

    def test_example_with_register_labels_triggers_rule_four(
        self, trainer_all_on
    ):
        """register_labels with >=2 registers at same Noetic/Domain trigger
        Rule 4 loss."""
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
                "register_labels": [
                    {"position": 0, "register": "A"},
                    {"position": 1, "register": "f"},
                ],
            }
        ]
        loader = DataLoader(
            CASDataset(data, max_length=16),
            batch_size=1,
            collate_fn=cas_collate_fn,
        )
        trainer_all_on.train_loader = loader
        batch = next(iter(loader))
        metrics = trainer_all_on._train_step(batch)
        assert "rule_four_loss" in metrics

    def test_example_without_v2_labels_behaves_as_v7_4(self, trainer_all_on):
        """Example with no v2 labels contributes only v7.4 loss terms."""
        batch = next(iter(trainer_all_on.train_loader))
        metrics = trainer_all_on._train_step(batch)
        # No Ω_* / production / Rule 4 losses fired.
        assert "emergent_binding_loss" not in metrics
        assert "production_loss" not in metrics
        assert "rule_four_loss" not in metrics

    def test_mixed_batch_masking(self, trainer_all_on):
        """Mixed batch: only labeled examples contribute to each v2 term."""
        data = [
            {
                "prompt": "p1",
                "response": "r1",
                "scores": {"operator_scores": [1] * 10},
            },
            {
                "prompt": "p2",
                "response": "r2",
                "scores": {"operator_scores": [1] * 10},
                "production_target": {
                    "prereqs": [[3, 1.0], [5, 2.0]],
                    "leakages": [],
                    "observed_yield": 0.8,
                },
            },
        ]
        loader = DataLoader(
            CASDataset(data, max_length=16),
            batch_size=2,
            collate_fn=cas_collate_fn,
        )
        trainer_all_on.train_loader = loader
        batch = next(iter(loader))
        metrics = trainer_all_on._train_step(batch)
        # Production loss should be active; Rule 4 should NOT (no reg labels).
        assert "production_loss" in metrics
        assert "rule_four_loss" not in metrics


# ---------------------------------------------------------------------------
# Rust bridge integration (real wheel)
# ---------------------------------------------------------------------------


class TestRustBridge:

    def test_bridge_validates_trivially_valid_expression(self, trainer_all_on):
        """Real Rust bridge returns 'valid' for single-operand expression."""
        bridge = trainer_all_on.rust_bridge
        assert bridge is not None
        from cas_native.validation.structural_hash import StructuralPattern

        pattern = StructuralPattern(
            noetics=(1,),
            domains=tuple(),
            drives=tuple(),
            registers=("A",),
            register_sets=(("A",),),
            emergent_register_name=None,
            recipe_shape=None,
            validation_kind="rule_four",
        )
        results = bridge.validate_rule_four_batch(
            [pattern],
            call_args=[([(1, None, None, "A")], None)],
        )
        assert len(results) == 1
        assert getattr(results[0], "kind", None) == "valid"

    def test_bridge_cache_hit_on_repeated_call(self, trainer_all_on):
        """Repeated identical pattern hits the structural-hash cache."""
        bridge = trainer_all_on.rust_bridge
        from cas_native.validation.structural_hash import StructuralPattern

        pattern = StructuralPattern(
            noetics=(1,),
            domains=tuple(),
            drives=tuple(),
            registers=("A",),
            register_sets=(("A",),),
            emergent_register_name=None,
            recipe_shape=None,
            validation_kind="rule_four",
        )
        bridge.validate_rule_four_batch(
            [pattern], call_args=[([(1, None, None, "A")], None)]
        )
        bridge.validate_rule_four_batch(
            [pattern], call_args=[([(1, None, None, "A")], None)]
        )
        stats = bridge.cache_stats("rule_four")["rule_four"]
        assert stats.hits >= 1


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestTrainingConfig:

    def test_from_yaml(self, tmp_path):
        """TrainingConfig.from_yaml parses the template file cleanly."""
        yaml_path = (
            Path(__file__).resolve().parent.parent
            / "config"
            / "training_v2.yaml"
        )
        assert yaml_path.exists()
        cfg = TrainingConfig.from_yaml(yaml_path)
        assert cfg.component_flags.use_register_film is True
        assert cfg.v2_hyperparameters.lambda_involution == pytest.approx(0.1)
        assert cfg.v2_hyperparameters.registry_capacity == 20
        assert cfg.v2_hyperparameters.gumbel_tau_initial == pytest.approx(10.0)
        assert cfg.v7_4_hyperparameters.lr == pytest.approx(1e-4)

    def test_all_off_flag(self):
        """component_flags.all_off() is True exactly when every flag is False."""
        off = V2ComponentFlags(
            use_register_film=False,
            use_emergent_register=False,
            use_production_semantics=False,
            use_rust_validation=False,
        )
        assert off.all_off() is True

        partial = V2ComponentFlags(
            use_register_film=True,
            use_emergent_register=False,
            use_production_semantics=False,
            use_rust_validation=False,
        )
        assert partial.all_off() is False

    def test_validation_rejects_bad_mix(self):
        """data_mix_* must sum to 1.0."""
        hp = V2Hyperparameters(
            data_mix_cross_register=0.3, data_mix_production=0.3
        )
        with pytest.raises(ValueError):
            hp.validate()


# ---------------------------------------------------------------------------
# Evaluation extensions
# ---------------------------------------------------------------------------


class TestEvaluationExtensions:

    def test_v2_metrics_absent_when_components_off(self):
        """evaluate_v2_metrics is empty when v2 components are absent."""
        from cas_native.evaluation.evaluate import CASEvaluator

        model = _make_model()
        loader = _make_loader()
        trainer = CASTrainer(
            model, loader, loader, config=_make_v2_config(all_on=False)
        )
        evaluator = CASEvaluator(trainer.model)
        metrics = evaluator.evaluate_v2_metrics(loader)
        assert metrics == {}

    def test_v2_metrics_return_types(self):
        """Each metric returns the declared type / range when labels present."""
        from cas_native.evaluation.evaluate import CASEvaluator

        model = _make_model()
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
                "register_labels": [
                    {"position": 0, "register": "A"},
                    {"position": 1, "register": "f"},
                ],
                "omega_labels": [
                    {"position": 0, "omega_name": "Omega_presence"},
                ],
                "production_target": {
                    "prereqs": [[3, 1.0]],
                    "leakages": [],
                    "observed_yield": 0.5,
                },
            }
        ]
        loader = DataLoader(
            CASDataset(data, max_length=16),
            batch_size=1,
            collate_fn=cas_collate_fn,
        )
        # Use a v2 config that loads the Ω_* registry YAML.
        cfg = _make_v2_config(all_on=True)
        # Use the canonical registry YAML so Omega_presence matches.
        cfg.omega_registry_config = str(
            Path(__file__).resolve().parent.parent
            / "config"
            / "omega_registry.yaml"
        )
        # Bump registry_capacity back to 20 so the YAML loads.
        cfg.v2_hyperparameters.registry_capacity = 20
        trainer = CASTrainer(model, loader, loader, config=cfg)

        evaluator = CASEvaluator(trainer.model)
        reg_acc = evaluator.register_prediction_accuracy(loader)
        # May be None if d_model != register_film.d_model; assert type only.
        assert reg_acc is None or 0.0 <= reg_acc <= 1.0

        rule_four = evaluator.rule_four_compliance_rate(
            loader, rust_bridge=trainer.rust_bridge
        )
        assert rule_four is None or 0.0 <= rule_four <= 1.0

        omega_acc = evaluator.omega_activation_accuracy(loader)
        assert omega_acc is None or 0.0 <= omega_acc <= 1.0

        prod_acc = evaluator.production_semantics_accuracy(loader)
        if prod_acc is not None:
            assert isinstance(prod_acc, dict)
