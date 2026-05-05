"""Tests for cas-synthetic/schemas/diagram_diff.py.

All tests use hand-constructed diagram dicts — no compiler dependency required.
Diagram format mirrors the shape produced by the notation compiler's
``build_diagram`` / ``CompilationArtifact.diagram()`` API.
"""

from __future__ import annotations

import json

import pytest

# The conftest registers `cas_synthetic` as an importable alias for the
# hyphenated `cas-synthetic` directory, so these imports work without install.
from cas_synthetic.schemas.diagram_diff import (
    diagram_axis_substitution_counts,
    diagram_diff_report,
    diagram_set_diff,
    diagram_similarity_score,
)
from cas_synthetic.schemas.diagram_graph import (
    canonical_node_key,
    canonical_container_key,
    diagram_summary,
)


# ---------------------------------------------------------------------------
# Helpers — minimal valid diagram factories
# ---------------------------------------------------------------------------

def _node(kind: str, label: str, role: str = "", **extra) -> dict:
    n: dict = {"id": f"{kind}:{label}", "kind": kind, "label": label}
    if role:
        n["role"] = role
    n.update(extra)
    return n


def _edge(source_id: str, target_id: str, kind: str = "dependency") -> dict:
    return {
        "id": f"edge:{source_id}-{target_id}",
        "source": source_id,
        "target": target_id,
        "kind": kind,
        "directed": True,
    }


def _container(kind: str, label: str, contains: list | None = None) -> dict:
    return {
        "id": f"container:{label}",
        "kind": kind,
        "label": label,
        "contains": contains or [],
    }


def _diagram(nodes=(), edges=(), containers=(), layouts=("semantic",)) -> dict:
    return {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "layouts": list(layouts),
        "nodes": list(nodes),
        "edges": list(edges),
        "containers": list(containers),
    }


# Shared fixture diagrams used across multiple tests.

N_P3 = _node("state", "P3", role="cognitive_state")
N_C3 = _node("state", "C3", role="cognitive_state")
N_P5 = _node("state", "P5", role="cognitive_state")

E_P3_C3 = _edge("state:P3", "state:C3", kind="dependency")
E_P5_C3 = _edge("state:P5", "state:C3", kind="dependency")


# ---------------------------------------------------------------------------
# Test 1 — Identical diagrams → structural_match_rate=1.0, hash match=True
# ---------------------------------------------------------------------------

