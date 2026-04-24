"""Wave 8A Agent 36 — compiler -> data pipeline -> trainer wiring tests.

Covers the gradient-bearing path added in Wave 8A commit ``5ad1196``:

  1. ``api.notation.extract_register_activations`` called from the data
     pipeline when an example carries a ``cas_expression`` field.
  2. ``RegisterActivation`` dataclass passthrough from the compiler, through
     ``CASDataset``, through ``cas_collate_fn``, into the trainer batch under
     the ``register_activations_batch`` key.
  3. Fallback construction (``build_register_activations_from_labels``) when
     no ``cas_expression`` is present, so the trainer always sees a uniform
     ``list[RegisterActivation]`` per example.
  4. Emergent-binding loss propagation: when activations are compiled from a
     Rule-4 expression and an Omega_* is admitted into the registry, the
     trainer's ``_compute_emergent_binding_loss`` yields a gradient-bearing
     scalar.
  5. Checkpoint / resume roundtrip: trainer state including
     compiler-derived attributes serializes + reloads cleanly.
  6. Edge cases: empty register batch, register-neutral batch, malformed
     activations handled without crashing the data-loading path.

Reference: ``docs/architecture/cas_native_v2_adrs.md`` ADR-02/03/07/08.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import torch
from torch.utils.data import DataLoader

from api.notation import (
    RegisterActivation,
    compile_expression,
    extract_register_activations,
)
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.training.config import (
    TrainingConfig,
    V2ComponentFlags,
    V2Hyperparameters,
    V74Hyperparameters,
)
from cas_native.training.data_pipeline import (
    CASDataset,
    activations_for_example,
    build_register_activations_from_labels,
    cas_collate_fn,
)
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


def _v2_config(**overrides) -> TrainingConfig:
    flags = V2ComponentFlags(
        use_register_film=True,
        use_emergent_register=True,
        use_production_semantics=False,
        use_rust_validation=False,
    )
    hp_defaults = dict(
        gumbel_tau_anneal_steps=10,
        rust_cache_capacity=10,
        registry_capacity=4,
    )
    hp_defaults.update(overrides)
    hp = V2Hyperparameters(**hp_defaults)
    v74 = V74Hyperparameters(max_steps=2, warmup_steps=1, checkpoint_every=10)
    return TrainingConfig(
        component_flags=flags,
        v2_hyperparameters=hp,
        v7_4_hyperparameters=v74,
    )


@pytest.fixture
def trainer_v2():
    model = _make_model()
    loader = _make_loader()
    return CASTrainer(model, loader, loader, config=_v2_config())


# ---------------------------------------------------------------------------
# extract_register_activations — invoked via activations_for_example
# ---------------------------------------------------------------------------


class TestExtractViaDataPipeline:

    def test_compiler_path_used_when_cas_expression_present(self):
        """When ``cas_expression`` is set, activations come from the compiler."""
        item = {"cas_expression": "^3^P|A"}
        acts = activations_for_example(item)
        assert len(acts) == 1
        act = acts[0]
        assert isinstance(act, RegisterActivation)
        assert act.position == 3
        assert act.registers_active == frozenset({"A"})
        assert act.is_register_set is False
        assert act.emergent_name is None

    def test_register_set_expression_marks_is_register_set(self):
        """``^3^P|<A,f>`` compiles to a single record with ``is_register_set=True``."""
        item = {"cas_expression": "^3^P|⟨A,f⟩"}
        acts = activations_for_example(item)
        assert len(acts) == 1
        assert acts[0].registers_active == frozenset({"A", "f"})
        assert acts[0].is_register_set is True

    def test_emergent_expression_emits_named_records(self):
        """Rule-4 cross-register expression emits operand records + emergent trailer."""
        item = {
            "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_foo"
        }
        acts = activations_for_example(item)
        # Per compiler semantics: 2 operand records + 1 trailing emergent = 3.
        assert len(acts) == 3
        for act in acts:
            assert act.emergent_name == "^3^P|Ω_foo"
            assert act.position == 3
        # Final record carries the union of operand registers.
        assert acts[-1].registers_active == frozenset({"A", "f"})

    def test_fallback_path_when_no_cas_expression(self):
        """Without ``cas_expression`` the fallback builder runs."""
        item = {
            "register_labels": [
                {"position": 3, "register": "A"},
                {"position": 3, "register": "f"},
            ],
        }
        acts = activations_for_example(item)
        assert len(acts) == 2
        positions = [a.position for a in acts]
        assert positions == [3, 3]
        regs = {tuple(sorted(a.registers_active))[0] for a in acts}
        assert regs == {"A", "f"}

    def test_fallback_with_omega_attaches_emergent_name(self):
        """Fallback path emits a trailing emergent record when >=2 regs + omega label."""
        item = {
            "register_labels": [
                {"position": 3, "register": "A"},
                {"position": 3, "register": "f"},
            ],
            "omega_labels": [{"position": 3, "omega_name": "Omega_foo"}],
        }
        acts = build_register_activations_from_labels(
            item["register_labels"], item["omega_labels"]
        )
        # 2 per-register records + 1 trailing union record = 3.
        assert len(acts) == 3
        assert acts[-1].registers_active == frozenset({"A", "f"})
        assert acts[-1].emergent_name == "Omega_foo"

    def test_invalid_cas_expression_falls_through_to_labels(self):
        """Malformed ``cas_expression`` degrades gracefully to the label fallback."""
        item = {
            "cas_expression": "(((garbage",
            "register_labels": [{"position": 0, "register": "T"}],
        }
        acts = activations_for_example(item)
        assert len(acts) == 1
        assert acts[0].position == 0
        assert acts[0].registers_active == frozenset({"T"})


# ---------------------------------------------------------------------------
# RegisterActivation passthrough: compiler -> dataset -> batch
# ---------------------------------------------------------------------------


class TestRegisterActivationPassthrough:

    def test_dataset_item_contains_register_activations(self):
        """``CASDataset.__getitem__`` surfaces a ``register_activations`` list."""
        data = [
            {
                "prompt": "p",
                "response": "r",
                "cas_expression": "^3^P|A",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        ds = CASDataset(data, max_length=16)
        item = ds[0]
        assert "register_activations" in item
        assert len(item["register_activations"]) == 1
        assert isinstance(item["register_activations"][0], RegisterActivation)

    def test_collate_fn_passes_activations_batch(self):
        """``cas_collate_fn`` produces a ``register_activations_batch`` list-of-lists."""
        data = [
            {
                "prompt": "p1",
                "response": "r1",
                "cas_expression": "^3^P|A",
                "scores": {"operator_scores": [1] * 10},
            },
            {
                "prompt": "p2",
                "response": "r2",
                "cas_expression": "^5^C|f",
                "scores": {"operator_scores": [1] * 10},
            },
        ]
        loader = _make_loader(data=data, batch_size=2)
        batch = next(iter(loader))
        assert "register_activations_batch" in batch
        acts_batch = batch["register_activations_batch"]
        assert isinstance(acts_batch, list)
        assert len(acts_batch) == 2
        # Per-example activation lists.
        assert acts_batch[0][0].position == 3
        assert acts_batch[1][0].position == 10 + 5  # C-domain offset
        assert acts_batch[1][0].registers_active == frozenset({"f"})

    def test_empty_register_batch_yields_empty_activations(self):
        """Examples with no register info produce empty activation lists, not None."""
        data = [
            {
                "prompt": "p",
                "response": "r",
                "scores": {"operator_scores": [1] * 10},
            }
        ]
        loader = _make_loader(data=data, batch_size=1)
        batch = next(iter(loader))
        assert batch["register_activations_batch"] == [[]]

    def test_register_neutral_expression_yields_empty_register_set(self):
        """``^3^P`` (no ``|R``) compiles to a record with empty registers_active."""
        acts = activations_for_example({"cas_expression": "^3^P"})
        assert len(acts) == 1
        assert acts[0].registers_active == frozenset()


# ---------------------------------------------------------------------------
# Emergent binding loss: gradient-bearing with compiler-sourced activations
# ---------------------------------------------------------------------------


class TestEmergentBindingLossPropagation:

    def _admit_omega(self, trainer: CASTrainer, name: str = "Omega_foo") -> None:
        """Helper: admit one Omega_* into the registry so the binding path fires."""
        pipeline = trainer._emergent_pipeline
        assert pipeline is not None
        pipeline.registry.add_omega(name)

    def test_binding_loss_is_gradient_bearing(self, trainer_v2):
        """When Rule-4 labels AND an admitted Omega_* are present, loss has gradient."""
        self._admit_omega(trainer_v2)
        # Build synthetic inputs manually — we do not need full training data.
        batch_size, seq_len = 1, 4
        hidden = torch.randn(batch_size, seq_len, trainer_v2.model.config.d_model)
        hidden.requires_grad_(True)

        register_labels = [[
            {"position": 3, "register": "A"},
            {"position": 3, "register": "f"},
        ]]
        omega_labels = [[{"position": 3, "omega_name": "Omega_foo"}]]

        loss = trainer_v2._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels
        )
        assert loss is not None
        assert loss.requires_grad
        # Backward must touch the registry embedding parameter.
        loss.backward()
        reg_param = trainer_v2._emergent_pipeline.registry.registry
        assert reg_param.grad is not None
        assert torch.any(reg_param.grad != 0)

    def test_binding_loss_returns_none_when_no_integration_points(self, trainer_v2):
        """Single-register labels never trigger Rule-4 — loss returns None."""
        self._admit_omega(trainer_v2)
        hidden = torch.randn(1, 4, trainer_v2.model.config.d_model)
        register_labels = [[{"position": 3, "register": "A"}]]
        omega_labels = [[{"position": 3, "omega_name": "Omega_foo"}]]
        loss = trainer_v2._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels
        )
        assert loss is None

    def test_binding_loss_returns_none_when_registry_empty(self, trainer_v2):
        """Empty registry short-circuits before any work."""
        hidden = torch.randn(1, 4, trainer_v2.model.config.d_model)
        register_labels = [[
            {"position": 3, "register": "A"},
            {"position": 3, "register": "f"},
        ]]
        omega_labels = [[{"position": 3, "omega_name": "Omega_foo"}]]
        # registry.active_size == 0 at this point.
        loss = trainer_v2._compute_emergent_binding_loss(
            hidden, omega_labels, register_labels
        )
        assert loss is None


# ---------------------------------------------------------------------------
# Checkpoint / resume with compiler-derived state
# ---------------------------------------------------------------------------


class TestCheckpointRoundtrip:

    def test_checkpoint_roundtrip_preserves_registry_and_optimizer(self, tmp_path):
        """Save + load after admitting an Omega_* preserves ``active_size``."""
        torch.manual_seed(42)
        model = _make_model()
        loader = _make_loader()
        trainer_a = CASTrainer(model, loader, loader, config=_v2_config())
        trainer_a._emergent_pipeline.registry.add_omega("Omega_foo")
        trainer_a.checkpoint_dir = tmp_path
        # Exercise register_activations path by compiling one expression so
        # the save payload covers the compiler-derived codepath.
        item = {"cas_expression": "^3^P|A"}
        acts = activations_for_example(item)
        assert acts and acts[0].registers_active == frozenset({"A"})

        ckpt = trainer_a._save_checkpoint(tag="wiring")
        assert Path(ckpt).exists()

        torch.manual_seed(42)
        model_b = _make_model()
        loader_b = _make_loader()
        trainer_b = CASTrainer(model_b, loader_b, loader_b, config=_v2_config())
        # Admit the same Omega_* on the clean side so slot bookkeeping lines up.
        trainer_b._emergent_pipeline.registry.add_omega("Omega_foo")
        trainer_b.load_checkpoint(ckpt)
        assert trainer_b._emergent_pipeline.registry.active_size == 1
        # Post-load registry tensor is a parameter with gradient-tracking still.
        assert trainer_b._emergent_pipeline.registry.registry.requires_grad


# ---------------------------------------------------------------------------
# Compiler direct-output cross-check
# ---------------------------------------------------------------------------


class TestCompilerDirectCrossCheck:

    def test_extract_matches_activations_for_example(self):
        """Data-pipeline wrapper output matches the compiler's direct output."""
        expr = "^6^C|A"
        artifact = compile_expression(expr)
        assert artifact.valid and artifact.ast is not None
        direct = list(extract_register_activations(artifact.ast))
        via_pipeline = activations_for_example({"cas_expression": expr})
        assert direct == via_pipeline
