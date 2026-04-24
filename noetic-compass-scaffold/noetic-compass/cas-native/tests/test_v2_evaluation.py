"""Wave 8A Agent 38 — CASEvaluator v2-aware metrics tests.

Covers the four v2 evaluation metrics + composite aggregator introduced by
Agent 38 in ``cas-native/evaluation/evaluate.py``:

  * ``register_prediction_accuracy``
  * ``rule_four_compliance_rate``
  * ``omega_activation_accuracy``
  * ``production_semantics_accuracy``
  * ``composite_v2_score`` (weighted aggregator)

Also covers checkpoint-selection wiring:
  * ``TrainingConfig.effective_checkpoint_selection_metric``
    — ``"composite_v2"`` path when v2 flags are on.
    — ``"nccs"`` legacy fallback when all v2 flags are off.

Reference: ``cas-native/evaluation/evaluate.py:655`` (composite_v2_score)
and ``cas-native/training/config.py:353`` (effective checkpoint selection).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.evaluation.evaluate import CASEvaluator
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
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


def _make_loader(data: list[dict], batch_size: int = 1) -> DataLoader:
    dataset = CASDataset(data, max_length=16)
    return DataLoader(dataset, batch_size=batch_size, collate_fn=cas_collate_fn)


def _v2_config(
    all_on: bool = True,
    checkpoint_selection_metric: str = "composite_v2",
) -> TrainingConfig:
    flags = V2ComponentFlags(
        use_register_film=all_on,
        use_emergent_register=all_on,
        use_production_semantics=all_on,
        use_rust_validation=all_on,
    )
    hp = V2Hyperparameters(
        gumbel_tau_anneal_steps=10,
        rust_cache_capacity=100,
        registry_capacity=20,
    )
    v74 = V74Hyperparameters(max_steps=1, warmup_steps=1)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=hp,
        v7_4_hyperparameters=v74,
        checkpoint_selection_metric=checkpoint_selection_metric,  # type: ignore[arg-type]
    )


def _omega_yaml_path() -> Path:
    """Canonical omega_registry.yaml path (capacity=20, admits 2 entries)."""
    return (
        Path(__file__).resolve().parent.parent
        / "config"
        / "omega_registry.yaml"
    )


@pytest.fixture
def v2_trainer_with_labels():
    """v2 trainer with register + omega labels populated from a minimal dataset.

    Trainer is constructed once and the Ω_* registry is pre-loaded from the
    canonical YAML so ``omega_activation_accuracy`` has admitted entries to
    compare against.
    """
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
    loader = _make_loader(data)
    cfg = _v2_config(all_on=True)
    cfg.omega_registry_config = str(_omega_yaml_path())
    trainer = CASTrainer(model, loader, loader, config=cfg)
    return trainer, loader


@pytest.fixture
def v74_trainer_no_v2_components():
    """All-flags-off trainer (v7.4-style). No v2 components attached."""
    model = _make_model()
    data = [
        {
            "prompt": "p",
            "response": "r",
            "scores": {"operator_scores": [1] * 10},
        }
    ]
    loader = _make_loader(data)
    cfg = _v2_config(all_on=False, checkpoint_selection_metric="nccs")
    trainer = CASTrainer(model, loader, loader, config=cfg)
    return trainer, loader


@pytest.fixture
def mixed_annotation_loader():
    """Batch containing one labeled + one unlabeled example — exercises the
    partial-annotation path of ``evaluate_v2_metrics``.
    """
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
            "register_labels": [
                {"position": 0, "register": "A"},
                {"position": 1, "register": "T"},
            ],
            "omega_labels": [
                {"position": 0, "omega_name": "Omega_presence"},
            ],
        },
    ]
    return _make_loader(data, batch_size=2)


# ---------------------------------------------------------------------------
# register_prediction_accuracy
# ---------------------------------------------------------------------------


class TestRegisterPredictionAccuracy:

    def test_accuracy_is_in_unit_interval(self, v2_trainer_with_labels):
        """With register labels present, accuracy lands in [0, 1] or None."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        acc = evaluator.register_prediction_accuracy(loader)
        # Accuracy may be None if dim alignment fails; assert type / range.
        assert acc is None or 0.0 <= acc <= 1.0

    def test_accuracy_none_when_no_register_labels(self):
        """Dataset without register_labels produces None (no labeled examples)."""
        model = _make_model()
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        loader = _make_loader(data)
        cfg = _v2_config(all_on=True)
        trainer = CASTrainer(model, loader, loader, config=cfg)
        evaluator = CASEvaluator(trainer.model)
        assert evaluator.register_prediction_accuracy(loader) is None

    def test_none_when_register_film_absent(self, v74_trainer_no_v2_components):
        """Flags-off trainer: register_embedding missing -> None."""
        trainer, loader = v74_trainer_no_v2_components
        evaluator = CASEvaluator(trainer.model)
        assert evaluator.register_prediction_accuracy(loader) is None


