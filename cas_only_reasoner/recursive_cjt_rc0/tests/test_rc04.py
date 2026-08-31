"""test_rc04.py -- RC-0.4 permanent tests (OWNER DIRECTIVE RC-0.4, final minimal
Gate-0 closure).

Targets, one section per owner-directive section:
  1. DiagnosticCommitReceipt ELIGIBILITY (only a genuine Effect-bound diagnostic
     commit can mint one; memory/RPM-only commits never can);
  2. Effect snapshot fields LOAD-BEARING (false embedded Bias provenance refused);
  3. exact-type canonical encoding (no default=str collisions, hashseed-independent,
     NaN rejected, no untyped fallback);
  4. seal only AFTER the transition finishes (every halt returns a final-current seal);
  5. complete runtime snapshot (queue envelopes, publication evidence, configuration,
     verifier oracles all seal-bound);
  6. mutation-status law (a crashed audit can never reuse a stale passing report).

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

import dataclasses as dc
import json
import subprocess
import sys
import tempfile
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
                              PublicationRefused, RejectedBatch)
from rc_canonical import canonical, digest  # noqa: E402

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)
GOLD = {("x0", "^6_decompose"): "intended"}
EXP = {("x0", "^6_decompose"): "parts[alpha|beta|gamma|delta]"}


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def _stack(gold=GOLD, expected=EXP):
    v = E.SealedVerifier(gold, expected, "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=v.validator())
    pub = PublicationCoordinator("ep0", coord)
    return v, coord, pub


def _verified_effect(v, coord, payload="parts[alpha|beta|gamma|delta]",
                     bias_v=None, bias_d=None):
    """A legitimately verified Effect + registered receipt for cause x0."""
    causeX = SC.cause("x0", C6, PAY)
    eff = T.EffectCandidate(
        "^6_decompose", "x0", "decompose", payload, originating_tick=0,
        base_bias_version=coord.version("^6_decompose") if bias_v is None else bias_v,
        base_bias_digest=coord.get_digest("^6_decompose") if bias_d is None else bias_d)
    receipt = v.verify(causeX, eff, 0)
    coord.register_verifier_receipt(receipt)
    return eff, receipt


# ================================================================ 1. DCR eligibility
def test_memory_only_commit_cannot_mint_diagnostic_receipt():
    """The owner's exact bypass: a legitimate intended receipt + an unrelated
    memory-only commit must NEVER mint a DiagnosticCommitReceipt. If a mutated
    implementation mints one anyway, this test proves the CONSEQUENCE -- unauthorized
    publication -- and fails on that, not on an incidental crash."""
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord)
    mem = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "memory",
                            (("x0", "note"),), coord.version("^6_decompose"),
                            coord.get_digest("^6_decompose"))
    ctx = T.EffectCommitContext(effect=eff,
                                verifier_receipt_digest=receipt.receipt_digest)
    out = None
    try:
        out = coord.commit([mem], 0, effect_context=ctx)   # memory-only batch
    except RejectedBatch as rb:
        assert rb.law == "LAW_DCR_REQUIRES_SEMANTIC_RECORD", rb.law
        assert coord.version("^6_decompose") == 0, "rejected batch mutated state"
        return                                             # the law held
    # Reached only under a broken implementation: prove the authority consequence.
    published = False
    if isinstance(out, T.DiagnosticCommitReceipt):
        intent = T.EffectPublicationIntent(
            "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "intended",
            receipt.receipt_digest, base_state_version=out.pre_state_version,
            base_state_digest=out.pre_state_digest,
            diagnostic_commit_digest=out.commit_digest)
        try:
            published = pub.commit_publication(intent) == "PUBLISHED"
        except PublicationRefused:
            published = False
    assert not published, ("published without diagnostic commit: a memory-only "
                           "commit minted a DiagnosticCommitReceipt and it published")
    raise AssertionError("memory-only commit returned something other than a "
                         "rejection: " + repr(out))


def test_rpm_only_commit_cannot_mint_diagnostic_receipt():
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord)
    new_rpm = T0.RPMState(desire=3.0, wisdom=3.0, power=3.0)
    rpm_it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "rpm", new_rpm,
                               coord.version("^6_decompose"),
                               coord.get_digest("^6_decompose"))
    ctx = T.EffectCommitContext(effect=eff,
                                verifier_receipt_digest=receipt.receipt_digest)
    try:
        coord.commit([rpm_it], 0, effect_context=ctx)
        raise AssertionError("RPM-only commit minted a DiagnosticCommitReceipt")
    except RejectedBatch as rb:
        assert rb.law == "LAW_DCR_REQUIRES_SEMANTIC_RECORD", rb.law
    assert coord.version("^6_decompose") == 0, "rejected batch mutated state"


def test_diagnostic_receipt_requires_matching_semantic_record():
    # a record intent that does NOT cite the receipt (unassessed, no receipt) is not
    # a diagnosis of THIS Effect -- eligibility must refuse
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="unassessed")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"))
    ctx = T.EffectCommitContext(effect=eff,
                                verifier_receipt_digest=receipt.receipt_digest)
    try:
        coord.commit([it], 0, effect_context=ctx)
        raise AssertionError("a non-matching record intent minted a diagnostic receipt")
    except RejectedBatch as rb:
        assert rb.law == "LAW_DCR_REQUIRES_SEMANTIC_RECORD", rb.law


def test_diagnostic_receipt_requires_matching_verifier_receipt():
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    # (a) context cites a receipt that was never registered
    ctx_unknown = T.EffectCommitContext(effect=eff, verifier_receipt_digest="0" * 64)
    try:
        coord.commit([it], 0, effect_context=ctx_unknown)
        raise AssertionError("unregistered receipt accepted for a diagnostic commit")
    except RejectedBatch as rb:
        # the record intent itself cites the registered receipt, so either law is a
        # correct refusal; the context law must be the DCR one when reached
        assert rb.law in ("LAW_DCR_RECEIPT_NOT_REGISTERED",), rb.law
    # (b) context receipt is registered but binds a DIFFERENT Effect
    other = T.EffectCandidate("^6_decompose", "x0", "decompose", "parts[OTHER]",
                              originating_tick=0,
                              base_bias_version=coord.version("^6_decompose"),
                              base_bias_digest=coord.get_digest("^6_decompose"))
    ctx_mismatch = T.EffectCommitContext(effect=other,
                                         verifier_receipt_digest=receipt.receipt_digest)
    try:
        coord.commit([it], 0, effect_context=ctx_mismatch)
        raise AssertionError("receipt for a different Effect accepted")
    except RejectedBatch as rb:
        assert rb.law == "LAW_DCR_RECEIPT_EFFECT_MISMATCH", rb.law


def test_diagnostic_receipt_requires_matching_effect_context():
    # disconnected/untyped arguments are dead: only a typed EffectCommitContext works
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord)
    mem = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "memory", (("a", "b"),),
                            coord.version("^6_decompose"),
                            coord.get_digest("^6_decompose"))
    for untyped in ("x0", ("x0", eff.effect_digest), {"cause_id": "x0"}):
        try:
            coord.commit([mem], 0, effect_context=untyped)
            raise AssertionError("untyped effect context accepted")
        except RejectedBatch as rb:
            assert rb.law == "LAW_TYPED_EFFECT_CONTEXT", rb.law
    # and the typed context validates its own construction
    try:
        T.EffectCommitContext(effect="not-an-effect", verifier_receipt_digest="d")
        raise AssertionError("EffectCommitContext accepted a non-Effect")
    except TypeError:
        pass
    try:
        T.EffectCommitContext(effect=eff, verifier_receipt_digest="")
        raise AssertionError("EffectCommitContext accepted an empty receipt digest")
    except ValueError:
        pass


# ================================================ 2. Effect snapshot load-bearing
def _run_with_patched_step(mutator, cid="m0"):
    original = E.cjt_step

    def bad_step(expert_id, cause, bias, allocation, budget, tick, bias_version,
                 bias_digest=""):
        res = original(expert_id, cause, bias, allocation, budget, tick, bias_version,
                       bias_digest=bias_digest)
        return mutator(res)
    E.cjt_step = bad_step
    try:
        r = SC.engine([c6(cid)],
                      SC.Reg().add(cid, "^6_decompose", "intended", PAY)).run()
    finally:
        E.cjt_step = original
    return r


def test_effect_bias_version_mismatch_refused():
    def mutate(res):
        eff = dc.replace(res.effect_candidate,
                         base_bias_version=res.effect_candidate.base_bias_version + 5)
        return dc.replace(res, effect_candidate=eff)
    r = _run_with_patched_step(mutate)
    assert r["metrics"]["step_metadata_rejects"] >= 1, \
        "an Effect with a false embedded Bias VERSION was accepted"
    assert r["metrics"]["published"] == 0


def test_effect_bias_digest_mismatch_refused():
    def mutate(res):
        eff = dc.replace(res.effect_candidate, base_bias_digest="forged-snapshot")
        return dc.replace(res, effect_candidate=eff)
    r = _run_with_patched_step(mutate)
    assert r["metrics"]["step_metadata_rejects"] >= 1, \
        "an Effect with a false embedded Bias DIGEST was accepted"
    assert r["metrics"]["published"] == 0


def test_step_authoritative_version_mismatch_refused():
    def mutate(res):
        return dc.replace(res,
                          authoritative_bias_version=res.authoritative_bias_version + 3)
    r = _run_with_patched_step(mutate)
    assert r["metrics"]["step_metadata_rejects"] >= 1, \
        "a step whose authoritative version disagrees with its snapshot was accepted"
    assert r["metrics"]["published"] == 0


def test_effect_snapshot_must_equal_commit_pre_state():
    # the DCR pre-state must equal the Effect's embedded snapshot: an Effect embedding
    # a WRONG snapshot cannot earn a diagnostic commit even with a valid receipt
    v, coord, pub = _stack()
    eff, receipt = _verified_effect(v, coord, bias_d="WRONG-SNAPSHOT-DIGEST")
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    ctx = T.EffectCommitContext(effect=eff,
                                verifier_receipt_digest=receipt.receipt_digest)
    try:
        coord.commit([it], 0, effect_context=ctx)
        raise AssertionError("Effect with a false embedded snapshot earned a "
                             "DiagnosticCommitReceipt")
    except RejectedBatch as rb:
        assert rb.law == "LAW_DCR_PRE_STATE_MISMATCH", rb.law


# ================================================ 3. exact-type canonical encoding
def test_bytes_and_lookalike_string_do_not_collide():
    # the owner's reproduced collision, exactly
    assert canonical((b"A",)) != canonical(("b'A'",)), \
        "bytes and their str() lookalike still collide"
    assert digest((b"A",)) != digest(("b'A'",))


def test_enum_and_lookalike_string_do_not_collide():
    run = T0.ControlAction.RUN
    assert canonical(run) != canonical("ControlAction.RUN")
    assert canonical(run) != canonical("RUN")
    assert digest((run,)) != digest(("ControlAction.RUN",))


def test_frozenset_replay_is_hashseed_independent():
    code = ("import sys; sys.path.insert(0, r'%s'); "
            "from rc_canonical import digest; "
            "print(digest(frozenset({'gamma','alpha','beta',1,2,(3,'x')})))" % SIM)
    outs = []
    for seed in ("0", "1", "42"):
        import os
        env = dict(os.environ, PYTHONHASHSEED=seed)
        p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env, timeout=60)
        assert p.returncode == 0, p.stderr
        outs.append(p.stdout.strip())
    assert outs[0] == outs[1] == outs[2], \
        f"frozenset digest varies with PYTHONHASHSEED: {outs}"


def test_nested_nan_rejected():
    for bad in (float("nan"), float("inf"), float("-inf")):
        try:
            digest((bad,))
            raise AssertionError(f"non-finite {bad!r} entered a digest inside a tuple")
        except ValueError:
            pass
        try:
            digest({"k": (0, (bad,))})
            raise AssertionError(f"non-finite {bad!r} entered a digest nested deep")
        except ValueError:
            pass


def test_unknown_canonical_type_rejected():
    class Custom:
        pass
    for bad in (Custom(), object(), {1, 2}, memoryview(b"x")):
        try:
            canonical((bad,))
            raise AssertionError(f"{type(bad).__name__} was encoded by an untyped fallback")
        except TypeError:
            pass


def test_distinct_authoritative_states_have_distinct_canonical_bytes():
    pairs = [
        ((b"A",), ("b'A'",)),                       # bytes vs lookalike string
        ((T0.ControlAction.RUN,), ("ControlAction.RUN",)),  # enum vs lookalike
        ((1,), (True,)),                            # int vs bool
        ((1,), (1.0,)),                             # int vs float
        (("1",), (1,)),                             # str vs int
        ((("a", "b"),), (("a,b",),)),               # nested tuple vs joined string
        (frozenset({"a"}), ("a",)),                 # frozenset vs tuple
        ((None,), ("None",)),                       # null vs its name
        ((b"",), ("",)),                            # empty bytes vs empty string
        ({"k": (1,)}, {"k": [1]}),                  # tuple vs list
    ]
    for a, b in pairs:
        assert canonical(a) != canonical(b), f"collision: {a!r} vs {b!r}"
        assert digest(a) != digest(b)


def test_canonical_binds_class_identity_and_enum_value():
    """Internal audit finding (RC-0.4): the enum/record tags used the bare class
    __name__ and dropped the member value, so two DIFFERENT classes sharing a name
    (or two same-named members with different values) collided. Now the qualified
    class identity and the member value are digest-bound."""
    import enum as _enum
    A = _enum.Enum("SameName", {"RUN": "x"})
    B = _enum.Enum("SameName", {"RUN": "y"})     # same class name, different VALUE
    assert canonical(A.RUN) != canonical(B.RUN), "enum member value not digest-bound"
    A.__qualname__, B.__qualname__ = "aud.EnumA", "aud.EnumB"
    C1 = _enum.Enum("SameName", {"RUN": "z"})
    C2 = _enum.Enum("SameName", {"RUN": "z"})    # same name+value, distinct classes
    C1.__qualname__, C2.__qualname__ = "aud.C1", "aud.C2"
    assert canonical(C1.RUN) != canonical(C2.RUN), "enum class identity not digest-bound"

    def make_record(ns):
        @dc.dataclass(frozen=True)
        class Rec:
            x: int
        Rec.__qualname__ = ns + ".Rec"
        return Rec
    R1, R2 = make_record("m1"), make_record("m2")
    assert canonical(R1(1)) != canonical(R2(1)), "record class identity not digest-bound"


def test_episode_id_is_directly_seal_bound():
    """Internal audit finding (RC-0.4): episode_id gates LAW_EPISODE_IDENTITY but a
    zero-commit run's seal was episode-blind (only transitively bound via commits)."""
    reg = SC.Reg().add("e0", "^6_decompose", "intended", PAY)
    e1 = SC.engine([c6("e0")], reg, episode_id="epA", budget=0)   # halts before any commit
    e2 = SC.engine([c6("e0")], reg, episode_id="epB", budget=0)
    e1.run()
    e2.run()
    assert e1.seal() != e2.seal(), "seal blind to episode_id on a zero-commit run"


