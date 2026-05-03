"""Smoke tests for the cross-channel consistency eval harness.

Tests cover the Phase 1 scoring functions only — no model checkpoint or
torch inference is required.  The full model-wiring path (Phase 2) requires
a checkpoint and is intentionally excluded from these smoke tests.
"""

from __future__ import annotations

from cas_native.training.evaluate_cross_channel_consistency import (
    compute_cross_channel_consistency,
    score_color_channel,
    score_diagram_channel,
    score_notation_channel,
    score_three_channels,
)


# ---------------------------------------------------------------------------
# Test 1: Three-channel scoring returns sensible bool flags on synthetic pairs.
# ---------------------------------------------------------------------------


def test_score_three_channels_exact_match():
    """Perfect prediction: all channels should agree and be True."""
    expression = "^2^C_{F4}|f"
    result = score_three_channels(
        expression,
        expression,
        compile_graphs=False,
        predicted_graph={"nodes": [], "edges": []},
        gt_graph={"nodes": [], "edges": []},
    )
    assert result["notation_match"] is True
    assert result["diagram_match"] is True  # empty == empty → similarity 1.0
    assert result["color_match"] is None    # no color metadata


def test_score_three_channels_notation_mismatch():
    """Surface mismatch should set notation_match=False."""
    result = score_three_channels(
        "^3^P",
        "^2^C",
        compile_graphs=False,
        predicted_graph=None,
        gt_graph=None,
    )
    assert result["notation_match"] is False
    assert result["diagram_match"] is False  # both None → False
    assert result["diagram_similarity"] is None


def test_score_three_channels_diagram_channel_partial_overlap():
    """Partial node overlap should produce similarity < 1.0 and diagram_match
    depends on threshold."""
    predicted_graph = {
        "nodes": [
            {"id": "state:CO-2", "kind": "state", "label": "CO-2"},
        ],
        "edges": [],
    }
    gt_graph = {
        "nodes": [
            {"id": "state:CO-2", "kind": "state", "label": "CO-2"},
            {"id": "state:CO-3", "kind": "state", "label": "CO-3"},
        ],
        "edges": [],
    }
    result_strict = score_three_channels(
        "^2^P",
        "^2^P + ^3^P",
        compile_graphs=False,
        predicted_graph=predicted_graph,
        gt_graph=gt_graph,
        diagram_similarity_threshold=0.95,
    )
    result_loose = score_three_channels(
        "^2^P",
        "^2^P + ^3^P",
        compile_graphs=False,
        predicted_graph=predicted_graph,
        gt_graph=gt_graph,
        diagram_similarity_threshold=0.4,
    )
    # 1 node shared, 2 total → Jaccard = 1/2 = 0.5
    assert result_strict["diagram_similarity"] is not None
    assert result_strict["diagram_similarity"] == 0.5
    assert result_strict["diagram_match"] is False
    assert result_loose["diagram_match"] is True


def test_score_notation_channel():
    """Direct notation channel: exact match only."""
    assert score_notation_channel("^2^C_{F4}|f", "^2^C_{F4}|f") is True
    assert score_notation_channel("^2^C", "^3^C") is False
    assert score_notation_channel("", "") is True
    assert score_notation_channel("^2^C", "") is False


# ---------------------------------------------------------------------------
# Test 2: Cross-channel consistency rate computed correctly.
# ---------------------------------------------------------------------------


def test_compute_cross_channel_consistency_all_agree():
    """All records consistent: disagreement rate should be 0."""
    channel_results = [
        {"notation_match": True, "diagram_match": True, "color_match": None},
        {"notation_match": True, "diagram_match": True, "color_match": None},
        {"notation_match": False, "diagram_match": False, "color_match": None},
    ]
    report = compute_cross_channel_consistency(channel_results)
    assert report["n"] == 3
    assert report["cross_channel_disagreement_count"] == 0
    assert report["cross_channel_disagreement_rate"] == 0.0
    assert report["notation_correct"] == 2
    assert report["diagram_correct"] == 2
    assert report["all_channels_consistent"] == 3


def test_compute_cross_channel_consistency_partial_disagreement():
    """One notation-correct-diagram-wrong record should be surfaced correctly."""
    channel_results = [
        {"notation_match": True,  "diagram_match": False, "color_match": None},  # disagreement
        {"notation_match": True,  "diagram_match": True,  "color_match": None},  # agree
        {"notation_match": False, "diagram_match": False, "color_match": None},  # agree
    ]
    report = compute_cross_channel_consistency(channel_results)
    assert report["notation_correct_diagram_wrong"] == 1
    assert report["diagram_correct_notation_wrong"] == 0
    assert report["cross_channel_disagreement_count"] == 1
    assert report["cross_channel_disagreement_rate"] == pytest_approx(1 / 3)


