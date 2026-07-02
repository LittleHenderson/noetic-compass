"""Paper-only WASTE sample collection coordinator.

The direction/outcome binders prove what happened after WASTE makes a decision.
This module answers the operator question before that proof exists: what is the
next safe paper-only step needed to collect broker-grade LONG/SHORT samples and
bind them to closed paper/demo outcomes?

It is a coordination packet, not trading authority. The status builder is
read-only. The optional run-once helper can run read-only market probes and demo
deal-history ingest, but it never dispatches orders, creates owner/broker
ACCEPT, authorizes live trading, mints edge tokens, or moves money.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEDULER_STATE_PATH = REPO_ROOT / "runtime" / "waste-paper-sample-collector-scheduler.json"
DEFAULT_SCHEDULER_AUDIT_PATH = REPO_ROOT / "runtime" / "waste-paper-sample-collector-scheduler-audit.jsonl"

REPORT_KIND = "cas_forex_waste_paper_sample_collector"
RUN_REPORT_KIND = "cas_forex_waste_paper_sample_collection_run"
SCHEDULER_REPORT_KIND = "cas_forex_waste_paper_sample_collector_scheduler"

STATUS_OUTCOMES_READY = "WASTE_PAPER_SAMPLE_OUTCOMES_READY"
STATUS_NEEDS_BROKER_GRADE_CANDLES = "WASTE_PAPER_SAMPLE_NEEDS_BROKER_GRADE_CANDLES"
STATUS_NEEDS_REAL_CANDLE_PROBE = "WASTE_PAPER_SAMPLE_NEEDS_REAL_CANDLE_PROBE"
STATUS_NEEDS_PASS_TOKEN = "WASTE_PAPER_SAMPLE_NEEDS_PASS_TOKEN"
STATUS_NEEDS_WASTE_RUNNER_CAPTURE = "WASTE_PAPER_SAMPLE_NEEDS_WASTE_RUNNER_CAPTURE"
STATUS_AWAITING_PAPER_EXECUTION = "WASTE_PAPER_SAMPLE_AWAITING_PAPER_EXECUTION"
STATUS_AWAITING_CLOSED_HISTORY = "WASTE_PAPER_SAMPLE_AWAITING_CLOSED_HISTORY"
STATUS_COLLECTING_OUTCOMES = "WASTE_PAPER_SAMPLE_COLLECTING_OUTCOMES"

MIN_SCHEDULER_INTERVAL_SECONDS = 5
DEFAULT_SCHEDULER_INTERVAL_SECONDS = 300
MAX_SCHEDULER_INTERVAL_SECONDS = 86_400
DEFAULT_SCAN_CANDIDATE_LIMIT = 8
MAX_SCAN_CANDIDATE_LIMIT = 32
SCHEDULER_RUNNING = "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING"
SCHEDULER_STOPPED = "WASTE_PAPER_SAMPLE_COLLECTOR_STOPPED"
SCAN_REPORT_KIND = "cas_forex_waste_paper_probe_scan"

CLAIM_BOUNDARY = (
    "WASTE paper sample collector coordinates PAPER/DEMO evidence collection "
    "from broker-grade market-data probes, WASTE PASS-token direction cycles, "
    "paper/demo order attempts, MT5 paper/demo deal-history ingest, and direction "
    "outcome binding. It does not place orders, close positions, create broker "
    "ACCEPT, create owner ACCEPT, authorize live trading, mint edge tokens, "
    "lower thresholds, raise risk, deposit, withdraw, move bank/card money, "
    "automate payouts, or mark evidence LICENSED."
)

SCHEDULER_CLAIM_BOUNDARY = (
    CLAIM_BOUNDARY
    + " The scheduler only repeats those paper/demo evidence collection steps on "
    + "an owner-started timer. Starting the scheduler does not start live trading, "
    + "does not dispatch paper/live orders, and does not change runtime controls."
)


def build_waste_paper_sample_collector(
    *,
    runner: Mapping[str, Any] | None = None,
    mt5_market_data_diagnostic: Mapping[str, Any] | None = None,
    real_candle_probe: Mapping[str, Any] | None = None,
    direction_learning: Mapping[str, Any] | None = None,
    direction_outcome_binding: Mapping[str, Any] | None = None,
    mt5_deal_history_ingest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only owner-visible collection status packet."""

    runner_report = dict(runner) if runner is not None else _runner_status()
    diagnostic = (
        dict(mt5_market_data_diagnostic)
        if mt5_market_data_diagnostic is not None
        else _latest_mt5_market_data_diagnostic()
    )
    probe = (
        dict(real_candle_probe)
        if real_candle_probe is not None
        else _latest_waste_real_candle_probe()
    )
    learning = (
        dict(direction_learning)
        if direction_learning is not None
        else _direction_learning()
    )
    outcome = (
        dict(direction_outcome_binding)
        if direction_outcome_binding is not None
        else _direction_outcome_binding()
    )
    history = (
        dict(mt5_deal_history_ingest)
        if mt5_deal_history_ingest is not None
        else _latest_mt5_deal_history_ingest()
    )

    market_ready = _market_ready(diagnostic, probe)
    probe_recorded = _probe_recorded(probe)
    probe_candidate = _mapping(probe.get("candidate"))
    probe_edge = _mapping(probe.get("edge"))
    probe_has_candidate = bool(probe_candidate)
    probe_edge_pass = _probe_edge_pass(probe)
    runner_paper = str(runner_report.get("mode") or "PAPER").upper() == "PAPER"
    runner_running = bool(runner_report.get("running", False))
    confirmed_count = _int(
        outcome.get("confirmed_direction_count"),
        _int(learning.get("confirmed_direction_count"), 0),
    )
    executed_count = _int(outcome.get("executed_confirmed_count"), 0)
    bound_count = _int(outcome.get("bound_outcome_count"), 0)
    bound_needed = _int(outcome.get("bound_outcomes_needed"), 0)
    outcome_ready = bool(outcome.get("outcome_ready_for_promotion", False))
    closed_history_count = _int(
        outcome.get("closed_history_count"),
        _int(_mapping(history.get("summary")).get("closed_position_count"), len(history.get("history_records") or [])),
    )

    status = _status(
        market_ready=market_ready,
        probe_recorded=probe_recorded,
        probe_has_candidate=probe_has_candidate,
        probe_edge_pass=probe_edge_pass,
        outcome_ready=outcome_ready,
        confirmed_count=confirmed_count,
        executed_count=executed_count,
        bound_count=bound_count,
    )
    checks = _checks(
        runner=runner_report,
        diagnostic=diagnostic,
        probe=probe,
        learning=learning,
        outcome=outcome,
        history=history,
        market_ready=market_ready,
        runner_paper=runner_paper,
        runner_running=runner_running,
        probe_recorded=probe_recorded,
        probe_has_candidate=probe_has_candidate,
        probe_edge_pass=probe_edge_pass,
        confirmed_count=confirmed_count,
        executed_count=executed_count,
        closed_history_count=closed_history_count,
        bound_count=bound_count,
        outcome_ready=outcome_ready,
    )
    actions = _required_actions(
        status=status,
        market_ready=market_ready,
        runner_running=runner_running,
        runner_paper=runner_paper,
        probe_recorded=probe_recorded,
        probe_has_candidate=probe_has_candidate,
        probe_edge_pass=probe_edge_pass,
        confirmed_count=confirmed_count,
        executed_count=executed_count,
        bound_count=bound_count,
        bound_needed=bound_needed,
    )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "read_only": True,
        "dry_run": True,
        "paper_only": True,
        "sample_collection_complete": outcome_ready,
        "paper_runner_running": runner_running,
        "paper_runner_mode": runner_report.get("mode") or "PAPER",
        "market_data_ready": market_ready,
        "mt5_market_data_status": diagnostic.get("status"),
        "mt5_ready_symbol_count": _int(diagnostic.get("ready_symbol_count"), 0),
        "real_candle_probe_status": probe.get("status"),
        "real_candle_probe_broker_grade": bool(probe.get("broker_grade_market_truth", False)),
        "real_candle_probe_fallback_used": bool(probe.get("fallback_used", False)),
        "probe_symbol": probe.get("symbol") or probe_candidate.get("symbol"),
        "probe_timeframe": probe.get("timeframe") or probe_candidate.get("timeframe"),
        "probe_direction": probe_candidate.get("direction"),
        "probe_edge_status": probe_edge.get("status"),
        "probe_edge_pass_unregistered": probe_edge_pass,
        "direction_rows": _int(learning.get("direction_rows"), _int(outcome.get("direction_rows"), 0)),
        "confirmed_direction_count": confirmed_count,
        "confirmed_samples_needed": _int(
            _mapping(learning.get("profile_recommendation")).get("min_confirmed_for_adaptation"),
            5,
        )
        - min(
            _int(
                _mapping(learning.get("profile_recommendation")).get("min_confirmed_for_adaptation"),
                5,
            ),
            confirmed_count,
        ),
        "executed_confirmed_count": executed_count,
        "closed_history_count": closed_history_count,
        "bound_outcome_count": bound_count,
        "bound_outcomes_needed": bound_needed,
        "net_paper_pnl": _float(outcome.get("net_paper_pnl"), 0.0),
        "mt5_deal_history_status": history.get("ingest_status"),
        "mt5_deal_history_account_mode": history.get("account_mode") or _mapping(history.get("query")).get("account_mode"),
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "broker_execution_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "checks": checks,
        "required_actions": actions,
        "source_summaries": {
            "runner": _runner_summary(runner_report),
            "mt5_market_data_diagnostic": _diagnostic_summary(diagnostic),
            "real_candle_probe": _probe_summary(probe),
            "direction_learning": _learning_summary(learning),
            "direction_outcome_binding": _outcome_summary(outcome),
            "mt5_deal_history_ingest": _history_summary(history),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, actions, bound_needed),
    }


