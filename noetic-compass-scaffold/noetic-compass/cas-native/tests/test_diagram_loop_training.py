"""End-to-end smoke tests for Phase 6: diagram-loop training integration."""

from __future__ import annotations

import torch
import pytest

from cas_native.training.diagram_loop_augmentation import expand_with_diagram_loop_pairs
from cas_native.training.diagram_serialization import (
    EDGE_FEATURE_DIM,
    NODE_FEATURE_DIM,
    compile_to_graph,
    serialize_diagram_for_batch,
)
from cas_native.model.graph_encoder import GraphEncoder
from cas_native.model.graph_text_fusion import GraphTextFusion
from cas_native.model.structured_prediction import StructuredPredictionHead
from cas_native.model.structured_token_embedding import (
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.training.structured_prediction_ingest import get_prior_diagram


# ---------------------------------------------------------------------------
# Helper: minimal records for smoke tests
# ---------------------------------------------------------------------------

def _make_canonical_records(n: int = 5) -> list[dict]:
    expressions = [
        "^4^E_{F2}|E",
        "^2^P_{F4}|f",
        "^5^C_{F1}|T",
        "^3^C_{F2}",
        "^7^O_{F6}|A",
    ]
    records = []
    for i in range(n):
        cas = expressions[i % len(expressions)]
        records.append({
            "id": f"rec_{i}",
            "cas_expression": cas,
            "user_prompt": f"families: {cas}. What notation should I use?",
            "bucket": "v75_register",
        })
    return records


# ---------------------------------------------------------------------------
# (a) Augmentation count: 5 canonicals + K=2 → 10 diagram-loop variants only
# ---------------------------------------------------------------------------

def test_diagram_loop_augmentation_count():
    """K=2 augmentation produces 5*(1+2)=15 total records."""
    records = _make_canonical_records(5)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=2)
    assert len(result) == 5 * 3  # canonical + 2 variants each


def test_augmented_records_have_prior_diagram_populated():
    """10 of 15 augmented records have prior_diagram set (the 10 variants)."""
    records = _make_canonical_records(5)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=2)
    n_with_diagram = sum(1 for r in result if r.get("prior_diagram") is not None)
    assert n_with_diagram == 5 * 2  # K variants per canonical


# ---------------------------------------------------------------------------
# (b) get_prior_diagram helper
# ---------------------------------------------------------------------------

def test_get_prior_diagram_on_canonical_returns_none():
    """Canonical records (no prior_diagram field) return None."""
    records = _make_canonical_records(3)
    for r in records:
        assert get_prior_diagram(r) is None


def test_get_prior_diagram_on_augmented_returns_dict():
    """Diagram-loop augmented records return a non-None dict."""
    records = _make_canonical_records(3)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=1)
    for r in result:
        if r.get("prior_diagram") is not None:
            pd = get_prior_diagram(r)
            assert isinstance(pd, dict)
            assert "n_nodes" in pd


# ---------------------------------------------------------------------------
# (c) End-to-end forward pass with prior_diagram produces sane logits shape
# ---------------------------------------------------------------------------

def test_forward_with_prior_diagram_returns_correct_logit_shapes():
    """StructuredTokenStructuredPredictor with graph path returns correct shapes."""
    from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
    from cas_native.training.structured_token_adapter import (
        records_to_structured_token_sequences,
        tokens_to_structured_token_batch,
    )
    from cas_native.model.structured_prediction import TURN_TYPE_LABELS, DOMAIN_LABELS

    # Build minimal records with diagram augmentation
    canonicals = _make_canonical_records(3)
    augmented = expand_with_diagram_loop_pairs(canonicals, variants_per_record=1)
    # Take one augmented record that has prior_diagram
    augmented_with_prior = [r for r in augmented if r.get("prior_diagram") is not None]
    assert augmented_with_prior, "No augmented records found"
    batch_records = augmented_with_prior[:2]

    # Build vocabulary from canonical records
    from cas_native.tokenizer.lexicon.schema import load_seed_lexicon
    lexicon = load_seed_lexicon()
    from cas_native.tokenizer.assembler import tokenize
    sequences = []
    for r in batch_records:
        tokens = tokenize(r.get("user_prompt", ""), lexicon=lexicon)
        sequences.append(tokens)

    vocabulary = StructuredTokenVocabulary.from_token_sequences(sequences, min_count=1)
    batch = tokens_to_structured_token_batch(sequences, vocabulary, max_length=64, device="cpu")

    # Build model with graph path
    d_model = 64
    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=32)
    graph_encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    graph_fusion = GraphTextFusion(d_text=d_model, d_graph=64)
    model = StructuredTokenStructuredPredictor(embedding, head, graph_encoder, graph_fusion)
    model.eval()

    # Build graph batch from prior_diagrams
    prior_diagrams = [r["prior_diagram"] for r in batch_records]
    graph_batch = serialize_diagram_for_batch(prior_diagrams, device="cpu")

    with torch.no_grad():
        outputs = model(batch, graph_batch=graph_batch)

    B = len(batch_records)
    assert "turn_type_logits" in outputs
    assert outputs["turn_type_logits"].shape[0] == B
    assert "noetic_logits" in outputs
    assert outputs["noetic_logits"].shape == (B, 10)
    assert "domain_logits" in outputs
    assert outputs["domain_logits"].shape == (B, len(DOMAIN_LABELS))


# ---------------------------------------------------------------------------
# (d) Text-only path unchanged with graph_batch=None (backward compat)
# ---------------------------------------------------------------------------

def test_forward_without_graph_batch_works_as_before():
    """text-only forward pass (no graph_batch) returns same shapes as pre-PR."""
    from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
    from cas_native.training.structured_token_adapter import (
        records_to_structured_token_sequences,
        tokens_to_structured_token_batch,
    )
    from cas_native.tokenizer.assembler import tokenize
    from cas_native.tokenizer.lexicon.schema import load_seed_lexicon

    canonicals = _make_canonical_records(2)
    lexicon = load_seed_lexicon()
    sequences = [tokenize(r.get("user_prompt", ""), lexicon=lexicon) for r in canonicals]
    vocabulary = StructuredTokenVocabulary.from_token_sequences(sequences, min_count=1)
    batch = tokens_to_structured_token_batch(sequences, vocabulary, max_length=64, device="cpu")

    d_model = 64
    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=32)
    # No graph encoder — text-only model
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.eval()

    with torch.no_grad():
        outputs = model(batch, graph_batch=None)

    assert outputs["noetic_logits"].shape == (2, 10)
