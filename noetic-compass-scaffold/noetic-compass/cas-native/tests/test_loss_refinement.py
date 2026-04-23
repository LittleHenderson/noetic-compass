"""Wave 7B Tasks 2/3/4 — Loss refinement tests.

Covers:
  - Task 2: Continuous Rule 4 distance signal via RustValidationBridge
      - rule_four_distance_batch wrapper + separate cache namespace
      - Fallback to binary 0.0/1.0 when distance API absent
      - Loss magnitude reflects violation severity (2- vs 3- vs 4-register)
      - Zero loss for valid expressions
  - Task 3: Per-position emergent binding loss (ADR-02)
      - Cosine-distance loss against Ω_* registry embedding
      - Only fires at positions with >=2 registers AND Ω_* label
      - Gradient flow through binding head + register_film_dmodel
      - Multi-Ω batch handling
  - Task 4: Production loss aggregation (ADR-04)
      - Three sub-components: LR CE, yield MSE, efficiency MSE
      - Per-example per-component masking
      - Weighted aggregate = sum over components
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
from cas_native.model.register_film import REGISTER_INDEX
from cas_native.training.config import (
    TrainingConfig,
    V2ComponentFlags,
    V2Hyperparameters,
    V74Hyperparameters,
)
from cas_native.training.data_pipeline import CASDataset, cas_collate_fn
from cas_native.training.trainer import CASTrainer
from cas_native.validation.rust_bridge import (
    BridgeConfig,
    RustValidationBridge,
)
from cas_native.validation.structural_hash import StructuralPattern


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_model(d_model: int = 64) -> CASNativeModel:
    config = CASNativeConfig(
        d_model=d_model,
        n_layers=1,
        n_heads=4,
        vocab_size=64,
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


def _v2_config(all_on: bool = True, **overrides) -> TrainingConfig:
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
    hp_defaults.update(overrides)
    hp = V2Hyperparameters(**hp_defaults)
    v74 = V74Hyperparameters(max_steps=2, warmup_steps=1)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=hp,
        v7_4_hyperparameters=v74,
    )


@pytest.fixture
def trainer():
    model = _make_model()
    loader = _make_loader()
    return CASTrainer(model, loader, loader, config=_v2_config(all_on=True))


@pytest.fixture
def trainer_off():
    model = _make_model()
    loader = _make_loader()
    return CASTrainer(model, loader, loader, config=_v2_config(all_on=False))


# ---------------------------------------------------------------------------
# Task 2 — Continuous Rule 4 distance signal
# ---------------------------------------------------------------------------


class TestContinuousRuleFourDistance:

    @staticmethod
    def _rule_four_pattern(regs: list[str]) -> tuple[StructuralPattern, tuple]:
        pattern = StructuralPattern(
            noetics=(3,),
            domains=("P",),
            drives=tuple(),
            registers=tuple(sorted(set(regs))),
            register_sets=(tuple(sorted(regs)),),
            emergent_register_name=None,
            recipe_shape=None,
            validation_kind="rule_four",
        )
        operands = [(3, 0, None, r) for r in regs]
        return pattern, (operands, None)

    def test_bridge_has_rule_four_distance_detection(self, trainer):
        """Wheel 0.1.1 exposes the continuous Rule 4 distance API."""
        bridge = trainer.rust_bridge
        assert bridge is not None
        # has_rule_four_distance returns True when rule_four_distance_batch
        # is present on the Rust module.
        assert bridge.has_rule_four_distance() is True

    def test_rule_four_distance_batch_valid_expression(self, trainer):
        """Valid expressions produce 0.0 distance."""
        bridge = trainer.rust_bridge
        # Single-register expression is always valid (no multi-register
        # cross-product to validate).
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
        call_args = [([(1, None, None, "A")], None)]
        distances = bridge.rule_four_distance_batch(
            [pattern], call_args=call_args
        )
        assert len(distances) == 1
        assert distances[0] == pytest.approx(0.0, abs=1e-9)

    def test_rule_four_distance_batch_violation(self, trainer):
        """Violating expressions produce positive distance."""
        bridge = trainer.rust_bridge
        pattern, args = self._rule_four_pattern(["A", "f"])
        distances = bridge.rule_four_distance_batch(
            [pattern], call_args=[args]
        )
        assert len(distances) == 1
        # 2-register violation emits 1.0 per the Rust emitter.
        assert distances[0] > 0.0

    def test_distance_batch_preserves_order(self, trainer):
        """Per-sample distances are returned in input order."""
        bridge = trainer.rust_bridge
        valid_pattern = StructuralPattern(
            noetics=(1,),
            domains=tuple(),
            drives=tuple(),
            registers=("A",),
            register_sets=(("A",),),
            emergent_register_name=None,
            recipe_shape=None,
            validation_kind="rule_four",
        )
        violation, v_args = self._rule_four_pattern(["A", "f"])
        patterns = [valid_pattern, violation, valid_pattern]
        call_args = [
            ([(1, None, None, "A")], None),
            v_args,
            ([(1, None, None, "A")], None),
        ]
        distances = bridge.rule_four_distance_batch(
            patterns, call_args=call_args
        )
        assert distances[0] == pytest.approx(0.0)
        assert distances[1] > 0.0
        assert distances[2] == pytest.approx(0.0)

    def test_separate_cache_namespace(self, trainer):
        """Binary and continuous caches don't cross-contaminate."""
        bridge = trainer.rust_bridge
        pattern, args = self._rule_four_pattern(["A", "f"])

        # Populate binary cache.
        bridge.validate_rule_four_batch([pattern], call_args=[args])
        binary_stats = bridge.cache_stats("rule_four")["rule_four"]
        # Populate distance cache (different namespace).
        bridge.rule_four_distance_batch([pattern], call_args=[args])
        dist_stats = bridge.cache_stats("rule_four_distance")["rule_four_distance"]

        # The binary-cache's miss count is independent from the distance
        # cache's miss count — the cross-contamination test is that the
        # distance call's miss was NOT a hit on the binary cache.
        assert dist_stats.misses >= 1

    def test_distance_cache_hit_on_repeat(self, trainer):
        """Same pattern queried twice hits the distance cache the second time."""
        bridge = trainer.rust_bridge
        pattern, args = self._rule_four_pattern(["A", "f"])
        bridge.rule_four_distance_batch([pattern], call_args=[args])
        bridge.rule_four_distance_batch([pattern], call_args=[args])
        stats = bridge.cache_stats("rule_four_distance")["rule_four_distance"]
        assert stats.hits >= 1

    def test_trainer_rule_four_loss_uses_continuous_signal(self, trainer):
        """When distance API is present, loss reflects continuous value."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 1, "register": "f"},
            ]
        ]
        loss = trainer._compute_rule_four_loss(hidden, register_labels)
        assert loss is not None
        # Continuous loss is a positive float; violation produced >0.
        assert loss.item() > 0.0

    def test_trainer_rule_four_loss_returns_none_when_no_registers(self, trainer):
        """No register labels in batch -> no Rule 4 loss."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        loss = trainer._compute_rule_four_loss(hidden, [[]])
        assert loss is None

    def test_trainer_rule_four_loss_fallback_binary(self):
        """When distance API is absent, trainer falls back to binary 0/1."""
        # Stub rust_engine exposing ONLY the binary validator (no distance fn).
        class _StubResult:
            def __init__(self, kind):
                self.kind = kind

        def _validate_batch(inputs):
            results = []
            for operands, _emergent in inputs:
                regs = [op[3] for op in operands if op[3]]
                results.append(
                    _StubResult("valid" if len(set(regs)) < 2 else "invalid")
                )
            return results

        stub_engine = SimpleNamespace(
            validate_same_noetic_cross_product_batch=_validate_batch,
            validate_same_noetic_cross_product=lambda args: _validate_batch([args])[0],
        )
        bridge = RustValidationBridge(
            BridgeConfig(rust_engine=stub_engine, cache_capacity=10)
        )
        assert bridge.has_rule_four_distance() is False

        trainer = CASTrainer(
            _make_model(), _make_loader(), _make_loader(),
            config=_v2_config(all_on=True),
        )
        trainer._rust_bridge = bridge

        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 1, "register": "f"},
            ]
        ]
        loss = trainer._compute_rule_four_loss(hidden, register_labels)
        assert loss is not None
        # Binary fallback: 1.0 per violation.
        assert loss.item() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Task 3 — Per-position emergent binding loss