def run_waste_paper_sample_collection_once(
    *,
    run_market_diagnostic: bool = True,
    run_real_candle_probe: bool = True,
    run_deal_history_ingest: bool = True,
    symbol: str | None = None,
    timeframe: str | None = None,
    bars: int | None = None,
    max_pairs: int | None = None,
    scan_candidates: bool = True,
    max_scan_candidates: int | None = None,
    market_diagnostic_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
    real_candle_probe_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
    deal_history_ingest_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
    direction_outcome_binding_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """Run one read-only evidence collection pass.

    This is deliberately narrow: it may run read-only market diagnostics,
    read-only real-candle probes, and demo/paper deal-history ingest. It does not
    start WASTE, register edge authorization, dispatch paper/live orders, or
    change runtime controls.
    """

    before = build_waste_paper_sample_collector()
    actions: list[dict[str, Any]] = []
    diagnostic: Mapping[str, Any] | None = None
    probe: Mapping[str, Any] | None = None
    probe_scan: Mapping[str, Any] | None = None
    history: Mapping[str, Any] | None = None
    outcome: Mapping[str, Any] | None = None

    if run_market_diagnostic:
        fn = market_diagnostic_fn or _run_mt5_market_data_diagnostic
        diagnostic = fn(
            symbols=[symbol] if symbol else None,
            timeframe=timeframe,
            bars=bars,
        )
        actions.append({"action_id": "mt5_market_data_diagnostic", "status": diagnostic.get("status")})

    if run_real_candle_probe:
        fn = real_candle_probe_fn or _run_waste_real_candle_probe
        if scan_candidates and symbol is None:
            probe_scan = _run_waste_real_candle_probe_scan(
                real_candle_probe_fn=fn,
                requested_timeframe=timeframe,
                bars=bars,
                max_pairs=max_pairs,
                max_scan_candidates=max_scan_candidates,
            )
            probe = _mapping(probe_scan.get("selected_probe"))
            actions.append(
                {
                    "action_id": "waste_real_candle_probe_scan",
                    "status": probe_scan.get("status"),
                    "attempt_count": probe_scan.get("attempt_count"),
                    "selected_symbol": probe_scan.get("selected_symbol"),
                    "selected_timeframe": probe_scan.get("selected_timeframe"),
                    "edge_status": _mapping(probe.get("edge")).get("status"),
                }
            )
        else:
            probe = fn(
                symbol=symbol,
                timeframe=timeframe,
                bars=bars,
                max_pairs=max_pairs,
            )
            actions.append({"action_id": "waste_real_candle_probe", "status": probe.get("status")})

    if run_deal_history_ingest:
        fn = deal_history_ingest_fn or _run_mt5_deal_history_ingest
        history = fn(symbol=symbol)
        actions.append({"action_id": "mt5_demo_deal_history_ingest", "status": history.get("ingest_status")})
        outcome_fn = direction_outcome_binding_fn or _run_waste_direction_outcome_binding
        outcome = outcome_fn(history_report=history)
        actions.append({"action_id": "waste_direction_outcome_binding", "status": outcome.get("status")})

    after = build_waste_paper_sample_collector(
        mt5_market_data_diagnostic=diagnostic,
        real_candle_probe=probe,
        direction_outcome_binding=outcome,
        mt5_deal_history_ingest=history,
    )
    return {
        "report_kind": RUN_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": after.get("status"),
        "paper_only": True,
        "read_only_market_actions_only": True,
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "broker_touched": False,
        "broker_execution_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "actions": actions,
        "scan_candidates_enabled": bool(scan_candidates and symbol is None),
        "probe_scan": probe_scan,
        "before": before,
        "after": after,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": after.get("next_action"),
    }


class WastePaperSampleCollectorScheduler:
    """Owner-started background loop for paper-only sample collection."""

    def __init__(
        self,
        *,
        run_once_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
        state_path: Path | str = DEFAULT_SCHEDULER_STATE_PATH,
        audit_path: Path | str = DEFAULT_SCHEDULER_AUDIT_PATH,
    ) -> None:
        self._run_once_fn = run_once_fn or run_waste_paper_sample_collection_once
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.interval_seconds = DEFAULT_SCHEDULER_INTERVAL_SECONDS
        self.cycles_run = 0
        self.started_at_iso = ""
        self.last_run_iso = ""
        self.last_error = ""
        self.latest_run: Optional[dict[str, Any]] = None
        self.run_market_diagnostic = True
        self.run_real_candle_probe = True
        self.run_deal_history_ingest = True
        self.symbol: Optional[str] = None
        self.timeframe: Optional[str] = None
        self.bars: Optional[int] = None
        self.max_pairs: Optional[int] = None
        self.scan_candidates = True
        self.max_scan_candidates = DEFAULT_SCAN_CANDIDATE_LIMIT

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status_locked(load_from_disk=False)

    def start(
        self,
        *,
        interval_seconds: int = DEFAULT_SCHEDULER_INTERVAL_SECONDS,
        run_market_diagnostic: bool = True,
        run_real_candle_probe: bool = True,
        run_deal_history_ingest: bool = True,
        symbol: str | None = None,
        timeframe: str | None = None,
        bars: int | None = None,
        max_pairs: int | None = None,
        scan_candidates: bool = True,
        max_scan_candidates: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self.interval_seconds = _clamp_scheduler_interval(interval_seconds)
            self.run_market_diagnostic = bool(run_market_diagnostic)
            self.run_real_candle_probe = bool(run_real_candle_probe)
            self.run_deal_history_ingest = bool(run_deal_history_ingest)
            self.symbol = _optional_text(symbol)
            self.timeframe = _optional_text(timeframe)
            self.bars = _optional_int(bars)
            self.max_pairs = _optional_int(max_pairs)
            self.scan_candidates = bool(scan_candidates)
            self.max_scan_candidates = _clamp_scan_candidate_limit(max_scan_candidates)
            if self._is_running_locked():
                status = self._status_locked(load_from_disk=False)
                self._write_state(status)
                self._audit("SCHEDULER_ALREADY_RUNNING", status)
                return status
            self._stop_event.clear()
            self.started_at_iso = utc_now().isoformat()
            self.last_error = ""
            self._thread = threading.Thread(
                target=self._run,
                name="cas-waste-paper-sample-collector",
                daemon=True,
            )
            self._thread.start()
            status = self._status_locked(load_from_disk=False)
            self._write_state(status)
            self._audit("SCHEDULER_STARTED", status)
            return status

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3.0)
        with self._lock:
            if thread and not thread.is_alive():
                self._thread = None
            status = self._status_locked(load_from_disk=False)
            self._write_state(status)
            self._audit("SCHEDULER_STOPPED", status)
            return status

    def run_once(
        self,
        *,
        run_market_diagnostic: bool | None = None,
        run_real_candle_probe: bool | None = None,
        run_deal_history_ingest: bool | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        bars: int | None = None,
        max_pairs: int | None = None,
        scan_candidates: bool | None = None,
        max_scan_candidates: int | None = None,
    ) -> dict[str, Any]:
        params = self._params(
            run_market_diagnostic=run_market_diagnostic,
            run_real_candle_probe=run_real_candle_probe,
            run_deal_history_ingest=run_deal_history_ingest,
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
            max_pairs=max_pairs,
            scan_candidates=scan_candidates,
            max_scan_candidates=max_scan_candidates,
        )
        try:
            run = dict(self._run_once_fn(**params))
            with self._lock:
                self.cycles_run += 1
                self.latest_run = run
                self.last_run_iso = utc_now().isoformat()
                self.last_error = ""
                status = self._status_locked(load_from_disk=False)
                self._write_state(status)
                self._audit("SCHEDULER_RUN_ONCE", status)
                return status
        except Exception as exc:
            with self._lock:
                self.last_error = f"{type(exc).__name__}: {exc}"
                self.last_run_iso = utc_now().isoformat()
                status = self._status_locked(load_from_disk=False)
                self._write_state(status)
                self._audit("SCHEDULER_RUN_ERROR", status)
                return status

    def _run(self) -> None:
        if self._stop_event.wait(
            min(max(MIN_SCHEDULER_INTERVAL_SECONDS, self.interval_seconds), 60.0)
        ):
            with self._lock:
                status = self._status_locked(load_from_disk=False)
                self._write_state(status)
                self._audit("SCHEDULER_THREAD_EXITED", status)
            return
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(max(MIN_SCHEDULER_INTERVAL_SECONDS, self.interval_seconds))
        with self._lock:
            status = self._status_locked(load_from_disk=False)
            self._write_state(status)
            self._audit("SCHEDULER_THREAD_EXITED", status)

    def _params(
        self,
        *,
        run_market_diagnostic: bool | None,
        run_real_candle_probe: bool | None,
        run_deal_history_ingest: bool | None,
        symbol: str | None,
        timeframe: str | None,
        bars: int | None,
        max_pairs: int | None,
        scan_candidates: bool | None,
        max_scan_candidates: int | None,
    ) -> dict[str, Any]:
        with self._lock:
            return {
                "run_market_diagnostic": self.run_market_diagnostic
                if run_market_diagnostic is None
                else bool(run_market_diagnostic),
                "run_real_candle_probe": self.run_real_candle_probe
                if run_real_candle_probe is None
                else bool(run_real_candle_probe),
                "run_deal_history_ingest": self.run_deal_history_ingest
                if run_deal_history_ingest is None
                else bool(run_deal_history_ingest),
                "symbol": _optional_text(symbol) if symbol is not None else self.symbol,
                "timeframe": _optional_text(timeframe) if timeframe is not None else self.timeframe,
                "bars": _optional_int(bars) if bars is not None else self.bars,
                "max_pairs": _optional_int(max_pairs) if max_pairs is not None else self.max_pairs,
                "scan_candidates": self.scan_candidates
                if scan_candidates is None
                else bool(scan_candidates),
                "max_scan_candidates": _clamp_scan_candidate_limit(max_scan_candidates)
                if max_scan_candidates is not None
                else self.max_scan_candidates,
            }

    def _status_locked(self, *, load_from_disk: bool) -> dict[str, Any]:
        running = self._is_running_locked()
        disk = self._load_state() if load_from_disk else {}
        latest_run = self.latest_run or _mapping(disk.get("latest_run")) or None
        latest_after = _mapping(latest_run.get("after")) if latest_run else {}
        return {
            "report_kind": SCHEDULER_REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "running": running,
            "status": SCHEDULER_RUNNING if running else SCHEDULER_STOPPED,
            "interval_seconds": self.interval_seconds,
            "cycles_run": self.cycles_run or _int(disk.get("cycles_run"), 0),
            "started_at_iso": self.started_at_iso or disk.get("started_at_iso"),
            "last_run_iso": self.last_run_iso or disk.get("last_run_iso"),
            "last_error": self.last_error or disk.get("last_error") or None,
            "latest_run": latest_run,
            "latest_collector_status": latest_after.get("status"),
            "sample_collection_complete": bool(latest_after.get("sample_collection_complete", False)),
            "market_data_ready": bool(latest_after.get("market_data_ready", False)),
            "confirmed_direction_count": _int(latest_after.get("confirmed_direction_count"), 0),
            "bound_outcome_count": _int(latest_after.get("bound_outcome_count"), 0),
            "bound_outcomes_needed": _int(latest_after.get("bound_outcomes_needed"), 0),
            "config": {
                "run_market_diagnostic": bool(self.run_market_diagnostic),
                "run_real_candle_probe": bool(self.run_real_candle_probe),
                "run_deal_history_ingest": bool(self.run_deal_history_ingest),
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "bars": self.bars,
                "max_pairs": self.max_pairs,
                "scan_candidates": bool(self.scan_candidates),
                "max_scan_candidates": self.max_scan_candidates,
            },
            "paper_only": True,
            "read_only_market_actions_only": True,
            "runtime_changed": False,
            "runtime_change_attempted": False,
            "would_apply_runtime_change": False,
            "would_lower_edge_threshold": False,
            "would_enable_live_trading": False,
            "would_raise_risk": False,
            "broker_touched": False,
            "broker_execution_touched": False,
            "live_order_attempted": False,
            "attempt_finalized": False,
            "edge_token_minted": False,
            "owner_accept_created": False,
            "money_moved": False,
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "claim_boundary": SCHEDULER_CLAIM_BOUNDARY,
            "next_action": _scheduler_next_action(running, latest_after, self.last_error or ""),
        }

    def _is_running_locked(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return dict(payload) if isinstance(payload, Mapping) else {}

    def _write_state(self, payload: Mapping[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)

    def _audit(self, action: str, payload: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "audit_id": stable_ledger_id(
                "waste-paper-sample-collector-scheduler",
                action,
                utc_now().isoformat(),
                str(payload.get("status") or ""),
                str(payload.get("latest_collector_status") or ""),
            ),
            "action": action,
            "timestamp": utc_now().isoformat(),
            "status": payload.get("status"),
            "latest_collector_status": payload.get("latest_collector_status"),
            "payload": dict(payload),
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


_scheduler: Optional[WastePaperSampleCollectorScheduler] = None
_scheduler_lock = threading.Lock()


def get_waste_paper_sample_collector_scheduler() -> WastePaperSampleCollectorScheduler:
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = WastePaperSampleCollectorScheduler()
        return _scheduler


def set_waste_paper_sample_collector_scheduler(
    scheduler: WastePaperSampleCollectorScheduler | None,
) -> None:
    global _scheduler
    with _scheduler_lock:
        _scheduler = scheduler


def waste_paper_sample_collector_scheduler_status() -> dict[str, Any]:
    status = get_waste_paper_sample_collector_scheduler().status()
    try:
        import os

        if not os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get(
            "CAS_FOREX_BACKGROUND_WORKER"
        ):
            from cas_forex.waste_background_worker import overlay_paper_sample_collector_status

            return overlay_paper_sample_collector_status(status)
    except Exception:
        pass
    return status


def start_waste_paper_sample_collector_scheduler(
    *,
    interval_seconds: int = DEFAULT_SCHEDULER_INTERVAL_SECONDS,
    run_market_diagnostic: bool = True,
    run_real_candle_probe: bool = True,
    run_deal_history_ingest: bool = True,
    symbol: str | None = None,
    timeframe: str | None = None,
    bars: int | None = None,
    max_pairs: int | None = None,
    scan_candidates: bool = True,
    max_scan_candidates: int | None = None,
) -> dict[str, Any]:
    return get_waste_paper_sample_collector_scheduler().start(
        interval_seconds=interval_seconds,
        run_market_diagnostic=run_market_diagnostic,
        run_real_candle_probe=run_real_candle_probe,
        run_deal_history_ingest=run_deal_history_ingest,
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        max_pairs=max_pairs,
        scan_candidates=scan_candidates,
        max_scan_candidates=max_scan_candidates,
    )


def stop_waste_paper_sample_collector_scheduler() -> dict[str, Any]:
    return get_waste_paper_sample_collector_scheduler().stop()


def run_waste_paper_sample_collector_scheduler_once(
    *,
    run_market_diagnostic: bool | None = None,
    run_real_candle_probe: bool | None = None,
    run_deal_history_ingest: bool | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    bars: int | None = None,
    max_pairs: int | None = None,
    scan_candidates: bool | None = None,
    max_scan_candidates: int | None = None,
) -> dict[str, Any]:
    return get_waste_paper_sample_collector_scheduler().run_once(
        run_market_diagnostic=run_market_diagnostic,
        run_real_candle_probe=run_real_candle_probe,
        run_deal_history_ingest=run_deal_history_ingest,
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        max_pairs=max_pairs,
        scan_candidates=scan_candidates,
        max_scan_candidates=max_scan_candidates,
    )


def _status(
    *,
    market_ready: bool,
    probe_recorded: bool,
    probe_has_candidate: bool,
    probe_edge_pass: bool,
    outcome_ready: bool,
    confirmed_count: int,
    executed_count: int,
    bound_count: int,
) -> str:
    if outcome_ready:
        return STATUS_OUTCOMES_READY
    if confirmed_count > 0 and executed_count <= 0:
        return STATUS_AWAITING_PAPER_EXECUTION
    if executed_count > 0 and bound_count <= 0:
        return STATUS_AWAITING_CLOSED_HISTORY
    if bound_count > 0:
        return STATUS_COLLECTING_OUTCOMES
    if probe_edge_pass and confirmed_count <= 0:
        return STATUS_NEEDS_WASTE_RUNNER_CAPTURE
    if not market_ready:
        return STATUS_NEEDS_BROKER_GRADE_CANDLES
    if not probe_recorded or not probe_has_candidate:
        return STATUS_NEEDS_REAL_CANDLE_PROBE
    return STATUS_NEEDS_PASS_TOKEN


def _checks(**kwargs: Any) -> list[dict[str, Any]]:
    runner = kwargs["runner"]
    diagnostic = kwargs["diagnostic"]
    probe = kwargs["probe"]
    history = kwargs["history"]
    outcome = kwargs["outcome"]
    return [
        _check(
            "paper_mode_only",
            bool(kwargs["runner_paper"]),
            "WASTE runner is in PAPER mode.",
            {"mode": runner.get("mode")},
        ),
        _check(
            "paper_runner_running",
            bool(kwargs["runner_running"]),
            "Timed WASTE runner is collecting PAPER cycles.",
            {"running": runner.get("running"), "cycles_run": runner.get("cycles_run")},
        ),
        _check(
            "broker_grade_market_data",
            bool(kwargs["market_ready"]),
            "Broker-grade candles or a broker-grade WASTE probe are available.",
            {
                "diagnostic_status": diagnostic.get("status"),
                "ready_symbol_count": diagnostic.get("ready_symbol_count"),
                "probe_broker_grade": probe.get("broker_grade_market_truth"),
                "probe_fallback_used": probe.get("fallback_used"),
            },
        ),
        _check(
            "real_candle_probe_candidate",
            bool(kwargs["probe_recorded"] and kwargs["probe_has_candidate"]),
            "Latest WASTE real-candle probe contains a LONG/SHORT candidate.",
            {
                "probe_status": probe.get("status"),
                "symbol": probe.get("symbol"),
                "timeframe": probe.get("timeframe"),
                "candidate": _candidate_brief(_mapping(probe.get("candidate"))),
            },
        ),
        _check(
            "probe_edge_pass_observed",
            bool(kwargs["probe_edge_pass"]),
            "A read-only real-candle probe has observed an unregistered edge PASS.",
            {"edge": _mapping(probe.get("edge")), "probe_status": probe.get("status")},
            informational=True,
        ),
        _check(
            "confirmed_pass_direction_samples",
            int(kwargs["confirmed_count"]) > 0,
            "WASTE cycle audit contains PASS-token LONG/SHORT samples.",
            {"confirmed_direction_count": kwargs["confirmed_count"]},
        ),
        _check(
            "paper_execution_attempts",
            int(kwargs["executed_count"]) > 0,
            "Confirmed WASTE samples have matching executed paper/demo attempts.",
            {"executed_confirmed_count": kwargs["executed_count"]},
        ),
        _check(
            "closed_mt5_paper_history",
            int(kwargs["closed_history_count"]) > 0,
            "MT5 paper/demo closed deal history is available.",
            {
                "closed_history_count": kwargs["closed_history_count"],
                "ingest_status": history.get("ingest_status"),
            },
        ),
        _check(
            "bound_paper_outcomes",
            int(kwargs["bound_count"]) > 0,
            "Closed MT5 paper/demo outcomes are bound to WASTE PASS-token samples.",
            {
                "bound_outcome_count": kwargs["bound_count"],
                "bound_outcomes_needed": outcome.get("bound_outcomes_needed"),
                "net_paper_pnl": outcome.get("net_paper_pnl"),
            },
        ),
        _check(
            "outcome_ready_for_promotion",
            bool(kwargs["outcome_ready"]),
            "Bound paper/demo outcomes are sufficient for promotion review.",
            {
                "outcome_ready_for_promotion": outcome.get("outcome_ready_for_promotion"),
                "min_bound_outcomes_for_promotion": outcome.get("min_bound_outcomes_for_promotion"),
            },
        ),
    ]


def _required_actions(
    *,
    status: str,
    market_ready: bool,
    runner_running: bool,
    runner_paper: bool,
    probe_recorded: bool,
    probe_has_candidate: bool,
    probe_edge_pass: bool,
    confirmed_count: int,
    executed_count: int,
    bound_count: int,
    bound_needed: int,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not market_ready:
        actions.append(
            _action(
                "run_mt5_market_data_diagnostic",
                "Run MT5 broker-grade market-data diagnostic.",
                route="POST /api/forex/waste-loop-control/mt5-market-data-diagnostic/run",
            )
        )
    if market_ready and (not probe_recorded or not probe_has_candidate):
        actions.append(
            _action(
                "run_waste_real_candle_probe",
                "Run a WASTE real-candle probe for a LONG/SHORT candidate.",
                route="POST /api/forex/waste-loop-control/real-candle-probe/run",
            )
        )
    if market_ready and probe_recorded and probe_has_candidate and not probe_edge_pass and confirmed_count <= 0:
        actions.append(
            _action(
                "keep_probing_for_pass_token",
                "Keep collecting real-candle probes until the edge gate returns PASS.",
                route="POST /api/forex/waste-loop-control/real-candle-probe/run",
            )
        )
    if not runner_running or not runner_paper:
        actions.append(
            _action(
                "keep_waste_runner_paper",
                "Keep the timed WASTE runner active in PAPER mode.",
                route="POST /api/forex/waste-loop-control/start",
            )
        )
    if probe_edge_pass and confirmed_count <= 0:
        actions.append(
            _action(
                "capture_pass_in_waste_audit",
                "Let the PAPER WASTE runner capture PASS-token direction cycles in the durable audit.",
                route="POST /api/forex/waste-loop-control/start",
            )
        )
    if confirmed_count > 0 and executed_count <= 0:
        actions.append(
            _action(
                "finalize_paper_execution_attempt",
                "Match each PASS-token direction to a finalized paper/demo order attempt.",
                route="GET /api/forex/waste-loop-control/direction-outcome-binding",
            )
        )
    if executed_count > 0 and bound_count <= 0:
        actions.append(
            _action(
                "run_mt5_demo_deal_history_ingest",
                "After the paper/demo position closes, ingest MT5 demo deal history.",
                route="GET /api/forex/strategy/mt5-deal-history-ingest/latest",
                command="python scripts/run_mt5_deal_history_ingest.py --summary-only",
            )
        )
    if bound_count > 0 and bound_needed > 0:
        actions.append(
            _action(
                "collect_more_bound_outcomes",
                f"Collect {bound_needed} more bound paper/demo outcome(s).",
                route="GET /api/forex/waste-loop-control/paper-sample-collector",
            )
        )
    if status == STATUS_OUTCOMES_READY:
        actions.append(
            _action(
                "owner_review_adaptation",
                "Bound outcomes are ready; keep live authority separate and move only to owner review.",
                route="GET /api/forex/waste-loop-control/adaptation-promotion-rule",
                requires_owner_review=True,
            )
        )
    return actions


def _next_action(status: str, actions: list[dict[str, Any]], bound_needed: int) -> str:
    if actions:
        return str(actions[0].get("detail") or actions[0].get("action_id"))
    if status == STATUS_OUTCOMES_READY:
        return "Bound paper/demo direction outcomes are ready for owner review; live authority remains separate."
    if status == STATUS_COLLECTING_OUTCOMES:
        return f"Collect {bound_needed} more bound paper/demo outcome(s)."
    return "Continue PAPER evidence collection until WASTE has broker-grade PASS-token samples and closed outcomes."


def _market_ready(diagnostic: Mapping[str, Any], probe: Mapping[str, Any]) -> bool:
    diagnostic_ready = (
        str(diagnostic.get("status") or "") == "MT5_MARKET_DATA_READY"
        and _int(diagnostic.get("ready_symbol_count"), 0) > 0
    )
    probe_ready = bool(probe.get("broker_grade_market_truth", False)) and not bool(probe.get("fallback_used", False))
    return diagnostic_ready or probe_ready


def _probe_recorded(probe: Mapping[str, Any]) -> bool:
    return str(probe.get("report_kind") or "") == "cas_forex_waste_real_candle_probe" and str(probe.get("status") or "") != "NO_PROBE_RECORDED"


def _probe_edge_pass(probe: Mapping[str, Any]) -> bool:
    edge = _mapping(probe.get("edge"))
    return str(probe.get("status") or "") == "EDGE_PASS_UNREGISTERED" or (
        str(edge.get("status") or "") == "PASS" and bool(edge.get("has_edge_token", False))
    )


def _check(
    check_id: str,
    passed: bool,
    detail: str,
    evidence: Mapping[str, Any],
    *,
    informational: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "PASS" if passed else ("INFO" if informational else "BLOCKED"),
        "passed": bool(passed),
        "detail": detail,
        "evidence": dict(evidence),
    }


def _action(
    action_id: str,
    detail: str,
    *,
    route: str,
    command: str | None = None,
    requires_owner_review: bool = False,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "detail": detail,
        "route": route,
        "command": command,
        "requires_owner_review": bool(requires_owner_review),
        "can_touch_broker_execution": False,
        "can_authorize_live_trading": False,
        "can_create_owner_accept": False,
        "can_create_broker_accept": False,
        "can_move_money": False,
    }


def _runner_status() -> dict[str, Any]:
    try:
        from cas_forex.waste_runner import runner_status

        return _overlay_external_waste_runner_status(runner_status())
    except Exception as exc:
        return _unavailable("cas_forex_waste_runner", exc)


def _overlay_external_waste_runner_status(status: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(status)
    if packet.get("running"):
        return packet
    worker = _external_waste_runner_worker_status()
    if not worker.get("running"):
        return packet
    config = _mapping(worker.get("config"))
    packet["running"] = True
    packet["status"] = "RUNNING"
    packet["mode"] = packet.get("mode") or "PAPER"
    packet["external_worker"] = worker
    packet["worker_isolated"] = True
    if _int(packet.get("interval_seconds"), 0) <= 0:
        packet["interval_seconds"] = _int(config.get("interval_seconds"), 0) or packet.get("interval_seconds")
    if not packet.get("started_at_iso") and worker.get("started_at"):
        packet["started_at_iso"] = worker.get("started_at")
    return packet


def _external_waste_runner_worker_status() -> dict[str, Any]:
    try:
        from cas_forex.waste_background_worker import RUNNER_KIND, worker_status

        return dict(worker_status(RUNNER_KIND))
    except Exception:
        return {}


def _latest_mt5_market_data_diagnostic() -> dict[str, Any]:
    try:
        from cas_forex.mt5_market_data_diagnostic import latest_mt5_market_data_diagnostic

        return latest_mt5_market_data_diagnostic()
    except Exception as exc:
        return _unavailable("cas_forex_mt5_market_data_diagnostic", exc)


def _latest_waste_real_candle_probe() -> dict[str, Any]:
    try:
        from cas_forex.waste_real_candle_probe import latest_waste_real_candle_probe

        return latest_waste_real_candle_probe()
    except Exception as exc:
        return _unavailable("cas_forex_waste_real_candle_probe", exc)


def _direction_learning() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger

        return build_waste_direction_learning_ledger()
    except Exception as exc:
        return _unavailable("cas_forex_waste_direction_learning_ledger", exc)


def _direction_outcome_binding() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_outcome_binding import build_waste_direction_outcome_binding

        return build_waste_direction_outcome_binding()
    except Exception as exc:
        return _unavailable("cas_forex_waste_direction_outcome_binding", exc)


def _latest_mt5_deal_history_ingest() -> dict[str, Any]:
    try:
        from cas_forex.mt5_deal_history_ingest import load_latest_mt5_deal_history_ingest_report

        return load_latest_mt5_deal_history_ingest_report()
    except Exception as exc:
        return _unavailable("cas_forex_mt5_deal_history_ingest_report", exc)


def _run_waste_real_candle_probe_scan(
    *,
    real_candle_probe_fn: Callable[..., Mapping[str, Any]],
    requested_timeframe: str | None,
    bars: int | None,
    max_pairs: int | None,
    max_scan_candidates: int | None,
) -> dict[str, Any]:
    candidates = _waste_probe_scan_candidates(
        requested_timeframe=requested_timeframe,
        max_scan_candidates=max_scan_candidates,
    )
    attempts: list[dict[str, Any]] = []
    selected_probe: dict[str, Any] | None = None
    selected_candidate: dict[str, Any] | None = None

    for candidate in candidates:
        try:
            probe = dict(
                real_candle_probe_fn(
                    symbol=candidate["symbol"],
                    timeframe=candidate["timeframe"],
                    bars=bars,
                    max_pairs=max_pairs,
                )
            )
        except Exception as exc:
            probe = {
                "report_kind": "cas_forex_waste_real_candle_probe",
                "status": "PROBE_ERROR",
                "symbol": candidate["symbol"],
                "timeframe": candidate["timeframe"],
                "broker_touched": False,
                "broker_execution_touched": False,
                "money_moved": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        attempts.append(_probe_scan_attempt(candidate, probe))
        if selected_probe is None or _probe_scan_score(probe) > _probe_scan_score(selected_probe):
            selected_probe = probe
            selected_candidate = candidate
        if _probe_edge_pass(probe):
            selected_probe = probe
            selected_candidate = candidate
            break

    status = "WASTE_PROBE_SCAN_NO_CANDIDATES"
    if attempts:
        status = (
            "WASTE_PROBE_SCAN_PASS_FOUND"
            if selected_probe is not None and _probe_edge_pass(selected_probe)
            else "WASTE_PROBE_SCAN_NO_PASS"
        )
    selected_probe = selected_probe or {}
    selected_candidate = selected_candidate or {}
    selected_edge = _mapping(selected_probe.get("edge"))
    return {
        "report_kind": SCAN_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "paper_only": True,
        "read_only_market_actions_only": True,
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "broker_touched": False,
        "broker_execution_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "edge_authorization_registered": False,
        "owner_accept_created": False,
        "money_moved": False,
        "candidate_source": "strategy_leads ACTIVE_RESEARCH_LEAD symbols/timeframes",
        "attempt_count": len(attempts),
        "attempts": attempts,
        "selected_symbol": selected_probe.get("symbol") or selected_candidate.get("symbol"),
        "selected_timeframe": selected_probe.get("timeframe") or selected_candidate.get("timeframe"),
        "selected_edge_status": selected_edge.get("status"),
        "selected_edge_has_token": bool(selected_edge.get("has_edge_token", False)),
        "selected_probe": selected_probe,
        "claim_boundary": (
            "WASTE probe scan only runs read-only real-candle probes over "
            "strategy-ledger-eligible paper lanes. It does not register edge "
            "authorization, dispatch orders, create broker ACCEPT, create owner "
            "ACCEPT, authorize live trading, deposit, withdraw, move bank/card "
            "money, automate payouts, or mark evidence LICENSED."
        ),
        "next_action": (
            "Let the PAPER WASTE runner capture the PASS-token cycle."
            if status == "WASTE_PROBE_SCAN_PASS_FOUND"
            else "Continue scanning eligible paper lanes until a broker-grade probe earns PASS."
        ),
    }


def _waste_probe_scan_candidates(
    *,
    requested_timeframe: str | None,
    max_scan_candidates: int | None,
) -> list[dict[str, Any]]:
    limit = _clamp_scan_candidate_limit(max_scan_candidates)
    requested_tf = _optional_text(requested_timeframe)
    candidates: list[dict[str, Any]] = []
    try:
        from cas_forex.strategy_ledger import LEDGER_PATH, load_strategy_lead_ledger

        ledger = load_strategy_lead_ledger(LEDGER_PATH)
        leads = [lead for lead in ledger.get("leads", []) if isinstance(lead, Mapping)]
        leads = sorted(leads, key=lambda lead: (_int(lead.get("priority"), 999), str(lead.get("lead_id") or "")))
        for lead in leads:
            if str(lead.get("status") or "") != "ACTIVE_RESEARCH_LEAD":
                continue
            if str(lead.get("deployment_status") or "") != "NOT LICENSED":
                continue
            for sym in _strings(lead.get("symbols_promoted_for_next_tests")):
                timeframes = [requested_tf] if requested_tf else list(
                    _strings(_mapping(lead.get("condition_fit")).get("preferred_timeframes"))
                )
                for tf in timeframes:
                    if not sym or not tf:
                        continue
                    candidates.append(
                        {
                            "symbol": sym,
                            "timeframe": _norm_tf(tf),
                            "lead_id": lead.get("lead_id"),
                            "priority": lead.get("priority"),
                            "source": "strategy_leads",
                        }
                    )
    except Exception:
        candidates = []

    if not candidates:
        try:
            from cas_forex.ai_control_authority import get_authority
            from cas_forex.waste_market_data import DEFAULT_WASTE_TIMEFRAME

            control_symbols = get_authority().control.get("symbols") or []
            for sym in control_symbols:
                if sym:
                    candidates.append(
                        {
                            "symbol": str(sym),
                            "timeframe": _norm_tf(requested_tf or DEFAULT_WASTE_TIMEFRAME),
                            "lead_id": None,
                            "priority": 999,
                            "source": "ai_control_symbols",
                        }
                    )
        except Exception:
            candidates = []

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (str(candidate.get("symbol") or ""), str(candidate.get("timeframe") or ""))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
        if len(deduped) >= limit:
            break
    return deduped


def _probe_scan_attempt(candidate: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
    edge = _mapping(probe.get("edge"))
    probe_candidate = _mapping(probe.get("candidate"))
    return {
        "symbol": probe.get("symbol") or candidate.get("symbol"),
        "timeframe": probe.get("timeframe") or candidate.get("timeframe"),
        "lead_id": candidate.get("lead_id"),
        "source": candidate.get("source"),
        "status": probe.get("status"),
        "edge_status": edge.get("status"),
        "edge_has_token": bool(edge.get("has_edge_token", False)),
        "measured_win_prob": edge.get("measured_win_prob"),
        "null_p95": edge.get("null_p95"),
        "broker_grade_market_truth": bool(probe.get("broker_grade_market_truth", False)),
        "fallback_used": bool(probe.get("fallback_used", False)),
        "candles_count": probe.get("candles_count"),
        "entry_pair_count": probe.get("entry_pair_count"),
        "candidate_direction": probe_candidate.get("direction"),
        "broker_touched": bool(probe.get("broker_touched", False)),
        "money_moved": bool(probe.get("money_moved", False)),
        "error": probe.get("error"),
    }


def _probe_scan_score(probe: Mapping[str, Any]) -> tuple[int, int, int, float, float]:
    edge = _mapping(probe.get("edge"))
    return (
        1 if _probe_edge_pass(probe) else 0,
        1 if bool(probe.get("broker_grade_market_truth", False)) and not bool(probe.get("fallback_used", False)) else 0,
        1 if bool(_mapping(probe.get("candidate"))) else 0,
        _float(edge.get("measured_win_prob"), 0.0),
        _float(probe.get("entry_pair_count"), 0.0),
    )


def _run_mt5_market_data_diagnostic(**kwargs: Any) -> Mapping[str, Any]:
    from cas_forex.mt5_market_data_diagnostic import run_mt5_market_data_diagnostic
    from cas_forex.waste_market_data import DEFAULT_WASTE_BARS, DEFAULT_WASTE_TIMEFRAME

    symbols = kwargs.get("symbols")
    timeframe = kwargs.get("timeframe") or DEFAULT_WASTE_TIMEFRAME
    bars = kwargs.get("bars") or DEFAULT_WASTE_BARS
    return run_mt5_market_data_diagnostic(symbols=symbols, timeframe=timeframe, bars=bars)


def _run_waste_real_candle_probe(**kwargs: Any) -> Mapping[str, Any]:
    from cas_forex.waste_market_data import DEFAULT_MAX_ENTRY_PAIRS, DEFAULT_WASTE_BARS, DEFAULT_WASTE_TIMEFRAME
    from cas_forex.waste_real_candle_probe import run_waste_real_candle_probe

    return run_waste_real_candle_probe(
        symbol=kwargs.get("symbol"),
        timeframe=kwargs.get("timeframe") or DEFAULT_WASTE_TIMEFRAME,
        bars=kwargs.get("bars") or DEFAULT_WASTE_BARS,
        max_pairs=kwargs.get("max_pairs") or DEFAULT_MAX_ENTRY_PAIRS,
    )


def _run_mt5_deal_history_ingest(**kwargs: Any) -> Mapping[str, Any]:
    from cas_forex.mt5_deal_history_ingest import build_mt5_deal_history_ingest_report

    return build_mt5_deal_history_ingest_report(
        symbol=kwargs.get("symbol"),
        account_mode="demo",
        confirm_live_history=False,
    )


def _run_waste_direction_outcome_binding(**kwargs: Any) -> Mapping[str, Any]:
    from cas_forex.waste_direction_outcome_binding import build_waste_direction_outcome_binding

    return build_waste_direction_outcome_binding(
        history_report=kwargs.get("history_report"),
    )


def _runner_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "running": bool(report.get("running", False)),
        "mode": report.get("mode"),
        "cycles_run": report.get("cycles_run"),
        "current_stage": report.get("current_stage"),
        "last_decision": report.get("last_decision"),
        "last_reason": report.get("last_reason"),
    }


def _diagnostic_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "ready_symbol_count": report.get("ready_symbol_count"),
        "checked_symbol_count": report.get("checked_symbol_count"),
        "broker_touched": bool(report.get("broker_touched", False)),
        "next_action": report.get("next_action"),
    }


def _probe_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(report.get("candidate"))
    edge = _mapping(report.get("edge"))
    return {
        "status": report.get("status"),
        "symbol": report.get("symbol") or candidate.get("symbol"),
        "timeframe": report.get("timeframe") or candidate.get("timeframe"),
        "direction": candidate.get("direction"),
        "broker_grade_market_truth": bool(report.get("broker_grade_market_truth", False)),
        "fallback_used": bool(report.get("fallback_used", False)),
        "edge_status": edge.get("status"),
        "edge_has_token": bool(edge.get("has_edge_token", False)),
        "broker_touched": bool(report.get("broker_touched", False)),
        "next_action": report.get("next_action"),
    }


def _learning_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _mapping(report.get("profile_recommendation"))
    return {
        "status": report.get("status"),
        "direction_rows": report.get("direction_rows"),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "blocked_direction_count": report.get("blocked_direction_count"),
        "learning_ready_for_adaptation": bool(report.get("learning_ready_for_adaptation", False)),
        "profile_recommendation_status": recommendation.get("status"),
        "next_action": report.get("next_action"),
    }


def _outcome_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "outcome_ready_for_promotion": bool(report.get("outcome_ready_for_promotion", False)),
        "confirmed_direction_count": report.get("confirmed_direction_count"),
        "executed_confirmed_count": report.get("executed_confirmed_count"),
        "bound_outcome_count": report.get("bound_outcome_count"),
        "bound_outcomes_needed": report.get("bound_outcomes_needed"),
        "net_paper_pnl": report.get("net_paper_pnl"),
        "money_moved": bool(report.get("money_moved", False)),
        "next_action": report.get("next_action"),
    }


def _history_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(report.get("summary"))
    return {
        "ingest_status": report.get("ingest_status"),
        "account_mode": report.get("account_mode") or _mapping(report.get("query")).get("account_mode"),
        "closed_position_count": summary.get("closed_position_count"),
        "history_record_count": summary.get("history_record_count") or len(report.get("history_records") or []),
        "net_profit_loss_account": summary.get("net_profit_loss_account"),
        "next_action": report.get("next_action"),
    }


def _candidate_brief(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "symbol": candidate.get("symbol"),
        "timeframe": candidate.get("timeframe"),
        "direction": candidate.get("direction"),
        "decision_ref": candidate.get("decision_ref"),
    }


def _unavailable(kind: str, exc: Exception) -> dict[str, Any]:
    return {
        "report_kind": kind,
        "status": "unavailable",
        "error": f"{type(exc).__name__}: {exc}",
        "broker_touched": False,
        "money_moved": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    try:
        return tuple(str(item) for item in value if str(item))
    except TypeError:
        return (str(value),)


def _norm_tf(value: Any) -> str:
    return str(value or "").strip().upper()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return round(float(default), 6)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clamp_scheduler_interval(value: int) -> int:
    return max(
        MIN_SCHEDULER_INTERVAL_SECONDS,
        min(MAX_SCHEDULER_INTERVAL_SECONDS, int(value)),
    )


def _clamp_scan_candidate_limit(value: int | None) -> int:
    if value is None:
        value = DEFAULT_SCAN_CANDIDATE_LIMIT
    return max(1, min(MAX_SCAN_CANDIDATE_LIMIT, int(value)))


def _scheduler_next_action(
    running: bool,
    latest_after: Mapping[str, Any],
    last_error: str,
) -> str:
    if last_error:
        return "Inspect the paper sample collector scheduler error before restarting it."
    if running:
        return "Paper sample collection scheduler is running read-only probes; wait for a PASS-token sample or stop it from Settings."
    if latest_after:
        return str(
            latest_after.get("next_action")
            or "Restart the paper sample collector scheduler when ready to keep collecting evidence."
        )
    return "Start the paper sample collector scheduler to run broker-grade paper evidence probes on an owner-controlled timer."


__all__ = [
    "DEFAULT_SCHEDULER_INTERVAL_SECONDS",
    "DEFAULT_SCAN_CANDIDATE_LIMIT",
    "MAX_SCHEDULER_INTERVAL_SECONDS",
    "MAX_SCAN_CANDIDATE_LIMIT",
    "MIN_SCHEDULER_INTERVAL_SECONDS",
    "REPORT_KIND",
    "RUN_REPORT_KIND",
    "SCAN_REPORT_KIND",
    "SCHEDULER_REPORT_KIND",
    "STATUS_AWAITING_CLOSED_HISTORY",
    "STATUS_AWAITING_PAPER_EXECUTION",
    "STATUS_COLLECTING_OUTCOMES",
    "STATUS_NEEDS_BROKER_GRADE_CANDLES",
    "STATUS_NEEDS_PASS_TOKEN",
    "STATUS_NEEDS_REAL_CANDLE_PROBE",
    "STATUS_NEEDS_WASTE_RUNNER_CAPTURE",
    "STATUS_OUTCOMES_READY",
    "SCHEDULER_RUNNING",
    "SCHEDULER_STOPPED",
    "WastePaperSampleCollectorScheduler",
    "build_waste_paper_sample_collector",
    "run_waste_paper_sample_collector_scheduler_once",
    "run_waste_paper_sample_collection_once",
    "set_waste_paper_sample_collector_scheduler",
    "start_waste_paper_sample_collector_scheduler",
    "stop_waste_paper_sample_collector_scheduler",
    "waste_paper_sample_collector_scheduler_status",
]
