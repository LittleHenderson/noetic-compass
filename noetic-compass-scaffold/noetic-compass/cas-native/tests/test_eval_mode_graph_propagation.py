"""Tests for the diagloop eval-mode fix: evaluate_structured_token_prediction
propagates graph_batch when the model has graph fusion components.

Four tests:
  1. Backward compat: text-only model (graph_encoder=None) → model called with
     model(batch) only; compile_to_graph is never invoked.
  2. Graph propagation: model with graph_encoder + records with compilable
     cas_expression → model called with graph_batch not None.
  3. Mixed records: some compilable, some not → model still called with
     graph_batch (compilable ones contribute; others get empty-graph fill).
  4. Empty graph fallback: all records fail to compile (n_nodes=0) → model
     called with graph_batch=None (graceful text-only fallback on graph model).
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
import torch

# ---------------------------------------------------------------------------
# Path bootstrap — mirrors train_structured_prediction.py's own setup
# ---------------------------------------------------------------------------
from pathlib import Path

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    _pkg = types.ModuleType("cas_native")
    _pkg.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    _pkg.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = _pkg

from cas_native.model.structured_prediction import (
    AUTHORITY_LABELS,
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
)
from cas_native.training.structured_token_adapter import (
    records_to_structured_token_sequences,
    tokens_to_structured_token_batch,
)
from cas_native.training.train_structured_prediction import (
    evaluate_structured_token_prediction,
    train_structured_token_prediction_local,
)
from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DIAG_SERIAL_MODULE_PATH = "cas_native.training.diagram_serialization"


def _records() -> list[dict[str, Any]]:
    return [
        {
            "id": "v75",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 in cognitive domain with drive F4 and affective register.",
        },
        {
            "id": "v76",
            "bucket": "v76_production",
            "cas_expression": (
                "Θ(Ω_focus) = 0.40*^3^P_{F2}|A + "
                "0.60*^7^O_{F5}|E → Ω_focus"
            ),
            "user_prompt": "Recipe target Omega focus.",
        },
        {
            "id": "v77",
            "bucket": "v77_omega",
            "cas_expression": "(^4_{F2}|E × ^4_{F7}|A) = ^4|Ω_attunement",
            "user_prompt": "Omega attunement integrates embodied F2 and analytical F7.",
        },
        {
            "id": "meta",
            "bucket": "meta_logic",
            "cas_expression": "Product(Noetics, Domains)",
            "user_prompt": "Cartesian product of Noetics and Domains.",
        },
    ]


def _build_vocab(records: list[dict[str, Any]]) -> StructuredTokenVocabulary:
    sequences = records_to_structured_token_sequences(records)
    return StructuredTokenVocabulary.from_token_sequences(sequences, min_count=1)


def _fake_logits(n: int) -> dict[str, torch.Tensor]:
    """Return zero-valued logit tensors with the correct class dimensions."""
    return {
        "turn_type_logits": torch.zeros(n, len(TURN_TYPE_LABELS)),
        "expression_family_logits": torch.zeros(n, len(EXPRESSION_FAMILY_LABELS)),
        "transition_kind_logits": torch.zeros(n, len(TRANSITION_KIND_LABELS)),
        "noetic_logits": torch.zeros(n, 10),
        "domain_logits": torch.zeros(n, len(DOMAIN_LABELS)),
        "drive_logits": torch.zeros(n, len(DRIVE_LABELS)),
        "register_mode_logits": torch.zeros(n, len(REGISTER_MODE_LABELS)),
        "authority_logits": torch.zeros(n, len(AUTHORITY_LABELS)),
        "omega_logits": torch.zeros(n, 2),
        "meta_logic_logits": torch.zeros(n, 2),
        "register_logits": torch.zeros(n, len(REGISTER_LABELS)),
        "meta_relation_logits": torch.zeros(n, len(META_RELATION_LABELS)),
    }


def _fake_graph_batch(batch_size: int) -> dict[str, torch.Tensor]:
    """Return a shape-correct batched graph dict for mocking serialize_diagram_for_batch."""
    return {
        "node_features": torch.zeros(batch_size, 32, 49),
        "edge_index": torch.zeros(batch_size, 2, 128, dtype=torch.long),
        "edge_features": torch.zeros(batch_size, 128, 34),
        "node_mask": torch.ones(batch_size, 32, dtype=torch.bool),
        "edge_mask": torch.zeros(batch_size, 128, dtype=torch.bool),
    }


def _inject_fake_diagram_serialization(
    *,
    compile_returns_empty: bool = False,
) -> MagicMock:
    """Inject a fake cas_native.training.diagram_serialization into sys.modules.

    Returns the mock module so callers can inspect call args.
    compile_returns_empty=True makes all compile_to_graph calls return n_nodes=0.
    """
    node_count = 0 if compile_returns_empty else 3

    def _fake_compile(expr: str) -> dict[str, Any]:
        return {
            "nodes": [],
            "edges": [],
            "node_features": [],
            "edge_features": [],
            "n_nodes": node_count,
            "n_edges": 0,
        }

    fake_module = MagicMock()
    fake_module.compile_to_graph = MagicMock(side_effect=_fake_compile)
    fake_module.serialize_diagram_for_batch = MagicMock(
        side_effect=lambda graphs, device=None: _fake_graph_batch(len(graphs))
    )
    sys.modules[_DIAG_SERIAL_MODULE_PATH] = fake_module
    return fake_module


def _make_graph_model(n_records: int) -> MagicMock:
    """Create a mock StructuredTokenStructuredPredictor with graph fusion enabled."""
    model = MagicMock()
    model.graph_encoder = MagicMock()   # not None → triggers graph path
    model.graph_text_fusion = MagicMock()  # not None
    model.return_value = _fake_logits(n_records)
    return model


# ---------------------------------------------------------------------------
# Test 1 — Backward compatibility: text-only model
# ---------------------------------------------------------------------------

def test_text_only_model_never_calls_compile_to_graph():
    """evaluate_structured_token_prediction on a model without graph_encoder must
    call model(batch) with no graph_batch kwarg, and must never invoke
    compile_to_graph — even when diagram_serialization is importable.
    """
    records = _records()

    # Build a real StructuredTokenStructuredPredictor via the normal local trainer.
    # This model has NO graph_encoder attribute (master code path).
    model, vocabulary, _ = train_structured_token_prediction_local(
        records,
        eval_records=None,
        d_model=32,
        bottleneck_dim=16,
        epochs=1,
        lr=0.01,
        seed=42,
        progress_print=False,
        filter_eval_overlaps=False,
        max_length=32,
    )

    # Inject a spy on diagram_serialization to detect any unwanted invocations.
    fake_ds = _inject_fake_diagram_serialization()

    try:
        manifest = evaluate_structured_token_prediction(
            model,
            records,
            vocabulary,
            batch_size=64,
            max_length=32,
        )
    finally:
        sys.modules.pop(_DIAG_SERIAL_MODULE_PATH, None)

    # Structural invariants
    assert manifest["n"] == len(records)
    assert 0.0 <= manifest["all_heads_exact_rate"] <= 1.0

    # compile_to_graph must never be called for a text-only model.
    fake_ds.compile_to_graph.assert_not_called()
    fake_ds.serialize_diagram_for_batch.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Graph propagation: model with graph_encoder + compilable records
# ---------------------------------------------------------------------------

def test_graph_model_passes_graph_batch_when_records_have_cas_expression():
    """When model has graph_encoder + graph_text_fusion and records have compilable
    cas_expression, evaluate_structured_token_prediction must call
    model(batch, graph_batch=<not None>).
    """
    records = _records()  # all have cas_expression
    vocabulary = _build_vocab(records)
    model = _make_graph_model(len(records))

    # compile_to_graph returns non-empty graphs (n_nodes=3)
    fake_ds = _inject_fake_diagram_serialization(compile_returns_empty=False)

    try:
        manifest = evaluate_structured_token_prediction(
            model,
            records,
            vocabulary,
            batch_size=64,
            max_length=32,
        )
    finally:
        sys.modules.pop(_DIAG_SERIAL_MODULE_PATH, None)

    assert manifest["n"] == len(records)

    # compile_to_graph must be called once per record
    assert fake_ds.compile_to_graph.call_count == len(records)

    # serialize_diagram_for_batch must be called once (one batch)
    fake_ds.serialize_diagram_for_batch.assert_called_once()

    # The model must be called with graph_batch not None
    assert model.call_count >= 1
    _, call_kwargs = model.call_args
    assert "graph_batch" in call_kwargs
    assert call_kwargs["graph_batch"] is not None


# ---------------------------------------------------------------------------
# Test 3 — Mixed records: some compilable, some not
# ---------------------------------------------------------------------------

def test_graph_model_handles_mixed_compilable_records():
    """When some records have compilable cas_expression (n_nodes > 0) and others
    do not (n_nodes == 0), the function builds graph_batch from all records
    (using empty-graph fill for non-compilable ones) and calls model with
    graph_batch not None.
    """
    records = _records()
    # Override two records to have no cas_expression → compile_to_graph("") → n_nodes=0
    records_mixed = [
        records[0],  # compilable
        {**records[1], "cas_expression": ""},  # empty → n_nodes=0
        records[2],  # compilable
        {**records[3], "cas_expression": None},  # None → n_nodes=0
    ]

    vocabulary = _build_vocab(records_mixed)
    model = _make_graph_model(len(records_mixed))

    # compile_to_graph returns 3 nodes for non-empty expressions, 0 for empty
    def _mixed_compile(expr: str) -> dict[str, Any]:
        n = 3 if expr and expr.strip() else 0
        return {"nodes": [], "edges": [], "node_features": [], "edge_features": [],
                "n_nodes": n, "n_edges": 0}

    fake_ds = MagicMock()
    fake_ds.compile_to_graph = MagicMock(side_effect=_mixed_compile)
    fake_ds.serialize_diagram_for_batch = MagicMock(
        side_effect=lambda graphs, device=None: _fake_graph_batch(len(graphs))
    )
    sys.modules[_DIAG_SERIAL_MODULE_PATH] = fake_ds

    try:
        manifest = evaluate_structured_token_prediction(
            model,
            records_mixed,
            vocabulary,
            batch_size=64,
            max_length=32,
        )
    finally:
        sys.modules.pop(_DIAG_SERIAL_MODULE_PATH, None)

    assert manifest["n"] == len(records_mixed)

    # serialize_diagram_for_batch was called (at least one record was compilable)
    fake_ds.serialize_diagram_for_batch.assert_called_once()

    # The batch passed to serialize includes ALL records (filled with empty graphs)
    passed_graphs = fake_ds.serialize_diagram_for_batch.call_args[0][0]
    assert len(passed_graphs) == len(records_mixed)

    # model called with graph_batch not None
    _, call_kwargs = model.call_args
    assert call_kwargs.get("graph_batch") is not None


# ---------------------------------------------------------------------------
# Test 4 — Empty graph fallback: all records fail to compile
# ---------------------------------------------------------------------------

def test_graph_model_falls_back_gracefully_when_all_graphs_empty():
    """When ALL records yield n_nodes=0 from compile_to_graph, evaluate_
    structured_token_prediction must call model(batch, graph_batch=None) and
    NOT call serialize_diagram_for_batch — graceful text-only fallback.
    """
    records = _records()
    vocabulary = _build_vocab(records)
    model = _make_graph_model(len(records))

    # All compile calls return n_nodes=0
    fake_ds = _inject_fake_diagram_serialization(compile_returns_empty=True)

    try:
        manifest = evaluate_structured_token_prediction(
            model,
            records,
            vocabulary,
            batch_size=64,
            max_length=32,
        )
    finally:
        sys.modules.pop(_DIAG_SERIAL_MODULE_PATH, None)

    assert manifest["n"] == len(records)

    # compile_to_graph was called (tried to compile) but all returned n_nodes=0
    assert fake_ds.compile_to_graph.call_count == len(records)

    # serialize_diagram_for_batch must NOT be called (no valid graphs to pack)
    fake_ds.serialize_diagram_for_batch.assert_not_called()

    # model is still called (graph-capable model path), but with graph_batch=None
    assert model.call_count >= 1
    _, call_kwargs = model.call_args
    assert "graph_batch" in call_kwargs
    assert call_kwargs["graph_batch"] is None
