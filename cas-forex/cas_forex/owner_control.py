"""Owner-controlled promotion policy for CAS FOREX strategy candidates.

This is the switchboard after CAS-SDG, Condition Lab, walk-forward, and paper
proof produce enough wins. It can authorize notification or paper-mode attempts,
but it cannot create live broker authority or payment transfers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence


CLAIM_BOUNDARY = "Owner control policy is research/paper-only. Live trading remains NOT LICENSED."
MAX_OWNER_AUTO_TRADES = 15
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "runtime" / "owner-control-overrides.json"


class OwnerControlMode(str, Enum):
    DENY = "DENY"
    NOTIFY_ONLY = "NOTIFY_ONLY"
    LIMITED_PAPER = "LIMITED_PAPER"
    PAPER_AUTO = "PAPER_AUTO"
    AI_FULL_AUTO_PAPER = "AI_FULL_AUTO_PAPER"
    LIVE_AUTO = "LIVE_AUTO"
    AI_FULL_AUTO_LIVE_REQUESTED = "AI_FULL_AUTO_LIVE_REQUESTED"


class OwnerPromotionVerdict(str, Enum):
    DENIED = "DENIED"
    NOTIFY = "NOTIFY"
    LIMITED_PAPER_AUTHORIZED = "LIMITED_PAPER_AUTHORIZED"
    PAPER_AUTO_AUTHORIZED = "PAPER_AUTO_AUTHORIZED"
    AI_FULL_AUTO_PAPER_AUTHORIZED = "AI_FULL_AUTO_PAPER_AUTHORIZED"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    LIVE_BLOCKED_NOT_LICENSED = "LIVE_BLOCKED_NOT_LICENSED"


@dataclass(frozen=True)
class PromotionThresholds:
    min_simulator_wins: int = 10
    min_walk_forward_windows: int = 10
    min_positive_routed_window_rate: float = 0.60
    min_mean_return_pct: float = 0.50
    max_drawdown_pct: float = 5.0
    min_trades: int = 30
    min_paper_days: int = 30
    require_paper_passed: bool = True


@dataclass
class StrategyPromotionCandidate:
    lead_id: str
    strategy_setting: str
    source: str
    simulator_wins: int = 0
    walk_forward_windows: int = 0
    positive_routed_window_rate: float = 0.0
    mean_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    trades: int = 0
    paper_days: int = 0
    paper_passed: bool = False
    evidence_refs: List[str] = field(default_factory=list)
    condition_contexts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class OwnerPromotionDecision:
    verdict: OwnerPromotionVerdict
    reasons: List[str]
    owner_mode: OwnerControlMode
    max_paper_trades_authorized: int = 0
    notification_required: bool = True
    can_place_live_trades: bool = False
    can_transfer_money: bool = False
    claim_boundary: str = CLAIM_BOUNDARY


_DEFAULT_STATE: dict[str, Any] = {
    "mode": OwnerControlMode.AI_FULL_AUTO_PAPER.value,
    "max_concurrent_trades": MAX_OWNER_AUTO_TRADES,
    "max_loss_cap_pct": 10,
    "ai_autonomy_enabled": True,
}
_OVERRIDES: dict[str, Any] = {}
_OVERRIDES_LOADED = False
_OVERRIDE_PATH: Path | None = DEFAULT_OVERRIDE_PATH


def _load_overrides() -> None:
    global _OVERRIDES_LOADED
    if _OVERRIDES_LOADED:
        return
    _OVERRIDES_LOADED = True
    if _OVERRIDE_PATH is None or not _OVERRIDE_PATH.exists():
        return
    try:
        payload = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    raw = payload.get("overrides") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return
    for key in _DEFAULT_STATE:
        if key in raw:
            try:
                _OVERRIDES[key] = _clean_owner_control_value(key, raw[key])
            except (TypeError, ValueError):
                continue


def _save_overrides() -> None:
    if _OVERRIDE_PATH is None:
        return
    if not _OVERRIDES:
        try:
            _OVERRIDE_PATH.unlink()
        except FileNotFoundError:
            pass
        return
    payload = {
        "report_kind": "cas_forex_owner_control_overrides",
        "overrides": dict(_OVERRIDES),
        "claim_boundary": (
            "Local owner-control mode for the single-owner CAS Forex cockpit. "
            "This state changes paper/autonomy policy only; it does not place "
            "orders, create broker ACCEPT, authorize payment movement, deposit, "
            "withdraw, or mark any live-money capability LICENSED."
        ),
    }
    _OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _OVERRIDE_PATH.with_suffix(_OVERRIDE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_OVERRIDE_PATH)


def set_owner_control_override_store_for_tests(path: Path | str | None) -> None:
    global _OVERRIDE_PATH, _OVERRIDES_LOADED
    _OVERRIDE_PATH = Path(path) if path is not None else None
    _OVERRIDES.clear()
    _OVERRIDES_LOADED = False


def _clean_owner_control_value(key: str, value: Any) -> Any:
    if key == "mode":
        mode = OwnerControlMode(str(value))
        return mode.value
    if key == "max_concurrent_trades":
        parsed = int(value)
        if parsed < 1:
            raise ValueError("max_concurrent_trades must be >= 1")
        return parsed
    if key == "max_loss_cap_pct":
        parsed = float(value)
        if parsed < 0:
            raise ValueError("max_loss_cap_pct must be >= 0")
        return parsed
    if key == "ai_autonomy_enabled":
        return bool(value)
    raise ValueError(f"Unknown owner-control field: {key}")


def set_owner_control_overrides(**fields: Any) -> dict[str, Any]:
    _load_overrides()
    changed = False
    for key, value in fields.items():
        if value is None:
            continue
        if key not in _DEFAULT_STATE:
            raise ValueError(f"Unknown owner-control field: {key}")
        _OVERRIDES[key] = _clean_owner_control_value(key, value)
        changed = True
    if changed:
        _save_overrides()
    return build_owner_control_report()


def clear_owner_control_overrides() -> None:
    global _OVERRIDES_LOADED
    _OVERRIDES.clear()
    _OVERRIDES_LOADED = True
    _save_overrides()


def build_owner_control_report(*, live_authorized: bool = False) -> dict[str, Any]:
    _load_overrides()
    state = dict(_DEFAULT_STATE)
    state.update(_OVERRIDES)
    mode = OwnerControlMode(str(state["mode"]))
    live_requested = mode in {OwnerControlMode.LIVE_AUTO, OwnerControlMode.AI_FULL_AUTO_LIVE_REQUESTED}
    live_blocked = bool(live_requested and not live_authorized)
    state.update(
        {
            "mode": mode.value,
            "live_requested": live_requested,
            "live_blocked": live_blocked,
            "override_count": len(_OVERRIDES),
            "persisted": bool(_OVERRIDE_PATH is not None and _OVERRIDE_PATH.exists()),
            "override_state_path": str(_OVERRIDE_PATH) if _OVERRIDE_PATH is not None else None,
            "allowed_modes": [item.value for item in OwnerControlMode],
            "claim_boundary": (
                "Owner control policy is owner-controlled: CAS Forex can run "
                "research/paper automation now. Selecting a live-requested mode "
                "records the owner's intent only; live trading, broker ACCEPT, "
                "and payment movement still require explicit owner enable flags, "
                "credentials/provider config, gate clearance, and action-time checks."
            ),
        }
    )
    return state


def review_owner_promotion(
    candidate: StrategyPromotionCandidate,
    *,
    owner_mode: OwnerControlMode = OwnerControlMode.NOTIFY_ONLY,
    thresholds: PromotionThresholds = PromotionThresholds(),
    max_paper_trades: int = 1,
) -> OwnerPromotionDecision:
    """Review whether a strategy candidate can move beyond research review."""
    if owner_mode == OwnerControlMode.DENY:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.DENIED,
            reasons=["Owner mode is DENY."],
            owner_mode=owner_mode,
        )

    if owner_mode in {OwnerControlMode.LIVE_AUTO, OwnerControlMode.AI_FULL_AUTO_LIVE_REQUESTED}:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.LIVE_BLOCKED_NOT_LICENSED,
            reasons=[
                f"Owner requested {owner_mode.value}, but live trading remains NOT LICENSED.",
                "Broker execution and payment transfers require separate legal/broker/paper-proof gates.",
            ],
            owner_mode=owner_mode,
        )

    blockers = _threshold_blockers(candidate, thresholds)
    if not candidate.evidence_refs:
        blockers.append("Candidate has no evidence_refs.")
    if not candidate.condition_contexts:
        blockers.append("Candidate has no condition_contexts.")

    if blockers:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.NOTIFY,
            reasons=blockers,
            owner_mode=owner_mode,
        )

    if owner_mode == OwnerControlMode.NOTIFY_ONLY:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.NOTIFY,
            reasons=["Candidate meets thresholds, but owner mode is NOTIFY_ONLY."],
            owner_mode=owner_mode,
        )

    if owner_mode == OwnerControlMode.LIMITED_PAPER:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.LIMITED_PAPER_AUTHORIZED,
            reasons=[f"Candidate meets thresholds; limited paper attempts capped at {allowed}."],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
        )

    if owner_mode == OwnerControlMode.PAPER_AUTO:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.PAPER_AUTO_AUTHORIZED,
            reasons=[f"Candidate meets thresholds for paper-mode auto routing, capped at {allowed} trades."],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
            notification_required=False,
        )

    if owner_mode == OwnerControlMode.AI_FULL_AUTO_PAPER:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.AI_FULL_AUTO_PAPER_AUTHORIZED,
            reasons=[
                "Owner authorized AI_FULL_AUTO_PAPER.",
                f"AI may choose paper-mode route/settings/risk within evidence gates, capped at {allowed} trades.",
            ],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
            notification_required=False,
        )

    return OwnerPromotionDecision(
        verdict=OwnerPromotionVerdict.FLAG_FOR_HUMAN_REVIEW,
        reasons=[f"Unsupported owner mode: {owner_mode}"],
        owner_mode=owner_mode,
    )


def candidate_from_tally_bucket(
    bucket: Mapping[str, Any],
    *,
    lead_id: str,
    source: str,
    simulator_wins: int = 0,
    paper_days: int = 0,
    paper_passed: bool = False,
    evidence_refs: Optional[List[str]] = None,
) -> StrategyPromotionCandidate:
    """Build a promotion candidate from a condition-tally bucket."""
    axes: Mapping[str, Any] = bucket.get("axes", {}) if isinstance(bucket.get("axes"), Mapping) else {}
    setting = str(axes.get("setting") or bucket.get("setting") or "unknown")
    contexts = [
        str(value)
        for key, value in axes.items()
        if key in {"test_event_context", "event_context", "test_regime", "regime", "timeframe", "symbol"}
    ]
    return StrategyPromotionCandidate(
        lead_id=lead_id,
        strategy_setting=setting,
        source=source,
        simulator_wins=simulator_wins,
        walk_forward_windows=int(bucket.get("routed_windows", bucket.get("windows", 0)) or 0),
        positive_routed_window_rate=float(bucket.get("positive_window_rate", 0.0) or 0.0),
        mean_return_pct=float(bucket.get("mean_return_pct", 0.0) or 0.0),
        max_drawdown_pct=float(bucket.get("max_drawdown_pct", 0.0) or 0.0),
        trades=int(bucket.get("trades", 0) or 0),
        paper_days=paper_days,
        paper_passed=paper_passed,
        evidence_refs=list(evidence_refs or []),
        condition_contexts=contexts,
    )


def count_condition_lab_simulator_wins(
    cells: Sequence[Mapping[str, Any]],
    *,
    setting: Optional[str] = None,
    min_return_pct: float = 0.0,
    max_drawdown_pct: float = 20.0,
    min_trades: float = 1.0,
    require_non_gap: bool = True,
) -> int:
    """Count Condition Lab cells that qualify as simulator wins."""
    wins = 0
    for cell in cells:
        if setting and cell.get("setting") != setting:
            continue
        if require_non_gap and bool(cell.get("is_gap", True)):
            continue
        if float(cell.get("mean_return_pct", 0.0) or 0.0) < min_return_pct:
            continue
        if float(cell.get("mean_max_dd_pct", 0.0) or 0.0) > max_drawdown_pct:
            continue
        if float(cell.get("mean_trades", 0.0) or 0.0) < min_trades:
            continue
        wins += 1
    return wins


def _threshold_blockers(
    candidate: StrategyPromotionCandidate,
    thresholds: PromotionThresholds,
) -> List[str]:
    blockers: List[str] = []
    if candidate.simulator_wins < thresholds.min_simulator_wins:
        blockers.append(
            f"simulator_wins {candidate.simulator_wins} < required {thresholds.min_simulator_wins}"
        )
    if candidate.walk_forward_windows < thresholds.min_walk_forward_windows:
        blockers.append(
            f"walk_forward_windows {candidate.walk_forward_windows} < required {thresholds.min_walk_forward_windows}"
        )
    if candidate.positive_routed_window_rate < thresholds.min_positive_routed_window_rate:
        blockers.append(
            "positive_routed_window_rate "
            f"{candidate.positive_routed_window_rate:.4f} < required {thresholds.min_positive_routed_window_rate:.4f}"
        )
    if candidate.mean_return_pct < thresholds.min_mean_return_pct:
        blockers.append(
            f"mean_return_pct {candidate.mean_return_pct:.4f} < required {thresholds.min_mean_return_pct:.4f}"
        )
    if candidate.max_drawdown_pct > thresholds.max_drawdown_pct:
        blockers.append(
            f"max_drawdown_pct {candidate.max_drawdown_pct:.4f} > allowed {thresholds.max_drawdown_pct:.4f}"
        )
    if candidate.trades < thresholds.min_trades:
        blockers.append(f"trades {candidate.trades} < required {thresholds.min_trades}")
    if candidate.paper_days < thresholds.min_paper_days:
        blockers.append(f"paper_days {candidate.paper_days} < required {thresholds.min_paper_days}")
    if thresholds.require_paper_passed and not candidate.paper_passed:
        blockers.append("paper_passed is false.")
    return blockers
