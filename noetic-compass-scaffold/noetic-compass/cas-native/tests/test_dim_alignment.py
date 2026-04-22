"""Tests for d_model dimension alignment across v2 components.

Covers Wave 7A follow-up #5 (trainer integration commit 357eb77 flagged a
d_model mismatch between the base model and the FiLM/binding-head components;
register-dependent eval metrics silently returned None). The fix
(`CognitiveStateEmbeddingWithRegister.register_film_dmodel`) is option (a):
make the register FiLM feeding the binding head configurable and inherit from
`CASNativeConfig.d_model` so every v2 component aligns at the model's native
hidden dim.

Principle under test: **single source of truth for d_model is
`CASNativeConfig.d_model`**. Every downstream v2 component (RegisterFiLM
operating at the binding-head width, EmergentRegisterBindingHead,
OmegaRegistry, per-example evaluation metrics) must align at that d_model
whether it is 64, 128, 256, or any other positive width.
"""

from __future__ import annotations

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.embedding import (
    CognitiveStateEmbeddingWithRegister,
    NUM_COGNITIVE_STATES,
)
from cas_native.model.emergent_register import (
    EmergentRegisterBindingHead,
    EmergentRegisterPipeline,
    OmegaRegistry,
)
from cas_native.model.register_film import NUM_REGISTERS
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


def _make_model(d_model: int) -> CASNativeModel:
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


def _make_loader() -> DataLoader:
    data = [
        {
            "prompt": "dim-alignment test prompt",
            "response": "dim-alignment test response",
            "scores": {"operator_scores": [0.5] * 10},
        }
    ]
    dataset = CASDataset(data, max_length=16)
    return DataLoader(dataset, batch_size=1, collate_fn=cas_collate_fn)


def _v2_config_all_on(registry_capacity: int = 4) -> TrainingConfig:
    flags = V2ComponentFlags(
        use_register_film=True,
        use_emergent_register=True,
        use_production_semantics=True,
        # Rust validation disabled so the test does not depend on the Rust
        # bridge being importable — the dim-alignment claim is not about
        # Rust validation.
        use_rust_validation=False,
    )
    hp = V2Hyperparameters(
        gumbel_tau_anneal_steps=10,
        rust_cache_capacity=100,
        registry_capacity=registry_capacity,
    )
    v74 = V74Hyperparameters(max_steps=1, warmup_steps=0, checkpoint_every=10)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=hp,
        v7_4_hyperparameters=v74,
    )


# ---------------------------------------------------------------------------
# Core alignment tests — at several d_model widths.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("d_model", [64, 128, 256])
def test_config_drives_all_v2_components_to_same_d_model(d_model: int) -> None:
    """CASNativeConfig.d_model is the single source of truth; all v2
    components align to it through the trainer's instantiation path."""
    model = _make_model(d_model)
    loader = _make_loader()
    trainer = CASTrainer(model, loader, loader, config=_v2_config_all_on())

    # Register FiLM operating at d_model (for binding-head feed) must match.
    assert trainer.register_film is not None
    assert trainer._register_film_dmodel_module is not None
    assert trainer._register_film_dmodel_module.d_model == d_model

    # Emergent pipeline binding head + registry both sized at d_model.
    pipeline = trainer.emergent_pipeline
    assert pipeline is not None
    assert pipeline.binding_head.d_model == d_model
    assert pipeline.registry.d_model == d_model

    # binding_projection is a Linear(d_model, d_model, bias=False) — exactly
    # d_model^2 parameters.
    bp = pipeline.binding_head.binding_projection
    assert bp.weight.shape == (d_model, d_model)
    assert sum(p.numel() for p in bp.parameters()) == d_model * d_model


def test_embedding_propagates_d_model_to_dmodel_film() -> None:
    """CognitiveStateEmbeddingWithRegister exposes register_film_dmodel sized
    at the base model's d_model (distinct from the 40-dim simplex FiLM)."""
    d_model = 256
    emb = CognitiveStateEmbeddingWithRegister(d_model=d_model)

    # Simplex FiLM stays at num_states (40) — unchanged v7.5 semantics.
    assert emb.register_film.d_model == NUM_COGNITIVE_STATES
    # New FiLM matches base d_model exactly.
    assert emb.register_film_dmodel.d_model == d_model
    # Both FiLMs have NUM_REGISTERS registers.
    assert emb.register_film.num_registers == NUM_REGISTERS
    assert emb.register_film_dmodel.num_registers == NUM_REGISTERS


