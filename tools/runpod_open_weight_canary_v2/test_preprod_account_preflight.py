"""Offline tests for the preproduction account preflight.

No boto3, no sockets, no AWS. The session is a fake.

Every test here is a failure mode that would otherwise be silent: deploying into
the management account, into the wrong region, on top of an existing ledger, or
with artifact bytes that differ from production.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import preprod_account_preflight as pf  # noqa: E402

GOOD = "123456789012"


class _FakeClient:
    def __init__(self, account, tables, stacks, instances):
        self._account, self._tables, self._stacks, self._instances = (
            account, tables, stacks, instances)

    def get_caller_identity(self):
        return {"Account": self._account,
                "Arn": f"arn:aws:sts::{self._account}:assumed-role/{pf.ORG_ROLE}/s"}

    def list_tables(self):
        return {"TableNames": self._tables}

    def list_stacks(self, **_):
        return {"StackSummaries": [{"StackName": n} for n in self._stacks]}

    def describe_instances(self):
        return {"Reservations": [{"Instances": self._instances}]}


class _FakeSession:
    def __init__(self, account, tables=(), stacks=(), instances=()):
        self._c = _FakeClient(account, list(tables), list(stacks), list(instances))

    def client(self, *_a, **_k):
        return self._c


def factory(account, **kw):
    return lambda _arn: _FakeSession(account, **kw)


# --- account identity --------------------------------------------------------


def test_clean_account_passes():
    report = pf.run(GOOD, factory(GOOD))
    assert report["verdict"] == "SAFE_TO_DEPLOY_PREPRODUCTION"
    assert report["role_arn"] == f"arn:aws:iam::{GOOD}:role/{pf.ORG_ROLE}"


def test_management_account_is_refused():
    with pytest.raises(pf.PreflightFailure, match="MANAGEMENT account"):
        pf.run(pf.MANAGEMENT_ACCOUNT, factory(pf.MANAGEMENT_ACCOUNT))


@pytest.mark.parametrize("bad", ["12345", "abcdefghijkl", "", "1234567890123"])
def test_malformed_account_id_is_refused(bad):
    with pytest.raises(pf.PreflightFailure, match="12 digits"):
        pf.run(bad, factory(bad))


def test_session_landing_in_a_different_account_is_refused():
    # Asked for GOOD, but the assumed session reports somewhere else.
    with pytest.raises(pf.PreflightFailure, match="expected"):
        pf.run(GOOD, factory("999999999999"))


def test_identity_without_the_org_role_is_refused():
    ident = {"Account": GOOD, "Arn": f"arn:aws:iam::{GOOD}:user/somebody"}
    with pytest.raises(pf.PreflightFailure, match="not OrganizationAccountAccessRole"):
        pf.check_assumed_identity(ident, GOOD)


# --- the collision this whole exercise exists to prevent ---------------------


def test_existing_guardian_ledger_is_refused():
    tables = [pf.LEDGER_PREFIX + GOOD]
    with pytest.raises(pf.PreflightFailure, match="ledger table already exists"):
        pf.run(GOOD, factory(GOOD, tables=tables))


def test_a_ledger_belonging_to_another_account_is_still_refused():
    # Wrong-account ledger is even more alarming than a matching one.
    with pytest.raises(pf.PreflightFailure, match="ledger table already exists"):
        pf.run(GOOD, factory(GOOD, tables=[pf.LEDGER_PREFIX + "807562639912"]))


def test_unrelated_tables_do_not_trip_the_check():
    report = pf.run(GOOD, factory(GOOD, tables=["some-other-table", "app-sessions"]))
    assert report["verdict"] == "SAFE_TO_DEPLOY_PREPRODUCTION"


def test_existing_guardian_stack_is_refused():
    with pytest.raises(pf.PreflightFailure, match="guardian-like stacks"):
        pf.run(GOOD, factory(GOOD, stacks=["cas-runpod-guardian-v1"]))


def test_guardian_stack_match_is_case_insensitive():
    with pytest.raises(pf.PreflightFailure, match="guardian-like stacks"):
        pf.check_no_guardian_stack(["My-GUARDIAN-Test"])


def test_preexisting_ec2_instance_is_refused():
    inst = [{"InstanceId": "i-abc", "State": {"Name": "stopped"}}]
    with pytest.raises(pf.PreflightFailure, match="unexpected EC2 instances"):
        pf.run(GOOD, factory(GOOD, instances=inst))


def test_terminated_instances_are_ignored():
    inst = [{"InstanceId": "i-dead", "State": {"Name": "terminated"}}]
    report = pf.run(GOOD, factory(GOOD, instances=inst))
    assert report["ec2_instances"] == []


# --- region and artifact identity -------------------------------------------


def test_wrong_region_is_refused():
    with pytest.raises(pf.PreflightFailure, match="EXPECTED_REGION"):
        pf.check_region("us-east-1")


def test_expected_region_passes():
    pf.check_region(pf.EXPECTED_REGION)


def test_artifact_hash_mismatch_is_refused():
    with pytest.raises(pf.PreflightFailure, match="proves nothing"):
        pf.check_artifact_hashes("0" * 64, pf.CORE_LOCK_SHA256)


def test_both_artifact_hashes_reported_when_both_wrong():
    with pytest.raises(pf.PreflightFailure) as caught:
        pf.check_artifact_hashes("0" * 64, "1" * 64)
    msg = str(caught.value)
    assert "runtime zip" in msg and "core lock" in msg


def test_matching_artifact_hashes_pass():
    pf.check_artifact_hashes(pf.RUNTIME_ZIP_SHA256, pf.CORE_LOCK_SHA256)


def test_pinned_hashes_are_carried_into_the_report():
    report = pf.run(GOOD, factory(GOOD))
    assert report["pinned_runtime_zip_sha256"] == pf.RUNTIME_ZIP_SHA256
    assert report["pinned_core_lock_sha256"] == pf.CORE_LOCK_SHA256


def test_there_is_no_override_flag():
    # The absence of a bypass is a property worth asserting, not a comment.
    source = (TOOLS / "preprod_account_preflight.py").read_text(encoding="utf-8")
    for bypass in ("--force", "--skip", "ignore_errors", "allow_unsafe"):
        assert bypass not in source
