"""Durable AI Control Authority for CAS Forex.

This module is the owner-authorized envelope around the adaptive AI. The owner
sets the fence; the AI can move the dials inside that fence. It does not enable
live trading or money movement by itself. Those gates still live in
``runtime_gates`` / broker controls. This module gives WASTE and the API a single
durable place for objective, direction, risk, compounding, and control-surface
state.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.ai_control_surface import (
    AiControlSurface,
    LEVER_NAMES,
    SUPPORTED_ENTRY_TIMEFRAMES,
    SUPPORTED_SESSIONS,
)
from cas_forex.ai_objective import ProfitObjective
from cas_forex.instruments import SUPPORTED_SYMBOLS
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "ai-control-authority.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "ai-control-authority-audit.jsonl"
AI_CONTROL_AUTHORITY_AUDIT_REPORT_KIND = "cas_forex_ai_control_authority_audit"
AI_CONTROL_AUTHORITY_AUDIT_CLAIM_BOUNDARY = (
    "AI control-authority audit records owner-envelope changes and AI/operator "
    "dial adjustments. It does not enable live trading, place broker orders, "
    "move funds, or bypass owner gates."
)

_CONTROL_NUMERIC_OWNER_LIMITS = {
    "edge_threshold": ("edge_threshold_min", "edge_threshold_max"),
    "min_directional_confidence": (
        "min_directional_confidence_min",
        "min_directional_confidence_max",
    ),
    "max_risk_pct_per_trade": (0.0, "max_risk_pct_per_trade"),
    "max_concurrent_trades": (1, "max_concurrent_trades"),
    "max_positions_per_symbol": (1, "max_positions_per_symbol"),
    "max_total_exposure_lots": (0.01, "max_total_exposure_lots"),
    "daily_loss_cap_usd": (0.0, "daily_loss_cap_usd_max"),
    "max_compound_units": (0, "max_compound_units"),
    "paper_learning_trades": (0, "paper_learning_trades"),
    "trailing_stop_enabled": (0, "trailing_stop_enabled"),
    "trailing_lock_fraction": (
        "trailing_lock_fraction_min",
        "trailing_lock_fraction_max",
    ),
}

_LOWER_VALUE_LOOSENS = {
    "edge_threshold",
    "edge_threshold_min",
    "min_directional_confidence",
    "min_directional_confidence_min",
}
_HIGHER_VALUE_LOOSENS = {
    "max_risk_pct_per_trade",
    "max_concurrent_trades",
    "max_positions_per_symbol",
    "max_total_exposure_lots",
    "daily_loss_cap_usd",
    "daily_loss_cap_usd_max",
    "max_compound_units",
    "paper_learning_trades",
}
_BREADTH_KEYS = {
    "symbols",
    "sessions",
    "timeframes",
    "allowed_symbols",
    "allowed_sessions",
    "allowed_timeframes",
}
_PERMISSION_KEYS = {
    "allow_long",
    "allow_short",
}
_FRESH_PASS_KEYS = {
    "require_fresh_pass_for_entry",
    "require_fresh_pass_for_compound",
}
AI_DIAL_LOOSEN_LOOKBACK_HOURS = 24
AI_DIAL_LOOSEN_WARNING_LIMIT = 6
AI_DIAL_LOOSEN_COOLDOWN_SECONDS = 30 * 60
AI_DIAL_LOOSEN_REASON_MIN_CHARS = 20
AI_DIAL_LOOSEN_JOURNAL_PROMPT = (
    "Before widening trading latitude, record why this is not revenge trading, "
    "FOMO, overconfidence, or chasing losses; include the expected account impact "
    "and the condition that should roll the change back."
)

_AI_DIAL_DEFINITIONS: dict[str, dict[str, str]] = {
    "edge_threshold": {
        "label": "Edge threshold",
        "operational_effect": "Minimum measured edge required before a route can pass strategy checks.",
        "loosens_when": "lower",
        "tightens_when": "higher",
        "enforced_by": "edge gate and dispatch route filtering",
        "value_kind": "number",
        "units": "edge score",
        "runtime_path": "ai_control_authority.control_surface.values.edge_threshold",
    },
    "min_directional_confidence": {
        "label": "Directional score floor",
        "operational_effect": "Minimum directional hypothesis score before a candidate forms.",
        "loosens_when": "lower",
        "tightens_when": "higher",
        "enforced_by": "directional intelligence before route formation",
        "value_kind": "number",
        "units": "confidence score",
        "runtime_path": "ai_control_authority.control_surface.values.min_directional_confidence",
    },
    "max_risk_pct_per_trade": {
        "label": "Max risk per trade",
        "operational_effect": "Risk budget percentage available to sizing logic before execution gates.",
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "sizing logic and pre-execution risk gate",
        "value_kind": "number",
        "units": "% equity risk",
        "runtime_path": "ai_control_authority.control_surface.values.max_risk_pct_per_trade",
    },
    "max_concurrent_trades": {
        "label": "Max concurrent trades",
        "operational_effect": "Open-position count cap used when no explicit owner risk override wins.",
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "pre-execution risk gate",
        "value_kind": "integer",
        "units": "open trades",
        "runtime_path": "ai_control_authority.control_surface.values.max_concurrent_trades",
    },
    "max_positions_per_symbol": {
        "label": "Max positions per symbol",
        "operational_effect": "Per-symbol stacking cap for concentration control.",
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "pre-execution risk gate",
        "value_kind": "integer",
        "units": "positions",
        "runtime_path": "ai_control_authority.control_surface.values.max_positions_per_symbol",
    },
    "max_total_exposure_lots": {
        "label": "Max total exposure",
        "operational_effect": "Total open lot exposure the AI may request before owner overrides.",
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "pre-execution risk gate",
        "value_kind": "number",
        "units": "lots",
        "runtime_path": "ai_control_authority.control_surface.values.max_total_exposure_lots",
    },
    "daily_loss_cap_usd": {
        "label": "Daily loss cap",
        "operational_effect": (
            "Reconciled daily realized-loss boundary for new entries and scale-ins. "
            "Risk-reducing management remains available after the boundary is reached."
        ),
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "AI trade-edge precheck and final execution chokepoint",
        "value_kind": "number",
        "units": "USD",
        "runtime_path": "ai_control_authority.control_surface.values.daily_loss_cap_usd",
    },
    "symbols": {
        "label": "Symbols",
        "operational_effect": "Broker-normalized markets the AI is allowed to consider.",
        "loosens_when": "more symbols",
        "tightens_when": "fewer symbols",
        "enforced_by": "market scan and route collection",
        "value_kind": "subset",
        "units": "markets",
        "runtime_path": "ai_control_authority.control_surface.values.symbols",
    },
    "sessions": {
        "label": "Sessions",
        "operational_effect": "Trading sessions the AI is allowed to operate in.",
        "loosens_when": "more sessions",
        "tightens_when": "fewer sessions",
        "enforced_by": "dispatch loop session filter",
        "value_kind": "subset",
        "units": "sessions",
        "runtime_path": "ai_control_authority.control_surface.values.sessions",
    },
    "timeframes": {
        "label": "Entry timeframes",
        "operational_effect": (
            "Completed broker-candle timeframes rotated through autonomous entry "
            "scanning; M1/M5 form the micro-scalp lane and M15/H1 form the broader "
            "intraday lane."
        ),
        "loosens_when": "more timeframes",
        "tightens_when": "fewer timeframes",
        "enforced_by": "agent dispatch timeframe rotation and live-candle route policy",
        "value_kind": "subset",
        "units": "completed-candle timeframes",
        "runtime_path": "ai_control_authority.control_surface.values.timeframes",
    },
    "max_compound_units": {
        "label": "Max compound units",
        "operational_effect": "Maximum autonomous Operator-selected add units for a protected parent that remains net winning after reported carry and costs.",
        "loosens_when": "higher",
        "tightens_when": "lower",
        "enforced_by": "AI position-edge scale-in planner and pre-execution risk gate",
        "value_kind": "integer",
        "units": "units",
        "runtime_path": "ai_control_authority.control_surface.values.max_compound_units",
    },
    "paper_learning_trades": {
        "label": "Paper learning trades",
        "operational_effect": "Whether paper mode may place token-less learning attempts for labeling.",
        "loosens_when": "1",
        "tightens_when": "0",
        "enforced_by": "paper dispatch path only; real dispatch still requires edge authorization",
        "value_kind": "toggle",
        "units": "flag",
        "runtime_path": "ai_control_authority.control_surface.values.paper_learning_trades",
    },
    "trailing_stop_enabled": {
        "label": "Trailing stop",
        "operational_effect": "Whether implemented trailing-stop exits can bank part of favorable movement.",
        "loosens_when": "0",
        "tightens_when": "1",
        "enforced_by": "paper outcome and position management path",
        "value_kind": "toggle",
        "units": "flag",
        "runtime_path": "ai_control_authority.control_surface.values.trailing_stop_enabled",
    },
    "trailing_lock_fraction": {
        "label": "Trailing lock fraction",
        "operational_effect": "Share of favorable run the trailing stop locks on pullback.",
        "loosens_when": "lower",
        "tightens_when": "higher",
        "enforced_by": "trailing-stop position management",
        "value_kind": "number",
        "units": "fraction",
        "runtime_path": "ai_control_authority.control_surface.values.trailing_lock_fraction",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tuple_sorted(values: Any, allowed: set[str], *, field_name: str) -> tuple[str, ...]:
    if values is None:
        return tuple(sorted(allowed))
    if isinstance(values, str):
        requested = {values}
    else:
        requested = {str(v) for v in values}
    kept = tuple(v for v in sorted(allowed) if v in requested)
    if not kept:
        raise ValueError(f"{field_name} must include at least one supported value")
    return kept


@dataclass(frozen=True)
class OwnerEnvelope:
    """Owner-set envelope. The AI can work inside it, never move it."""

    monthly_profit_target_usd: float = 5000.0
    daily_profit_floor_usd: float = 250.0
    daily_profit_cap_usd: float = 3500.0
    ai_incentive_rate: float = 0.025
    allowed_symbols: tuple[str, ...] = field(
        default_factory=lambda: tuple(sorted(SUPPORTED_SYMBOLS))
    )
    allowed_sessions: tuple[str, ...] = field(default_factory=lambda: SUPPORTED_SESSIONS)
    allowed_timeframes: tuple[str, ...] = field(
        default_factory=lambda: SUPPORTED_ENTRY_TIMEFRAMES
    )
    allow_long: bool = True
    allow_short: bool = True
    edge_threshold_min: float = 0.50
    edge_threshold_max: float = 0.95
    min_directional_confidence_min: float = 0.05
    min_directional_confidence_max: float = 0.90
    max_risk_pct_per_trade: float = 5.0
    max_concurrent_trades: int = 50
    max_positions_per_symbol: int = 10
    max_total_exposure_lots: float = 5.0
    daily_loss_cap_usd_max: float = 500.0
    max_compound_units: int = 8
    paper_learning_trades: int = 1
    trailing_stop_enabled: int = 1
    trailing_lock_fraction_min: float = 0.10
    trailing_lock_fraction_max: float = 0.90
    require_fresh_pass_for_entry: bool = True
    require_fresh_pass_for_compound: bool = True

    def normalized(self) -> "OwnerEnvelope":
        if self.monthly_profit_target_usd < 0:
            raise ValueError("monthly_profit_target_usd must be >= 0")
        if self.daily_profit_floor_usd < 0:
            raise ValueError("daily_profit_floor_usd must be >= 0")
        if self.daily_profit_cap_usd < 0:
            raise ValueError("daily_profit_cap_usd must be >= 0")
        if self.ai_incentive_rate < 0:
            raise ValueError("ai_incentive_rate must be >= 0")
        if not self.allow_long and not self.allow_short:
            raise ValueError("At least one direction must be allowed")
        if self.edge_threshold_min < 0 or self.edge_threshold_max < 0:
            raise ValueError("edge thresholds must be >= 0")
        if self.edge_threshold_min > self.edge_threshold_max:
            raise ValueError("edge_threshold_min cannot exceed edge_threshold_max")
        if self.min_directional_confidence_min < 0 or self.min_directional_confidence_max < 0:
            raise ValueError("min directional confidence bounds must be >= 0")
        if self.min_directional_confidence_min > self.min_directional_confidence_max:
            raise ValueError("min_directional_confidence_min cannot exceed min_directional_confidence_max")
        if self.max_risk_pct_per_trade < 0:
            raise ValueError("max_risk_pct_per_trade must be >= 0")
        if self.max_concurrent_trades < 1:
            raise ValueError("max_concurrent_trades must be >= 1")
        if self.max_positions_per_symbol < 1:
            raise ValueError("max_positions_per_symbol must be >= 1")
        if self.max_total_exposure_lots <= 0:
            raise ValueError("max_total_exposure_lots must be > 0")
        if self.daily_loss_cap_usd_max < 0:
            raise ValueError("daily_loss_cap_usd_max must be >= 0")
        if self.max_compound_units < 0:
            raise ValueError("max_compound_units must be >= 0")
        if int(self.paper_learning_trades) not in {0, 1}:
            raise ValueError("paper_learning_trades must be 0 or 1")
        if int(self.trailing_stop_enabled) not in {0, 1}:
            raise ValueError("trailing_stop_enabled must be 0 or 1")
        if self.trailing_lock_fraction_min < 0 or self.trailing_lock_fraction_max < 0:
            raise ValueError("trailing lock fraction bounds must be >= 0")
        if self.trailing_lock_fraction_min > self.trailing_lock_fraction_max:
            raise ValueError("trailing_lock_fraction_min cannot exceed trailing_lock_fraction_max")
        symbols = _tuple_sorted(
            self.allowed_symbols,
            set(SUPPORTED_SYMBOLS),
            field_name="allowed_symbols",
        )
        sessions = _tuple_sorted(
            self.allowed_sessions,
            set(SUPPORTED_SESSIONS),
            field_name="allowed_sessions",
        )
        timeframes = _tuple_sorted(
            self.allowed_timeframes,
            set(SUPPORTED_ENTRY_TIMEFRAMES),
            field_name="allowed_timeframes",
        )
        return replace(
            self,
            allowed_symbols=symbols,
            allowed_sessions=sessions,
            allowed_timeframes=timeframes,
            paper_learning_trades=int(self.paper_learning_trades),
            trailing_stop_enabled=int(self.trailing_stop_enabled),
        )

    def objective(self) -> ProfitObjective:
        trading_days = 20
        return ProfitObjective(
            monthly_target=float(self.monthly_profit_target_usd),
            daily_target=float(self.daily_profit_floor_usd),
            daily_max_target=float(self.daily_profit_cap_usd),
            trading_days=trading_days,
            edge_threshold_default=float(self.edge_threshold_min),
        )


@dataclass(frozen=True)
class AuthoritySnapshot:
    owner_envelope: dict[str, Any]
    control_surface: dict[str, Any]
    updated_at: str
    state_path: str


class AiControlAuthority:
    """Owner envelope plus live AI control surface, persisted as JSON."""

    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str | None = None,
    ) -> None:
        self.state_path = Path(state_path)
        if audit_path is None:
            self.audit_path = (
                DEFAULT_AUDIT_PATH
                if self.state_path == DEFAULT_STATE_PATH
                else self.state_path.with_name(f"{self.state_path.stem}-audit.jsonl")
            )
        else:
            self.audit_path = Path(audit_path)
        self._lock = threading.RLock()
        self.owner_envelope = OwnerEnvelope().normalized()
        self.control = AiControlSurface(persist=self._persist_surface)
        self.updated_at = _now_iso()
        self._loading = False
        self._load()
        self._clamp_surface_to_envelope()

    # -- persistence -----------------------------------------------------
    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self._loading = True
        try:
            owner = payload.get("owner_envelope")
            if isinstance(owner, Mapping):
                self.owner_envelope = OwnerEnvelope(**owner).normalized()
            values = payload.get("control_surface", {}).get("values")
            if isinstance(values, Mapping):
                for key, value in values.items():
                    self.control.adjust(str(key), value)
            self.updated_at = str(payload.get("updated_at") or _now_iso())
        finally:
            self._loading = False

    def _persist_surface(self, _snapshot: dict[str, Any]) -> None:
        if self._loading:
            return
        self.save()

    def save(self) -> None:
        with self._lock:
            self.updated_at = _now_iso()
            payload = self.snapshot()
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.state_path)

    # -- reports ---------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            surface = self.control.snapshot()
            surface["dial_definitions"] = _jsonable(_AI_DIAL_DEFINITIONS)
            surface["anti_impulse"] = self.anti_impulse_report()
            return {
                "report_kind": "cas_forex_ai_control_authority",
                "owner_envelope": _jsonable(asdict(self.owner_envelope)),
                "control_surface": surface,
                "updated_at": self.updated_at,
                "state_path": str(self.state_path),
                "audit_path": str(self.audit_path),
                "latest_audit": (self.recent_audit(1) or [None])[0],
                "authority_note": (
                    "Owner sets the envelope. AI may adjust dials inside it. "
                    "This does not enable live trading or money movement."
                ),
                "direction_note": (
                    "LONG and SHORT are separate owner-permitted actions; the AI "
                    "may also choose NO_TRADE."
                ),
            }

    def recent_audit(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return recent authority audit rows, newest first."""
        with self._lock:
            if not self.audit_path.exists():
                return []
            try:
                lines = self.audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
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

    def audit_report(self, limit: int = 25) -> dict[str, Any]:
        return {
            "report_kind": AI_CONTROL_AUTHORITY_AUDIT_REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "rows": self.recent_audit(limit),
            "claim_boundary": AI_CONTROL_AUTHORITY_AUDIT_CLAIM_BOUNDARY,
        }

    def anti_impulse_report(self, *, proposed_posture: str | None = None) -> dict[str, Any]:
        """Summarize recent loosening so dial changes do not hide drift."""
        now = utc_now()
        window_seconds = AI_DIAL_LOOSEN_LOOKBACK_HOURS * 60 * 60
        recent: list[dict[str, Any]] = []
        for row in self.recent_audit(200):
            at = _parse_audit_datetime(row.get("at"))
            if at is None:
                continue
            age = max(0.0, (now - at).total_seconds())
            if age > window_seconds:
                continue
            changes = row.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                if str(change.get("posture") or "").lower() != "loosen":
                    continue
                recent.append(
                    {
                        "at": row.get("at"),
                        "action": row.get("action"),
                        "source": row.get("source"),
                        "key": change.get("key"),
                        "before": change.get("before"),
                        "after": change.get("after"),
                    }
                )
        projected = len(recent) + (1 if proposed_posture == "loosen" else 0)
        last_loosened_at = recent[0].get("at") if recent else None
        cooldown_active = False
        cooldown_remaining_seconds = 0
        cooldown_detail = (
            "AI dial loosening cooldown applies only to additional dial-widening writes; "
            "tightening remains available."
        )
        if last_loosened_at:
            last_at = _parse_audit_datetime(last_loosened_at)
            if last_at is not None:
                age = max(0.0, (now - last_at).total_seconds())
                remaining = max(0, int(AI_DIAL_LOOSEN_COOLDOWN_SECONDS - age))
                if remaining > 0:
                    cooldown_active = True
                    cooldown_remaining_seconds = remaining
                    cooldown_detail = (
                        "Another AI dial loosening is cooling down after a recent widening change. "
                        "Tightening remains available."
                    )
        return {
            "report_kind": "cas_forex_ai_dial_anti_impulse",
            "lookback_hours": AI_DIAL_LOOSEN_LOOKBACK_HOURS,
            "recent_loosen_count": len(recent),
            "projected_loosen_count": projected,
            "loosen_warning_limit": AI_DIAL_LOOSEN_WARNING_LIMIT,
            "warning_active": len(recent) >= AI_DIAL_LOOSEN_WARNING_LIMIT,
            "projected_warning_active": projected >= AI_DIAL_LOOSEN_WARNING_LIMIT,
            "cooldown_seconds": AI_DIAL_LOOSEN_COOLDOWN_SECONDS,
            "cooldown_active": cooldown_active,
            "cooldown_remaining_seconds": cooldown_remaining_seconds,
            "projected_cooldown_blocked": bool(
                proposed_posture == "loosen" and cooldown_active
            ),
            "last_loosened_at": last_loosened_at,
            "cooldown_detail": cooldown_detail,
            "journal_prompt_required_on_loosen": True,
            "journal_prompt_min_chars": AI_DIAL_LOOSEN_REASON_MIN_CHARS,
            "journal_prompt": AI_DIAL_LOOSEN_JOURNAL_PROMPT,
            "recent_loosening_changes": recent[:10],
            "policy": (
                "Tightening dials is always allowed. Loosening remains possible, "
                "but every loosening must include an anti-impulse journal reason, "
                "is rate-limited by cooldown, and is audited so FOMO-style parameter drift is visible."
            ),
        }

    def preview_ai_adjust(self, lever: str, value: Any, *, reason: str = "") -> dict[str, Any]:
        """Preview an AI dial adjustment with concrete impact and posture."""
        with self._lock:
            if lever not in LEVER_NAMES:
                return {
                    "ready": False,
                    "lever": lever,
                    "requested": value,
                    "current": None,
                    "proposed": None,
                    "posture": "blocked",
                    "blockers": [f"Unknown dial '{lever}'. Known: {sorted(LEVER_NAMES)}"],
                    "effects": [],
                }
            current = self.control.get(lever)
            try:
                checked_value, owner_clamped, owner_reason = self._apply_owner_limit(lever, value)
            except ValueError as exc:
                return {
                    "ready": False,
                    "lever": lever,
                    "requested": value,
                    "current": current,
                    "proposed": current,
                    "posture": "blocked",
                    "blockers": [str(exc)],
                    "effects": [],
                }
            preview = self.control.preview_adjust(lever, checked_value)
            if not preview.get("ok"):
                return {
                    "ready": False,
                    "lever": lever,
                    "requested": value,
                    "current": current,
                    "proposed": preview.get("new"),
                    "checked": checked_value,
                    "posture": "blocked",
                    "owner_clamped": bool(owner_clamped),
                    "owner_reason": owner_reason,
                    "blockers": [str(preview.get("reason") or "dial preview failed")],
                    "effects": [],
                }
            proposed = preview.get("new")
            posture = _change_posture(lever, current, proposed)
            definition = _AI_DIAL_DEFINITIONS.get(
                lever,
                {
                    "label": lever,
                    "operational_effect": "Typed CAS/AI control-surface lever.",
                    "loosens_when": "value widens trade latitude",
                    "tightens_when": "value narrows trade latitude",
                    "enforced_by": "control surface",
                    "value_kind": "unknown",
                    "units": "",
                    "runtime_path": f"ai_control_authority.control_surface.values.{lever}",
                },
            )
            binding = self._preview_binding(lever, definition)
            contract_rows = self._preview_contract_rows(
                lever=lever,
                requested=value,
                checked=checked_value,
                current=current,
                proposed=proposed,
                posture=posture,
                definition=definition,
                binding=binding,
            )
            effects = [
                (
                    f"{definition['label']}: {definition['operational_effect']} "
                    f"Enforced by {definition['enforced_by']}."
                ),
                (
                    f"Runtime contract: {_contract_row_effect(contract_rows[0])}"
                    if contract_rows
                    else "Runtime contract unavailable."
                ),
                f"Posture impact: {posture}. Loosens when {definition['loosens_when']}; tightens when {definition['tightens_when']}.",
            ]
            if owner_clamped or preview.get("clamped"):
                effects.append(str(preview.get("reason") or owner_reason))
            if posture == "loosen":
                effects.append(
                    "This widens trading latitude; an anti-impulse journal reason is required before apply."
                )
            elif posture == "tighten":
                effects.append("This narrows trading latitude; tightening is allowed immediately.")
            anti_impulse = self.anti_impulse_report(proposed_posture=posture)
            journal_review = _anti_impulse_journal_review(
                reason,
                posture=posture,
                projected_warning_active=bool(anti_impulse.get("projected_warning_active")),
            )
            blockers: list[str] = []
            if journal_review.get("required") and not journal_review.get("satisfied"):
                blockers.extend(str(item) for item in (journal_review.get("blockers") or []))
                effects.append(
                    "An anti-impulse journal reason must be recorded before this widening can apply."
                )
            requires_cooldown_clear = bool(
                posture == "loosen" and anti_impulse.get("projected_cooldown_blocked")
            )
            if requires_cooldown_clear:
                blockers.append(
                    str(anti_impulse.get("cooldown_detail") or "AI dial loosening cooldown is active.")
                )
                effects.append(
                    "Another dial widening is cooling down after a recent loosening; tightening remains available."
                )
            return {
                "ready": not blockers,
                "lever": lever,
                "requested": value,
                "checked": checked_value,
                "current": current,
                "proposed": proposed,
                "posture": posture,
                "owner_clamped": bool(owner_clamped),
                "base_clamped": bool(preview.get("clamped")),
                "owner_reason": owner_reason,
                "reason": preview.get("reason"),
                "impact": _jsonable(definition),
                "binding": binding,
                "before_after": {
                    "requested": _jsonable(value),
                    "checked": _jsonable(checked_value),
                    "current": _jsonable(current),
                    "proposed": _jsonable(proposed),
                },
                "contract_rows": contract_rows,
                "anti_impulse": anti_impulse,
                "anti_impulse_journal": journal_review,
                "journal_prompt_required": bool(journal_review.get("required")),
                "journal_prompt": journal_review.get("prompt"),
                "requires_cooldown_clear": requires_cooldown_clear,
                "blockers": blockers,
                "effects": effects,
                "claim_boundary": (
                    "This preview describes a bounded AI dial change only. It does not "
                    "authorize live trading, place orders, or move money."
                ),
            }

    def _owner_bound_for_lever(self, lever: str) -> dict[str, Any]:
        owner = self.owner_envelope
        if lever == "symbols":
            return {"allowed": list(owner.allowed_symbols)}
        if lever == "sessions":
            return {"allowed": list(owner.allowed_sessions)}
        if lever == "timeframes":
            return {"allowed": list(owner.allowed_timeframes)}
        bounds = _CONTROL_NUMERIC_OWNER_LIMITS.get(lever)
        if bounds is None:
            return {}
        lo_ref, hi_ref = bounds
        lo = getattr(owner, lo_ref) if isinstance(lo_ref, str) else lo_ref
        hi = getattr(owner, hi_ref) if isinstance(hi_ref, str) else hi_ref
        payload: dict[str, Any] = {"min": _jsonable(lo), "max": _jsonable(hi)}
        if lever in {"paper_learning_trades", "trailing_stop_enabled"}:
            payload["allowed"] = [0, 1]
        return payload

    def _preview_binding(
        self,
        lever: str,
        definition: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "lever": lever,
            "label": definition.get("label") or lever,
            "operational_effect": definition.get("operational_effect") or "",
            "enforced_by": definition.get("enforced_by") or "",
            "loosens_when": definition.get("loosens_when") or "",
            "tightens_when": definition.get("tightens_when") or "",
            "value_kind": definition.get("value_kind") or "unknown",
            "units": definition.get("units") or "",
            "runtime_path": definition.get("runtime_path")
            or f"ai_control_authority.control_surface.values.{lever}",
            "owner_bound": self._owner_bound_for_lever(lever),
        }

    def _preview_contract_rows(
        self,
        *,
        lever: str,
        requested: Any,
        checked: Any,
        current: Any,
        proposed: Any,
        posture: str,
        definition: Mapping[str, Any],
        binding: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        row = {
            "field": lever,
            "label": str(definition.get("label") or lever),
            "posture": posture,
            "value_kind": str(binding.get("value_kind") or "unknown"),
            "units": str(binding.get("units") or ""),
            "operational_effect": str(definition.get("operational_effect") or ""),
            "enforced_by": str(definition.get("enforced_by") or ""),
            "runtime_path": str(
                binding.get("runtime_path")
                or f"ai_control_authority.control_surface.values.{lever}"
            ),
            "owner_bound": _jsonable(binding.get("owner_bound") or {}),
            "requested": _jsonable(requested),
            "checked": _jsonable(checked),
        }
        if lever in _BREADTH_KEYS:
            before_items = [str(item) for item in (current or [])]
            after_items = [str(item) for item in (proposed or [])]
            row.update(
                {
                    "before": before_items,
                    "after": after_items,
                    "before_count": len(before_items),
                    "after_count": len(after_items),
                    "added": [item for item in after_items if item not in before_items],
                    "removed": [item for item in before_items if item not in after_items],
                }
            )
        else:
            row.update(
                {
                    "before": _jsonable(current),
                    "after": _jsonable(proposed),
                }
            )
        return [row]

    def _append_audit(
        self,
        *,
        action: str,
        source: str,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        changes: list[Mapping[str, Any]],
        request: Mapping[str, Any] | None = None,
        result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        safe_changes = _jsonable(changes)
        record = {
            "report_kind": AI_CONTROL_AUTHORITY_AUDIT_REPORT_KIND,
            "audit_id": stable_ledger_id(
                "ai-control-authority-audit",
                action,
                source,
                generated_at,
                json.dumps(safe_changes, sort_keys=True, default=str),
            ),
            "at": generated_at,
            "action": str(action),
            "source": str(source or "ai_control_authority"),
            "before": _authority_audit_summary(before),
            "after": _authority_audit_summary(after),
            "changes": safe_changes,
            "request": _jsonable(request or {}),
            "result": _jsonable(result or {}),
            "external_money_movement": False,
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "claim_boundary": AI_CONTROL_AUTHORITY_AUDIT_CLAIM_BOUNDARY,
        }
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                with self.audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
                self._notify_control_change(record)
                return record
            except OSError as exc:
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            record["audit_write_error"] = str(last_error)
        return record

    def _notify_control_change(self, record: Mapping[str, Any]) -> None:
        try:
            from cas_forex.critical_notifications import (
                build_ai_control_changed_event,
                emit_critical_notification,
            )

            emit_critical_notification(
                build_ai_control_changed_event(record),
                source=str(record.get("source") or "ai_control_authority"),
            )
        except Exception:
            return

    def objective(self) -> ProfitObjective:
        objective = self.owner_envelope.objective()
        return replace(
            objective,
            edge_threshold_default=float(self.control.get("edge_threshold")),
        )

    # -- owner writes ----------------------------------------------------
    def owner_update(self, source: str = "owner_update", **changes: Any) -> dict[str, Any]:
        with self._lock:
            allowed = set(asdict(self.owner_envelope))
            unknown = sorted(set(changes) - allowed)
            if unknown:
                raise ValueError(f"Unknown owner envelope field(s): {unknown}")
            before = self.snapshot()
            next_owner = replace(self.owner_envelope, **changes).normalized()
            self.owner_envelope = next_owner
            self._clamp_surface_to_envelope()
            self.save()
            after = self.snapshot()
            before_owner = before.get("owner_envelope") if isinstance(before.get("owner_envelope"), Mapping) else {}
            after_owner = after.get("owner_envelope") if isinstance(after.get("owner_envelope"), Mapping) else {}
            before_values = (
                (before.get("control_surface") or {}).get("values")
                if isinstance(before.get("control_surface"), Mapping)
                else {}
            )
            after_values = (
                (after.get("control_surface") or {}).get("values")
                if isinstance(after.get("control_surface"), Mapping)
                else {}
            )
            change_rows = [
                {**row, "scope": "owner_envelope"}
                for row in _diff_mapping(before_owner, after_owner, set(changes))
            ]
            change_rows.extend(
                {**row, "scope": "control_surface"}
                for row in _diff_mapping(before_values, after_values)
            )
            audit = self._append_audit(
                action="OWNER_ENVELOPE_UPDATE",
                source=source,
                before=before,
                after=after,
                changes=change_rows,
                request={"changes": changes},
            )
            after["latest_audit"] = audit
            return after

    # -- AI writes -------------------------------------------------------
    def ai_adjust(
        self,
        lever: str,
        value: Any,
        *,
        reason: str = "",
        source: str = "ai_adjust",
    ) -> dict[str, Any]:
        with self._lock:
            before = self.snapshot()
            impact_preview = self.preview_ai_adjust(lever, value, reason=reason)
            preview_posture = str(impact_preview.get("posture") or "unchanged")
            preview_anti_impulse = (
                impact_preview.get("anti_impulse") if isinstance(impact_preview, Mapping) else {}
            )
            journal_review = _anti_impulse_journal_review(
                reason,
                posture=preview_posture,
                projected_warning_active=bool(
                    preview_anti_impulse.get("projected_warning_active")
                    if isinstance(preview_anti_impulse, Mapping)
                    else False
                ),
            )
            if journal_review.get("required") and not journal_review.get("satisfied"):
                raise ValueError(
                    "Loosening AI dials requires an anti-impulse journal reason before the "
                    f"control file can change: {'; '.join(journal_review.get('blockers') or [])}"
                )
            if preview_posture == "loosen" and bool(
                preview_anti_impulse.get("projected_cooldown_blocked")
                if isinstance(preview_anti_impulse, Mapping)
                else False
            ):
                raise ValueError(
                    str(
                        preview_anti_impulse.get("cooldown_detail")
                        if isinstance(preview_anti_impulse, Mapping)
                        else "AI dial loosening cooldown is active."
                    )
                )
            checked_value, owner_clamped, owner_reason = self._apply_owner_limit(lever, value)
            result = self.control.adjust(lever, checked_value)
            result["owner_clamped"] = bool(owner_clamped or result.get("clamped"))
            result["owner_reason"] = owner_reason
            result["ai_reason"] = reason
            after = self.snapshot()
            before_values = (
                (before.get("control_surface") or {}).get("values")
                if isinstance(before.get("control_surface"), Mapping)
                else {}
            )
            after_values = (
                (after.get("control_surface") or {}).get("values")
                if isinstance(after.get("control_surface"), Mapping)
                else {}
            )
            change_rows = [
                {**row, "scope": "control_surface"}
                for row in _diff_mapping(before_values, after_values, {str(lever)})
            ]
            posture = (
                str(change_rows[0].get("posture"))
                if change_rows
                else str(impact_preview.get("posture") or "unchanged")
            )
            audit = self._append_audit(
                action="AI_DIAL_ADJUST",
                source=source,
                before=before,
                after=after,
                changes=change_rows,
                request={"lever": lever, "requested": value, "checked": checked_value, "reason": reason},
                result={
                    "ok": result.get("ok"),
                    "old": result.get("old"),
                    "new": result.get("new"),
                    "clamped": result.get("clamped"),
                    "owner_clamped": result.get("owner_clamped"),
                    "owner_reason": result.get("owner_reason"),
                    "ai_reason": result.get("ai_reason"),
                    "anti_impulse_journal": journal_review,
                },
            )
            result["audit"] = audit
            result["snapshot"] = after
            result["posture"] = posture
            result["impact"] = impact_preview.get("impact") if isinstance(impact_preview, Mapping) else None
            result["binding"] = impact_preview.get("binding") if isinstance(impact_preview, Mapping) else None
            result["contract_rows"] = (
                impact_preview.get("contract_rows")
                if isinstance(impact_preview, Mapping)
                else None
            )
            result["anti_impulse"] = self.anti_impulse_report()
            result["anti_impulse_journal"] = journal_review
            return result

    def _apply_owner_limit(self, lever: str, value: Any) -> tuple[Any, bool, str]:
        owner = self.owner_envelope
        if lever == "symbols":
            requested = {value} if isinstance(value, str) else {str(v) for v in value}
            kept = [s for s in owner.allowed_symbols if s in requested]
            if not kept:
                raise ValueError("symbols request falls outside owner allowed_symbols")
            return kept, kept != list(requested), "symbols constrained by owner allowed_symbols"
        if lever == "sessions":
            requested = {value} if isinstance(value, str) else {str(v) for v in value}
            kept = [s for s in owner.allowed_sessions if s in requested]
            if not kept:
                raise ValueError("sessions request falls outside owner allowed_sessions")
            return kept, kept != list(requested), "sessions constrained by owner allowed_sessions"
        if lever == "timeframes":
            requested = (
                {str(value).upper()}
                if isinstance(value, str)
                else {str(v).upper() for v in value}
            )
            kept = [tf for tf in owner.allowed_timeframes if tf in requested]
            if not kept:
                raise ValueError("timeframes request falls outside owner allowed_timeframes")
            return (
                kept,
                set(kept) != requested,
                "timeframes constrained by owner allowed_timeframes",
            )
        bounds = _CONTROL_NUMERIC_OWNER_LIMITS.get(lever)
        if bounds is None:
            return value, False, "no additional owner limit for this lever"
        raw = float(value)
        lo_ref, hi_ref = bounds
        lo = float(getattr(owner, lo_ref) if isinstance(lo_ref, str) else lo_ref)
        hi = float(getattr(owner, hi_ref) if isinstance(hi_ref, str) else hi_ref)
        clamped = min(max(raw, lo), hi)
        if lever in {"max_concurrent_trades", "max_compound_units"}:
            clamped = int(round(clamped))
        return clamped, clamped != raw, f"clamped to owner range [{lo}, {hi}]"

    def _clamp_surface_to_envelope(self) -> None:
        for lever, bounds in _CONTROL_NUMERIC_OWNER_LIMITS.items():
            current = self.control.get(lever)
            checked, _clamped, _reason = self._apply_owner_limit(lever, current)
            self.control.adjust(lever, checked)
        self.control.adjust(
            "symbols",
            [s for s in self.control.get("symbols") if s in self.owner_envelope.allowed_symbols]
            or [self.owner_envelope.allowed_symbols[0]],
        )
        self.control.adjust(
            "sessions",
            [s for s in self.control.get("sessions") if s in self.owner_envelope.allowed_sessions]
            or [self.owner_envelope.allowed_sessions[0]],
        )
        self.control.adjust(
            "timeframes",
            [
                tf
                for tf in self.control.get("timeframes")
                if tf in self.owner_envelope.allowed_timeframes
            ]
            or [self.owner_envelope.allowed_timeframes[0]],
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _authority_audit_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    surface = snapshot.get("control_surface") if isinstance(snapshot, Mapping) else {}
    values = surface.get("values") if isinstance(surface, Mapping) else {}
    return {
        "updated_at": snapshot.get("updated_at") if isinstance(snapshot, Mapping) else None,
        "owner_envelope": _jsonable(snapshot.get("owner_envelope") if isinstance(snapshot, Mapping) else {}),
        "control_values": _jsonable(values if isinstance(values, Mapping) else {}),
    }


def _diff_mapping(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    if keys is None:
        keys = set(before) | set(after)
    rows: list[dict[str, Any]] = []
    for key in sorted(keys):
        before_value = _jsonable(before.get(key))
        after_value = _jsonable(after.get(key))
        if before_value == after_value:
            continue
        rows.append(
            {
                "key": key,
                "before": before_value,
                "after": after_value,
                "posture": _change_posture(str(key), before_value, after_value),
            }
        )
    return rows


def _parse_audit_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _anti_impulse_journal_review(
    reason: Any,
    *,
    posture: str,
    projected_warning_active: bool,
) -> dict[str, Any]:
    required = str(posture or "").lower() == "loosen"
    text = str(reason or "").strip()
    lowered = text.lower()
    blockers: list[str] = []
    if required:
        if len(text) < AI_DIAL_LOOSEN_REASON_MIN_CHARS:
            blockers.append(
                f"reason must be at least {AI_DIAL_LOOSEN_REASON_MIN_CHARS} characters"
            )
        if "no reason" in lowered:
            blockers.append("reason cannot say no reason was given")
    return {
        "required": required,
        "satisfied": not blockers,
        "reason_length": len(text),
        "minimum_reason_length": AI_DIAL_LOOSEN_REASON_MIN_CHARS,
        "blockers": blockers,
        "prompt": AI_DIAL_LOOSEN_JOURNAL_PROMPT if required else "",
        "owner_review_recommended": bool(projected_warning_active),
        "claim_boundary": (
            "Anti-impulse journaling gates dial-loosening writes only. It does not "
            "authorize live trading, place orders, or prove that a change is profitable."
        ),
    }


def _change_posture(key: str, before: Any, after: Any) -> str:
    """Classify whether an authority change widens or narrows trade latitude."""
    if before == after:
        return "unchanged"
    if key in _BREADTH_KEYS:
        before_count = _item_count(before)
        after_count = _item_count(after)
        if after_count > before_count:
            return "loosen"
        if after_count < before_count:
            return "tighten"
        return "changed"
    if key in _PERMISSION_KEYS:
        if bool(after) and not bool(before):
            return "loosen"
        if bool(before) and not bool(after):
            return "tighten"
        return "changed"
    if key in _FRESH_PASS_KEYS:
        if bool(after) and not bool(before):
            return "tighten"
        if bool(before) and not bool(after):
            return "loosen"
        return "changed"
    numeric = _numeric_delta(before, after)
    if numeric is None:
        return "changed"
    old, new = numeric
    if key in _LOWER_VALUE_LOOSENS:
        return "loosen" if new < old else "tighten"
    if key in _HIGHER_VALUE_LOOSENS:
        return "loosen" if new > old else "tighten"
    if key == "trailing_stop_enabled":
        return "tighten" if new > old else "loosen"
    return "changed"


def _numeric_delta(before: Any, after: Any) -> tuple[float, float] | None:
    try:
        return float(before), float(after)
    except (TypeError, ValueError):
        return None


def _item_count(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value else 0
    if isinstance(value, (list, tuple, set, frozenset)):
        return len(value)
    if value is None:
        return 0
    return 1


def _contract_row_effect(row: Mapping[str, Any]) -> str:
    value_kind = str(row.get("value_kind") or "")
    units = str(row.get("units") or "").strip()
    bound = _owner_bound_effect_text(row.get("owner_bound"))
    if value_kind == "subset":
        before_count = int(row.get("before_count") or 0)
        after_count = int(row.get("after_count") or 0)
        added = ", ".join(str(item) for item in (row.get("added") or []))
        removed = ", ".join(str(item) for item in (row.get("removed") or []))
        parts = [
            f"{row.get('field')} goes from {before_count} to {after_count} allowed {units or 'items'}",
        ]
        if added:
            parts.append(f"added: {added}")
        if removed:
            parts.append(f"removed: {removed}")
        if bound:
            parts.append(f"owner envelope {bound}")
        return ". ".join(parts) + "."
    before = _display_contract_value(row.get("before"), value_kind=value_kind)
    after = _display_contract_value(row.get("after"), value_kind=value_kind)
    unit_suffix = f" {units}" if units else ""
    parts = [f"{row.get('field')} changes from {before} to {after}{unit_suffix}"]
    if bound:
        parts.append(f"owner envelope {bound}")
    return ". ".join(parts) + "."


def _owner_bound_effect_text(bound: Any) -> str:
    if not isinstance(bound, Mapping):
        return ""
    if "min" in bound and "max" in bound:
        return f"[{bound.get('min')}, {bound.get('max')}]"
    allowed = bound.get("allowed")
    if isinstance(allowed, list):
        return "allows {" + ", ".join(str(item) for item in allowed) + "}"
    return ""


def _display_contract_value(value: Any, *, value_kind: str = "") -> str:
    if value_kind == "toggle":
        return "ON" if bool(value) else "OFF"
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


_AUTHORITY: Optional[AiControlAuthority] = None
_AUTHORITY_LOCK = threading.Lock()


def get_authority(state_path: Path | str | None = None) -> AiControlAuthority:
    """Return the process-global control authority.

    A bare call (``state_path is None``) means "give me the current process
    authority" — it returns whatever is set (including a test-injected one via
    ``set_authority_for_tests``) and only constructs a default if none exists.
    Passing an explicit path (re)binds to that store.
    """
    global _AUTHORITY
    with _AUTHORITY_LOCK:
        if state_path is None:
            if _AUTHORITY is None:
                resolved = DEFAULT_STATE_PATH
                # Test isolation: a pytest run must NEVER touch (or persist to)
                # the owner's live authority store — full-suite runs were
                # scrambling the live dials (edge threshold, learning mode)
                # mid-trading.
                if os.environ.get("PYTEST_CURRENT_TEST"):
                    import tempfile

                    resolved = Path(tempfile.gettempdir()) / f"cas-forex-test-authority-{os.getpid()}.json"
                _AUTHORITY = AiControlAuthority(resolved)
            return _AUTHORITY
        if _AUTHORITY is None or Path(state_path) != _AUTHORITY.state_path:
            _AUTHORITY = AiControlAuthority(Path(state_path))
        return _AUTHORITY


def set_authority_for_tests(authority: Optional[AiControlAuthority]) -> None:
    global _AUTHORITY
    with _AUTHORITY_LOCK:
        _AUTHORITY = authority


def reset_authority(state_path: Path | str = DEFAULT_STATE_PATH) -> AiControlAuthority:
    """Reset the authority file and singleton to defaults."""
    path = Path(state_path)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    authority = AiControlAuthority(path)
    set_authority_for_tests(authority)
    authority.save()
    return authority
