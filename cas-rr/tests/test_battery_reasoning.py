"""The native-reasoning battery: six tasks, seven halt states."""

from cas_rr.runtime import CASRuntime, default_constitution
from tasks.battery import (
    A,
    task_constraint, task_contradiction, task_fault,
    task_fault_missing_reading, task_inadmissible, task_memory,
    task_missing_info, task_needs_capability, task_recursive_plan,
    task_transitive, task_transitive_negative,
    _plan_constitution,
)


def _find_inference(packet, conclusion):
    for rec in packet["inferences"].values():
        if rec["conclusion"] == conclusion:
            return rec
    return None


# --------------------------------------------------------------------------
# 1. Transitive inference
# --------------------------------------------------------------------------
def test_transitive_concludes_with_provenance():
    packet = CASRuntime(default_constitution(), task_transitive()).run()
    assert packet["terminal_status"] == "CONCLUDED"
    assert packet["output"]["conclusion"] == "precedes(a,c)"
    rec = _find_inference(packet, "precedes(a,c)")
    assert rec is not None and rec["success"] is True
    assert rec["rules_used"] == ["r_trans"]
    assert "precedes(a,b)" in rec["premises_used"]
    assert "precedes(b,c)" in rec["premises_used"]
    # The losing alternative was eliminated, not ignored.
    assert any("precedes(c,a)" in str(r.get("divergence"))
               for r in packet["comparisons"][-1]["reports"])


def test_transitive_negative_halts_needs_information():
    packet = CASRuntime(default_constitution(), task_transitive_negative()).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"
    assert packet["output"] is None
    # RPM converted the block into a knowledge subgoal, which could not resolve.
    events = packet["rpm"]["subgoal_events"]
    assert any(e["event"] == "SUBGOAL_CREATED" and e["subgoal_type"] == "KNOWLEDGE"
               for e in events)


# --------------------------------------------------------------------------
# 2. Constraint satisfaction
# --------------------------------------------------------------------------
def test_constraint_satisfaction_picks_viable_plan():
    packet = CASRuntime(default_constitution(), task_constraint()).run()
    assert packet["terminal_status"] == "CONCLUDED"
    assert packet["output"]["conclusion"] == "viable(P1)"
    assert _find_inference(packet, "viable(P2)")["contradiction_status"] == "FALSIFIED"
    assert _find_inference(packet, "viable(P3)")["contradiction_status"] == "FALSIFIED"
    tour = packet["comparisons"][-1]
    assert "cand_02" in tour["eliminated"] and "cand_03" in tour["eliminated"]


def test_inadmissible_when_plans_violate_charter():
    packet = CASRuntime(default_constitution(), task_inadmissible()).run()
    assert packet["terminal_status"] == "INADMISSIBLE"
    gates = packet["commitment"]["gates"]
    principled = next(g for g in gates if g["gate"] == "PRINCIPLED_CONSTRAINTS")
    assert principled["passed"] is False


# --------------------------------------------------------------------------
# 3. Fault diagnosis via test-point walk-down
# --------------------------------------------------------------------------
def test_fault_localizes_first_bad_stage():
    packet = CASRuntime(default_constitution(), task_fault()).run()
    assert packet["terminal_status"] == "CONCLUDED"
    assert packet["output"]["conclusion"] == "first_bad(S3)"
    # The walk-down is visible: S4's decomposition lacks good(tp3).
    found = any(
        "good(tp3)" in rec.get("premises_missing", [])
        for rec in packet["decompositions"].values()
    )
    assert found
    # Exactly one stage is provable.
    proven = [r["conclusion"] for r in packet["inferences"].values() if r["success"]]
    assert proven == ["first_bad(S3)"]


def test_fault_missing_reading_halts_needs_information():
    packet = CASRuntime(default_constitution(), task_fault_missing_reading()).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"


# --------------------------------------------------------------------------
# 4. Missing-information reasoning
# --------------------------------------------------------------------------
def test_missing_info_reports_lacunae_not_invention():
    packet = CASRuntime(default_constitution(), task_missing_info()).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"
    kinds = []
    for mem in packet["memory"]:
        for lacuna in mem["lacunae"]:
            kinds.append((lacuna["query"], lacuna["kind"]))
    assert ("is(b,y)", "KNOWLEDGE_MISSING") in kinds
    assert ("has(b,y)", "EXPERIENCE_MISSING") in kinds


# --------------------------------------------------------------------------
# 5. Recursive planning
# --------------------------------------------------------------------------
def test_recursive_planning_descends_and_ascends():
    packet = CASRuntime(_plan_constitution(), task_recursive_plan()).run()
    assert packet["terminal_status"] == "CONCLUDED"
    assert packet["output"]["conclusion"] == "executable(P_launch)"
    created = [e for e in packet["rpm"]["subgoal_events"]
               if e["event"] == "SUBGOAL_CREATED"]
    resolved = [e for e in packet["rpm"]["subgoal_events"]
                if e["event"] == "SUBGOAL_RESOLVED"]
    assert [e["subgoal_type"] for e in created] == ["KNOWLEDGE", "CAPABILITY"]
    assert [e["action"] for e in resolved] == ["market_research", "restructure_resources"]
    # The parent was re-measured from scratch after each resolution
    # (section-retraction: no assumed reversibility).
    parent_scans = [s for s in packet["rpm"]["scan_history"]
                    if s["goal_id"] == "g_launch"]
    assert len(parent_scans) >= 3
    assert any(s["cached"] for s in parent_scans)
    assert any(not s["cached"] for s in parent_scans)
    # P_defer lost: the goal-channel profile preferred the launch plan.
    assert "cand_02" in packet["comparisons"][-1]["eliminated"] or any(
        "P_defer" in str(r["divergence"]) for r in packet["comparisons"][-1]["reports"])


def test_needs_capability_halts_correctly():
    packet = CASRuntime(_plan_constitution(), task_needs_capability()).run()
    assert packet["terminal_status"] == "NEEDS_CAPABILITY"


# --------------------------------------------------------------------------
# 6. Memory-dependent reasoning
# --------------------------------------------------------------------------
def test_memory_dependent_reasoning():
    problem = task_memory()
    constitution = default_constitution()

    run1 = CASRuntime(constitution, problem).run()
    assert run1["terminal_status"] == "NEEDS_INFORMATION"

    # Same constitution, same problem; only a verified memory was added.
    rt2 = CASRuntime(constitution, problem)
    rt2.cmb.store_atom(A("has", "b", "y"), "^5", "C", "semantic",
                       "verified_memory_episode_1")
    run2 = rt2.run()
    assert run2["terminal_status"] == "CONCLUDED"
    assert run2["output"]["conclusion"] == "is(b,y)"
    rec = _find_inference(run2, "is(b,y)")
    assert rec["success"] is True and "has(b,y)" in rec["premises_used"]
    # The changed memory is visible in the provenance.
    sources = []
    for mem in run2["memory"]:
        for item in mem["selected_items"]:
            sources.append((item["content"], item["source"]))
    assert ("has(b,y)", "verified_memory_episode_1") in sources


# --------------------------------------------------------------------------
# 7. Contradiction surface
# --------------------------------------------------------------------------
def test_contradiction_surfaces_as_conflict():
    packet = CASRuntime(default_constitution(), task_contradiction()).run()
    assert packet["terminal_status"] == "CONFLICT_UNRESOLVED"
    assert _find_inference(packet, "viable(P1)")["contradiction_status"] == "CONTRADICTED"