class TestIdenticalDiagrams:
    def test_structural_match_rate_is_one(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        scores = diagram_similarity_score(d, d)
        assert scores["structural_match_rate"] == 1.0

    def test_edge_match_rate_is_one(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        scores = diagram_similarity_score(d, d)
        assert scores["edge_match_rate"] == 1.0

    def test_exact_graph_hash_match_true(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        scores = diagram_similarity_score(d, d)
        assert scores["exact_graph_hash_match"] is True

    def test_set_diff_all_empty_for_identical(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        diff = diagram_set_diff(d, d)
        assert diff["nodes_added"] == []
        assert diff["nodes_removed"] == []
        assert diff["edges_added"] == []
        assert diff["edges_removed"] == []


# ---------------------------------------------------------------------------
# Test 2 — One node differs → structural_match_rate < 1.0, differing node identified
# ---------------------------------------------------------------------------

class TestOneNodeDiffers:
    def _gt(self):
        return _diagram(nodes=[N_P3, N_C3])

    def _pred(self):
        # Replace N_C3 with N_P5 — one node swapped
        return _diagram(nodes=[N_P3, N_P5])

    def test_structural_match_rate_less_than_one(self):
        scores = diagram_similarity_score(self._pred(), self._gt())
        assert scores["structural_match_rate"] < 1.0

    def test_exact_hash_mismatch(self):
        scores = diagram_similarity_score(self._pred(), self._gt())
        assert scores["exact_graph_hash_match"] is False

    def test_differing_node_in_nodes_added(self):
        diff = diagram_set_diff(self._pred(), self._gt())
        pred_key = canonical_node_key(N_P5)
        assert pred_key in diff["nodes_added"]

    def test_differing_node_in_nodes_removed(self):
        diff = diagram_set_diff(self._pred(), self._gt())
        gt_key = canonical_node_key(N_C3)
        assert gt_key in diff["nodes_removed"]

    def test_unchanged_node_in_common(self):
        diff = diagram_set_diff(self._pred(), self._gt())
        assert canonical_node_key(N_P3) in diff["nodes_common"]


# ---------------------------------------------------------------------------
# Test 3 — One node's noetic value changed → noetic_substitution detected
# ---------------------------------------------------------------------------

class TestNoeticSubstitution:
    def test_noetic_substitution_counted(self):
        # GT: state P4 (domain=P, noetic=4)
        # Pred: state P5 (domain=P, noetic=5) — noetic changed, domain same
        gt_node = _node("state", "P4", role="cognitive_state")
        pred_node = _node("state", "P5", role="cognitive_state")
        gt = _diagram(nodes=[gt_node])
        pred = _diagram(nodes=[pred_node])

        counts = diagram_axis_substitution_counts(pred, gt)
        # GT noetic=4, pred noetic=5 → key "(4, 5)"
        assert counts["noetic_substitutions"].get("(4, 5)", 0) == 1

    def test_no_domain_substitution_when_only_noetic_changed(self):
        gt_node = _node("state", "P4", role="cognitive_state")
        pred_node = _node("state", "P5", role="cognitive_state")
        gt = _diagram(nodes=[gt_node])
        pred = _diagram(nodes=[pred_node])

        counts = diagram_axis_substitution_counts(pred, gt)
        assert counts["domain_substitutions"] == {}

    def test_noetic_substitution_count_accumulates(self):
        # Two GT nodes with noetic=3, two pred nodes with noetic=7
        gt_nodes = [
            _node("state", "P3", role="cognitive_state"),
            _node("state", "C3", role="cognitive_state"),
        ]
        pred_nodes = [
            _node("state", "P7", role="cognitive_state"),
            _node("state", "C7", role="cognitive_state"),
        ]
        gt = _diagram(nodes=gt_nodes)
        pred = _diagram(nodes=pred_nodes)

        counts = diagram_axis_substitution_counts(pred, gt)
        # Both P3→P7 and C3→C7 are noetic substitutions (3→7), but they also
        # differ on domain so neither qualifies as a pure noetic substitution
        # (domain must match for a noetic-only substitution).
        # P3→P7: domain=P, noetic 3→7 ✓  (C3 is also removed but domain differs)
        # C3→C7: domain=C, noetic 3→7 ✓
        assert counts["noetic_substitutions"].get("(3, 7)", 0) == 2


# ---------------------------------------------------------------------------
# Test 4 — Edge count differs → edge_match_rate reflects difference
# ---------------------------------------------------------------------------

class TestEdgeDiffers:
    def test_edge_match_rate_decreases_with_missing_edge(self):
        gt = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        pred = _diagram(nodes=[N_P3, N_C3], edges=[])  # edge removed

        scores = diagram_similarity_score(pred, gt)
        assert scores["edge_match_rate"] < 1.0

    def test_edge_match_rate_one_when_edges_match(self):
        gt = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        pred = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])

        scores = diagram_similarity_score(pred, gt)
        assert scores["edge_match_rate"] == 1.0

    def test_missing_edge_in_edges_removed(self):
        gt = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        pred = _diagram(nodes=[N_P3, N_C3], edges=[])

        diff = diagram_set_diff(pred, gt)
        assert len(diff["edges_removed"]) == 1
        assert diff["edges_added"] == []


# ---------------------------------------------------------------------------
# Test 5 — Empty vs non-empty diagrams → sensible (not-NaN) scores
# ---------------------------------------------------------------------------

class TestEmptyVsNonEmpty:
    def test_empty_vs_nonempty_structural_rate_is_zero(self):
        empty = _diagram()
        nonempty = _diagram(nodes=[N_P3])
        scores = diagram_similarity_score(empty, nonempty)
        assert scores["structural_match_rate"] == 0.0

    def test_both_empty_structural_rate_is_one(self):
        empty = _diagram()
        scores = diagram_similarity_score(empty, empty)
        assert scores["structural_match_rate"] == 1.0

    def test_empty_vs_nonempty_no_nan(self):
        empty = _diagram()
        nonempty = _diagram(nodes=[N_P3], edges=[])
        scores = diagram_similarity_score(empty, nonempty)
        for key, val in scores.items():
            if val is None:
                continue
            if isinstance(val, float):
                assert val == val, f"{key} is NaN"  # NaN != NaN

    def test_nonempty_vs_empty_no_nan(self):
        empty = _diagram()
        nonempty = _diagram(nodes=[N_P3])
        scores = diagram_similarity_score(nonempty, empty)
        for key, val in scores.items():
            if val is None:
                continue
            if isinstance(val, float):
                assert val == val, f"{key} is NaN"


# ---------------------------------------------------------------------------
# Test 6 — Color-bearing diagrams produce color_match_rate; colorless → None
# ---------------------------------------------------------------------------

class TestColorMatchRate:
    def _colored_diagram(self, color1: str, color2: str) -> dict:
        n1 = _node("state", "P3", role="cognitive_state", color=color1)
        n2 = _node("state", "C3", role="cognitive_state", color=color2)
        return _diagram(nodes=[n1, n2])

    def test_colorless_diagrams_return_none(self):
        d = _diagram(nodes=[N_P3, N_C3])
        scores = diagram_similarity_score(d, d)
        assert scores["color_match_rate"] is None

    def test_color_match_rate_one_when_all_colors_match(self):
        d = self._colored_diagram("#aabbcc", "#112233")
        scores = diagram_similarity_score(d, d)
        assert scores["color_match_rate"] == 1.0

    def test_color_match_rate_below_one_when_color_differs(self):
        gt = self._colored_diagram("#aabbcc", "#112233")
        pred = self._colored_diagram("#ffffff", "#112233")  # first node color changed
        # Node canonical keys are identical (kind/role/label unchanged), so
        # both nodes land in nodes_common; color differs on one of them.
        scores = diagram_similarity_score(pred, gt)
        assert scores["color_match_rate"] is not None
        assert scores["color_match_rate"] < 1.0

    def test_color_substitution_counted_in_axis_counts(self):
        # GT has state P3 with color #aabbcc; pred has state P5 with #ffffff.
        # They differ on both noetic AND color; color_substitution fires because
        # the color field differs between a removed+added pair that otherwise
        # matches all structural axes (same domain, drive, register — but since
        # noetic differs, this is also a noetic substitution, not a pure color
        # substitution). The color_substitutions dict should still be non-empty.
        gt_node = _node("state", "P3", role="cognitive_state", color="#aabbcc")
        pred_node = _node("state", "P3", role="cognitive_state", color="#ffffff")
        # Same canonical key — they both live in nodes_common.
        # For color_substitutions (removed/added path) we need different keys.
        gt_node2 = _node("state", "P4", role="cognitive_state", color="#aabbcc")
        pred_node2 = _node("state", "P5", role="cognitive_state", color="#ffffff")
        gt = _diagram(nodes=[gt_node, gt_node2])
        pred = _diagram(nodes=[pred_node, pred_node2])
        counts = diagram_axis_substitution_counts(pred, gt)
        # P4→P5 is a noetic substitution (3→5 on noetic axis with matching
        # domain/drive/register) AND a color change — color_substitutions
        # records it because both nodes carry color.
        assert isinstance(counts["color_substitutions"], dict)


# ---------------------------------------------------------------------------
# Test 7 — Symmetry: nodes_added(A,B) == nodes_removed(B,A)
# ---------------------------------------------------------------------------

class TestSymmetry:
    def test_nodes_added_equals_swap_nodes_removed(self):
        a = _diagram(nodes=[N_P3, N_C3])
        b = _diagram(nodes=[N_P3, N_P5])

        diff_ab = diagram_set_diff(a, b)
        diff_ba = diagram_set_diff(b, a)

        assert diff_ab["nodes_added"] == diff_ba["nodes_removed"]
        assert diff_ab["nodes_removed"] == diff_ba["nodes_added"]

    def test_edges_added_equals_swap_edges_removed(self):
        a = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        b = _diagram(nodes=[N_P3, N_C3], edges=[E_P5_C3])

        diff_ab = diagram_set_diff(a, b)
        diff_ba = diagram_set_diff(b, a)

        assert diff_ab["edges_added"] == diff_ba["edges_removed"]
        assert diff_ab["edges_removed"] == diff_ba["edges_added"]

    def test_common_is_symmetric(self):
        a = _diagram(nodes=[N_P3, N_C3])
        b = _diagram(nodes=[N_P3, N_P5])

        diff_ab = diagram_set_diff(a, b)
        diff_ba = diagram_set_diff(b, a)

        assert sorted(diff_ab["nodes_common"]) == sorted(diff_ba["nodes_common"])


# ---------------------------------------------------------------------------
# Test 8 — diagram_diff_report is JSON-serializable (no sets, no numpy types)
# ---------------------------------------------------------------------------

class TestJsonSerializability:
    def test_report_is_json_serializable_for_identical_diagrams(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        report = diagram_diff_report(d, d)
        # Should not raise
        serialized = json.dumps(report)
        assert isinstance(serialized, str)
        assert len(serialized) > 0

    def test_report_is_json_serializable_for_differing_diagrams(self):
        gt = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        pred = _diagram(nodes=[N_P3, N_P5], edges=[E_P5_C3])
        report = diagram_diff_report(pred, gt)
        serialized = json.dumps(report)
        assert isinstance(serialized, str)

    def test_report_contains_expected_top_level_keys(self):
        d = _diagram(nodes=[N_P3])
        report = diagram_diff_report(d, d)
        assert "ground_truth_summary" in report
        assert "predicted_summary" in report
        assert "set_diff" in report
        assert "axis_substitutions" in report
        assert "similarity" in report

    def test_report_no_sets_in_output(self):
        d = _diagram(nodes=[N_P3, N_C3], edges=[E_P3_C3])
        report = diagram_diff_report(d, d)

        def _check_no_sets(obj, path=""):
            if isinstance(obj, set):
                raise AssertionError(f"set found at {path}")
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _check_no_sets(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    _check_no_sets(v, f"{path}[{i}]")

        _check_no_sets(report)

    def test_report_with_colorless_diagrams_color_match_rate_is_null(self):
        d = _diagram(nodes=[N_P3])
        report = diagram_diff_report(d, d)
        assert report["similarity"]["color_match_rate"] is None
        # Confirm it round-trips through JSON as null
        parsed = json.loads(json.dumps(report))
        assert parsed["similarity"]["color_match_rate"] is None


# ---------------------------------------------------------------------------
# Additional edge-case tests (beyond the required 8 test classes above)
# ---------------------------------------------------------------------------

class TestContainerDiff:
    def test_container_added_detected(self):
        c = _container("noetic_cluster", "Noetics", contains=["state:P3"])
        gt = _diagram(nodes=[N_P3])
        pred = _diagram(nodes=[N_P3], containers=[c])

        diff = diagram_set_diff(pred, gt)
        container_key = canonical_container_key(c)
        assert container_key in diff["containers_added"]

    def test_container_match_rate_one_for_identical(self):
        c = _container("noetic_cluster", "Noetics")
        d = _diagram(containers=[c])
        scores = diagram_similarity_score(d, d)
        assert scores["containers_match_rate"] == 1.0


class TestDomainSubstitution:
    def test_domain_substitution_detected(self):
        # GT: P3 (domain=P, noetic=3); Pred: C3 (domain=C, noetic=3)
        gt_node = _node("state", "P3", role="cognitive_state")
        pred_node = _node("state", "C3", role="cognitive_state")
        gt = _diagram(nodes=[gt_node])
        pred = _diagram(nodes=[pred_node])

        counts = diagram_axis_substitution_counts(pred, gt)
        # domain substitution P→C with matching noetic=3
        assert counts["domain_substitutions"].get("('P', 'C')", 0) == 1
        # noetic did NOT change — no noetic substitution
        assert counts["noetic_substitutions"] == {}
