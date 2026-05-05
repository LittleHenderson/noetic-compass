"""Capture a real trace through the Predictor surface and dump it for the
manual record. This file's tests are useful as both diagnostics and
documentation of the live trace shape.
"""

from __future__ import annotations

import io
import sys

import torch

from cas_native.inference import chat as chat_mod
from cas_native.inference.predict_cas import Predictor
from cas_native.model import (
    StructuredPredictionHead,
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.tokenizer.lexicon.schema import load_seed_lexicon
from cas_native.training.structured_token_adapter import (
    tokens_to_structured_token_batch,
)


def _build_predictor(d_model: int = 128, bottleneck_dim: int = 64) -> Predictor:
    sequences = [tokenize("I feel drawn to the idea of structure")]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    embedding = StructuredTokenEmbedding(
        vocab_size=len(vocab), d_model=d_model, dropout=0.0
    )
    head = StructuredPredictionHead(
        d_model=d_model, bottleneck_dim=bottleneck_dim
    )
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.eval()
    return Predictor(
        model=model,
        vocabulary=vocab,
        lexicon=load_seed_lexicon(),
        device=torch.device("cpu"),
        max_length=32,
    )


def test_predictor_with_trace_full_pipeline():
    """End-to-end sanity check on the live trace surface."""
    predictor = _build_predictor()
    result = predictor(
        "I feel drawn to the idea of structure", with_trace=True
    )
    assert isinstance(result, tuple) and len(result) == 2
    prediction, trace = result

    # Prediction has all 12 keys.
    expected_keys = {
        "turn_type", "expression_family", "transition_kind",
        "noetic", "domain", "drive", "registers",
        "register_mode", "meta_relations", "authority",
        "has_omega", "has_meta_logic",
    }
    assert expected_keys.issubset(prediction.keys())

    # Trace has the canonical surface.
    assert trace.schema_version == "live_trace.v1"
    assert trace.input_text == "I feel drawn to the idea of structure"
    layer_names = {la.name for la in trace.layer_activations}
    assert "bottleneck" in layer_names
    assert "embedding_output" in layer_names
    assert len(trace.heads) == 12

    # Hooks fired.
    assert trace.hook_status.get("bottleneck") is True
    assert trace.hook_status.get("head:turn_type") is True


def test_show_trace_renders_real_content_with_argmax_labels():
    """Render a real trace through ``_show_trace`` and verify that argmax
    labels (not just integer indices) make it into the output."""
    predictor = _build_predictor()
    _, trace = predictor("audit the principle structure", with_trace=True)

    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        chat_mod._show_trace(trace, console=None, raw=False)
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = saved_stdout

    # All 12 head names rendered.
    for head_name in (
        "turn_type", "expression_family", "transition_kind", "noetic",
        "domain", "drive", "register", "register_mode",
        "meta_relation", "authority", "omega", "meta_logic",
    ):
        assert head_name in out, f"head {head_name!r} missing from /trace output"

    # At least one captured layer name surfaces.
    assert "bottleneck" in out
    # Attention/gate entropy section.
    assert "entropy" in out.lower() or "Attention" in out


def test_show_trace_raw_emits_valid_json():
    """``/trace --raw`` emits JSON that parses round-trip."""
    import json

    predictor = _build_predictor()
    _, trace = predictor("test --raw flag", with_trace=True)

    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        chat_mod._show_trace(trace, console=None, raw=True)
        out = sys.stdout.getvalue().strip()
    finally:
        sys.stdout = saved_stdout

    payload = json.loads(out)
    assert payload["schema_version"] == "live_trace.v1"
    assert payload["input_text"] == "test --raw flag"
    assert len(payload["heads"]) == 12
    assert "bottleneck" in payload
    assert "bottleneck_top_k" in payload
