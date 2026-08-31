"""test_heartbeat_failclosed.py -- heartbeat type safety + clock immutability
(GATE 1A.2R.2A).

Post-construction reassignment of driver._clock is inert in REAL (the heartbeat
reads time.time() directly). Every malformed heartbeat value (string, list,
dict, bool, NaN, infinity, negative) fails closed as WATCHDOG_INVALID_HEARTBEAT
rather than escaping as a raw TypeError, and the separate watchdog_main loop
requests termination on any unexpected error. No invalid heartbeat ever counts
as fresh.
"""
from __future__ import annotations

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

from exec.campaign_driver import CampaignDriver  # noqa: E402
from exec.watchdog import Watchdog, is_valid_timestamp  # noqa: E402


def _base_kwargs(mode, tmp):
    er = Path(tmp) / "er"; er.mkdir(parents=True, exist_ok=True)
    ap = Path(tmp) / "a.json"; ap.write_text("{}", encoding="utf-8")
    return dict(mode=mode, package_root=PKG, campaign_id="c",
                execution_approval_path=ap, prep_approval_path=ap,
                prep_receipt_path=ap, evidence_root=er)


def _write_hb(path: Path, value):
    """Write a heartbeat file carrying an arbitrary (possibly invalid) t value.
    NaN/inf are written as the JSON tokens a naive producer would emit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if value == "NaN_TOKEN":
        path.write_text('{"t": NaN}\n', encoding="utf-8")
    elif value == "INF_TOKEN":
        path.write_text('{"t": Infinity}\n', encoding="utf-8")
    else:
        path.write_text(json.dumps({"t": value}) + "\n", encoding="utf-8")


def _poll_invalid(value, name):
    with tempfile.TemporaryDirectory() as tmp:
        hb = Path(tmp) / "hb.json"
        _write_hb(hb, value)
        wd = Watchdog(hb, Path(tmp), stale_limit_seconds=100, launched_at=1000.0)
        # must NOT raise, must return False, must leave a termination marker
        alive = wd.poll_once(1050.0)
        assert alive is False, f"{name}: invalid heartbeat treated as alive"
        marker = json.loads((Path(tmp) / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_INVALID_HEARTBEAT", \
            f"{name}: reason {marker['reason']}"
    print(f"PASS {name}")


def test_real_postconstruction_clock_replacement_is_inert():
    with tempfile.TemporaryDirectory() as tmp:
        d = CampaignDriver(**_base_kwargs("REAL", tmp))
        d._clock = lambda: "not-a-number"              # hostile mutation
        before = time.time()
        d._beat()                                      # must not use _clock
        hb = json.loads((Path(tmp) / "er" / "heartbeat.json")
                        .read_text(encoding="utf-8"))["t"]
        assert isinstance(hb, (int, float)) and before <= hb <= time.time() + 1, \
            "REAL heartbeat used the mutated clock"
    print("PASS test_real_postconstruction_clock_replacement_is_inert")


def test_real_string_clock_cannot_crash_watchdog():
    # even if a string somehow reaches the heartbeat file, the watchdog refuses
    # it fail-closed rather than raising
    _poll_invalid("not-a-number", "test_real_string_clock_cannot_crash_watchdog")


def test_string_heartbeat_terminates_as_invalid():
    _poll_invalid("2026-08-31", "test_string_heartbeat_terminates_as_invalid")


def test_list_heartbeat_terminates_as_invalid():
    _poll_invalid([1, 2, 3], "test_list_heartbeat_terminates_as_invalid")


def test_dict_heartbeat_terminates_as_invalid():
    _poll_invalid({"nested": 1}, "test_dict_heartbeat_terminates_as_invalid")


def test_bool_heartbeat_terminates_as_invalid():
    assert is_valid_timestamp(True) is False and is_valid_timestamp(False) is False
    _poll_invalid(True, "test_bool_heartbeat_terminates_as_invalid")


def test_nan_heartbeat_terminates_as_invalid():
    _poll_invalid("NaN_TOKEN", "test_nan_heartbeat_terminates_as_invalid")


def test_infinite_heartbeat_terminates_as_invalid():
    _poll_invalid("INF_TOKEN", "test_infinite_heartbeat_terminates_as_invalid")


def test_negative_heartbeat_terminates_as_invalid():
    _poll_invalid(-5.0, "test_negative_heartbeat_terminates_as_invalid")


def test_invalid_observed_now_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Watchdog(Path(tmp) / "hb.json", Path(tmp), stale_limit_seconds=100)
        assert wd.poll_once("not-a-number") is False
        marker = json.loads((Path(tmp) / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_INVALID_OBSERVED_NOW"
    print("PASS test_invalid_observed_now_is_refused")


def test_invalid_heartbeat_never_counts_as_fresh():
    # a string heartbeat with a "recent" numeric-looking prefix must NOT be fresh
    for bad in ("1050", "1050.0abc", [1050.0], {"t": 1050.0}, True):
        with tempfile.TemporaryDirectory() as tmp:
            hb = Path(tmp) / "hb.json"; _write_hb(hb, bad)
            wd = Watchdog(hb, Path(tmp), stale_limit_seconds=100,
                          launched_at=1000.0)
            assert wd.poll_once(1050.0) is False, f"{bad!r} counted as fresh"
    print("PASS test_invalid_heartbeat_never_counts_as_fresh")


def test_watchdog_main_exception_requests_termination():
    # a watchdog_config.json with an invalid (negative) stale limit makes
    # Watchdog.__init__ raise WatchdogError INSIDE the poll loop: watchdog_main
    # must catch it, request termination, and exit nonzero -- never vanish
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "ev"; evidence.mkdir()
        (evidence / "watchdog_config.json").write_text(
            json.dumps({"stale_limit_seconds": -1.0}), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(PKG / "exec" / "watchdog_main.py"),
             "--mode", "SYNTHETIC_CONFORMANCE",
             "--heartbeat", str(evidence / "heartbeat.json"),
             "--evidence", str(evidence),
             "--config", str(evidence / "watchdog_config.json"),
             "--poll-seconds", "0"],
            capture_output=True, text=True, timeout=30)
        assert r.returncode == 2, f"watchdog_main did not fail closed: rc={r.returncode}"
        marker = json.loads((evidence / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_INTERNAL_ERROR", marker
        assert (evidence / "TERMINATION_REQUESTED.json").is_file() \
            or (evidence / "TERMINATION_UNAVAILABLE_NOT_ON_EC2.json").is_file(), \
            "watchdog_main did not request termination"
    print("PASS test_watchdog_main_exception_requests_termination")


def main():
    test_real_postconstruction_clock_replacement_is_inert()
    test_real_string_clock_cannot_crash_watchdog()
    test_string_heartbeat_terminates_as_invalid()
    test_list_heartbeat_terminates_as_invalid()
    test_dict_heartbeat_terminates_as_invalid()
    test_bool_heartbeat_terminates_as_invalid()
    test_nan_heartbeat_terminates_as_invalid()
    test_infinite_heartbeat_terminates_as_invalid()
    test_negative_heartbeat_terminates_as_invalid()
    test_invalid_observed_now_is_refused()
    test_invalid_heartbeat_never_counts_as_fresh()
    test_watchdog_main_exception_requests_termination()
    print("ALL HEARTBEAT FAIL-CLOSED TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
