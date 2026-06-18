"""Persistent LIVE_LOCKED controller."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from cas_forex.schemas.live_lock import LiveLockReason, LiveLockState, UnlockReceipt
from cas_forex.time_utils import ensure_utc, utc_now


class LiveLockController:
    """Persists LIVE_LOCKED state and human unlock receipts."""

    def __init__(
        self,
        state_path: str | Path = "live_lock_state.json",
        unlock_log_path: str | Path = "live_lock_unlocks.jsonl",
        cooldown_seconds: int = 0,
    ):
        self.state_path = Path(state_path)
        self.unlock_log_path = Path(unlock_log_path)
        self.cooldown_seconds = cooldown_seconds

    def current(self) -> Optional[LiveLockState]:
        if not self.state_path.exists():
            return None
        try:
            return LiveLockState.model_validate_json(
                self.state_path.read_text(encoding="utf-8")
            )
        except Exception:
            return LiveLockState(
                lock_id="corrupt-state",
                reasons=[LiveLockReason.MANUAL_OPERATOR_LOCK],
                details={"error": "live lock state could not be decoded"},
            )

    def is_locked(self) -> bool:
        state = self.current()
        return bool(state and state.active)

    def lock(
        self,
        reasons: Iterable[LiveLockReason],
        evidence_refs: Optional[list[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> LiveLockState:
        existing = self.current()
        reason_list = list(reasons)
        if existing and existing.active:
            merged = list(dict.fromkeys([*existing.reasons, *reason_list]))
            existing.reasons = merged
            existing.evidence_refs = list(dict.fromkeys([
                *existing.evidence_refs,
                *(evidence_refs or []),
            ]))
            existing.details.update(details or {})
            state = existing
        else:
            state = LiveLockState(
                lock_id=str(uuid.uuid4()),
                reasons=reason_list,
                evidence_refs=evidence_refs or [],
                details=details or {},
            )
        self._write_state(state)
        return state

    def unlock(
        self,
        operator_id: str,
        signed_reason: str,
        evidence_receipt_hash: str,
        risk_snapshot: Dict[str, Any],
        next_session_id: str,
        open_positions_count: int = 0,
        override_open_positions: bool = False,
    ) -> UnlockReceipt:
        state = self.current()
        if state is None or not state.active:
            raise ValueError("No active LIVE_LOCKED state")
        if not operator_id or not signed_reason:
            raise ValueError("Unlock requires operator identity and signed reason")
        if not evidence_receipt_hash:
            raise ValueError("Unlock requires evidence receipt hash")
        if not risk_snapshot:
            raise ValueError("Unlock requires fresh risk snapshot")
        if open_positions_count > 0 and not override_open_positions:
            raise ValueError("Unlock requires closed positions or explicit override")
        if self.cooldown_seconds > 0:
            elapsed = utc_now() - ensure_utc(state.created_at)
            if elapsed < timedelta(seconds=self.cooldown_seconds):
                raise ValueError("Unlock cooldown has not elapsed")

        receipt = UnlockReceipt(
            unlock_id=str(uuid.uuid4()),
            lock_id=state.lock_id,
            operator_id=operator_id,
            signed_reason=signed_reason,
            evidence_receipt_hash=evidence_receipt_hash,
            next_session_id=next_session_id,
            override_open_positions=override_open_positions,
        )
        receipt.receipt_hash = self._receipt_hash(receipt)
        self.unlock_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.unlock_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.model_dump(mode="json"), sort_keys=True) + "\n")

        state.active = False
        state.cleared_at = utc_now()
        state.unlocked_by = operator_id
        state.unlock_reason = signed_reason
        state.effective_session_id = next_session_id
        self._write_state(state)
        return receipt

    def _write_state(self, state: LiveLockState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _receipt_hash(receipt: UnlockReceipt) -> str:
        payload = receipt.model_dump(mode="json", exclude={"receipt_hash"})
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
