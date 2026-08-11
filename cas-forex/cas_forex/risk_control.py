"""Owner risk control: set ANY concurrent-trade count and ANY loss cap — or none.

The pre-execution risk gate enforces hard caps that, until now, came only from
static config (max 5 open positions, 0.5 total lots, etc.) with no way for the
owner to change them at runtime — not even on paper. This module is the
owner-driven override for those caps, mirroring ``broker_control``:

  - ``max_concurrent_trades`` — open-position count cap (and per-symbol cap).
  - ``max_total_exposure_lots`` — total lots cap.
  - ``max_loss_cap_usd`` — floating-loss cap in USD.
  - ``max_drawdown_pct`` — drawdown-from-equity-peak cap.

Each can be set to a number (a cap) or to ``None`` (UNLIMITED — no cap).
``execution_guard.caps_from_config`` consults this, so the overrides take effect
immediately on the next dispatch with no restart.

Anti-impulse rule: tightening caps is always easy. When real-money controls are
armed, loosening or removing a cap must go through an explicit confirmation
phrase at the route/owner-command layer. The owner can still do it; the app just
refuses to make a high-amplification change look like an ordinary save.

Overrides are local durable state for the single-owner cockpit. They persist in
``runtime/risk-control-overrides.json`` so an API restart cannot silently change
which caps outrank the AI Operator's dials. Static config values remain fallback
defaults, and an explicit reset removes the durable override file.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import ensure_utc, utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "runtime" / "risk-control-overrides.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "risk-control-audit.jsonl"

# The override keys. A key present in _OVERRIDES means "explicitly set by the
# owner"; its value is a number (cap) or None (unlimited / no cap).
_RISK_KEYS = (
    "max_concurrent_trades",
    "max_total_exposure_lots",
    "max_loss_cap_usd",
    "max_drawdown_pct",
)

# Sentinel distinct from None (None means "unlimited"); used to mean "not set".
_UNSET = object()

_OVERRIDES: dict[str, Any] = {}
_OVERRIDES_LOADED = False
_OVERRIDE_PATH: Path | None = DEFAULT_OVERRIDE_PATH
_OVERRIDE_LOCK = threading.RLock()
_OVERRIDE_LOAD_ERROR: str | None = None
_OVERRIDE_LOADED_FROM_DISK = False
_OVERRIDE_LAST_SAVED_AT: str | None = None
_AUDIT_PATH = DEFAULT_AUDIT_PATH
_AUDIT_LOCK = threading.RLock()

RISK_LOOSEN_CONFIRM_PHRASE = "CONFIRM RISK LOOSEN"
RISK_LOOSEN_COOLDOWN_SECONDS = 30 * 60
RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS = 20
RISK_LOOSEN_JOURNAL_PROMPT = (
    "Before loosening or removing a risk cap, record why this is not revenge "
    "trading, FOMO, overconfidence, or chasing losses; include the expected "
    "account impact and the condition that should restore the tighter cap."
)
RISK_CONTROL_AUDIT_REPORT_KIND = "cas_forex_risk_control_audit"
RISK_CONTROL_AUDIT_CLAIM_BOUNDARY = (
    "Risk-control audit records owner risk-cap changes for accountability. "
    "It does not place orders, authorize live trading, move broker funds, or "
    "override the dispatch risk gate."
)
_HIGH_STAKES_LIVE_KEYS = (
    "live_mode",
    "owner_enable_live_trading",
    "live_trading_licensed",
    "owner_enable_broker_accept",
    "owner_enable_auto_deposit",
    "owner_enable_bank_card_movement",
    "owner_enable_payout_automation",
)


@dataclass(frozen=True)
class RiskControl:
    # None on any field means UNLIMITED (no cap on that dimension).
    max_concurrent_trades: Optional[int]
    max_total_exposure_lots: Optional[float]
    max_loss_cap_usd: Optional[float]
    max_drawdown_pct: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_concurrent_trades": self.max_concurrent_trades,
            "max_total_exposure_lots": self.max_total_exposure_lots,
            "max_loss_cap_usd": self.max_loss_cap_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "unlimited": {
                "concurrent_trades": self.max_concurrent_trades is None,
                "total_exposure_lots": self.max_total_exposure_lots is None,
                "loss_cap_usd": self.max_loss_cap_usd is None,
                "drawdown_pct": self.max_drawdown_pct is None,
            },
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _as_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def _as_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _pytest_default_store_isolated() -> bool:
    return bool(
        os.environ.get("PYTEST_CURRENT_TEST")
        and _OVERRIDE_PATH == DEFAULT_OVERRIDE_PATH
    )


def _coerce_persisted_override(key: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{key} cannot be boolean")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{key} must be a finite non-negative number or null")
    if key == "max_concurrent_trades":
        integer = int(number)
        if number != integer:
            raise ValueError("max_concurrent_trades must be an integer or null")
        return integer
    return number


def _load_overrides() -> None:
    """Load durable explicit owner overrides once per process."""

    global _OVERRIDES_LOADED, _OVERRIDE_LOAD_ERROR, _OVERRIDE_LOADED_FROM_DISK
    with _OVERRIDE_LOCK:
        if _OVERRIDES_LOADED:
            return
        _OVERRIDES_LOADED = True
        _OVERRIDE_LOAD_ERROR = None
        _OVERRIDE_LOADED_FROM_DISK = False
        if _pytest_default_store_isolated():
            return
        if _OVERRIDE_PATH is None or not _OVERRIDE_PATH.exists():
            return
        try:
            payload = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
            raw = payload.get("overrides") if isinstance(payload, Mapping) else None
            if not isinstance(raw, Mapping):
                raise ValueError("override file is missing an overrides object")
            loaded: dict[str, Any] = {}
            for key, value in raw.items():
                if key not in _RISK_KEYS:
                    continue
                loaded[key] = _coerce_persisted_override(key, value)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            _OVERRIDE_LOAD_ERROR = f"{type(exc).__name__}: {exc}"
            return
        _OVERRIDES.clear()
        _OVERRIDES.update(loaded)
        _OVERRIDE_LOADED_FROM_DISK = True


def _save_overrides_snapshot(overrides: Mapping[str, Any]) -> None:
    """Atomically persist a proposed snapshot before it becomes active in memory."""

    global _OVERRIDE_LAST_SAVED_AT, _OVERRIDE_LOAD_ERROR
    if _OVERRIDE_PATH is None or _pytest_default_store_isolated():
        return
    if not overrides:
        try:
            _OVERRIDE_PATH.unlink()
        except FileNotFoundError:
            pass
        _OVERRIDE_LAST_SAVED_AT = utc_now().isoformat()
        _OVERRIDE_LOAD_ERROR = None
        return
    generated_at = utc_now().isoformat()
    payload = {
        "report_kind": "cas_forex_risk_control_overrides",
        "schema_version": "risk_control_overrides.v1",
        "generated_at": generated_at,
        "overrides": {
            key: overrides[key]
            for key in _RISK_KEYS
            if key in overrides
        },
        "explicit_override_keys": [key for key in _RISK_KEYS if key in overrides],
        "claim_boundary": (
            "Durable owner risk-cap authority for the single-owner CAS Forex cockpit. "
            "This file does not place an order or move money. The dispatch guard "
            "re-reads these values through risk-control precedence on every action."
        ),
    }
    _OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _OVERRIDE_PATH.with_suffix(_OVERRIDE_PATH.suffix + ".tmp")
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            tmp.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp.replace(_OVERRIDE_PATH)
            _OVERRIDE_LAST_SAVED_AT = generated_at
            _OVERRIDE_LOAD_ERROR = None
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1 * (attempt + 1))
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    if last_error is not None:
        raise last_error


def set_risk_control_override_store_for_tests(path: Path | str | None) -> None:
    """Point persistence at a test file, or disable it with ``None``."""

    global _OVERRIDE_PATH, _OVERRIDES_LOADED, _OVERRIDE_LOAD_ERROR
    global _OVERRIDE_LOADED_FROM_DISK, _OVERRIDE_LAST_SAVED_AT
    with _OVERRIDE_LOCK:
        _OVERRIDE_PATH = Path(path) if path is not None else None
        _OVERRIDES.clear()
        _OVERRIDES_LOADED = False
        _OVERRIDE_LOAD_ERROR = None
        _OVERRIDE_LOADED_FROM_DISK = False
        _OVERRIDE_LAST_SAVED_AT = None


def set_risk_control_audit_path_for_tests(path: Path | str | None) -> None:
    """Redirect the append-only risk-control audit during tests."""
    global _AUDIT_PATH
    _AUDIT_PATH = Path(path) if path is not None else DEFAULT_AUDIT_PATH


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(v) for v in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _safe_json(to_dict())
        except Exception:
            pass
    return str(value)


def _append_risk_control_audit(
    *,
    action: str,
    source: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    changes: list[Mapping[str, Any]],
    assessment: Mapping[str, Any] | None = None,
    confirm_supplied: bool = False,
    journal_reason: str = "",
    journal_review: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = utc_now().isoformat()
    safe_changes = _safe_json(changes)
    record = {
        "report_kind": RISK_CONTROL_AUDIT_REPORT_KIND,
        "audit_id": stable_ledger_id(
            "risk-control-audit",
            action,
            source,
            generated_at,
            json.dumps(safe_changes, sort_keys=True, default=str),
        ),
        "at": generated_at,
        "action": str(action),
        "source": str(source or "risk_control"),
        "before": _safe_json(before),
        "after": _safe_json(after),
        "changes": safe_changes,
        "assessment": _safe_json(assessment or {}),
        "confirm_supplied": bool(confirm_supplied),
        "journal_reason": str(journal_reason or ""),
        "journal_review": _safe_json(journal_review or {}),
        "external_money_movement": False,
        "audit_path": str(_AUDIT_PATH),
        "claim_boundary": RISK_CONTROL_AUDIT_CLAIM_BOUNDARY,
    }
    with _AUDIT_LOCK:
        _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                with _AUDIT_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
                _notify_risk_control_change(record)
                return record
            except OSError as exc:
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            record["audit_write_error"] = str(last_error)
    return record


def _notify_risk_control_change(record: Mapping[str, Any]) -> None:
    try:
        from cas_forex.critical_notifications import (
            build_risk_control_changed_event,
            emit_critical_notification,
        )

        emit_critical_notification(
            build_risk_control_changed_event(record),
            source=str(record.get("source") or "risk_control"),
        )
    except Exception:
        return


def recent_risk_control_audit(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent risk-control audit rows, newest first."""
    with _AUDIT_LOCK:
        if not _AUDIT_PATH.exists():
            return []
        try:
            lines = _AUDIT_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(limit)):]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return list(reversed(rows))


