"""Learning from a mathematical mistake: the full cycle.

The parent ruleset carries the incorrect procedure square_sum
((a+b)^2 -> a^2 + b^2). The machine attempts to prove the false
identity (x+1)^2 = x^2+1; the checker rejects at the first step via
exact sample validation. Diagnosis names the guilty rule; the lesson
library supplies the correct replacement; the repaired descendant is
promoted only under the acceptance law.
"""

from conftest import load_fixture
from cas_math.m1 import CCB_M1


def _cycle():
    package = load_fixture("mistake_package.json")
    m1 = CCB_M1(package)
    cycle = m1.mistake_cycle(package["mistake_task"])
    return m1, cycle


def test_attempt_rejected_at_first_step():
    m1, cycle = _cycle()
    assert cycle["attempt_outcome"]["verdict"] == "REJECTED"
    assert cycle["attempt_outcome"]["first_invalid_step"] == 0
    assert "equality-preserving" in cycle["attempt_outcome"]["reason"]


def test_diagnosis_names_the_guilty_rule():
    m1, cycle = _cycle()
    fault = cycle["fault"]
    assert fault["guilty_rule"] == "square_sum"
    assert fault["classification"] == "procedure_not_equality_preserving"


def test_repair_promoted_and_corrected_proof_verified():
    m1, cycle = _cycle()
    verdicts = {d["repair"]["replacement"]: d["verdict"]
                for d in cycle["decisions"]}
    assert verdicts["square_expand"] == "PROMOTED"
    assert cycle["current_revision"] == 2
    # The corrected machine now proves the true identity with steps.
    result = m1.verify_identity(m1.package["held_out"][0], m1.package)
    assert result["passed"] is True
    assert result["outcome"]["verdict"] == "VERIFIED"
    assert result["steps"], "proof must contain steps after repair"


def test_regression_intact_after_repair():
    m1, cycle = _cycle()
    for task in m1.package["regression"]:
        result = m1.verify_identity(task, m1.package)
        assert result["passed"] is True, task["task_id"]


def test_decisions_sealed_and_cycle_deterministic():
    a_m1, a = _cycle()
    b_m1, b = _cycle()
    assert a["cycle_digest"] == b["cycle_digest"]
    for decision in a["decisions"]:
        assert decision.get("evidence_digest")


def test_rollback_restores_parent_ruleset():
    m1, cycle = _cycle()
    result = m1.rollback()
    assert result["action"] == "ROLLBACK"
    assert result["restored_revision"] == 1
    assert "square_sum" in m1.package["ruleset"]["procedures"]
