"""test_rc01.py -- RC-0.1 permanent tests (OWNER DIRECTIVE RC-0.1 section 12).

Deterministic, CPU-only, no neural network. Self-runnable and pytest-discoverable.
"""
from __future__ import annotations

import dataclasses
import math
import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
sys.path.insert(0, str(SIM))

import rc0_types as T0            # noqa: E402
import rc01_types as T            # noqa: E402
import rc01_engine as E           # noqa: E402
import rc01_scenarios as SC       # noqa: E402
import rc01_experts as X          # noqa: E402
from rc01_coordinator import HardenedCoordinator, RejectedBatch  # noqa: E402

C6 = ("structure_cue",)


def _engine(causes, gold, **kw):
    return E.RC01Engine(causes, gold, **kw)


def _cause(cid, ev=C6, payload="alpha beta gamma delta"):
    return T.Cause(cause_id=cid, evidence=tuple(ev), payload=payload)


# ---------------------------------------------------------------- CJTStep interface
def test_cjtstep_receives_cause_and_bias():
    b = SC.bias()
    budget = T.ComputeBudget.make(3)
    res = X.cjt_step("^6_decompose", _cause("c0"), b, 1.0, budget, tick=0, bias_version=0)
    assert isinstance(res, T.CJTStepResult)
    assert res.actual_compute_used == 1 and budget.left == 2
    # untyped inputs are refused
    for bad in (("not-a-cause", b), (_cause("c1"), "not-a-bias")):
        try:
            X.cjt_step("^6_decompose", bad[0], bad[1], 1.0, budget, 0, 0)
            raise AssertionError("untyped input accepted")
        except TypeError:
            pass


def test_cjtstep_returns_effect_and_intents():
    res = X.cjt_step("^6_decompose", _cause("c0", payload="a b"), SC.bias(), 1.0,
                     T.ComputeBudget.make(1), 0, 0)
    eff = res.effect_candidate
    assert isinstance(eff, T.EffectCandidate)
    assert eff.op_kind == "decompose" and eff.payload == "parts[a|b]"
    assert isinstance(res.intents, tuple)
    # each expert performs a DISTINCT registered transformation
    outs = {e: X.cjt_step(e, _cause("c1", payload="x y"), SC.bias(), 1.0,
                          T.ComputeBudget.make(1), 0, 0).effect_candidate.payload
            for e in X.EVIDENCE_MARKERS}
    assert len(set(outs.values())) == 4, outs


# ---------------------------------------------------------------- temporal feedback
def test_current_tick_route_independent_of_current_verdict():
    causes = [_cause("t0"), _cause("t1")]
    a = _engine(causes, {("t0", "^6_decompose"): "intended",
                         ("t1", "^6_decompose"): "intended"}).run()
    b = _engine(causes, {("t0", "^6_decompose"): "opposite",
                         ("t1", "^6_decompose"): "intended"}).run()
    # tick 0's allocation is identical although its verdict differs
    assert a["allocations"][0] == b["allocations"][0]
    assert a["publications"][0]["verdict"] != b["publications"][0]["verdict"]


def test_committed_rejection_changes_next_tick_state_or_route():
    causes = [_cause("t0", ("valence_positive",)), _cause("t1", ("valence_positive",))]
    good = _engine(causes, {("t0", "^2_attract"): "intended",
                            ("t1", "^2_attract"): "intended"}).run()
    bad = _engine(causes, {("t0", "^2_attract"): "opposite",
                           ("t1", "^2_attract"): "intended"}).run()
    # the delayed wire: tick 1 differs after a committed rejection at tick 0
    assert good["allocations"][0] == bad["allocations"][0], "same-tick law broken"
    assert good["allocations"][1] != bad["allocations"][1], "rejection did not change next tick"
    assert bad["quarantined"] == ["^2_attract"]


def test_uncommitted_verdict_cannot_change_next_tick():
    causes = [_cause("t0", ("valence_positive",)), _cause("t1", ("valence_positive",))]
    gold_bad = {("t0", "^2_attract"): "opposite", ("t1", "^2_attract"): "intended"}
    committed = _engine(causes, gold_bad, commit_verdicts=True).run()
    uncommitted = _engine(causes, gold_bad, commit_verdicts=False).run()
    neutral = _engine(causes, {("t0", "^2_attract"): "intended",
                               ("t1", "^2_attract"): "intended"},
                      commit_verdicts=False).run()
    # with commitment, the rejection quarantines; without it, nothing changes
    assert committed["quarantined"] == ["^2_attract"]
    assert uncommitted["quarantined"] == []
    assert uncommitted["allocations"][1] == neutral["allocations"][1]


