"""test_protected_lock.py -- the section-7 one-use protected-campaign lock tests."""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.protected_lock import (LocalProtectedLock,  # noqa: E402
                                 ProtectedLockViolation)

BIND = {"execution_approval_sha256": "aa" * 32, "package_commit_sha": "ab" * 20,
        "protected_derivation": "PUBLIC_SEED_20260831",
        "claimant_identity": "TEST", "claim_utc": "SYNTHETIC"}


def test_second_protected_read_refused():
    with tempfile.TemporaryDirectory() as tmp:
        lock = LocalProtectedLock(Path(tmp))
        lock.claim("c1", **BIND)
        lock.burn("c1", final_state_reason="SUCCESS",
                  result_or_failure_sha256="cc" * 32)
        try:
            lock.claim("c1", **BIND)
            raise AssertionError("second protected read allowed")
        except ProtectedLockViolation as exc:
            assert "PROTECTED_ALREADY_BURNED" in str(exc)
    print("PASS test_second_protected_read_refused")


def test_failed_and_interrupted_runs_still_burn():
    with tempfile.TemporaryDirectory() as tmp:
        lock = LocalProtectedLock(Path(tmp))
        lock.claim("c2", **BIND)
        lock.burn("c2", final_state_reason="FAILURE:RuntimeError",
                  result_or_failure_sha256="dd" * 32)     # failure path burns
        assert lock.state("c2") == "PROTECTED_BURNED"
        lock2 = LocalProtectedLock(Path(tmp))             # fresh process view
        lock2.claim("c3", **BIND)                         # interruption: claimed,
        lock3 = LocalProtectedLock(Path(tmp))             # a NEW process must
        lock3.burn("c3", final_state_reason="FAILURE:Interrupted",  # still burn
                   result_or_failure_sha256="ee" * 32)
        assert lock3.state("c3") == "PROTECTED_BURNED"
    print("PASS test_failed_protected_run_still_burns")
    print("PASS test_interrupted_protected_run_still_burns")


def test_two_processes_cannot_claim_same_campaign():
    with tempfile.TemporaryDirectory() as tmp:
        results = []

        def try_claim(i):
            lock = LocalProtectedLock(Path(tmp))          # separate instances
            try:
                lock.claim("c4", **BIND)
                return "CLAIMED"
            except ProtectedLockViolation:
                return "REFUSED"

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(try_claim, range(8)))
        assert results.count("CLAIMED") == 1 and results.count("REFUSED") == 7, \
            f"atomicity broken: {results}"
    print("PASS test_two_processes_cannot_claim_same_campaign "
          "(8 concurrent claimants, exactly 1 wins)")


def test_protected_state_is_receipt_bound():
    with tempfile.TemporaryDirectory() as tmp:
        lock = LocalProtectedLock(Path(tmp))
        claim = lock.claim("c5", **BIND)
        assert claim["execution_approval_sha256"] == BIND["execution_approval_sha256"]
        burn = lock.burn("c5", final_state_reason="SUCCESS",
                         result_or_failure_sha256="ff" * 32)
        for field in ("campaign_id", "execution_approval_sha256",
                      "package_commit_sha", "protected_derivation",
                      "claimant_identity", "claim_utc", "state",
                      "final_state_reason", "result_or_failure_sha256",
                      "lock_receipt_sha256"):
            assert field in burn, f"lock receipt missing {field}"
        assert burn["state"] == "PROTECTED_BURNED"
    print("PASS test_protected_state_is_receipt_bound")


def test_wrong_campaign_cannot_reuse_burned_token():
    with tempfile.TemporaryDirectory() as tmp:
        lock = LocalProtectedLock(Path(tmp))
        lock.claim("c6", **BIND)
        lock.burn("c6", final_state_reason="SUCCESS",
                  result_or_failure_sha256="ab" * 32)
        try:
            lock.burn("c7", final_state_reason="SUCCESS",
                      result_or_failure_sha256="ab" * 32)
            raise AssertionError("burned a never-claimed campaign")
        except ProtectedLockViolation as exc:
            assert "BURN_WITHOUT_CLAIM" in str(exc)
        other = lock.claim("c7", **BIND)                  # c7 has its OWN token
        assert other["campaign_id"] == "c7"
        assert lock.state("c6") == "PROTECTED_BURNED"     # c6 stays burned
    print("PASS test_wrong_campaign_cannot_reuse_burned_token")


def main():
    test_second_protected_read_refused()
    test_failed_and_interrupted_runs_still_burn()
    test_two_processes_cannot_claim_same_campaign()
    test_protected_state_is_receipt_bound()
    test_wrong_campaign_cannot_reuse_burned_token()
    print("ALL PROTECTED-LOCK TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
