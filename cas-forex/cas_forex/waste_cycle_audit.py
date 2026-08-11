"""Durable WASTE cycle state and audit log.

The in-memory heartbeat is useful for a live badge, but real-money readiness
needs a durable trail of what each WASTE tick decided. This module records the
latest cycle plus an append-only JSONL audit row. It does not authorize trades,
mint edge tokens, place orders, or move money.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "waste-runner-state.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-runner-audit.jsonl"
REPORT_KIND = "cas_forex_waste_cycle_audit"

CLAIM_BOUNDARY = (
    "WASTE cycle audit records WATCH/ANALYZE/STRATEGIZE/TEST/EXECUTE outcomes "
    "for observability and recovery. It does not authorize live trading, mint "
    "edge tokens, place orders, deposit, withdraw, transfer funds, or override "
    "owner gates."
)


class WasteCycleAuditStore:
    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
    ) -> None:
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)

    def record_cycle(
        self,
        result: Mapping[str, Any],
        *,
        running: bool,
        interval_seconds: int,
        mode: str,
        cycles_run: int,
        last_error: str = "",
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        setup = result.get("setup")
        edge = result.get("edge")
        execute_result = result.get("execute_result")
        compound = result.get("compound")
        record = {
            "report_kind": REPORT_KIND,
            "cycle_id": stable_ledger_id(
                "waste-cycle",
                generated_at,
                result.get("decision"),
                _attr(setup, "decision_ref"),
                _attr(edge, "status"),
            ),
            "generated_at": generated_at,
            "running": bool(running),
            "interval_seconds": int(interval_seconds),
            "mode": str(mode),
            "cycles_run": int(cycles_run),
            "decision": result.get("decision"),
            "reason": result.get("reason"),
            "stage_trace": list(result.get("stage_trace") or []),
            "watch_state": _safe_json(result.get("watch_state")),
            "analysis": _safe_json(result.get("analysis")),
            "candidate": _candidate_summary(setup),
            "edge": _edge_summary(edge),
            "execute_result": _safe_json(execute_result),
            "compound": _safe_json(compound),
            "learning_trade": bool(result.get("learning_trade", False)),
            "source": str(result.get("source") or "waste_runner"),
            "last_error": str(last_error or ""),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self._save_state(record)
        self._append_audit(record)
        return record

    def record_error(
        self,
        error: str,
        *,
        running: bool,
        interval_seconds: int,
        mode: str,
        cycles_run: int,
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        record = {
            "report_kind": REPORT_KIND,
            "cycle_id": stable_ledger_id("waste-cycle-error", generated_at, error),
            "generated_at": generated_at,
            "running": bool(running),
            "interval_seconds": int(interval_seconds),
            "mode": str(mode),
            "cycles_run": int(cycles_run),
            "decision": "BLOCKED",
            "reason": error,
            "stage_trace": ["blocked"],
            "watch_state": None,
            "analysis": None,
            "candidate": None,
            "edge": None,
            "execute_result": None,
            "compound": None,
            "last_error": str(error or ""),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self._save_state(record)
        self._append_audit(record)
        return record

    def build_status(self) -> dict[str, Any]:
        latest = self.latest_cycle()
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "latest_cycle": latest,
            "has_latest_cycle": latest is not None,
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": (
                "Inspect latest WASTE cycle evidence before restarting or scaling live operation."
                if latest
                else "No durable WASTE cycle has been recorded yet."
            ),
        }

    def latest_cycle(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, Mapping):
            return None
        latest = payload.get("latest_cycle")
        return dict(latest) if isinstance(latest, Mapping) else None

    def _save_state(self, record: Mapping[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "report_kind": REPORT_KIND,
            "updated_at": utc_now().isoformat(),
            "latest_cycle": dict(record),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)

    def _append_audit(self, record: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), sort_keys=True, default=str) + "\n")


def default_waste_cycle_audit_store() -> WasteCycleAuditStore:
    return WasteCycleAuditStore(DEFAULT_STATE_PATH, DEFAULT_AUDIT_PATH)


def build_waste_cycle_audit_status() -> dict[str, Any]:
    return default_waste_cycle_audit_store().build_status()


def _candidate_summary(setup: Any) -> dict[str, Any] | None:
    if setup is None:
        return None
    return {
        "symbol": _attr(setup, "symbol"),
        "timeframe": _attr(setup, "timeframe"),
        "direction": _attr(setup, "direction"),
        "entry": _float_attr(setup, "entry"),
        "stop_loss": _float_attr(setup, "stop_loss"),
        "take_profit": _float_attr(setup, "take_profit"),
        "signal_strength": _float_attr(setup, "signal_strength"),
        "regime": _attr(setup, "regime"),
        "decision_ref": _attr(setup, "decision_ref"),
        "entry_pair_count": len(getattr(setup, "entry_pairs", []) or []),
        "directional_hypothesis": _safe_json(getattr(setup, "directional_hypothesis", None)),
        "strategy_firewall": _safe_json(getattr(setup, "strategy_firewall", None)),
        "market_state_meta": _safe_json(getattr(setup, "market_state_meta", None)),
    }


def _edge_summary(edge: Any) -> dict[str, Any] | None:
    if edge is None:
        return None
    return {
        "status": _attr(edge, "status"),
        "measured_win_prob": _float_attr(edge, "measured_win_prob"),
        "null_p95": _float_attr(edge, "null_p95"),
        "threshold": _float_attr(edge, "threshold"),
        "has_edge_token": bool(_attr(edge, "edge_token")),
        "evaluated_at": _attr(edge, "evaluated_at"),
        "reason": _attr(edge, "reason"),
    }


def _attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _float_attr(obj: Any, name: str) -> float | None:
    value = _attr(obj, name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_json(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return _safe_json(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _safe_json(to_dict())
        except Exception:
            pass
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _safe_json(model_dump(mode="json"))
        except Exception:
            pass
    return str(value)