# ---------------------------------------------------------------- publication latch
def test_off_axis_effect_not_published():
    r = _engine([_cause("x0")], {("x0", "^6_decompose"): "off_axis"}).run()
    assert r["metrics"]["published"] == 0 and r["metrics"]["refused"] == 1
    assert r["publications"][0]["status"] == "REFUSED"
    r2 = _engine([_cause("o0")], {("o0", "^6_decompose"): "opposite"}).run()
    assert r2["metrics"]["published"] == 0 and r2["publications"][0]["status"] == "REFUSED"


def test_unassessed_effect_abstains():
    r = _engine([_cause("u0")], {}).run()
    assert r["metrics"]["abstained"] == 1 and r["metrics"]["published"] == 0
    assert r["publications"][0]["status"] == "ABSTAINED"


# ---------------------------------------------------------------- RPM ablation (strict)
def test_no_rpm_strictly_increases_unready_execution_or_forced_publication():
    causes = [_cause(f"r{i}") for i in range(3)]
    gold = {(f"r{i}", "^6_decompose"): "intended" for i in range(3)}
    st = lambda: SC.states(**{"^6_decompose": {"wisdom": 0.0}})  # noqa: E731
    enforced = _engine(causes, gold, states=st(), rpm_enforcement_enabled=True).run()
    ablated = _engine(causes, gold, states=st(), rpm_enforcement_enabled=False).run()
    # latent truth survives the ablation, so the counters can SEE the failure:
    inc_unready = ablated["metrics"]["unready_executions"] > enforced["metrics"]["unready_executions"]
    inc_forced = ablated["metrics"]["forced_publications"] > enforced["metrics"]["forced_publications"]
    assert inc_unready or inc_forced, (
        f"STRICT increase required: unready {enforced['metrics']['unready_executions']}"
        f"->{ablated['metrics']['unready_executions']}, forced "
        f"{enforced['metrics']['forced_publications']}->{ablated['metrics']['forced_publications']}")
    assert ablated["metrics"]["unready_executions"] >= 1


# ---------------------------------------------------------------- action dispatch
def test_each_control_action_has_observable_semantics():
    rows, _ = None, None
    # RUN: executes (normal_intended); CAP: allocation clamped (saturation_cap);
    # SPLIT: children + budget (split_children); REPAIR: subgoal opened (off_axis);
    # QUARANTINE: later routing changes (opposite); HALT: sealed stop (halt_budget).
    by_id = {s["id"]: s for s in SC.SCENARIOS()}
    checks = {
        "normal_intended": lambda r: r["metrics"]["action_run"] >= 1,
        "saturation_cap": lambda r: r["metrics"]["action_cap"] >= 1 and r["metrics"]["cap_events"] >= 1,
        "split_children": lambda r: r["metrics"]["action_split"] >= 1 and r["metrics"]["splits_created"] == 2,
        "off_axis_refused_repair": lambda r: r["metrics"]["action_repair"] >= 1,
        "opposite_refused_quarantined": lambda r: r["metrics"]["action_quarantine"] >= 1,
        "halt_budget": lambda r: r["metrics"]["action_halt"] >= 1,
    }
    for sid, chk in checks.items():
        r = by_id[sid]["build"]().run()
        assert chk(r), f"action semantics not observable in {sid}"


def test_split_creates_children_and_spends_budget():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "split_children")
    eng = sc["build"]()
    total = eng.budget.total
    r = eng.run()
    assert r["metrics"]["splits_created"] == 2
    # budget spent: SPLIT_COST + 2 child executions
    assert total - r["budget_left"] >= E.SPLIT_COST + 2
    split_events = [e for e in r["events"] if e["event"] == "SPLIT"]
    assert split_events and split_events[0]["return_address"] == "sp0"


def test_quarantine_changes_later_routing():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "quarantine_reopen")
    r = sc["build"]().run()
    names = [e["event"] for e in r["events"]]
    assert "QUARANTINE" in names and "ROUTE_UNAVAILABLE_QUARANTINED" in names
    assert "REOPEN" in names
    # after reopen, the expert executed again and published
    assert r["metrics"]["published"] == 1


