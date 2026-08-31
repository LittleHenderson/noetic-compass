"""test_rc02.py -- RC-0.2 permanent tests (OWNER DIRECTIVE RC-0.2 section 11).

Every test here targets a defect the owner's audit of 60b36e06 confirmed. Deterministic,
CPU-only, no neural network.
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
sys.path.insert(0, str(SIM))

import rc0_types as T0             # noqa: E402
import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402
import rc01_experts as X           # noqa: E402
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,  # noqa: E402
                              PublicationRefused, RejectedBatch)

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)


def eng(causes, reg, **kw):
    return SC.engine(causes, reg, **kw)


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


# ------------------------------------------------- 1. publication authority
def test_uncommitted_intended_effect_cannot_publish():
    r = eng([c6("u0")], SC.Reg().add("u0", "^6_decompose", "intended", PAY),
            commit_verdicts=False).run()
    assert r["metrics"]["published"] == 0, "uncommitted verdict published"
    assert r["metrics"]["refused"] == 1
    assert r["publications"][0]["law"] == "PUB_LAW_UNCOMMITTED_VERDICT"
    assert all(d["decision"] != "PUBLISHED" for d in r["publication_ledger"])


def test_failed_state_commit_cannot_leave_publication():
    e = eng([c6("f0")], SC.Reg().add("f0", "^6_decompose", "intended", PAY))
    original = e.coord.commit

    def sabotage(intents, tick, **kw):   # the diagnostic commit fails (RC-0.3 signature)
        raise RejectedBatch("LAW_INJECTED_FAILURE", "audit sabotage")
    e.coord.commit = sabotage
    r = e.run()
    e.coord.commit = original
    assert r["metrics"]["published"] == 0, "publication survived a failed state commit"
    assert all(d["decision"] != "PUBLISHED" for d in r["publication_ledger"])


def test_publication_intent_is_actually_consumed():
    e = eng([c6("p0")], SC.Reg().add("p0", "^6_decompose", "intended", PAY))
    r = e.run()
    assert r["metrics"]["published"] == 1
    pub = [d for d in e.pubcoord.ledger if d["decision"] == "PUBLISHED"][0]
    # replaying the SAME publication intent must be refused: receipt consumed
    receipt = e.coord.get_receipt(pub["receipt"])
    intent = T.EffectPublicationIntent(
        episode_id="ep0", tick=pub["tick"], cause_id=pub["cause"],
        effect_digest=pub["effect_digest"], producer_expert_id=pub["producer"],
        verdict="intended", verifier_receipt_digest=pub["receipt"],
        base_state_version=0, base_state_digest="d")
    try:
        e.pubcoord.commit_publication(intent)
        raise AssertionError("consumed receipt allowed a second publication")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_RECEIPT_CONSUMED"
    assert receipt is not None


# ------------------------------------------------- 2. semantic verification
def test_wrong_effect_payload_refused():
    # correct expert, corrupted payload (theta mode mismatch vs registered oracle)
    r = eng([c6("wp0")], SC.Reg().add("wp0", "^6_decompose", "intended", PAY),
            states=SC.states(**{"^6_decompose": {"theta": ("K_coarse",)}})).run()
    assert r["metrics"]["published"] == 0
    assert r["metrics"]["off_axis_effects"] == 1, "corrupted payload not caught"
    assert r["publications"][0]["status"] == "REFUSED"


def test_wrong_effect_cause_id_refused():
    verifier = E.SealedVerifier({("a0", "^6_decompose"): "intended"},
                                {("a0", "^6_decompose"): "parts[x]"}, "ep0")
    causeA = SC.cause("a0", C6, "x")
    rogue = T.EffectCandidate(producer_expert_id="^6_decompose", cause_id="OTHER",
                              op_kind="decompose", payload="parts[x]")
    receipt = verifier.verify(causeA, rogue, 0)
    assert receipt.verdict == "off_axis", "cross-cause Effect accepted"


def test_verifier_receipt_binds_effect_digest():
    verifier = E.SealedVerifier({("b0", "^6_decompose"): "intended"},
                                {("b0", "^6_decompose"): "parts[x]"}, "ep0")
    causeB = SC.cause("b0", C6, "x")
    good = T.EffectCandidate("^6_decompose", "b0", "decompose", "parts[x]")
    receipt = verifier.verify(causeB, good, 0)
    assert receipt.effect_digest == good.effect_digest
    other = T.EffectCandidate("^6_decompose", "b0", "decompose", "parts[TAMPERED]")
    assert receipt.effect_digest != other.effect_digest, "digest ignores payload"
    # a publication intent citing the good receipt for the tampered effect is refused
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=verifier.validator())
    coord.register_verifier_receipt(receipt)
    pubc = PublicationCoordinator("ep0", coord)
    intent = T.EffectPublicationIntent("ep0", 0, "b0", other.effect_digest,
                                       "^6_decompose", "intended",
                                       receipt.receipt_digest, 0, "d")
    try:
        pubc.commit_publication(intent)
        raise AssertionError("receipt accepted for a different Effect")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_RECEIPT_EFFECT"


def test_registered_fake_receipt_rejected():
    verifier = E.SealedVerifier({}, {}, "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=verifier.validator())
    # (a) raw strings are dead
    try:
        coord.register_verifier_receipt("deadbeef")
        raise AssertionError("raw-string receipt registered")
    except RejectedBatch as rb:
        assert rb.law == "LAW_TYPED_RECEIPT"
    # (b) a self-built receipt (no examiner seal) is rejected
    fake = T.VerifierReceipt(episode_id="ep0", tick=0, cause_id="x",
                             effect_digest="d", producer_expert_id="^6_decompose",
                             verdict="intended", examiner_id="sealed_examiner_v1",
                             receipt_version=1, seal="forged")
    try:
        coord.register_verifier_receipt(fake)
        raise AssertionError("forged-seal receipt registered")
    except RejectedBatch as rb:
        assert rb.law == "LAW_RECEIPT_NOT_ISSUED"


def test_receipt_cannot_be_reused():
    # cross-tick reuse at the STATE coordinator: receipt.tick must equal commit tick
    verifier = E.SealedVerifier({("r0", "^6_decompose"): "intended"},
                                {("r0", "^6_decompose"): "parts[x]"}, "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=verifier.validator())
    causeR = SC.cause("r0", C6, "x")
    eff = T.EffectCandidate("^6_decompose", "r0", "decompose", "parts[x]")
    receipt = verifier.verify(causeR, eff, 0)
    coord.register_verifier_receipt(receipt)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 5, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    try:
        coord.commit([it], 5)   # receipt was issued for tick 0
        raise AssertionError("cross-tick receipt accepted")
    except RejectedBatch as rb:
        assert rb.law == "LAW_RECEIPT_TICK"


def test_semantic_outcome_update_requires_receipt():
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           0, coord.get_digest("^6_decompose"))
    try:
        coord.commit([it], 0)
        raise AssertionError("semantic outcome written without a receipt")
    except RejectedBatch as rb:
        assert rb.law == "LAW_VERIFIER_RECEIPT_REQUIRED"


# ------------------------------------------------- 3. seals and digests
def test_intent_digest_changes_with_new_value():
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    kw = dict(episode_id="ep0", tick=0, producer_id="kernel", expert_id="^6_decompose",
              fld="memory", base_state_version=0,
              base_state_digest=coord.get_digest("^6_decompose"))
    a = T.VersionedIntent(new_value=("A",), **kw)
    b = T.VersionedIntent(new_value=("B",), **kw)
    assert a.intent_digest != b.intent_digest, "new_value collision (owner-reproduced defect)"


def test_final_state_change_changes_trace_digest():
    # two runs identical except one committed value (different theta -> different final
    # memory/effect) must produce different seals; also the commit trace itself carries
    # pre/post digests so the same-metadata different-value commit is distinguishable
    r1 = eng([c6("s0")], SC.Reg().add("s0", "^6_decompose", "intended", PAY)).run()
    r2 = eng([c6("s0")], SC.Reg().add("s0", "^6_decompose", "intended", PAY),
             states=SC.states(**{"^6_decompose": {"theta": ("K_coarse",)}})).run()
    assert r1["trace_digest"] != r2["trace_digest"]
    assert r1["final_states"] != r2["final_states"]
    # coordinator-level: same metadata, different values -> different post digests
    ca = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    cb = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    kw = dict(episode_id="ep0", tick=0, producer_id="kernel", expert_id="^6_decompose",
              fld="memory", base_state_version=0,
              base_state_digest=ca.get_digest("^6_decompose"))
    ca.commit([T.VersionedIntent(new_value=("A",), **kw)], 0)
    cb.commit([T.VersionedIntent(new_value=("B",), **kw)], 0)
    assert ca.trace != cb.trace, "commit traces identical for different committed values"
    assert ca.seal() != cb.seal()


# ------------------------------------------------- 4. Bias-conditioned CJTStep
def test_bias_change_affects_cjtstep_or_recurrent_claim_withdrawn():
    b_id = SC.bias(theta=("K_identity",))
    b_co = SC.bias(theta=("K_coarse",))
    e1 = X.cjt_step("^6_decompose", c6("bc0"), b_id, 1.0, T.ComputeBudget.make(1), 0, 0)
    e2 = X.cjt_step("^6_decompose", c6("bc0"), b_co, 1.0, T.ComputeBudget.make(1), 0, 0)
    assert e1.effect_candidate.payload != e2.effect_candidate.payload, \
        "Bias does not condition the Effect -- the recurrent claim would be withdrawn"
    # and CJTStep PROPOSES real updates (not a decorative empty tuple)
    assert e1.proposed_updates, "CJTStep proposes no updates"
    fld, value, reason = e1.proposed_updates[0]
    assert fld == "memory" and isinstance(value, tuple)


# ------------------------------------------------- 5. CAP
def test_single_route_cap_does_not_fake_enforcement():
    r = eng([c6("sr0")], SC.Reg().add("sr0", "^6_decompose", "intended", PAY),
            states=SC.states(**{"^6_decompose": {"region": "saturation"}})).run()
    assert r["metrics"]["cap_events"] == 0, "CAP_ENFORCED faked on a single route"
    assert r["metrics"]["deferred_causes"] == 1
    assert r["metrics"]["executions"] == 0


def test_multiple_caps_all_remain_bounded():
    scores = {"a": 10.0, "b": 8.0, "c": 1.0}
    alloc, applied = E.waterfill(scores, {"a", "b"}, E.CAP_ALLOCATION_LIMIT)
    assert applied
    assert alloc["a"] <= E.CAP_ALLOCATION_LIMIT + 1e-9
    assert alloc["b"] <= E.CAP_ALLOCATION_LIMIT + 1e-9
    assert abs(sum(alloc.values()) - 1.0) <= 1e-9
    # engine-level: capped expert stays bounded in every emitted allocation
    r = eng([SC.cause("mc0", ("structure_cue", "association_cue"), PAY)],
            SC.Reg().add("mc0", "^8_trigger", "intended", PAY),
            states=SC.states(**{"^6_decompose": {"region": "saturation", "desire": 9.0}})).run()
    for a in r["allocations"]:
        if a and "^6_decompose" in a:
            assert a["^6_decompose"] <= E.CAP_ALLOCATION_LIMIT + 1e-9


# ------------------------------------------------- 6. SPLIT return path
def test_split_parent_resumes_and_combines_children():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "split_resume_combine")
    e = sc["build"]()
    r = e.run()
    assert r["metrics"]["split_frames_resumed"] == 1
    names = [ev["event"] for ev in r["events"]]
    assert "SPLIT" in names and "CHILD_COLLECTED" in names and "SPLIT_RESUMED" in names
    combined = [p for p in r["publications"] if p["cause"] == "sp0"]
    assert combined and combined[0]["status"] == "PUBLISHED"
    assert combined[0]["effect_payload"] == "parts[a|b|c] + parts[d|e|f]"
    assert e.split_frames == {}, "return address not consumed"


# ------------------------------------------------- 7. multi-prerequisite RPM
def test_two_missing_prerequisites_complete():
    r = eng([c6("t2")], SC.Reg().add("t2", "^6_decompose", "intended", PAY),
            states=SC.states(**{"^6_decompose": {"wisdom": 0.0, "power": 0.0}})).run()
    assert r["metrics"]["repairs_completed"] == 2
    assert r["metrics"]["published"] == 1, "fully repaired cause was stranded"


def test_three_missing_prerequisites_complete_or_halt_typed():
    # D missing too -> the Desire law governs: deprioritize, never invent relevance
    r = eng([c6("t3")], SC.Reg().add("t3", "^6_decompose", "intended", PAY),
            states=SC.states(**{"^6_decompose": {"desire": 0.0, "wisdom": 0.0,
                                                  "power": 0.0}})).run()
    assert r["metrics"]["desire_deprioritized"] == 1, "typed outcome missing"
    assert r["metrics"]["published"] == 0
    # and a bounded retry limit exists: unrepairable-but-repairable-looking loops halt typed
    r2 = eng([c6("t4")], SC.Reg(),
             states=SC.states(**{"^6_decompose": {"wisdom": 0.0}}),
             max_total_branches=0).run()
    assert r2["metrics"]["total_branch_limit_hits"] >= 1


# ------------------------------------------------- 8. numeric / immutability
def test_negative_budget_spend_rejected():
    b = T.ComputeBudget.make(3)
    try:
        b.spend(-1)
        raise AssertionError("spend(-1) accepted")
    except (TypeError, ValueError):
        pass
    assert b.left == 3, "budget mutated by a rejected spend"


def test_boolean_budget_spend_rejected():
    b = T.ComputeBudget.make(3)
    try:
        b.spend(True)
        raise AssertionError("spend(True) accepted")
    except (TypeError, ValueError):
        pass
    assert b.left == 3


def test_region_nan_and_bool_rejected():
    for bad in ((float("nan"), 0.5, 0.25, 0.25), (True, 0.0, 0.0, 0.0),
                (float("inf"), 0.0, 0.0, 0.0)):
        try:
            T0.RegionRecord(region_posterior=bad, committed_region="active")
            raise AssertionError(f"RegionRecord accepted {bad}")
        except (TypeError, ValueError):
            pass


def test_governance_negative_limits_rejected():
    for kw in (dict(hard_mask=True), dict(hard_mask=1, max_depth=-1),
               dict(hard_mask=1, max_branches=-2), dict(hard_mask=1, max_depth=True)):
        try:
            T0.Governance(**kw)
            raise AssertionError(f"Governance accepted {kw}")
        except (TypeError, ValueError):
            pass


def test_nested_bias_state_cannot_mutate():
    # mutable containers are rejected at construction, deeply
    try:
        SC.bias().__class__(substrate=(["mutable"],), memory=(), rpm=SC.bias().rpm,
                            record=SC.bias().record, theta=("K_identity",),
                            governance=SC.bias().governance)
        raise AssertionError("nested list accepted into BiasState")
    except TypeError:
        pass
    try:
        T0.RPMState(desire=1.0, wisdom=1.0, power=1.0, acquired=(["x"],))
        raise AssertionError("nested list accepted into RPMState")
    except TypeError:
        pass
    b = SC.bias()
    try:
        b.rpm = T0.RPMState(desire=9.0, wisdom=9.0, power=9.0)  # type: ignore[misc]
        raise AssertionError("field reassignment allowed")
    except dataclasses.FrozenInstanceError:
        pass


# ------------------------------------------------- 9. receipt generator
def test_receipt_generator_reproduces_raw_status():
    import os
    gen = Path(__file__).resolve().parent.parent / "generate_rc02_receipt.py"
    assert gen.exists(), "receipt generator program is not committed"
    if os.environ.get("RC02_IN_GENERATOR") == "1":
        return  # inside the generator's own suite run: recursion guard, existence proven
    out = subprocess.run([sys.executable, str(gen), "--check-only"],
                         capture_output=True, text=True, cwd=str(gen.parent))
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.strip().splitlines()
    assert any(line.startswith("STATUS:") for line in lines), "generator emits no status"
    status = [line for line in lines if line.startswith("STATUS:")][-1].split(":", 1)[1].strip()
    assert status in ("DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS",
                      "GATE0_INCONCLUSIVE", "GATE0_REFUTED")


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