def _parse_audit_time(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _loosening_changes_from_audit(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    changes = row.get("changes")
    if not isinstance(changes, list):
        return []
    out: list[dict[str, Any]] = []
    for item in changes:
        if isinstance(item, Mapping) and str(item.get("posture") or "").lower() == "loosen":
            out.append(dict(item))
    return out


def risk_loosening_cooldown_status(
    *,
    loosening_changes: list[Mapping[str, Any]] | None = None,
    real_money_controls: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Report whether a recent successful loosening blocks another loosening."""
    requested = bool(loosening_changes)
    applies = bool(requested and real_money_controls)
    current_time = ensure_utc(now or utc_now())
    status = {
        "report_kind": "cas_forex_risk_loosening_cooldown",
        "applies": applies,
        "active": False,
        "cooldown_seconds": RISK_LOOSEN_COOLDOWN_SECONDS,
        "remaining_seconds": 0,
        "last_loosened_at": None,
        "last_loosened_changes": [],
        "detail": (
            "Cooldown applies only to additional loosening/removal of caps while real-money controls are armed."
        ),
    }
    if not applies:
        return status
    for row in recent_risk_control_audit(100):
        changes = _loosening_changes_from_audit(row)
        if not changes:
            continue
        at = _parse_audit_time(row.get("at"))
        if at is None:
            continue
        age = max(0.0, (current_time - at).total_seconds())
        remaining = max(0, int(RISK_LOOSEN_COOLDOWN_SECONDS - age))
        status["last_loosened_at"] = at.isoformat()
        status["last_loosened_changes"] = changes
        if remaining > 0:
            status["active"] = True
            status["remaining_seconds"] = remaining
            status["detail"] = (
                "Another risk loosening is cooling down after a recent successful loosening. "
                "Tightening caps remains available."
            )
        return status
    return status


def risk_loosening_journal_review(
    reason: Any = "",
    *,
    loosening_changes: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    required = bool(loosening_changes)
    text = str(reason or "").strip()
    lowered = text.lower()
    blockers: list[str] = []
    if required:
        if len(text) < RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS:
            blockers.append(
                f"reason must be at least {RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS} characters"
            )
        if "no reason" in lowered:
            blockers.append("reason cannot say no reason was given")
    return {
        "report_kind": "cas_forex_risk_loosening_journal",
        "required": required,
        "satisfied": not blockers,
        "reason_length": len(text),
        "minimum_reason_length": RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS,
        "blockers": blockers,
        "prompt": RISK_LOOSEN_JOURNAL_PROMPT if required else "",
        "claim_boundary": (
            "Risk-cap journaling gates cap-loosening writes only. It does not "
            "authorize live trading, place orders, or prove a looser cap is profitable."
        ),
    }


def build_risk_control_audit_report(limit: int = 25) -> dict[str, Any]:
    return {
        "report_kind": RISK_CONTROL_AUDIT_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "audit_path": str(_AUDIT_PATH),
        "rows": recent_risk_control_audit(limit),
        "claim_boundary": RISK_CONTROL_AUDIT_CLAIM_BOUNDARY,
    }


def resolve_risk_control_snapshot(
    config: Any,
    overrides: Mapping[str, Any],
) -> RiskControl:
    """Resolve an explicit override snapshot without mutating runtime state."""

    config = _resolve_config(config)

    def pick_int(key: str, cfg_attr: str) -> Optional[int]:
        if key in overrides:
            return _as_int_or_none(overrides[key])
        return _as_int_or_none(getattr(config, cfg_attr, None))

    def pick_float(key: str, cfg_attr: str) -> Optional[float]:
        if key in overrides:
            return _as_float_or_none(overrides[key])
        return _as_float_or_none(getattr(config, cfg_attr, None))

    return RiskControl(
        max_concurrent_trades=pick_int("max_concurrent_trades", "max_open_positions"),
        max_total_exposure_lots=pick_float("max_total_exposure_lots", "max_total_exposure_lots"),
        # No persistent config attr for a USD floating-loss cap today → default None.
        max_loss_cap_usd=pick_float("max_loss_cap_usd", "max_floating_loss_usd"),
        max_drawdown_pct=pick_float("max_drawdown_pct", "max_weekly_drawdown_pct"),
    )


def owner_override_snapshot() -> dict[str, Any]:
    _load_overrides()
    with _OVERRIDE_LOCK:
        return dict(_OVERRIDES)


def resolve_risk_control(config: Any = None) -> RiskControl:
    """Effective owner layer: explicit override over static config fallback."""

    return resolve_risk_control_snapshot(config, owner_override_snapshot())


def _config_default_risk_control(config: Any = None) -> RiskControl:
    """Static config defaults, ignoring any runtime owner overrides."""
    config = _resolve_config(config)
    return RiskControl(
        max_concurrent_trades=_as_int_or_none(getattr(config, "max_open_positions", None)),
        max_total_exposure_lots=_as_float_or_none(getattr(config, "max_total_exposure_lots", None)),
        # No persistent config attr for a USD floating-loss cap today â†’ default None.
        max_loss_cap_usd=_as_float_or_none(getattr(config, "max_floating_loss_usd", None)),
        max_drawdown_pct=_as_float_or_none(getattr(config, "max_weekly_drawdown_pct", None)),
    )


def set_risk_control_overrides(
    *,
    max_concurrent_trades: Any = _UNSET,
    max_total_exposure_lots: Any = _UNSET,
    max_loss_cap_usd: Any = _UNSET,
    max_drawdown_pct: Any = _UNSET,
    audit_source: str | None = None,
    audit_confirm_supplied: bool = False,
    audit_assessment: Mapping[str, Any] | None = None,
    audit_journal_reason: str = "",
) -> RiskControl:
    """Set owner risk overrides. Pass a number for a cap, or ``None`` for UNLIMITED.

    Only arguments you actually pass are changed; omit one to leave it as-is.
    Negative caps are rejected; ``None`` (unlimited) is always allowed.
    """
    _load_overrides()
    pending: list[tuple[str, Any]] = [
        ("max_concurrent_trades", max_concurrent_trades),
        ("max_total_exposure_lots", max_total_exposure_lots),
        ("max_loss_cap_usd", max_loss_cap_usd),
        ("max_drawdown_pct", max_drawdown_pct),
    ]
    pending = [
        (key, _coerce_persisted_override(key, value))
        if value is not _UNSET
        else (key, value)
        for key, value in pending
    ]
    provided = {key: value for key, value in pending if value is not _UNSET}
    before = resolve_risk_control().to_dict() if audit_source and provided else {}
    assessment = (
        dict(audit_assessment)
        if audit_assessment is not None
        else (
            assess_risk_control_update(provided, journal_reason=audit_journal_reason)
            if audit_source and provided
            else {}
        )
    )
    assessed_changes = {
        str(row.get("key")): dict(row)
        for row in (assessment.get("changes") or [])
        if isinstance(row, Mapping) and row.get("key")
    }
    change_rows = [
        assessed_changes.get(
            key,
            {
                "key": key,
                "before": before.get(key),
                "after": value,
                "posture": _cap_posture(before.get(key), value),
                "owner_layer_posture": _cap_posture(before.get(key), value),
                "unlimited_after": value is None,
            },
        )
        for key, value in provided.items()
    ] if before else []
    effective_loosening = [
        dict(row)
        for row in (assessment.get("loosening_changes") or [])
        if isinstance(row, Mapping)
    ]
    journal_review = (
        risk_loosening_journal_review(
            audit_journal_reason,
            loosening_changes=effective_loosening,
        )
        if audit_source and provided
        else {}
    )
    if journal_review.get("required") and not journal_review.get("satisfied"):
        raise ValueError(
            "Loosening/removing risk caps requires an anti-impulse journal reason before "
            f"the override can change: {'; '.join(journal_review.get('blockers') or [])}"
        )
    with _OVERRIDE_LOCK:
        next_overrides = dict(_OVERRIDES)
        for key, value in pending:
            if value is _UNSET:
                continue
            next_overrides[key] = value  # number (cap) or None (unlimited)
        _save_overrides_snapshot(next_overrides)
        _OVERRIDES.clear()
        _OVERRIDES.update(next_overrides)
    after = resolve_risk_control()
    if audit_source and provided:
        _append_risk_control_audit(
            action="RISK_CONTROL_UPDATE",
            source=audit_source,
            before=before,
            after=after.to_dict(),
            changes=change_rows,
            assessment=assessment,
            confirm_supplied=audit_confirm_supplied,
            journal_reason=audit_journal_reason,
            journal_review=journal_review,
        )
    return after


def _cap_posture(current: Any, proposed: Any) -> str:
    """Classify a cap change from the owner's risk point of view."""
    if current == proposed:
        return "unchanged"
    if proposed is None:
        return "loosen"
    if current is None:
        return "tighten"
    try:
        cur = float(current)
        new = float(proposed)
    except (TypeError, ValueError):
        return "unknown"
    if new > cur:
        return "loosen"
    if new < cur:
        return "tighten"
    return "unchanged"


def real_money_controls_armed(config: Any = None) -> bool:
    """Whether risk loosening should require a deliberate confirmation.

    This intentionally triggers before the full live gate is authorized. If the
    owner has armed any live/money capability, risk expansion should stop being a
    casual one-click update.
    """
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        cfg = apply_live_enable_overrides(_resolve_config(config))
    except Exception:
        cfg = _resolve_config(config)
    return any(bool(getattr(cfg, key, False)) for key in _HIGH_STAKES_LIVE_KEYS)


def _effective_values_for_overrides(
    config: Any,
    overrides: Mapping[str, Any],
) -> dict[str, Any]:
    from cas_forex.execution_guard import caps_from_config

    caps = caps_from_config(config, owner_overrides=overrides)
    return {
        "max_concurrent_trades": caps.max_open_position_count,
        "max_total_exposure_lots": caps.max_total_exposure_lots,
        "max_loss_cap_usd": caps.max_floating_loss_usd,
        "max_drawdown_pct": caps.max_drawdown_pct_from_equity_peak,
        "max_positions_per_symbol": caps.max_positions_per_symbol,
        "max_risk_pct_per_trade": caps.max_risk_per_trade_pct,
        "max_margin_utilization_pct": caps.max_margin_utilization_pct,
    }


def assess_risk_control_update(
    updates: dict[str, Any],
    *,
    config: Any = None,
    journal_reason: Any = "",
) -> dict[str, Any]:
    """Preview whether a risk update tightens, loosens, or removes caps."""
    current_overrides = owner_override_snapshot()
    proposed_overrides = dict(current_overrides)
    proposed_overrides.update(
        {
            key: _coerce_persisted_override(key, value)
            for key, value in updates.items()
            if key in _RISK_KEYS
        }
    )
    current = resolve_risk_control_snapshot(config, current_overrides).to_dict()
    return _build_risk_control_assessment(
        current=current,
        proposed=updates,
        effective_current=_effective_values_for_overrides(config, current_overrides),
        effective_proposed=_effective_values_for_overrides(config, proposed_overrides),
        explicit_before=current_overrides,
        explicit_after=proposed_overrides,
        report_kind="cas_forex_risk_control_update_assessment",
        config=config,
        journal_reason=journal_reason,
    )


def _build_risk_control_assessment(
    *,
    current: Mapping[str, Any],
    proposed: Mapping[str, Any],
    effective_current: Mapping[str, Any],
    effective_proposed: Mapping[str, Any],
    explicit_before: Mapping[str, Any],
    explicit_after: Mapping[str, Any],
    report_kind: str,
    config: Any = None,
    journal_reason: Any = "",
) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    for key, proposed_value in proposed.items():
        if key not in _RISK_KEYS:
            continue
        before = current.get(key)
        effective_before = effective_current.get(key)
        effective_after = effective_proposed.get(key)
        owner_layer_posture = _cap_posture(before, proposed_value)
        posture = _cap_posture(effective_before, effective_after)
        changes.append(
            {
                "key": key,
                "before": before,
                "after": proposed_value,
                "posture": posture,
                "owner_layer_posture": owner_layer_posture,
                "effective_before": effective_before,
                "effective_after": effective_after,
                "unlimited_after": proposed_value is None,
            }
        )
    loosening = [c for c in changes if c["posture"] == "loosen"]
    high_stakes = real_money_controls_armed(config)
    cooldown = risk_loosening_cooldown_status(
        loosening_changes=loosening,
        real_money_controls=high_stakes,
    )
    journal = risk_loosening_journal_review(journal_reason, loosening_changes=loosening)
    return {
        "report_kind": report_kind,
        "current": dict(current),
        "effective_current": dict(effective_current),
        "effective_proposed": dict(effective_proposed),
        "explicit_override_keys_before": sorted(explicit_before),
        "explicit_override_keys_after": sorted(explicit_after),
        "changes": changes,
        "loosening_changes": loosening,
        "tightening_changes": [c for c in changes if c["posture"] == "tighten"],
        "requires_confirmation": bool(loosening and high_stakes),
        "requires_journal_reason": bool(journal.get("required")),
        "journal": journal,
        "journal_prompt": journal.get("prompt") or "",
        "cooldown": cooldown,
        "requires_cooldown_clear": bool(cooldown.get("active")),
        "confirm_phrase": RISK_LOOSEN_CONFIRM_PHRASE if loosening and high_stakes else "",
        "real_money_controls_armed": high_stakes,
        "claim_boundary": (
            "Risk-control assessment previews owner-layer and effective-dispatch cap changes. "
            "Anti-impulse posture is based on the effective dispatch change. Tightening is immediate; "
            "effective loosening/removal requires an anti-impulse journal reason. "
            "When real-money controls are armed, it also requires typed confirmation "
            "and a clear anti-impulse cooldown before the update is applied."
        ),
    }


def assess_risk_control_reset(
    *,
    config: Any = None,
    journal_reason: Any = "",
) -> dict[str, Any]:
    """Preview whether resetting overrides back to defaults tightens or loosens caps."""
    current_overrides = owner_override_snapshot()
    current = resolve_risk_control_snapshot(config, current_overrides).to_dict()
    defaults = _config_default_risk_control(config).to_dict()
    proposed = {key: defaults.get(key) for key in _RISK_KEYS}
    return _build_risk_control_assessment(
        current=current,
        proposed=proposed,
        effective_current=_effective_values_for_overrides(config, current_overrides),
        effective_proposed=_effective_values_for_overrides(config, {}),
        explicit_before=current_overrides,
        explicit_after={},
        report_kind="cas_forex_risk_control_reset_assessment",
        config=config,
        journal_reason=journal_reason,
    )


def clear_risk_control_overrides(
    *,
    audit_source: str | None = None,
    audit_confirm_supplied: bool = False,
    audit_assessment: Mapping[str, Any] | None = None,
    audit_journal_reason: str = "",
) -> None:
    """Drop all risk overrides (revert to static config defaults)."""
    _load_overrides()
    before = resolve_risk_control().to_dict() if audit_source else {}
    override_keys = sorted(_OVERRIDES)
    assessment = (
        dict(audit_assessment)
        if audit_assessment is not None
        else (assess_risk_control_reset(journal_reason=audit_journal_reason) if audit_source else {})
    )
    reset_target = _config_default_risk_control().to_dict() if audit_source else {}
    keys = override_keys or list(_RISK_KEYS)
    assessed_changes = {
        str(row.get("key")): dict(row)
        for row in (assessment.get("changes") or [])
        if isinstance(row, Mapping) and row.get("key")
    }
    changes = [
        assessed_changes.get(
            key,
            {
                "key": key,
                "before": before.get(key),
                "after": reset_target.get(key),
                "posture": _cap_posture(before.get(key), reset_target.get(key)),
                "owner_layer_posture": _cap_posture(before.get(key), reset_target.get(key)),
                "unlimited_after": reset_target.get(key) is None,
            },
        )
        for key in keys
    ] if audit_source else []
    effective_loosening = [
        dict(row)
        for row in (assessment.get("loosening_changes") or [])
        if isinstance(row, Mapping)
    ]
    journal_review = (
        risk_loosening_journal_review(
            audit_journal_reason,
            loosening_changes=effective_loosening,
        )
        if audit_source
        else {}
    )
    if journal_review.get("required") and not journal_review.get("satisfied"):
        raise ValueError(
            "Loosening/removing risk caps requires an anti-impulse journal reason before "
            f"the override can change: {'; '.join(journal_review.get('blockers') or [])}"
        )
    with _OVERRIDE_LOCK:
        _save_overrides_snapshot({})
        _OVERRIDES.clear()
    if audit_source:
        after = resolve_risk_control().to_dict()
        _append_risk_control_audit(
            action="RISK_CONTROL_RESET",
            source=audit_source,
            before=before,
            after=after,
            changes=changes,
            assessment=assessment,
            confirm_supplied=audit_confirm_supplied,
            journal_reason=audit_journal_reason,
            journal_review=journal_review,
        )


def explicit_override_keys() -> frozenset[str]:
    """Cap keys the owner has EXPLICITLY set at runtime (value may be None =
    unlimited). ``execution_guard`` uses this for precedence: an explicit owner
    override beats the AI operator's dial; an unset key lets the dial drive."""
    _load_overrides()
    return frozenset(_OVERRIDES)


def _effective_dispatch_caps_report(config: Any = None) -> dict[str, Any]:
    from cas_forex.execution_guard import caps_from_config

    caps = caps_from_config(config)
    owner_keys = explicit_override_keys()
    return {
        "precedence": "explicit owner risk-control override > AI dial > static config",
        "max_open_position_count": caps.max_open_position_count,
        "max_positions_per_symbol": caps.max_positions_per_symbol,
        "max_total_exposure_lots": caps.max_total_exposure_lots,
        "max_risk_per_trade_pct": caps.max_risk_per_trade_pct,
        "max_margin_utilization_pct": caps.max_margin_utilization_pct,
        "max_drawdown_pct_from_equity_peak": caps.max_drawdown_pct_from_equity_peak,
        "max_floating_loss_usd": caps.max_floating_loss_usd,
        "sources": {
            "max_open_position_count": (
                "explicit_owner_override"
                if "max_concurrent_trades" in owner_keys
                else "ai_dial_then_static_config"
            ),
            "max_positions_per_symbol": "ai_dial_bounded_by_effective_open_position_cap",
            "max_total_exposure_lots": (
                "explicit_owner_override"
                if "max_total_exposure_lots" in owner_keys
                else "ai_dial_then_static_config"
            ),
            "max_risk_per_trade_pct": "ai_dial_then_static_config",
            "max_drawdown_pct_from_equity_peak": (
                "explicit_owner_override"
                if "max_drawdown_pct" in owner_keys
                else "static_config"
            ),
            "max_floating_loss_usd": (
                "explicit_owner_override"
                if "max_loss_cap_usd" in owner_keys
                else "static_config"
            ),
        },
        "claim_boundary": (
            "These are the caps resolved for the dispatch chokepoint at report time. "
            "Every broker-bound action recalculates them again before broker contact."
        ),
    }


def _override_persistence_report() -> dict[str, Any]:
    _load_overrides()
    if _OVERRIDE_PATH is None:
        status = "PERSISTENCE_DISABLED"
    elif _OVERRIDE_LOAD_ERROR:
        status = "PERSISTENCE_LOAD_ERROR"
    elif _OVERRIDES:
        status = "PERSISTED_OWNER_OVERRIDES_ACTIVE"
    else:
        status = "NO_EXPLICIT_OWNER_OVERRIDES"
    return {
        "status": status,
        "enabled": _OVERRIDE_PATH is not None,
        "state_path": str(_OVERRIDE_PATH) if _OVERRIDE_PATH is not None else None,
        "state_file_present": bool(_OVERRIDE_PATH and _OVERRIDE_PATH.exists()),
        "loaded_from_disk": _OVERRIDE_LOADED_FROM_DISK,
        "last_saved_at": _OVERRIDE_LAST_SAVED_AT,
        "load_error": _OVERRIDE_LOAD_ERROR,
        "explicit_override_count": len(_OVERRIDES),
        "explicit_override_keys": [key for key in _RISK_KEYS if key in _OVERRIDES],
        "claim_boundary": (
            "Only explicit owner risk overrides are persisted. An absent key leaves "
            "that dimension under AI-dial then static-config precedence."
        ),
    }


def build_risk_control_report(config: Any = None) -> dict[str, Any]:
    """Owner-control layer plus the separately resolved dispatch caps."""
    rc = resolve_risk_control(config)
    data = rc.to_dict()
    data["report_kind"] = "cas_forex_risk_control"
    data["cap_layer"] = "OWNER_OVERRIDE_OR_STATIC_FALLBACK"
    data["explicit_override_keys"] = sorted(explicit_override_keys())
    data["effective_dispatch_caps"] = _effective_dispatch_caps_report(config)
    data["override_persistence"] = _override_persistence_report()
    data["notes"] = [
        "Set any cap to a number, or to null for UNLIMITED (no cap on that dimension).",
        "Top-level values are explicit owner overrides when set, otherwise static fallbacks shown by this editor.",
        "effective_dispatch_caps is the actual owner-override > AI-dial > static-config result at report time.",
        "max_concurrent_trades caps total open positions; per-symbol positions remain the tighter AI dial bounded by that cap.",
        "Explicit owner overrides apply immediately and persist across API restarts.",
        "Tightening caps is immediate. Loosening/removing caps requires an anti-impulse journal reason; when real-money controls are armed it also requires typed confirmation.",
    ]
    data["anti_impulse_journal_policy"] = {
        "required_on_loosen": True,
        "minimum_reason_length": RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS,
        "prompt": RISK_LOOSEN_JOURNAL_PROMPT,
    }
    data["anti_impulse_status"] = build_risk_control_anti_impulse_status(config)
    data["audit_path"] = str(_AUDIT_PATH)
    latest = recent_risk_control_audit(1)
    data["latest_audit"] = latest[0] if latest else None
    return data


def build_risk_control_anti_impulse_status(config: Any = None) -> dict[str, Any]:
    """Current anti-impulse friction around future risk-cap loosening.

    This is observational. It does not preview or apply a specific cap change;
    it tells owner/chat surfaces whether another loosening would currently hit
    cooldown, require typed confirmation, and require a journal reason.
    """
    config = _resolve_config(config)
    real_money_armed = real_money_controls_armed(config)
    synthetic_loosening = [{"key": "preview_loosen", "posture": "loosen"}]
    cooldown = risk_loosening_cooldown_status(
        loosening_changes=synthetic_loosening,
        real_money_controls=real_money_armed,
    )
    journal = risk_loosening_journal_review(
        "",
        loosening_changes=synthetic_loosening,
    )
    return {
        "report_kind": "cas_forex_risk_control_anti_impulse_status",
        "real_money_controls_armed": real_money_armed,
        "typed_confirmation_required_on_loosen": real_money_armed,
        "journal_required_on_loosen": bool(journal.get("required")),
        "journal_minimum_reason_length": RISK_LOOSEN_JOURNAL_REASON_MIN_CHARS,
        "journal_prompt": RISK_LOOSEN_JOURNAL_PROMPT,
        "cooldown": cooldown,
        "would_block_new_loosening": bool(cooldown.get("active")),
        "claim_boundary": (
            "Risk anti-impulse status is observational. It reports whether a new "
            "risk-cap loosening would currently require a journal reason, typed "
            "confirmation, or cooldown clearance. It does not change caps, place "
            "orders, authorize live trading, or promise safer outcomes."
        ),
    }
