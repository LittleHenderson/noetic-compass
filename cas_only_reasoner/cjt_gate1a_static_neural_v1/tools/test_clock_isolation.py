"""test_clock_isolation.py -- production clock isolation (GATE 1A.2R.2).

The production CampaignDriver has NO clock parameter; REAL always uses real epoch
time. A caller cannot inject a future-valued clock to suppress timeout detection,
and the separate watchdog refuses an impossible future heartbeat. A fake clock is
permitted only in the non-claim-bearing REAL_BRANCH_CONFORMANCE posture. The
status-emission path itself is executed to prove SOFTWARE_CONFORMANCE_ONLY and
the refusal of a production owner-key id.
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

from exec.campaign_driver import CampaignDriver, RealBranchConformanceDriver  # noqa: E402
from exec.watchdog import MAX_FUTURE_HEARTBEAT_SKEW_SECONDS, Watchdog  # noqa: E402


def _base_kwargs(mode, tmp):
    er = Path(tmp) / "er"; er.mkdir(parents=True, exist_ok=True)
    ap = Path(tmp) / "a.json"; ap.write_text("{}", encoding="utf-8")
    return dict(mode=mode, package_root=PKG, campaign_id="c",
                execution_approval_path=ap, prep_approval_path=ap,
                prep_receipt_path=ap, evidence_root=er)


def test_real_driver_signature_has_no_clock_parameter():
    sig = inspect.signature(CampaignDriver.__init__).parameters
    assert "clock" not in sig, "production driver still has a public clock param"
    print("PASS test_real_driver_signature_has_no_clock_parameter")


def test_real_mode_cannot_receive_custom_clock():
    with tempfile.TemporaryDirectory() as tmp:
        # the only clock channel is the underscore conformance clock, refused
        # outside REAL_BRANCH_CONFORMANCE
        try:
            CampaignDriver(**_base_kwargs("REAL", tmp),
                           _conformance_clock=lambda: 0.0)
            raise AssertionError("REAL accepted a custom clock")
        except ValueError as exc:
            assert "CLOCK_ISOLATION_VIOLATION" in str(exc)
        try:
            CampaignDriver(**_base_kwargs("SYNTHETIC_CONFORMANCE", tmp),
                           _conformance_clock=lambda: 5.0)
            raise AssertionError("SYNTHETIC accepted a custom clock")
        except ValueError as exc:
            assert "CLOCK_ISOLATION_VIOLATION" in str(exc)
    print("PASS test_real_mode_cannot_receive_custom_clock")


def test_real_mode_heartbeat_uses_real_epoch_time():
    with tempfile.TemporaryDirectory() as tmp:
        d = CampaignDriver(**_base_kwargs("REAL", tmp))
        assert d._clock is time.time, "REAL heartbeat clock is not real epoch"
        before = time.time()
        t = d._clock()
        assert before <= t <= time.time() + 1
    print("PASS test_real_mode_heartbeat_uses_real_epoch_time")


def test_future_heartbeat_exceeding_skew_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Watchdog(Path(tmp) / "hb.json", Path(tmp), stale_limit_seconds=100,
                      startup_grace_seconds=300, launched_at=1000.0)
        wd.beat(1000.0 + 1_000_000_000)               # far-future heartbeat
        assert wd.poll_once(1000.0) is False, "future heartbeat treated as fresh"
        marker = json.loads((Path(tmp) / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_FUTURE_HEARTBEAT"
        assert marker["allowed_future_skew_seconds"] == MAX_FUTURE_HEARTBEAT_SKEW_SECONDS
        # a heartbeat within the small allowed skew is still fresh
        wd2 = Watchdog(Path(tmp) / "hb2.json", Path(tmp), stale_limit_seconds=100,
                       launched_at=1000.0)
        wd2.beat(1002.0)
        assert wd2.poll_once(1000.0) is True
    print("PASS test_future_heartbeat_exceeding_skew_is_refused")


def test_future_clock_injection_cannot_disable_timeout():
    # even if a heartbeat were written by a future-valued clock, the watchdog
    # (on the real epoch clock) refuses it rather than reading it as fresh
    with tempfile.TemporaryDirectory() as tmp:
        wd = Watchdog(Path(tmp) / "hb.json", Path(tmp), stale_limit_seconds=100,
                      launched_at=0.0)
        future = time.time() + 1_000_000_000
        wd.beat(future)
        assert wd.poll_once(time.time()) is False, \
            "future-clock heartbeat disabled the timeout"
    print("PASS test_future_clock_injection_cannot_disable_timeout")


def test_real_branch_conformance_accepts_fake_clock():
    with tempfile.TemporaryDirectory() as tmp:
        ticks = iter([10.0, 20.0, 30.0])
        d = RealBranchConformanceDriver(
            real_hooks={"feature_backend": ("m", "t", "cpu")},
            conformance_clock=lambda: next(ticks),
            **{k: v for k, v in _base_kwargs("REAL", tmp).items() if k != "mode"})
        assert d._clock() == 10.0 and d._clock() == 20.0
    print("PASS test_real_branch_conformance_accepts_fake_clock")


def test_real_branch_fake_clock_is_non_claim_bearing():
    with tempfile.TemporaryDirectory() as tmp:
        d = RealBranchConformanceDriver(
            real_hooks={"feature_backend": ("m", "t", "cpu")},
            conformance_clock=lambda: 42.0,
            **{k: v for k, v in _base_kwargs("REAL", tmp).items() if k != "mode"})
        assert d._is_claim_bearing() is False
        assert d._trust_mode() == "SYNTHETIC_CONFORMANCE"
    print("PASS test_real_branch_fake_clock_is_non_claim_bearing")


def _run_status(raw_path, evidence_root, conformance):
    cmd = [sys.executable, str(PKG / "tools" / "emit_gate1_status.py"),
           str(raw_path), "--evidence-root", str(evidence_root),
           "--out", str(Path(evidence_root) / "GATE1_STATUS.json")]
    if conformance:
        cmd.append("--conformance")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=PKG)


def test_real_branch_conformance_emits_software_conformance_only():
    # execute the ACTUAL status program (not just _is_claim_bearing()) on a
    # complete TEST-key evidence fixture under --conformance
    import test_status_fixtures as fx
    results = fx.fixture()                              # TEST- key + evidence dir
    raw = Path(fx._EVIDENCE_ROOT) / "RAW.json"
    raw.write_text(json.dumps(results), encoding="utf-8")
    r = _run_status(raw, fx._EVIDENCE_ROOT, conformance=True)
    assert r.returncode == 0, r.stdout + r.stderr
    status = json.loads((Path(fx._EVIDENCE_ROOT) / "GATE1_STATUS.json")
                        .read_text(encoding="utf-8"))
    assert status["claim_a_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert status["claim_b_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert status["non_claim_bearing"] is True
    print("PASS test_real_branch_conformance_emits_software_conformance_only")


def test_production_owner_key_refused_in_real_branch_conformance():
    # a production-looking (non-TEST) owner key under --conformance is refused
    import test_status_fixtures as fx
    results = fx.fixture(owner_key_id="OWNER-PROD-KEY-2026")
    raw = Path(fx._EVIDENCE_ROOT) / "RAW.json"
    raw.write_text(json.dumps(results), encoding="utf-8")
    r = _run_status(raw, fx._EVIDENCE_ROOT, conformance=True)
    assert r.returncode != 0 and "EVIDENCE_UNBOUND" in r.stdout, \
        f"production key not refused in conformance: {r.stdout}"
    print("PASS test_production_owner_key_refused_in_real_branch_conformance")


def main():
    test_real_driver_signature_has_no_clock_parameter()
    test_real_mode_cannot_receive_custom_clock()
    test_real_mode_heartbeat_uses_real_epoch_time()
    test_future_heartbeat_exceeding_skew_is_refused()
    test_future_clock_injection_cannot_disable_timeout()
    test_real_branch_conformance_accepts_fake_clock()
    test_real_branch_fake_clock_is_non_claim_bearing()
    test_real_branch_conformance_emits_software_conformance_only()
    test_production_owner_key_refused_in_real_branch_conformance()
    print("ALL CLOCK-ISOLATION TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
