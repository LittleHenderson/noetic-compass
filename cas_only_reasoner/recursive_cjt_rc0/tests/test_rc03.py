"""test_rc03.py -- RC-0.3 permanent tests (OWNER DIRECTIVE RC-0.3).

Targets: publication-commit binding, verifier issuance registry, complete Effect
envelope, CJTStep snapshot laundering, complete runtime snapshot seal, split-failure
atomicity, budget/immutability construction. Deterministic, CPU-only.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
sys.path.insert(0, str(SIM))

import rc0_types as T0             # noqa: E402
import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,  # noqa: E402
                              PublicationRefused, RejectedBatch)
from rc01_types import canonical  # noqa: E402

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def _stack(gold, expected):
    """verifier + state coordinator + publication coordinator, wired."""
    v = E.SealedVerifier(gold, expected, "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=v.validator())
    pub = PublicationCoordinator("ep0", coord)
    return v, coord, pub


def _effect(payload="parts[alpha|beta|gamma|delta]", tick=0, bias_v=0, bias_d="d0"):
    return T.EffectCandidate("^6_decompose", "x0", "decompose", payload,
                             originating_tick=tick, base_bias_version=bias_v,
                             base_bias_digest=bias_d)


def _committed_flow(v, coord):
    """Run the legitimate verify -> commit flow; returns (effect, receipt, dcr)."""
    causeX = SC.cause("x0", C6, PAY)
    eff = T.EffectCandidate("^6_decompose", "x0", "decompose",
                            "parts[alpha|beta|gamma|delta]", originating_tick=0,
                            base_bias_version=coord.version("^6_decompose"),
                            base_bias_digest=coord.get_digest("^6_decompose"))
    receipt = v.verify(causeX, eff, 0)
    coord.register_verifier_receipt(receipt)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome=receipt.verdict)
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    ctx = T.EffectCommitContext(effect=eff,
                                verifier_receipt_digest=receipt.receipt_digest)
    dcr = coord.commit([it], 0, effect_context=ctx)
    return eff, receipt, dcr


GOLD = {("x0", "^6_decompose"): "intended"}
EXP = {("x0", "^6_decompose"): "parts[alpha|beta|gamma|delta]"}


# ---------------------------------------------------- 1. publication-commit binding
def test_publication_requires_diagnostic_commit_receipt():
    # valid intended receipt registered, NO state commit, bogus base state,
    # direct publication call -> typed refusal
    v, coord, pub = _stack(GOLD, EXP)
    causeX = SC.cause("x0", C6, PAY)
    eff = _effect(bias_d=coord.get_digest("^6_decompose"))
    receipt = v.verify(causeX, eff, 0)
    coord.register_verifier_receipt(receipt)
    intent = T.EffectPublicationIntent(
        "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=999, base_state_digest="garbage",
        diagnostic_commit_digest="")
    try:
        pub.commit_publication(intent)
        raise AssertionError("published without any diagnostic commit")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_NO_DIAGNOSTIC_COMMIT"


def test_pub_law_stale_state():
    v, coord, pub = _stack(GOLD, EXP)
    eff, receipt, dcr = _committed_flow(v, coord)
    intent = T.EffectPublicationIntent(
        "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version + 7,
        base_state_digest="not-the-pre-state", diagnostic_commit_digest=dcr.commit_digest)
    try:
        pub.commit_publication(intent)
        raise AssertionError("stale base state accepted")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_STALE_STATE"


def test_pub_law_state_moved_after_commit():
    v, coord, pub = _stack(GOLD, EXP)
    eff, receipt, dcr = _committed_flow(v, coord)
    # a SECOND commit moves the authoritative state past the named commit
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "memory", ("later",),
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"))
    coord.commit([it], 0)
    intent = T.EffectPublicationIntent(
        "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version,
        base_state_digest=dcr.pre_state_digest, diagnostic_commit_digest=dcr.commit_digest)
    try:
        pub.commit_publication(intent)
        raise AssertionError("publication skipped past an intervening state change")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_STATE_MOVED"


def test_authority_level_only_intended_publishes():
    gold = {("x0", "^6_decompose"): "opposite"}
    v, coord, pub = _stack(gold, {})
    eff, receipt, dcr = _committed_flow(v, coord)
    assert receipt.verdict == "opposite"
    intent = T.EffectPublicationIntent(
        "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "opposite",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version,
        base_state_digest=dcr.pre_state_digest, diagnostic_commit_digest=dcr.commit_digest)
    try:
        pub.commit_publication(intent)
        raise AssertionError("non-intended verdict published at the authority level")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_ONLY_INTENDED_PUBLISHES"


def test_happy_path_publication_with_commit_receipt():
    v, coord, pub = _stack(GOLD, EXP)
    eff, receipt, dcr = _committed_flow(v, coord)
    assert isinstance(dcr, T.DiagnosticCommitReceipt)
    intent = T.EffectPublicationIntent(
        "ep0", 0, "x0", eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version,
        base_state_digest=dcr.pre_state_digest, diagnostic_commit_digest=dcr.commit_digest)
    assert pub.commit_publication(intent) == "PUBLISHED"
    # both receipts consumed exactly once
    try:
        pub.commit_publication(intent)
        raise AssertionError("receipts reusable")
    except PublicationRefused as pr:
        assert pr.law in ("PUB_LAW_RECEIPT_CONSUMED", "PUB_LAW_COMMIT_RECEIPT_CONSUMED")


# ---------------------------------------------------- 2. issuance registry
def test_old_public_seal_formula_rejected():
    v, coord, pub = _stack({}, {})
    causeX = SC.cause("x9", C6, PAY)
    eff = T.EffectCandidate("^6_decompose", "x9", "decompose", "parts[q]",
                            originating_tick=0)
    # the attacker computes the RC-0.2 public formula EXACTLY
    secret = hashlib.sha256("examiner::ep0::sealed_examiner_v1".encode()).hexdigest()
    forged = T.VerifierReceipt(
        episode_id="ep0", tick=0, cause_id="x9", effect_digest=eff.effect_digest,
        producer_expert_id="^6_decompose", verdict="intended",
        examiner_id="sealed_examiner_v1", receipt_version=1)
    forged_sealed = T.VerifierReceipt(
        episode_id="ep0", tick=0, cause_id="x9", effect_digest=eff.effect_digest,
        producer_expert_id="^6_decompose", verdict="intended",
        examiner_id="sealed_examiner_v1", receipt_version=1,
        seal=hashlib.sha256((secret + canonical(forged.content)).encode()).hexdigest())
    try:
        coord.register_verifier_receipt(forged_sealed)
        raise AssertionError("old public-formula seal accepted")
    except RejectedBatch as rb:
        assert rb.law == "LAW_RECEIPT_NOT_ISSUED"


# ---------------------------------------------------- 3. complete Effect envelope
def test_wrong_op_kind_refused():
    v, coord, pub = _stack(GOLD, EXP)
    causeX = SC.cause("x0", C6, PAY)
    rogue = T.EffectCandidate("^6_decompose", "x0", "erase_memory",
                              "parts[alpha|beta|gamma|delta]", originating_tick=0)
    receipt = v.verify(causeX, rogue, 0)
    assert receipt.verdict == "off_axis", "correct payload with wrong op_kind accepted"


def test_stale_effect_tick_refused():
    v, coord, pub = _stack(GOLD, EXP)
    causeX = SC.cause("x0", C6, PAY)
    old = _effect(tick=0)
    receipt = v.verify(causeX, old, 3)     # re-presented at a later tick
    assert receipt.verdict == "off_axis", "stale Effect earned a fresh receipt"


# ---------------------------------------------------- 4. CJTStep snapshot laundering
def test_stale_cjtstep_result_rejected():
    original = E.cjt_step

    def stale_step(expert_id, cause, bias, allocation, budget, tick, bias_version,
                   bias_digest=""):
        res = original(expert_id, cause, bias, allocation, budget, tick, bias_version,
                       bias_digest=bias_digest)
        import dataclasses as dc
        return dc.replace(res, base_state_version=999, base_state_digest="stale")
    E.cjt_step = stale_step
    try:
        r = SC.engine([c6("st0")], SC.Reg().add("st0", "^6_decompose", "intended", PAY)).run()
    finally:
        E.cjt_step = original
    assert r["metrics"]["step_metadata_rejects"] >= 1, "stale step laundered"
    assert r["metrics"]["published"] == 0


# ---------------------------------------------------- 5. complete runtime snapshot
def test_seal_binds_consumed_receipts():
    eng = SC.engine([c6("s0")], SC.Reg().add("s0", "^6_decompose", "intended", PAY))
    eng.run()
    seal1 = eng.seal()
    eng.pubcoord._consumed.add("injected-consumed-entry")
    assert eng.seal() != seal1, "seal blind to the consumed-receipt registry"


def test_seal_binds_each_runtime_family():
    def fresh():
        e = SC.engine([c6("f0")], SC.Reg().add("f0", "^6_decompose", "intended", PAY))
        e.run()
        return e
    mutations = {
        "child_queue": lambda e: e.child_queue.append(c6("ghost")),
        "cancelled": lambda e: e.cancelled_causes.add("ghost"),
        "quarantine": lambda e: e.quarantine_registry.update({"^8_trigger": 9}),
        "halted": lambda e: setattr(e, "halted", not e.halted),
        "branch_count": lambda e: setattr(e, "total_branches_opened",
                                          e.total_branches_opened + 1),
        "budget": lambda e: e.budget.spend(1),
        "reopen_schedule": lambda e: e.reopen_events.update({99: "^2_attract"}),
        "consecutive": lambda e: e.consecutive.update({"^8_trigger": 7}),
        "invalidation_events": lambda e: e.invalidation_events.add(("^8_trigger", "POWER")),
    }
    base_seal = fresh().seal()
    for fam, mutate in mutations.items():
        e = fresh()
        mutate(e)
        assert e.seal() != base_seal, f"seal blind to runtime family: {fam}"
    # and the snapshot names every required family
    snap = fresh().runtime_snapshot()
    for key in ("remaining_queue", "child_queue", "child_to_frame", "cancelled_causes",
                "split_frames", "repair_frames", "active_subgoals", "return_addresses",
                "quarantine", "verifier_issued_registry", "coordinator_receipt_registry",
                "commit_receipt_registry", "publication_consumed", "publication_ledger",
                "budget", "branches", "invalidation_events", "invalidations_consumed",
                "reopen_schedule", "repair_dependency_graph", "consecutive",
                "exec_counts", "halted", "final_states", "commits", "events",
                "alloc", "metrics"):
        assert key in snap, f"runtime snapshot missing {key}"


# ---------------------------------------------------- 6. split-failure atomicity
def test_split_child_failure_no_orphan_publication():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "split_child_failure_no_orphan")
    e = sc["build"]()
    r = e.run()
    assert r["metrics"]["published"] == 0, "a sibling escaped and published"
    assert r["metrics"]["children_cancelled"] >= 1
    assert r["metrics"]["split_frames_failed"] == 1
    names = [ev["event"] for ev in r["events"]]
    assert "SPLIT_FAILED" in names and "CHILD_CANCELLED" in names
    assert "SPLIT_RESUMED" not in names
    assert e.split_frames == {} and e.child_to_frame == {}, "frame not settled"


# ---------------------------------------------------- 7. budget + immutability
def test_compute_budget_construction_guarded():
    for bad in (lambda: T.ComputeBudget("anything", 3, 3),
                lambda: T.ComputeBudget("CJT_EXPERT_EVALUATION", -10, 0),
                lambda: T.ComputeBudget("CJT_EXPERT_EVALUATION", 3, 5),
                lambda: T.ComputeBudget.make(-1),
                lambda: T.ComputeBudget.make(True)):
        try:
            bad()
            raise AssertionError("invalid budget construction accepted")
        except (TypeError, ValueError):
            pass
    b = T.ComputeBudget.make(3)
    for attack in ("left", "total", "unit"):
        try:
            setattr(b, attack, 999)
            raise AssertionError(f"direct mutation of {attack} allowed")
        except AttributeError:
            pass
    assert b.left == 3 and b.total == 3


def test_nested_custom_mutable_rejected():
    class Evil:
        pass
    try:
        T0.RPMState(desire=1.0, wisdom=1.0, power=1.0, acquired=(Evil(),))
        raise AssertionError("custom mutable object accepted inside a tuple")
    except TypeError:
        pass
    try:
        T.CJTStepResult(
            effect_candidate=_effect(), observations=(Evil(),), proposed_updates=(),
            actual_compute_used=1, producer_expert_id="^6_decompose",
            originating_tick=0, authoritative_bias_version=0)
        raise AssertionError("custom mutable object accepted in observations")
    except TypeError:
        pass


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
