"""The five load-bearing laws and the runtime invariants."""

from dataclasses import replace

import pytest

from cas_rr.cjt import CJTConfig, ConstitutionError, transfer, BiasRef
from cas_rr.domains import DomainDescent, DomainPowerError, DomainPowerState
from cas_rr.foundations import FoundationEngineBank
from cas_rr.learning import LearningController, LearningDisabled
from cas_rr.ontology import CHANNELS, DRIVE_ADAPTER
from cas_rr.runtime import CASRuntime, default_constitution
from tasks.battery import (
    task_contradiction, task_recursive_plan, task_transitive, _plan_constitution,
)


def _run(constitution, problem):
    return CASRuntime(constitution, problem).run()


# --------------------------------------------------------------------------
# Law 2: gain is not truth - evaluation gain is constitution-locked to unity.
# --------------------------------------------------------------------------
def test_eval_gain_must_be_unity():
    with pytest.raises(ConstitutionError):
        replace(default_constitution(), eval_gain=2.0).validate()


def test_eval_cjt_rejects_non_unity_gain():
    with pytest.raises(ConstitutionError):
        CJTConfig(label="x", noetic="^6", domain="C", drive="F2",
                  register="A", role="infer", beta=2.0, cutoff=0.2, sat=0.95,
                  breakdown=1.2, bias=BiasRef("memory_bias", "^5", "C", "F2", "A"))


# --------------------------------------------------------------------------
# Law 1: there is no bias-free CJT.
# --------------------------------------------------------------------------
def test_no_bias_free_cjt():
    with pytest.raises(TypeError):
        CJTConfig(label="x", noetic="^8", domain="C", drive="F2",
                  register="A", role="generate", beta=1.5, cutoff=0.2, sat=0.95,
                  breakdown=1.2)  # bias missing -> TypeError
    cfg = CJTConfig(label="x", noetic="^8", domain="C", drive="F2",
                    register="A", role="generate", beta=1.5, cutoff=0.2,
                    sat=0.95, breakdown=1.2,
                    bias=BiasRef("goal_bias", "^5", "E", "F5", "A"))
    with pytest.raises(ConstitutionError):
        transfer(1.0, -0.5, cfg)  # negative bias is not a substrate


# --------------------------------------------------------------------------
# Law 3: association is not deduction.
# --------------------------------------------------------------------------
def test_association_is_not_deduction():
    packet = _run(default_constitution(), task_transitive())
    # The ^8 generator never marks anything proven; every successful
    # inference carries a rule chain (the ^6+^9 compound).
    generated = packet["candidates"]
    assert all("success" not in c for batch in generated
               for c in batch["candidates"])
    for rec in packet["inferences"].values():
        if rec["success"]:
            assert rec["rules_used"], "successful conclusion without a rule path"


# --------------------------------------------------------------------------
# Law 4: action cannot authorize its own principle.
# --------------------------------------------------------------------------
def test_action_cannot_authorize_principle():
    state = DomainPowerState()
    state.update(True, True, True)
    learning = LearningController()
    descent = DomainDescent(state, learning)
    with pytest.raises(DomainPowerError):
        descent.forbid_feedback()
    with pytest.raises(LearningDisabled):
        learning.request_constitutional()
    with pytest.raises(LearningDisabled):
        learning.request_procedural()


# --------------------------------------------------------------------------
# Law 5: parent totals never replace child probes.
# --------------------------------------------------------------------------
def test_child_probes_retained():
    packet = _run(default_constitution(), task_transitive())
    decomp = packet["decompositions"]
    infer = packet["inferences"]
    assert set(decomp) == {"cand_01", "cand_02"}
    assert set(infer) == {"cand_01", "cand_02"}
    for rec in decomp.values():
        assert rec["probe"] is not None and rec["probe"]["region"] in (
            "cutoff", "active", "saturation", "breakdown")
    for rec in infer.values():
        assert rec["probe"] is not None


