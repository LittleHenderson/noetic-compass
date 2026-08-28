"""The CAS-G8 qualification suite: Adaptive Learner.

Per the CRQS standard (spec section 11): correction + delayed retention
+ transfer + regression - now held to the section-19 anti-gaming bar
after an adversarial audit refuted the first version of this suite:

  - the CAUSAL ABLATION is a test: remove the learned strategy and the
    same repair FAILS under the same budget (the default pool is
    neutral, so the strategy is load-bearing, not decorative);
  - the transfer target is STRUCTURALLY varied (different predicates,
    different variable names, reversed premise order, distractor
    entity and facts), not a string rename;
  - the machine closes diagnose -> recall -> apply ITSELF via
    improve(strategy_memory=...) - production code, not test stitching;
  - delayed retention crosses a PROCESS boundary: the corrected package
    is persisted, reloaded in a fresh interpreter, and re-verified.
"""

import json
import os
import subprocess
import sys
import tempfile

from rlp.fixture_loader import load_package
from rlp.mutations import DEFAULT_GUARD_POOL, Mutation, ProtectedTarget
from rlp.procedural import ProceduralLearner
from rlp.rlp import CAS_RLP, VersionEntry_digest
from rlp.sandbox import grade, run_suite
from rlp.strategies import StrategyMemory

import pytest

RLP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _corrected():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    return rlp, cycle


def _learned_memory():
    """Learn the class strategy ONCE, on taller (training) with bigger
    as the learner's held-out - the structural fixture stays unseen."""
    memory = StrategyMemory()
    learner = ProceduralLearner(load_package("r1_overgeneralization"),
                                load_package("r1_bigger_held_out"),
                                budget=1, memory=memory)
    packet = learner.learn()
    return memory, packet


# ------------------------------------------------------ G8-1: correction
def test_g8_correction_is_retained():
    """The promoted correction persists in the package: a FRESH re-run
    of the corrected suite passes, and the repaired rule carries its
    learning provenance."""
    rlp, cycle = _corrected()
    assert any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    results, _ = run_suite(rlp.current_package)
    grades = grade(rlp.current_package, results)
    assert all(g["passed"] for g in grades.values())
    rule = rlp.current_package["tasks"]["held_out"][0]["rules"][0]
    assert rule["source"] == "rlp:restrict_r_taller_gt"
    revisions = [e["revision"] for e in cycle["version_history"]]
    assert 12 in revisions and 13 in revisions


# ----------------------------------------------- G8-2: delayed retention
def test_g8_correction_survives_intervening_work():
    """Within-process leg: unrelated kernel work between the correction
    and the re-check; learned content byte-identical and still passing."""
    from kernel.fixtures import load_problem
    from kernel.kernel import CAS_RRK

    rlp, _ = _corrected()
    digest_before = VersionEntry_digest(rlp.current_package)
    for name in ("modux_ponens", "transitive_reasoning",
                 "candidate_planning", "rpm_recursion"):
        packet = CAS_RRK(load_problem(name), run_id="g8_delay", seed=0).run()
        assert packet["terminal_status"] in ("CONCLUDED", "NEEDS_INFORMATION")
    assert VersionEntry_digest(rlp.current_package) == digest_before
    results, _ = run_suite(rlp.current_package)
    assert all(g["passed"]
               for g in grade(rlp.current_package, results).values())


def test_g8_correction_survives_process_boundary():
    """Cross-process leg: persist the corrected package, reload it in a
    FRESH interpreter, re-run and re-grade there. Retention is on disk,
    not an artifact of one in-memory object."""
    rlp, _ = _corrected()
    digest = VersionEntry_digest(rlp.current_package)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "corrected_package.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rlp.current_package, fh, sort_keys=True)
        code = (
            "import json, sys\n"
            "sys.path.insert(0, " + repr(RLP_ROOT) + ")\n"
            "from rlp.rlp import VersionEntry_digest\n"
            "from rlp.sandbox import grade, run_suite\n"
            "pkg = json.load(open(" + repr(path) + ", encoding='utf-8'))\n"
            "results, _ = run_suite(pkg)\n"
            "grades = grade(pkg, results)\n"
            "assert all(g['passed'] for g in grades.values()), grades\n"
            "print('DIGEST=' + VersionEntry_digest(pkg))\n"
            "print('ALL_PASS')\n"
        )
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr
        assert "ALL_PASS" in proc.stdout
        assert "DIGEST=" + digest in proc.stdout


# --------------------------------------------- G8-3: structural transfer
def test_g8_learned_strategy_transfers_structurally():
    """The class strategy is learned once (taller/bigger), then the
    MACHINE ITSELF - improve(strategy_memory=...) - diagnoses the
    structurally-varied heavier package (different predicates and
    variable names, reversed premises, distractor entity and facts),
    recalls the strategy by fault class, and repairs it in ONE
    evaluation, landing the guard on the right structural variables."""
    memory, packet = _learned_memory()
    assert packet["promoted_strategy"] == "s_gt_first"
    assert memory.lookup("overgeneral_rule")["status"] == "verified"

    cycle = CAS_RLP(load_package("r1_heavier_structural")).improve(
        strategy_memory=memory, max_evaluations=1)
    promoted = [d for d in cycle["decisions"] if d["verdict"] == "PROMOTED"]
    assert len(promoted) == 1
    assert cycle["evaluations_used"] == 1
    assert promoted[0]["mutation"]["mutation_id"] == "restrict_r_heavier_gt"
    # the recall was the machine's own act, recorded as provenance
    assert cycle["strategy_recalls"] == [{
        "problem_id": "held_heavier_bo",
        "fault_class": "overgeneral_rule",
        "recalled": True,
        "guard_order": ["gt", "lt"],
    }]
    # the guard landed on the rule's OWN variables, conclusion-aligned
    rule = promoted[0]["child_package"]["tasks"]["held_out"][0]["rules"][0]
    assert {"pred": "gt", "args": ["?Wx", "?Wy"]} in rule["premises"]


