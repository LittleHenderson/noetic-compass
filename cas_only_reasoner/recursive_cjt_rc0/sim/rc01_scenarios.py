"""rc01_scenarios.py -- the RC-0.2 integrated adversarial scenario matrix and runner.

Every registered control path is exercised, INCLUDING the RC-0.2 authority paths:
real publication latch, corrupted-Effect refusal, single-route saturation deferral,
bounded multi-candidate CAP, split-resume-combine, and multi-prerequisite repair.

Expected payloads are registered through an INDEPENDENTLY WRITTEN oracle (different
string-construction code than the producer; declared literals in spirit) -- the producer
function is never used as its own oracle. Honest limit: same-process independence.

Deterministic, CPU-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rc0_types import BiasState, Governance, RegionRecord, RPMState  # noqa: E402
import rc01_engine as E  # noqa: E402
from rc01_types import Cause, digest  # noqa: E402
from rc01_experts import EVIDENCE_MARKERS  # noqa: E402


def bias(desire=2.0, wisdom=2.0, power=2.0, mask=1, region="unassessed",
         posterior=None, max_branches=8, max_depth=4, theta=("K_identity",)):
    post = posterior or {"unassessed": E.UNIFORM4, "saturation": E.SATUR4,
                         "active": E.ACTIVE4, "cutoff": E.CUTOFF4,
                         "breakdown": E.BREAK4}[region]
    return BiasState(
        substrate=("declared",), memory=(),
        rpm=RPMState(desire=desire, wisdom=wisdom, power=power),
        record=RegionRecord(region_posterior=post, committed_region=region),
        theta=tuple(theta),
        governance=Governance(hard_mask=mask, max_branches=max_branches, max_depth=max_depth))


def states(**over):
    base = {e: bias() for e in EVIDENCE_MARKERS}
    for eid, kw in over.items():
        base[eid] = bias(**kw)
    return base


C6 = ("structure_cue",)
C2 = ("valence_positive",)
C8 = ("association_cue",)
C68 = ("structure_cue", "association_cue")


def cause(cid, ev, payload="alpha beta gamma delta"):
    return Cause(cause_id=cid, evidence=tuple(ev), payload=payload)


# ---------------------------------------------------------------- independent oracle
def oracle_expected(expert: str, payload: str, mode: str = "K_identity") -> str:
    """INDEPENDENT expected-payload oracle. Written with different string code than
    the producer (replace/% formatting vs split/join/f-strings)."""
    bang = "!" if mode == "K_coarse" else ""
    if expert == "^2_attract":
        return "approach%s(%s)" % (bang, payload)
    if expert == "^3_averse":
        return "withdraw" + bang + "(" + payload + ")"
    if expert == "^6_decompose":
        if mode == "K_coarse":
            words = payload.split(" ")
            mid = max(1, len(words) // 2)
            return "parts[" + " ".join(words[:mid]) + "|" + " ".join(words[mid:]) + "]"
        return "parts[" + payload.replace(" ", "|") + "]"
    if expert == "^8_trigger":
        n = sum(1 for _ in payload)
        return "assoc%s(%s->recalled_%d)" % (bang, payload, n)
    raise KeyError(expert)


class Reg:
    """Builds the gold table + expected-payload registry together."""

    def __init__(self):
        self.gold = {}
        self.expected = {}

    def add(self, cid, expert, verdict, payload=None, mode="K_identity",
            combined_children=None):
        self.gold[(cid, expert)] = verdict
        if verdict == "intended":
            if combined_children is not None:
                self.expected[(cid, expert)] = " + ".join(
                    oracle_expected(expert, p, mode) for p in combined_children)
            elif payload is not None:
                self.expected[(cid, expert)] = oracle_expected(expert, payload, mode)
        return self

    def add_raw_expected(self, cid, expert, literal):
        self.expected[(cid, expert)] = literal
        return self


def engine(causes, reg: Reg, **kw):
    return E.RC01Engine(causes, reg.gold, expected_payloads=reg.expected, **kw)


PAY = "alpha beta gamma delta"


def _is_real_seal(d) -> bool:
    """RC-0.4C internal audit: the UNSEALED_TERMINAL_FAULT marker (or anything that is
    not a 64-hex digest) must never be accepted as a seal, and two markers must never
    read as an identical replay."""
    return (isinstance(d, str) and len(d) == 64
            and all(c in "0123456789abcdef" for c in d))


def _s(id_, build, expect, prohibit=(), checks=None, kind="engine", description=""):
    return {"id": id_, "build": build, "expect": tuple(expect),
            "prohibit": tuple(prohibit), "checks": checks, "kind": kind,
            "description": description}


def SCENARIOS():
    S = []
    S.append(_s("normal_intended",
        lambda: engine([cause("n0", C6, PAY)],
                       Reg().add("n0", "^6_decompose", "intended", PAY)),
        expect=["EXECUTED"], prohibit=["NO_READY_CJT", "HALT", "QUARANTINE"],
        checks=lambda r: r["metrics"]["published"] == 1
                         and r["publication_ledger"][0]["decision"] == "PUBLISHED"
                         and r["publications"][0]["producer"] == "^6_decompose",
        description="Relevant CJT selected; intended Effect PUBLISHED through the latch."))
    S.append(_s("corrupted_payload_refused",
        lambda: engine([cause("cp0", C6, PAY)],
                       Reg().add("cp0", "^6_decompose", "intended", PAY),
                       states=states(**{"^6_decompose": {"theta": ("K_coarse",)}})),
        expect=["EXECUTED"], prohibit=[],
        checks=lambda r: r["metrics"]["published"] == 0 and r["metrics"]["refused"] == 1
                         and r["metrics"]["off_axis_effects"] == 1,
        description="Correct expert, corrupted payload (mode mismatch): verifier refuses; nothing publishes."))
    S.append(_s("desire_block",
        lambda: engine([cause("d0", C6, PAY)], Reg(),
                       states=states(**{"^6_decompose": {"desire": 0.0}})),
        expect=["TYPED_ABSTENTION", "NO_READY_CJT", "DESIRE_DEPRIORITIZED"],
        prohibit=["REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["desire_deprioritized"] == 1
                         and r["metrics"]["repairs_opened"] == 0,
        description="Desire block deprioritizes; the kernel never invents relevance."))
    S.append(_s("wisdom_block_repair_return",
        lambda: engine([cause("w0", C6, PAY)],
                       Reg().add("w0", "^6_decompose", "intended", PAY),
                       states=states(**{"^6_decompose": {"wisdom": 0.0}})),
        expect=["TYPED_ABSTENTION", "NO_READY_CJT", "REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["repairs_completed"] == 1
                         and r["metrics"]["published"] == 1,
        description="FIRST_BLOCK=WISDOM; repair opens, completes, cause retried, published."))
    S.append(_s("power_block_repair",
        lambda: engine([cause("p0", C6, PAY)],
                       Reg().add("p0", "^6_decompose", "intended", PAY),
                       states=states(**{"^6_decompose": {"power": 0.0}})),
        expect=["NO_READY_CJT", "REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["repairs_completed"] == 1,
        description="Power block -> capacity repair -> return."))
    S.append(_s("two_missing_prerequisites",
        lambda: engine([cause("tm0", C6, PAY)],
                       Reg().add("tm0", "^6_decompose", "intended", PAY),
                       states=states(**{"^6_decompose": {"wisdom": 0.0, "power": 0.0}})),
        expect=["REPAIR_DONE", "EXECUTED"],
        checks=lambda r: r["metrics"]["repairs_completed"] == 2
                         and r["metrics"]["published"] == 1
                         and r["metrics"]["retry_limit_hits"] == 0,
        description="TWO missing prerequisites: repair W, return, repair P, return, execute, publish. Never stranded."))
    S.append(_s("hard_mask_extreme_V",
        lambda: engine([cause("m0", C6, PAY)], Reg(),
                       states=states(**{"^6_decompose": {"mask": 0, "desire": 1e12}})),
        expect=["NO_READY_CJT", "HALT"], prohibit=["EXECUTED"],
        checks=lambda r: r["metrics"]["executions"] == 0,
        description="Hard mask stays exactly zero under extreme Drive."))
    S.append(_s("all_unavailable",
        lambda: engine([cause("u0", C6, PAY)], Reg(),
                       states={e: bias(mask=0) for e in EVIDENCE_MARKERS}),
        expect=["NO_READY_CJT", "HALT"], prohibit=["EXECUTED"],
        checks=lambda r: r["metrics"]["no_ready_events"] == 1,
        description="All CJTs unavailable -> NO_READY_CJT -> typed halt."))
    S.append(_s("opposite_refused_quarantined",
        lambda: engine([cause("o0", C2, PAY), cause("o1", C2, PAY)],
                       Reg().add("o0", "^2_attract", "opposite")
                            .add("o1", "^2_attract", "intended", PAY)),
        expect=["QUARANTINE", "NO_READY_CJT"],
        checks=lambda r: r["metrics"]["refused"] == 1 and r["metrics"]["published"] == 0
                         and r["quarantined"] == ["^2_attract"],
        description="Opposite: REFUSED by the latch; producer quarantined; next tick route changes."))
    S.append(_s("off_axis_refused_repair",
        lambda: engine([cause("x0", C6, PAY)],
                       Reg().add("x0", "^6_decompose", "off_axis")),
        expect=["EXECUTED", "REPAIR_DONE"],
        checks=lambda r: r["metrics"]["refused"] == 1 and r["metrics"]["published"] == 0
                         and r["metrics"]["repairs_completed"] == 1,
        description="Off-axis: REFUSED; typed WISDOM repair opens."))
    S.append(_s("unassessed_abstains",
        lambda: engine([cause("q0", C8, PAY)], Reg()),
        expect=["EXECUTED"],
        checks=lambda r: r["metrics"]["abstained"] == 1 and r["metrics"]["published"] == 0
                         and r["publication_ledger"][0]["decision"] == "ABSTAINED",
        description="Unassessed -> typed abstention; publication refused by the latch."))
    S.append(_s("saturation_cap_bounded",
        lambda: engine([cause("sc0", C68, PAY)],
                       Reg().add("sc0", "^8_trigger", "intended", PAY),
                       states=states(**{"^6_decompose": {"region": "saturation",
                                                          "desire": 9.0}})),
        expect=["CAP_ENFORCED", "EXECUTED"],
        checks=lambda r: r["metrics"]["cap_events"] >= 1
                         and all(a.get("^6_decompose", 0) <= E.CAP_ALLOCATION_LIMIT + 1e-9
                                 for a in r["allocations"] if a),
        description="Multi-candidate CAP: the saturated route is ACTUALLY bounded <= 0.34 after redistribution."))
    S.append(_s("single_route_saturation_defers",
        lambda: engine([cause("sd0", C6, PAY)],
                       Reg().add("sd0", "^6_decompose", "intended", PAY),
                       states=states(**{"^6_decompose": {"region": "saturation"}})),
        expect=["CAUSE_DEFERRED"], prohibit=["CAP_ENFORCED", "EXECUTED"],
        checks=lambda r: r["metrics"]["deferred_causes"] == 1
                         and r["metrics"]["published"] == 0,
        description="Single live saturated route: DEFERRED. No fake CAP_ENFORCED at 1.0."))
    S.append(_s("split_resume_combine",
        lambda: engine([cause("sp0", ("structure_cue", "overload_cue"), "a b c d e f")],
                       Reg().add("sp0.c0", "^6_decompose", "intended", "a b c")
                            .add("sp0.c1", "^6_decompose", "intended", "d e f")
                            .add("sp0", "^6_decompose", "intended",
                                 combined_children=("a b c", "d e f")),
                       states=states(**{"^6_decompose": {"region": "saturation"}})),
        expect=["SPLIT", "CHILD_COLLECTED", "SPLIT_RESUMED"],
        checks=lambda r: r["metrics"]["splits_created"] == 2
                         and r["metrics"]["split_frames_resumed"] == 1
                         and r["metrics"]["published"] == 1
                         and any(p["status"] == "PUBLISHED"
                                 and p["cause"] == "sp0" for p in r["publications"]),
        description="SPLIT suspends the parent, collects verified children, resumes ONCE, publishes the combined Effect."))
    S.append(_s("split_child_failure_no_orphan",
        lambda: engine([cause("sf0", ("structure_cue", "overload_cue"), "a b c d e f")],
                       Reg().add("sf0.c0", "^6_decompose", "off_axis")
                            .add("sf0.c1", "^6_decompose", "intended", "d e f"),
                       states=states(**{"^6_decompose": {"region": "saturation"}})),
        expect=["SPLIT", "CHILD_COLLECTED", "SPLIT_FAILED"],
        prohibit=["SPLIT_RESUMED"],
        checks=lambda r: r["metrics"]["published"] == 0
                         and r["metrics"]["split_frames_failed"] == 1
                         and r["metrics"]["children_cancelled"] >= 1
                         and not any(p["status"] == "PUBLISHED" for p in r["publications"]),
        description="Child 0 fails: sibling with an intended oracle is CANCELLED, cannot escape and publish; no parent Effect."))
    S.append(_s("quarantine_reopen",
        lambda: engine([cause("qr0", C2, PAY), cause("qr1", C2, PAY), cause("qr2", C2, PAY)],
                       Reg().add("qr0", "^2_attract", "opposite")
                            .add("qr2", "^2_attract", "intended", PAY),
                       reopen_events={2: "^2_attract"}),
        expect=["QUARANTINE", "ROUTE_UNAVAILABLE_QUARANTINED", "REOPEN"],
        checks=lambda r: r["metrics"]["reopens"] == 1 and r["metrics"]["published"] == 1,
        description="Quarantine excludes the expert until an authorized reopen event."))
    S.append(_s("halt_budget",
        lambda: engine([cause("h0", C6, PAY), cause("h1", C6, PAY)],
                       Reg().add("h0", "^6_decompose", "intended", PAY), budget=1),
        expect=["HALT"],
        checks=lambda r: r["metrics"]["action_halt"] == 1 and _is_real_seal(r["trace_digest"]),
        description="Budget exhaustion -> HALT with state and trace sealed."))
    S.append(_s("cycle_detected",
        lambda: engine([cause("cy0", C6, PAY)], Reg(),
                       states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                       repair_requires={("^6_decompose", "WISDOM"): ("^8_trigger", "POWER"),
                                        ("^8_trigger", "POWER"): ("^6_decompose", "WISDOM")}),
        expect=["CYCLE_DETECTED"],
        checks=lambda r: r["metrics"]["cycle_detected"] >= 1,
        description="Typed prerequisite cycle detected; stack unwound."))
    S.append(_s("depth_limit",
        lambda: engine([cause("dp0", C6, PAY)], Reg(),
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
        lambda: engine([cause("ab0", C6, PAY)], Reg(),
                       states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                       max_active_branches=1,
                       repair_requires={("^6_decompose", "WISDOM"): ("^8_trigger", "POWER")}),
        expect=["ACTIVE_BRANCH_LIMIT"],
        checks=lambda r: r["metrics"]["active_branch_limit_hits"] >= 1,
        description="Kernel active-branch ceiling fires distinctly from the depth limit."))
    S.append(_s("total_branch_limit",
        lambda: engine([cause("tb0", C6, PAY)], Reg(),
                       states=states(**{"^6_decompose": {"wisdom": 0.0}}),
                       max_total_branches=0),
        expect=["TOTAL_BRANCH_LIMIT"],
        checks=lambda r: r["metrics"]["total_branch_limit_hits"] >= 1,
        description="Lifetime branch ceiling fires distinctly from the active ceiling."))
    S.append(_s("cached_acquisition",
        lambda: engine([cause("ca0", C6, PAY), cause("ca1", C6, PAY)],
                       Reg().add("ca0", "^6_decompose", "off_axis")
                            .add("ca1", "^6_decompose", "off_axis")),
        expect=["REPAIR_DONE", "CACHE_HIT"],
        checks=lambda r: r["metrics"]["cache_hits"] >= 1
                         and r["metrics"]["repairs_completed"] == 1,
        description="A cached acquisition prevents a duplicate repair."))
    S.append(_s("invalidation_reopens",
        lambda: engine([cause("iv0", C6, PAY), cause("iv1", C6, PAY)],
                       Reg().add("iv0", "^6_decompose", "off_axis")
                            .add("iv1", "^6_decompose", "off_axis"),
                       invalidation_events={("^6_decompose", "WISDOM")}),
        expect=["REPAIR_DONE", "INVALIDATION_REOPEN"],
        checks=lambda r: r["metrics"]["invalidations_honored"] >= 1
                         and r["metrics"]["repairs_completed"] == 2,
        description="An explicit invalidation event (consumed once) reopens a cached prerequisite."))
    return S


# ------------------------------------------------------- coordinator-level scenarios
def coordinator_scenarios():
    from rc01_coordinator import HardenedCoordinator, RejectedBatch
    from rc01_types import VersionedIntent
    results = []

    def fresh():
        return HardenedCoordinator({"^6_decompose": bias()}, "ep0")

    ok_rpm = RPMState(desire=3.0, wisdom=3.0, power=3.0)

    c = fresh()
    good = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm", ok_rpm,
                           c.version("^6_decompose"), c.get_digest("^6_decompose"))
    c.commit([good], 0)
    stale = VersionedIntent("ep0", 1, "kernel", "^6_decompose", "rpm", ok_rpm,
                            0, "old-digest")
    try:
        c.commit([stale], 1)
        results.append(("stale_intent_rejected", False, "stale intent committed"))
    except RejectedBatch as rb:
        results.append(("stale_intent_rejected", rb.law == "LAW_STALE_VERSION", rb.law))

    c = fresh()
    a = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm",
                        RPMState(desire=3.0, wisdom=3.0, power=3.0),
                        c.version("^6_decompose"), c.get_digest("^6_decompose"))
    b2 = VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm",
                         RPMState(desire=4.0, wisdom=4.0, power=4.0),
                         c.version("^6_decompose"), c.get_digest("^6_decompose"))
    try:
        c.commit([a, b2], 0)
        results.append(("duplicate_conflicting_rejected", False, "conflict committed"))
    except RejectedBatch as rb:
        results.append(("duplicate_conflicting_rejected",
                        rb.law == "LAW_NO_CONFLICTING_WRITES", rb.law))

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
                             "quarantined", "halted", "deferred",
                             "correct_expert_selections", "incorrect_expert_selections")}
    for sc in SCENARIOS():
        eng = sc["build"]()
        res = eng.run()
        res2 = sc["build"]().run()
        names = {e["event"] for e in res["events"]}
        missing = [x for x in sc["expect"] if x not in names]
        present_bad = [x for x in sc["prohibit"] if x in names]
        checks_ok = sc["checks"](res) if sc["checks"] else True
        replay_ok = (_is_real_seal(res["trace_digest"])
                     and res["trace_digest"] == res2["trace_digest"])
        passed = not missing and not present_bad and checks_ok and replay_ok
        m = res["metrics"]
        counts["intended"] += m["intended_effects"]; counts["opposite"] += m["opposite_effects"]
        counts["off_axis"] += m["off_axis_effects"]; counts["unassessed"] += m["unassessed_effects"]
        counts["published"] += m["published"]; counts["refused"] += m["refused"]
        counts["abstained"] += m["abstained"]; counts["repaired"] += m["repairs_completed"]
        counts["quarantined"] += m["quarantines"]; counts["halted"] += m["action_halt"]
        counts["deferred"] += m["deferred_causes"]
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
    failed = [r for r in rows if not r["passed"]]
    for r in failed:
        print("FAILED:", r["id"], r.get("missing_expected"), r.get("prohibited_present"),
              r.get("detail"), "checks_ok=", r.get("checks_ok"))
    raise SystemExit(1 if failed else 0)