# ================================================ 4. seal after the transition
def test_no_ready_halt_seal_equals_recomputed_seal():
    # RC-0.4D: a cutoff region now dispatches REPAIR (no halt), so the no-ready halt
    # fixture uses a governance-quarantined route instead (no registry entry, no
    # repairable block, no dispatchable ASOM action -> HALT)
    import dataclasses as _dc
    from rc0_types import Governance
    b = _dc.replace(SC.bias(), governance=Governance(hard_mask=1, quarantined=True))
    e = SC.engine([c6("h0")], SC.Reg().add("h0", "^6_decompose", "intended", PAY),
                  states={**SC.states(), "^6_decompose": b})
    r = e.run()
    assert e.halted and any(ev["event"] == "HALT" for ev in r["events"])
    assert r["trace_digest"] == e.seal(), \
        "no-ready HALT sealed before the final state mutation"


def test_hard_mask_halt_seal_equals_recomputed_seal():
    e = SC.engine([c6("h1")], SC.Reg().add("h1", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"mask": 0}}))
    r = e.run()
    assert e.halted and any(ev["event"] == "HALT" for ev in r["events"])
    assert r["trace_digest"] == e.seal(), \
        "hard-mask HALT sealed before the final state mutation"


def test_budget_halt_seal_equals_recomputed_seal():
    e = SC.engine([c6("h2")], SC.Reg().add("h2", "^6_decompose", "intended", PAY),
                  budget=0)
    r = e.run()
    assert e.halted and any(ev["event"] == "HALT" for ev in r["events"])
    assert r["trace_digest"] == e.seal(), \
        "budget HALT sealed before the final state mutation"