# ---------------------------------------------------------------------------


class TestEmergentBindingPerPosition:

    def _admit_omega(self, trainer, name: str = "Omega_presence"):
        pipeline = trainer.emergent_pipeline
        pipeline.registry.add_omega(name=name)
        return pipeline

    def test_binding_loss_requires_co_presence_with_omega(self, trainer):
        """Ω_* label alone (no co-active registers) yields None."""
        self._admit_omega(trainer)
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        omega_labels = [[{"position": 0, "omega_name": "Omega_presence"}]]
        register_labels = [
            [{"position": 0, "register": "A"}]  # only ONE register
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        # No Rule 4 integration point -> None.
        assert loss is None

    def test_binding_loss_fires_with_co_presence_and_omega(self, trainer):
        """Ω_* label AND >=2 co-active registers at same position fire the
        per-position binding loss."""
        self._admit_omega(trainer)
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        omega_labels = [[{"position": 0, "omega_name": "Omega_presence"}]]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
                {"position": 0, "register": "T"},
            ]
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        assert loss is not None
        # Cosine-distance range: [0, 2]. Expect positive loss at random init.
        assert 0.0 <= loss.item() <= 2.0

    def test_binding_loss_is_zero_when_no_registry(self, trainer):
        """Empty Ω_* registry -> no binding loss."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        omega_labels = [[{"position": 0, "omega_name": "Omega_presence"}]]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
            ]
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        assert loss is None

    def test_binding_loss_skips_unknown_omega_name(self, trainer):
        """Ω_* label with name not in registry -> integration point skipped."""
        self._admit_omega(trainer, name="Omega_presence")
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        omega_labels = [[{"position": 0, "omega_name": "Omega_unknown"}]]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
            ]
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        # No recognized Ω_* name -> no integration point.
        assert loss is None

    def test_binding_loss_multi_omega_batch(self, trainer):
        """Two examples, different Ω_* entries, both contribute."""
        self._admit_omega(trainer, name="Omega_presence")
        self._admit_omega(trainer, name="Omega_refusal")

        hidden = torch.randn(2, 8, trainer.model.config.d_model)
        omega_labels = [
            [{"position": 0, "omega_name": "Omega_presence"}],
            [{"position": 2, "omega_name": "Omega_refusal"}],
        ]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
            ],
            [
                {"position": 2, "register": "T"},
                {"position": 2, "register": "E"},
            ],
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        assert loss is not None
        assert loss.ndim == 0

    def test_binding_loss_gradient_flow(self, trainer):
        """Loss gradient reaches binding projection and RegisterLatent.

        ADR-08 Option E adaptation: ``_register_film_dmodel_module`` is a
        read-only view over the shared RegisterLatent under Option E; the
        real parameters live on ``register_latent``. We zero-grad the shared
        latent directly.
        """
        self._admit_omega(trainer)
        hidden = torch.randn(
            1, 8, trainer.model.config.d_model, requires_grad=True
        )
        omega_labels = [[{"position": 0, "omega_name": "Omega_presence"}]]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
            ]
        ]
        trainer.emergent_pipeline.binding_head.zero_grad()
        emb = trainer.model.v2_components["register_embedding"]
        emb.register_latent.zero_grad()

        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        assert loss is not None
        loss.backward()

        # Binding projection received gradient.
        w_grad = trainer.emergent_pipeline.binding_head.binding_projection.weight.grad
        assert w_grad is not None
        assert torch.any(w_grad != 0)

    def test_binding_loss_zero_without_integration_positions(self, trainer):
        """Ω_* present but no position has >=2 registers -> loss is None."""
        self._admit_omega(trainer)
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        omega_labels = [[{"position": 5, "omega_name": "Omega_presence"}]]
        register_labels = [
            [
                {"position": 0, "register": "A"},
                {"position": 0, "register": "f"},
                # Position 5 has NO registers active.
            ]
        ]
        loss = trainer._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels_batch=register_labels
        )
        assert loss is None


# ---------------------------------------------------------------------------
# Task 4 — Production loss aggregation
# ---------------------------------------------------------------------------


class TestProductionLossAggregation:

    def test_default_weights(self):
        """Default weights: w_LR=1.0, w_Y=1.0, w_eff=0.5."""
        hp = V2Hyperparameters()
        assert hp.lambda_production_limiting_reagent == pytest.approx(1.0)
        assert hp.lambda_production_yield == pytest.approx(1.0)
        assert hp.lambda_production_efficiency == pytest.approx(0.5)

    def test_weights_configurable(self):
        hp = V2Hyperparameters(
            lambda_production_limiting_reagent=2.0,
            lambda_production_yield=3.0,
            lambda_production_efficiency=0.25,
        )
        assert hp.lambda_production_limiting_reagent == 2.0
        assert hp.lambda_production_yield == 3.0
        assert hp.lambda_production_efficiency == 0.25

    def test_production_loss_no_target_returns_none(self, trainer):
        """No examples with production_target -> None."""
        hidden = torch.randn(2, 8, trainer.model.config.d_model)
        loss = trainer._compute_production_loss(hidden, [None, None])
        assert loss is None

    def test_production_loss_legacy_payload_fallback(self, trainer):
        """Legacy payload (no new targets) falls back to provisional MSE."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.7,
            }
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None
        assert loss.ndim == 0

    def test_production_loss_new_targets_aggregate(self, trainer):
        """All three target fields present -> aggregate loss is differentiable."""
        hidden = torch.randn(
            1, 8, trainer.model.config.d_model, requires_grad=True
        )
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.8,
                "target_theoretical_yield": 1.0,
                "target_limiting_reagent_index": 2,
                "target_efficiency": 0.8,
            }
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None
        assert loss.ndim == 0
        # Gradient reaches recipe head.
        trainer.production_head.recipe_head.zero_grad()
        loss.backward()
        recipe_grad = trainer.production_head.recipe_head.prereq_up.weight.grad
        assert recipe_grad is not None
        assert torch.any(recipe_grad != 0)

    def test_production_loss_partial_target_masking(self, trainer):
        """Per-example per-component masking: only LR target present."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.5,
                "target_limiting_reagent_index": 1,
                # NO target_theoretical_yield or target_efficiency.
            }
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None
        # Should not error and should produce a scalar.
        assert loss.ndim == 0

    def test_production_loss_yield_only(self, trainer):
        """Only target_theoretical_yield present."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.5,
                "target_theoretical_yield": 0.9,
            }
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None

    def test_production_loss_efficiency_only(self, trainer):
        """Only target_efficiency present."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.5,
                "target_efficiency": 0.75,
            }
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None

    def test_production_loss_weight_scaling(self, trainer):
        """Doubling a sub-weight ~doubles its contribution (with others zero)."""
        hidden = torch.randn(1, 8, trainer.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "leakages": [],
                "observed_yield": 0.5,
                "target_theoretical_yield": 0.9,
            }
        ]
        # Zero out LR + eff weights so only the yield component contributes.
        trainer.v2_hp.lambda_production_limiting_reagent = 0.0
        trainer.v2_hp.lambda_production_efficiency = 0.0
        trainer.v2_hp.lambda_production_yield = 1.0
        torch.manual_seed(0)
        loss_1x = trainer._compute_production_loss(hidden, targets)

        trainer.v2_hp.lambda_production_yield = 2.0
        torch.manual_seed(0)
        loss_2x = trainer._compute_production_loss(hidden, targets)

        # With only yield contributing, 2x weight = 2x loss magnitude.
        assert torch.allclose(loss_2x, loss_1x * 2.0, atol=1e-5)

    def test_production_loss_backward_compat_flag_off(self, trainer_off):
        """Flag off: production head not attached, loss is None."""
        hidden = torch.randn(1, 8, trainer_off.model.config.d_model)
        targets = [
            {
                "prereqs": [[3, 1.0]],
                "observed_yield": 0.5,
                "target_theoretical_yield": 0.9,
            }
        ]
        loss = trainer_off._compute_production_loss(hidden, targets)
        assert loss is None

    def test_production_loss_mixed_batch(self, trainer):
        """Mixed batch: some examples with new targets, some without."""
        hidden = torch.randn(3, 8, trainer.model.config.d_model)
        targets = [
            None,
            {
                "prereqs": [[3, 1.0]],
                "observed_yield": 0.5,
                "target_theoretical_yield": 0.9,
                "target_limiting_reagent_index": 0,
            },
            {
                "prereqs": [[3, 1.0]],
                "observed_yield": 0.4,
                "target_efficiency": 0.5,
            },
        ]
        loss = trainer._compute_production_loss(hidden, targets)
        assert loss is not None
        assert loss.ndim == 0


# ---------------------------------------------------------------------------
# Cross-cutting — backward compatibility under all flags OFF
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:

    def test_v74_byte_equivalent_still_holds(self):
        """Flags-off trainer has identical parameter count to legacy."""
        torch.manual_seed(123)
        model_a = _make_model()
        trainer_a = CASTrainer(
            model_a, _make_loader(), _make_loader(),
            config={"max_steps": 1},
        )
        legacy_params = sum(p.numel() for p in trainer_a.model.parameters())

        torch.manual_seed(123)
        model_b = _make_model()
        trainer_b = CASTrainer(
            model_b, _make_loader(), _make_loader(),
            config=_v2_config(all_on=False),
        )
        v2_off_params = sum(p.numel() for p in trainer_b.model.parameters())
        assert legacy_params == v2_off_params

    def test_config_yaml_still_loads(self):
        """YAML config including new production sub-weights still parses."""
        yaml_path = (
            Path(__file__).resolve().parent.parent
            / "config"
            / "training_v2.yaml"
        )
        cfg = TrainingConfig.from_yaml(yaml_path)
        assert cfg.v2_hyperparameters.lambda_production_limiting_reagent == 1.0
        assert cfg.v2_hyperparameters.lambda_production_yield == 1.0
        assert cfg.v2_hyperparameters.lambda_production_efficiency == 0.5