def test_halt_seals_state_and_trace():
    r = _engine([_cause("h0"), _cause("h1")], {("h0", "^6_decompose"): "intended"},
                budget=1).run()
    assert r["metrics"]["action_halt"] == 1
    assert isinstance(r["trace_digest"], str) and len(r["trace_digest"]) == 64
    halt_events = [e for e in r["events"] if e["event"] == "HALT"]
    assert halt_events and halt_events[0]["why"] in ("budget",)


# ---------------------------------------------------------------- limits + cache
def test_branch_limit_is_distinct_from_depth_limit():
    dep = next(s for s in SC.SCENARIOS() if s["id"] == "depth_limit")["build"]().run()
    act = next(s for s in SC.SCENARIOS() if s["id"] == "active_branch_limit")["build"]().run()
    tot = next(s for s in SC.SCENARIOS() if s["id"] == "total_branch_limit")["build"]().run()
    assert dep["metrics"]["depth_limit_hits"] >= 1 and dep["metrics"]["active_branch_limit_hits"] == 0
    assert act["metrics"]["active_branch_limit_hits"] >= 1 and act["metrics"]["depth_limit_hits"] == 0
    assert tot["metrics"]["total_branch_limit_hits"] >= 1 and tot["metrics"]["depth_limit_hits"] == 0


def test_cached_acquisition_prevents_duplicate_repair():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "cached_acquisition")
    r = sc["build"]().run()
    assert r["metrics"]["cache_hits"] >= 1
    assert r["metrics"]["repairs_completed"] == 1, "duplicate repair ran despite cache"


def test_invalidation_reopens_prerequisite():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "invalidation_reopens")
    r = sc["build"]().run()
    assert r["metrics"]["invalidations_honored"] >= 1
    assert r["metrics"]["repairs_completed"] == 2, "invalidation did not reopen the repair"


# ---------------------------------------------------------------- coordinator
def test_rejected_batch_is_sealed():
    c = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    bad = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "governance",
                            T0.Governance(hard_mask=1), 0, c.get_digest("^6_decompose"))
    try:
        c.commit([bad], 0)
        raise AssertionError("governance write committed")
    except RejectedBatch:
        pass
    sealed = [e for e in c.trace if e["event"] == "REJECTED"]
    assert sealed and sealed[0]["first_failed_law"] == "LAW_GOVERNANCE_OWNER_ONLY"


def test_stale_intent_rejected():
    ids = [r for r in SC.coordinator_scenarios() if r[0] == "stale_intent_rejected"]
    assert ids and ids[0][1] is True, ids


def test_wrong_tick_intent_rejected():
    c = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    it = T.VersionedIntent("ep0", 5, "kernel", "^6_decompose", "memory", ("x",),
                           0, c.get_digest("^6_decompose"))
    try:
        c.commit([it], 0)   # commit tick 0, intent tick 5
        raise AssertionError("wrong-tick intent committed")
    except RejectedBatch as rb:
        assert rb.law == "LAW_TICK_IDENTITY"
    # wrong episode too
    c2 = HardenedCoordinator({"^6_decompose": SC.bias()}, "epA")
    it2 = T.VersionedIntent("epB", 0, "kernel", "^6_decompose", "memory", ("x",),
                            0, c2.get_digest("^6_decompose"))
    try:
        c2.commit([it2], 0)
        raise AssertionError("wrong-episode intent committed")
    except RejectedBatch as rb:
        assert rb.law == "LAW_EPISODE_IDENTITY"


def test_duplicate_conflicting_intents_rejected():
    ids = [r for r in SC.coordinator_scenarios() if r[0] == "duplicate_conflicting_rejected"]
    assert ids and ids[0][1] is True, ids


def test_atomic_rejection_leaves_state_byte_identical():
    ids = [r for r in SC.coordinator_scenarios() if r[0] == "atomic_rollback_byte_identical"]
    assert ids and ids[0][1] is True, ids


def test_verifier_receipt_required_for_publication_consequence():
    c = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "memory", ("x",),
                           0, c.get_digest("^6_decompose"),
                           verifier_receipt_digest="deadbeef-unknown")
    try:
        c.commit([it], 0)
        raise AssertionError("unknown verifier receipt accepted")
    except RejectedBatch as rb:
        assert rb.law == "LAW_VERIFIER_RECEIPT"


