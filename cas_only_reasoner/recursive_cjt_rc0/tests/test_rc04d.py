"""test_rc04d.py -- RC-0.4D permanent tests (OWNER DIRECTIVE RC-0.4D: schema-complete
construction, final-publication atomicity, ASOM dispatch, whole-object detachment).

One section per directive section:
  1. ONE INPUT SCHEMA -- every constructor parameter registered, validated, owned;
     signature-coverage law; initial sealability probe (64-hex before the engine is
     returned).
  2. PUBLICATION IS PROVISIONAL until the final-seal barrier promotes it; an unsealed
     run holds ZERO publications (the invariant, not a display rule).
  3. ASOM ACTIONS ARE LOAD-BEARING -- cutoff dispatches repair, breakdown dispatches
     quarantine; masked experts are never mutated; RPM blocks stay a separate axis.
  4. SNAPSHOTS AND CONFIGURATION FULLY OWNED -- whole-object detachment; no caller
     alias reaches sealed state.
  5. GENERALIZED ADVERSARIAL MATRIX -- every parameter attacked with the standard
     poison set; every legal mutable input proven owned.

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

import dataclasses as dc
import inspect
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(ROOT))

import rc0_types as T0             # noqa: E402
import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,  # noqa: E402
                              PublicationRefused)

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def eng(cid="a0", **kw):
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY), **kw)


def build(**over):
    """Valid baseline engine build with per-parameter overrides."""
    reg = SC.Reg().add("m0", "^6_decompose", "intended", PAY)
    kw = dict(causes=[c6("m0")], gold_table=reg.gold, expected_payloads=reg.expected)
    kw.update(over)
    causes = kw.pop("causes")
    gold = kw.pop("gold_table")
    return E.RC01Engine(causes, gold, **kw)


# ================================================ 1. one complete input schema
POISONS = {
    "causes": [None, True, object(), float("nan"), [c6("x"), object()],
               [c6("d"), c6("d")]],
    "gold_table": [None, True, object(), float("nan"), []],
    "states": [True, object(), float("nan"), [], {},
               {"^6_decompose": None}],                     # None is legal; a dict
    #                                                         must cover ALL experts
    "budget": [None, True, object(), float("nan"), float("inf"), -1, 3.5],
    "taus": [None, True, object(), (1.0, 1.0), (1.0, 1.0, 1.0, 1.0),
             (float("nan"), 1.0, 1.0), (float("inf"), 1.0, 1.0), "111"],
    "episode_id": [None, True, object(), 5, b"ep0", ""],
    "rpm_enforcement_enabled": [None, object(), 1, 0, "true", float("nan")],
    "ohm_enabled": [None, object(), 1, "yes"],
    "commit_verdicts": [None, object(), 1, 2.0],
    "repair_requires": [True, object(), {"bad": 1},
                        {("^6_decompose", "WISDOM"): "notatuple"}],
    "max_total_branches": [None, True, object(), float("nan"), float("inf"), -1,
                           2.5, "lots"],
    "max_active_branches": [None, True, object(), float("nan"), -3, 1.5],
    "reopen_events": [object(), {"1": "^2_attract"}, {True: "^2_attract"},
                      {-1: "^2_attract"}, {1: "ghost_expert"}],
    "invalidation_events": [object(), 5, ("stringentry",), ((1, 2),),
                            (("^6_decompose", "NOPE"),)],
    "expected_payloads": [True, object(), 5, []],
}


def test_every_constructor_parameter_has_registered_validator():
    sig_params = set(inspect.signature(E.RC01Engine.__init__).parameters) - {"self"}
    assert sig_params == set(E.CONSTRUCTOR_SCHEMA_PARAMS), \
        "constructor signature and schema diverge"
    assert sig_params == set(POISONS), \
        "a constructor parameter has no adversarial poison coverage in this suite"


def test_nonbool_rpm_flag_rejected():
    for bad in (1, 0, "true", object(), None):
        try:
            build(rpm_enforcement_enabled=bad)
            raise AssertionError(f"non-bool rpm_enforcement_enabled accepted: {bad!r}")
        except (TypeError, ValueError):
            pass


def test_nonbool_ohm_flag_rejected():
    for bad in (1, "yes", object(), None):
        try:
            build(ohm_enabled=bad)
            raise AssertionError(f"non-bool ohm_enabled accepted: {bad!r}")
        except (TypeError, ValueError):
            pass


def test_nonbool_commit_flag_rejected():
    # includes the owner's direct attack (object()) AND the sealable poison (int 1):
    # int 1 is truthy and canonicalizable, so ONLY the schema stops it
    for bad in (object(), 1, 2.0, None):
        try:
            build(commit_verdicts=bad)
            raise AssertionError(f"non-bool commit_verdicts accepted: {bad!r}")
        except (TypeError, ValueError):
            pass


def test_untyped_cause_rejected_at_construction():
    for bad in ([object()], ["a-string"], [42], [None]):
        try:
            build(causes=bad)
            raise AssertionError(f"untyped cause accepted: {bad!r}")
        except (TypeError, ValueError):
            pass


def test_valid_cause_followed_by_poison_rejected_before_run():
    try:
        build(causes=[c6("v0"), object()])
        raise AssertionError("a poison entry after a valid Cause was accepted")
    except (TypeError, ValueError):
        pass
    try:
        build(causes=[c6("dup"), c6("dup")])
        raise AssertionError("duplicate cause_id accepted (policy is REJECT)")
    except ValueError:
        pass


def test_taus_requires_exact_immutable_three_tuple():
    for bad in ((1.0, 1.0), (1.0, 1.0, 1.0, 1.0), "111", None, object()):
        try:
            build(taus=bad)
            raise AssertionError(f"invalid taus accepted: {bad!r}")
        except (TypeError, ValueError):
            pass
    e = build(taus=[1.0, 1.0, 1.0])            # legal list input, owned as tuple
    assert isinstance(e.taus, tuple) and e.taus == (1.0, 1.0, 1.0)


def test_repair_requires_is_owned_not_caller_aliased():
    rr = {("^6_decompose", "WISDOM"): ("^6_decompose", "POWER")}
    e = build(repair_requires=rr)
    s1 = e.seal()
    rr[("^2_attract", "POWER")] = ("^2_attract", "WISDOM")   # mutate the ORIGINAL
    assert e.seal() == s1, "repair_requires is caller-aliased into sealed state"
    assert len(e.repair_requires) == 1


def test_every_accepted_engine_has_initial_real_seal():
    engines = [build(), build(budget=0), build(taus=(2.0, 1.0, 1.0)),
               build(rpm_enforcement_enabled=False, ohm_enabled=False,
                     commit_verdicts=False)]
    for e in engines:
        assert E._is_hex_seal(e.seal()), "an accepted engine failed the initial probe"


def test_generalized_constructor_adversarial_matrix():
    """RC-0.4D section 5: EVERY registered parameter attacked with the standard
    poison set; every illegal value must be rejected at construction (the engine
    never exists, so zero budget/commits/receipts/publications follow trivially)."""
    for param, poisons in POISONS.items():
        for bad in poisons:
            try:
                build(**{param: bad})
                raise AssertionError(f"poison accepted: {param}={bad!r}")
            except (TypeError, ValueError):
                pass
    build()                                     # and the valid baseline constructs


def test_legal_mutable_inputs_are_owned_after_construction():
    causes = [c6("own0")]
    reg = SC.Reg().add("own0", "^6_decompose", "intended", PAY)
    gold, exp = dict(reg.gold), dict(reg.expected)
    states = dict(SC.states())
    taus = [1.0, 1.0, 1.0]
    rr = {("^6_decompose", "WISDOM"): ("^6_decompose", "POWER")}
    ro = {5: "^2_attract"}
    inv = [("^6_decompose", "POWER")]
    e = E.RC01Engine(causes, gold, states=states, taus=taus, repair_requires=rr,
                     reopen_events=ro, invalidation_events=inv,
                     expected_payloads=exp)
    s1 = e.seal()
    causes.append(c6("ghost"))
    gold[("g", "^2_attract")] = "intended"
    exp[("g", "^2_attract")] = "x"
    states["^8_trigger"] = SC.bias(desire=9.0)
    taus[0] = 99.0
    rr.clear()
    ro[99] = "^3_averse"
    inv.append(("^2_attract", "WISDOM"))
    assert e.seal() == s1, \
        "mutating a caller-owned original after construction reached sealed state"


def test_subset_states_rejected_at_construction():
    """Internal audit round 2 (MAJOR): a SUBSET states dict was accepted and deferred
    failure to a raw mid-run KeyError -- past budget, commits, and a provisional
    publication. A provided states dict must cover EXACTLY the registered experts."""
    partial = {k: SC.bias() for k in ("^6_decompose", "^2_attract")}
    try:
        build(states=partial)
        raise AssertionError("a subset states dict was accepted at construction")
    except ValueError:
        pass
    try:
        build(states={})
        raise AssertionError("states={} was accepted (ambiguous with defaults)")
    except (TypeError, ValueError):
        pass


def test_multi_cutoff_dispatch_requeues_once():
    """Internal audit round 2 (MAJOR): one Cause naming K ready cutoff experts was
    requeued K times and PUBLISHED K times. The law: one authoritative envelope per
    cause id -- the dispatch requeues at most once, and exactly one publication."""
    both = ("structure_cue", "association_cue")     # names ^6_decompose AND ^8_trigger
    e = SC.engine([SC.cause("mc1", both, PAY)],
                  SC.Reg().add("mc1", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "cutoff"},
                                      "^8_trigger": {"region": "cutoff"}}))
    r = e.run()
    assert r["metrics"]["executions"] == 1, \
        f"one Cause executed {r['metrics']['executions']} times"
    assert r["metrics"]["published"] == 1, \
        f"one Cause published {r['metrics']['published']} times"
    assert sum(1 for d in e.pubcoord.ledger if d["decision"] == "PUBLISHED") == 1


# ================================================ 2. publication atomicity
def _standalone_provisional_flow():
    v = E.SealedVerifier({("s0", "^6_decompose"): "intended"},
                         {("s0", "^6_decompose"): "parts[alpha|beta|gamma|delta]"},
                         "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=v.validator())
    pubc = PublicationCoordinator("ep0", coord)
    causeS = SC.cause("s0", C6, PAY)
    eff = T.EffectCandidate("^6_decompose", "s0", "decompose",
                            "parts[alpha|beta|gamma|delta]", originating_tick=0,
                            base_bias_version=coord.version("^6_decompose"),
                            base_bias_digest=coord.get_digest("^6_decompose"))
    receipt = v.verify(causeS, eff, 0)
    coord.register_verifier_receipt(receipt)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    dcr = coord.commit([it], 0, effect_context=T.EffectCommitContext(
        effect=eff, verifier_receipt_digest=receipt.receipt_digest))
    intent = T.EffectPublicationIntent(
        "ep0", 0, "s0", eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version,
        base_state_digest=dcr.pre_state_digest,
        diagnostic_commit_digest=dcr.commit_digest)
    return pubc, intent


def test_publication_is_provisional_before_final_seal():
    pubc, intent = _standalone_provisional_flow()
    assert pubc.commit_publication(intent) == "PROVISIONAL_PUBLICATION"
    assert pubc.ledger[-1]["decision"] == "PROVISIONAL_PUBLICATION", \
        "PUBLISHED was written before the final-seal barrier"
    assert pubc.promote_provisionals() == 1
    assert pubc.ledger[-1]["decision"] == "PUBLISHED"
    # and in a full engine run, every published Effect passed through provisional
    e = eng("pv0")
    r = e.run()
    assert r["metrics"]["provisional_publications"] == r["metrics"]["published"] == 1


def _unsealed_publishing_run(cid="up0"):
    e = eng(cid)
    e.invalidation_events = {("x", object())}   # out-of-API poison past the gate
    try:
        e.run()
        raise AssertionError("unsealable publishing run escaped without a typed fault")
    except E.ControllerFault:
        return e


def test_unsealed_run_has_zero_published():
    e = _unsealed_publishing_run("up1")
    assert e.seal_digest == "UNSEALED_TERMINAL_FAULT"
    assert e.metrics["published"] == 0, \
        "an unsealed terminal run holds a published count"


def test_unsealed_run_has_no_published_ledger_entry():
    e = _unsealed_publishing_run("up2")
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger), \
        "an unsealed run holds an authoritative PUBLISHED ledger entry"
    assert all(p["status"] != "PUBLISHED" for p in e.publications)


def test_final_seal_promotes_provisional_publication_once():
    e = eng("pr0")
    r = e.run()
    assert r["metrics"]["published"] == 1
    published_rows = [d for d in e.pubcoord.ledger if d["decision"] == "PUBLISHED"]
    assert len(published_rows) == 1, "promotion did not yield exactly one PUBLISHED"
    # promotion is unrepeatable after finalization (gate) and idempotent by design
    try:
        e.pubcoord.promote_provisionals()
        raise AssertionError("promotion re-ran after finalization")
    except E.FinalizedControllerError:
        pass
    assert e.metrics["published"] == 1 and e.seal() == r["trace_digest"]


def test_finalization_failure_voids_provisional_receipts():
    e = _unsealed_publishing_run("up3")
    voided = [d for d in e.pubcoord.ledger if d["decision"] == "VOIDED_UNSEALED"]
    assert voided and voided[0].get("voided_from") == "PROVISIONAL_PUBLICATION", \
        "the provisional was not terminally voided"
    assert e.metrics["voided_publications"] >= 1
    # terminal void: the receipts stay consumed -- replay can never succeed
    assert e.pubcoord.consumed_registry_digest() != T.digest({"vr": [], "dc": []})


def test_valid_run_still_publishes_exactly_once():
    e = eng("ok0")
    r = e.run()
    assert r["metrics"]["published"] == 1
    assert sum(1 for d in e.pubcoord.ledger if d["decision"] == "PUBLISHED") == 1
    assert not any(d["decision"] == "PROVISIONAL_PUBLICATION" for d in e.pubcoord.ledger)
    assert not any(d["decision"] == "VOIDED_UNSEALED" for d in e.pubcoord.ledger)
    assert r["publications"][0]["status"] == "PUBLISHED"


# ================================================ 3. ASOM actions load-bearing
def test_cutoff_region_dispatches_repair_not_halt():
    e = SC.engine([c6("cu0")], SC.Reg().add("cu0", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "cutoff"}}))
    r = e.run()
    names = [ev["event"] for ev in r["events"]]
    assert "HALT" not in names, "cutoff region silently HALTED instead of repairing"
    assert "ASOM_CUTOFF_REPAIR" in names, "no typed cutoff repair dispatched"
    assert r["metrics"]["published"] == 1, "the repaired route did not run"


def test_breakdown_region_dispatches_quarantine_not_halt():
    e = SC.engine([c6("bd0")], SC.Reg().add("bd0", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "breakdown"}}))
    r = e.run()
    names = [ev["event"] for ev in r["events"]]
    assert "HALT" not in names, "breakdown region silently HALTED"
    q = [ev for ev in r["events"] if ev["event"] == "QUARANTINE"]
    assert q and q[0]["authorized_by"] == "asom_region:breakdown", \
        "no ASOM-authorized quarantine transition"
    assert "^6_decompose" in r["quarantined"]
    assert r["metrics"]["executions"] == 0 and r["metrics"]["published"] == 0


def test_cutoff_and_rpm_block_remain_separate_reasons():
    # (a) cutoff + fully-ready RPM: ASOM repair, no invented prerequisite
    e1 = SC.engine([c6("sep0")], SC.Reg().add("sep0", "^6_decompose", "intended", PAY),
                   states=SC.states(**{"^6_decompose": {"region": "cutoff"}}))
    r1 = e1.run()
    n1 = [ev["event"] for ev in r1["events"]]
    assert "ASOM_CUTOFF_REPAIR" in n1 and "NO_READY_CJT" not in n1
    assert r1["metrics"]["repairs_opened"] == 0, \
        "cutoff dispatch INVENTED an RPM prerequisite repair"
    # (b) active region + real WISDOM block: the RPM path, no ASOM cutoff event
    e2 = SC.engine([c6("sep1")], SC.Reg().add("sep1", "^6_decompose", "intended", PAY),
                   states=SC.states(**{"^6_decompose": {"wisdom": 0.0}}))
    r2 = e2.run()
    n2 = [ev["event"] for ev in r2["events"]]
    assert "NO_READY_CJT" in n2 and "REPAIR_DONE" in n2
    assert "ASOM_CUTOFF_REPAIR" not in n2, "an RPM block was relabeled as ASOM cutoff"


def test_masked_cutoff_does_not_open_repair():
    e = SC.engine([c6("mc0")], SC.Reg().add("mc0", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "cutoff", "mask": 0}}))
    r = e.run()
    names = [ev["event"] for ev in r["events"]]
    assert "ASOM_CUTOFF_REPAIR" not in names and "REPAIR_DONE" not in names, \
        "a hard-masked cutoff expert was repaired"
    assert all(m["version"] == 0 for m in r["final_states"].values()), \
        "a masked expert's state was mutated"
    assert "HALT" in names                       # masked dead-end halts, sealed


def test_masked_breakdown_does_not_mutate_quarantine():
    e = SC.engine([c6("mb0")], SC.Reg().add("mb0", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "breakdown", "mask": 0}}))
    r = e.run()
    assert r["quarantined"] == [], "a hard-masked breakdown expert was quarantined"
    assert not any(ev["event"] == "QUARANTINE" for ev in r["events"])


def test_asom_action_changes_next_tick_behavior():
    e = SC.engine([c6("nx0")], SC.Reg().add("nx0", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "cutoff"}}))
    r = e.run()
    ev = r["events"]
    repair_tick = next(x["tick"] for x in ev if x["event"] == "ASOM_CUTOFF_REPAIR")
    exec_tick = next(x["tick"] for x in ev if x["event"] == "EXECUTED")
    assert exec_tick > repair_tick, \
        "the dispatched ASOM action did not change next-tick behavior"


# ================================================ 4. fully owned snapshots/config
def _sealed_fault_engine(cid="fd0"):
    e = SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"theta": ("UNKNOWN_MODE",)}}))
    try:
        e.run()
        raise AssertionError("theta fault did not raise")
    except E.ControllerFault:
        return e


def test_fault_record_is_detached_from_runtime_snapshot():
    e = _sealed_fault_engine("fd1")
    snap = e.runtime_snapshot()
    assert snap["fault"] is not e.fault, \
        "runtime_snapshot aliases the live fault record"
    snap["fault"]["detail"] = "FORGED"
    assert e.fault["detail"] != "FORGED", "snapshot mutation reached the fault record"


def test_mutating_snapshot_fault_does_not_move_engine_seal():
    e = _sealed_fault_engine("fd2")
    sealed = e.seal_digest
    snap = e.runtime_snapshot()
    snap["fault"]["detail"] = "FORGED"
    snap["events"].append({"tick": 99, "event": "FORGED"})
    snap["metrics"]["published"] = 999
    assert e.seal() == sealed, "mutating the snapshot moved the engine seal"


def test_mutating_original_taus_after_construction_changes_nothing():
    taus = [1.0, 1.0, 1.0]
    e = build(taus=taus)
    s1 = e.seal()
    taus[0] = 99.0
    assert e.seal() == s1 and e.taus == (1.0, 1.0, 1.0)


def test_mutating_original_repair_map_after_construction_changes_nothing():
    rr = {("^6_decompose", "WISDOM"): ("^6_decompose", "POWER")}
    e = build(repair_requires=rr)
    s1 = e.seal()
    rr[("^3_averse", "POWER")] = ("^3_averse", "WISDOM")
    del rr[("^6_decompose", "WISDOM")]
    assert e.seal() == s1 and len(e.repair_requires) == 1


def test_no_snapshot_member_aliases_authoritative_mutable_state():
    e = eng("al0")
    e.run()
    snap = e.runtime_snapshot()
    live = [e.events, e.metrics, e.allocations, e.publications, e.pubcoord.ledger,
            e.coord.trace, e.quarantine_registry, e.reopen_events,
            e.repair_requires, e.split_frames, e.repair_frames, e.child_to_frame,
            e.consecutive, e.exec_counts]
    live_ids = {id(x) for x in live}
    if e.fault is not None:
        live_ids.add(id(e.fault))

    def walk(v):
        if isinstance(v, (list, dict)):
            assert id(v) not in live_ids, "a snapshot member aliases live engine state"
            for x in (v.values() if isinstance(v, dict) else v):
                walk(x)
    walk(snap)


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
