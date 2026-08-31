"""rc01_scenarios.py -- the RC-0.1 integrated adversarial scenario matrix and runner.

Every registered control path is exercised by at least one scenario, each declaring
initial state, input Cause evidence, budget, expected events, prohibited events,
expected publication behavior, and digest behavior. The runner executes the matrix,
validates every expectation, computes verifier-side selection metrics (the engine
cannot -- gold lives behind the wall), and writes RC01_SCENARIO_MATRIX.json +
RC01_FEEDBACK_CLOSURE_RECEIPT.json.

A Gate 0 receipt with zero executions of the registered failure paths does not close
Gate 0 -- this matrix is the closure. Deterministic, CPU-only.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rc0_types import BiasState, Governance, RegionRecord, RPMState  # noqa: E402
from rc0_simulator import initial_bias, default_states  # noqa: E402
import rc01_engine as E  # noqa: E402
from rc01_types import Cause, digest  # noqa: E402


def bias(desire=2.0, wisdom=2.0, power=2.0, mask=1, region="unassessed",
         posterior=None, max_branches=8, max_depth=4):
    post = posterior or {"unassessed": E.UNIFORM4, "saturation": E.SATUR4,
                         "active": E.ACTIVE4, "cutoff": E.CUTOFF4,
                         "breakdown": E.BREAK4}[region]
    return BiasState(
        substrate=("declared",), memory=(),
        rpm=RPMState(desire=desire, wisdom=wisdom, power=power),
        record=RegionRecord(region_posterior=post, committed_region=region),
        theta=("K_identity",),
        governance=Governance(hard_mask=mask, max_branches=max_branches, max_depth=max_depth))


def states(**over):
    base = {e: bias() for e in E.EVIDENCE_MARKERS}
    for eid, kw in over.items():
        base[eid] = bias(**kw)
    return base


C6 = ("structure_cue",)          # only ^6_decompose is a candidate
C2 = ("valence_positive",)       # only ^2_attract
C8 = ("association_cue",)        # only ^8_trigger


def cause(cid, ev, payload="alpha beta gamma delta"):
    return Cause(cause_id=cid, evidence=tuple(ev), payload=payload)


def gold(*entries):
    return {(cid, exp): verdict for cid, exp, verdict in entries}


# ---------------------------------------------------------------- scenario registry
# Each: id, build() -> RC01Engine (or callable for coordinator scenarios),
# expect (event names that MUST appear), prohibit (must NOT appear), checks(result).
def _s(id_, build, expect, prohibit=(), checks=None, kind="engine", description=""):
    return {"id": id_, "build": build, "expect": tuple(expect),
            "prohibit": tuple(prohibit), "checks": checks, "kind": kind,
            "description": description}


def SCENARIOS():
    S = []
    S.append(_s("normal_intended",
        lambda: E.RC01Engine([cause("n0", C6)], gold(("n0", "^6_decompose", "intended"))),
        expect=["EXECUTED"], prohibit=["NO_READY_CJT", "HALT", "QUARANTINE"],
        checks=lambda r: r["metrics"]["published"] == 1 and r["metrics"]["intended_effects"] == 1
                         and r["publications"][0]["producer"] == "^6_decompose",
        description="Relevant CJT selected from evidence; intended Effect published."))
    S.append(_s("desire_block",
        lambda: E.RC01Engine([cause("d0", C6)], {}, states=states(**{"^6_decompose": {"desire": 0.0}})),
        expect=["TYPED_ABSTENTION", "NO_READY_CJT", "DESIRE_DEPRIORITIZED"],
        prohibit=["REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["desire_deprioritized"] == 1
                         and r["metrics"]["repairs_opened"] == 0,
        description="Desire block deprioritizes; the kernel never invents relevance."))
    S.append(_s("wisdom_block_repair_return",
        lambda: E.RC01Engine([cause("w0", C6)], gold(("w0", "^6_decompose", "intended")),
                             states=states(**{"^6_decompose": {"wisdom": 0.0}})),
        expect=["TYPED_ABSTENTION", "NO_READY_CJT", "REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["repairs_completed"] == 1
                         and r["metrics"]["published"] == 1,
        description="FIRST_BLOCK=WISDOM; repair opens, completes, cause retried, intended Effect."))
    S.append(_s("power_block_repair",
        lambda: E.RC01Engine([cause("p0", C6)], gold(("p0", "^6_decompose", "intended")),
                             states=states(**{"^6_decompose": {"power": 0.0}})),
        expect=["NO_READY_CJT", "REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["repairs_completed"] == 1,
        description="Power block -> capacity repair -> return."))
    S.append(_s("hard_mask_extreme_V",
        lambda: E.RC01Engine([cause("m0", C6)], {},
                             states=states(**{"^6_decompose": {"mask": 0, "desire": 1e12}})),
        expect=["NO_READY_CJT", "HALT"], prohibit=["EXECUTED"],
        checks=lambda r: r["metrics"]["executions"] == 0,
        description="Hard mask stays exactly zero under extreme Drive."))
    S.append(_s("all_unavailable",
        lambda: E.RC01Engine([cause("u0", C6)], {},
                             states={e: bias(mask=0) for e in E.EVIDENCE_MARKERS}),
        expect=["NO_READY_CJT", "HALT"], prohibit=["EXECUTED"],
        checks=lambda r: r["metrics"]["no_ready_events"] == 1,
        description="All CJTs unavailable -> NO_READY_CJT -> typed halt."))
    S.append(_s("opposite_refused_quarantined",
        lambda: E.RC01Engine([cause("o0", C2), cause("o1", C2)],
                             gold(("o0", "^2_attract", "opposite"), ("o1", "^2_attract", "intended"))),
        expect=["QUARANTINE", "NO_READY_CJT"],
        checks=lambda r: r["metrics"]["refused"] == 1 and r["metrics"]["published"] == 0
                         and r["quarantined"] == ["^2_attract"]
                         and r["metrics"]["opposite_effects"] == 1,
        description="Opposite Effect: publication REFUSED; producer quarantined; NEXT tick route changes."))
    S.append(_s("off_axis_refused_repair",
        lambda: E.RC01Engine([cause("x0", C6)], gold(("x0", "^6_decompose", "off_axis"))),
        expect=["EXECUTED", "REPAIR_DONE"],
        checks=lambda r: r["metrics"]["refused"] == 1 and r["metrics"]["published"] == 0
                         and r["metrics"]["off_axis_effects"] == 1
                         and r["metrics"]["repairs_completed"] == 1,
        description="Off-axis Effect: publication REFUSED; typed WISDOM repair opens."))
    S.append(_s("unassessed_abstains",
        lambda: E.RC01Engine([cause("q0", C8)], {}),
        expect=["EXECUTED"],
        checks=lambda r: r["metrics"]["abstained"] == 1 and r["metrics"]["published"] == 0
                         and r["metrics"]["unassessed_effects"] == 1,
        description="Unassessed Effect -> typed abstention; publication refused."))
    S.append(_s("saturation_cap",
        lambda: E.RC01Engine([cause(f"s{i}", C6) for i in range(5)],
                             {(f"s{i}", "^6_decompose"): "intended" for i in range(5)}),
        expect=["CAP_ENFORCED"],
        checks=lambda r: r["metrics"]["cap_events"] >= 1 and r["metrics"]["action_cap"] >= 1,
        description="Saturation: CAP is actually enforced on the allocation."))
    S.append(_s("split_children",
        lambda: E.RC01Engine([cause("sp0", ("structure_cue", "overload_cue"),
                                    payload="a b c d e f")],
                             {("sp0.c0", "^6_decompose"): "intended",
                              ("sp0.c1", "^6_decompose"): "intended"},
                             states=states(**{"^6_decompose": {"region": "saturation"}})),
        expect=["SPLIT", "EXECUTED"],
        checks=lambda r: r["metrics"]["splits_created"] == 2
                         and r["metrics"]["action_split"] == 1
                         and r["metrics"]["published"] == 2,
        description="SPLIT creates bounded typed child work with a return address and spends budget."))
    S.append(_s("quarantine_reopen",
        lambda: E.RC01Engine([cause("qr0", C2), cause("qr1", C2), cause("qr2", C2)],
                             gold(("qr0", "^2_attract", "opposite"),
                                  ("qr2", "^2_attract", "intended")),
                             reopen_events={2: "^2_attract"}),
        expect=["QUARANTINE", "ROUTE_UNAVAILABLE_QUARANTINED", "REOPEN"],
        checks=lambda r: r["metrics"]["reopens"] == 1 and r["metrics"]["published"] == 1,
        description="Quarantine excludes the expert until an authorized reopen event."))
    S.append(_s("halt_budget",
        lambda: E.RC01Engine([cause("h0", C6), cause("h1", C6)],
                             gold(("h0", "^6_decompose", "intended")), budget=1),
        expect=["HALT"],
        checks=lambda r: r["metrics"]["action_halt"] == 1 and r["trace_digest"] is not None,
        description="Budget exhaustion -> HALT with state and trace sealed."))
    S.append(_s("cycle_detected",
        lambda: E.RC01Engine([cause("cy0", C6)], {},
                             states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                             repair_requires={("^6_decompose", "WISDOM"): ("^8_trigger", "POWER"),
                                              ("^8_trigger", "POWER"): ("^6_decompose", "WISDOM")}),
        expect=["CYCLE_DETECTED"],
        checks=lambda r: r["metrics"]["cycle_detected"] >= 1,
        description="Typed prerequisite cycle detected; stack unwound."))
    S.append(_s("depth_limit",
        lambda: E.RC01Engine([cause("dp0", C6)], {},
                             states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                             repair_requires={("^6_decompose", "WISDOM"): ("^8_trigger", "WISDOM"),
                                              ("^8_trigger", "WISDOM"): ("^2_attract", "WISDOM"),
                                              ("^2_attract", "WISDOM"): ("^3_averse", "WISDOM"),
                                              ("^3_averse", "WISDOM"): ("^3_averse", "POWER"),
                                              ("^3_averse", "POWER"): ("^2_attract", "POWER"),
                                              ("^2_attract", "POWER"): ("^8_trigger", "DESIRE")}),
        expect=["DEPTH_LIMIT"],
        checks=lambda r: r["metrics"]["depth_limit_hits"] >= 1,
        description="Prerequisite chain beyond max_depth halts with DEPTH_LIMIT."))
    S.append(_s("active_branch_limit",
        lambda: E.RC01Engine([cause("ab0", C6)], {},
                             states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                             max_active_branches=1,
                             repair_requires={("^6_decompose", "WISDOM"): ("^8_trigger", "POWER")}),
        expect=["ACTIVE_BRANCH_LIMIT"],
        checks=lambda r: r["metrics"]["active_branch_limit_hits"] >= 1,
        description="Active-branch ceiling fires distinctly from the depth limit."))
    S.append(_s("total_branch_limit",
        lambda: E.RC01Engine([cause("tb0", C6)], {},
                             states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                             max_total_branches=0),
        expect=["TOTAL_BRANCH_LIMIT"],
        checks=lambda r: r["metrics"]["total_branch_limit_hits"] >= 1,
        description="Lifetime branch ceiling fires distinctly from the active ceiling."))
    S.append(_s("cached_acquisition",
        lambda: E.RC01Engine([cause("ca0", C6), cause("ca1", C6)],
                             gold(("ca0", "^6_decompose", "off_axis"),
                                  ("ca1", "^6_decompose", "off_axis"))),
        expect=["REPAIR_DONE", "CACHE_HIT"],
        checks=lambda r: r["metrics"]["cache_hits"] >= 1
                         and r["metrics"]["repairs_completed"] == 1,
        description="A cached acquisition prevents a duplicate repair."))
    S.append(_s("invalidation_reopens",
        lambda: E.RC01Engine([cause("iv0", C6), cause("iv1", C6)],
                             gold(("iv0", "^6_decompose", "off_axis"),
                                  ("iv1", "^6_decompose", "off_axis")),
                             invalidation_events={("^6_decompose", "WISDOM")}),
        expect=["REPAIR_DONE", "INVALIDATION_REOPEN"],
        checks=lambda r: r["metrics"]["invalidations_honored"] >= 1
                         and r["metrics"]["repairs_completed"] == 2,
        description="An explicit invalidation event reopens a cached prerequisite."))
    return S


# ------------------------------------------------------- coordinator-level scenarios
def coordinator_scenarios():
    """stale intent / duplicate conflicting intent / atomic rollback, run directly
    against the hardened coordinator. Returns list of (id, passed, detail)."""
    from rc01_coordinator import HardenedCoordinator, RejectedBatch, state_digest
    from rc01_types import VersionedIntent
    results = []

    def fresh():
        return HardenedCoordinator({"^6_decompose": bias()}, "ep0")

    # stale intent
    c = fresh()
    ok_rpm = RPMState(desire=3.0, wisdom=3.0, power=3.0)
    good = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm", ok_rpm,
                           c.version("^6_decompose"), c.get_digest("^6_decompose"))
    c.commit([good], 0)  # bumps version to 1
    stale = VersionedIntent("ep0", 1, "kernel", "^6_decompose", "rpm", ok_rpm,
                            0, "old-digest")  # base version 0 is now stale
    try:
        c.commit([stale], 1)
        results.append(("stale_intent_rejected", False, "stale intent committed"))
    except RejectedBatch as rb:
        results.append(("stale_intent_rejected", rb.law == "LAW_STALE_VERSION", rb.law))

    # duplicate conflicting intents in one batch
    c = fresh()
    a = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm",
                        RPMState(desire=3.0, wisdom=3.0, power=3.0),
                        c.version("^6_decompose"), c.get_digest("^6_decompose"))
    b = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm",
                        RPMState(desire=4.0, wisdom=4.0, power=4.0),
                        c.version("^6_decompose"), c.get_digest("^6_decompose"))
    try:
        c.commit([a, b], 0)
        results.append(("duplicate_conflicting_rejected", False, "conflict committed"))
    except RejectedBatch as rb:
        results.append(("duplicate_conflicting_rejected",
                        rb.law == "LAW_NO_CONFLICTING_WRITES", rb.law))

    # atomic rollback leaves state byte-identical + rejection sealed
    c = fresh()
    before = c.get_digest("^6_decompose")
    good = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm", ok_rpm,
                           c.version("^6_decompose"), c.get_digest("^6_decompose"))
    bad = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "governance",
                          Governance(hard_mask=1), c.version("^6_decompose"),
                          c.get_digest("^6_decompose"))
    try:
        c.commit([good, bad], 0)
        results.append(("atomic_rollback_byte_identical", False, "bad batch committed"))
    except RejectedBatch:
        sealed = any(e["event"] == "REJECTED" and "first_failed_law" in e for e in c.trace)
        results.append(("atomic_rollback_byte_identical",
                        c.get_digest("^6_decompose") == before and sealed,
                        "state unchanged + rejection sealed" if sealed else "not sealed"))
    return results


# ---------------------------------------------------------------- runner + receipt
def run_matrix():
    rows = []
    counts = {k: 0 for k in ("intended", "opposite", "off_axis", "unassessed",
                             "published", "refused", "abstained", "repaired",
                             "quarantined", "halted",
                             "correct_expert_selections", "incorrect_expert_selections")}
    for sc in SCENARIOS():
        eng = sc["build"]()
        res = eng.run()
        res2 = sc["build"]().run()
        names = {e["event"] for e in res["events"]}
        missing = [x for x in sc["expect"] if x not in names]
        present_bad = [x for x in sc["prohibit"] if x in names]
        checks_ok = sc["checks"](res) if sc["checks"] else True
        replay_ok = res["trace_digest"] == res2["trace_digest"]
        passed = not missing and not present_bad and checks_ok and replay_ok
        m = res["metrics"]
        counts["intended"] += m["intended_effects"]; counts["opposite"] += m["opposite_effects"]
        counts["off_axis"] += m["off_axis_effects"]; counts["unassessed"] += m["unassessed_effects"]
        counts["published"] += m["published"]; counts["refused"] += m["refused"]
        counts["abstained"] += m["abstained"]; counts["repaired"] += m["repairs_completed"]
        counts["quarantined"] += m["quarantines"]; counts["halted"] += m["action_halt"]
        # verifier-side selection metrics (the engine cannot see gold)
        for p in res["publications"]:
            if p["verdict"] == "intended":
                counts["correct_expert_selections"] += 1
            else:
                counts["incorrect_expert_selections"] += 1
        rows.append({"id": sc["id"], "description": sc["description"],
                     "passed": passed, "missing_expected": missing,
                     "prohibited_present": present_bad, "checks_ok": checks_ok,
                     "replay_identical": replay_ok,
                     "trace_digest": res["trace_digest"],
                     "second_run_digest": res2["trace_digest"],
                     "metrics": m, "budget_left": res["budget_left"]})
    for cid, ok, detail in coordinator_scenarios():
        rows.append({"id": cid, "description": "coordinator authority scenario",
                     "passed": ok, "detail": detail, "kind": "coordinator"})
    return rows, counts


if __name__ == "__main__":
    import json
    rows, counts = run_matrix()
    print(json.dumps({"scenarios": len(rows),
                      "passed": sum(1 for r in rows if r["passed"]),
                      "counts": counts}, indent=2))
    for r in rows:
        if not r["passed"]:
            print("FAILED:", r["id"], r.get("missing_expected"), r.get("prohibited_present"),
                  r.get("detail"), "checks_ok=", r.get("checks_ok"))
