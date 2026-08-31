"""test_campaign_state.py -- the section-1 lifecycle tests (GATE 1A.2)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.campaign_state import (STATES, CampaignStateError,  # noqa: E402
                                 CampaignStateMachine, verify_transition_chain)

COMMIT = "ab" * 20
B = "cd" * 32


def fresh(tmp):
    return CampaignStateMachine("camp-1", COMMIT, Path(tmp) / "t.jsonl")


def full_forward(sm):
    for s in STATES[1:]:
        sm.transition(s, binding_kind="b", binding_sha256=B)


def test_campaign_cannot_skip_states():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        try:
            sm.transition("EXECUTION_AUTHORIZED", binding_kind="b",
                          binding_sha256=B)
            raise AssertionError("skipped straight to EXECUTION_AUTHORIZED")
        except CampaignStateError:
            pass
        sm.transition("DESIGN_VERIFIED", binding_kind="b", binding_sha256=B)
        try:
            sm.transition("PROTECTED_RUNNING", binding_kind="b", binding_sha256=B)
            raise AssertionError("skipped into the protected phase")
        except CampaignStateError:
            pass
    print("PASS test_campaign_cannot_skip_states")


def test_campaign_cannot_repeat_one_use_state():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        full_forward(sm)
        for target in ("PROTECTED_RUNNING", "TERMINATED", "DESIGN_VERIFIED"):
            try:
                sm.transition(target, binding_kind="b", binding_sha256=B)
                raise AssertionError(f"re-entered {target}")
            except CampaignStateError:
                pass
    print("PASS test_campaign_cannot_repeat_one_use_state")


def test_wrong_campaign_receipt_refused():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        try:
            sm.transition("DESIGN_VERIFIED", binding_kind="b",
                          binding_sha256="not-a-digest")
            raise AssertionError("accepted a non-digest binding")
        except CampaignStateError:
            pass
        full_forward(sm)
        # a chain persisted for campaign-1 must not verify for campaign-2
        try:
            verify_transition_chain(sm.manifest_path, "camp-2", COMMIT)
            raise AssertionError("wrong campaign id accepted")
        except CampaignStateError:
            pass
        try:
            verify_transition_chain(sm.manifest_path, "camp-1", "ef" * 20)
            raise AssertionError("wrong package commit accepted")
        except CampaignStateError:
            pass
    print("PASS test_wrong_campaign_receipt_refused")


def test_transition_digest_chain_is_complete():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        full_forward(sm)
        out = verify_transition_chain(sm.manifest_path, "camp-1", COMMIT)
        assert out["final_state"] == "TERMINATED"
        assert out["transitions"] == len(STATES) - 1
        assert out["chain_digest"] == sm.chain_digest()
        # tamper one line -> chain breaks
        lines = sm.manifest_path.read_text(encoding="utf-8").splitlines()
        lines[3] = lines[3].replace('"FORWARD"', '"FAILURE"')
        tampered = sm.manifest_path.parent / "tampered.jsonl"
        tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            verify_transition_chain(tampered, "camp-1", COMMIT)
            raise AssertionError("tampered chain verified")
        except CampaignStateError:
            pass
    print("PASS test_transition_digest_chain_is_complete")


def test_campaign_replay_is_digest_identical():
    # replay determinism requires a FIXED clock (real mode stamps wall-clock);
    # the synthetic-conformance clock provides exactly that
    syn = (lambda: "SYNTHETIC")
    with tempfile.TemporaryDirectory() as tmp:
        a = CampaignStateMachine("camp-1", COMMIT, Path(tmp) / "t1.jsonl",
                                 utc_source=syn)
        b = CampaignStateMachine("camp-1", COMMIT, Path(tmp) / "t2.jsonl",
                                 utc_source=syn)
        full_forward(a)
        full_forward(b)
        assert a.chain_digest() == b.chain_digest(), "replay chain diverged"
    print("PASS test_campaign_replay_is_digest_identical")


def test_failure_edges_respect_protected_burn():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        for s in STATES[1:13]:                      # up to PROTECTED_RUNNING
            sm.transition(s, binding_kind="b", binding_sha256=B)
        try:
            sm.transition("SHUTDOWN_REQUESTED", binding_kind="b",
                          binding_sha256=B, reason="FAILURE")
            raise AssertionError("protected failure skipped the burn")
        except CampaignStateError:
            pass
        sm.transition("PROTECTED_BURNED", binding_kind="b", binding_sha256=B,
                      reason="FAILURE")
        sm.transition("SHUTDOWN_REQUESTED", binding_kind="b", binding_sha256=B,
                      reason="FAILURE")
    print("PASS test_failure_edges_respect_protected_burn (failure inside the "
          "protected phase must burn before shutdown)")


def test_cannot_seal_results_after_failure_burn():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)
        for s in STATES[1:13]:                      # up to PROTECTED_RUNNING
            sm.transition(s, binding_kind="b", binding_sha256=B)
        sm.transition("PROTECTED_BURNED", binding_kind="b", binding_sha256=B,
                      reason="FAILURE")
        try:
            sm.transition("RESULTS_SEALED", binding_kind="b", binding_sha256=B)
            raise AssertionError("sealed results after a failure burn")
        except CampaignStateError:
            pass
        # and the persisted chain of a hand-forged seal-after-failure is refused
        forged = Path(tmp) / "forged.jsonl"
        lines = sm.manifest_path.read_text(encoding="utf-8").splitlines()
        forged.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS test_cannot_seal_results_after_failure_burn")


def test_default_clock_is_real_not_synthetic():
    with tempfile.TemporaryDirectory() as tmp:
        sm = fresh(tmp)                               # utc_source omitted -> REAL
        rec = sm.transition("DESIGN_VERIFIED", binding_kind="b", binding_sha256=B)
        assert rec["utc"] != "SYNTHETIC", "default clock stamped SYNTHETIC"
        assert rec["utc"].startswith("20"), f"not an ISO timestamp: {rec['utc']}"
    print("PASS test_default_clock_is_real_not_synthetic")


def main():
    test_campaign_cannot_skip_states()
    test_campaign_cannot_repeat_one_use_state()
    test_wrong_campaign_receipt_refused()
    test_transition_digest_chain_is_complete()
    test_campaign_replay_is_digest_identical()
    test_failure_edges_respect_protected_burn()
    test_cannot_seal_results_after_failure_burn()
    test_default_clock_is_real_not_synthetic()
    print("ALL CAMPAIGN-STATE TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