def test_no_state_or_evidence_mutates_after_finalization():
    e = SC.engine([c6("h3")], SC.Reg().add("h3", "^6_decompose", "intended", PAY))
    r = e.run()
    d1 = r["trace_digest"]
    assert d1 == e.seal(), "finalized seal is not the current seal"
    r2 = e.result()
    assert r2["trace_digest"] == d1 and e.seal() == d1, \
        "state or evidence mutated after finalization"


# ================================================ 5. complete runtime snapshot
def test_remaining_queue_payload_change_changes_seal():
    e = SC.engine([c6("q0")], SC.Reg().add("q0", "^6_decompose", "intended", PAY))
    e.remaining_queue = [SC.cause("qX", C6, "payload AAA")]
    s1 = e.seal()
    e.remaining_queue = [SC.cause("qX", C6, "payload BBB")]   # SAME id, new payload
    assert e.seal() != s1, "seal blind to a queued Cause's payload"


def test_remaining_queue_evidence_change_changes_seal():
    e = SC.engine([c6("q1")], SC.Reg().add("q1", "^6_decompose", "intended", PAY))
    e.remaining_queue = [SC.cause("qX", ("structure_cue",), PAY)]
    s1 = e.seal()
    e.remaining_queue = [SC.cause("qX", ("structure_cue", "association_cue"), PAY)]
    assert e.seal() != s1, "seal blind to a queued Cause's evidence"


