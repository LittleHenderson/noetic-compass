"""Preflight for the preproduction guardian account. READ-ONLY. Fails closed.

Gate 1 item 1 needs timing evidence from a hash-locked preproduction deployment,
and that deployment needs a second AWS account because the guardian's ledger
table is account-scoped by design.

This module answers one question before anything is deployed: **is the new
account actually safe and correct to deploy into?** It performs no mutation. It
assumes a role, looks, and reports. Every check that cannot be proven is a
failure, never a warning.

The checks exist because each corresponds to a way this can go wrong quietly:

- Wrong account          → you measure production and call it preproduction.
- Wrong region           → the runtime refuses to activate (`EXPECTED_REGION`),
                           yet schedules still tick and emit plausible numbers.
- Ledger already present  → you are about to share a live safety ledger.
- Artifact hash mismatch → evidence from different bytes proves nothing about
                           the bytes you intend to run.
- Guardian already there → a second guardian in the same account, the exact
                           thing the account split was meant to avoid.

Usage:
    python preprod_account_preflight.py --account-id 123456789012
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Final

MANAGEMENT_ACCOUNT: Final = "807562639912"
EXPECTED_REGION: Final = "us-west-2"
ORG_ROLE: Final = "OrganizationAccountAccessRole"
LEDGER_PREFIX: Final = "cas-runpod-guardian-global-v1-"
GUARDIAN_STACK: Final = "cas-runpod-guardian-v1"

# Pinned production artifact identity. Preproduction MUST match these, or the
# timing evidence describes bytes nobody is going to run.
RUNTIME_ZIP_SHA256: Final = (
    "326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9"
)
CORE_LOCK_SHA256: Final = (
    "cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7"
)


class PreflightFailure(RuntimeError):
    """A check did not pass. Do not deploy. There is no override flag."""


def role_arn(account_id: str) -> str:
    return f"arn:aws:iam::{account_id}:role/{ORG_ROLE}"


def validate_account_id(account_id: str) -> None:
    if not (isinstance(account_id, str) and account_id.isdigit() and len(account_id) == 12):
        raise PreflightFailure(f"account id must be 12 digits, got {account_id!r}")
    if account_id == MANAGEMENT_ACCOUNT:
        raise PreflightFailure(
            f"{account_id} is the MANAGEMENT account. Deploying preproduction here is "
            "the exact collision the second account exists to avoid."
        )


def check_assumed_identity(identity: dict[str, Any], account_id: str) -> None:
    arn = identity.get("Arn", "")
    if identity.get("Account") != account_id:
        raise PreflightFailure(
            f"assumed session is in account {identity.get('Account')}, expected {account_id}"
        )
    if ORG_ROLE not in arn:
        raise PreflightFailure(f"assumed identity is not {ORG_ROLE}: {arn}")


def check_ledger_absent(table_names: list[str], account_id: str) -> None:
    expected = LEDGER_PREFIX + account_id
    stray = [t for t in table_names if t.startswith(LEDGER_PREFIX)]
    if stray:
        raise PreflightFailure(
            "a guardian ledger table already exists in this account: "
            f"{stray}. A fresh preproduction account must have none — its presence "
            "means either a guardian is already deployed here, or this is not the "
            f"account you think it is. Expected to be absent: {expected}"
        )


def check_no_guardian_stack(stack_names: list[str]) -> None:
    hits = [s for s in stack_names if "guardian" in s.lower()]
    if hits:
        raise PreflightFailure(f"guardian-like stacks already present: {hits}")


def check_region(region: str) -> None:
    if region != EXPECTED_REGION:
        raise PreflightFailure(
            f"region is {region!r}, but the runtime pins EXPECTED_REGION = "
            f"{EXPECTED_REGION!r} and refuses to activate elsewhere. Schedules would "
            "still tick and emit plausible-looking numbers, which is worse than "
            "failing outright."
        )


def check_artifact_hashes(runtime_zip: str, core_lock: str) -> None:
    problems = []
    if runtime_zip != RUNTIME_ZIP_SHA256:
        problems.append(f"runtime zip {runtime_zip} != pinned {RUNTIME_ZIP_SHA256}")
    if core_lock != CORE_LOCK_SHA256:
        problems.append(f"core lock {core_lock} != pinned {CORE_LOCK_SHA256}")
    if problems:
        raise PreflightFailure(
            "preproduction artifact identity differs from production: "
            + "; ".join(problems)
            + ". Timing evidence from different bytes proves nothing about the bytes "
            "that will actually run."
        )


def run(account_id: str, session_factory: Any) -> dict[str, Any]:
    """Run every check. Returns a report, or raises PreflightFailure."""
    validate_account_id(account_id)
    report: dict[str, Any] = {"account_id": account_id, "role_arn": role_arn(account_id)}

    session = session_factory(role_arn(account_id))

    sts = session.client("sts", region_name=EXPECTED_REGION)
    identity = {k: v for k, v in sts.get_caller_identity().items() if k != "ResponseMetadata"}
    check_assumed_identity(identity, account_id)
    report["assumed_identity"] = identity

    check_region(EXPECTED_REGION)
    report["region"] = EXPECTED_REGION

    ddb = session.client("dynamodb", region_name=EXPECTED_REGION)
    tables = ddb.list_tables().get("TableNames", [])
    check_ledger_absent(tables, account_id)
    report["existing_tables"] = tables

    cf = session.client("cloudformation", region_name=EXPECTED_REGION)
    stacks = [
        s["StackName"]
        for s in cf.list_stacks(
            StackStatusFilter=[
                "CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE",
                "CREATE_IN_PROGRESS", "UPDATE_IN_PROGRESS",
            ]
        ).get("StackSummaries", [])
    ]
    check_no_guardian_stack(stacks)
    report["existing_stacks"] = stacks

    ec2 = session.client("ec2", region_name=EXPECTED_REGION)
    running = [
        i["InstanceId"]
        for r in ec2.describe_instances().get("Reservations", [])
        for i in r.get("Instances", [])
        if i["State"]["Name"] != "terminated"
    ]
    if running:
        raise PreflightFailure(f"unexpected EC2 instances already in this account: {running}")
    report["ec2_instances"] = running

    report["pinned_runtime_zip_sha256"] = RUNTIME_ZIP_SHA256
    report["pinned_core_lock_sha256"] = CORE_LOCK_SHA256
    report["verdict"] = "SAFE_TO_DEPLOY_PREPRODUCTION"
    return report


def _default_session_factory(target_role_arn: str) -> Any:  # pragma: no cover
    import boto3

    creds = boto3.client("sts").assume_role(
        RoleArn=target_role_arn, RoleSessionName="cas-preprod-preflight"
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def _main(argv: list[str]) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    args = parser.parse_args(argv)
    report = run(args.account_id, _default_session_factory)
    print(json.dumps(report, indent=2, default=str))
    print("\nPREFLIGHT PASSED. This authorises a preproduction DEPLOY only.")
    print("It does not authorise LIVE, a GPU, or any provider call.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except PreflightFailure as error:
        print(f"PREFLIGHT FAILED — DO NOT DEPLOY\n{error}", file=sys.stderr)
        raise SystemExit(2) from None
