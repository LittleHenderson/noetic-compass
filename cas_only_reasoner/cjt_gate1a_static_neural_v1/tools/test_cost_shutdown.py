"""test_cost_shutdown.py -- the section-9 cost- and termination-authority tests."""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.cost import CostAuthority, CostViolation  # noqa: E402
from exec.shutdown import ShutdownPath  # noqa: E402
from exec.watchdog import Watchdog  # noqa: E402

APPROVAL = {"max_hourly_rate_usd": 10.0, "cost_ceiling_usd": 100.0,
            "per_job_wall_clock_cap_hours": 2.0}


def test_caller_cannot_lower_hourly_rate():
    sig = inspect.signature(CostAuthority.__init__).parameters
    assert list(sig) == ["self", "approval"], \
        "CostAuthority must take ONLY the signed approval"
    import exec.launcher as launcher
    src = (PKG / "exec" / "launcher.py").read_text(encoding="utf-8")
    assert "hourly-rate" not in src.replace("NO --hourly-rate", ""), \
        "an hourly-rate argument exists on the launcher"
    print("PASS test_caller_cannot_lower_hourly_rate")
    print("PASS test_unsigned_rate_refused (no unsigned rate path exists)")


def test_projected_cost_ceiling_breach_refused():
    cost = CostAuthority(APPROVAL)
    for i in range(4):                       # 4 x worst-case 20 = 80 <= 100
        cost.gate_job(f"j{i}"); cost.record_job(f"j{i}", 2.0)
    try:
        cost.gate_job("j5")                  # 80 + 20 = 100 ok; record to 100
        cost.record_job("j5", 2.0)
        cost.gate_job("j6")                  # 100 + 20 > 100 -> refuse
        raise AssertionError("ceiling breach allowed")
    except CostViolation as exc:
        assert "COST_CEILING_REFUSAL" in str(exc)
    print("PASS test_projected_cost_ceiling_breach_refused")


def test_actual_cost_overrun_marks_campaign_failed():
    cost = CostAuthority({**APPROVAL, "per_job_wall_clock_cap_hours": 20.0})
    try:
        cost.record_job("big", 11.0)         # 110 > 100
        raise AssertionError("overrun unpunished")
    except CostViolation:
        assert cost.failed is True
    cost2 = CostAuthority(APPROVAL)
    try:
        cost2.record_job("toolong", 3.0)     # > 2h cap
        raise AssertionError("cap breach unpunished")
    except CostViolation:
        assert cost2.failed is True
    print("PASS test_actual_cost_overrun_marks_campaign_failed (+ per-job cap)")


def test_all_paths_request_termination():
    for reason in ("TIMEOUT", "FAILURE", "SUCCESS"):
        with tempfile.TemporaryDirectory() as tmp:
            sp = ShutdownPath("SYNTHETIC_CONFORMANCE", Path(tmp))
            receipt_path = Path(tmp) / "final.json"
            sp.finalize({"reason": reason}, receipt_path, [], "s3://x/y", reason)
            assert receipt_path.is_file()
            marker = json.loads((Path(tmp) / "TERMINATION_REQUESTED.json")
                                .read_text(encoding="utf-8"))
            assert marker["reason"] == reason
    print("PASS test_timeout_requests_termination")
    print("PASS test_failure_requests_termination")
    print("PASS test_success_requests_termination")


def test_watchdog_terminates_abandoned_campaign():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Watchdog(Path(tmp) / "hb.json", Path(tmp), stale_limit_seconds=100,
                      startup_grace_seconds=300, launched_at=1000.0)
        wd.beat(1000.0)
        assert wd.poll_once(1050.0) is True              # fresh
        assert wd.poll_once(1200.0) is False             # stale -> terminate
        marker = json.loads((Path(tmp) / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_STALE_HEARTBEAT"
    print("PASS test_watchdog_terminates_abandoned_campaign")


def test_watchdog_does_not_terminate_before_first_heartbeat():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Watchdog(Path(tmp) / "none.json", Path(tmp), stale_limit_seconds=100,
                      startup_grace_seconds=300, launched_at=1000.0)
        # no heartbeat file yet, but within the startup grace -> alive
        assert wd.poll_once(1200.0) is True
        assert not (Path(tmp) / "WATCHDOG_TERMINATION.json").is_file()
        # past the grace with still no heartbeat -> terminate
        assert wd.poll_once(1400.0) is False
        marker = json.loads((Path(tmp) / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_NO_HEARTBEAT_AFTER_GRACE"
    print("PASS test_watchdog_does_not_terminate_before_first_heartbeat")


def test_watchdog_receives_signed_cap():
    # the driver writes a BOUND watchdog_config.json; the config authority
    # derives the stale limit from the signed per-job cap (GATE 1A.2R.2B)
    from exec.watchdog_config import load_config, stale_limit_of
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "watchdog_config.json"
        bound = {"config_id": "WATCHDOG_CONFIG", "campaign_id": "c",
                 "package_commit_sha": "ab" * 20,
                 "execution_approval_sha256": "cd" * 32,
                 "owner_key_id": "OWNER-KEY", "signed_per_job_cap_hours": 2.0,
                 "stale_limit_seconds": 2.0 * 3600 * 1.1}
        cfg.write_text(json.dumps(bound), encoding="utf-8")
        assert stale_limit_of(load_config(cfg, "REAL")) == 2.0 * 3600 * 1.1
    print("PASS test_watchdog_receives_signed_cap")


def test_terminate_on_shutdown_is_frozen():
    launch = json.loads((PKG / "infra" / "instance_launch.json")
                        .read_text(encoding="utf-8"))
    assert launch["RunInstances"]["InstanceInitiatedShutdownBehavior"] \
        == "terminate"
    assert launch["RunInstances"]["MetadataOptions"]["HttpTokens"] == "required"
    print("PASS terminate-on-shutdown + IMDSv2 frozen in the launch template")


def main():
    test_caller_cannot_lower_hourly_rate()
    test_projected_cost_ceiling_breach_refused()
    test_actual_cost_overrun_marks_campaign_failed()
    test_all_paths_request_termination()
    test_watchdog_terminates_abandoned_campaign()
    test_watchdog_does_not_terminate_before_first_heartbeat()
    test_watchdog_receives_signed_cap()
    test_terminate_on_shutdown_is_frozen()
    print("ALL COST/SHUTDOWN TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