def test_compute_cross_channel_consistency_empty():
    """Empty list returns zeroed-out report without error."""
    report = compute_cross_channel_consistency([])
    assert report["n"] == 0
    assert report["cross_channel_disagreement_rate"] == 0.0
    assert report["color_correct_rate"] is None


def test_compute_cross_channel_consistency_diagram_correct_notation_wrong():
    """Diagram-correct-notation-wrong failure mode is counted correctly."""
    channel_results = [
        {"notation_match": False, "diagram_match": True, "color_match": None},
        {"notation_match": True,  "diagram_match": True, "color_match": None},
    ]
    report = compute_cross_channel_consistency(channel_results)
    assert report["diagram_correct_notation_wrong"] == 1
    assert report["notation_correct_diagram_wrong"] == 0
    assert report["cross_channel_disagreement_count"] == 1


# ---------------------------------------------------------------------------
# Test 3: Color channel returns None when nodes lack color metadata.
# ---------------------------------------------------------------------------


def test_color_channel_returns_none_no_color_metadata():
    """Color channel should return None when nodes have no 'color' field."""
    predicted_nodes = [
        {"id": "state:CO-2", "kind": "state", "label": "CO-2"},
    ]
    gt_nodes = [
        {"id": "state:CO-2", "kind": "state", "label": "CO-2"},
    ]
    result = score_color_channel(predicted_nodes, gt_nodes)
    assert result is None


def test_color_channel_returns_none_empty_nodes():
    """Color channel should return None when node lists are empty."""
    assert score_color_channel([], []) is None


def test_score_three_channels_color_none_when_no_metadata():
    """score_three_channels color_match is None when graphs carry no color."""
    graph = {
        "nodes": [{"id": "state:CO-2", "kind": "state", "label": "CO-2"}],
        "edges": [],
    }
    result = score_three_channels(
        "^2^P",
        "^2^P",
        compile_graphs=False,
        predicted_graph=graph,
        gt_graph=graph,
    )
    assert result["color_match"] is None
    assert result["color_match_rate"] is None


# ---------------------------------------------------------------------------
# Test 4: Color channel returns a real rate when nodes carry color metadata.
# ---------------------------------------------------------------------------


def test_color_channel_returns_rate_with_color_metadata():
    """Color channel should compute a match rate when nodes have 'color'."""
    predicted_nodes = [
        {"id": "state:CO-2", "kind": "state", "label": "CO-2", "color": "blue"},
        {"id": "state:CO-3", "kind": "state", "label": "CO-3", "color": "red"},
    ]
    gt_nodes = [
        {"id": "state:CO-2", "kind": "state", "label": "CO-2", "color": "blue"},
        {"id": "state:CO-3", "kind": "state", "label": "CO-3", "color": "green"},
    ]
    rate = score_color_channel(predicted_nodes, gt_nodes)
    assert rate is not None
    assert rate == 0.5  # 1 match out of 2


def test_color_channel_full_match():
    """Perfect color match returns 1.0."""
    nodes = [
        {"id": "n1", "kind": "state", "label": "CO-2", "color": "blue"},
        {"id": "n2", "kind": "state", "label": "CO-3", "color": "red"},
    ]
    rate = score_color_channel(nodes, nodes)
    assert rate == 1.0


def test_color_channel_no_match():
    """Zero color matches returns 0.0."""
    predicted_nodes = [
        {"id": "n1", "kind": "state", "label": "CO-2", "color": "blue"},
    ]
    gt_nodes = [
        {"id": "n1", "kind": "state", "label": "CO-2", "color": "red"},
    ]
    rate = score_color_channel(predicted_nodes, gt_nodes)
    assert rate == 0.0


def test_score_three_channels_color_active_when_metadata_present():
    """score_three_channels color_match is bool when nodes carry color."""
    predicted_graph = {
        "nodes": [{"id": "n1", "kind": "state", "label": "CO-2", "color": "blue"}],
        "edges": [],
    }
    gt_graph = {
        "nodes": [{"id": "n1", "kind": "state", "label": "CO-2", "color": "blue"}],
        "edges": [],
    }
    result = score_three_channels(
        "^2^P",
        "^2^P",
        compile_graphs=False,
        predicted_graph=predicted_graph,
        gt_graph=gt_graph,
    )
    assert result["color_match"] is True
    assert result["color_match_rate"] == 1.0


# ---------------------------------------------------------------------------
# Helper — import pytest.approx locally to avoid coupling to pytest symbols
# at module level (keeps the test file importable outside pytest).
# ---------------------------------------------------------------------------

def pytest_approx(value: float, rel: float = 1e-6):  # type: ignore[override]
    import pytest
    return pytest.approx(value, rel=rel)
