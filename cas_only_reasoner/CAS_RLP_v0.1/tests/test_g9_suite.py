"""The CAS-G9 qualification suite: Self-Improving Architect.

Per the CRQS standard (spec section 11), the G9 suite is:
self-diagnosis + sandbox + reject-unauthorized + promote + parent
replay - held to the section-19 anti-gaming bar from the start:

  - the machine diagnoses its own PROCEDURE fault from its own SEALED
    evidence (never from a human pointing at it);
  - the candidate procedure is SYNTHESIZED from the machine's own
    sandbox exploration (closing the recorded G8 bound: no hand-
    authored strategy library in this loop);
  - the causal ablation is a test: skip the self-improvement cycle and
    the same budgeted repair fails on training AND held-out;
  - the judge (expectations + protected set) is digest-checked
    untouched across the whole cycle;
  - the parent's exact behavior replays after rollback;
  - the whole cycle, twice from scratch, is digest-identical (the
    STABLE D9 demonstration).
"""

import copy
import json

from rlp.fixture_loader import load_package
from rlp.mutations import DEFAULT_GUARD_POOL, Mutation, ProtectedTarget
from rlp.rlp import CAS_RLP, VersionEntry_digest
from rlp.sandbox import grade, run_suite
from rlp.self_improvement import (SelfImprover, diagnose_procedure,
                                  synthesize_order)
from rlp.strategies import StrategyMemory

import pytest


def _improver(memory=None):
    return SelfImprover(load_package("r1_overgeneralization"),
                        load_package("r1_bigger_held_out"),
                        budget=1, memory=memory)


# ------------------------------------------------- G9-1: self-diagnosis
def test_g9_self_diagnosis_reads_sealed_evidence_only():
    """The machine finds the fault in its own PROCEDURE from the sealed
    cycle packet: no promotion + budget-starved candidates = a typed
    procedure_budget_failure naming the starved candidates and the
    evidence digest it was read from."""
    cycle = CAS_RLP(load_package("r1_overgeneralization")).improve(
        max_evaluations=1)
    fault = diagnose_procedure(cycle, budget=1)
    assert fault is not None
    assert fault["fault_kind"] == "procedure_budget_failure"
    assert fault["starved_candidates"] == ["restrict_r_taller_gt",
                                           "restrict_r_taller_lt"]
    assert fault["evidence_digest"] == cycle["cycle_digest"]


def test_g9_no_false_positive_when_procedure_is_fine():
    """A successful cycle diagnoses NO procedural fault - the machine
    does not invent work for itself."""
    good = CAS_RLP(load_package("r1_overgeneralization")).improve(
        guard_order=["gt"], max_evaluations=1)
    assert diagnose_procedure(good, budget=1) is None
    # and the full loop reports the typed no-op honestly
    memory = StrategyMemory()
    memory.add_provisional("overgeneral_rule", ["gt", "eq", "lt"])
    memory.promote("overgeneral_rule")
    packet = _improver(memory=memory).run()
    assert packet["status"] == "NO_PROCEDURAL_FAULT"


# ------------------------------------------------------- G9-2: sandbox
def test_g9_exploration_is_sandboxed_parent_untouched():
    """The exploration and validation runs happen on COPIES: the parent
    packages and the parent strategy memory are byte-identical after
    the whole cycle."""
    training = load_package("r1_overgeneralization")
    held_out = load_package("r1_bigger_held_out")
    improver = SelfImprover(training, held_out, budget=1)
    before_train = VersionEntry_digest(improver.training_package)
    before_held = VersionEntry_digest(improver.held_out_package)
    parent_memory = copy.deepcopy(improver.parent_memory)
    packet = improver.run()
    assert packet["status"] == "PROMOTED"
    assert VersionEntry_digest(improver.training_package) == before_train
    assert VersionEntry_digest(improver.held_out_package) == before_held
    assert packet["parent_memory"] == parent_memory


# ------------------------------------------------------ G9-3: synthesis
def test_g9_procedure_synthesized_from_own_evidence():
    """The candidate order is DERIVED from the sealed exploration - the
    promoted mutation's guard moves to the front - and the synthesis
    records exactly which evidence it came from. No library entry
    supplies it."""
    packet = _improver().run()
    assert packet["status"] == "PROMOTED"
    synthesis = packet["synthesis"]
    assert synthesis["guard_order"] == ["gt", "eq", "lt"]
    assert synthesis["guard_order"] != list(DEFAULT_GUARD_POOL)
    assert synthesis["derived_from_mutation"] == "restrict_r_taller_gt"
    assert synthesis["derived_from_evidence"] == packet["exploration_digest"]
    entry = packet["memory"]["overgeneral_rule"]
    assert entry["status"] == "verified"
    assert entry["provenance"].startswith("self_improvement:")