def test_child_queue_payload_change_changes_seal():
    e = SC.engine([c6("q2")], SC.Reg().add("q2", "^6_decompose", "intended", PAY))
    e.child_queue = [SC.cause("qC", C6, "child AAA")]
    s1 = e.seal()
    e.child_queue = [SC.cause("qC", C6, "child BBB")]         # SAME id, new payload
    assert e.seal() != s1, "seal blind to a queued child Cause's payload"


def test_publication_evidence_change_changes_seal():
    e = SC.engine([c6("q3")], SC.Reg().add("q3", "^6_decompose", "intended", PAY))
    r = e.run()
    assert r["metrics"]["published"] == 1
    s1 = e.seal()
    e.publications[0]["effect_payload"] = "TAMPERED-AFTER-THE-FACT"
    assert e.seal() != s1, "returned publication evidence is not seal-bound"


def test_threshold_change_changes_configuration_seal():
    reg = SC.Reg().add("q4", "^6_decompose", "intended", PAY)
    e1 = SC.engine([c6("q4")], reg, taus=(1.0, 1.0, 1.0))
    e2 = SC.engine([c6("q4")], reg, taus=(2.0, 1.0, 1.0))
    assert e1.seal() != e2.seal(), "seal blind to the readiness thresholds"


def test_verifier_oracle_change_changes_configuration_seal():
    reg1 = SC.Reg().add("q5", "^6_decompose", "intended", PAY)
    reg2 = SC.Reg().add("q5", "^6_decompose", "intended", "totally different words here")
    e1 = SC.engine([c6("q5")], reg1)
    e2 = SC.engine([c6("q5")], reg2)
    assert e1.seal() != e2.seal(), "seal blind to the expected-Effect oracle"
    reg3 = SC.Reg().add("q5", "^6_decompose", "opposite")
    e3 = SC.engine([c6("q5")], reg3)
    assert e1.seal() != e3.seal(), "seal blind to the gold verdict table"