@pytest.mark.parametrize("d_model", [64, 128, 256])
def test_emergent_binding_head_d_model_squared_params(d_model: int) -> None:
    """EmergentRegisterBindingHead has exactly d_model^2 params at any d."""
    head = EmergentRegisterBindingHead(d_model=d_model)
    total = sum(p.numel() for p in head.parameters())
    assert total == d_model * d_model
    assert head.binding_projection.weight.shape == (d_model, d_model)


@pytest.mark.parametrize("d_model", [64, 128, 256])
def test_omega_registry_embedding_width_matches_d_model(d_model: int) -> None:
    """OmegaRegistry embeddings are (capacity, d_model) at any d."""
    capacity = 5
    registry = OmegaRegistry(d_model=d_model, capacity=capacity)
    assert registry.registry.shape == (capacity, d_model)
    assert registry.d_model == d_model


# ---------------------------------------------------------------------------
# Trainer forward / backward succeeds at d_model != 128.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("d_model", [64, 256])
def test_trainer_instantiation_and_step_at_non_default_d_model(
    d_model: int,
) -> None:
    """Trainer instantiation + one _train_step completes at d_model != 128.

    Regresses the pre-fix behavior where emergent-binding silently returned
    None (or raised) because the register FiLM was sized at 40 while the
    binding head was sized at config.d_model.
    """
    model = _make_model(d_model)
    loader = _make_loader()
    trainer = CASTrainer(model, loader, loader, config=_v2_config_all_on())

    batch = next(iter(loader))
    # _train_step must not raise at any d_model width.
    metrics = trainer._train_step(batch)
    assert "total" in metrics
    # Register FiLM is enabled, so involution loss should be present in the
    # returned metrics dict (zero at identity init but present as a key).
    assert "involution_loss" in metrics


# ---------------------------------------------------------------------------
# Evaluation metrics do not silently return None due to dim mismatch.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("d_model", [64, 256])
def test_evaluation_register_prediction_does_not_silently_drop_samples(
    d_model: int,
) -> None:
    """At non-default d_model, register_prediction_accuracy must still run
    the FiLM scoring path instead of silently skipping examples.

    Pre-fix: pooled.shape[-1] != register_film.d_model (which was 40)
    triggered a `scores = []; break`, skipping every example and returning
    None. Post-fix: register_film (simplex) is 40-dim and pooled from the
    simplex output IS 40-dim, so the path aligns at any d_model.
    """
    from cas_native.evaluation.evaluate import CASEvaluator

    model = _make_model(d_model)
    loader = _make_loader()
    trainer = CASTrainer(model, loader, loader, config=_v2_config_all_on())

    evaluator = CASEvaluator(trainer.model)
    # Provide a loader containing register_labels so the accuracy function
    # actually enters its scoring path.
    labeled_data = [
        {
            "prompt": "reg prediction prompt",
            "response": "reg prediction response",
            "scores": {"operator_scores": [0.5] * 10},
            "register_labels": [{"register": "A"}],
        }
    ]
    dataset = CASDataset(labeled_data, max_length=16)
    labeled_loader = DataLoader(dataset, batch_size=1, collate_fn=cas_collate_fn)
    acc = evaluator.register_prediction_accuracy(labeled_loader)
    # Must be a float in [0,1] — NOT None — at any d_model.
    assert acc is not None
    assert 0.0 <= acc <= 1.0


def test_v2_emergent_pipeline_end_to_end_at_non_default_dim() -> None:
    """EmergentRegisterPipeline binding -> similarity at d_model=192.

    Not a trainer-level test; directly exercises the pipeline at a non-128
    width with synthetic inputs, matching what the binding head receives
    when fed register_film_dmodel outputs. Admits one Omega and verifies
    the similarity dict is populated at that d_model.
    """
    d_model = 192
    pipeline = EmergentRegisterPipeline(
        d_model=d_model,
        registry_capacity=4,
    )
    pipeline.registry.add_omega(
        "Omega_presence",
        embedding=torch.randn(d_model),
        slot=0,
    )

    register_states = torch.randn(2, NUM_REGISTERS, d_model)
    register_activations = torch.rand(2, 10, 4, NUM_REGISTERS)

    out = pipeline(register_states, register_activations, cell=(0, 0))
    assert out["binding"].shape == (2, d_model)
    assert "Omega_presence" in out["similarities"]
    assert out["similarities"]["Omega_presence"].shape == (2,)


def test_default_128_path_unchanged() -> None:
    """Backward-compat guard: default d_model=128 still aligns every v2
    component at 128 (as before)."""
    d_model = 128
    model = _make_model(d_model)
    loader = _make_loader()
    trainer = CASTrainer(model, loader, loader, config=_v2_config_all_on())

    assert trainer._register_film_dmodel_module.d_model == 128
    assert trainer.emergent_pipeline.binding_head.d_model == 128
    assert trainer.emergent_pipeline.registry.d_model == 128