# --------------------------------------------------------------------------
# Determinism: same input -> identical execution trace.
# --------------------------------------------------------------------------
def test_determinism():
    a = _run(default_constitution(), task_transitive())
    b = _run(default_constitution(), task_transitive())
    key = lambda p: [(e["tick"], e["phase"], e["kind"]) for e in p["trace"]]
    assert key(a) == key(b)
    assert a["terminal_status"] == b["terminal_status"]
    assert a["output"] == b["output"]


# --------------------------------------------------------------------------
# Candidate invariant: >= 2 hypotheses, or the trace explains why not.
# --------------------------------------------------------------------------
def test_candidate_invariant_documented_for_single_hypothesis():
    packet = _run(default_constitution(), task_contradiction())
    assert packet["candidates"][0]["reason_single"] is not None


# --------------------------------------------------------------------------
# Boot invariant: O_ENABLED only after P, C, E are power-good, in order.
# --------------------------------------------------------------------------
def test_boot_power_sequence():
    packet = _run(default_constitution(), task_transitive())
    phases = [e["payload"]["stage"] for e in packet["trace"]
              if e["kind"] == "POWER"]
    assert phases == ["P_POWERED", "C_POWERED", "E_POWERED", "O_ENABLED"]
    assert packet["domain_power"]["O_ENABLED"] is True


# --------------------------------------------------------------------------
# Stop gates: RESOURCE_EXHAUSTED and LOOP_LIMIT_REACHED.
# --------------------------------------------------------------------------
def test_resource_exhausted():
    constitution = replace(_plan_constitution(), attention_budget=1.5)
    packet = _run(constitution, task_recursive_plan())
    assert packet["terminal_status"] == "RESOURCE_EXHAUSTED"


def test_loop_limit_reached():
    # max_ticks=0: no reasoning cycle is permitted before the rumination
    # stop gate fires.
    constitution = replace(default_constitution(), max_ticks=0)
    packet = _run(constitution, task_transitive())
    assert packet["terminal_status"] == "LOOP_LIMIT_REACHED"


# --------------------------------------------------------------------------
# Foundation bank structure.
# --------------------------------------------------------------------------
def test_28_channels_and_distributions():
    bank = FoundationEngineBank(
        {f"TF{m}": 0.7 for m in range(1, 8)},
        {f"TF{m}": {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
         for m in range(1, 8)},
        {"A_root": 1.0,
         **{f"D{m}": 0.8 for m in range(1, 8)},
         **{f"W{m}": 0.8 for m in range(1, 8)},
         **{f"P{m}": 0.8 for m in range(1, 8)}})
    report = bank.evaluate("probe", {})
    assert len(report.effects) == 28
    assert set(CHANNELS) == {e.channel for e in report.effects}
    for m in range(1, 8):
        total = sum(bank.q[f"TF{m}"].values())
        assert abs(total - 1.0) < 1e-9


def test_drive_adapter_examples():
    assert set(DRIVE_ADAPTER["TF5b"]) == {"F2", "F5", "F6"}
    assert set(DRIVE_ADAPTER["TF6d"]) == {"F3", "F5", "F6"}
    assert set(DRIVE_ADAPTER["TF7b"]) == {"F2", "F7"}


# --------------------------------------------------------------------------
# The four CJT operating regions.
# --------------------------------------------------------------------------
def test_four_operating_regions():
    cfg = CJTConfig(label="r", noetic="^8", domain="C", drive="F2",
                    register="A", role="generate", beta=1.5, cutoff=0.2,
                    sat=0.9, breakdown=1.2,
                    bias=BiasRef("goal_bias", "^5", "E", "F5", "A"))
    assert transfer(1.0, 0.1, cfg).region == "cutoff"
    assert transfer(1.0, 0.4, cfg).region == "active"
    assert transfer(1.0, 0.7, cfg).region == "saturation"
    assert transfer(1.0, 0.9, cfg).region == "breakdown"
