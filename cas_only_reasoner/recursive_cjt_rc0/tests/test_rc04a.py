"""test_rc04a.py -- RC-0.4A permanent tests (OWNER DIRECTIVE RC-0.4A, finalization
and exact-snapshot patch).

One section per directive section:
  1. FINALIZATION IS A REAL STATE -- run/tick/repair/split refuse after the latch;
     result() is a detached deep copy; the latch is seal-bound.
  2. NO PRE-CANONICALIZATION TYPE ERASURE -- reopen/invalidation/repair structures
     keep exact types into the seal; lookalike strings rejected at construction.
  3. EVERY FAULT PATH SEALS -- theta validated before budget spend; a typed
     ControllerFault carries the final seal; faults cannot publish; atomic rollback.
  4. FROZEN MUTATION INVENTORY -- the status law requires the exact manifest set.

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(ROOT))

import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402
from rc01_experts import cjt_step  # noqa: E402

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def eng(cid="a0", **kw):
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY), **kw)


# ================================================ 1. finalization is a real state
def test_run_cannot_execute_twice_after_finalization():
    e = eng("r0")
    r = e.run()
    assert e.finalized and r["finalized"]
    sealed = e.seal()
    execs = e.metrics["executions"]
    try:
        e.run()
        raise AssertionError("run() executed a second time after finalization")
    except E.FinalizedControllerError:
        pass
    assert e.seal() == sealed, "second run() mutated the sealed controller"
    assert e.metrics["executions"] == execs


def test_tick_cannot_mutate_after_finalization():
    e = eng("t0")
    e.run()
    sealed = e.seal()
    events_n = len(e.events)
    try:
        e.tick(99, c6("ghost"))
        raise AssertionError("tick() executed after finalization")
    except E.FinalizedControllerError:
        pass
    assert e.seal() == sealed and len(e.events) == events_n, \
        "direct tick() mutated the sealed controller"


def test_repair_cannot_mutate_after_finalization():
    e = eng("p0")
    e.run()
    sealed = e.seal()
    for attack, call in (
            ("_repair", lambda: e._repair("^6_decompose", "WISDOM", 99)),
            ("_do_split", lambda: e._do_split(99, c6("ghost2"), "^6_decompose")),
            ("_publish_or_refuse", lambda: e._publish_or_refuse(
                99, c6("ghost3"), None, None, None))):
        try:
            call()
            raise AssertionError(f"{attack} executed after finalization")
        except E.FinalizedControllerError:
            pass
    assert e.seal() == sealed, "a mutating entry point moved the sealed state"


def test_result_returns_detached_evidence():
    e = eng("d0")
    r = e.run()
    assert r["events"] is not e.events
    assert r["allocations"] is not e.allocations
    assert r["publications"] is not e.publications
    assert r["metrics"] is not e.metrics
    n_events, n_pubs = len(e.events), len(e.publications)
    r["events"].append({"event": "FORGED"})
    r["publications"][0]["effect_payload"] = "TAMPERED"
    r["metrics"]["published"] = 999
    assert len(e.events) == n_events and len(e.publications) == n_pubs
    assert e.publications[0]["effect_payload"] != "TAMPERED"
    assert e.metrics["published"] != 999


def test_mutating_returned_result_does_not_change_engine_seal():
    e = eng("d1")
    r = e.run()
    d = r["trace_digest"]
    r["events"].clear()
    r["publications"].clear()
    r["metrics"].clear()
    r["publication_ledger"].append({"decision": "PUBLISHED", "forged": True})
    assert e.seal() == d, "mutating the returned result reached engine state"


def test_finalized_flag_is_seal_bound():
    e = eng("d2")
    s1 = e.seal()                      # pre-run: finalized False
    e.finalized = True                 # direct injection: the latch itself
    assert e.seal() != s1, "seal blind to the finalized latch"


# ================================================ 2. no pre-canonicalization erasure
def test_reopen_int_key_and_string_key_cannot_share_seal():
    e1, e2 = eng("s0"), eng("s0")
    e1.reopen_events = {1: "^2_attract"}
    e2.reopen_events = {"1": "^2_attract"}     # injected past construction on purpose
    assert e1.seal() != e2.seal(), \
        "int tick 1 and string tick '1' share a seal (type erased before encoding)"


def test_reopen_string_tick_rejected():
    try:
        eng("s1", reopen_events=(("1", "^2_attract"),))
        raise AssertionError("string reopen tick accepted at construction")
    except (TypeError, ValueError):
        pass
    try:
        eng("s1", reopen_events=((2, "not_an_expert"),))
        raise AssertionError("unregistered reopen expert accepted at construction")
    except (TypeError, ValueError):
        pass


def test_invalidation_tuple_and_lookalike_string_cannot_share_seal():
    e1, e2 = eng("s2"), eng("s2")
    e1.invalidation_events = {("^8_trigger", "POWER")}
    e2.invalidation_events = {"('^8_trigger', 'POWER')"}
    assert e1.seal() != e2.seal(), \
        "typed invalidation tuple and its lookalike string share a seal"
    try:
        eng("s2", invalidation_events=("('^8_trigger', 'POWER')",))
        raise AssertionError("lookalike-string invalidation accepted at construction")
    except (TypeError, ValueError):
        pass


def test_repair_key_and_lookalike_string_cannot_share_seal():
    e1, e2 = eng("s3"), eng("s3")
    e1.repair_requires = {("^6_decompose", "WISDOM"): ("^6_decompose", "POWER")}
    e2.repair_requires = {"('^6_decompose', 'WISDOM')": "('^6_decompose', 'POWER')"}
    assert e1.seal() != e2.seal(), \
        "typed repair key and its lookalike string share a seal"
    try:
        eng("s3", repair_requires={"('^6_decompose', 'WISDOM')": ("^6_decompose", "POWER")})
        raise AssertionError("lookalike-string repair key accepted at construction")
    except (TypeError, ValueError):
        pass


def test_runtime_snapshot_contains_no_str_coercion_of_typed_state():
    e = eng("s4", reopen_events=((3, "^2_attract"),),
            invalidation_events=(("^6_decompose", "POWER"),),
            repair_requires={("^6_decompose", "WISDOM"): ("^6_decompose", "POWER")})
    snap = e.runtime_snapshot()
    for tick, expert in snap["reopen_schedule"]:
        assert isinstance(tick, int) and not isinstance(tick, bool), \
            f"reopen tick stringified: {tick!r}"
        assert isinstance(expert, str)
    for entry in snap["invalidation_events"]:
        assert isinstance(entry, tuple) and len(entry) == 2, \
            f"invalidation entry stringified: {entry!r}"
    for k, v in snap["repair_dependency_graph"]:
        assert isinstance(k, tuple) and isinstance(v, tuple), \
            f"repair graph entry stringified: {k!r} -> {v!r}"


# ================================================ 3. every fault path seals
def test_invalid_theta_rejected_before_budget_spend():
    b = SC.bias(theta=("UNKNOWN_MODE",))
    budget = T.ComputeBudget.make(3)
    try:
        cjt_step("^6_decompose", c6("f0"), b, 1.0, budget, 0, 0, "d")
        raise AssertionError("unknown theta mode executed")
    except ValueError:
        pass
    assert budget.left == 3, "budget was spent before the mode was validated"


def test_invalid_theta_cannot_escape_unsealed():
    e = eng("f1", states=SC.states(**{"^6_decompose": {"theta": ("UNKNOWN_MODE",)}}))
    try:
        e.run()
        raise AssertionError("invalid theta escaped without a typed fault")
    except E.ControllerFault as cf:
        assert e.finalized, "fault did not finalize the controller"
        assert e.seal_digest == e.seal(), "fault escaped with a stale/absent seal"
        assert cf.seal_digest == e.seal_digest
        assert cf.fault["exception_class"] == "ValueError"
    assert any(ev["event"] == "FAULT" for ev in e.events), "no typed FAULT event"
    assert e.metrics["faults"] == 1


def test_unexpected_cjtstep_exception_returns_sealed_fault():
    original = E.cjt_step
    def exploding(*_a, **_k):
        raise RuntimeError("unexpected explosion (not the budget signal)")
    E.cjt_step = exploding
    try:
        e = eng("f2")
        try:
            e.run()
            raise AssertionError("unexpected step exception escaped unsealed")
        except E.ControllerFault as cf:
            assert cf.fault["exception_class"] == "RuntimeError"
            assert e.finalized and e.seal_digest == e.seal()
    finally:
        E.cjt_step = original


def test_fault_path_cannot_publish():
    e = eng("f3", states=SC.states(**{"^6_decompose": {"theta": ("UNKNOWN_MODE",)}}))
    try:
        e.run()
    except E.ControllerFault:
        pass
    assert e.metrics["published"] == 0, "the fault path published"
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger)
    r = e.result()
    assert r["fault"] is not None and r["trace_digest"] == e.seal()


def test_fault_path_final_seal_equals_recomputed_seal():
    e = eng("f4", states=SC.states(**{"^6_decompose": {"theta": ("UNKNOWN_MODE",)}}))
    try:
        e.run()
    except E.ControllerFault:
        pass
    assert e.seal_digest == e.seal(), "fault seal is not the final-current seal"
    sealed = e.seal_digest
    try:
        e.run()
        raise AssertionError("faulted controller ran again")
    except E.FinalizedControllerError:
        pass
    assert e.seal() == sealed


def test_fault_after_partial_intent_generation_rolls_back_atomically():
    # the verifier explodes AFTER the step ran (budget spent, Effect built) but
    # BEFORE any intent commit: no state commit, no receipt, no publication may
    # survive; the fault is sealed
    e = eng("f5")
    def exploding_verify(*_a, **_k):
        raise ValueError("oracle exploded mid-verification")
    e.verifier.verify = exploding_verify
    try:
        e.run()
        raise AssertionError("verifier fault escaped unsealed")
    except E.ControllerFault:
        pass
    assert all(e.coord.version(x) == 0 for x in e.coord.expert_ids()), \
        "a partial transition left committed state behind"
    assert not any(t.get("event") == "COMMIT" for t in e.coord.trace), \
        "a COMMIT survived the fault"
    assert e.metrics["published"] == 0
    assert e.finalized and e.seal_digest == e.seal()


# ================================================ 4. frozen mutation inventory
def _law_env():
    import generate_rc02_receipt as G
    manifest, reason = G.load_required_manifest()
    assert manifest is not None and reason == "OK", reason
    return G, manifest


def _report_from(manifest, drop=None, add=None, rename=None, break_pair=None):
    muts = []
    for m in manifest["mutations"]:
        if m["name"] == drop:
            continue
        entry = {"name": m["name"], "file": m["file"],
                 "expected_test": m["expected_test"],
                 "applied": True, "caught": True, "semantic_failure": True}
        if m["name"] == rename:
            entry["name"] = "renamed_" + m["name"]
        if m["name"] == break_pair:
            entry["expected_test"] = "test_wrong::test_other"
        muts.append(entry)
    if add:
        muts.append({"name": add, "file": "sim/other.py",
                     "expected_test": "test_x::test_y",
                     "applied": True, "caught": True, "semantic_failure": True})
    return {"mutations": muts}


def test_missing_required_mutation_refutes_status():
    G, manifest = _law_env()
    victim = manifest["mutations"][0]["name"]
    ok, reason = G.mutation_manifest_law(_report_from(manifest, drop=victim), manifest)
    assert not ok and reason.startswith("MUTATION_MANIFEST_MISSING_REQUIRED"), reason
    status = G.emit_status(True, False, True, ok, True, True, True, True)
    assert status == "GATE0_REFUTED", \
        "a deleted required mutation did not refute the status"


def test_extra_unregistered_mutation_refuses_status():
    G, manifest = _law_env()
    ok, reason = G.mutation_manifest_law(
        _report_from(manifest, add="sneaky_new_mutation"), manifest)
    assert not ok and reason.startswith("MUTATION_MANIFEST_EXTRA_UNREGISTERED"), reason
    assert G.emit_status(True, False, True, ok, True, True, True, True) == "GATE0_REFUTED"


def test_mutation_name_substitution_refuses_status():
    G, manifest = _law_env()
    victim = manifest["mutations"][2]["name"]
    ok, reason = G.mutation_manifest_law(_report_from(manifest, rename=victim), manifest)
    assert not ok and reason.startswith("MUTATION_MANIFEST_"), reason
    assert G.emit_status(True, False, True, ok, True, True, True, True) == "GATE0_REFUTED"


def test_mutation_file_or_test_mismatch_refuses_status():
    G, manifest = _law_env()
    victim = manifest["mutations"][4]["name"]
    ok, reason = G.mutation_manifest_law(
        _report_from(manifest, break_pair=victim), manifest)
    assert not ok and reason.startswith("MUTATION_MANIFEST_PAIR_MISMATCH"), reason
    assert G.emit_status(True, False, True, ok, True, True, True, True) == "GATE0_REFUTED"


def test_complete_frozen_mutation_set_passes():
    import json
    import tempfile
    G, manifest = _law_env()
    ok, reason = G.mutation_manifest_law(_report_from(manifest), manifest)
    assert ok and reason == "OK", reason
    status = G.emit_status(True, False, True, ok, True, True, True, True)
    assert status == \
        "DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT"
    # and the manifest itself is tamper-checked against the pinned digest
    with tempfile.TemporaryDirectory(prefix="rc04a_man_") as tmp:
        tampered = dict(manifest)
        tampered["required_count"] = 1
        p = Path(tmp) / "tampered.json"
        p.write_text(json.dumps(tampered), encoding="utf-8")
        m2, r2 = G.load_required_manifest(p)
        assert m2 is None and r2 == "MUTATION_MANIFEST_TAMPERED", r2


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
