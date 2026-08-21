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

# --- why these bounds are what they are -------------------------------------
#
# FOUND THE HARD WAY, 2026-08-21. The first live induction used a 240 s window
# and produced a **311,788 ms** gap against a 180,000 ms acceptance bound. The
# harness refused the measurement, correctly -- but the failure was manufactured
# by this tool, not observed in the guardian.
#
# That is the worst kind of test defect: a procedure that creates the very
# failure it exists to detect, and would have been read as a property of the
# system under test.
#
# The window must now satisfy BOTH ends:
#   * long enough to miss a tick   -> the scenario section 6 asks for
#   * short enough that the gap stays inside the bound -> or the test fails itself
#
# Observed overhead was 71.8 s (240 s window -> 311.8 s gap). Worst case is two
# cadences: up to one waiting for the disable to land after a tick, up to one
# waiting for the next tick after re-enable. `align_to_tick` removes the first,
# which is why the ceiling below assumes only one cadence of slop.
MIN_DISABLE_SECONDS: Final = 75
MAX_DISABLE_SECONDS: Final = GAP_ACCEPTANCE_BOUND_MILLISECONDS // 1000 - CADENCE_SECONDS


def worst_case_gap_milliseconds(disable_seconds: int, *, aligned: bool) -> int:
    """Largest gap the window can produce, so it can be checked BEFORE running.

    Unaligned, the disable can land just before a tick and the re-enable just
    after one, costing two cadences. Aligned, the first cadence is removed.
    """
    slop = CADENCE_SECONDS if aligned else 2 * CADENCE_SECONDS
    return (disable_seconds + slop) * 1000


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


def check_window(seconds: int, *, aligned: bool = True) -> None:
    if type(seconds) is not int:
        raise InductionRefused("REFUSED: window must be an int")
    if seconds < MIN_DISABLE_SECONDS:
        raise InductionRefused(
            f"REFUSED: {seconds}s is below {MIN_DISABLE_SECONDS}s. At a "
            f"{CADENCE_SECONDS}s cadence a shorter window cannot reliably miss a "
            "consecutive tick, so it would produce a scenario that did not happen."
        )
    if seconds > MAX_DISABLE_SECONDS:
        raise InductionRefused(
            f"REFUSED: {seconds}s exceeds the {MAX_DISABLE_SECONDS}s ceiling. There is "
            "no unbounded mode, and the ceiling is not arbitrary: it is the "
            f"{GAP_ACCEPTANCE_BOUND_MILLISECONDS} ms acceptance bound minus one "
            f"{CADENCE_SECONDS}s cadence of slop."
        )
    worst = worst_case_gap_milliseconds(seconds, aligned=aligned)
    if worst > GAP_ACCEPTANCE_BOUND_MILLISECONDS:
        raise InductionRefused(
            f"REFUSED: a {seconds}s window can produce a gap of up to {worst} ms, "
            f"which exceeds the {GAP_ACCEPTANCE_BOUND_MILLISECONDS} ms acceptance "
            "bound. The test would manufacture the failure it exists to detect. "
            f"(aligned={aligned})"
        )


def expected_missed_ticks(seconds: int, cadence: int = CADENCE_SECONDS) -> int:
    """Ticks expected to be missed. Reported so the plan is stated before the run."""
    return max(0, seconds // cadence - 1)


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
    parser.add_argument("--disable-seconds", type=int, default=180)
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
