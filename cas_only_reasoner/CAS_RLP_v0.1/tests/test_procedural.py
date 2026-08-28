"""Procedural learning: strategies promoted under the acceptance law."""

from rlp.fixture_loader import load_package
from rlp.procedural import ProceduralLearner, STRATEGY_LIBRARY
from rlp.rlp import CAS_RLP
from rlp.strategies import StrategyError, StrategyMemory


def _packages():
    training = load_package("r1_overgeneralization")
    held_out = load_package("r1_bigger_held_out")
    return training, held_out


def test_strategy_memory_versioning():
    memory = StrategyMemory()
    memory.add_provisional("overgeneral_rule", ["gt", "lt"])
    entry = memory.promote("overgeneral_rule")
    assert entry["status"] == "verified"
    assert entry["revision"] == 2
    assert entry["history"][0]["revision"] == 1
    try:
        memory.add_provisional("overgeneral_rule", ["lt", "gt"])
        assert False, "duplicate strategy should raise"
    except StrategyError:
        pass


def test_improve_respects_budget():
    training, _ = _packages()
    cycle = CAS_RLP(training).improve(guard_order=["lt", "gt"],
                                      max_evaluations=1)
    verdicts = [d.get("verdict") for d in cycle["decisions"]]
    assert "BUDGET_EXHAUSTED" in verdicts
    assert cycle["evaluations_used"] == 1
    assert cycle["current_revision"] == 12  # nothing promoted


def test_gt_first_repairs_within_budget():
    training, _ = _packages()
    cycle = CAS_RLP(training).improve(guard_order=["gt", "lt"],
                                      max_evaluations=1)
    assert cycle["evaluations_used"] == 1
    assert cycle["current_revision"] == 13
    assert any(d.get("verdict") == "PROMOTED" for d in cycle["decisions"])


def test_learner_promotes_gt_first_rejects_lt_first():
    training, held_out = _packages()
    learner = ProceduralLearner(training, held_out, budget=1)
    cycle = learner.learn()
    verdicts = {d["strategy"]["strategy_id"]: d["verdict"]
                for d in cycle["decisions"]}
    assert verdicts["s_gt_first"] == "PROMOTED"
    assert verdicts["s_lt_first"] == "REJECTED"
    assert cycle["promoted_strategy"] == "s_gt_first"
    entry = learner.memory.lookup("overgeneral_rule")
    assert entry["status"] == "verified"
    assert entry["guard_order"] == ["gt", "lt"]
    assert entry["provenance"] == "prior_proof"


def test_held_out_repair_evidence_recorded():
    training, held_out = _packages()
    learner = ProceduralLearner(training, held_out, budget=1)
    cycle = learner.learn()
    gt = [d for d in cycle["decisions"]
          if d["strategy"]["strategy_id"] == "s_gt_first"][0]
    assert gt["held_out"]["promoted"] is True
    assert gt["held_out"]["evaluations_used"] == 1
    assert gt["training"]["promoted"] is True
    lt = [d for d in cycle["decisions"]
          if d["strategy"]["strategy_id"] == "s_lt_first"][0]
    assert lt["held_out"]["promoted"] is False


def test_acceptance_law_checks_present():
    training, held_out = _packages()
    learner = ProceduralLearner(training, held_out, budget=1)
    cycle = learner.learn()
    gt = [d for d in cycle["decisions"]
          if d["strategy"]["strategy_id"] == "s_gt_first"][0]
    checks = {c["check"]: c["passed"] for c in gt["checks"]}
    assert checks["budget_success"] is True
    assert checks["held_out_gain"] is True
    assert checks["no_regression"] is True
    assert checks["evaluator_untouched"] is True
    assert checks["rollback_preserved"] is True


def test_unbudgeted_default_behavior_regression_intact():
    training, _ = _packages()
    cycle = CAS_RLP(training).improve()
    assert cycle["current_revision"] == 13
    verdicts = {d["mutation"]["mutation_id"]: d["verdict"]
                for d in cycle["decisions"]}
    assert verdicts["restrict_r_taller_gt"] == "PROMOTED"


def test_learner_deterministic():
    training, held_out = _packages()
    a = ProceduralLearner(training, held_out, budget=1).learn()
    b = ProceduralLearner(training, held_out, budget=1).learn()
    assert a["cycle_digest"] == b["cycle_digest"]
    assert a["promoted_strategy"] == b["promoted_strategy"]


def test_decisions_seal_evidence():
    training, held_out = _packages()
    cycle = ProceduralLearner(training, held_out, budget=1).learn()
    for decision in cycle["decisions"]:
        assert decision.get("evidence_digest")


def test_rollback_restores_parent_memory():
    training, held_out = _packages()
    learner = ProceduralLearner(training, held_out, budget=1)
    learner.learn()
    assert learner.memory.lookup("overgeneral_rule") is not None
    result = learner.rollback()
    assert result["action"] == "ROLLBACK"
    assert learner.memory.lookup("overgeneral_rule") is None
