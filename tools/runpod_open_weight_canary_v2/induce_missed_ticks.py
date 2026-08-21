"""Induce a bounded consecutive missed-tick window on PREPRODUCTION only.

`RUNBOOK.md` section 6 requires the timing evidence to include *"at least one
consecutive missed-tick scenario."* EventBridge will not politely skip ticks on
request, so the window has to be induced: disable the recovery rule, wait, then
re-enable it.

That makes this the most dangerous tool in the set. It is the only one that
disables a safety schedule. Everything below exists so it can never be pointed
at production.

**Four independent guards, all of which must pass:**

1. The target account must NOT be the management account `807562639912`.
2. The caller must supply the target account id explicitly, and the assumed
   session must actually land in that account. A mismatch aborts.
3. The rule name must belong to a stack whose name marks it preproduction.
4. The disable window is bounded. There is no unbounded mode.

**And one that runs even when things go wrong:** re-enable is issued from a
`finally` block, so a crash, a timeout, or a keyboard interrupt still restores
the schedule. A tool that can leave recovery disabled after an exception is a
worse hazard than the gap it was measuring.

This tool is deliberately NOT importable by the measurement harness. Inducing a
fault and measuring it are separate jobs; a harness that could induce its own
inputs would be measuring itself.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Final

MANAGEMENT_ACCOUNT: Final = "807562639912"
EXPECTED_REGION: Final = "us-west-2"
PREPROD_MARKERS: Final = ("preprod", "pre-prod", "staging", "test")
CADENCE_SECONDS: Final = 60

# The acceptance bound the induced gap must still satisfy, mirrored from
# guardian_runtime._verify_timing_evidence.
GAP_ACCEPTANCE_BOUND_MILLISECONDS: Final = 180_000

# --- what three live runs actually proved -----------------------------------
#
# 2026-08-21, three real inductions against a live preproduction schedule:
#
#     window 240 s -> gap 311,788 ms   (over the 180,000 ms bound)
#     window 120 s -> gap 210,900 ms   (over the bound)
#     window  60 s -> gap  94,900 ms   (in bound, but ZERO missed ticks)
#
# The admissible outcome is narrower than any of them. A gap must simultaneously
#   * register at least one missed tick -> `(gap // cadence) - 1 >= 1` -> >= 120 s
#   * stay inside the acceptance bound                                -> <= 180 s
# so the target band is [120_000, 180_000] ms -- exactly 60 seconds wide.
#
# Measured overhead (gap minus window) was 34.9 s, 90.9 s and 71.8 s: a spread
# of ~56 s, because the disable lands at an arbitrary point in the cycle and
# EventBridge re-anchors its cadence on re-enable. **No fixed window can
# guarantee landing in a 60-second band when the noise is 56 seconds wide.**
#
# THE DEFECT THAT MATTERED MOST was not the window size. This tool returned
# `MISSED_TICK_WINDOW_INDUCED_AND_SCHEDULE_RESTORED` on all three runs -- while
# none of them produced an admissible gap. It asserted an outcome it never
# checked. A tool that reports success it did not verify is worse than one that
# fails, because the failure is silent and downstream work inherits it.
#
# So the verdict no longer claims the induction worked. It claims only what the
# tool actually knows: the schedule was disabled and restored. Whether a usable
# missed-tick window resulted is decided by MEASUREMENT, against the band below.
MIN_DISABLE_SECONDS: Final = CADENCE_SECONDS
MAX_DISABLE_SECONDS: Final = 2 * CADENCE_SECONDS

# A gap must land inside this band to be usable. Mirrored from the harness.
ADMISSIBLE_GAP_BAND_MILLISECONDS: Final = (2 * CADENCE_SECONDS * 1000,
                                           GAP_ACCEPTANCE_BOUND_MILLISECONDS)


def classify_induced_gap(gap_milliseconds: int) -> str:
    """Decide whether an observed gap is usable. Measurement calls this, not induce()."""
    low, high = ADMISSIBLE_GAP_BAND_MILLISECONDS
    if gap_milliseconds < low:
        return "TOO_SHORT_NO_MISSED_TICK"
    if gap_milliseconds > high:
        return "TOO_LONG_EXCEEDS_ACCEPTANCE_BOUND"
    return "IN_BAND"


class InductionRefused(RuntimeError):
    """A guard rejected the request. Nothing was changed."""


def check_not_management(account_id: str) -> None:
    if account_id == MANAGEMENT_ACCOUNT:
        raise InductionRefused(
            f"REFUSED: {account_id} is the management/production account. This tool "
            "disables a recovery schedule and must never point at production."
        )
    if not (account_id.isdigit() and len(account_id) == 12):
        raise InductionRefused(f"REFUSED: malformed account id {account_id!r}")


def check_session_account(identity: dict[str, Any], account_id: str) -> None:
    actual = identity.get("Account")
    if actual != account_id:
        raise InductionRefused(
            f"REFUSED: session landed in account {actual}, but {account_id} was "
            "requested. Refusing rather than disabling a schedule in an unknown place."
        )


def check_preproduction_rule(rule_name: str) -> None:
    lowered = rule_name.lower()
    if not any(marker in lowered for marker in PREPROD_MARKERS):
        raise InductionRefused(
            f"REFUSED: rule {rule_name!r} carries no preproduction marker "
            f"{PREPROD_MARKERS}. Refusing to disable a schedule that may be production."
        )


def check_window(seconds: int) -> None:
    """Bound the window. This does NOT promise the outcome will be usable.

    No fixed window can, because the observed overhead varies by ~56 s against a
    60 s target band. The outcome is decided by measurement, via
    `classify_induced_gap`.
    """
    if type(seconds) is not int:
        raise InductionRefused("REFUSED: window must be an int")
    if not MIN_DISABLE_SECONDS <= seconds <= MAX_DISABLE_SECONDS:
        raise InductionRefused(
            f"REFUSED: window must be between {MIN_DISABLE_SECONDS}s and "
            f"{MAX_DISABLE_SECONDS}s, got {seconds}s. Below the floor cannot span a "
            "tick boundary at all; above the ceiling the gap is very likely to "
            f"exceed the {GAP_ACCEPTANCE_BOUND_MILLISECONDS} ms acceptance bound. "
            "Three live runs measured 240s -> 311788 ms, 120s -> 210900 ms and "
            "60s -> 94900 ms, so neither end is theoretical."
        )


def expected_missed_ticks(seconds: int, cadence: int = CADENCE_SECONDS) -> int:
    """Ticks expected to be missed. Reported so the plan is stated before the run.

    A window of exactly one cadence always spans exactly one tick boundary.
    """
    return max(1, seconds // cadence) if seconds >= cadence else 0


def induce(
    *,
    account_id: str,
    rule_name: str,
    disable_seconds: int,
    session_factory: Any,
    sleep: Any = time.sleep,
) -> dict[str, Any]:
    """Disable, wait, re-enable. Re-enable is guaranteed by `finally`."""
    check_not_management(account_id)
    check_window(disable_seconds)
    check_preproduction_rule(rule_name)

    session = session_factory(account_id)
    sts = session.client("sts", region_name=EXPECTED_REGION)
    identity = {k: v for k, v in sts.get_caller_identity().items() if k != "ResponseMetadata"}
    check_session_account(identity, account_id)

    events = session.client("events", region_name=EXPECTED_REGION)
    before = events.describe_rule(Name=rule_name).get("State")
    if before != "ENABLED":
        raise InductionRefused(
            f"REFUSED: rule {rule_name!r} is {before!r}, not ENABLED. There is no "
            "running schedule to interrupt, so any 'missed' tick would be fictional."
        )

    record: dict[str, Any] = {
        "account_id": account_id,
        "rule_name": rule_name,
        "state_before": before,
        "disable_seconds": disable_seconds,
        "expected_missed_ticks": expected_missed_ticks(disable_seconds),
        "cadence_seconds": CADENCE_SECONDS,
    }

    events.disable_rule(Name=rule_name)
    record["disabled"] = True
    try:
        sleep(disable_seconds)
    finally:
        # Runs on success, on exception, and on KeyboardInterrupt.
        events.enable_rule(Name=rule_name)
        record["re_enabled"] = True
        record["state_after"] = events.describe_rule(Name=rule_name).get("State")

    if record["state_after"] != "ENABLED":
        raise InductionRefused(
            f"CRITICAL: rule {rule_name!r} is {record['state_after']!r} after "
            "re-enable. Recovery may still be disabled. Fix this by hand now."
        )
    # NOT "induced successfully" -- this tool cannot see the resulting gap, and
    # claiming otherwise is exactly the defect that survived three live runs.
    record["verdict"] = "SCHEDULE_DISABLED_AND_RESTORED_OUTCOME_UNVERIFIED"
    record["admissible_gap_band_milliseconds"] = list(ADMISSIBLE_GAP_BAND_MILLISECONDS)
    record["next_step"] = (
        "Measure the resulting gap and pass it to classify_induced_gap(). Only "
        "IN_BAND is usable. TOO_SHORT or TOO_LONG means the scenario did not "
        "happen and the attempt must be repeated, not reinterpreted."
    )
    return record


def _default_session_factory(account_id: str) -> Any:  # pragma: no cover
    import boto3

    creds = boto3.client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole",
        RoleSessionName="cas-preprod-missed-tick",
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def _main(argv: list[str]) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description="PREPRODUCTION ONLY. Bounded.")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--rule-name", required=True)
    parser.add_argument("--disable-seconds", type=int, default=60)
    args = parser.parse_args(argv)
    record = induce(
        account_id=args.account_id,
        rule_name=args.rule_name,
        disable_seconds=args.disable_seconds,
        session_factory=_default_session_factory,
    )
    print(json.dumps(record, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except InductionRefused as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from None
