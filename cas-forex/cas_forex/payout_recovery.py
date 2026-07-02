"""Idempotent payout-attempt recovery ledger for CAS Forex.

Verified-profit sweep can eventually touch a real payment rail. A network drop
or app crash during that transfer must not create a second payout on retry. This
module writes a durable attempt record before provider contact and then updates
it with the provider outcome.

It does not move money, authorize payout automation, or invent provider
receipts. It only records and gates retry behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTEMPT_PATH = REPO_ROOT / "runtime" / "payout-attempts.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "payout-attempts-audit.jsonl"

REPORT_KIND = "cas_forex_payout_recovery"
STATUS_RESERVED = "RESERVED"
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

    def build_status(self) -> dict[str, Any]:
        attempts = self._load()
        latest = _latest_attempt(attempts)
        pending = [
            item
            for item in attempts.values()
            if item.get("status") in {STATUS_RESERVED, STATUS_RECOVERY_REQUIRED}
        ]
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "attempt_count": len(attempts),
            "pending_count": len(pending),
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

    def reserve(
        self,
        idempotency_key: str,
        *,
        amount_usd: float,
        destination_id: str | None,
        preview: Mapping[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """Reserve an attempt. Returns (attempt, can_call_provider)."""
        key = _clean_key(idempotency_key)
        attempts = self._load()
        existing = attempts.get(key)
        if existing:
            status = existing.get("status")
            if status == STATUS_SETTLED:
                return existing, False
            if status in {STATUS_RESERVED, STATUS_RECOVERY_REQUIRED}:
                existing["status"] = STATUS_RECOVERY_REQUIRED
                existing["updated_at"] = utc_now().isoformat()
                existing["recovery_reason"] = "Retry blocked until provider/bank evidence resolves the prior attempt."
                attempts[key] = existing
                self._save(attempts)
                self._audit("PAYOUT_RECOVERY_REQUIRED", existing)
                return existing, False
        attempt = {
            "attempt_id": stable_ledger_id("payout-attempt", key),
            "idempotency_key": key,
            "status": STATUS_RESERVED,
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "amount_usd": round(float(amount_usd), 2),
            "destination_id": destination_id,
            "preview_status": preview.get("status"),
            "preview_reason": preview.get("reason"),
            "provider_reference": None,
            "provider_status": None,
            "provider_is_real": None,
            "movement_status": None,
            "movement_reason": None,
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
        attempts = self._load()
        attempt = dict(attempts.get(key) or {"idempotency_key": key, "created_at": utc_now().isoformat()})
        receipt = (movement or {}).get("provider_receipt") or {}
        movement_status = status or str((movement or {}).get("status") or STATUS_FAILED)
        attempt.update(
            {
                "status": STATUS_SETTLED if movement_status == STATUS_SETTLED else STATUS_FAILED,
                "updated_at": utc_now().isoformat(),
                "provider_reference": receipt.get("reference"),
                "provider_status": receipt.get("status"),
                "provider_is_real": receipt.get("is_real"),
                "movement_status": movement_status,
                "movement_reason": (movement or {}).get("reason"),
                "movement": dict(movement or {}),
            }
        )
        attempts[key] = attempt
        self._save(attempts)
        self._audit("PAYOUT_ATTEMPT_RESULT", attempt)
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
        if status not in {STATUS_SETTLED, STATUS_FAILED, STATUS_BLOCKED}:
            raise PayoutRecoveryError("owner_status must be SETTLED, FAILED, or BLOCKED")
        attempts = self._load()
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
