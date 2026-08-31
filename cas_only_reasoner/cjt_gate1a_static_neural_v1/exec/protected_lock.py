"""protected_lock.py -- the durable ONE-USE protected-campaign lock (GATE 1A.2 s.7).

States: PROTECTED_UNOPENED -> PROTECTED_RUNNING -> PROTECTED_BURNED.
Claiming RUNNING is ATOMIC (os.open O_CREAT|O_EXCL locally; a conditional
PutItem on AWS -- an atomic conditional operation, never check-then-write).
Success, failure, interruption, and timeout all end in BURNED; a second claim
is refused; a burned token can never be reused by another campaign (the lock
receipt binds the campaign id, approval digest, package commit, derivation,
claimant identity, claim time, final state, and result/failure digest).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

STATES = ("PROTECTED_UNOPENED", "PROTECTED_RUNNING", "PROTECTED_BURNED")


class ProtectedLockViolation(RuntimeError):
    pass


class LocalProtectedLock:
    """File-based backend for CPU conformance: atomicity via O_CREAT|O_EXCL."""

    def __init__(self, lock_dir: Path):
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _claim_path(self, campaign_id: str) -> Path:
        return self.lock_dir / f"{campaign_id}.claim"

    def _burn_path(self, campaign_id: str) -> Path:
        return self.lock_dir / f"{campaign_id}.burned"

    def state(self, campaign_id: str) -> str:
        if self._burn_path(campaign_id).is_file():
            return "PROTECTED_BURNED"
        if self._claim_path(campaign_id).is_file():
            return "PROTECTED_RUNNING"
        return "PROTECTED_UNOPENED"

    def claim(self, campaign_id: str, *, execution_approval_sha256: str,
              package_commit_sha: str, protected_derivation: str,
              claimant_identity: str, claim_utc: str) -> dict:
        if self._burn_path(campaign_id).is_file():
            raise ProtectedLockViolation(
                f"PROTECTED_ALREADY_BURNED: campaign {campaign_id} has consumed "
                "its one protected pass; a second read is refused forever")
        receipt = {"campaign_id": campaign_id,
                   "execution_approval_sha256": execution_approval_sha256,
                   "package_commit_sha": package_commit_sha,
                   "protected_derivation": protected_derivation,
                   "claimant_identity": claimant_identity,
                   "claim_utc": claim_utc, "state": "PROTECTED_RUNNING"}
        payload = (json.dumps(receipt, sort_keys=True, separators=(",", ":"))
                   + "\n").encode("utf-8")
        try:                                    # ATOMIC: exclusive create
            fd = os.open(self._claim_path(campaign_id),
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise ProtectedLockViolation(
                f"PROTECTED_CLAIM_RACE_REFUSED: campaign {campaign_id} is "
                "already claimed by another process") from None
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
        return receipt

    def burn(self, campaign_id: str, *, final_state_reason: str,
             result_or_failure_sha256: str) -> dict:
        claim_path = self._claim_path(campaign_id)
        if not claim_path.is_file():
            raise ProtectedLockViolation(
                f"BURN_WITHOUT_CLAIM: campaign {campaign_id} was never claimed")
        receipt = json.loads(claim_path.read_text(encoding="utf-8"))
        receipt.update({"state": "PROTECTED_BURNED",
                        "final_state_reason": final_state_reason,
                        "result_or_failure_sha256": result_or_failure_sha256})
        receipt["lock_receipt_sha256"] = hashlib.sha256(
            json.dumps({k: v for k, v in receipt.items()
                        if k != "lock_receipt_sha256"},
                       sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        with self._burn_path(campaign_id).open("w", encoding="utf-8",
                                               newline="\n") as fh:
            fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return receipt


class AwsProtectedLock:
    """DynamoDB conditional-write backend for the real campaign: PutItem with
    ConditionExpression attribute_not_exists(campaign_id) is a single atomic
    conditional operation -- never a check-then-write sequence. Code only in
    Gate 1A.2 (no AWS call is made locally)."""

    def __init__(self, table_name: str, region: str):
        self.table_name, self.region = table_name, region

    def _table(self):
        import boto3
        return boto3.resource("dynamodb", region_name=self.region) \
            .Table(self.table_name)

    def state(self, campaign_id: str) -> str:
        item = self._table().get_item(Key={"campaign_id": campaign_id}) \
            .get("Item")
        return item["state"] if item else "PROTECTED_UNOPENED"

    def claim(self, campaign_id: str, **bindings) -> dict:
        item = {"campaign_id": campaign_id, "state": "PROTECTED_RUNNING",
                **bindings}
        try:
            self._table().put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(campaign_id)")
        except Exception as exc:
            raise ProtectedLockViolation(
                f"PROTECTED_CLAIM_REFUSED (conditional write): {exc}") from exc
        return item

    def burn(self, campaign_id: str, *, final_state_reason: str,
             result_or_failure_sha256: str) -> dict:
        try:
            self._table().update_item(
                Key={"campaign_id": campaign_id},
                UpdateExpression="SET #s = :burned, final_state_reason = :r, "
                                 "result_or_failure_sha256 = :d",
                ConditionExpression="#s = :running",
                ExpressionAttributeNames={"#s": "state"},
                ExpressionAttributeValues={":burned": "PROTECTED_BURNED",
                                           ":running": "PROTECTED_RUNNING",
                                           ":r": final_state_reason,
                                           ":d": result_or_failure_sha256})
        except Exception as exc:
            raise ProtectedLockViolation(f"PROTECTED_BURN_FAILED: {exc}") from exc
        return {"campaign_id": campaign_id, "state": "PROTECTED_BURNED"}
