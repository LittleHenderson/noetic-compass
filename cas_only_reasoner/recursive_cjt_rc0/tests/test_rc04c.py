"""test_rc04c.py -- RC-0.4C permanent tests (OWNER DIRECTIVE RC-0.4C, verifier-gate
and configuration-preflight patch).

One section per directive section:
  1. VERIFIER GATED AFTER FINALIZATION -- verify() refuses before issuing a receipt,
     mutating the issuance registry, or moving the engine seal.
  2. COMPLETE CONFIGURATION PREFLIGHT -- every accepted verifier configuration is
     validated, canonicalized, and digest-precomputed at construction; a poison entry
     can never let work or a publication happen before a delayed seal failure.
  3. A FAULT-ONLY HASH IS NOT A SEAL -- a seal-computation failure yields the marker
     UNSEALED_TERMINAL_FAULT (never a digest), prohibits publication eligibility, and
     preserves the underlying exception separately.

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(ROOT))

import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def eng(cid="a0", **kw):
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY), **kw)


def _post_finalize_verify_attempt(e):
    causeX = SC.cause("pfx", C6, PAY)
    eff = T.EffectCandidate("^6_decompose", "pfx", "decompose", PAY, originating_tick=0)
    return lambda: e.verifier.verify(causeX, eff, 0)


# ==================================== 1. verifier gated after finalization
def test_verifier_verify_refused_after_finalization():
    e = eng("v0")
    e.run()
    try:
        _post_finalize_verify_attempt(e)()
        raise AssertionError("verifier.verify issued a receipt after finalization")
    except E.FinalizedControllerError:
        pass


def test_post_finalize_verify_leaves_issued_registry_unchanged():
    e = eng("v1")
    e.run()
    reg_before = e.verifier.issued_registry_digest()
    try:
        _post_finalize_verify_attempt(e)()
    except E.FinalizedControllerError:
        pass
    assert e.verifier.issued_registry_digest() == reg_before, \
        "the issuance registry moved on a refused post-finalization verify"


def test_post_finalize_verify_leaves_engine_seal_unchanged():
    e = eng("v2")
    r = e.run()
    try:
        _post_finalize_verify_attempt(e)()
    except E.FinalizedControllerError:
        pass
    assert e.seal() == r["trace_digest"] == e.seal_digest, \
        "the engine seal moved on a refused post-finalization verify"


def test_result_remains_valid_after_refused_post_finalize_verify():
    e = eng("v3")
    r = e.run()
    try:
        _post_finalize_verify_attempt(e)()
    except E.FinalizedControllerError:
        pass
    r2 = e.result()      # must NOT raise ControllerTampered
    assert r2["trace_digest"] == r["trace_digest"]


# ==================================== 2. complete configuration preflight
def _mk_verifier(gold, expected):
    return E.SealedVerifier(gold, expected, "ep0")


def test_malformed_gold_key_rejected_at_construction():
    for bad_key in ("not-a-tuple", ("only-one",), (True, "^6_decompose"),
                    ("c0", 5), ("c0", "^6_decompose", "extra")):
        try:
            _mk_verifier({bad_key: "intended"}, {})
            raise AssertionError(f"malformed gold key accepted: {bad_key!r}")
        except (TypeError, ValueError):
            pass


def test_unknown_gold_verdict_rejected_at_construction():
    for bad_verdict in ("banana", "INTENDED", 1, True, None, object()):
        try:
            _mk_verifier({("c0", "^6_decompose"): bad_verdict}, {})
            raise AssertionError(f"unknown gold verdict accepted: {bad_verdict!r}")
        except (TypeError, ValueError):
            pass


def test_uncanonicalizable_gold_value_rejected_at_construction():
    try:
        _mk_verifier({("c0", "^6_decompose"): object()}, {})
        raise AssertionError("uncanonicalizable gold value accepted")
    except (TypeError, ValueError):
        pass
    # unregistered expert in the key is rejected too
    try:
        _mk_verifier({("c0", "^99_not_an_expert"): "intended"}, {})
        raise AssertionError("unregistered expert accepted in gold key")
    except (TypeError, ValueError):
        pass


def test_malformed_expected_payload_key_rejected_at_construction():
    for bad_key in ("raw-string", (1, "^6_decompose"), ("c0", False)):
        try:
            _mk_verifier({}, {bad_key: "parts[x]"})
            raise AssertionError(f"malformed expected-payload key accepted: {bad_key!r}")
        except (TypeError, ValueError):
            pass


def test_uncanonicalizable_expected_payload_rejected_at_construction():
    for bad_val in (object(), 5, True, None, ("tuple", "payload")):
        try:
            _mk_verifier({}, {("c0", "^6_decompose"): bad_val})
            raise AssertionError(f"non-str expected payload accepted: {bad_val!r}")
        except (TypeError, ValueError):
            pass


def test_unused_poison_gold_entry_rejected_before_first_tick():
    # the owner's exact attack: the real task never consults the poison entry, so in
    # the old code the engine could route/execute/verify/commit/PUBLISH and only then
    # fail at final sealing. Preflight must kill it at CONSTRUCTION.
    reg = SC.Reg().add("p0", "^6_decompose", "intended", PAY)
    poison_gold = dict(reg.gold)
    poison_gold[("unused", "^2_attract")] = object()
    try:
        E.RC01Engine([c6("p0")], poison_gold, expected_payloads=reg.expected)
        raise AssertionError("unused poison gold entry accepted at construction")
    except (TypeError, ValueError):
        pass


def test_unused_poison_expected_entry_rejected_before_first_tick():
    reg = SC.Reg().add("p1", "^6_decompose", "intended", PAY)
    poison_exp = dict(reg.expected)
    poison_exp[("unused", "^2_attract")] = object()
    try:
        E.RC01Engine([c6("p1")], reg.gold, expected_payloads=poison_exp)
        raise AssertionError("unused poison expected entry accepted at construction")
    except (TypeError, ValueError):
        pass


def test_invalid_verifier_configuration_spends_zero_budget():
    # the verifier is constructed BEFORE the budget in RC01Engine.__init__; a config
    # rejection therefore precedes the existence of any spendable budget. Constructing
    # must raise; a subsequently built VALID engine anchors the zero-spend state.
    reg = SC.Reg().add("p2", "^6_decompose", "intended", PAY)
    try:
        E.RC01Engine([c6("p2")], {("x", "^6_decompose"): "banana"},
                     expected_payloads=reg.expected, budget=7)
        raise AssertionError("invalid verifier configuration built an engine")
    except (TypeError, ValueError):
        pass
    ok = E.RC01Engine([c6("p2")], reg.gold, expected_payloads=reg.expected, budget=7)
    assert ok.budget.left == 7, "budget existed/spent before preflight"


def test_invalid_verifier_configuration_commits_nothing():
    reg = SC.Reg().add("p3", "^6_decompose", "intended", PAY)
    try:
        E.RC01Engine([c6("p3")], {"malformed-key": "intended"},
                     expected_payloads=reg.expected)
        raise AssertionError("invalid verifier configuration built an engine")
    except (TypeError, ValueError):
        pass
    ok = E.RC01Engine([c6("p3")], reg.gold, expected_payloads=reg.expected)
    assert all(ok.coord.version(x) == 0 for x in ok.coord.expert_ids())
    assert not any(t.get("event") == "COMMIT" for t in ok.coord.trace)


def test_invalid_verifier_configuration_publishes_nothing():
    reg = SC.Reg().add("p4", "^6_decompose", "intended", PAY)
    try:
        E.RC01Engine([c6("p4")], reg.gold,
                     expected_payloads={("p4", "^6_decompose"): object()})
        raise AssertionError("invalid verifier configuration built an engine")
    except (TypeError, ValueError):
        pass
    ok = E.RC01Engine([c6("p4")], reg.gold, expected_payloads=reg.expected)
    assert ok.metrics["published"] == 0 and ok.pubcoord.ledger == []


# ==================================== 3. a fault-only hash is not a seal
def _unsealable_run(cid="u0"):
    """An engine whose FINAL SEAL fails: gold {} (verdict unassessed, nothing
    publishes) plus an out-of-API injected unsealable value -- the only remaining
    route, since preflight + construction validation close every public path."""
    e = SC.engine([c6(cid)], SC.Reg())     # empty gold -> unassessed -> no publish
    e.invalidation_events = {("^6_decompose", object())}   # raw write past the gate
    try:
        e.run()
        raise AssertionError("unsealable state escaped without a typed fault")
    except E.ControllerFault as cf:
        return e, cf


def test_seal_failure_never_returns_fault_only_hash_as_trace_seal():
    e, cf = _unsealable_run("u0")
    assert e.seal_digest == "UNSEALED_TERMINAL_FAULT", e.seal_digest
    assert cf.seal_digest == "UNSEALED_TERMINAL_FAULT"
    assert not HEX64.match(str(e.seal_digest)), \
        "a digest-shaped value was returned where no seal exists"
    assert not str(e.seal_digest).startswith("SEAL_FAILED:"), \
        "the retired fault-only hash form reappeared"


def test_seal_failure_cannot_leave_published_effect():
    e, _ = _unsealable_run("u1")
    assert e.metrics["published"] == 0, "an unsealed terminal run holds a publication"
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger)
    # and publication eligibility is prohibited afterwards: the gate is tripped
    try:
        e.pubcoord.refuse(9, "x", "^6_decompose", "d", "post-fault")
        raise AssertionError("publication ledger accepted writes after the fault")
    except E.FinalizedControllerError:
        pass


def test_seal_failure_status_is_not_gate0_pass():
    e, cf = _unsealable_run("u2")
    assert e.finalized and e.fault is not None
    assert cf.fault["phase"] == "seal" and cf.fault.get("seal_failed") is True
    # RC-0.4C internal-audit hardening: an unsealed run HAS no result -- result()
    # raises the typed ControllerFault instead of emitting pass-shaped evidence;
    # the partial evidence stays on the engine object for forensics
    try:
        e.result()
        raise AssertionError("result() emitted evidence for an unsealed run")
    except E.ControllerFault as rf:
        assert rf.seal_digest == "UNSEALED_TERMINAL_FAULT"
    assert e.fault is not None, "the underlying exception was not preserved"


def test_all_accepted_configurations_preflight_as_sealable():
    configs = [
        ({}, {}),
        ({("c0", "^6_decompose"): "intended"}, {("c0", "^6_decompose"): "parts[a|b]"}),
        ({("c1", "^2_attract"): "opposite", ("c2", "^3_averse"): "off_axis",
          ("c3", "^8_trigger"): "unassessed"}, {}),
        ({("cu", "^6_decompose"): "intended"},
         {("cu", "^6_decompose"): "parts[ünicode|payload]"}),
    ]
    for gold, exp in configs:
        v = E.SealedVerifier(gold, exp, "ep0")
        assert HEX64.match(v.gold_table_digest()), "gold digest not precomputed hex"
        assert HEX64.match(v.expected_payloads_digest()), \
            "expected digest not precomputed hex"
    # and an engine over an accepted configuration seals BEFORE any tick
    e = eng("s0")
    assert HEX64.match(e.seal()), "an accepted configuration failed to seal"


# ==================================== 4. internal-audit locks (round 2)
def test_nonfinite_branch_limits_rejected_at_construction():
    """Internal audit CRITICAL: a NaN branch limit was accepted, the engine PUBLISHED,
    then failed to seal. Every constructor arg that reaches the seal is validated."""
    reg = SC.Reg().add("b0", "^6_decompose", "intended", PAY)
    for kw in ({"max_total_branches": float("nan")},
               {"max_total_branches": float("inf")},
               {"max_active_branches": float("nan")},
               {"max_total_branches": "lots"},
               {"max_active_branches": 3.5},
               {"max_total_branches": True}):
        try:
            E.RC01Engine([c6("b0")], reg.gold, expected_payloads=reg.expected, **kw)
            raise AssertionError(f"invalid branch limit accepted: {kw!r}")
        except (TypeError, ValueError):
            pass


def test_states_keys_validated_at_construction():
    reg = SC.Reg().add("b1", "^6_decompose", "intended", PAY)
    bad_states = dict(SC.states())
    bad_states[1] = SC.bias()                       # non-str expert key
    try:
        E.RC01Engine([c6("b1")], reg.gold, states=bad_states,
                     expected_payloads=reg.expected)
        raise AssertionError("non-str states key accepted")
    except (TypeError, ValueError):
        pass
    ghost_states = dict(SC.states())
    ghost_states["^99_ghost"] = SC.bias()           # unregistered expert
    try:
        E.RC01Engine([c6("b1")], reg.gold, states=ghost_states,
                     expected_payloads=reg.expected)
        raise AssertionError("unregistered expert silently admitted to state")
    except (TypeError, ValueError):
        pass


def test_episode_id_validated_at_construction():
    reg = SC.Reg().add("b2", "^6_decompose", "intended", PAY)
    for bad in (object(), 5, None, b"ep0"):
        try:
            E.RC01Engine([c6("b2")], reg.gold, expected_payloads=reg.expected,
                         episode_id=bad)
            raise AssertionError(f"non-str episode_id accepted: {bad!r}")
        except (TypeError, ValueError):
            pass


def test_unsealed_run_cannot_emit_published_evidence():
    """OWNER AUDIT RC-0.4D critical 2 (repairing this test's own prior assertion of
    published==1): an unsealed terminal run holds ZERO publications. The publication
    was PROVISIONAL; the failed final-seal barrier terminally VOIDED it -- published
    stays 0, no ledger row says PUBLISHED, and result() raises."""
    e = eng("pub0")
    e.invalidation_events = {("x", object())}       # out-of-API poison past the gate
    try:
        e.run()
        raise AssertionError("unsealable publishing run escaped without a typed fault")
    except E.ControllerFault:
        pass
    # THE INVARIANT: marker implies zero publications
    assert e.seal_digest == "UNSEALED_TERMINAL_FAULT"
    assert e.metrics["published"] == 0, \
        "an unsealed run holds a published count"
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger), \
        "an unsealed run holds an authoritative PUBLISHED ledger entry"
    assert all(p["status"] != "PUBLISHED" for p in e.publications)
    # the provisional was terminally voided, not hidden
    assert any(d["decision"] == "VOIDED_UNSEALED" for d in e.pubcoord.ledger)
    assert e.metrics["voided_publications"] >= 1
    try:
        e.result()
        raise AssertionError("evidence emitted from an unsealed run")
    except E.ControllerFault:
        pass
    assert not SC._is_real_seal("UNSEALED_TERMINAL_FAULT"), \
        "the scenario runner accepts the marker as a seal"
    assert SC._is_real_seal("a" * 64) and not SC._is_real_seal("z" * 64)


def test_finalize_failed_frame_refused_after_finalization():
    """Internal audit MAJOR: _finalize_failed_frame was the one split helper without
    the finalization guard -- it mutated metrics/events/frames and only then hit the
    gate, permanently bricking result()."""
    from rc01_engine import SplitFrame
    e = eng("ff0")
    e.run()
    sealed = e.seal()
    frame = SplitFrame(parent_cause=c6("ghostp"), chosen_expert="^6_decompose",
                       child_ids=("ghostp.c0",), pending={"ghostp.c0": "FAILED"},
                       return_address="ghostp")
    e.split_frames["ghostp"] = frame                # raw injection to reach the helper
    events_n, m1, m2 = len(e.events), e.metrics["split_frames_failed"], e.metrics["refused"]
    try:
        e._finalize_failed_frame(99, frame)
        raise AssertionError("_finalize_failed_frame executed after finalization")
    except E.FinalizedControllerError:
        pass
    assert len(e.events) == events_n, "the helper mutated events before refusing"
    assert e.metrics["split_frames_failed"] == m1 and e.metrics["refused"] == m2, \
        "the helper mutated metrics before refusing"
    del e.split_frames["ghostp"]                    # undo the raw injection
    assert e.seal() == sealed and e.result()["trace_digest"] == sealed


def test_runtime_snapshot_returns_detached_copies():
    e = eng("sn0")
    e.run()
    snap = e.runtime_snapshot()
    for key, live in (("events", e.events), ("metrics", e.metrics),
                      ("alloc", e.allocations), ("publications_evidence", e.publications),
                      ("publication_ledger", e.pubcoord.ledger),
                      ("commits", e.coord.trace)):
        assert snap[key] is not live, f"runtime_snapshot returns the LIVE {key}"
    sealed = e.seal()
    snap["events"].append({"tick": 99, "event": "FORGED_VIA_SNAPSHOT"})
    snap["metrics"]["published"] = 999
    assert e.seal() == sealed, "mutating the snapshot reached authoritative state"
    assert e.result()["trace_digest"] == sealed


def test_tamper_tripwire_survives_finalized_flag_flip():
    """Internal audit hardening: flipping e.finalized to False must not silently
    disable tamper detection -- the tripwire keys on seal_digest alone."""
    e = eng("tw0")
    e.run()
    e.metrics["published"] = 777                    # raw tamper past the gate
    e.finalized = False                             # attempted kill-switch
    try:
        e.result()
        raise AssertionError("flipping the finalized flag disabled tamper detection")
    except E.ControllerTampered:
        pass


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
