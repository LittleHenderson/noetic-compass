"""watchdog_config.py -- the fail-closed watchdog configuration authority
(GATE 1A.2R.2B).

The separate watchdog's stale limit is owner-signed governance: it is derived
from the signed per-job wall-clock cap and bound to the campaign. In REAL
(claim-bearing) mode a missing, malformed, or type-wrong configuration MUST fail
closed (terminate) -- the watchdog may NEVER substitute an unsigned local
default for the signed cap. The configuration envelope is DICTIONARY-ONLY with
an exact key set: arrays, null, scalars, and list-valued limits are refused, and
NaN/infinity are rejected by the JSON parser.

SYNTHETIC_CONFORMANCE / REAL_BRANCH_CONFORMANCE are non-claim-bearing; there a
missing config may use a documented conformance default, but a PRESENT config
is still validated by the same schema.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

CONFIG_ID = "WATCHDOG_CONFIG"
STALE_LIMIT_MULTIPLIER = 1.1               # signed cap hours * 3600 * 1.1
CONFORMANCE_DEFAULT_STALE_SECONDS = 2.5 * 3600

REQUIRED_KEYS = frozenset([
    "config_id", "campaign_id", "package_commit_sha", "execution_approval_sha256",
    "owner_key_id", "signed_per_job_cap_hours", "stale_limit_seconds"])
OPTIONAL_KEYS = frozenset(["aws_protected_lock"])


class WatchdogConfigError(RuntimeError):
    pass


def _reject_non_finite(x):
    raise WatchdogConfigError(f"CONFIG_JSON_CONSTANT_REFUSED: {x}")


def _pos_finite(v):
    return type(v) in (int, float) and not isinstance(v, bool) \
        and math.isfinite(v) and v > 0


def _hex(v, n):
    return isinstance(v, str) and len(v) == n \
        and all(c in "0123456789abcdef" for c in v)


def validate_config(obj) -> dict:
    """Validate a PARSED configuration object against the exact schema. Raises
    WatchdogConfigError on any defect. Returns the object on success."""
    # dictionary-only envelope: arrays / null / scalars refused
    if not isinstance(obj, dict):
        raise WatchdogConfigError(
            f"CONFIG_NOT_A_DICT: got {type(obj).__name__}")
    keys = set(obj)
    if not REQUIRED_KEYS <= keys or not keys <= (REQUIRED_KEYS | OPTIONAL_KEYS):
        raise WatchdogConfigError(
            f"CONFIG_KEY_SET_INVALID: {sorted(keys)}")
    if obj["config_id"] != CONFIG_ID:
        raise WatchdogConfigError("CONFIG_ID_MISMATCH")
    if not isinstance(obj["campaign_id"], str) or not obj["campaign_id"]:
        raise WatchdogConfigError("CONFIG_CAMPAIGN_ID_INVALID")
    if not _hex(obj["package_commit_sha"], 40):
        raise WatchdogConfigError("CONFIG_PACKAGE_COMMIT_INVALID")
    if not _hex(obj["execution_approval_sha256"], 64):
        raise WatchdogConfigError("CONFIG_APPROVAL_DIGEST_INVALID")
    if not isinstance(obj["owner_key_id"], str) or len(obj["owner_key_id"]) < 4:
        raise WatchdogConfigError("CONFIG_OWNER_KEY_ID_INVALID")
    # scalar-only limits: a list-valued cap is refused by _pos_finite
    if not _pos_finite(obj["signed_per_job_cap_hours"]):
        raise WatchdogConfigError("CONFIG_SIGNED_CAP_INVALID")
    if not _pos_finite(obj["stale_limit_seconds"]):
        raise WatchdogConfigError("CONFIG_STALE_LIMIT_INVALID")
    # the derived stale limit MUST equal signed_cap_hours * 3600 * multiplier
    expected = obj["signed_per_job_cap_hours"] * 3600.0 * STALE_LIMIT_MULTIPLIER
    if abs(obj["stale_limit_seconds"] - expected) > 1e-6:
        raise WatchdogConfigError(
            f"CONFIG_STALE_LIMIT_NOT_DERIVED: {obj['stale_limit_seconds']} != "
            f"{expected}")
    apl = obj.get("aws_protected_lock")
    if apl is not None:
        if not isinstance(apl, dict) or set(apl) != {"table_name", "region",
                                                     "campaign_id"}:
            raise WatchdogConfigError("CONFIG_AWS_LOCK_INVALID")
    return obj


def load_config(config_path: Path, mode: str) -> dict:
    """Read + validate the config INSIDE the fail-closed boundary. In REAL mode
    a missing/malformed config raises (no unsigned default). In a conformance
    mode a missing config yields a documented non-signed conformance default,
    but a PRESENT config is still schema-validated."""
    path = Path(config_path)
    if not path.is_file():
        if mode == "REAL":
            raise WatchdogConfigError(
                "CONFIG_MISSING: REAL mode requires a signed watchdog config; "
                "no unsigned default is permitted")
        return {"config_id": CONFIG_ID, "mode": "CONFORMANCE_DEFAULT",
                "stale_limit_seconds": CONFORMANCE_DEFAULT_STALE_SECONDS}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"),
                         parse_constant=_reject_non_finite)
    except (OSError, ValueError) as exc:
        raise WatchdogConfigError(f"CONFIG_UNREADABLE: {type(exc).__name__}") \
            from exc
    return validate_config(obj)


def stale_limit_of(config: dict) -> float:
    return float(config["stale_limit_seconds"])
