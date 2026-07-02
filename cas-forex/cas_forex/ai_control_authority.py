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
import threading
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.ai_control_surface import AiControlSurface, SUPPORTED_SESSIONS
from cas_forex.ai_objective import ProfitObjective
from cas_forex.instruments import SUPPORTED_SYMBOLS

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "ai-control-authority.json"

_CONTROL_NUMERIC_OWNER_LIMITS = {
    "edge_threshold": ("edge_threshold_min", "edge_threshold_max"),
    "max_risk_pct_per_trade": (0.0, "max_risk_pct_per_trade"),
    "max_concurrent_trades": (1, "max_concurrent_trades"),
    "max_compound_units": (0, "max_compound_units"),
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
    allow_long: bool = True
    allow_short: bool = True
    edge_threshold_min: float = 0.50
    edge_threshold_max: float = 0.95
    max_risk_pct_per_trade: float = 5.0
    max_concurrent_trades: int = 50
    max_compound_units: int = 8
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
        if self.max_risk_pct_per_trade < 0:
            raise ValueError("max_risk_pct_per_trade must be >= 0")
        if self.max_concurrent_trades < 1:
            raise ValueError("max_concurrent_trades must be >= 1")
        if self.max_compound_units < 0:
            raise ValueError("max_compound_units must be >= 0")
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
        return replace(self, allowed_symbols=symbols, allowed_sessions=sessions)

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

    def __init__(self, state_path: Path | str = DEFAULT_STATE_PATH) -> None:
        self.state_path = Path(state_path)
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
            return {
                "report_kind": "cas_forex_ai_control_authority",
                "owner_envelope": _jsonable(asdict(self.owner_envelope)),
                "control_surface": surface,
                "updated_at": self.updated_at,
                "state_path": str(self.state_path),
                "authority_note": (
                    "Owner sets the envelope. AI may adjust dials inside it. "
                    "This does not enable live trading or money movement."
                ),
                "direction_note": (
                    "LONG and SHORT are separate owner-permitted actions; the AI "
                    "may also choose NO_TRADE."
                ),
            }

    def objective(self) -> ProfitObjective:
        objective = self.owner_envelope.objective()
        return replace(
            objective,
            edge_threshold_default=float(self.control.get("edge_threshold")),
        )

    # -- owner writes ----------------------------------------------------
    def owner_update(self, **changes: Any) -> dict[str, Any]:
        with self._lock:
            allowed = set(asdict(self.owner_envelope))
            unknown = sorted(set(changes) - allowed)
            if unknown:
                raise ValueError(f"Unknown owner envelope field(s): {unknown}")
            next_owner = replace(self.owner_envelope, **changes).normalized()
            self.owner_envelope = next_owner
            self._clamp_surface_to_envelope()
            self.save()
            return self.snapshot()

    # -- AI writes -------------------------------------------------------
    def ai_adjust(self, lever: str, value: Any, *, reason: str = "") -> dict[str, Any]:
        with self._lock:
            checked_value, owner_clamped, owner_reason = self._apply_owner_limit(lever, value)
            result = self.control.adjust(lever, checked_value)
            result["owner_clamped"] = bool(owner_clamped or result.get("clamped"))
            result["owner_reason"] = owner_reason
            result["ai_reason"] = reason
            result["snapshot"] = self.snapshot()
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


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


_AUTHORITY: Optional[AiControlAuthority] = None
_AUTHORITY_LOCK = threading.Lock()


def get_authority(state_path: Path | str = DEFAULT_STATE_PATH) -> AiControlAuthority:
    global _AUTHORITY
    with _AUTHORITY_LOCK:
        if _AUTHORITY is None or Path(state_path) != _AUTHORITY.state_path:
            _AUTHORITY = AiControlAuthority(state_path)
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