# ---------------------------------------------------------------- numeric fail-closed
def test_nan_inf_bool_and_negative_values_rejected():
    for bad in (float("nan"), float("inf"), float("-inf"), -1.0, True, False, "x"):
        try:
            T.require_finite_nonneg("q", bad)
            raise AssertionError(f"accepted {bad!r}")
        except (TypeError, ValueError):
            pass
    # RPMState / Resistance construction rejects them too
    for bad in (float("nan"), -1.0, True):
        try:
            T0.RPMState(desire=bad, wisdom=1.0, power=1.0)
            raise AssertionError(f"RPMState accepted {bad!r}")
        except (TypeError, ValueError):
            pass
        try:
            T0.Resistance(r_cap=bad, r_context=0.0, r_resource=0.0)
            raise AssertionError(f"Resistance accepted {bad!r}")
        except (TypeError, ValueError):
            pass


def test_route_allocations_are_a_valid_simplex():
    # engine-produced allocations always validate
    r = _engine([_cause("v0"), _cause("v1")],
                {("v0", "^6_decompose"): "intended", ("v1", "^6_decompose"): "intended"}).run()
    for alloc in r["allocations"]:
        if alloc:
            T.validate_allocation(alloc)
            assert all(math.isfinite(v) and v >= 0 for v in alloc.values())
    # and the validator itself refuses bad simplexes
    for bad in ({"a": 0.5, "b": 0.6}, {"a": -0.1, "b": 1.1}, {"a": float("nan"), "b": 1.0}):
        try:
            T.validate_allocation(bad)
            raise AssertionError(f"validator accepted {bad}")
        except (TypeError, ValueError):
            pass


# ---------------------------------------------------------------- gold wall
def test_router_cannot_read_gold():
    # (a) the Cause type has no slot for gold and rejects gold-looking evidence
    try:
        T.Cause(cause_id="g0", evidence=("required_op:^6",))
        raise AssertionError("gold marker accepted into Cause evidence")
    except ValueError:
        pass
    # (b) poisoning the gold table after candidate generation cannot change routing:
    causes = [_cause("g1"), _cause("g2")]
    gold_a = {("g1", "^6_decompose"): "intended", ("g2", "^6_decompose"): "intended"}
    gold_b = {("g1", "^6_decompose"): "off_axis", ("g2", "^6_decompose"): "opposite"}
    ra = _engine(causes, gold_a, commit_verdicts=False).run()
    rb = _engine(causes, gold_b, commit_verdicts=False).run()
    assert ra["allocations"] == rb["allocations"], "gold leaked into routing"


def test_changing_cause_evidence_changes_candidates():
    r6 = _engine([_cause("e0", ("structure_cue",))], {}).run()
    r2 = _engine([_cause("e1", ("valence_positive",))], {}).run()
    p6 = [p["producer"] for p in r6["publications"]]
    p2 = [p["producer"] for p in r2["publications"]]
    assert p6 == ["^6_decompose"] and p2 == ["^2_attract"]


# ---------------------------------------------------------------- matrix + replay
def test_scenario_matrix_covers_every_registered_path():
    rows, counts = SC.run_matrix()
    assert all(r["passed"] for r in rows), [r["id"] for r in rows if not r["passed"]]
    required_paths = {"normal_intended", "desire_block", "wisdom_block_repair_return",
                      "power_block_repair", "hard_mask_extreme_V", "all_unavailable",
                      "opposite_refused_quarantined", "off_axis_refused_repair",
                      "unassessed_abstains", "saturation_cap", "split_children",
                      "quarantine_reopen", "halt_budget", "cycle_detected",
                      "depth_limit", "active_branch_limit", "total_branch_limit",
                      "cached_acquisition", "invalidation_reopens",
                      "stale_intent_rejected", "duplicate_conflicting_rejected",
                      "atomic_rollback_byte_identical"}
    assert required_paths <= {r["id"] for r in rows}
    # every outcome class occurred somewhere in the matrix
    for k in ("intended", "opposite", "off_axis", "unassessed",
              "published", "refused", "abstained", "repaired", "quarantined", "halted"):
        assert counts[k] >= 1, f"path class {k} never occurred"


def test_scenario_matrix_replays_digest_identically():
    rows, _ = SC.run_matrix()
    for r in rows:
        if r.get("kind") != "coordinator":
            assert r["replay_identical"], r["id"]


def test_fresh_process_replay_and_mutation_sensitivity():
    entry = str(SIM / "rc01_replay_entry.py")
    def run(args):
        return subprocess.run([sys.executable, entry] + args,
                              capture_output=True, text=True, check=True).stdout.strip()
    d1 = run(["normal_intended"])
    d2 = run(["normal_intended"])
    d3 = run(["normal_intended", "--mutate"])
    assert d1 == d2, "fresh-process replay differs"
    assert d1 != d3, "digest insensitive to a changed input"


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
