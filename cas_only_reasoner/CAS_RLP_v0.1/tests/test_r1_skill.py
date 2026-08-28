"""Ring R1: propose, sandbox-test, promote or reject a skill change.

The parent has an overgeneralized taller rule (no magnitude comparison).
RLP must diagnose the held-out failure, propose guarded repairs, promote
the gt-guard child, and reject the lt-guard child because it breaks the
protected regression case.
"""

from rlp.fixture_loader import load_package
from rlp.rlp import CAS_RLP


def test_r1_diagnoses_and_promotes_gt_guard():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    assert cycle["current_revision"] == 13

    verdicts = {d["mutation"]["mutation_id"]: d["verdict"]
                for d in cycle["decisions"]}
    assert verdicts["restrict_r_taller_gt"] == "PROMOTED"
    assert verdicts["restrict_r_taller_lt"] == "REJECTED"

    promoted = rlp.current_package
    rule = promoted["tasks"]["held_out"][0]["rules"][0]
    assert rule["rule_id"] == "r_taller_v13"
    assert {"pred": "gt", "args": ["?Hx", "?Hy"]} in rule["premises"]
    assert rule["source"] == "rlp:restrict_r_taller_gt"


def test_r1_promoted_child_passes_everything():
    from rlp.sandbox import grade, run_suite

    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    rlp.improve()
    results, _ = run_suite(rlp.current_package)
    grades = grade(rlp.current_package, results)
    assert all(g["passed"] for g in grades.values())
    assert grades["held_taller_bo"]["actual_status"] == "NEEDS_INFORMATION"


def test_r1_rejected_child_broke_regression():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    rejected = [d for d in cycle["decisions"]
                if d["mutation"]["mutation_id"] == "restrict_r_taller_lt"][0]
    checks = {c["check"]: c["passed"] for c in rejected["checks"]}
    assert checks["no_protected_regression"] is False
