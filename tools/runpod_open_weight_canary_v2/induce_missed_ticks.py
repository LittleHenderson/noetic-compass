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

# --- why the window is EXACTLY one cadence ----------------------------------
#
# FOUND THE HARD WAY, TWICE, on live runs 2026-08-21.
#
# Attempt 1: a 240 s window produced a 311,788 ms gap against a 180,000 ms
# acceptance bound. Attempt 2, after "fixing" the ceiling to 120 s, produced a
# 210,900 ms gap -- still over. Measured overhead was 71.8 s then 90.9 s.
#
# The second failure exposed a worse defect than the first: the code carried an
# `aligned=True` parameter asserting that the disable lands immediately after a
# tick. **It does not. The tool never aligns -- it disables the instant it is
# called.** So the slop is up to TWO cadences, not one: up to a full cadence
# before the disable lands relative to the previous tick, and up to another
# before the next tick arrives after re-enable. A parameter that claims a
# property the code does not implement is worse than no parameter, because it
# makes the arithmetic look sound.
#
# The honest derivation, with two cadences of slop and no alignment claimed:
#
#     worst gap = window + 2*CADENCE <= 180_000 ms   =>  window <= 60 s
#     the window must cover a tick boundary          =>  window >= 60 s
#     therefore the ONLY admissible window is exactly CADENCE.
#
# A 60 s window at a 60 s cadence always spans exactly one tick boundary, so it
# misses exactly one tick -- which is all section 6 asks for, and all the bound
# leaves room for. There is no range to tune, and that is the point.
MIN_DISABLE_SECONDS: Final = CADENCE_SECONDS
MAX_DISABLE_SECONDS: Final = CADENCE_SECONDS


def worst_case_gap_milliseconds(disable_seconds: int) -> int:
    """Largest gap the window can produce, checkable BEFORE anything is disabled.

    Two cadences of slop, because this tool does not align to a tick. If it ever
    learns to, this function -- and the bounds above -- must change together.
    """
    return (disable_seconds + 2 * CADENCE_SECONDS) * 1000


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
    if type(seconds) is not int:
        raise InductionRefused("REFUSED: window must be an int")
    if seconds != CADENCE_SECONDS:
        raise InductionRefused(
            f"REFUSED: the window must be exactly {CADENCE_SECONDS}s, not {seconds}s. "
            "This is derived, not chosen: shorter cannot span a tick boundary, and "
            f"longer can produce a gap above the {GAP_ACCEPTANCE_BOUND_MILLISECONDS} ms "
            "acceptance bound once two cadences of slop are counted. Two live runs "
            "already proved the point -- 240s gave 311788 ms and 120s gave 210900 ms."
        )
    worst = worst_case_gap_milliseconds(seconds)
    if worst > GAP_ACCEPTANCE_BOUND_MILLISECONDS:
        raise InductionRefused(
            f"REFUSED: a {seconds}s window can produce a gap of up to {worst} ms, "
            f"which exceeds the {GAP_ACCEPTANCE_BOUND_MILLISECONDS} ms acceptance "
            "bound. The test would manufacture the failure it exists to detect."
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
    record["verdict"] = "MISSED_TICK_WINDOW_INDUCED_AND_SCHEDULE_RESTORED"
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
