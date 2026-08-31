"""test_watchdog_config_authority.py -- watchdog config authority + JSON-envelope
totality (GATE 1A.2R.2B).

In REAL mode a missing/malformed signed config fails closed -- no unsigned
default. The configuration envelope is dictionary-only with an exact schema:
arrays, null, scalars, wrong keys, list-valued limits, and NaN/infinity are all
refused, and every malformed configuration causes watchdog_main to emit a
termination marker + request termination + exit nonzero (the read+validation is
inside the fail-closed boundary, so a top-level `[]` or `null` config can no
longer kill the watchdog before it activates the emergency path).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

from exec.watchdog_config import (CONFIG_ID, STALE_LIMIT_MULTIPLIER,  # noqa: E402
                                  WatchdogConfigError, load_config,
                                  validate_config)


def _bound(**over):
    cfg = {"config_id": CONFIG_ID, "campaign_id": "c",
           "package_commit_sha": "ab" * 20,
           "execution_approval_sha256": "cd" * 32, "owner_key_id": "OWNER-KEY",
           "signed_per_job_cap_hours": 2.0,
           "stale_limit_seconds": 2.0 * 3600 * STALE_LIMIT_MULTIPLIER}
    cfg.update(over)
    return cfg


def _expect_config_error(name, obj):
    try:
        validate_config(obj)
    except WatchdogConfigError:
        print(f"PASS reject {name}")
        return
    raise AssertionError(f"{name}: malformed config ACCEPTED")


def test_valid_bound_config_passes():
    v = validate_config(_bound())
    assert v["stale_limit_seconds"] == 2.0 * 3600 * STALE_LIMIT_MULTIPLIER
    v2 = validate_config(_bound(aws_protected_lock={
        "table_name": "t", "region": "us-east-1", "campaign_id": "c"}))
    assert v2["aws_protected_lock"]["region"] == "us-east-1"
    print("PASS test_valid_bound_config_passes")


def test_envelope_totality_non_dict_refused():
    for name, obj in [("array", [1, 2, 3]), ("null", None), ("scalar_int", 5),
                      ("scalar_str", "2.5"), ("scalar_float", 9000.0)]:
        _expect_config_error(f"envelope_{name}", obj)


def test_missing_or_extra_keys_refused():
    m = _bound(); del m["signed_per_job_cap_hours"]
    _expect_config_error("missing_signed_cap", m)
    _expect_config_error("extra_key", _bound(bonus=1))
    _expect_config_error("wrong_config_id", _bound(config_id="X"))


def test_list_valued_and_nonfinite_limits_refused():
    _expect_config_error("list_valued_cap",
                         _bound(signed_per_job_cap_hours=[2.0]))
    _expect_config_error("list_valued_stale",
                         _bound(stale_limit_seconds=[7920.0]))
    _expect_config_error("bool_cap", _bound(signed_per_job_cap_hours=True))
    _expect_config_error("zero_cap", _bound(signed_per_job_cap_hours=0))
    _expect_config_error("negative_stale", _bound(stale_limit_seconds=-1.0))


def test_stale_limit_must_be_derived_from_signed_cap():
    _expect_config_error("stale_not_derived",
                         _bound(stale_limit_seconds=99999.0))


def test_malformed_binding_fields_refused():
    _expect_config_error("bad_commit", _bound(package_commit_sha="short"))
    _expect_config_error("bad_approval_digest",
                         _bound(execution_approval_sha256="short"))
    _expect_config_error("empty_campaign_id", _bound(campaign_id=""))
    _expect_config_error("bad_aws_lock", _bound(aws_protected_lock={"x": 1}))


def test_real_mode_missing_config_fails_closed_no_default():
    with tempfile.TemporaryDirectory() as tmp:
        absent = Path(tmp) / "absent.json"
        try:
            load_config(absent, "REAL")
            raise AssertionError("REAL used an unsigned default for a missing config")
        except WatchdogConfigError as exc:
            assert "CONFIG_MISSING" in str(exc)
        # conformance MAY use a documented default
        d = load_config(absent, "SYNTHETIC_CONFORMANCE")
        assert d["mode"] == "CONFORMANCE_DEFAULT"
    print("PASS test_real_mode_missing_config_fails_closed_no_default")


def test_real_mode_nan_config_refused():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.json"
        p.write_text('{"config_id": "WATCHDOG_CONFIG", "stale_limit_seconds": NaN}',
                     encoding="utf-8")
        try:
            load_config(p, "REAL")
            raise AssertionError("NaN config accepted")
        except WatchdogConfigError:
            pass
    print("PASS test_real_mode_nan_config_refused")


def test_watchdog_main_toplevel_array_config_fails_closed():
    # GATE 1A.2R.2B earned envelope totality on the configuration validator: a
    # top-level array / null / scalar is refused. That module-level proof is
    # FROZEN and preserved here (validate_config below). GATE 1A.2R.2C retired
    # watchdog_config.json as the watchdog's authority surface -- the watchdog now
    # derives its timeout from the VERIFIED approval and binds an immutable
    # watchdog_authority.json. The SAME envelope-totality property on that live
    # authority surface (a top-level [] / null / 5 authority file fails closed via
    # watchdog_main with a termination marker) is proven in
    # tools/test_watchdog_bootstrap_authority.test_end_to_end_registered_bootstrap_order.
    for label, obj in [("array", [1, 2, 3]), ("null", None), ("scalar", 5)]:
        _expect_config_error(f"toplevel_{label}", obj)
        print(f"PASS watchdog_config_{label}_envelope_refused")


def main():
    test_valid_bound_config_passes()
    test_envelope_totality_non_dict_refused()
    test_missing_or_extra_keys_refused()
    test_list_valued_and_nonfinite_limits_refused()
    test_stale_limit_must_be_derived_from_signed_cap()
    test_malformed_binding_fields_refused()
    test_real_mode_missing_config_fails_closed_no_default()
    test_real_mode_nan_config_refused()
    test_watchdog_main_toplevel_array_config_fails_closed()
    print("ALL WATCHDOG-CONFIG-AUTHORITY TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
