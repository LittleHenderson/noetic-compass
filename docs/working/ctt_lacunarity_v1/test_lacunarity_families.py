"""Hand-computed checks for the Rank 3 measures. Every expected value below is derived by hand in the comment."""
from __future__ import annotations

from lacunarity_families import recipe_fragility, rpm_fragility, theoretical_yield


def test_yield_single_ingredient():
    assert theoretical_yield({"a": 5.0}, [["a"]]) == 5.0


def test_yield_substitution_takes_best():
    # group [a, b]: 2 vs 3 -> 3
    assert theoretical_yield({"a": 2.0, "b": 3.0}, [["a", "b"]]) == 3.0


def test_yield_and_of_two_groups():
    # min(2, 2) = 2
    assert theoretical_yield({"a": 2.0, "b": 2.0}, [["a"], ["b"]]) == 2.0


def test_fragility_single_required_ingredient_is_one():
    assert recipe_fragility({"a": 5.0}, [["a"]]) == 1.0


def test_fragility_two_substitutes():
    # base 3; removing a leaves max(3) = 3 (ratio 1); removing b leaves 2 (ratio 2/3); F = 1 - (1 + 2/3)/2 = 1/6
    assert abs(recipe_fragility({"a": 2.0, "b": 3.0}, [["a", "b"]]) - (1.0 - (1.0 + 2.0 / 3.0) / 2.0)) < 1e-12


def test_fragility_and_of_two_required_is_one():
    # base 2; remove either -> 0; F = 1
    assert recipe_fragility({"a": 2.0, "b": 2.0}, [["a"], ["b"]]) == 1.0


def test_fragility_partial_substitution():
    # base min(1,1)=1; remove a -> min(1,1)=1 (b); remove b -> 1 (a); remove c -> 0; F = 1 - 2/3
    assert abs(recipe_fragility({"a": 1.0, "b": 1.0, "c": 1.0}, [["a", "b"], ["c"]]) - (1.0 - 2.0 / 3.0)) < 1e-12


def test_fragility_zero_state_is_one():
    assert recipe_fragility({}, [["a"]]) == 1.0


def test_rpm_chain_of_four():
    # 0->1->2->3: reach 0=3, 1=2, 2=1; after removal 0->2, 1->1, 2->0; F = 1 - (2/3+1/2+0)/3
    edges = [("0", "1"), ("1", "2"), ("2", "3")]
    expected = 1.0 - ((2 / 3) + (1 / 2) + 0.0) / 3
    assert abs(rpm_fragility(edges) - expected) < 1e-12


def test_rpm_star_center_carries_all():
    # 0 -> 1,2,3: only node 0 has reach; removing it loses everything -> F = 1
    assert rpm_fragility([("0", "1"), ("0", "2"), ("0", "3")]) == 1.0


def test_rpm_no_edges_is_zero():
    assert rpm_fragility([]) == 0.0


def test_rpm_two_node_chain_is_one():
    # 0->1: reach 0 = 1; removing 0 -> 0; F = 1
    assert rpm_fragility([("0", "1")]) == 1.0


def test_rpm_cycle_hand_value():
    # 0->1->2->0: each reach 2; after removing n, successor reaches 1 (other of 2); ratio 1/2; F = 1/2
    assert abs(rpm_fragility([("0", "1"), ("1", "2"), ("2", "0")]) - 0.5) < 1e-12


def test_rpm_negative_control_two_independent_chains():
    # 0->1 and 2->3: removing 0 loses {1} of reach {1} -> 0; same for 2 -> F = 1
    assert rpm_fragility([("0", "1"), ("2", "3")]) == 1.0