def test_rpm_flag_change_changes_configuration_seal():
    reg = SC.Reg().add("q6", "^6_decompose", "intended", PAY)
    e1 = SC.engine([c6("q6")], reg, rpm_enforcement_enabled=True)
    e2 = SC.engine([c6("q6")], reg, rpm_enforcement_enabled=False)
    assert e1.seal() != e2.seal(), "seal blind to rpm_enforcement_enabled"


def test_ohm_flag_change_changes_configuration_seal():
    reg = SC.Reg().add("q7", "^6_decompose", "intended", PAY)
    e1 = SC.engine([c6("q7")], reg, ohm_enabled=True)
    e2 = SC.engine([c6("q7")], reg, ohm_enabled=False)
    assert e1.seal() != e2.seal(), "seal blind to ohm_enabled"


# ================================================ 6. mutation-status law
def test_mutation_audit_crash_cannot_reuse_stale_report():
    import generate_rc02_receipt as G
    with tempfile.TemporaryDirectory(prefix="rc04_stale_") as tmp:
        here = Path(tmp)
        stale = {"report_id": "rc04_mutation_report", "all_caught": True,
                 "pristine_unchanged": True,
                 "source_tree_digest": "stale-src", "test_tree_digest": "stale-tst",
                 "mutations": [{"applied": True, "caught": True,
                                "semantic_failure": True}]}
        (here / "rc03_mutation_report.json").write_text(json.dumps(stale),
                                                        encoding="utf-8")

        class Crash:
            returncode = 1
            stdout = ""
            stderr = "simulated crash before any report write"

        def crashing_runner(*_a, **_k):
            return Crash()
        rc, report = G.run_fresh_mutation_audit(here, check_only=False,
                                                runner=crashing_runner)
        assert report is None, \
            "a crashed mutation audit fell back to the stale committed report"
        assert not (here / "rc03_mutation_report.json").exists(), \
            "the stale report survived to be reused by a later reader"
        ok, reason = G.mutation_status_law(rc, report, "cur-src", "cur-tst")
        assert not ok and reason == "MUTATION_AUDIT_MISSING_FRESH_REPORT", reason
        # and even a FRESH-looking report for the WRONG tree is refused
        wrong_tree = dict(stale)
        ok2, reason2 = G.mutation_status_law(0, wrong_tree, "cur-src", "cur-tst")
        assert not ok2 and reason2 == "MUTATION_REPORT_SOURCE_TREE_MISMATCH", reason2


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