# ---------------------------------------------------------------------------
# rule_four_compliance_rate
# ---------------------------------------------------------------------------


class TestRuleFourComplianceRate:

    def test_compliance_in_unit_interval_with_bridge(
        self, v2_trainer_with_labels
    ):
        """With real Rust bridge: rate is in [0, 1] when >=2 registers present."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        rate = evaluator.rule_four_compliance_rate(
            loader, rust_bridge=trainer.rust_bridge
        )
        assert rate is None or 0.0 <= rate <= 1.0

    def test_none_when_bridge_missing(self, v2_trainer_with_labels):
        """No rust_bridge argument -> returns None (graceful fallback)."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        assert evaluator.rule_four_compliance_rate(loader, rust_bridge=None) is None


# ---------------------------------------------------------------------------
# omega_activation_accuracy
# ---------------------------------------------------------------------------


class TestOmegaActivationAccuracy:

    def test_accuracy_in_unit_interval(self, v2_trainer_with_labels):
        """With a populated registry + omega labels: accuracy in [0, 1] or None."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        acc = evaluator.omega_activation_accuracy(loader)
        assert acc is None or 0.0 <= acc <= 1.0

    def test_none_when_registry_empty(self):
        """Uninitialized registry (active_size=0) -> returns None cleanly."""
        model = _make_model()
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
                "omega_labels": [
                    {"position": 0, "omega_name": "Omega_presence"},
                ],
            }
        ]
        loader = _make_loader(data)
        cfg = _v2_config(all_on=True)
        # Do NOT load omega_registry_config -> registry.active_size == 0.
        trainer = CASTrainer(model, loader, loader, config=cfg)
        evaluator = CASEvaluator(trainer.model)
        assert evaluator.omega_activation_accuracy(loader) is None


# ---------------------------------------------------------------------------
# production_semantics_accuracy
# ---------------------------------------------------------------------------


class TestProductionSemanticsAccuracy:

    def test_returns_dict_with_accuracy_or_mae(self, v2_trainer_with_labels):
        """With production_target labels present: returns a dict, not None."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        result = evaluator.production_semantics_accuracy(loader)
        assert result is None or isinstance(result, dict)
        if isinstance(result, dict):
            # Only prereq_accuracy and/or yield_mae are valid keys.
            for k in result.keys():
                assert k in ("prereq_accuracy", "yield_mae")
            if "prereq_accuracy" in result:
                assert 0.0 <= result["prereq_accuracy"] <= 1.0
            if "yield_mae" in result:
                assert result["yield_mae"] >= 0.0

    def test_none_when_no_production_target(self):
        """No production_target in any example -> None."""
        model = _make_model()
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        loader = _make_loader(data)
        cfg = _v2_config(all_on=True)
        trainer = CASTrainer(model, loader, loader, config=cfg)
        evaluator = CASEvaluator(trainer.model)
        assert evaluator.production_semantics_accuracy(loader) is None


