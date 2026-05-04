"""Tests for evaluate_diagram_loop_honest — no-oracle-leak invariant and protocol.

The five tests here mirror the acceptance criteria from the diagloop honest eval
proposal:

1. No ground-truth leak  — compile_to_graph must never receive a ground-truth
   cas_expression string during the eval path.
2. Self-prediction prior shape (correct prediction) — when model was right in
   pass 1 the prior graph encodes the same structure as ground truth, but
   arrives via the model's own prediction string, not from the record directly.
3. Self-prediction prior shape (wrong prediction) — when model was wrong in
   pass 1 the prior encodes the wrong answer; ground-truth prior differs.
4. Pass 1 is text-only — predict_canonical calls the model with no graph_batch.
5. Pass 2 propagates prior — _run_pass2_inference calls the model with a
   non-None graph_batch built from pass-1 self-predictions.
"""

from __future__ import annotations

from unittest.mock import patch
from typing import Any

import pytest
import torch
import torch.nn as nn

from cas_native.model.structured_prediction import StructuredPredictionHead
from cas_native.model.structured_token_embedding import (
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.training.structured_token_adapter import tokens_to_structured_token_batch
from cas_native.training.diagram_serialization import compile_to_graph
from cas_native.training.evaluate_diagram_loop_honest import (
    compile_self_prediction_priors,
    predict_canonical,
    _run_pass2_inference,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _minimal_records() -> list[dict[str, Any]]:
    return [
        {
            "id": "r1",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 cognitive domain drive F4 affective register.",
        },
        {
            "id": "r2",
            "bucket": "v77_omega",
            "cas_expression": "^3^P_{F2}|A",
            "user_prompt": "Noetic 3 principled domain drive F2 analytical register.",
        },
    ]


def _make_model_and_vocab(d_model: int = 32, bottleneck_dim: int = 16):
    """Build a minimal real model and matching vocabulary for integration tests."""
    records = _minimal_records()
    sequences = [
        tokenize(str(r.get("user_prompt", ""))) for r in records
    ]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    embedding = StructuredTokenEmbedding(vocab_size=len(vocab), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    inner = StructuredTokenStructuredPredictor(embedding, head)
    return inner, vocab, sequences


class _RecordingPredictor(nn.Module):
    """Wraps a real predictor and records every forward() call's kwargs."""

    def __init__(self, inner: StructuredTokenStructuredPredictor) -> None:
        super().__init__()
        self.inner = inner
        self.call_log: list[dict[str, Any]] = []

    def forward(self, batch, graph_batch=None):  # type: ignore[override]
        self.call_log.append({"graph_batch": graph_batch})
        return self.inner(batch)

    def eval(self):
        self.inner.eval()
        return self

    def train(self, mode: bool = True):  # type: ignore[override]
        self.inner.train(mode)
        return self

    def load_state_dict(self, *args, **kwargs):
        return self.inner.load_state_dict(*args, **kwargs)

    def to(self, *args, **kwargs):
        self.inner.to(*args, **kwargs)
        return self

    def parameters(self):
        return self.inner.parameters()


# ---------------------------------------------------------------------------
# Test 1 — No ground-truth leak
# ---------------------------------------------------------------------------


def test_no_ground_truth_leak():
    """compile_to_graph must never receive a ground-truth cas_expression during eval.

    Monkeypatches compile_to_graph in the honest-eval module namespace and
    records every string it is called with.  Asserts that none of those strings
    match any of the eval records' ground-truth cas_expression values.
    """
    records = _minimal_records()
    ground_truth_exprs = {r["cas_expression"] for r in records}

    # Simulate model predicting something completely different from ground truth
    canonical_predictions = {r["id"]: "^1^O" for r in records}

    compile_calls: list[str] = []

    def tracking_compile(expr: str):
        compile_calls.append(expr)
        # Delegate to real implementation for correct return value
        return compile_to_graph(expr)

    with patch(
        "cas_native.training.evaluate_diagram_loop_honest.compile_to_graph",
        side_effect=tracking_compile,
    ):
        compile_self_prediction_priors(
            canonical_predictions,
            records,
            variants_per_record=2,
        )

    assert compile_calls, "compile_to_graph was never called — implementation drift"
    for called_with in compile_calls:
        assert called_with not in ground_truth_exprs, (
            f"Oracle leak detected: compile_to_graph received ground-truth "
            f"expression {called_with!r} which is in {ground_truth_exprs!r}. "
            f"This is the anti-pattern. Only model-predicted strings are allowed."
        )


# ---------------------------------------------------------------------------
# Test 2 — Self-prediction prior when prediction is correct
# ---------------------------------------------------------------------------


def test_self_prediction_prior_shape_when_prediction_correct():
    """When canonical prediction matches ground truth, prior encodes the right structure.

    The prior is STILL built from the model's own predicted string — the fact
    that the prediction happens to equal the ground truth is incidental.
    The path through the code must be identical whether the model is right or wrong.
    """
    records = [
        {
            "id": "r1",
            "bucket": "v75_register",
            "cas_expression": "^2^C",
            "user_prompt": "Noetic 2 cognitive.",
        }
    ]
    # Model predicted the correct expression
    canonical_predictions = {"r1": "^2^C"}

    variants = compile_self_prediction_priors(
        canonical_predictions, records, variants_per_record=1
    )

    assert len(variants) == 1
    variant = variants[0]

    # Prior was built from the model's predicted string "^2^C"
    expected_prior = compile_to_graph("^2^C")
    assert variant["prior_diagram"] == expected_prior
    assert variant["prior_diagram_source"] == "self_prediction"
    assert variant["canonical_prediction"] == "^2^C"

    # Confirm the prior matches compile_to_graph(ground_truth) ONLY because
    # the model was right — not because we used ground truth directly.
    ground_truth_prior = compile_to_graph(records[0]["cas_expression"])
    assert variant["prior_diagram"] == ground_truth_prior  # coincidental match is ok


# ---------------------------------------------------------------------------
# Test 3 — Self-prediction prior when prediction is wrong
# ---------------------------------------------------------------------------


def test_self_prediction_prior_shape_when_prediction_wrong():
    """When canonical prediction is wrong, prior encodes the wrong structure.

    The model must recover from a noisy prior in pass 2 — this is the honest
    production condition.  The prior must NOT silently fall back to ground truth.
    """
    records = [
        {
            "id": "r1",
            "bucket": "v75_register",
            "cas_expression": "^2^C",
            "user_prompt": "Noetic 2 cognitive.",
        }
    ]
    # Model predicted wrong expression
    canonical_predictions = {"r1": "^3^P"}

    variants = compile_self_prediction_priors(
        canonical_predictions, records, variants_per_record=1
    )

    assert len(variants) == 1
    variant = variants[0]

    # Prior is built from wrong prediction "^3^P"
    wrong_prior = compile_to_graph("^3^P")
    ground_truth_prior = compile_to_graph("^2^C")

    assert variant["prior_diagram"] == wrong_prior
    assert variant["prior_diagram"] != ground_truth_prior, (
        "Prior must encode the model's wrong prediction, not silently correct to ground truth"
    )
    assert variant["canonical_prediction"] == "^3^P"
    assert variant["prior_diagram_source"] == "self_prediction"


# ---------------------------------------------------------------------------
# Test 4 — Empty / invalid canonical prediction produces None prior, no crash
# ---------------------------------------------------------------------------


def test_empty_graph_fallback_no_crash():
    """Empty or invalid model prediction → prior_diagram is None; eval does not crash.

    This is the zero-attention fallback path.  compile_to_graph("") returns None
    and compile_self_prediction_priors must propagate that None without raising.
    """
    records = [
        {
            "id": "r1",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 cognitive.",
        }
    ]
    # Simulate model predicting empty string (e.g. degenerate output)
    canonical_predictions = {"r1": ""}

    variants = compile_self_prediction_priors(
        canonical_predictions, records, variants_per_record=1
    )

    assert len(variants) == 1
    assert variants[0]["prior_diagram"] is None, (
        "Empty model prediction must yield None prior (zero-attention fallback), not ground truth"
    )
    assert variants[0]["prior_diagram_source"] == "self_prediction"

    # Variants for record with missing id also get None priors without crashing
    records_no_pred = [{"id": "unknown_id", "bucket": "v75", "cas_expression": "^9^O", "user_prompt": "x"}]
    variants2 = compile_self_prediction_priors({}, records_no_pred, variants_per_record=1)
    assert len(variants2) == 1
    assert variants2[0]["prior_diagram"] is None


# ---------------------------------------------------------------------------
# Test 5 — Pass 1 is text-only; pass 2 passes non-None graph_batch
# ---------------------------------------------------------------------------


def test_pass1_text_only_pass2_receives_prior():
    """predict_canonical calls model with no graph_batch; _run_pass2_inference provides one.

    Uses _RecordingPredictor to log every model.forward() call and inspect the
    graph_batch argument.  Asserts:
    - Pass 1: all forward calls had graph_batch=None.
    - Pass 2: at least one forward call had graph_batch is not None, and the
      batch was constructed from pass-1 self-prediction strings, not ground truth.
    """
    inner_model, vocab, sequences = _make_model_and_vocab(d_model=32, bottleneck_dim=16)
    recording_model = _RecordingPredictor(inner_model)
    records = _minimal_records()

    # ---- Pass 1 ----
    canonical_predictions = predict_canonical(
        recording_model,
        vocab,
        records,
        token_sequences=sequences,
        device="cpu",
        batch_size=4,
        max_length=32,
    )

    pass1_calls = list(recording_model.call_log)
    assert pass1_calls, "predict_canonical made no forward() calls"
    for entry in pass1_calls:
        assert entry["graph_batch"] is None, (
            f"Pass 1 must be text-only: found graph_batch={entry['graph_batch']!r}"
        )

    # ---- Build self-prediction priors ----
    recording_model.call_log.clear()

    variants = compile_self_prediction_priors(
        canonical_predictions,
        records,
        variants_per_record=2,
    )
    para_seqs = [
        tokenize(str(v.get("user_prompt", ""))) for v in variants
    ]

    # ---- Pass 2 ----
    _run_pass2_inference(
        recording_model,
        vocab,
        variants,
        token_sequences=para_seqs,
        device="cpu",
        batch_size=4,
        max_length=32,
    )

    pass2_calls = list(recording_model.call_log)
    assert pass2_calls, "_run_pass2_inference made no forward() calls"

    # At least one batch must have received a non-None graph_batch
    non_none_prior_calls = [
        entry for entry in pass2_calls if entry["graph_batch"] is not None
    ]
    # (some batches may have all-None priors if model's pass-1 was all empty;
    # here the real model produces non-empty predictions so we expect at least one)
    if any(v.get("prior_diagram") is not None for v in variants):
        assert non_none_prior_calls, (
            "Pass 2 must propagate non-None priors to model as graph_batch when available"
        )

    # Verify the graph_batch data comes from predicted strings, not ground truth
    ground_truth_exprs = {r["cas_expression"] for r in records}
    for entry in pass2_calls:
        gb = entry["graph_batch"]
        if gb is not None and "expressions" in gb:
            for expr in gb["expressions"]:
                if expr:  # skip empty-string slots
                    assert expr not in ground_truth_exprs, (
                        f"graph_batch expression {expr!r} leaked from ground truth — "
                        f"it must come from canonical_predictions only"
                    )
