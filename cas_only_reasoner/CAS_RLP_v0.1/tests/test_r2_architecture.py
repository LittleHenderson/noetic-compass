"""Ring R2: parameter changes run in sandboxes with regression gates."""

from rlp.acceptance import decide
from rlp.fixture_loader import load_package
from rlp.mutations import Mutation
from rlp.rlp import CAS_RLP
from rlp.sandbox import grade, run_suite


def _evaluate(rlp, mutation):
    parent_results, _ = run_suite(rlp.current_package)
    parent_grades = grade(rlp.current_package, parent_results)
    return rlp._evaluate_mutation(mutation, parent_grades)


def test_r2_breaking_parameter_change_rejected():
    rlp = CAS_RLP(load_package("r2_parameter"))
    mutation = Mutation("m_ticks1", "R2", "max_ticks",
                        {"kind": "param_change", "value": 1},
                        "starve the tick budget")
    decision = _evaluate(rlp, mutation)
    assert decision["verdict"] == "REJECTED"
    checks = {c["check"]: c for c in decision["checks"]}
    assert checks["no_protected_regression"]["passed"] is False


def test_r2_no_gain_quarantined():
    rlp = CAS_RLP(load_package("r2_parameter"))
    mutation = Mutation("m_ticks300", "R2", "max_ticks",
                        {"kind": "param_change", "value": 300},
                        "more ticks, no demonstrated gain")
    decision = _evaluate(rlp, mutation)
    assert decision["verdict"] == "QUARANTINED"
    checks = {c["check"]: c for c in decision["checks"]}
    assert checks["no_protected_regression"]["passed"] is True
    assert checks["held_out_gain"]["passed"] is False
