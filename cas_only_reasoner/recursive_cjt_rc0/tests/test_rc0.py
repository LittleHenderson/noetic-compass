"""test_rc0.py -- the 17 permanent tests required by OWNER DIRECTIVE RC-0 (section 10).

Deterministic, CPU-only, no neural network, no network access. Self-runnable
(python tests/test_rc0.py) and pytest-discoverable.
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
sys.path.insert(0, str(SIM))
REPO = Path(__file__).resolve().parents[3]

import rc0_types as T          # noqa: E402
import rc0_routing as R        # noqa: E402
import rc0_coordinator as C    # noqa: E402
import rc0_simulator as S      # noqa: E402


def _bias(**kw):
    return S.initial_bias(**kw)


# 1 ---------------------------------------------------------------- RPM vs resistance
def test_01_rpm_state_and_resistance_cannot_be_confused():
    rpm = T.RPMState(desire=2.0, wisdom=2.0, power=2.0)
    res = T.Resistance(r_cap=1.0, r_context=0.0, r_resource=0.0)
    gov = T.Governance(hard_mask=1)
    # passing an RPMState where a Resistance is required raises
    try:
        R.route_score(gov, 1, "active", 1.0, rpm)  # type: ignore[arg-type]
        raise AssertionError("route_score accepted an RPMState as resistance")
    except TypeError:
        pass
    # RPMState refuses arithmetic entirely
    try:
        _ = rpm * 2.0
        raise AssertionError("RPMState entered arithmetic")
    except TypeError:
        pass
    # a Resistance works
    assert R.route_score(gov, 1, "active", 1.0, res) > 0


# 2 ---------------------------------------------------------------- ASOM dimension
def test_02_asom_posterior_dimension_matches_class_set():
    assert len(T.REGIONS) == 4
    T.RegionRecord(region_posterior=(0.1, 0.65, 0.2, 0.05), committed_region="active")
    # a 7-entry posterior (the old conflated status list) is rejected
    try:
        T.RegionRecord(region_posterior=(0.2, 0.2, 0.2, 0.2, 0.1, 0.05, 0.05),
                       committed_region="active")
        raise AssertionError("7-entry posterior accepted")
    except ValueError:
        pass
    # non-region statuses live in their own fields, not the posterior
    rec = T.RegionRecord(region_posterior=(0.25, 0.25, 0.25, 0.25),
                         committed_region="unassessed",
                         response_model_status="non_ohmic", stability_status="unstable")
    assert rec.response_model_status == "non_ohmic" and rec.stability_status == "unstable"


# 3 ---------------------------------------------------------------- actions vs scalars
def test_03_actions_cannot_enter_scalar_route_arithmetic():
    for a in T.ControlAction:
        for op in (lambda: a * 0.5, lambda: 0.5 * a, lambda: a + 1, lambda: 1 - a,
                   lambda: a / 2, lambda: float(a)):
            try:
                op()
                raise AssertionError(f"{a} entered arithmetic")
            except TypeError:
                pass
    # route_multiplier is a plain scalar in [0,1]
    for region in T.REGIONS + ("unassessed",):
        k = R.route_multiplier(region)
        assert isinstance(k, float) and 0.0 <= k <= 1.0


# 4 ---------------------------------------------------------------- all-zero routes
def test_04_all_zero_routes_return_no_ready_cjt():
    try:
        R.normalize_scores({"a": 0.0, "b": 0.0})
        raise AssertionError("normalized an all-zero score set")
    except T.NoReadyCJT as e:
        assert e.code == "NO_READY_CJT"
    # kernel level: all experts masked -> NO_READY_CJT event, no crash, no divide-by-zero
    states = S.default_states({e: {"mask": 0} for e in S.EXPERTS})
    kernel = S.RC0Kernel(S.default_tasks()[:2], states=states)
    out = kernel.run()
    assert out["metrics"]["no_ready_events"] >= 1


# 5 ---------------------------------------------------------------- mask beats V
def test_05_policy_mask_cannot_be_overridden_by_large_V():
    gov0 = T.Governance(hard_mask=0)
    res = T.Resistance(r_cap=1e-6, r_context=0.0, r_resource=0.0)
    assert R.route_score(gov0, 1, "active", 1e12, res) == 0.0
    # and quarantine zeroes the effective mask too
    govq = T.Governance(hard_mask=1, quarantined=True)
    assert R.route_score(govq, 1, "active", 1e12, res) == 0.0
    # mask must be exactly 0/1 -- a "soft mask" is rejected at construction
    try:
        T.Governance(hard_mask=0.5)  # type: ignore[arg-type]
        raise AssertionError("soft mask accepted")
    except ValueError:
        pass


# 6 ---------------------------------------------------------------- verdict != route
def test_06_same_tick_route_independent_of_current_verdict():
    """AMENDED per OWNER DIRECTIVE RC-0.1 item 3: the original assertion (the ENTIRE
    multi-tick allocation sequence identical under flipped verdicts) enforced a SEVERED
    feedback wire. The correct law is same-tick independence only; the delayed
    next-tick feedback wire is implemented and tested in the RC-0.1 engine
    (tests/test_rc01.py::test_committed_rejection_changes_next_tick_state_or_route).
    The RC-0 shell has no feedback wire at all, so this narrowed check is all it can
    honestly demonstrate."""
    tasks = S.default_tasks()
    base_table = S.build_outcome_table(tasks)
    flipped = dict(base_table)
    for key in list(flipped.keys())[:20]:      # flip many outcomes
        flipped[key] = "opposite" if flipped[key] != "opposite" else "off_axis"
    out_a = S.RC0Kernel(tasks, outcome_table=base_table).run()
    out_b = S.RC0Kernel(tasks, outcome_table=flipped).run()
    # SAME-TICK law only: tick 0's allocation (produced before any verdict existed)
    # is identical; later ticks are NOT asserted (a feedback-closed engine may differ)
    assert out_a["allocations"][0] == out_b["allocations"][0]
    verdicts_a = [e["outcome"] for e in out_a["events"] if e["event"] == "EXECUTED"]
    verdicts_b = [e["outcome"] for e in out_b["events"] if e["event"] == "EXECUTED"]
    assert verdicts_a != verdicts_b, "test setup failed to change any verdict"


# 7 ---------------------------------------------------------------- coordinator only
def test_07_bias_updates_cannot_bypass_the_transaction_coordinator():
    b = _bias()
    try:
        b.rpm = T.RPMState(desire=9.0, wisdom=9.0, power=9.0)  # type: ignore[misc]
        raise AssertionError("BiasState mutated directly")
    except dataclasses.FrozenInstanceError:
        pass
    coord = C.TransactionCoordinator({"^6_decompose": b})
    # governance is owner-only: an intent touching it is rejected
    bad = T.BiasUpdateIntent("^6_decompose", "governance",
                             T.Governance(hard_mask=1), "sneak", 0)
    try:
        coord.commit([bad], 0)
        raise AssertionError("governance intent committed")
    except ValueError:
        pass
    # atomicity: one bad intent in a batch rejects the WHOLE batch
    good = T.BiasUpdateIntent("^6_decompose", "rpm",
                              T.RPMState(desire=3.0, wisdom=3.0, power=3.0), "ok", 0)
    try:
        coord.commit([good, bad], 0)
        raise AssertionError("batch with a bad intent committed")
    except ValueError:
        pass
    assert coord.get("^6_decompose").rpm.desire == 2.0, "rollback failed: good intent leaked"
    coord.commit([good], 0)
    assert coord.get("^6_decompose").rpm.desire == 3.0


# 8 ---------------------------------------------------------------- D/W/P source table
def test_08_dwp_source_records_are_complete():
    import json
    schema = json.loads((Path(__file__).resolve().parent.parent /
                         "RECURSIVE_CJT_STATE_SCHEMA_v0_1.json").read_text(encoding="utf-8"))
    contract = schema["measurement_contract"]
    required_quantities = {"D", "W", "P", "V", "r_cap", "r_context", "r_resource",
                           "hard_policy_mask"}
    assert required_quantities <= set(contract.keys()), "missing quantities"
    for q, rec in contract.items():
        for fld in ("source", "scale", "units", "kind", "used_in"):
            assert fld in rec, f"{q} missing {fld}"
        assert rec["kind"] in ("observed", "derived", "declared")
        assert set(rec["used_in"]) <= {"readiness", "routing", "diagnosis"}
    # non-duplication: Wisdom is readiness-only; policy is mask-only (not routing resistance)
    assert contract["W"]["used_in"] == ["readiness"]
    assert contract["hard_policy_mask"]["used_in"] == ["routing"] and \
        contract["hard_policy_mask"]["kind"] == "declared"
    # registered dual roles are explicit
    assert contract["D"].get("dual_role_registered") is True
    assert contract["P"].get("dual_role_registered") is True


# 9 ---------------------------------------------------------------- depth/branch halt
def test_09_recursion_depth_and_branch_limits_halt_correctly():
    tasks = [{"id": "t00", "required_op": "^6_decompose"}]
    # chain longer than max_depth: W needs P needs D needs W-of-other ... build depth 6
    chain = {("^6_decompose", "WISDOM"): ("^8_trigger", "WISDOM"),
             ("^8_trigger", "WISDOM"): ("^2_attract", "WISDOM"),
             ("^2_attract", "WISDOM"): ("^3_averse", "WISDOM"),
             ("^3_averse", "WISDOM"): ("^3_averse", "POWER"),
             ("^3_averse", "POWER"): ("^3_averse", "DESIRE"),
             ("^3_averse", "DESIRE"): ("^2_attract", "POWER")}
    states = S.default_states({"^6_decompose": {"wisdom": 0.0}})
    kernel = S.RC0Kernel(tasks, states=states, repair_requires=chain)
    out = kernel.run()
    assert out["metrics"]["depth_limit_hits"] >= 1
    assert kernel.active_subgoal_stack == [], "return addresses not unwound"


# 10 --------------------------------------------------------------- cycle detection
def test_10_cycle_detection_identifies_a_repeated_typed_subgoal():
    tasks = [{"id": "t00", "required_op": "^6_decompose"}]
    cyc = {("^6_decompose", "WISDOM"): ("^8_trigger", "POWER"),
           ("^8_trigger", "POWER"): ("^6_decompose", "WISDOM")}   # a typed cycle
    states = S.default_states({"^6_decompose": {"wisdom": 0.0}})
    kernel = S.RC0Kernel(tasks, states=states, repair_requires=cyc)
    out = kernel.run()
    assert out["metrics"]["cycle_detected"] >= 1
    assert kernel.active_subgoal_stack == []


# 11 --------------------------------------------------------------- parent vs child
def test_11_healthy_parent_aggregate_cannot_hide_a_failed_child():
    kernel = S.RC0Kernel(S.default_tasks()[:1])
    # force one child into cutoff via the coordinator (legal path)
    rec = T.RegionRecord(region_posterior=S.CUTOFF4, committed_region="cutoff")
    kernel.coord.commit([T.BiasUpdateIntent("^3_averse", "record", rec, "starve", 0)], 0)
    rep = kernel.board_report("evaluation_board", ["^2_attract", "^3_averse"])
    assert "^3_averse:STARVED" in rep["flags"], "starved child hidden"
    assert "children" in rep and "^3_averse" in rep["children"]
    assert rep["parent_health"] > 0, "parent looks healthy overall -- child still flagged"


# 12 --------------------------------------------------------------- RPM ablation
def test_12_rpm_ablation_collapses_typed_abstentions_shell_scope_only():
    """AMENDED per OWNER DIRECTIVE RC-0.1 item 4. WHAT THIS TEST PROVES: disabling RPM
    in the RC-0 shell collapses typed abstentions to zero. WHAT IT CANNOT PROVE: a
    strict increase in forced answers -- the shell's ablation forces readiness to 1,
    and its forced-answer counter fires only on readiness 0, so that metric is
    structurally blind here (the trap the owner identified). The STRICT causal
    signature (latent readiness kept as truth; unready executions / forced
    publications strictly increase under ablation) is implemented and enforced in
    tests/test_rc01.py::test_no_rpm_strictly_increases_unready_execution_or_forced_publication."""
    states = lambda: S.default_states({"^6_decompose": {"wisdom": 0.0}})  # noqa: E731
    tasks = [{"id": f"t{i:02d}", "required_op": "^6_decompose"} for i in range(6)]
    with_rpm = S.RC0Kernel(tasks, states=states(), enable_rpm=True).run()
    no_rpm = S.RC0Kernel(tasks, states=states(), enable_rpm=False).run()
    assert with_rpm["metrics"]["typed_abstentions"] >= 1
    assert no_rpm["metrics"]["typed_abstentions"] == 0
    blocks = [e for e in with_rpm["events"] if e["event"] == "TYPED_ABSTENTION"]
    assert blocks and all(e["FIRST_BLOCK"] in T.FIRST_BLOCK_POLICY for e in blocks)


# 13 --------------------------------------------------------------- ASOM ablation
def test_13_removing_asom_produces_the_saturation_signature():
    tasks = [{"id": f"t{i:02d}", "required_op": "^8_trigger"} for i in range(10)]
    with_asom = S.RC0Kernel(tasks, enable_asom=True).run()
    no_asom = S.RC0Kernel(tasks, enable_asom=False).run()
    assert no_asom["metrics"]["saturation_events"] > with_asom["metrics"]["saturation_events"]


# 14 --------------------------------------------------------------- Ohm ablation
def test_14_removing_cas_ohm_changes_allocation_but_not_verifier_truth():
    # give experts DIFFERENT desire surpluses so V/r routing differs from uniform
    states = lambda: S.default_states({"^6_decompose": {"desire": 5.0},   # noqa: E731
                                       "^8_trigger": {"desire": 3.0}})
    tasks = S.default_tasks()
    with_ohm = S.RC0Kernel(tasks, states=states(), enable_ohm=True).run()
    no_ohm = S.RC0Kernel(tasks, states=states(), enable_ohm=False).run()
    assert with_ohm["allocations"] != no_ohm["allocations"], "ablation changed nothing"
    # verifier truth is the same registered pure table in both runs: for every
    # (task, expert) pair the verdict function returns the identical registered value
    table = S.build_outcome_table(tasks)
    for task in tasks:
        for expert in S.EXPERTS:
            assert S.verify(table, task["id"], expert) == table[(task["id"], expert)]
    # and every executed verdict in both runs came from that same table
    for run in (with_ohm, no_ohm):
        executed = [e for e in run["events"] if e["event"] == "EXECUTED"]
        assert executed, "no executions in run"
        for e, task in zip(executed, tasks):  # ticks align 1:1 with tasks here
            assert e["outcome"] == table[(task["id"], e["expert"])]


# 15 --------------------------------------------------------------- matched budgets
def test_15_controller_configuration_slot_count_matches():
    """SIMULATOR_CONFIG_COUNT_MATCH only (renamed per OWNER DIRECTIVE RC-0.1 item 10):
    the two config dictionaries have the same number of scalar slots. This is NOT a
    neural parameter-count match. No matched neural parameter claim is permitted until
    actual neural modules exist and trainable parameters / optimizer state / FLOPs /
    memory are measured directly (see STATIC_CONDITIONS_v2.yaml compute contract)."""
    cas = S.cas_controller_config()
    gen = S.generic_controller_config()
    assert len(cas) == len(gen), (len(cas), len(gen))
    assert all(isinstance(v, float) for v in list(cas.values()) + list(gen.values()))


# 16 --------------------------------------------------------------- replay
def test_16_replay_is_digest_identical():
    _, a = S.run_default()
    _, b = S.run_default()
    assert a["trace_digest"] == b["trace_digest"]
    assert a["metrics"] == b["metrics"] and a["allocations"] == b["allocations"]


# 17 --------------------------------------------------------------- artifact identity
def test_17_repository_file_matches_the_reported_commit_artifact():
    path = "docs/research/RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md"
    blob_at_commit = subprocess.run(
        ["git", "rev-parse", f"7bf2a3b9:{path}"], cwd=REPO,
        capture_output=True, text=True, check=True).stdout.strip()
    blob_at_head = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"], cwd=REPO,
        capture_output=True, text=True, check=True).stdout.strip()
    assert blob_at_commit == blob_at_head, "v0_1 drifted from the reported commit"
    clean = subprocess.run(["git", "diff", "HEAD", "--quiet", "--", path], cwd=REPO)
    assert clean.returncode == 0, "working tree v0_1 differs from HEAD"


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
