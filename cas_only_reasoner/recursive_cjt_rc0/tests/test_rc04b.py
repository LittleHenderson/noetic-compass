"""test_rc04b.py -- RC-0.4B post-audit hardening locks.

These tests lock the fixes for the CRITICAL/MAJOR findings from the internal pre-commit
adversarial audit of RC-0.4A (5 lenses; internal review, no authority):

  A. FINALIZATION GOVERNS THE WRITE PATHS (critical 1): the shared seal gate makes the
     coordinator, publication coordinator, and budget refuse every write after
     finalization -- not just 5 engine methods.
  B. RESULT() IS SELF-VERIFYING (major 2): a post-finalization out-of-API mutation makes
     result() refuse (ControllerTampered) rather than emit evidence under a stale seal.
  C. STORABLE == SEALABLE (critical 2): non-finite floats are rejected at construction
     (BiasState substrate/memory/theta, and taus), so seal() can never throw; and the
     fault boundary + FINALIZE seal never let a bare encoder exception escape.
  D. invalidations_consumed anti-stringification lock (directive-completeness major).
  E. frame_full binds parent evidence (snapshot-types suspicion).
  F. manifest-law hardening (three MINOR robustness fixes).

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

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
from rc01_coordinator import RejectedBatch, PublicationRefused  # noqa: E402

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def eng(cid="a0", **kw):
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY), **kw)


# ==================================== A. finalization governs the write paths
def test_coordinator_commit_refused_after_finalization():
    e = eng("g0")
    e.run()
    sealed = e.seal()
    intent = e._intent("^2_attract", "memory", (("forged", "x"),), 0, "forge")
    try:
        e.coord.commit([intent], 0)
        raise AssertionError("coordinator.commit mutated state after finalization")
    except E.FinalizedControllerError:
        pass
    assert e.seal() == sealed, "a post-finalization commit moved the sealed state"


def test_register_receipt_refused_after_finalization():
    e = eng("g1")
    e.run()
    causeX = SC.cause("g1", C6, PAY)
    eff = T.EffectCandidate("^6_decompose", "g1", "decompose", PAY, originating_tick=0)
    receipt = e.verifier.verify(causeX, eff, 0)
    try:
        e.coord.register_verifier_receipt(receipt)
        raise AssertionError("receipt registration succeeded after finalization")
    except E.FinalizedControllerError:
        pass


def test_budget_spend_refused_after_finalization():
    e = eng("g2")
    e.run()
    left = e.budget.left
    try:
        e.budget.spend(1)
        raise AssertionError("budget.spend succeeded after finalization")
    except E.FinalizedControllerError:
        pass
    assert e.budget.left == left, "budget moved after finalization"


def test_publication_mutators_refused_after_finalization():
    e = eng("g3")
    e.run()
    n = len(e.pubcoord.ledger)
    for call in (lambda: e.pubcoord.refuse(9, "x", "^6_decompose", "d", "forged"),
                 lambda: e.pubcoord.abstain(9, "x", "^6_decompose", "d")):
        try:
            call()
            raise AssertionError("publication ledger forged after finalization")
        except E.FinalizedControllerError:
            pass
    assert len(e.pubcoord.ledger) == n, "ledger grew after finalization"


def test_internal_helpers_refused_after_finalization():
    e = eng("g4")
    e.run()
    sealed = e.seal()
    for call in (lambda: e._quarantine("^3_averse", 9, "forged"),
                 lambda: e._reopen("^3_averse", 9),
                 lambda: e._seal_and_halt(9, "forged")):
        try:
            call()
            raise AssertionError("an internal helper mutated after finalization")
        except E.FinalizedControllerError:
            pass
    assert e.seal() == sealed


# ==================================== B. result() is self-verifying
def test_result_refuses_after_out_of_api_tamper():
    e = eng("t0")
    e.run()
    e.metrics["published"] = 999            # raw dict write, past the gate
    try:
        e.result()
        raise AssertionError("result() emitted evidence under a stale seal")
    except E.ControllerTampered:
        pass


def test_honest_result_recompute_matches():
    e = eng("t1")
    r = e.run()
    # no tamper: result() recomputes and matches, twice
    assert e.result()["trace_digest"] == r["trace_digest"] == e.seal()


# ==================================== C. storable == sealable
def test_nonfinite_float_rejected_in_biasstate():
    for bad in (float("nan"), float("inf"), float("-inf")):
        for field in ("substrate", "memory", "theta"):
            kw = {"substrate": ("declared",), "memory": (),
                  "rpm": T0.RPMState(2.0, 2.0, 2.0),
                  "record": T0.RegionRecord((0.25, 0.25, 0.25, 0.25), "unassessed"),
                  "theta": ("K_identity",),
                  "governance": T0.Governance(hard_mask=1)}
            kw[field] = (bad,) if field != "theta" else (bad,)
            try:
                T0.BiasState(**kw)
                raise AssertionError(f"BiasState accepted non-finite {bad!r} in {field}")
            except ValueError:
                pass


def test_nonfinite_tau_rejected_at_construction():
    for bad in (float("nan"), float("inf")):
        try:
            eng("t2", taus=(bad, 1.0, 1.0))
            raise AssertionError(f"engine accepted non-finite tau {bad!r}")
        except (ValueError, TypeError):
            pass


def test_seal_cannot_throw_via_stored_state():
    # every value BiasState/taus accept must be sealable: build the richest legal
    # state and confirm seal() succeeds
    e = eng("t3", states=SC.states(**{"^6_decompose": {
        "theta": ("K_identity",), "desire": 3.0, "wisdom": 3.0, "power": 3.0}}))
    e.run()
    assert isinstance(e.seal(), str) and len(e.seal()) == 64


# ==================================== D. invalidations_consumed lock
def test_invalidations_consumed_tuple_and_lookalike_cannot_share_seal():
    e1, e2 = eng("d0"), eng("d0")
    e1.invalidations_consumed = {("^8_trigger", "POWER")}
    e2.invalidations_consumed = {"('^8_trigger', 'POWER')"}
    assert e1.seal() != e2.seal(), \
        "typed invalidations_consumed tuple and its lookalike string share a seal"


def test_invalidations_consumed_typed_in_snapshot():
    # drive a real invalidation-consume: cached prereq + live invalidation + a
    # repair-triggering cause, then assert the snapshot entries stay typed tuples
    from rc0_types import RPMState
    b = SC.bias(wisdom=0.0)                        # WISDOM blocked -> repair needed
    b = __import__("dataclasses").replace(
        b, rpm=RPMState(desire=2.0, wisdom=0.0, power=2.0,
                        acquired=("WISDOM@-1",)))    # cached, so invalidation reopens it
    e = SC.engine([c6("dc0")], SC.Reg().add("dc0", "^6_decompose", "intended", PAY),
                  states={**SC.states(), "^6_decompose": b},
                  invalidation_events=(("^6_decompose", "WISDOM"),))
    e.run()
    snap = e.runtime_snapshot()
    for entry in snap["invalidations_consumed"]:
        assert isinstance(entry, tuple) and len(entry) == 2 \
            and all(isinstance(x, str) for x in entry), \
            f"invalidations_consumed entry stringified: {entry!r}"


# ==================================== E. frame_full binds parent evidence
def test_frame_full_binds_parent_evidence():
    from rc01_engine import SplitFrame
    from rc01_types import Cause
    def make():
        return eng("z0")
    a, b = make(), make()
    def frame(parent):
        return SplitFrame(parent_cause=parent, chosen_expert="^6_decompose",
                          child_ids=("p.c0", "p.c1"),
                          pending={"p.c0": None, "p.c1": None}, return_address="p")
    a.split_frames = {"p": frame(Cause("p", ("structure_cue", "overload_cue"), "a b c d"))}
    b.split_frames = {"p": frame(Cause("p", ("valence_positive",), "a b c d"))}
    assert a.seal() != b.seal(), "seal blind to a suspended frame's parent evidence"


# ==================================== F. manifest-law hardening
def _law():
    import generate_rc02_receipt as G
    manifest, reason = G.load_required_manifest()
    assert manifest is not None and reason == "OK", reason
    return G, manifest


def _base_report(manifest):
    return {"mutations": [{"name": m["name"], "file": m["file"],
                           "expected_test": m["expected_test"],
                           "applied": True, "caught": True, "semantic_failure": True}
                          for m in manifest["mutations"]]}


def test_duplicate_report_entry_refused():
    G, manifest = _law()
    rep = _base_report(manifest)
    rep["mutations"].append(dict(rep["mutations"][0]))   # 10 entries, 9 unique names
    ok, reason = G.mutation_manifest_law(rep, manifest)
    assert not ok and reason == "MUTATION_MANIFEST_DUPLICATE_ENTRY", reason


def test_nameless_report_entry_refused_cleanly():
    G, manifest = _law()
    rep = _base_report(manifest)
    rep["mutations"].append({"file": "x", "expected_test": "y",
                             "applied": True, "caught": True, "semantic_failure": True})
    ok, reason = G.mutation_manifest_law(rep, manifest)   # must not raise TypeError
    assert not ok and reason == "MUTATION_MANIFEST_MALFORMED_ENTRY", reason


def test_emit_status_is_independently_sound():
    G, _ = _law()
    # manifest_ok False must never yield PASS, regardless of report_exists
    for report_exists in (True, False):
        s = G.emit_status(all_detected=True, mutation_survived=False,
                          report_exists=report_exists, manifest_ok=False,
                          mutations_ok=True, suites_ok=True, scenarios_ok=True,
                          replay_ok=True)
        assert s != "DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT", \
            f"PASS emitted with manifest_ok False (report_exists={report_exists})"


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
