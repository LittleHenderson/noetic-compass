"""Durable real-candle WASTE probe.

This is an owner-visible rehearsal of WATCH -> ANALYZE -> STRATEGIZE -> TEST on
real connector candles. It never starts the timed runner, registers edge
authorization, touches a broker bridge, places orders, closes positions, or
moves money.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.ai_control_authority import AiControlAuthority, get_authority
from cas_forex.directional_intelligence import analyze_market_state, strategize_market_state
from cas_forex.edge_gate import CandidateSetup as GateCandidateSetup
from cas_forex.edge_gate import evaluate_candidate
from cas_forex.market_data.connector import MarketDataConnector
from cas_forex.time_utils import utc_now
from cas_forex.waste_market_data import (
    DEFAULT_MAX_ENTRY_PAIRS,
    DEFAULT_OOS_HORIZON_BARS,
    DEFAULT_WASTE_BARS,
    DEFAULT_WASTE_TIMEFRAME,
    build_waste_market_state,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "waste-real-candle-probe.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-real-candle-probe-audit.jsonl"

REPORT_KIND = "cas_forex_waste_real_candle_probe"
STATUS_NO_CANDLES = "NO_USABLE_CANDLES"
STATUS_NO_CANDIDATE = "NO_CANDIDATE"
STATUS_EDGE_BLOCKED = "EDGE_BLOCKED"
STATUS_EDGE_PASS_UNREGISTERED = "EDGE_PASS_UNREGISTERED"
STATUS_ERROR = "PROBE_ERROR"
STATUS_DRY_RUN_HANDOFF_READY = "WASTE_PROBE_DRY_RUN_HANDOFF_READY"

CLAIM_BOUNDARY = (
    "WASTE real-candle probe runs WATCH/ANALYZE/STRATEGIZE/TEST on connector "
    "candles for evidence. It does not start the timed WASTE runner, register "
    "edge authorization, place orders, close positions, call a broker bridge, "
    "create broker ACCEPT, create owner ACCEPT, authorize live trading, deposit, "
    "withdraw, transfer funds, or automate payouts. Any edge PASS token returned "
    "by the edge gate is not persisted and is not registered for dispatch."
)


class WasteRealCandleProbeLog:
    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
    ) -> None:
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)

    def record(self, report: Mapping[str, Any]) -> dict[str, Any]:
        record = {
            "audit_id": stable_ledger_id(
                "waste-real-candle-probe",
                str(report.get("generated_at") or ""),
                str(report.get("symbol") or ""),
                str(report.get("status") or ""),
                str((report.get("candidate") or {}).get("decision_ref") if isinstance(report.get("candidate"), Mapping) else ""),
            ),
            "action": "WASTE_REAL_CANDLE_PROBE",
            "timestamp": utc_now().isoformat(),
            "status": report.get("status"),
            "symbol": report.get("symbol"),
            "timeframe": report.get("timeframe"),
            "payload": dict(report),
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "report_kind": REPORT_KIND,
            "updated_at": utc_now().isoformat(),
            "latest_probe": dict(report),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

    def latest(self) -> Optional[dict[str, Any]]:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        latest = payload.get("latest_probe") if isinstance(payload, Mapping) else None
        return dict(latest) if isinstance(latest, Mapping) else None


class WasteRealCandleProbeDryRunError(ValueError):
    """Raised when a real-candle probe is not valid source evidence for dry-run."""


def latest_waste_real_candle_probe(
    *,
    log: Optional[WasteRealCandleProbeLog] = None,
) -> dict[str, Any]:
    log = log or WasteRealCandleProbeLog()
    latest = log.latest()
    if latest is None:
        return {
            "report_kind": REPORT_KIND,
            "status": "NO_PROBE_RECORDED",
            "broker_touched": False,
            "edge_authorization_registered": False,
            "detail": "No WASTE real-candle probe has been recorded yet.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    return latest


def build_live_order_dry_run_from_latest_probe(
    *,
    volume: float,
    order_id: Optional[str] = None,
    expected_loss_usd: Optional[float] = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    log: Optional[WasteRealCandleProbeLog] = None,
    dry_run_audit: Any = None,
) -> dict[str, Any]:
    """Build a live-order dry-run from the latest broker-grade WASTE probe.

    This is the server-side companion to the cockpit button. It refuses stale,
    synthetic, fallback, or non-market-backed candidates before a live-order
    dry-run audit can be created. The resulting live-order dry run still does
    not touch a broker bridge, and it still fails closed unless the normal live,
    edge, pilot, and risk gates pass.
    """

    probe = latest_waste_real_candle_probe(log=log)
    candidate, source = _market_backed_probe_candidate(probe)
    from cas_forex.live_order_dry_run import (
        DEFAULT_AUDIT_PATH,
        LiveOrderDryRunAuditLog,
        LiveOrderDryRunRequest,
        build_live_order_dry_run,
    )

    decision_ref = str(candidate["decision_ref"])
    generated_at = str(probe.get("generated_at") or utc_now().isoformat())
    request = LiveOrderDryRunRequest(
        order_id=order_id or _probe_dry_run_order_id(generated_at, decision_ref),
        decision_ref=decision_ref,
        symbol=str(candidate["symbol"]),
        direction=str(candidate["direction"]),
        volume=float(volume),
        stop_loss=float(candidate["stop_loss"]),
        take_profit=float(candidate["take_profit"]),
        price=float(candidate["entry"]),
        expected_loss_usd=expected_loss_usd,
        comment="CAS_WASTE_MARKET_DRY_RUN",
    )
    audit = dry_run_audit or LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH)
    report = build_live_order_dry_run(
        request,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        audit=None,
    )
    report["waste_real_candle_source"] = source
    report["claim_boundary"] = (
        str(report.get("claim_boundary") or "")
        + " This report was built from a persisted WASTE real-candle probe. "
        + "The handoff requires broker-grade read-only market data, a directional "
        + "hypothesis, no-lookahead holdout entry pairs, and strategy-firewall "
        + "allowance before dry-run evidence is recorded."
    )
    report["audit"] = audit.append(report)
    return report


def run_waste_real_candle_probe(
    *,
    symbol: Optional[str] = None,
    timeframe: str = DEFAULT_WASTE_TIMEFRAME,
    bars: int = DEFAULT_WASTE_BARS,
    horizon_bars: int = DEFAULT_OOS_HORIZON_BARS,
    max_pairs: int = DEFAULT_MAX_ENTRY_PAIRS,
    threshold: Optional[float] = None,
    connector: Optional[MarketDataConnector] = None,
    authority: Optional[AiControlAuthority] = None,
    log: Optional[WasteRealCandleProbeLog] = None,
) -> dict[str, Any]:
    """Run one real-candle WASTE probe and persist its evidence."""

    log = log or WasteRealCandleProbeLog()
    authority = authority or get_authority()
    generated_at = utc_now().isoformat()
    try:
        market_state = build_waste_market_state(
            connector=connector,
            authority=authority,
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
            horizon_bars=horizon_bars,
            max_pairs=max_pairs,
        )
        analysis = analyze_market_state(market_state)
        setup = strategize_market_state(market_state, analysis) if market_state.get("candles") else None
        edge = None
        status = STATUS_NO_CANDLES
        next_action = "Resolve connector/firewall blockers before WASTE can test real candles."
        if market_state.get("candles") and setup is None:
            status = STATUS_NO_CANDIDATE
            next_action = "Real candles were available, but WASTE did not form a candidate."
        elif setup is not None:
            gate_setup = _to_gate_setup(setup)
            edge = evaluate_candidate(
                gate_setup,
                list(getattr(setup, "entry_pairs", []) or []),
                threshold=float(threshold if threshold is not None else authority.control.get("edge_threshold")),
            )
            if edge.status == "PASS":
                status = STATUS_EDGE_PASS_UNREGISTERED
                next_action = (
                    "Edge gate returned PASS on real candles, but this probe did not register "
                    "authorization. Use the controlled runner/dry-run path before any dispatch."
                )
            else:
                status = STATUS_EDGE_BLOCKED
                next_action = "Real-candle candidate failed or underpowered at the edge gate; no dispatch path is opened."

        report = {
            "report_kind": REPORT_KIND,
            "generated_at": generated_at,
            "status": status,
            "symbol": market_state.get("symbol"),
            "timeframe": market_state.get("timeframe") or timeframe,
            "source": market_state.get("source"),
            "fallback_used": bool(market_state.get("fallback_used", False)),
            "broker_grade_market_truth": bool(market_state.get("broker_grade_market_truth", False)),
            "broker_touched": False,
            "edge_authorization_registered": False,
            "edge_token_persisted": False,
            "candles_count": len(market_state.get("candles") or []),
            "entry_pair_count": len(market_state.get("entry_pairs") or []),
            "market_state": _market_state_summary(market_state),
            "analysis": _safe_json(analysis),
            "candidate": _candidate_summary(setup),
            "edge": _edge_summary(edge),
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": next_action,
        }
    except Exception as exc:
        report = {
            "report_kind": REPORT_KIND,
            "generated_at": generated_at,
            "status": STATUS_ERROR,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": None,
            "fallback_used": False,
            "broker_touched": False,
            "edge_authorization_registered": False,
            "edge_token_persisted": False,
            "candles_count": 0,
            "entry_pair_count": 0,
            "market_state": None,
            "analysis": None,
            "candidate": None,
            "edge": None,
            "error": f"{type(exc).__name__}: {exc}",
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": "Fix the probe error before using WASTE real-candle evidence.",
        }
    audit = log.record(report)
    report["audit"] = audit
    return report


def _market_backed_probe_candidate(probe: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    candidate = probe.get("candidate") if isinstance(probe, Mapping) else None
    candidate = candidate if isinstance(candidate, Mapping) else {}
    market_state = probe.get("market_state") if isinstance(probe, Mapping) else None
    market_state = market_state if isinstance(market_state, Mapping) else {}
    hypothesis = candidate.get("directional_hypothesis")
    hypothesis = hypothesis if isinstance(hypothesis, Mapping) else {}
    market_meta = candidate.get("market_state_meta")
    market_meta = market_meta if isinstance(market_meta, Mapping) else {}
    entry_pair_report = market_state.get("entry_pair_report")
    entry_pair_report = entry_pair_report if isinstance(entry_pair_report, Mapping) else {}
    tuning = market_state.get("directional_hypothesis_tuning")
    tuning = tuning if isinstance(tuning, Mapping) else {}
    firewall = market_state.get("strategy_firewall")
    firewall = firewall if isinstance(firewall, Mapping) else {}
    edge = probe.get("edge") if isinstance(probe.get("edge"), Mapping) else {}

    def add(check_id: str, ok: bool, detail: str, evidence: Any = None) -> None:
        checks.append(
            {
                "check_id": check_id,
                "passed": bool(ok),
                "status": "PASS" if ok else "BLOCKED",
                "detail": detail,
                "evidence": _safe_json(evidence),
            }
        )

    add(
        "probe_report_kind",
        probe.get("report_kind") == REPORT_KIND,
        "Latest WASTE real-candle probe report is present.",
        {"report_kind": probe.get("report_kind")},
    )
    add(
        "probe_has_candidate",
        bool(candidate),
        "Probe contains a strategized candidate.",
        {"candidate_present": bool(candidate), "probe_status": probe.get("status")},
    )
    add(
        "probe_status_candidate_backed",
        str(probe.get("status") or "") in {STATUS_EDGE_BLOCKED, STATUS_EDGE_PASS_UNREGISTERED},
        "Probe reached the edge gate with a real candidate.",
        {"status": probe.get("status")},
    )
    add(
        "probe_broker_not_touched",
        not bool(probe.get("broker_touched", False)),
        "Probe did not touch a broker bridge.",
        {"broker_touched": probe.get("broker_touched")},
    )
    add(
        "probe_no_edge_authorization",
        not bool(probe.get("edge_authorization_registered", False)) and not bool(probe.get("edge_token_persisted", False)),
        "Probe did not register or persist an edge token.",
        {
            "edge_authorization_registered": probe.get("edge_authorization_registered"),
            "edge_token_persisted": probe.get("edge_token_persisted"),
        },
    )
    add(
        "broker_grade_market_truth",
        bool(probe.get("broker_grade_market_truth", False)) and bool(market_state.get("broker_grade_market_truth", False)),
        "Probe source is broker-grade read-only market data.",
        {
            "probe_broker_grade_market_truth": probe.get("broker_grade_market_truth"),
            "state_broker_grade_market_truth": market_state.get("broker_grade_market_truth"),
            "source": probe.get("source"),
        },
    )
    add(
        "candidate_geometry",
        _candidate_geometry_ok(candidate),
        "Candidate has symbol, direction, decision ref, entry, stop loss, and take profit.",
        {
            "symbol": candidate.get("symbol"),
            "direction": candidate.get("direction"),
            "decision_ref": candidate.get("decision_ref"),
        },
    )
    add(
        "directional_hypothesis_present",
        bool(hypothesis) and str(hypothesis.get("direction") or hypothesis.get("action") or "") in {"LONG", "SHORT"},
        "Candidate carries a LONG/SHORT directional hypothesis.",
        {
            "direction": hypothesis.get("direction"),
            "action": hypothesis.get("action"),
            "confidence": hypothesis.get("confidence"),
            "profile": hypothesis.get("profile"),
        },
    )
    entry_pair_count = int(candidate.get("entry_pair_count") or entry_pair_report.get("entry_pair_count") or 0)
    add(
        "holdout_entry_pairs_present",
        entry_pair_count > 0,
        "Candidate carries no-lookahead holdout entry pairs for edge testing.",
        {
            "candidate_entry_pair_count": candidate.get("entry_pair_count"),
            "state_entry_pair_count": entry_pair_report.get("entry_pair_count"),
        },
    )
    add(
        "no_lookahead_holdout",
        bool(tuning.get("no_lookahead", False)) and bool(tuning.get("validation_pairs_holdout", False)),
        "Directional tuning declares no-lookahead holdout validation.",
        {
            "no_lookahead": tuning.get("no_lookahead"),
            "validation_pairs_holdout": tuning.get("validation_pairs_holdout"),
            "selection_status": tuning.get("status"),
        },
    )
    add(
        "strategy_firewall_allows_candidate",
        bool(firewall.get("candidate_allowed", False)),
        "Strategy-ledger firewall allows this candidate for edge-gate testing.",
        {
            "candidate_allowed": firewall.get("candidate_allowed"),
            "firewall_status": firewall.get("firewall_status"),
            "lead_id": firewall.get("lead_id"),
        },
    )
    add(
        "market_state_meta_present",
        bool(market_meta),
        "Candidate preserves market-state metadata for owner review.",
        {
            "source": market_meta.get("source"),
            "broker_grade_market_truth": market_meta.get("broker_grade_market_truth"),
        },
    )

    blockers = [check for check in checks if not bool(check["passed"])]
    source = {
        "report_kind": "cas_forex_waste_real_candle_dry_run_source",
        "status": STATUS_DRY_RUN_HANDOFF_READY if not blockers else "WASTE_PROBE_DRY_RUN_SOURCE_BLOCKED",
        "probe_status": probe.get("status"),
        "probe_generated_at": probe.get("generated_at"),
        "probe_audit_id": (probe.get("audit") or {}).get("audit_id") if isinstance(probe.get("audit"), Mapping) else None,
        "symbol": candidate.get("symbol"),
        "timeframe": candidate.get("timeframe") or probe.get("timeframe"),
        "direction": candidate.get("direction"),
        "decision_ref": candidate.get("decision_ref"),
        "source": probe.get("source"),
        "broker_grade_market_truth": bool(probe.get("broker_grade_market_truth", False)),
        "entry_pair_count": entry_pair_count,
        "edge_status": edge.get("status") if isinstance(edge, Mapping) else None,
        "edge_has_token": bool(edge.get("has_edge_token")) if isinstance(edge, Mapping) else False,
        "checks": checks,
        "claim_boundary": (
            "WASTE real-candle dry-run source validation only proves that a "
            "candidate came from broker-grade read-only market data, directional "
            "hypothesis evidence, no-lookahead holdout entry pairs, and an allowed "
            "strategy-firewall lane. It does not authorize trading, mint edge "
            "tokens, place orders, create broker ACCEPT, create owner ACCEPT, "
            "deposit, withdraw, move bank/card money, automate payouts, or mark "
            "evidence LICENSED."
        ),
    }
    if blockers:
        reasons = "; ".join(f"{item['check_id']}: {item['detail']}" for item in blockers)
        raise WasteRealCandleProbeDryRunError(
            "Latest WASTE real-candle probe is not valid dry-run source evidence: " + reasons
        )
    return candidate, source


def _candidate_geometry_ok(candidate: Mapping[str, Any]) -> bool:
    if not candidate:
        return False
    if str(candidate.get("direction") or "") not in {"LONG", "SHORT"}:
        return False
    if not str(candidate.get("symbol") or "").strip():
        return False
    if not str(candidate.get("decision_ref") or "").strip():
        return False
    return all(_float(candidate.get(key)) is not None for key in ("entry", "stop_loss", "take_profit"))


def _probe_dry_run_order_id(generated_at: str, decision_ref: str) -> str:
    suffix = stable_ledger_id("waste-probe-dry-run", generated_at, decision_ref).rsplit("-", 1)[-1]
    return f"dry-waste-{suffix}"[:64]


def _to_gate_setup(setup: Any) -> GateCandidateSetup:
    return GateCandidateSetup(
        symbol=str(getattr(setup, "symbol")),
        timeframe=str(getattr(setup, "timeframe")),
        direction=str(getattr(setup, "direction")),
        entry=float(getattr(setup, "entry")),
        stop_loss=float(getattr(setup, "stop_loss")),
        take_profit=float(getattr(setup, "take_profit")),
        signal_strength=float(getattr(setup, "signal_strength")),
        regime=str(getattr(setup, "regime")),
        decision_ref=str(getattr(setup, "decision_ref")),
    )


def _market_state_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": state.get("report_kind"),
        "symbol": state.get("symbol"),
        "timeframe": state.get("timeframe"),
        "source": state.get("source"),
        "feed_label": state.get("feed_label"),
        "fallback_used": bool(state.get("fallback_used", False)),
        "broker_grade_market_truth": bool(state.get("broker_grade_market_truth", False)),
        "read_only_market_data": bool(state.get("read_only_market_data", False)),
        "execution_costs": _safe_json(state.get("execution_costs")),
        "market_data_claim_boundary": state.get("market_data_claim_boundary"),
        "error": state.get("error"),
        "quote": _safe_json(state.get("quote")),
        "strategy_firewall": _safe_json(state.get("strategy_firewall")),
        "strategy_firewall_skipped": _safe_json(state.get("strategy_firewall_skipped")),
        "connector_attempts": _safe_json(state.get("connector_attempts")),
        "entry_pair_report": _entry_pair_report_summary(state.get("entry_pair_report")),
        "selected_directional_profile": state.get("selected_directional_profile"),
        "directional_hypothesis_tuning": _hypothesis_tuning_summary(
            state.get("directional_hypothesis_tuning")
        ),
        "cas_feature_map": _safe_json(state.get("cas_feature_map")),
    }


def _entry_pair_report_summary(report: Any) -> dict[str, Any] | None:
    if not isinstance(report, Mapping):
        return None
    return {
        "evaluated_windows": report.get("evaluated_windows"),
        "skipped_no_trade": report.get("skipped_no_trade"),
        "horizon_bars": report.get("horizon_bars"),
        "cost_pips": report.get("cost_pips"),
        "entry_pair_count": len(report.get("entry_pairs") or []),
        "selected_profile": report.get("selected_profile"),
        "selection_status": (report.get("hypothesis_tuning") or {}).get("status")
        if isinstance(report.get("hypothesis_tuning"), Mapping)
        else None,
    }


def _hypothesis_tuning_summary(report: Any) -> dict[str, Any] | None:
    if not isinstance(report, Mapping):
        return None
    return {
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "reason": report.get("reason"),
        "selected_profile": report.get("selected_profile"),
        "selection_window_count": report.get("selection_window_count"),
        "validation_window_count": report.get("validation_window_count"),
        "no_lookahead": bool(report.get("no_lookahead", False)),
        "validation_pairs_holdout": bool(report.get("validation_pairs_holdout", False)),
        "candidate_profile_count": len(report.get("candidate_profiles") or []),
        "cas_feature_map": _safe_json(report.get("cas_feature_map")),
        "claim_boundary": report.get("claim_boundary"),
    }


def _candidate_summary(setup: Any) -> dict[str, Any] | None:
    if setup is None:
        return None
    return {
        "symbol": getattr(setup, "symbol", None),
        "timeframe": getattr(setup, "timeframe", None),
        "direction": getattr(setup, "direction", None),
        "entry": _float(getattr(setup, "entry", None)),
        "stop_loss": _float(getattr(setup, "stop_loss", None)),
        "take_profit": _float(getattr(setup, "take_profit", None)),
        "signal_strength": _float(getattr(setup, "signal_strength", None)),
        "regime": getattr(setup, "regime", None),
        "decision_ref": getattr(setup, "decision_ref", None),
        "entry_pair_count": len(getattr(setup, "entry_pairs", []) or []),
        "directional_hypothesis": _safe_json(getattr(setup, "directional_hypothesis", None)),
        "strategy_firewall": _safe_json(getattr(setup, "strategy_firewall", None)),
        "market_state_meta": _safe_json(getattr(setup, "market_state_meta", None)),
    }


def _edge_summary(edge: Any) -> dict[str, Any] | None:
    if edge is None:
        return None
    return {
        "status": getattr(edge, "status", None),
        "measured_win_prob": _float(getattr(edge, "measured_win_prob", None)),
        "null_p95": _float(getattr(edge, "null_p95", None)),
        "threshold": _float(getattr(edge, "threshold", None)),
        "has_edge_token": bool(getattr(edge, "edge_token", None)),
        "edge_token_persisted": False,
        "evaluated_at": getattr(edge, "evaluated_at", None),
        "reason": getattr(edge, "reason", None),
    }


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
    return str(value)


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
