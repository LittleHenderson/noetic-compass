"""Regression cover for the two prover changes that unblocked CCB-T1:

1. unify_rule_conclusion - goal-side variables stay FREE instead of
   binding rule variables to the literal variable string;
2. two-pass fact selection - distinct premise variables prefer distinct
   facts, with reuse as a fallback only.

Without change 1, prove(total(?T)) dies because ?N gets bound to the
string "?T". Without change 2, value(?X,..) and value(?Y,..) both grab
the first value fact and sum(?X,?Y,..) can never match.
"""

from kernel.cas_sem import (Proposition, evidence, match, prove,
                            unify_rule_conclusion)
from kernel.schemas import Rule


def P(pred, *args):
    return Proposition(pred, tuple(args))


def R(rule_id, premises, conclusion):
    return Rule(rule_id=rule_id, premises=list(premises),
                conclusion=conclusion, source="test")


# ------------------------------------------------- unify_rule_conclusion
def test_goal_side_variables_stay_free():
    binding = unify_rule_conclusion(P("total", "?N"), P("total", "?T"))
    assert binding == {}          # ?N left FREE, not bound to "?T"
    # the old behavior (plain match) is exactly the bug:
    assert match(P("total", "?N"), P("total", "?T")) == {"?N": "?T"}


def test_ground_goals_behave_exactly_as_match():
    assert unify_rule_conclusion(P("total", "?N"), P("total", "5")) \
        == match(P("total", "?N"), P("total", "5")) == {"?N": "5"}
    assert unify_rule_conclusion(P("total", "a", "?N"),
                                 P("total", "b", "5")) is None
    assert unify_rule_conclusion(P("other", "?N"), P("total", "5")) is None


def test_conflicting_repeat_variable_rejected():
    assert unify_rule_conclusion(P("pair", "?N", "?N"),
                                 P("pair", "1", "2")) is None
    assert unify_rule_conclusion(P("pair", "?N", "?N"),
                                 P("pair", "1", "1")) == {"?N": "1"}


def test_prove_goal_with_variable_through_rule():
    props = [P("value", "x", "2")]
    rules = [R("r1", [P("value", "?X", "?N")], P("total", "?N"))]
    proof = prove(P("total", "?T"), props, rules)
    assert proof.success
    assert proof.rules_used == ["r1"]


# ------------------------------------------------- two-pass fact selection
def test_distinct_variables_prefer_distinct_facts():
    props = [P("value", "x", "2"), P("value", "y", "3"),
             P("sum", "x", "y", "5")]
    rules = [R("r_total",
               [P("value", "?X", "?Nx"), P("value", "?Y", "?Ny"),
                P("sum", "?X", "?Y", "?S")],
               P("total", "?S"))]
    status, proof = evidence(P("total", "5"), props, rules)
    assert status == "SUPPORTED"
    assert proof.rules_used == ["r_total"]


def test_reuse_still_allowed_as_fallback():
    # Only ONE value fact exists; ?X and ?Y must legitimately share it.
    props = [P("value", "x", "2"), P("sum", "x", "x", "4")]
    rules = [R("r_double",
               [P("value", "?X", "?Nx"), P("value", "?Y", "?Ny"),
                P("sum", "?X", "?Y", "?S")],
               P("total", "?S"))]
    status, _ = evidence(P("total", "4"), props, rules)
    assert status == "SUPPORTED"