# ------------------------------------------- G9-4: promote + held-out
def test_g9_promoted_procedure_repairs_held_out_and_transfers():
    """The promoted procedure fits the budget on training AND the
    held-out fault case, and the improved memory then drives the
    machine's own recall loop on the structurally-varied package."""
    improver = _improver()
    packet = improver.run()
    checks = {c["check"]: c["passed"] for c in packet["validation"]["checks"]}
    assert checks == {"budget_success": True, "held_out_gain": True,
                      "no_regression": True, "evaluator_untouched": True,
                      "versioned": True, "rollback_preserved": True}
    # the self-improved memory now powers the G8 transfer path
    cycle = CAS_RLP(load_package("r1_heavier_structural")).improve(
        strategy_memory=improver.memory, max_evaluations=1)
    assert any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    assert cycle["evaluations_used"] == 1
    assert cycle["strategy_recalls"][0]["recalled"] is True


# ------------------------------------------- G9-5: reject-unauthorized
def test_g9_unauthorized_descendants_rejected_judge_untouched():
    """Inside the improvement context: an R3-target mutation raises,
    evaluator tampering is rejected, and the judge digest is identical
    before and after the whole promoted cycle."""
    from rlp.mutations import apply_mutation

    improver = _improver()
    packet = improver.run()
    assert packet["judge_digest_before"] == packet["judge_digest_after"]

    with pytest.raises(ProtectedTarget):
        apply_mutation(improver.training_package,
                       Mutation(mutation_id="attack", ring="R1",
                                target="proof_checker",
                                change={"kind": "param_change", "value": 0}))
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    rlp.improve()
    results, _ = run_suite(rlp.current_package)
    tamper = rlp._evaluate_mutation(
        Mutation(mutation_id="tamper", ring="R1", target="expectations",
                 change={"kind": "param_change", "value": {}}),
        grade(rlp.current_package, results))
    assert tamper["verdict"] == "REJECTED_AS_PROTECTED"


# --------------------------------------------- G9-6: parent replay
def test_g9_parent_replays_exactly_after_rollback():
    """Seal the parent's behavior, promote a child, roll back, re-run:
    the restored parent's grades and state hashes are identical to the
    pre-promotion run - the parent is replayable, not just 'saved'."""
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    before_results, _ = run_suite(rlp.current_package)
    before = {pid: (g["actual_status"], g["final_state_hash"])
              for pid, g in grade(rlp.current_package,
                                  before_results).items()}
    cycle = rlp.improve()
    assert any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    assert rlp.current_package["revision"] == 13
    rollback = rlp.rollback()
    assert rollback["restored_revision"] == 12
    after_results, _ = run_suite(rlp.current_package)
    after = {pid: (g["actual_status"], g["final_state_hash"])
             for pid, g in grade(rlp.current_package,
                                 after_results).items()}
    assert after == before
    # memory rollback restores the parent snapshot too
    improver = _improver()
    improver.run()
    assert improver.memory.lookup("overgeneral_rule") is not None
    improver.rollback()
    assert improver.memory.lookup("overgeneral_rule") is None


# --------------------------------------------- G9-7: causal ablation
def test_g9_causal_ablation_without_self_improvement_fails():
    """Section-19 anti-gaming: skip the self-improvement cycle and the
    same budgeted repair fails on training AND held-out; run it and
    both succeed under the same budget. The cycle is load-bearing."""
    for name in ("r1_overgeneralization", "r1_bigger_held_out"):
        bare = CAS_RLP(load_package(name)).improve(max_evaluations=1)
        assert not any(d["verdict"] == "PROMOTED"
                       for d in bare["decisions"])
    improver = _improver()
    assert improver.run()["status"] == "PROMOTED"
    for name in ("r1_overgeneralization", "r1_bigger_held_out"):
        improved = CAS_RLP(load_package(name)).improve(
            strategy_memory=improver.memory, max_evaluations=1)
        assert any(d["verdict"] == "PROMOTED"
                   for d in improved["decisions"])
        assert improved["evaluations_used"] == 1


# --------------------------------------------- G9-8: stable D9 run
def test_g9_whole_cycle_is_stable():
    """The STABLE D9 demonstration: the complete self-improvement
    sequence - diagnose, explore, synthesize, validate, promote,
    transfer - run twice from scratch, digest-identical."""
    def one_pass():
        improver = _improver()
        packet = improver.run()
        transfer = CAS_RLP(load_package("r1_heavier_structural")).improve(
            strategy_memory=improver.memory, max_evaluations=1)
        return (packet["cycle_digest"], packet["exploration_digest"],
                json.dumps(packet["synthesis"], sort_keys=True),
                transfer["cycle_digest"],
                json.dumps(improver.memory.to_json(), sort_keys=True))

    assert one_pass() == one_pass()
