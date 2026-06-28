"""Tests for canonical CAS diagram graph helpers."""

from __future__ import annotations

from cas_synthetic.schemas.diagram_graph import (
    canonical_graph_keys,
    diagram_summary,
    diff_diagrams,
)


def _diagram(label: str = "CO-2") -> dict:
    return {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "layouts": ["radial", "dependency"],
        "nodes": [
            {"id": "n1", "kind": "noetic", "label": label, "role": "atomic_noetic"},
            {"id": "n2", "kind": "domain", "label": "P", "role": "processing_domain"},
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "kind": "dependency",
                "label": "->",
                "directed": True,
            }
        ],
        "containers": [
            {
                "id": "c1",
                "kind": "noetic_cluster",
                "label": "NoeticCluster{^2}",
                "contains": ["n1"],
                "cardinality": 1,
                "element_type": "noetic",
            }
        ],
    }


def test_canonical_graph_keys_ignore_raw_ids_but_preserve_structure():
    first = _diagram()
    second = _diagram()
    second["nodes"][0]["id"] = "different"
    second["containers"][0]["contains"] = ["different"]
    second["edges"][0]["source"] = "different"

    assert canonical_graph_keys(first) == canonical_graph_keys(second)


def test_diagram_summary_hash_changes_on_structural_change():
    first = diagram_summary(_diagram("CO-2"))
    second = diagram_summary(_diagram("CO-3"))

    assert first["node_count"] == 2
    assert first["edge_count"] == 1
    assert first["container_count"] == 1
    assert first["graph_hash"] != second["graph_hash"]


def test_diff_diagrams_reports_missing_and_extra_structure():
    predicted = _diagram("CO-3")
    expected = _diagram("CO-2")

    diff = diff_diagrams(predicted, expected)

    assert diff["equal"] is False
    assert diff["nodes"]["missing_count"] == 1
    assert diff["nodes"]["extra_count"] == 1
