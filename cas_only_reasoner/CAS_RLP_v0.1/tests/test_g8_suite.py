"""The CAS-G8 qualification suite: Adaptive Learner.

Per the CRQS standard (spec section 11), the G8 suite is: correction +
delayed retention + structural transfer + protected regression. This
module runs each pillar against the REAL machinery - the kernel judges,
RLP learns, nothing is simulated - plus the stability run that earns
the STABLE D8 demonstration flag: the whole sequence, twice, digest-
identical.
"""

import copy

from rlp.fixture_loader import load_package
from rlp.mutations import Mutation, ProtectedTarget
from rlp.procedural import ProceduralLearner
from rlp.rlp import CAS_RLP, VersionEntry_digest
from rlp.sandbox import grade, run_suite
from rlp.strategies import StrategyMemory

import pytest


def _corrected():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    return rlp, cycle


# ------------------------------------------------------ G8-1: correction
def test_g8_correction_is_retained():
    """The promoted correction persists in the package: a FRESH re-run
    of the corrected suite passes, and the repaired rule carries its
    learning provenance."""
    rlp, cycle = _corrected()
    assert any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    # fresh re-run of the retained package
    results, _ = run_suite(rlp.current_package)
    grades = grade(rlp.current_package, results)
    assert all(g["passed"] for g in grades.values())
    rule = rlp.current_package["tasks"]["held_out"][0]["rules"][0]
    assert rule["source"] == "rlp:restrict_r_taller_gt"
    # the parent remains restorable: retention never destroys history
    revisions = [e["revision"] for e in cycle["version_history"]]
    assert 12 in revisions and 13 in revisions


# ----------------------------------------------- G8-2: delayed retention
def test_g8_correction_survives_intervening_work():
    """DELAYED retention: after the correction, the machine does other,
    unrelated reasoning; the learned content is byte-identical after and
    the corrected suite still passes."""
    from kernel.fixtures import load_problem
    from kernel.kernel import CAS_RRK

    rlp, _ = _corrected()
    digest_before = VersionEntry_digest(rlp.current_package)

    # unrelated intervening work through the same kernel
    for name in ("modux_ponens", "transitive_reasoning",
                 "candidate_planning", "rpm_recursion"):
        packet = CAS_RRK(load_problem(name), run_id="g8_delay", seed=0).run()
        assert packet["terminal_status"] in ("CONCLUDED", "NEEDS_INFORMATION")

    assert VersionEntry_digest(rlp.current_package) == digest_before
    results, _ = run_suite(rlp.current_package)
    grades = grade(rlp.current_package, results)
    assert all(g["passed"] for g in grades.values())


# --------------------------------------------- G8-3: structural transfer
def test_g8_learned_strategy_transfers_without_relearning():
    """The repair strategy is learned ONCE (taller), remembered by fault
    CLASS, then repairs a structurally-similar unseen package (bigger)
    within the same budget of one evaluation - no re-learning."""
    memory = StrategyMemory()
    taller = load_package("r1_overgeneralization")
    learner = ProceduralLearner(taller, copy.deepcopy(taller),
                                budget=1, memory=memory)
    packet = learner.learn()
    assert packet["promoted_strategy"] == "s_gt_first"
    entry = memory.lookup("overgeneral_rule")
    assert entry["status"] == "verified"

    # transfer: the remembered class-level procedure, applied cold
    bigger = load_package("r1_bigger_held_out")
    cycle = CAS_RLP(bigger).improve(guard_order=entry["guard_order"],
                                    max_evaluations=1)
    promoted = [d for d in cycle["decisions"] if d["verdict"] == "PROMOTED"]
    assert len(promoted) == 1
    assert cycle["evaluations_used"] == 1
    assert promoted[0]["mutation"]["mutation_id"] == "restrict_r_bigger_gt"


def test_g8_unstrategic_order_still_fails_the_budget():
    """Contrast case: without the learned order, the same budget is
    exhausted - the transfer above is the strategy working, not the
    problem being easy."""
    bigger = load_package("r1_bigger_held_out")
    cycle = CAS_RLP(bigger).improve(guard_order=["lt", "gt"],
                                    max_evaluations=1)
    assert not any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    assert any(d["verdict"] == "BUDGET_EXHAUSTED"
               for d in cycle["decisions"])


# -------------------------------------------- G8-4: protected regression
def test_g8_regression_intact_and_protection_unweakened():
    """After learning: every regression task still passes, an R3
    mutation is still rejected, and evaluator tampering is still
    rejected. Learning must not weaken the cage it lives in."""
    rlp, _ = _corrected()
    results, _ = run_suite(rlp.current_package)
    grades = grade(rlp.current_package, results)
    assert all(g["passed"] for g in grades.values()
               if g["group"] == "regression")

    with pytest.raises(ProtectedTarget):
        from rlp.mutations import apply_mutation
        apply_mutation(rlp.current_package,
                       Mutation(mutation_id="attack_kernel", ring="R1",
                                target="kernel",
                                change={"kind": "param_change", "value": 0}))

    tamper = rlp._evaluate_mutation(
        Mutation(mutation_id="tamper_tests", ring="R1",
                 target="expectations",
                 change={"kind": "param_change", "value": {}}),
        grade(rlp.current_package, results))
    assert tamper["verdict"] == "REJECTED_AS_PROTECTED"


# ------------------------------------------------- G8-5: stable D8 run
def test_g8_whole_sequence_is_stable():
    """The stability demonstration behind the STABLE D8 flag: the full
    G8 sequence run twice from scratch is digest-identical - cycle
    digests, promoted-package digests, and strategy memory."""
    def one_pass():
        rlp = CAS_RLP(load_package("r1_overgeneralization"))
        cycle = rlp.improve()
        memory = StrategyMemory()
        taller = load_package("r1_overgeneralization")
        learner = ProceduralLearner(taller, copy.deepcopy(taller),
                                    budget=1, memory=memory)
        learn_packet = learner.learn()
        transfer = CAS_RLP(load_package("r1_bigger_held_out")).improve(
            guard_order=memory.lookup("overgeneral_rule")["guard_order"],
            max_evaluations=1)
        return (cycle["cycle_digest"],
                VersionEntry_digest(rlp.current_package),
                learn_packet["cycle_digest"],
                transfer["cycle_digest"],
                memory.to_json())

    assert one_pass() == one_pass()
