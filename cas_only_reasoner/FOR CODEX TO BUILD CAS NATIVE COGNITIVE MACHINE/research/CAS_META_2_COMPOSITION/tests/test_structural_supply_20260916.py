"""Pure source audit tests: structural identity and real public-byte transport."""
import pytest

from tools.check_structural_supply_20260916 import (
    face_inventory, graph_key, probe_public_audit, topology_key)


def test_topology_ignores_names_node_order_and_edge_order():
    assert topology_key(["a", "b", "c"], [("a", "b"), ("b", "c")]) == topology_key(
        ["Y", "Z", "X"], [("Y", "Z"), ("X", "Y")])


def test_topology_distinguishes_same_size_different_directed_structure():
    chain = topology_key(["a", "b", "c"], [("a", "b"), ("b", "c")])
    fork = topology_key(["a", "b", "c"], [("a", "b"), ("a", "c")])
    assert chain != fork


def test_topology_distinguishes_degree_equivalent_nonisomorphic_graphs():
    # A six-cycle and two three-cycles have the same per-node degrees.
    nodes = list(range(6))
    cycle = [(i, (i + 1) % 6) for i in nodes]
    triangles = [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)]
    assert topology_key(nodes, cycle) != topology_key(nodes, triangles)


def test_isolated_nodes_are_not_dropped():
    assert topology_key(["a", "b"], [("a", "b")]) != topology_key(
        ["a", "b", "isolated"], [("a", "b")])


@pytest.mark.parametrize("nodes,edges,code", [
    (["a", "a"], [], "UNIQUE_NONEMPTY_NODES_REQUIRED"),
    (["a"], [("a", "missing")], "UNKNOWN_EDGE_NODE"),
    (["a", "b"], [("a", "b"), ("a", "b")], "DUPLICATE_EDGE"),
])
def test_invalid_graphs_fail_closed(nodes, edges, code):
    with pytest.raises(ValueError, match=code):
        topology_key(nodes, edges)


def test_non_containment_graph_is_not_silently_collapsed():
    with pytest.raises(ValueError, match="CONTAINMENT_ONLY_AUDIT"):
        graph_key({"nodes": [{"identifier": "a"}, {"identifier": "b"}],
                   "relations": [{"kind": "triggers", "source": "a", "target": "b"}]})


def test_face_holdout_ids_do_not_become_unseen_topologies():
    report = face_inventory()
    assert report["root_family_ids"] == 96
    assert report["exact_topologies"] == 6
    assert report["splits"]["final_held_out"]["root_family_ids"] == 16
    assert report["splits"]["final_held_out"]["topologies_absent_from_training"] == 0


def test_probe_report_follows_current_public_transport():
    report = probe_public_audit()
    assert report["neural_measurements"] == 0
    assert report["by_contrast"]["reordered"]["whole_public_unchanged"] == 0
    for stats in report["by_contrast"].values():
        assert stats["public_problem_unchanged"] == 0
        assert stats["record_id_unchanged"] == 0
    assert report["list_length_inputs_function_present"]
    assert report["length_permutations_per_list_case"] == [6] * 10
