"""Smoke tests for Phase 7: evaluate_diagram_loop_invariance."""

from __future__ import annotations

import torch
import pytest

from cas_native.training.diagram_loop_augmentation import expand_with_diagram_loop_pairs
from cas_native.training.evaluate_diagram_loop_invariance import (
    build_diagram_loop_invariance_report,
    make_diagram_loop_records,
)
from cas_native.training.diagram_serialization import compile_to_graph


# ---------------------------------------------------------------------------
# Helpers
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


def _make_fake_sample(record: dict, all_heads_exact: bool = True) -> dict:
    return {
        "id": record["id"],
        "base_id": record.get("base_id", record["id"]),
        "bucket": record.get("bucket"),
        "prediction": {"noetic": 4, "domain": 2, "drive": 1},
        "correctness": {"noetic": all_heads_exact, "domain": all_heads_exact, "drive": all_heads_exact},
        "all_heads_exact": all_heads_exact,
    }


# ---------------------------------------------------------------------------
# (a) make_diagram_loop_records
# ---------------------------------------------------------------------------

def test_make_diagram_loop_records_count():
    """make_diagram_loop_records returns one variant per input record."""
    records = _make_canonical_records(4)
    result = make_diagram_loop_records(records)
    assert len(result) == 4


def test_make_diagram_loop_records_all_have_prior_diagram():
    """Every record returned has prior_diagram set as a dict with n_nodes."""
    records = _make_canonical_records(3)
    result = make_diagram_loop_records(records)
    for r in result:
        assert r.get("prior_diagram") is not None
        assert isinstance(r["prior_diagram"], dict)
        assert "n_nodes" in r["prior_diagram"]


def test_make_diagram_loop_records_base_id_matches_canonical():
    """base_id on each variant matches the originating record's id."""
    records = _make_canonical_records(3)
    result = make_diagram_loop_records(records)
    for original, variant in zip(records, result):
        assert variant["base_id"] == original["id"]


# ---------------------------------------------------------------------------
# (b) build_diagram_loop_invariance_report
# ---------------------------------------------------------------------------

def test_invariance_report_keys():
    """Report contains all required top-level keys."""
    records = _make_canonical_records(3)
    canonical_samples = [_make_fake_sample(r, True) for r in records]
    dl_records = make_diagram_loop_records(records)
    dl_samples = [_make_fake_sample(r, True) for r in dl_records]
    report = build_diagram_loop_invariance_report(canonical_samples, dl_samples)
    for key in (
        "n_canonical", "n_diagram_loop", "n_comparable",
        "canonical_all_heads_exact_rate", "diagram_loop_all_heads_exact_rate",
        "accuracy_delta", "all_heads_prediction_consistency_rate",
        "per_head_prediction_consistency", "by_bucket",
    ):
        assert key in report, f"Missing key: {key}"


def test_invariance_report_consistency_rate_perfect_agreement():
    """When DL predictions match canonical, consistency rate = 1.0."""
    records = _make_canonical_records(3)
    canonical_samples = [_make_fake_sample(r, True) for r in records]
    dl_records = make_diagram_loop_records(records)
    dl_samples = [_make_fake_sample(r, True) for r in dl_records]
    report = build_diagram_loop_invariance_report(canonical_samples, dl_samples)
    assert report["all_heads_prediction_consistency_rate"] == 1.0


def test_invariance_report_consistency_rate_zero_agreement():
    """When DL predictions all differ, consistency rate = 0.0."""
    records = _make_canonical_records(3)
    canonical_samples = [_make_fake_sample(r, True) for r in records]
    dl_records = make_diagram_loop_records(records)
    dl_samples = []
    for r in dl_records:
        s = _make_fake_sample(r, False)
        s["prediction"] = {"noetic": 99, "domain": 99, "drive": 99}
        dl_samples.append(s)
    report = build_diagram_loop_invariance_report(canonical_samples, dl_samples)
    assert report["all_heads_prediction_consistency_rate"] == 0.0


def test_invariance_report_accuracy_delta_sign():
    """accuracy_delta is positive when DL exact rate > canonical exact rate."""
    records = _make_canonical_records(4)
    # Canonical: 0 exact; DL: 4 exact
    canonical_samples = [_make_fake_sample(r, False) for r in records]
    dl_records = make_diagram_loop_records(records)
    dl_samples = [_make_fake_sample(r, True) for r in dl_records]
    report = build_diagram_loop_invariance_report(canonical_samples, dl_samples)
    assert report["accuracy_delta"] > 0.0


def test_invariance_report_raises_on_no_matching_ids():
    """Report raises when no DL samples match canonical ids."""
    canonical_samples = [{"id": "a", "base_id": "a", "prediction": {"noetic": 1}, "all_heads_exact": True}]
    dl_samples = [{"id": "b", "base_id": "z", "prediction": {"noetic": 1}, "all_heads_exact": True}]
    with pytest.raises(ValueError, match="no diagram-loop samples matched"):
        build_diagram_loop_invariance_report(canonical_samples, dl_samples)


# ---------------------------------------------------------------------------
# (c) End-to-end _eval_pass smoke test (no checkpoint needed)
# ---------------------------------------------------------------------------

def test_eval_pass_text_only_returns_samples():
    """_eval_pass with text-only model returns sample list with correct length."""
    from cas_native.training.evaluate_diagram_loop_invariance import _eval_pass
    from cas_native.model.structured_prediction import StructuredPredictionHead
    from cas_native.model.structured_token_embedding import (
        StructuredTokenEmbedding,
        StructuredTokenStructuredPredictor,
    )
    from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
    from cas_native.tokenizer.assembler import tokenize
    from cas_native.tokenizer.lexicon.schema import load_seed_lexicon

    records = _make_canonical_records(3)
    lexicon = load_seed_lexicon()
    sequences = [tokenize(r["user_prompt"], lexicon=lexicon) for r in records]
    vocabulary = StructuredTokenVocabulary.from_token_sequences(sequences, min_count=1)

    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=64)
    head = StructuredPredictionHead(d_model=64, bottleneck_dim=32)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.eval()

    manifest = _eval_pass(
        model, records, vocabulary,
        device="cpu", batch_size=4, max_length=64,
        use_graph_path=False,
    )
    assert manifest["n"] == 3
    assert len(manifest["samples"]) == 3
    assert "all_heads_exact_rate" in manifest
