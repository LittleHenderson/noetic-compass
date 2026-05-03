"""Tests for diagram_loop_augmentation.py (Phase 5 — diagram-loop lever)."""

from __future__ import annotations

import copy

import pytest

from cas_native.training.diagram_loop_augmentation import (
    DIAGRAM_LOOP_SOURCE_LABEL,
    expand_with_diagram_loop_pairs,
)
from cas_native.training.diagram_serialization import compile_to_graph


# ---------------------------------------------------------------------------
# Sample records for testing
# ---------------------------------------------------------------------------

def _make_record(idx: int, cas: str = "^4^E_{F2}|E") -> dict:
    return {
        "id": f"rec_{idx}",
        "cas_expression": cas,
        "user_prompt": f"families: {cas}. What notation should I use?",
        "bucket": "v75_register",
    }


def _make_records(n: int = 5) -> list[dict]:
    expressions = [
        "^4^E_{F2}|E",
        "^2^P_{F4}|f",
        "^5^C_{F1}|T",
        "^3^C_{F2}",
        "^7^O_{F6}|A",
    ]
    return [_make_record(i, expressions[i % len(expressions)]) for i in range(n)]


# ---------------------------------------------------------------------------
# (a) Backward compat: K=0 is a no-op pass-through
# ---------------------------------------------------------------------------

def test_zero_variants_is_passthrough():
    """K=0 returns records unchanged, with no prior_diagram added."""
    records = _make_records(3)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=0)
    assert len(result) == 3
    for r in result:
        assert "prior_diagram" not in r


def test_zero_variants_preserves_record_identity():
    """K=0: output records are the same objects (no copies made)."""
    records = _make_records(2)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=0)
    for original, returned in zip(records, result):
        assert original is returned


# ---------------------------------------------------------------------------
# (b) Augmentation count: len * (1 + K)
# ---------------------------------------------------------------------------

def test_augmentation_count_k1():
    """K=1 → 2× records per canonical."""
    records = _make_records(4)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=1)
    assert len(result) == 4 * 2


def test_augmentation_count_k3():
    """K=3 → 4× records per canonical."""
    records = _make_records(5)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=3)
    assert len(result) == 5 * (1 + 3)


def test_negative_variants_raises():
    """Negative K raises ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        expand_with_diagram_loop_pairs(_make_records(1), variants_per_record=-1)


# ---------------------------------------------------------------------------
# (c) prior_diagram is populated on augmented records, absent on canonicals
# ---------------------------------------------------------------------------

def test_prior_diagram_populated_on_augmented():
    """Every augmented (non-canonical) record has a prior_diagram dict."""
    records = _make_records(3)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=2)
    # First record of each group is the canonical (no prior_diagram)
    for i, record in enumerate(result):
        if record.get("paraphrase_source") == DIAGRAM_LOOP_SOURCE_LABEL:
            assert "prior_diagram" in record
            pd = record["prior_diagram"]
            assert isinstance(pd, dict)
            assert "n_nodes" in pd
            assert "n_edges" in pd
            assert "node_features" in pd
            assert "edge_features" in pd


def test_canonical_records_have_no_prior_diagram():
    """Canonical records (no paraphrase_source) never have prior_diagram."""
    records = _make_records(3)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=2)
    for record in result:
        if record.get("paraphrase_source") != DIAGRAM_LOOP_SOURCE_LABEL:
            assert "prior_diagram" not in record


# ---------------------------------------------------------------------------
# (d) prior_diagram matches compile_to_graph(canonical_cas_expression)
# ---------------------------------------------------------------------------

def test_prior_diagram_matches_compile_to_graph():
    """prior_diagram on augmented records equals compile_to_graph(cas_expression)."""
    records = _make_records(2)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=1)
    for record in result:
        if record.get("paraphrase_source") == DIAGRAM_LOOP_SOURCE_LABEL:
            expected = compile_to_graph(record["cas_expression"])
            actual = record["prior_diagram"]
            assert actual["n_nodes"] == expected["n_nodes"]
            assert actual["n_edges"] == expected["n_edges"]
            assert actual["node_features"] == expected["node_features"]
            assert actual["edge_features"] == expected["edge_features"]


def test_cas_expression_is_inherited_from_canonical():
    """Augmented records inherit cas_expression from the canonical record."""
    records = _make_records(3)
    result = expand_with_diagram_loop_pairs(records, variants_per_record=2)
    canonical_exprs = {r["id"]: r["cas_expression"] for r in records}
    for record in result:
        if record.get("paraphrase_source") == DIAGRAM_LOOP_SOURCE_LABEL:
            base_id = record["base_id"]
            assert record["cas_expression"] == canonical_exprs[base_id]
