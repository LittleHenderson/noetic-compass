"""Idempotent payout-attempt recovery ledger for CAS Forex.

Verified-profit sweep can eventually touch a real payment rail. A network drop
or app crash during that transfer must not create a second payout on retry. This
module writes a durable attempt record before provider contact and then updates
it with the provider outcome.

It does not move money, authorize payout automation, or invent provider
receipts. It only records and gates retry behavior.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTEMPT_PATH = REPO_ROOT / "runtime" / "payout-attempts.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "payout-attempts-audit.jsonl"

REPORT_KIND = "cas_forex_payout_recovery"
STATUS_RESERVED = "RESERVED"
STATUS_PENDING = "PENDING"
STATUS_SETTLED = "SETTLED"
STATUS_FAILED = "FAILED"
STATUS_BLOCKED = "BLOCKED"
STATUS_RECOVERY_REQUIRED = "RECOVERY_REQUIRED"

CLAIM_BOUNDARY = (
    "Payout recovery is an idempotency and audit ledger for payout attempts. "
    "It reserves a transfer key before provider contact and records the provider "
    "result so retries do not duplicate withdrawals. It does not move money, "
    "create provider receipts, authorize payout automation, deposit, withdraw, "
    "or transfer funds by itself."
)


class PayoutRecoveryError(ValueError):
    """Raised when a payout attempt cannot be recorded."""


class PayoutAttemptStore:
    def __init__(
        self,
        path: Path | str = DEFAULT_ATTEMPT_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
    ) -> None:
        self.path = Path(path)
        self.audit_path = Path(audit_path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def build_status(self) -> dict[str, Any]:
        attempts = self._load()
        latest = _latest_attempt(attempts)
        pending = [
            item
            for item in attempts.values()
            if item.get("status") in {STATUS_RESERVED, STATUS_PENDING, STATUS_RECOVERY_REQUIRED}
        ]
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "attempt_count": len(attempts),
            "pending_count": len(pending),
            "pending_amount_usd": round(
                sum(float(item.get("amount_usd") or 0.0) for item in pending),
                2,
            ),
            "has_pending_recovery": bool(pending),
            "latest_attempt": latest,
            "pending_attempts": pending,
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": (
                "Resolve pending payout attempts against provider/bank evidence before retrying a sweep."
                if pending
                else "No pending payout recovery attempts are open."
            ),
        }

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        key = _clean_key(idempotency_key)
        attempt = self._load().get(key)
        return dict(attempt) if attempt else None

    def reserve(
        self,
        idempotency_key: str,
        *,
        amount_usd: float,
        destination_id: str | None,
        preview: Mapping[str, Any],
        kind: str = "payout",
        source_id: str | None = None,
        purpose: str = "verified_profit_sweep",
        policy_id: str | None = None,
        daily_cap_usd: float | None = None,
        anomaly_checks: Mapping[str, Any] | None = None,
        authority_mode: str = "MANUAL",
    ) -> tuple[dict[str, Any], bool]:
        """Reserve an attempt. Returns (attempt, can_call_provider)."""
        key = _clean_key(idempotency_key)
        now = utc_now()
        amount = round(float(amount_usd), 2)
        with self._locked_attempts() as attempts:
            existing = attempts.get(key)
            if existing:
                status = existing.get("status")
                if status in {
                    STATUS_SETTLED,
                    STATUS_PENDING,
                    STATUS_BLOCKED,
                    STATUS_FAILED,
                    STATUS_RECOVERY_REQUIRED,
                }:
                    return existing, False
                existing["status"] = STATUS_RECOVERY_REQUIRED
                existing["updated_at"] = now.isoformat()
                existing["recovery_reason"] = (
                    "A prior provider attempt was reserved without a final result. "
                    "Reconcile provider/bank evidence before any retry."
                )
                attempts[key] = existing
                self._save(attempts)
                self._audit("PAYOUT_RECOVERY_REQUIRED", existing)
                return existing, False

            day = now.date().isoformat()
            reserved_today = round(
                sum(
                    float(item.get("amount_usd") or 0.0)
                    for item in attempts.values()
                    if str(item.get("created_at") or "")[:10] == day
                    and item.get("status")
                    in {
                        STATUS_RESERVED,
                        STATUS_PENDING,
                        STATUS_SETTLED,
                        STATUS_RECOVERY_REQUIRED,
                    }
                ),
                2,
            )
            if daily_cap_usd is not None and reserved_today + amount > float(daily_cap_usd):
                attempt = {
                    "attempt_id": stable_ledger_id("payout-attempt", key),
                    "idempotency_key": key,
                    "status": STATUS_BLOCKED,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "amount_usd": amount,
                    "kind": str(kind),
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "purpose": purpose,
                    "policy_id": policy_id,
                    "authority_mode": str(authority_mode or "MANUAL").upper(),
                    "daily_cap_usd": round(float(daily_cap_usd), 2),
                    "reserved_today_usd": reserved_today,
                    "movement_reason": (
                        f"daily movement cap {float(daily_cap_usd):.2f} would be exceeded"
                    ),
                    "anomaly_checks": dict(anomaly_checks or {}),
                    "claim_boundary": CLAIM_BOUNDARY,
                }
                attempts[key] = attempt
                self._save(attempts)
                self._audit("PAYOUT_DAILY_CAP_BLOCKED", attempt)
                return attempt, False

            attempt = {
                "attempt_id": stable_ledger_id("payout-attempt", key),
                "idempotency_key": key,
                "status": STATUS_RESERVED,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "amount_usd": amount,
                "kind": str(kind),
                "source_id": source_id,
                "destination_id": destination_id,
                "purpose": purpose,
                "policy_id": policy_id,
                "authority_mode": str(authority_mode or "MANUAL").upper(),
                "daily_cap_usd": round(float(daily_cap_usd), 2)
                if daily_cap_usd is not None
                else None,
                "reserved_today_usd": reserved_today,
                "preview_status": preview.get("status"),
                "preview_reason": preview.get("reason"),
                "provider_reference": None,
                "provider_status": None,
                "provider_is_real": None,
                "movement_status": None,
                "movement_reason": None,
                "anomaly_checks": dict(anomaly_checks or {}),
                "claim_boundary": CLAIM_BOUNDARY,
            }
            attempts[key] = attempt
            self._save(attempts)
            self._audit("PAYOUT_ATTEMPT_RESERVED", attempt)
            return attempt, True

    def record_result(
        self,
        idempotency_key: str,
        *,
        movement: Mapping[str, Any] | None,
        status: str | None = None,
    ) -> dict[str, Any]:
        key = _clean_key(idempotency_key)
        with self._locked_attempts() as attempts:
            attempt = dict(
                attempts.get(key)
                or {"idempotency_key": key, "created_at": utc_now().isoformat()}
            )
            movement_payload = dict(movement or {})
            receipt = movement_payload.get("provider_receipt") or {}
            movement_status = status or str(movement_payload.get("status") or STATUS_FAILED)
            balance_snapshot = movement_payload.get("before_after_balance_snapshot")
            balance_snapshot_complete = bool(
                isinstance(balance_snapshot, Mapping)
                and balance_snapshot.get("complete") is True
            )
            real_provider = bool(receipt.get("is_real"))
            evidence_complete = bool(
                receipt.get("reference")
                and movement_payload.get("ledger_entry")
                and movement_payload.get("event_hash")
                and balance_snapshot
                and (balance_snapshot_complete or not real_provider)
            )
            if movement_status == STATUS_SETTLED and evidence_complete:
                attempt_status = STATUS_SETTLED
                recovery_reason = None
            elif movement_status == STATUS_SETTLED:
                attempt_status = STATUS_RECOVERY_REQUIRED
                recovery_reason = (
                    "Provider reported settlement but receipt/ledger/event-hash/balance "
                    "evidence is incomplete. Reconcile before another movement."
                )
            elif movement_status == STATUS_PENDING:
                attempt_status = STATUS_PENDING
                recovery_reason = (
                    "Provider accepted the movement but final settlement is pending. "
                    "Reconcile webhook/provider evidence before another movement."
                )
            elif bool(movement_payload.get("provider_outcome_uncertain")):
                attempt_status = STATUS_RECOVERY_REQUIRED
                recovery_reason = (
                    "Provider contact may have escaped without a final receipt. "
                    "Do not retry until provider/bank evidence is reconciled."
                )
            elif movement_status == STATUS_BLOCKED:
                attempt_status = STATUS_BLOCKED
                recovery_reason = None
            else:
                attempt_status = STATUS_FAILED
                recovery_reason = None
            attempt.update(
                {
                    "status": attempt_status,
                    "updated_at": utc_now().isoformat(),
                    "provider_reference": receipt.get("reference"),
                    "provider_status": receipt.get("provider_status") or receipt.get("status"),
                    "provider_receipt_status": receipt.get("status"),
                    "provider_is_real": receipt.get("is_real"),
                    "movement_status": movement_status,
                    "movement_reason": movement_payload.get("reason"),
                    "evidence_complete": evidence_complete,
                    "provider_receipt": dict(receipt),
                    "ledger_entry": movement_payload.get("ledger_entry"),
                    "event_hash": movement_payload.get("event_hash"),
                    "before_after_balance_snapshot": movement_payload.get(
                        "before_after_balance_snapshot"
                    ),
                    "balance_snapshot_complete": balance_snapshot_complete,
                    "movement": movement_payload,
                }
            )
            if recovery_reason:
                attempt["recovery_reason"] = recovery_reason
            else:
                attempt.pop("recovery_reason", None)
            attempts[key] = attempt
            self._save(attempts)
            self._audit("PAYOUT_ATTEMPT_RESULT", attempt)
            return attempt

    def record_blocked(
        self,
        idempotency_key: str,
        *,
        amount_usd: float,
        kind: str,
        source_id: str | None,
        destination_id: str | None,
        purpose: str,
        policy_id: str | None,
        authority_mode: str,
        reason: str,
        anomaly_checks: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = _clean_key(idempotency_key)
        now = utc_now().isoformat()
        with self._locked_attempts() as attempts:
            existing = attempts.get(key)
            if existing:
                return existing
            attempt = {
                "attempt_id": stable_ledger_id("payout-attempt", key),
                "idempotency_key": key,
                "status": STATUS_BLOCKED,
                "created_at": now,
                "updated_at": now,
                "amount_usd": round(float(amount_usd), 2),
                "kind": str(kind),
                "source_id": source_id,
                "destination_id": destination_id,
                "purpose": purpose,
                "policy_id": policy_id,
                "authority_mode": str(authority_mode or "MANUAL").upper(),
                "movement_status": STATUS_BLOCKED,
                "movement_reason": str(reason),
                "anomaly_checks": dict(anomaly_checks or {}),
                "claim_boundary": CLAIM_BOUNDARY,
            }
            attempts[key] = attempt
            self._save(attempts)
            self._audit("PAYOUT_ATTEMPT_BLOCKED", attempt)
            return attempt

    def resolve(
        self,
        idempotency_key: str,
        *,
        owner_status: str,
        provider_reference: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        key = _clean_key(idempotency_key)
        status = str(owner_status or "").upper()
        if status == STATUS_SETTLED:
            raise PayoutRecoveryError(
                "Owner review cannot declare a movement SETTLED. Settlement requires "
                "provider reconciliation plus receipt, ledger, event-hash, and matching "
                "before/after balance evidence."
            )
        if status not in {STATUS_FAILED, STATUS_BLOCKED}:
            raise PayoutRecoveryError("owner_status must be FAILED or BLOCKED")
        with self._locked_attempts() as attempts:
            if key not in attempts:
                raise PayoutRecoveryError(f"No payout attempt found for idempotency key {key}")
            attempt = dict(attempts[key])
            attempt.update(
                {
                    "status": status,
                    "updated_at": utc_now().isoformat(),
                    "owner_resolved_at": utc_now().isoformat(),
                    "owner_resolution_notes": str(notes or "").strip(),
                    "provider_reference": provider_reference or attempt.get("provider_reference"),
                }
            )
            attempts[key] = attempt
            self._save(attempts)
            self._audit("PAYOUT_ATTEMPT_OWNER_RESOLVED", attempt)
            return attempt

    def settled_total_usd(
        self,
        *,
        purpose: str | None = None,
        policy_id: str | None = None,
        destination_id: str | None = None,
    ) -> float:
        """Return durably settled movement total for an entitlement/policy scope."""

        attempts = self._load()
        total = 0.0
        for item in attempts.values():
            if item.get("status") != STATUS_SETTLED:
                continue
            if purpose is not None and item.get("purpose") != purpose:
                continue
            if policy_id is not None and item.get("policy_id") != policy_id:
                continue
            if destination_id is not None and item.get("destination_id") != destination_id:
                continue
            total += float(item.get("amount_usd") or 0.0)
        return round(total, 2)

    def total_for_utc_day(
        self,
        *,
        day: str | None = None,
        include_unresolved: bool = True,
    ) -> float:
        target = day or utc_now().date().isoformat()
        statuses = {STATUS_SETTLED}
        if include_unresolved:
            statuses.update({STATUS_RESERVED, STATUS_PENDING, STATUS_RECOVERY_REQUIRED})
        return round(
            sum(
                float(item.get("amount_usd") or 0.0)
                for item in self._load().values()
                if str(item.get("created_at") or "")[:10] == target
                and item.get("status") in statuses
            ),
            2,
        )

    @contextlib.contextmanager
    def _locked_attempts(self) -> Iterator[dict[str, dict[str, Any]]]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            _lock_file(handle)
            try:
                yield self._load()
            finally:
                _unlock_file(handle)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
        return {str(k): dict(v) for k, v in (attempts or {}).items() if isinstance(v, Mapping)}

    def _save(self, attempts: Mapping[str, Mapping[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "report_kind": REPORT_KIND,
            "updated_at": utc_now().isoformat(),
            "attempts": {str(k): dict(v) for k, v in attempts.items()},
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.path)

    def _audit(self, action: str, payload: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "audit_id": stable_ledger_id("payout-recovery-audit", action, utc_now().isoformat(), json.dumps(payload, sort_keys=True, default=str)),
            "action": action,
            "timestamp": utc_now().isoformat(),
            "payload": dict(payload),
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def default_payout_attempt_store() -> PayoutAttemptStore:
    return PayoutAttemptStore(DEFAULT_ATTEMPT_PATH, DEFAULT_AUDIT_PATH)


def build_payout_recovery_status() -> dict[str, Any]:
    return default_payout_attempt_store().build_status()


def _clean_key(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PayoutRecoveryError("idempotency_key is required")
    return text


def _latest_attempt(attempts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    if not attempts:
        return None
    return dict(sorted(attempts.values(), key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""))[-1])


def _lock_file(handle: Any) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    except ImportError:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle: Any) -> None:
    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