def test_g8_causal_ablation_no_strategy_fails():
    """Section-19 anti-gaming: REMOVE the learned component and the
    capability degrades. The neutral default pool (eq first) exhausts
    the same budget on the same package with no promotion."""
    assert DEFAULT_GUARD_POOL == ("eq", "gt", "lt")
    cycle = CAS_RLP(load_package("r1_heavier_structural")).improve(
        max_evaluations=1)
    assert not any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])
    assert any(d["verdict"] == "BUDGET_EXHAUSTED"
               for d in cycle["decisions"])
    # empty memory degrades identically: recall honestly reports a miss
    cycle2 = CAS_RLP(load_package("r1_heavier_structural")).improve(
        strategy_memory=StrategyMemory(), max_evaluations=1)
    assert not any(d["verdict"] == "PROMOTED" for d in cycle2["decisions"])
    assert cycle2["strategy_recalls"][0]["recalled"] is False


def test_g8_wrong_order_contrast_still_fails():
    """The wrong explicit order also fails the budget - success above
    is the ORDER, not the problem being easy."""
    cycle = CAS_RLP(load_package("r1_heavier_structural")).improve(
        guard_order=["lt", "eq", "gt"], max_evaluations=1)
    assert not any(d["verdict"] == "PROMOTED" for d in cycle["decisions"])


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
    G8 sequence - correction, learning, machine-driven structural
    transfer - run twice from scratch, digest-identical."""
    def one_pass():
        rlp = CAS_RLP(load_package("r1_overgeneralization"))
        cycle = rlp.improve()
        memory, learn_packet = _learned_memory()
        transfer = CAS_RLP(load_package("r1_heavier_structural")).improve(
            strategy_memory=memory, max_evaluations=1)
        return (cycle["cycle_digest"],
                VersionEntry_digest(rlp.current_package),
                learn_packet["cycle_digest"],
                transfer["cycle_digest"],
                memory.to_json())

    assert one_pass() == one_pass()


def test_g8_learned_strategy_cannot_block_a_correct_eq_repair():
    """Audit finding, closed: a strategy REORDERS the pool, never
    shrinks it. On a fault whose correct guard is eq - which the
    learned gt-first strategy did not anticipate - the residual pool
    still reaches eq, so the repair promotes instead of dead-ending."""
    import copy as _copy
    pkg = _copy.deepcopy(load_package("r1_heavier_structural"))
    # counterfactual same_weight package: crate_a and crate_b weigh the
    # same (8); crate_c weighs 5. The unguarded rule wrongly concludes
    # same_weight(crate_a, crate_c); the CORRECT guard is eq.
    for group in ("regression", "held_out"):
        for task in pkg["tasks"][group]:
            task["propositions"] = [
                prop for prop in task["propositions"]
                if prop["pred"] not in ("gt",)]
            for prop in task["propositions"]:
                if prop["pred"] == "weight" and prop["args"][1] == "2":
                    prop["args"][1] = "8"
            task["propositions"].append({"pred": "eq", "args": ["8", "8"]})
            for rule in task["rules"]:
                rule["conclusion"]["pred"] = "same_weight"
    reg = pkg["tasks"]["regression"][0]
    held = pkg["tasks"]["held_out"][0]
    reg["goal"]["desired_outcome"] = {"pred": "same_weight",
                                      "args": ["crate_a", "crate_b"]}
    reg["alternatives"] = [reg["goal"]["desired_outcome"]]
    held["goal"]["desired_outcome"] = {"pred": "same_weight",
                                       "args": ["crate_a", "crate_c"]}
    held["alternatives"] = [held["goal"]["desired_outcome"]]
    pkg["expectations"] = {
        reg["problem_id"]: {"status": "CONCLUDED",
                            "conclusion": {"pred": "same_weight",
                                           "args": ["crate_a", "crate_b"]}},
        held["problem_id"]: {"status": "NEEDS_INFORMATION",
                             "conclusion": None},
    }

    memory, _ = _learned_memory()          # gt-first strategy on record
    cycle = CAS_RLP(pkg).improve(strategy_memory=memory)
    promoted = [d for d in cycle["decisions"] if d["verdict"] == "PROMOTED"]
    # gt and lt fail, the RESIDUAL eq candidate still gets its turn
    assert promoted, [d["verdict"] for d in cycle["decisions"]]
    assert promoted[0]["mutation"]["mutation_id"].endswith("_eq")
    rejected = {d["mutation"]["mutation_id"]: d["verdict"]
                for d in cycle["decisions"]}
    assert rejected["restrict_r_heavier_gt"] == "REJECTED"