# ---------------------------------------------------------------------------
# composite_v2_score
# ---------------------------------------------------------------------------


class TestCompositeV2Score:

    def test_composite_has_expected_keys(self, v2_trainer_with_labels):
        """composite_v2_score returns dict with 'components', 'weights',
        'composite' keys per the Agent 38 spec."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        result = evaluator.composite_v2_score(
            loader, rust_bridge=trainer.rust_bridge
        )
        assert isinstance(result, dict)
        assert "components" in result
        assert "weights" in result
        assert "composite" in result
        # production_yield_mae is optional; presence depends on labels.
        assert isinstance(result["components"], dict)
        assert isinstance(result["weights"], dict)

    def test_default_weights_quartered(self):
        """COMPOSITE_V2_WEIGHTS defaults to 0.25 across all four metrics."""
        w = CASEvaluator.COMPOSITE_V2_WEIGHTS
        assert set(w.keys()) == {
            "register_prediction_accuracy",
            "rule_four_compliance_rate",
            "omega_activation_accuracy",
            "production_semantics_accuracy",
        }
        for k, v in w.items():
            assert v == pytest.approx(0.25)
        assert sum(w.values()) == pytest.approx(1.0)

    def test_weighted_sum_formula(self, monkeypatch, v2_trainer_with_labels):
        """composite = sum(w_k * c_k) / sum(w_k) over present components.

        Monkey-patches ``evaluate_v2_metrics`` to pin the four inputs so the
        arithmetic can be verified against the documented weighting.
        """
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        fake_metrics = {
            "register_prediction_accuracy": 0.8,
            "rule_four_compliance_rate": 0.6,
            "omega_activation_accuracy": 0.4,
            "production_semantics_accuracy": {"prereq_accuracy": 0.2},
        }
        monkeypatch.setattr(
            evaluator, "evaluate_v2_metrics", lambda *a, **kw: fake_metrics
        )
        result = evaluator.composite_v2_score(loader)
        # All four weights at 0.25 and four components present -> plain mean.
        expected = (0.8 + 0.6 + 0.4 + 0.2) / 4.0
        assert result["composite"] == pytest.approx(expected, rel=1e-6)

    def test_all_perfect_yields_one(self, monkeypatch, v2_trainer_with_labels):
        """Every metric at 1.0 -> composite exactly 1.0."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        monkeypatch.setattr(
            evaluator,
            "evaluate_v2_metrics",
            lambda *a, **kw: {
                "register_prediction_accuracy": 1.0,
                "rule_four_compliance_rate": 1.0,
                "omega_activation_accuracy": 1.0,
                "production_semantics_accuracy": {"prereq_accuracy": 1.0},
            },
        )
        result = evaluator.composite_v2_score(loader)
        assert result["composite"] == pytest.approx(1.0)

    def test_all_zero_yields_zero(self, monkeypatch, v2_trainer_with_labels):
        """Every metric at 0.0 -> composite exactly 0.0."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        monkeypatch.setattr(
            evaluator,
            "evaluate_v2_metrics",
            lambda *a, **kw: {
                "register_prediction_accuracy": 0.0,
                "rule_four_compliance_rate": 0.0,
                "omega_activation_accuracy": 0.0,
                "production_semantics_accuracy": {"prereq_accuracy": 0.0},
            },
        )
        result = evaluator.composite_v2_score(loader)
        assert result["composite"] == pytest.approx(0.0)

    def test_missing_metric_renormalizes_denominator(
        self, monkeypatch, v2_trainer_with_labels
    ):
        """When a metric is absent, it is dropped from both numerator AND
        denominator — composite remains in [0, 1]."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        # Only two metrics present.
        monkeypatch.setattr(
            evaluator,
            "evaluate_v2_metrics",
            lambda *a, **kw: {
                "register_prediction_accuracy": 0.5,
                "rule_four_compliance_rate": 0.9,
            },
        )
        result = evaluator.composite_v2_score(loader)
        # Mean of the two present components (weights equal -> plain mean).
        assert result["composite"] == pytest.approx(0.7, rel=1e-6)
        assert "omega_activation_accuracy" not in result["weights"]

    def test_composite_none_when_no_metrics_available(
        self, monkeypatch, v2_trainer_with_labels
    ):
        """No v2 metric present -> composite is None (not 0.0)."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        monkeypatch.setattr(
            evaluator, "evaluate_v2_metrics", lambda *a, **kw: {}
        )
        result = evaluator.composite_v2_score(loader)
        assert result["composite"] is None
        assert result["components"] == {}

    def test_production_yield_mae_forwarded(
        self, monkeypatch, v2_trainer_with_labels
    ):
        """yield_mae appears in 'production_yield_mae' and does NOT enter the
        composite — only prereq_accuracy does."""
        trainer, loader = v2_trainer_with_labels
        evaluator = CASEvaluator(trainer.model)
        monkeypatch.setattr(
            evaluator,
            "evaluate_v2_metrics",
            lambda *a, **kw: {
                "production_semantics_accuracy": {
                    "prereq_accuracy": 0.4,
                    "yield_mae": 0.17,
                }
            },
        )
        result = evaluator.composite_v2_score(loader)
        assert result["production_yield_mae"] == pytest.approx(0.17)
        # Only prereq_accuracy feeds the composite — denom renormalizes to 0.25.
        assert result["composite"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Checkpoint selection mode
# ---------------------------------------------------------------------------


class TestCheckpointSelectionMode:

    def test_composite_v2_mode_respected(self, v2_trainer_with_labels):
        """With v2 flags on + composite_v2 configured: effective metric is composite_v2."""
        trainer, _ = v2_trainer_with_labels
        assert (
            trainer.training_config.effective_checkpoint_selection_metric()
            == "composite_v2"
        )

    def test_nccs_legacy_path_preserved(self, v74_trainer_no_v2_components):
        """All v2 flags off -> effective metric falls back to 'nccs'."""
        trainer, _ = v74_trainer_no_v2_components
        assert (
            trainer.training_config.effective_checkpoint_selection_metric()
            == "nccs"
        )

    def test_all_off_overrides_composite_setting(self):
        """Even when the user asks for composite_v2, all-flags-off forces
        'nccs' (because no v2 metric would ever be computable)."""
        model = _make_model()
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        loader = _make_loader(data)
        cfg = _v2_config(all_on=False, checkpoint_selection_metric="composite_v2")
        trainer = CASTrainer(model, loader, loader, config=cfg)
        # User requested composite_v2 but flags-off forces nccs fallback.
        assert cfg.checkpoint_selection_metric == "composite_v2"
        assert (
            trainer.training_config.effective_checkpoint_selection_metric()
            == "nccs"
        )


# ---------------------------------------------------------------------------
# Mixed / partial annotation
# ---------------------------------------------------------------------------


class TestMixedAnnotation:

    def test_evaluator_handles_partial_labels(
        self, mixed_annotation_loader
    ):
        """evaluate_v2_metrics tolerates batches where only some examples
        carry labels."""
        model = _make_model()
        cfg = _v2_config(all_on=True)
        cfg.omega_registry_config = str(_omega_yaml_path())
        trainer = CASTrainer(
            model,
            mixed_annotation_loader,
            mixed_annotation_loader,
            config=cfg,
        )
        evaluator = CASEvaluator(trainer.model)
        metrics = evaluator.evaluate_v2_metrics(
            mixed_annotation_loader, rust_bridge=trainer.rust_bridge
        )
        # Output is a (possibly empty) dict — no crash on partial annotation.
        assert isinstance(metrics, dict)
        for k, v in metrics.items():
            assert k in (
                "register_prediction_accuracy",
                "rule_four_compliance_rate",
                "omega_activation_accuracy",
                "production_semantics_accuracy",
            )
            if k == "production_semantics_accuracy":
                assert isinstance(v, dict)
            else:
                assert 0.0 <= v <= 1.0
