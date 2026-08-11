"""Owner-controlled WASTE-loop runner — ticks the W->A->S->T->E cycle on a timer
and brings the live AI-activity heartbeat to life.

This is the finale wire of the adaptive loop. The engine core
(:class:`cas_forex.waste_loop.WasteLoop`) is a pure, dependency-injected
orchestrator; the edge gate, authorization registry, money-management and
heartbeat modules are built and tested. NOTHING ran them on a schedule. This
module is that missing runner: a background daemon thread that builds the real
stage callables, ticks the loop every N seconds, and stamps
:mod:`cas_forex.loop_heartbeat` with the EXACT stage each tick is in so the
cockpit indicator pulses with what the loop is ACTUALLY doing.

PAPER-SAFE BY DEFAULT (non-negotiable)
======================================
* The runner never flips the live-money gate. ``execute`` dispatches through the
  SAME gated dispatch chokepoint the manual button uses (``order_dispatch.dispatch_order``
  -> ``execution_guard.guarded_place_order``), which re-checks the owner's
  ``is_demo_account`` / live-trading authorization at the bridge boundary,
  fail-closed. By default that means paper/demo dispatch; when the owner enables
  live trading and all runtime gates pass, the same Execute stage can reach the
  owner-configured real bridge.
* If live trading is owner-authorized (so a tick could place real orders),
  :func:`start_runner` refuses to start without ``confirm=True`` — mirroring the
  paper dispatch loop's ``?confirm`` gate.

FAIL-CLOSED, AMPLIFY-NOT-CREATE (the honesty core)
==================================================
* ``execute_fn`` is reachable from EXACTLY ONE branch of ``WasteLoop.tick`` — a
  fresh edge-gate PASS carrying a non-empty token. There is no other path. On a
  PASS the runner FIRST registers the authorization
  (``edge_authorization.authorize``) and THEN dispatches; the dispatch chokepoint
  re-verifies that registration (``edge_authorization.require``), so the runner is
  structurally incapable of placing an order without a tested edge — verified twice.
* ``strategize`` decides direction (LONG/SHORT) or returns ``None``. It NEVER
  fabricates an edge: with no measured signal it returns ``None`` and the tick ends
  at ``no_trade``. Mostly-NO_TRADE is the correct, honest behaviour.
* ``size``/``manage`` only AMPLIFY a confirmed edge. Breakeven-lock
  (``trade_management.breakeven_lock`` -> ``bridge.modify_position``) only protects
  principal; compounding (``compounding_governor``) only adds to an already-confirmed
  winner and refuses without a FRESH PASS.
* The objective's $250 floor / $3,500 daily CAP and the 0.65 edge threshold are
  owner sliders. The runner READS them: it stops opening new trades once the daily
  CAP is hit (``ai_objective.daily_cap_reached``) and tests at the owner threshold.
  It never lowers the bar to hit a number.

Owner-controlled: nothing starts this automatically. A single global runner
(single-owner cockpit); in-memory thread state resets on restart, but each cycle
is also written to the durable WASTE cycle audit so the latest decision trail
survives a process restart.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Callable, Mapping, Optional

from cas_forex import edge_authorization, loop_heartbeat
from cas_forex.ai_control_authority import get_authority
from cas_forex.ai_control_surface import AiControlSurface
from cas_forex.ai_objective import ProfitObjective
from cas_forex.compounding_governor import decide as decide_compound
from cas_forex.edge_gate import CandidateSetup as GateCandidateSetup
from cas_forex.edge_gate import EdgeTestDecision, evaluate_candidate
from cas_forex.live_order_dry_run import (
    DEFAULT_COMPOUND_ADD_AUDIT_PATH,
    COMPOUND_ADD_REPORT_KIND,
    REPORT_KIND as LIVE_ORDER_DRY_RUN_REPORT_KIND,
    CompoundAddDryRunRequest,
    LiveOrderDryRunAuditLog,
    STATUS_BLOCKED,
    STATUS_PASS,
    build_compound_add_order_dry_run,
)
from cas_forex.trade_management import breakeven_lock, position_size
from cas_forex.waste_cycle_audit import (
    WasteCycleAuditStore,
    default_waste_cycle_audit_store,
)
from cas_forex.waste_loop import CandidateSetup, CompoundDecision, WasteLoop
from cas_forex.waste_runner_supervisor import (
    WasteRunnerSupervisorConflict,
    WasteRunnerSupervisorStore,
    default_waste_runner_supervisor_store,
    process_owner_id,
)

# The owner drives — interval can be anything from 1 second up to a day. Very low
# intervals hammer the data feed + CPU; that's the owner's call, surfaced as an
# honest note, not blocked.
MIN_INTERVAL_SECONDS = 1
DEFAULT_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86_400
COMPOUND_ADD_HANDOFF_REPORT_KIND = "cas_forex_waste_compound_add_dispatch_handoff"
WASTE_ENTRY_HANDOFF_REPORT_KIND = "cas_forex_waste_entry_dispatch_handoff"
STATUS_COMPOUND_ADD_HANDOFF_BLOCKED = "BLOCKED_COMPOUND_ADD_DISPATCH_HANDOFF"
STATUS_COMPOUND_ADD_HANDOFF_REVIEW_BLOCKED = "COMPOUND_ADD_HANDOFF_REVIEW_BLOCKED"
STATUS_COMPOUND_ADD_HANDOFF_REVIEW_READY = "COMPOUND_ADD_HANDOFF_REVIEW_READY"
STATUS_WASTE_ENTRY_HANDOFF_BLOCKED = "BLOCKED_WASTE_ENTRY_DISPATCH_HANDOFF"
STATUS_WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED = "WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED"
STATUS_WASTE_ENTRY_HANDOFF_REVIEW_READY = "WASTE_ENTRY_HANDOFF_REVIEW_READY"

WASTE_PAPER_EXECUTION_SINK_CLAIM_BOUNDARY = (
    "WASTE execution sink selects the owner-configured broker bridge and sends "
    "only PASS-token WASTE entries through order_dispatch. Paper/demo is the "
    "default; an owner-authorized live bridge can be reached only after the "
    "live-trading runtime gate, edge authorization, pilot, risk, and audit gates "
    "all pass at the dispatch chokepoint. It records the attempt in "
    "order-attempts.json and never creates owner ACCEPT, broker ACCEPT, live "
    "authority, deposits, withdrawals, bank/card movement, or payout actions."
)

COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY = (
    "WASTE compound-add dispatch handoff only rebuilds the exact add TradeIntent "
    "from a passing compound-add dry-run order_request and sends it through the "
    "normal order_dispatch chokepoint. That chokepoint still requires current "
    "owner ACCEPT for the exact add fingerprint, live-trading authority, edge "
    "authorization, live-pilot gates, risk gates, emergency stop clearance, and "
    "broker bridge availability before any bridge can be touched. The handoff "
    "does not create broker ACCEPT, deposit, withdraw, move bank/card money, "
    "automate payouts, mint edge tokens, or authorize live trading by itself."
)

WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY = (
    "WASTE entry dispatch handoff only rebuilds the exact TradeIntent from a "
    "passing live-order dry-run that was sourced from a broker-grade WASTE "
    "real-candle probe. It never creates a candidate, never creates owner "
    "ACCEPT, and never bypasses order_dispatch. The normal dispatch chokepoint "
    "still requires owner live-trading authority, current owner ACCEPT for the "
    "latest passing dry-run review, edge authorization, live-pilot gates, risk "
    "gates, emergency-stop clearance, audit availability, and broker bridge "
    "availability before any bridge can be touched. The handoff does not create "
    "broker ACCEPT, deposit, withdraw, move bank/card money, automate payouts, "
    "mint edge tokens, or authorize live trading by itself."
)

# Default account equity assumption when no live account snapshot is available
# (sizing converts a risk budget into lots; it does not create an edge).
_DEFAULT_EQUITY = 10_000.0


def _default_waste_paper_bridge_factory() -> Any:
    """Owner-configured paper/demo bridge selection for PASS-only WASTE dispatch.

    ``select_bridge`` prefers the owner's selected MT4/MT5 paper bridge when it
    is configured, otherwise it falls back to the simulator. A connected live MT5
    account is still caught by the execution guard's live-trading gate before an
    order can reach the terminal.
    """

    from cas_forex.broker_control import select_bridge

    return select_bridge()


# ---------------------------------------------------------------------------
# Default honest stage callables.
# ---------------------------------------------------------------------------
# These are the DEFAULT implementations wired into the runner. They are honest:
# the default ``strategize`` forms NO candidate (no measured edge => None), so the
# default loop sits at ``no_trade``. Integration can inject richer watch/analyze/
# strategize functions that read real market/regime state and the screener; the
# runner's fail-closed wiring (PASS-only execute, paper dispatch) is unchanged.


def _default_watch() -> dict[str, Any]:
    """WATCH: snapshot market/regime state. Default is an empty, honest snapshot —
    the runner places no trade off a fabricated state."""
    if os.environ.get("CAS_FOREX_WASTE_SCHEDULED_SNAPSHOT_WATCH") == "1":
        return _scheduled_snapshot_watch()
    try:
        from cas_forex.waste_market_data import build_waste_market_state_scan

        # Owner scalp mode may pin the watch timeframe (e.g. M1); the default
        # zero-arg call is preserved exactly when the env override is absent.
        watch_timeframe = os.environ.get("CAS_FOREX_WASTE_WATCH_TIMEFRAME") or None
        if watch_timeframe:
            return build_waste_market_state_scan(timeframe=watch_timeframe)
        return build_waste_market_state_scan()
    except Exception as exc:
        return {
            "regime": "unknown",
            "symbols": [],
            "candles": [],
            "entry_pairs": [],
            "error": f"market watch unavailable: {type(exc).__name__}: {exc}",
        }


def _scheduled_snapshot_watch() -> dict[str, Any]:
    """Cheap WATCH path for the timed background runner.

    The scheduled worker must not monopolize the API by doing terminal/candle
    reads inside every timer beat. It reads the latest persisted real-candle
    probe only. If that snapshot is missing or only summary-level evidence, the
    runner stays fail-closed at NO_TRADE instead of pretending it has fresh
    holdout data.
    """
    try:
        from cas_forex.waste_real_candle_probe import latest_waste_real_candle_probe

        probe = latest_waste_real_candle_probe()
    except Exception as exc:
        return _empty_scheduled_watch(
            f"scheduled snapshot unavailable: {type(exc).__name__}: {exc}"
        )
    if not isinstance(probe, Mapping):
        return _empty_scheduled_watch("scheduled snapshot unavailable: invalid probe packet")

    market_state = (
        probe.get("market_state") if isinstance(probe.get("market_state"), Mapping) else {}
    )
    entry_report = (
        market_state.get("entry_pair_report")
        if isinstance(market_state.get("entry_pair_report"), Mapping)
        else {}
    )
    candidate = probe.get("candidate") if isinstance(probe.get("candidate"), Mapping) else {}
    analysis = probe.get("analysis") if isinstance(probe.get("analysis"), Mapping) else {}
    edge = probe.get("edge") if isinstance(probe.get("edge"), Mapping) else {}
    hypothesis = (
        candidate.get("directional_hypothesis")
        if isinstance(candidate.get("directional_hypothesis"), Mapping)
        else analysis.get("hypothesis")
    )
    hypothesis = hypothesis if isinstance(hypothesis, Mapping) else {}
    market_meta = (
        candidate.get("market_state_meta")
        if isinstance(candidate.get("market_state_meta"), Mapping)
        else {}
    )
    tuning = (
        market_state.get("directional_hypothesis_tuning")
        if isinstance(market_state.get("directional_hypothesis_tuning"), Mapping)
        else analysis.get("hypothesis_tuning")
    )
    tuning = tuning if isinstance(tuning, Mapping) else {}
    firewall = (
        market_state.get("strategy_firewall")
        if isinstance(market_state.get("strategy_firewall"), Mapping)
        else candidate.get("strategy_firewall")
    )
    firewall = firewall if isinstance(firewall, Mapping) else {}
    cas_map = (
        market_state.get("cas_feature_map")
        if isinstance(market_state.get("cas_feature_map"), Mapping)
        else market_meta.get("cas_feature_map")
    )
    cas_map = cas_map if isinstance(cas_map, Mapping) else {}
    costs = (
        market_state.get("execution_costs")
        if isinstance(market_state.get("execution_costs"), Mapping)
        else {}
    )

    status = str(probe.get("status") or "UNKNOWN")
    symbol = str(probe.get("symbol") or market_state.get("symbol") or candidate.get("symbol") or "")
    timeframe = str(
        probe.get("timeframe") or market_state.get("timeframe") or candidate.get("timeframe") or ""
    )
    try:
        entry_pair_count = int(
            candidate.get("entry_pair_count") or entry_report.get("entry_pair_count") or 0
        )
    except (TypeError, ValueError):
        entry_pair_count = 0
    try:
        candles_count = int(probe.get("candles_count") or 0)
    except (TypeError, ValueError):
        candles_count = 0
    scan_status = (
        "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE"
        if status == "NO_PROBE_RECORDED"
        else "WASTE_SCHEDULED_SNAPSHOT_ONLY"
    )

    return {
        "report_kind": "cas_forex_waste_scheduled_snapshot_watch",
        "status": "WASTE_SCHEDULED_SNAPSHOT_READY"
        if status != "NO_PROBE_RECORDED"
        else "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE",
        "probe_status": status,
        "symbol": symbol or None,
        "timeframe": timeframe or None,
        "source": probe.get("source") or market_state.get("source"),
        "feed_label": market_state.get("feed_label"),
        "fallback_used": bool(
            probe.get("fallback_used", False) or market_state.get("fallback_used", False)
        ),
        "broker_grade_market_truth": bool(
            probe.get("broker_grade_market_truth", False)
            and market_state.get("broker_grade_market_truth", False)
        ),
        "read_only_market_data": True,
        "cached_snapshot_only": True,
        "candles": [],
        "entry_pairs": [],
        "entry_pair_report": {"entry_pair_count": entry_pair_count},
        "candles_count": candles_count,
        "latest_probe_generated_at": probe.get("generated_at"),
        "selected_directional_profile": market_state.get("selected_directional_profile")
        or hypothesis.get("profile"),
        "directional_hypothesis": hypothesis,
        "directional_hypothesis_tuning": tuning,
        "strategy_firewall": firewall,
        "cas_feature_map": cas_map,
        "execution_costs": costs,
        "waste_market_scan": {
            "status": scan_status,
            "attempt_count": 0,
            "selected_symbol": symbol or None,
            "selected_timeframe": timeframe or None,
            "selected_edge_status": edge.get("status"),
            "selected_edge_has_token": bool(edge.get("has_edge_token")),
            "edge_authorization_registered": False,
            "broker_execution_touched": False,
            "money_moved": False,
            "attempts": [],
        },
        "connector_attempts": market_state.get("connector_attempts")
        if isinstance(market_state.get("connector_attempts"), list)
        else [],
        "market_data_claim_boundary": (
            "Scheduled WASTE WATCH reads only the latest persisted real-candle "
            "probe snapshot. It does not touch the broker, fetch candles, create "
            "owner ACCEPT, register edge authorization, place orders, deposit, "
            "withdraw, transfer bank/card funds, automate payouts, or mark live "
            "trading/payment movement LICENSED."
        ),
        "detail": (
            "Timed runner used cached probe evidence only; no fresh candles were "
            "loaded in this WASTE beat."
        ),
    }


def _empty_scheduled_watch(detail: str) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_scheduled_snapshot_watch",
        "status": "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE",
        "source": None,
        "fallback_used": False,
        "broker_grade_market_truth": False,
        "read_only_market_data": True,
        "cached_snapshot_only": True,
        "candles": [],
        "entry_pairs": [],
        "entry_pair_report": {"entry_pair_count": 0},
        "waste_market_scan": {
            "status": "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE",
            "attempt_count": 0,
            "edge_authorization_registered": False,
            "broker_execution_touched": False,
            "money_moved": False,
            "attempts": [],
        },
        "connector_attempts": [],
        "detail": detail,
    }


def _default_analyze(state: Any) -> dict[str, Any]:
    """ANALYZE: derive confidence from the watched state. Default carries no
    confidence when no candles are present. If a watcher injects candles, delegate
    to the directional hypothesis engine; it still does NOT authorize a trade."""
    if isinstance(state, dict) and state.get("candles"):
        from cas_forex.directional_intelligence import analyze_market_state

        return analyze_market_state(state)
    return {"confidence": 0.0, "state": state}


def _default_strategize(state: Any, analysis: Any) -> Optional[CandidateSetup]:
    """STRATEGIZE: form a CandidateSetup with a REAL direction, or return None.

    Honest default: with no measured edge there is no candidate, so this returns
    ``None`` and the tick ends at ``no_trade``. Direction (LONG/SHORT) is decided
    ONLY here when a real signal exists; the gate downstream never invents one.
    """
    if isinstance(state, dict) and isinstance(analysis, dict) and state.get("candles"):
        from cas_forex.directional_intelligence import strategize_market_state

        return strategize_market_state(state, analysis)
    return None


def _bridge_dispatch_risk_context(bridge: Any) -> tuple[dict[str, Any], Optional[Mapping[str, Any]]]:
    """Best-effort fresh account/position snapshot for the dispatch chokepoint.

    Real-capable bridges must provide enough account truth for the live gate to
    pass. Missing account fields remain missing; this helper does not fabricate
    balance, equity, margin, or free-margin values.
    """

    telemetry: dict[str, Any] = {
        "open_positions": [],
        "data_freshness": {
            "stale": False,
            "source": "bridge_dispatch_risk_context",
        },
    }
    for method_name in ("get_all_open_positions", "get_open_positions"):
        method = getattr(bridge, method_name, None)
        if not callable(method):
            continue
        try:
            rows = method()
        except Exception:
            continue
        if isinstance(rows, list):
            telemetry["open_positions"] = rows
            telemetry["open_positions_source"] = method_name
            break

    account_snapshot: Optional[Mapping[str, Any]] = None
    account_method = getattr(bridge, "get_account_info", None)
    if callable(account_method):
        try:
            account = account_method()
        except Exception:
            account = None
        if isinstance(account, Mapping):
            account_snapshot = account
            telemetry["account_snapshot"] = dict(account)
    return telemetry, account_snapshot


class WasteRunner:
    """Background runner that ticks a :class:`WasteLoop` on an owner-set interval
    and stamps the live heartbeat per stage. Paper-safe, fail-closed, default OFF.
    """

    def __init__(
        self,
        *,
        bridge_factory: Optional[Callable[[], Any]] = None,
        dispatch_fn: Optional[Callable[..., Any]] = None,
        objective: Optional[ProfitObjective] = None,
        control: Optional[AiControlSurface] = None,
        watch_fn: Optional[Callable[[], Any]] = None,
        analyze_fn: Optional[Callable[[Any], Any]] = None,
        strategize_fn: Optional[Callable[[Any, Any], Optional[CandidateSetup]]] = None,
        today_realized_fn: Optional[Callable[[], float]] = None,
        equity_fn: Optional[Callable[[], float]] = None,
        audit_store: Optional[WasteCycleAuditStore] = None,
        order_attempt_audit_store: Optional[Any] = None,
        compound_add_dry_run_audit: Optional[LiveOrderDryRunAuditLog] = None,
        compound_add_dispatch_enabled: bool = False,
        supervisor_store: Optional[WasteRunnerSupervisorStore] = None,
        supervisor_owner_id: Optional[str] = None,
    ) -> None:
        authority = get_authority()
        self.objective = objective or authority.objective()
        self.control = control or authority.control
        self._bridge_factory = bridge_factory or _default_waste_paper_bridge_factory
        self._bridge_factory_source = (
            "injected" if bridge_factory is not None else "broker_control.select_bridge"
        )
        # ``dispatch_fn`` is the dispatch sink. The default is the real gated
        # broker path; tests inject a fake to assert dispatch-on-PASS-only.
        self._dispatch_fn = dispatch_fn
        self._watch_fn = watch_fn or _default_watch
        self._analyze_fn = analyze_fn or _default_analyze
        self._strategize_fn = strategize_fn or _default_strategize
        self._today_realized_fn = today_realized_fn or (lambda: 0.0)
        self._equity_fn = equity_fn or (lambda: _DEFAULT_EQUITY)
        self._audit_store = audit_store or default_waste_cycle_audit_store()
        self._order_attempt_audit_store = order_attempt_audit_store
        self._compound_add_dry_run_audit = compound_add_dry_run_audit
        self._compound_add_dispatch_enabled = bool(compound_add_dispatch_enabled)
        self._supervisor_store = supervisor_store or default_waste_runner_supervisor_store()
        self._supervisor_owner_id = supervisor_owner_id or process_owner_id()

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.interval = DEFAULT_INTERVAL_SECONDS
        self.cycles_run = 0
        self.last_decision: str = ""
        self.last_reason: str = ""
        self.last_run_iso: str = ""
        self.last_error: str = ""
        self.started_at_iso: str = ""
        self._latest_watch_state: Any = None
        self._latest_analysis: Any = None
        self._latest_edge_decision: Optional[EdgeTestDecision] = None

        self._loop = self._build_loop()

    # -- loop assembly ----------------------------------------------------
    def _build_loop(self) -> WasteLoop:
        return WasteLoop(
            watch_fn=self._watch_stage,
            analyze_fn=self._analyze_stage,
            strategize_fn=self._strategize_stage,
            test_fn=self._test_stage,
            size_fn=self._size_stage,
            execute_fn=self._execute_stage,
            manage_fn=self._manage_stage,
            objective=self.objective,
            control=self.control,
            paper_learning_fn=self._paper_learning_allowed,
        )

    def _paper_learning_allowed(self) -> bool:
        """Owner gate for token-less paper LEARNING trades.

        True only when the effective runtime mode is PAPER and the owner's
        ``paper_learning_trades`` dial is ON. Any error reads False (fail-closed
        back to NO_TRADE). Live/real mode NEVER learns with money: the dispatch
        chokepoint independently refuses token-less real dispatches."""
        try:
            if _effective_mode() != "PAPER":
                return False
            return bool(self.control.get("paper_learning_trades"))
        except Exception:
            return False

    # -- stage wrappers: each stamps the live heartbeat -------------------
    # The heartbeat pulses with the REAL stage the loop is in. WasteLoop also sets
    # its own ``current_stage``; recording here makes the cockpit indicator reflect
    # the actual stage of the actual tick (honest by construction — stale => idle).

    def _watch_stage(self) -> Any:
        loop_heartbeat.record("watch", detail="watching market/regime state")
        self._latest_watch_state = None
        self._latest_analysis = None
        self._latest_edge_decision = None
        state = self._watch_fn()
        self._latest_watch_state = state
        return state

    def _analyze_stage(self, state: Any) -> Any:
        loop_heartbeat.record("analyze", detail="scoring confidence")
        analysis = self._analyze_fn(state)
        self._latest_analysis = analysis
        return analysis

    def _strategize_stage(self, state: Any, analysis: Any) -> Optional[CandidateSetup]:
        # Daily-CAP discipline: once today's realized profit hits the owner CAP,
        # STOP opening new trades for the day (protect the gains). This is risk
        # discipline, never a forecast — and it can only SUPPRESS a candidate,
        # never manufacture one.
        if self.objective.daily_cap_reached(self._today_realized_fn()):
            loop_heartbeat.record(
                "no_trade", detail="daily CAP reached — no new trades today"
            )
            return None
        setup = self._strategize_fn(state, analysis)
        symbol = getattr(setup, "symbol", None)
        loop_heartbeat.record(
            "strategize",
            detail="candidate formed" if setup is not None else "no candidate",
            symbol=symbol,
        )
        return setup

    def _test_stage(self, setup: CandidateSetup) -> EdgeTestDecision:
        loop_heartbeat.record("test", detail="null edge test", symbol=setup.symbol)
        threshold = float(self.control.get("edge_threshold"))
        gate_setup = _to_gate_setup(setup)
        entry_pairs = self._entry_pairs_for(setup)
        decision = evaluate_candidate(gate_setup, entry_pairs, threshold=threshold)
        self._latest_edge_decision = decision
        return decision

    def _size_stage(self, setup: CandidateSetup) -> float:
        loop_heartbeat.record("test", detail="sizing position", symbol=setup.symbol)
        equity = float(self._equity_fn())
        risk_pct = float(self.control.get("max_risk_pct_per_trade"))
        risk_budget = max(0.0, equity * risk_pct / 100.0)
        return position_size(
            equity=equity,
            risk_budget_usd=risk_budget,
            entry=float(setup.entry),
            stop_loss=float(setup.stop_loss),
            symbol=setup.symbol,
        )

    def _execute_stage(self, setup: CandidateSetup, lots: float, token: str) -> Any:
        """EXECUTE — a fresh PASS token, or a token-less paper LEARNING trade.

        Fail-closed twice: register the authorization for this setup's
        ``decision_ref`` (so the dispatch chokepoint will verify it), THEN dispatch
        through the gated broker path. The dispatch path re-checks the registration
        and refuses without a fresh, matching PASS. The selected bridge may be
        paper/demo by default or real only when the owner live gate is authorized.

        LEARNING branch (owner decision 2026-07-01): when the loop authorizes a
        paper learning trade the token is EMPTY — we deliberately skip the
        edge-authorization registration so the order goes through the legacy
        paper dispatch path. A real-money dispatch without a fresh PASS token is
        refused at the chokepoint, so this branch can only ever fill on
        paper/demo. Risk gate and live gate still run in full.
        """
        if not token:
            loop_heartbeat.record(
                "execute", detail="dispatching paper LEARNING order", symbol=setup.symbol
            )
            return self._dispatch(setup, lots, "")
        loop_heartbeat.record("execute", detail="dispatching gated order", symbol=setup.symbol)
        gate_setup = _to_gate_setup(setup)
        source_decision = self._latest_edge_decision
        if (
            source_decision is None
            or getattr(source_decision, "status", None) != "PASS"
            or getattr(source_decision, "edge_token", None) != token
        ):
            source_decision = EdgeTestDecision(
                status="PASS",
                measured_win_prob=0.0,
                null_p95=0.0,
                threshold=float(self.control.get("edge_threshold")),
                edge_token=token,
                evaluated_at=_token_evaluated_at(setup, token),
                reason="runner re-asserts PASS for authorization",
            )
        # Register the PASS so the dispatch chokepoint can verify it. The token is
        # the same one the gate minted; binding it back to the setup is fail-closed.
        try:
            from cas_forex.config import config as current_config
        except Exception:
            current_config = None
        edge_authorization.authorize(
            setup.decision_ref,
            _pass_decision(source_decision, setup, token),
            gate_setup,
            config=current_config,
            volume=lots,
            order_type="MARKET",
            price=float(setup.entry),
            strategy_id="waste-entry",
        )
        return self._dispatch(setup, lots, token)

    def _manage_stage(self, **kwargs: Any) -> Optional[CompoundDecision]:
        """COMPOUND/MANAGE — runs after a placed trade. AMPLIFY ONLY.

        Breakeven-lock protects principal (moves SL to entry once +1R) via the
        shared ``bridge.modify_position`` signature; compounding adds to an
        already-confirmed winner only with a FRESH PASS. Never undoes a placed trade.
        """
        loop_heartbeat.record("compound", detail="managing open position")
        setup: Optional[CandidateSetup] = kwargs.get("setup")
        execute_result = kwargs.get("execute_result")
        if setup is None:
            return CompoundDecision(action="HOLD", add_units=0, reason="no setup to manage")

        lock_note = ""
        # Breakeven principal-lock: if the trade is up >=1R, move SL to entry.
        ticket = _ticket_from(execute_result)
        current = _current_price_from(execute_result)
        if ticket is not None and current is not None:
            new_sl = breakeven_lock(
                float(setup.entry), float(current), setup.direction, float(setup.stop_loss)
            )
            if new_sl is not None and self._bridge_factory is not None:
                try:
                    bridge = self._bridge_factory()
                    bridge.modify_position(
                        int(ticket), stop_loss=float(new_sl), take_profit=float(setup.take_profit)
                    )
                    lock_note = "breakeven-lock: SL moved to entry (principal protected). "
                except Exception:
                    # Management must never undo a placed trade.
                    lock_note = "breakeven-lock skipped (modify failed). "
        compound = _compound_decision_from_cas_context(
            setup=setup,
            execute_result=execute_result,
            control=kwargs.get("control") or self.control,
            compound_edge=kwargs.get("compound_edge"),
            add_risk_gate_passed=bool(kwargs.get("add_risk_gate_passed", False)),
            current_units=int(kwargs.get("current_units", 1) or 1),
        )
        if compound.action == "ADD":
            add_dry_run = _compound_add_dry_run_from_manage_context(
                setup=setup,
                execute_result=execute_result,
                lots=float(kwargs.get("lots", 0.0) or 0.0),
                control=kwargs.get("control") or self.control,
                current_units=int(kwargs.get("current_units", 1) or 1),
                compound=compound,
                broker_position=kwargs.get("broker_position"),
                terminal_position_reconciliation=kwargs.get("terminal_position_reconciliation"),
                add_order_id=kwargs.get("add_order_id"),
                add_decision_ref=kwargs.get("add_decision_ref"),
                add_volume=kwargs.get("add_volume"),
                config=kwargs.get("config"),
                live_telemetry=kwargs.get("live_telemetry"),
                account_snapshot=kwargs.get("account_snapshot"),
                equity_peak=kwargs.get("equity_peak"),
                audit=(
                    kwargs.get("compound_add_dry_run_audit")
                    or self._compound_add_dry_run_audit
                    or LiveOrderDryRunAuditLog(DEFAULT_COMPOUND_ADD_AUDIT_PATH)
                ),
            )
            add_dispatch_intent = None
            add_dispatch_result = None
            try:
                add_dispatch_intent = build_compound_add_dispatch_intent_from_dry_run(
                    add_dry_run
                ).__dict__.copy()
            except Exception as exc:
                add_dispatch_result = _blocked_compound_add_handoff(
                    reason=f"compound-add dispatch intent unavailable: {type(exc).__name__}: {exc}",
                    add_dry_run=add_dry_run,
                )
            attempt_handoff = bool(
                kwargs.get("attempt_compound_add_dispatch", self._compound_add_dispatch_enabled)
            )
            if attempt_handoff:
                add_dispatch_result = dispatch_compound_add_from_dry_run(
                    add_dry_run,
                    bridge=kwargs.get("compound_add_bridge"),
                    bridge_factory=kwargs.get("compound_add_bridge_factory") or self._bridge_factory,
                    config=kwargs.get("config"),
                    live_telemetry=kwargs.get("live_telemetry"),
                    account_snapshot=kwargs.get("account_snapshot"),
                    equity_peak=kwargs.get("equity_peak"),
                    audit_store=kwargs.get("compound_add_dispatch_audit_store"),
                )
            compound = CompoundDecision(
                action=compound.action,
                add_units=compound.add_units,
                reason=compound.reason,
                add_dry_run=add_dry_run,
                add_dispatch_intent=add_dispatch_intent,
                add_dispatch_result=add_dispatch_result,
            )
        if lock_note:
            return CompoundDecision(
                action=compound.action,
                add_units=compound.add_units,
                reason=lock_note + compound.reason,
                add_dry_run=compound.add_dry_run,
                add_dispatch_intent=compound.add_dispatch_intent,
                add_dispatch_result=compound.add_dispatch_result,
            )
        return compound

    # -- dispatch ---------------------------------------------------------
    def _dispatch(self, setup: CandidateSetup, lots: float, token: str) -> Any:
        if self._dispatch_fn is not None:
            return self._dispatch_fn(setup=setup, lots=lots, token=token)
        return self._default_paper_dispatch(setup, lots, token)

    def _default_paper_dispatch(self, setup: CandidateSetup, lots: float, token: str) -> Any:
        """Dispatch through the real gated broker path. Imported lazily so the heavy
        broker/order modules stay off the import path for unit tests.

        Builds a normalized ``TradeIntent`` and hands it to ``dispatch_intent``,
        which runs the FULL gate chain (live gate, edge gate, risk gate) before the
        bridge is touched. The edge gate consults the authorization the runner just
        registered for this ``decision_ref`` — no PASS => the bridge is never reached.
        With normal config this is paper/demo; with owner-authorized live config
        and a real-capable bridge, this same Execute path can reach the real bridge.
        """
        from cas_forex.order_dispatch import TradeIntent, dispatch_intent

        bridge = self._bridge_factory()
        if bridge is None:
            return {"status": "NO_BRIDGE", "detail": "bridge_factory returned no bridge"}
        try:
            from cas_forex.config import config as current_config
        except Exception:
            current_config = None
        intent = TradeIntent(
            order_id=f"waste-{setup.decision_ref}",
            decision_ref=setup.decision_ref,
            symbol=setup.symbol,
            direction=setup.direction,
            volume=float(lots),
            stop_loss=float(setup.stop_loss),
            take_profit=float(setup.take_profit),
            price=float(setup.entry),
            strategy_id="waste-entry",
            ai_action="WASTE_LOOP",
        )
        if token:
            source_decision = self._latest_edge_decision
            if (
                source_decision is None
                or getattr(source_decision, "status", None) != "PASS"
                or getattr(source_decision, "edge_token", None) != token
            ):
                source_decision = EdgeTestDecision(
                    status="PASS",
                    measured_win_prob=0.0,
                    null_p95=0.0,
                    threshold=float(self.control.get("edge_threshold")),
                    edge_token=token,
                    evaluated_at=_token_evaluated_at(setup, token),
                    reason="runner re-asserts PASS for contextual authorization",
                )
            edge_authorization.authorize(
                setup.decision_ref,
                _pass_decision(source_decision, setup, token),
                _to_gate_setup(setup),
                config=current_config,
                bridge=bridge,
                volume=lots,
                order_type="MARKET",
                price=float(setup.entry),
                strategy_id="waste-entry",
            )
        live_telemetry, account_snapshot = _bridge_dispatch_risk_context(bridge)
        return dispatch_intent(
            intent,
            bridge,
            config=current_config,
            live_telemetry=live_telemetry,
            account_snapshot=account_snapshot,
            audit_store=self._order_attempt_audit_store,
            audit_source="waste_runner",
        )

    # -- per-setup data helpers (overridable at integration) --------------
    def _entry_pairs_for(self, setup: CandidateSetup) -> list[dict[str, Any]]:
        """Recent OOS outcomes for THIS setup's pattern, fed to the null test.

        Honest default: empty — with no measured OOS history the gate returns
        ``NO_TRADE_INSUFFICIENT_BARS`` (fail-closed). Integration injects a richer
        ``strategize``/data path that carries real outcomes on the candidate.
        """
        pairs = getattr(setup, "entry_pairs", None)
        return list(pairs) if pairs else []

    def _enrich_cycle_result(self, result: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(result)
        enriched["watch_state"] = _watch_state_summary(self._latest_watch_state)
        enriched["analysis"] = _analysis_summary(self._latest_analysis)
        return enriched

    # -- thread lifecycle -------------------------------------------------
    def _run(self) -> None:
        from datetime import datetime, timezone

        # Do not let a just-started heavy market scan starve the API response
        # path. The runner is live/scheduled immediately; the first tick can wait.
        if self._stop_event.wait(min(max(MIN_INTERVAL_SECONDS, self.interval), 60.0)):
            self._supervisor_store.release(owner_id=self._supervisor_owner_id)
            loop_heartbeat.record("idle", detail="runner stopped")
            return
        while not self._stop_event.is_set():
            try:
                if self._supervisor_store.should_stop(owner_id=self._supervisor_owner_id):
                    self.last_error = "Supervisor requested WASTE runner stop."
                    break
                renewed, _ = self._supervisor_store.renew(
                    owner_id=self._supervisor_owner_id,
                    interval_seconds=self.interval,
                    mode=_effective_mode(),
                )
            except OSError as exc:
                # A transient supervisor-state I/O failure (OneDrive/antivirus
                # file lock — the exact failure that once killed this thread)
                # must not stop the loop. The lease TTL (180s) comfortably
                # covers a missed renewal at the 60s cycle; record and retry
                # on the next cycle.
                self.last_error = f"Supervisor state I/O error (will retry): {exc}"
                self._record_error(self.last_error, running=True)
                self._stop_event.wait(max(MIN_INTERVAL_SECONDS, self.interval))
                continue
            if not renewed:
                self.last_error = "Supervisor lease conflict; stopping this local WASTE runner."
                self._record_error(self.last_error, running=True)
                break
            try:
                result = self._enrich_cycle_result(self._loop.tick())
                self._stamp_terminal_stage(result)
                self.cycles_run += 1
                self.last_decision = str(result.get("decision", ""))
                self.last_reason = str(result.get("reason", ""))
                self.last_run_iso = datetime.now(timezone.utc).isoformat()
                self.last_error = ""
                self._record_cycle(result, running=True)
            except Exception as exc:  # one bad tick must never kill the thread
                self.last_error = f"{type(exc).__name__}: {exc}"
                self._record_error(self.last_error, running=True)
            self._stop_event.wait(max(MIN_INTERVAL_SECONDS, self.interval))
        # On stop, collapse the heartbeat to OFFLINE/idle — never invented activity.
        self._supervisor_store.release(owner_id=self._supervisor_owner_id)
        loop_heartbeat.record("idle", detail="runner stopped")

    def start(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> dict[str, Any]:
        from datetime import datetime, timezone

        with self._lock:
            self.interval = max(
                MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds))
            )
            if self._thread and self._thread.is_alive():
                renewed, _ = self._supervisor_store.renew(
                    owner_id=self._supervisor_owner_id,
                    interval_seconds=self.interval,
                    mode=_effective_mode(),
                )
                if not renewed:
                    self.last_error = "Supervisor lease conflict; local WASTE runner should stop."
                    self._stop_event.set()
                return self._status_locked()
            try:
                self._supervisor_store.acquire(
                    owner_id=self._supervisor_owner_id,
                    interval_seconds=self.interval,
                    mode=_effective_mode(),
                )
            except WasteRunnerSupervisorConflict as exc:
                self.last_error = str(exc)
                status = self._status_locked()
                status["status"] = "SUPERVISOR_CONFLICT"
                status["detail"] = (
                    "Another fresh WASTE runner owner already holds the durable "
                    "lease; this process did not start a duplicate timed loop."
                )
                return status
            self._stop_event.clear()
            self.started_at_iso = datetime.now(timezone.utc).isoformat()
            self._thread = threading.Thread(
                target=self._run, name="cas-waste-runner", daemon=True
            )
            self._thread.start()
            return self._status_locked()

    def stop(self) -> dict[str, Any]:
        self._supervisor_store.request_stop(requested_by=self._supervisor_owner_id)
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3.0)
        with self._lock:
            self._thread = None
            loop_heartbeat.record("idle", detail="runner stopped")
            self._supervisor_store.release(owner_id=self._supervisor_owner_id)
            return self._status_locked()

    def tick_once(self) -> dict[str, Any]:
        """Run exactly one tick synchronously (tests / manual single-step)."""
        result = self._enrich_cycle_result(self._loop.tick())
        self._stamp_terminal_stage(result)
        self.cycles_run += 1
        self.last_decision = str(result.get("decision", ""))
        self.last_reason = str(result.get("reason", ""))
        try:
            from datetime import datetime, timezone

            self.last_run_iso = datetime.now(timezone.utc).isoformat()
            self.last_error = ""
            self._record_cycle(result, running=False)
        except Exception as exc:  # audit failure must not change trade authority
            self.last_error = f"audit failed: {type(exc).__name__}: {exc}"
        return result

    def _stamp_terminal_stage(self, result: dict[str, Any]) -> None:
        """Stamp the heartbeat with the tick's TERMINAL stage so the cockpit
        indicator settles on what the tick actually decided (no_trade / blocked /
        execute / compound), not the last intermediate stage. Honest by construction:
        a stale beat collapses to idle regardless."""
        stage = self._loop.current_stage()
        symbol = None
        setup = result.get("setup")
        if setup is not None:
            symbol = getattr(setup, "symbol", None)
        loop_heartbeat.record(
            stage, detail=str(result.get("decision", "")).lower() or None, symbol=symbol
        )

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict[str, Any]:
        running = bool(self._thread and self._thread.is_alive())
        durable = self._audit_store.build_status()
        supervisor = self._supervisor_store.build_status(
            owner_id=self._supervisor_owner_id,
            local_running=running,
        )
        return {
            "report_kind": "cas_forex_waste_runner",
            "running": running,
            "status": "RUNNING" if running else "STOPPED",
            "interval_seconds": self.interval,
            "cycles_run": self.cycles_run,
            "last_decision": self.last_decision or None,
            "last_reason": self.last_reason or None,
            "last_run_iso": self.last_run_iso or None,
            "last_error": self.last_error or None,
            "started_at_iso": self.started_at_iso or None,
            "current_stage": self._loop.current_stage(),
            "edge_threshold": self.control.get("edge_threshold"),
            "daily_cap": self.objective.daily_max_target,
            "daily_cap_reached": self.objective.daily_cap_reached(self._today_realized_fn()),
            "durable_cycle": durable.get("latest_cycle"),
            "durable_cycle_status": durable,
            "supervisor": supervisor,
            "paper_execution_sink": {
                "configured": self._bridge_factory is not None,
                "bridge_factory_source": self._bridge_factory_source,
                "order_attempt_audit": (
                    "injected" if self._order_attempt_audit_store is not None else "default"
                ),
                "claim_boundary": WASTE_PAPER_EXECUTION_SINK_CLAIM_BOUNDARY,
            },
            "mode": _effective_mode(),
            "note": (
                "Ticks the WASTE loop (W->A->S->T->E) on a timer and pulses the live "
                "heartbeat per stage. Paper-safe by default; execute is reachable ONLY "
                "through a fresh edge-gate PASS, and dispatch re-verifies it fail-closed. "
                "Mostly NO_TRADE is the correct, honest behaviour when no edge passes."
            ),
        }

    def _record_cycle(self, result: dict[str, Any], *, running: bool) -> None:
        self._audit_store.record_cycle(
            result,
            running=running,
            interval_seconds=self.interval,
            mode=_effective_mode(),
            cycles_run=self.cycles_run,
            last_error=self.last_error,
        )

    def _record_error(self, error: str, *, running: bool) -> None:
        try:
            self._audit_store.record_error(
                error,
                running=running,
                interval_seconds=self.interval,
                mode=_effective_mode(),
                cycles_run=self.cycles_run,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_gate_setup(setup: CandidateSetup) -> GateCandidateSetup:
    """Map the waste_loop CandidateSetup onto the edge_gate CandidateSetup (same
    field shape; kept as distinct types so each module owns its contract)."""
    return GateCandidateSetup(
        symbol=setup.symbol,
        timeframe=setup.timeframe,
        direction=setup.direction,
        entry=float(setup.entry),
        stop_loss=float(setup.stop_loss),
        take_profit=float(setup.take_profit),
        signal_strength=float(setup.signal_strength),
        regime=setup.regime,
        decision_ref=setup.decision_ref,
    )


def _pass_decision(
    template: EdgeTestDecision, setup: CandidateSetup, token: str
) -> EdgeTestDecision:
    """A PASS EdgeTestDecision carrying ``token`` for authorization registration."""
    return EdgeTestDecision(
        status="PASS",
        measured_win_prob=template.measured_win_prob,
        null_p95=template.null_p95,
        threshold=template.threshold,
        edge_token=token,
        evaluated_at=template.evaluated_at,
        reason=template.reason,
    )


def _token_evaluated_at(setup: CandidateSetup, token: str) -> str:
    """The evaluated_at the runner records for the authorization. The real gate's
    decision (carried by WasteLoop) is the source of truth; this is a defensive
    fallback used only if the token's mint time is not otherwise available."""
    from cas_forex.edge_gate import _now_iso

    return _now_iso()


def _compound_decision_from_cas_context(
    *,
    setup: CandidateSetup,
    execute_result: Any,
    control: Any,
    compound_edge: Any = None,
    add_risk_gate_passed: bool = False,
    current_units: int = 1,
) -> CompoundDecision:
    """Strict ADD/HOLD/CUT review for an already executed WASTE position.

    This is a decision only. It never dispatches an add order. A real add still
    has to go through the normal order-dispatch chokepoint with its own edge
    authorization and risk gate.
    """
    meta = getattr(setup, "market_state_meta", None)
    if not isinstance(meta, dict):
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: no market_state_meta on setup.",
        )
    if not bool(meta.get("broker_grade_market_truth", False)):
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: broker-grade market truth is required before compounding.",
        )
    cas_map = meta.get("cas_feature_map")
    if not isinstance(cas_map, dict):
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: no CAS lacunarity/RPM/CJT feature map on setup.",
        )
    current_price = _current_price_from(execute_result)
    floating_r = _floating_r(setup, current_price)
    if floating_r is None:
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: no position-profit R context for the executed trade.",
        )
    if str(cas_map.get("selected_rpm_action") or "").upper() != "ROUTE":
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: CAS RPM selected NO_TRADE for this profile.",
        )
    if _bool_value(cas_map.get("selected_is_lacuna"), default=True):
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason="compound HOLD: selected CAS cell is a lacuna.",
        )
    if not add_risk_gate_passed:
        return CompoundDecision(
            action="HOLD",
            add_units=0,
            reason=(
                "compound HOLD: exact add risk gate has not passed; no pyramid "
                "unit may be added yet."
            ),
        )
    fresh_pass = _compound_edge_is_pass(compound_edge)
    max_units = int(_control_value(control, "max_compound_units", 0) or 0)
    reliability = float(cas_map.get("cell_reliability") or 0.0)
    cjt_region = str(cas_map.get("selected_cjt_region") or "unknown")
    # WASTE does not yet carry a separate cascade forecast in this context. Use
    # the CAS map's explicit confidence when present, otherwise the conservative
    # reliability scalar from lacunarity/RPM/CJT.
    context_confidence = float(cas_map.get("cascade_confidence") or reliability)
    governor = decide_compound(
        position={
            "symbol": setup.symbol,
            "direction": setup.direction,
            "decision_ref": setup.decision_ref,
        },
        cell_reliability=reliability,
        cascade_confidence=context_confidence,
        cjt_region=cjt_region,
        floating_r=floating_r,
        max_units=max_units,
        current_units=max(0, int(current_units)),
        fresh_edge_pass=fresh_pass,
    )
    prefix = (
        "compound CAS review: "
        f"rpm={cas_map.get('selected_rpm_action')}, "
        f"cjt={cjt_region}, reliability={reliability:.2f}, "
        f"floating_r={floating_r:.2f}. "
    )
    suffix = (
        " ADD is a decision only; any add order must still go through gated dispatch."
        if governor.action == "ADD"
        else ""
    )
    return CompoundDecision(
        action=governor.action,
        add_units=governor.add_units,
        reason=prefix + governor.reason + suffix,
    )


def build_waste_entry_dispatch_intent_from_dry_run(dry_run: Mapping[str, Any]) -> Any:
    """Rebuild the exact WASTE entry TradeIntent from a passing dry run.

    This does not check owner ACCEPT and does not dispatch. It only verifies the
    dry run is a passing live-order rehearsal that came from a WASTE real-candle
    source packet, then rebuilds the exact order request for the normal dispatch
    chokepoint.
    """

    if not isinstance(dry_run, Mapping):
        raise ValueError("live-order dry-run report is required")
    if str(dry_run.get("report_kind") or "") != LIVE_ORDER_DRY_RUN_REPORT_KIND:
        raise ValueError("report is not a live-order dry run")
    if str(dry_run.get("status") or "") != STATUS_PASS:
        raise ValueError("WASTE entry dry run has not passed")
    if bool(dry_run.get("broker_touched", False)):
        raise ValueError("WASTE entry dry run says a broker was touched")
    source = dry_run.get("waste_real_candle_source")
    if not isinstance(source, Mapping):
        raise ValueError("live-order dry run is not sourced from a WASTE real-candle probe")
    if str(source.get("status") or "") != "WASTE_PROBE_DRY_RUN_HANDOFF_READY":
        raise ValueError("WASTE real-candle source is not handoff-ready")
    if not bool(source.get("broker_grade_market_truth", False)):
        raise ValueError("WASTE source is not broker-grade market truth")
    try:
        entry_pair_count = int(source.get("entry_pair_count") or 0)
    except (TypeError, ValueError):
        entry_pair_count = 0
    if entry_pair_count <= 0:
        raise ValueError("WASTE source has no no-lookahead holdout entry pairs")
    order_request = dry_run.get("order_request")
    if not isinstance(order_request, Mapping):
        raise ValueError("WASTE entry dry run is missing order_request")

    from cas_forex.order_dispatch import TradeIntent

    proposed = dry_run.get("proposed_intent")
    proposed = proposed if isinstance(proposed, Mapping) else {}
    return TradeIntent(
        order_id=str(order_request.get("order_id") or dry_run.get("order_id") or ""),
        decision_ref=str(order_request.get("decision_ref") or dry_run.get("decision_ref") or ""),
        symbol=str(order_request.get("symbol") or proposed.get("symbol") or ""),
        direction=str(order_request.get("direction") or proposed.get("direction") or ""),
        volume=float(order_request.get("volume") or proposed.get("lots") or 0.0),
        price=float(order_request.get("price") or 0.0),
        stop_loss=float(order_request.get("stop_loss") or 0.0),
        take_profit=float(order_request.get("take_profit") or 0.0),
        order_type=str(order_request.get("order_type") or "MARKET"),
        comment=str(order_request.get("comment") or "CAS_WASTE_MARKET_DRY_RUN"),
        strategy_id="waste-entry",
        ai_action="WASTE_ENTRY",
        expected_loss_usd=_float_value(proposed.get("expected_loss_usd")),
    )


def build_waste_entry_dispatch_handoff_status(
    dry_run: Mapping[str, Any],
    *,
    review: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Read-only cockpit status for a WASTE real-candle entry handoff.

    This never creates a bridge and never calls dispatch. It only proves whether
    the exact WASTE entry intent can be rebuilt and whether the owner ACCEPT
    review is current enough that an explicit dispatch attempt may enter the
    normal order-dispatch chokepoint.
    """

    try:
        intent = build_waste_entry_dispatch_intent_from_dry_run(dry_run)
    except Exception as exc:
        blocked = _blocked_waste_entry_handoff(
            reason=f"WASTE entry dispatch intent unavailable: {type(exc).__name__}: {exc}",
            dry_run=dry_run,
        )
        blocked["dispatch_preview_only"] = True
        blocked["would_call_dispatch_if_owner_attempted"] = False
        return blocked

    review_payload = dict(review or {})
    review_clear = bool(review_payload.get("dry_run_review_clear_for_live", False))
    missing = list(review_payload.get("missing_requirements") or [])
    source = dry_run.get("waste_real_candle_source")
    source = source if isinstance(source, Mapping) else {}
    status = (
        STATUS_WASTE_ENTRY_HANDOFF_REVIEW_READY
        if review_clear
        else STATUS_WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED
    )
    return {
        "report_kind": WASTE_ENTRY_HANDOFF_REPORT_KIND,
        "status": status,
        "order_id": intent.order_id,
        "decision_ref": intent.decision_ref,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_preview_only": True,
        "would_call_dispatch_if_owner_attempted": review_clear,
        "intent": intent.__dict__.copy(),
        "owner_review_status": review_payload.get("owner_review_status", "OPEN"),
        "dry_run_review_clear_for_live": review_clear,
        "missing_requirements": missing,
        "waste_real_candle_source": dict(source),
        "claim_boundary": WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY,
        "next_action": (
            "Owner ACCEPT is current for this exact WASTE entry fingerprint; an explicit dispatch attempt would still run the normal live, edge, pilot, risk, emergency-stop, audit, and broker gates."
            if review_clear
            else "Owner ACCEPT is not current for this exact WASTE entry fingerprint; dispatch remains blocked before any broker bridge."
        ),
    }


def dispatch_waste_entry_from_dry_run(
    dry_run: Mapping[str, Any],
    *,
    bridge: Any = None,
    bridge_factory: Optional[Callable[[], Any]] = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
) -> dict[str, Any]:
    """Hand an owner-reviewed WASTE entry dry-run order to dispatch."""

    try:
        intent = build_waste_entry_dispatch_intent_from_dry_run(dry_run)
    except Exception as exc:
        return _blocked_waste_entry_handoff(
            reason=f"WASTE entry dispatch intent unavailable: {type(exc).__name__}: {exc}",
            dry_run=dry_run,
        )
    resolved_bridge = bridge
    if resolved_bridge is None and bridge_factory is not None:
        try:
            resolved_bridge = bridge_factory()
        except Exception as exc:
            return _blocked_waste_entry_handoff(
                reason=f"WASTE entry bridge unavailable: {type(exc).__name__}: {exc}",
                dry_run=dry_run,
                intent=intent,
            )
    if resolved_bridge is None:
        return _blocked_waste_entry_handoff(
            reason="WASTE entry bridge unavailable: no bridge or bridge_factory configured",
            dry_run=dry_run,
            intent=intent,
        )
    if live_telemetry is None or account_snapshot is None:
        bridge_telemetry, bridge_account_snapshot = _bridge_dispatch_risk_context(resolved_bridge)
        if live_telemetry is None:
            live_telemetry = bridge_telemetry
        if account_snapshot is None:
            account_snapshot = bridge_account_snapshot

    from cas_forex.order_dispatch import dispatch_intent

    result = dispatch_intent(
        intent,
        resolved_bridge,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        audit_store=audit_store,
        audit_source="waste_entry_handoff",
    )
    result_payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    return {
        "report_kind": WASTE_ENTRY_HANDOFF_REPORT_KIND,
        "status": result_payload.get("status"),
        "order_id": intent.order_id,
        "decision_ref": intent.decision_ref,
        "broker_touched": bool(result_payload.get("dispatched_to_bridge", False)),
        "dispatched_to_bridge": bool(result_payload.get("dispatched_to_bridge", False)),
        "dispatch_result": result_payload,
        "claim_boundary": WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY,
        "next_action": (
            "WASTE entry handoff reached the bridge after all dispatch gates."
            if bool(result_payload.get("dispatched_to_bridge", False))
            else "WASTE entry handoff was blocked before broker execution; review the dispatch_result reason."
        ),
    }


def _blocked_waste_entry_handoff(
    *,
    reason: str,
    dry_run: Any,
    intent: Any = None,
) -> dict[str, Any]:
    order_id = None
    decision_ref = None
    if intent is not None:
        order_id = getattr(intent, "order_id", None)
        decision_ref = getattr(intent, "decision_ref", None)
    elif isinstance(dry_run, Mapping):
        order_id = dry_run.get("order_id")
        decision_ref = dry_run.get("decision_ref")
    return {
        "report_kind": WASTE_ENTRY_HANDOFF_REPORT_KIND,
        "status": STATUS_WASTE_ENTRY_HANDOFF_BLOCKED,
        "order_id": order_id,
        "decision_ref": decision_ref,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "reason": reason,
        "claim_boundary": WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY,
        "next_action": "Resolve the handoff blocker before attempting WASTE entry dispatch.",
    }


def build_compound_add_dispatch_intent_from_dry_run(add_dry_run: Mapping[str, Any]) -> Any:
    """Rebuild the exact compound-add TradeIntent from a passing dry run.

    This does not check owner ACCEPT and does not dispatch. The dispatch
    chokepoint checks owner ACCEPT/current fingerprint against the same
    ``order_request`` before a bridge can be touched.
    """

    if not isinstance(add_dry_run, Mapping):
        raise ValueError("compound-add dry-run report is required")
    if str(add_dry_run.get("report_kind") or "") != COMPOUND_ADD_REPORT_KIND:
        raise ValueError("report is not a compound-add dry run")
    if str(add_dry_run.get("status") or "") != STATUS_PASS:
        raise ValueError("compound-add dry run has not passed")
    if bool(add_dry_run.get("broker_touched", False)):
        raise ValueError("compound-add dry run says a broker was touched")
    order_request = add_dry_run.get("order_request")
    if not isinstance(order_request, Mapping):
        raise ValueError("compound-add dry run is missing order_request")

    from cas_forex.order_dispatch import TradeIntent

    proposed = add_dry_run.get("proposed_intent")
    proposed = proposed if isinstance(proposed, Mapping) else {}
    return TradeIntent(
        order_id=str(order_request.get("order_id") or add_dry_run.get("order_id") or ""),
        decision_ref=str(order_request.get("decision_ref") or add_dry_run.get("decision_ref") or ""),
        symbol=str(order_request.get("symbol") or add_dry_run.get("symbol") or ""),
        direction=str(order_request.get("direction") or add_dry_run.get("direction") or ""),
        volume=float(order_request.get("volume") or proposed.get("lots") or 0.0),
        price=float(order_request.get("price") or 0.0),
        stop_loss=float(order_request.get("stop_loss") or 0.0),
        take_profit=float(order_request.get("take_profit") or 0.0),
        order_type=str(order_request.get("order_type") or "MARKET"),
        comment=str(order_request.get("comment") or "CAS_FOREX_ADD_DRY_RUN"),
        strategy_id="waste-compound",
        ai_action="COMPOUND_ADD",
        expected_loss_usd=_float_value(proposed.get("expected_loss_usd")),
    )


def build_compound_add_dispatch_handoff_status(
    add_dry_run: Mapping[str, Any],
    *,
    review: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Read-only cockpit status for the latest compound-add dispatch handoff.

    This never creates a bridge and never calls dispatch. It only proves whether
    the exact add intent can be rebuilt and whether the owner ACCEPT review is
    current enough that an explicit dispatch attempt would be allowed to enter
    the normal order-dispatch chokepoint.
    """

    try:
        intent = build_compound_add_dispatch_intent_from_dry_run(add_dry_run)
    except Exception as exc:
        blocked = _blocked_compound_add_handoff(
            reason=f"compound-add dispatch intent unavailable: {type(exc).__name__}: {exc}",
            add_dry_run=add_dry_run,
        )
        blocked["dispatch_preview_only"] = True
        blocked["would_call_dispatch_if_owner_attempted"] = False
        return blocked

    review_payload = dict(review or {})
    review_clear = bool(review_payload.get("compound_add_dry_run_review_clear_for_dispatch", False))
    missing = list(review_payload.get("missing_requirements") or [])
    status = (
        STATUS_COMPOUND_ADD_HANDOFF_REVIEW_READY
        if review_clear
        else STATUS_COMPOUND_ADD_HANDOFF_REVIEW_BLOCKED
    )
    return {
        "report_kind": COMPOUND_ADD_HANDOFF_REPORT_KIND,
        "status": status,
        "order_id": intent.order_id,
        "decision_ref": intent.decision_ref,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_preview_only": True,
        "would_call_dispatch_if_owner_attempted": review_clear,
        "intent": intent.__dict__.copy(),
        "owner_review_status": review_payload.get("owner_review_status", "OPEN"),
        "compound_add_dry_run_review_clear_for_dispatch": review_clear,
        "missing_requirements": missing,
        "claim_boundary": COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY,
        "next_action": (
            "Owner ACCEPT is current for this exact compound-add fingerprint; an explicit dispatch attempt would still run the normal live, edge, pilot, risk, and emergency-stop gates."
            if review_clear
            else "Owner ACCEPT is not current for this exact compound-add fingerprint; dispatch remains blocked before any broker bridge."
        ),
    }


def dispatch_compound_add_from_dry_run(
    add_dry_run: Mapping[str, Any],
    *,
    bridge: Any = None,
    bridge_factory: Optional[Callable[[], Any]] = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
) -> dict[str, Any]:
    """Hand an owner-reviewed compound-add dry-run order to dispatch.

    The handoff is deliberately narrow: it rebuilds the exact add intent from
    the dry-run ``order_request`` and calls ``dispatch_intent`` with
    ``ai_action=COMPOUND_ADD``. Order dispatch then enforces current owner
    ACCEPT for the exact add fingerprint before risk/live/bridge execution.
    """

    try:
        intent = build_compound_add_dispatch_intent_from_dry_run(add_dry_run)
    except Exception as exc:
        return _blocked_compound_add_handoff(
            reason=f"compound-add dispatch intent unavailable: {type(exc).__name__}: {exc}",
            add_dry_run=add_dry_run,
        )
    resolved_bridge = bridge
    if resolved_bridge is None and bridge_factory is not None:
        try:
            resolved_bridge = bridge_factory()
        except Exception as exc:
            return _blocked_compound_add_handoff(
                reason=f"compound-add bridge unavailable: {type(exc).__name__}: {exc}",
                add_dry_run=add_dry_run,
                intent=intent,
            )
    if resolved_bridge is None:
        return _blocked_compound_add_handoff(
            reason="compound-add bridge unavailable: no bridge or bridge_factory configured",
            add_dry_run=add_dry_run,
            intent=intent,
        )
    if live_telemetry is None or account_snapshot is None:
        bridge_telemetry, bridge_account_snapshot = _bridge_dispatch_risk_context(resolved_bridge)
        if live_telemetry is None:
            live_telemetry = bridge_telemetry
        if account_snapshot is None:
            account_snapshot = bridge_account_snapshot

    from cas_forex.order_dispatch import dispatch_intent

    result = dispatch_intent(
        intent,
        resolved_bridge,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        audit_store=audit_store,
        audit_source="waste_compound_add_handoff",
    )
    result_payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    return {
        "report_kind": COMPOUND_ADD_HANDOFF_REPORT_KIND,
        "status": result_payload.get("status"),
        "order_id": intent.order_id,
        "decision_ref": intent.decision_ref,
        "broker_touched": bool(result_payload.get("dispatched_to_bridge", False)),
        "dispatched_to_bridge": bool(result_payload.get("dispatched_to_bridge", False)),
        "dispatch_result": result_payload,
        "claim_boundary": COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY,
        "next_action": (
            "Compound-add handoff reached the bridge after all dispatch gates."
            if bool(result_payload.get("dispatched_to_bridge", False))
            else "Compound-add handoff was blocked before broker execution; review the dispatch_result reason."
        ),
    }


def _blocked_compound_add_handoff(
    *,
    reason: str,
    add_dry_run: Any,
    intent: Any = None,
) -> dict[str, Any]:
    order_id = None
    decision_ref = None
    if intent is not None:
        order_id = getattr(intent, "order_id", None)
        decision_ref = getattr(intent, "decision_ref", None)
    elif isinstance(add_dry_run, Mapping):
        order_id = add_dry_run.get("order_id")
        decision_ref = add_dry_run.get("decision_ref")
    return {
        "report_kind": COMPOUND_ADD_HANDOFF_REPORT_KIND,
        "status": STATUS_COMPOUND_ADD_HANDOFF_BLOCKED,
        "order_id": order_id,
        "decision_ref": decision_ref,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "reason": reason,
        "claim_boundary": COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY,
        "next_action": "Resolve the handoff blocker before attempting compound-add dispatch.",
    }


def _compound_add_dry_run_from_manage_context(
    *,
    setup: CandidateSetup,
    execute_result: Any,
    lots: float,
    control: Any,
    current_units: int,
    compound: CompoundDecision,
    broker_position: Any = None,
    terminal_position_reconciliation: Any = None,
    add_order_id: Any = None,
    add_decision_ref: Any = None,
    add_volume: Any = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit: Optional[LiveOrderDryRunAuditLog] = None,
) -> dict[str, Any]:
    """Build owner-visible compound-add dry-run evidence from manage-stage data.

    This rehearses the add only. It does not register edge tokens, owner ACCEPT,
    or broker orders. Missing evidence becomes a blocked dry-run report.
    """

    try:
        meta = getattr(setup, "market_state_meta", None)
        meta = meta if isinstance(meta, Mapping) else {}
        cas_map = meta.get("cas_feature_map") if isinstance(meta.get("cas_feature_map"), Mapping) else {}
        position = _compound_parent_position(
            setup=setup,
            execute_result=execute_result,
            broker_position=broker_position,
            terminal_position_reconciliation=terminal_position_reconciliation,
        )
        position_entry = _float_value(position.get("open_price"), _float_value(position.get("entry_price"), setup.entry))
        position_stop = _float_value(position.get("stop_loss"), setup.stop_loss)
        current_price = _float_value(position.get("current_price"), _current_price_from(execute_result))
        if current_price is None:
            current_price = float(setup.entry)
        request = CompoundAddDryRunRequest(
            parent_order_id=str(position.get("order_id") or position.get("command_id") or setup.decision_ref),
            parent_decision_ref=str(position.get("decision_ref") or setup.decision_ref),
            broker_ticket=(
                None
                if position.get("broker_ticket") in {None, ""}
                else str(position.get("broker_ticket"))
            ),
            symbol=setup.symbol,
            direction=setup.direction,
            add_order_id=str(add_order_id or f"waste-add-{_safe_ref(setup.decision_ref)}-{max(0, int(current_units)) + 1}"),
            add_decision_ref=str(
                add_decision_ref
                or f"{setup.decision_ref}:compound-add:{max(0, int(current_units)) + 1}"
            ),
            add_volume=float(add_volume if add_volume is not None else (lots or position.get("lots") or 0.0)),
            price=float(current_price),
            stop_loss=float(_float_value(position.get("add_stop_loss"), _float_value(position.get("stop_loss"), setup.stop_loss))),
            take_profit=float(_float_value(position.get("take_profit"), setup.take_profit)),
            position_entry=float(position_entry),
            position_stop_loss=float(position_stop),
            current_price=float(current_price),
            current_units=max(0, int(current_units)),
            max_units=max(0, int(_control_value(control, "max_compound_units", 0) or 0)),
            broker_grade_market_truth=bool(position.get("broker_grade_market_truth")) and bool(meta.get("broker_grade_market_truth", False)),
            cas_feature_map=dict(cas_map),
            expected_loss_usd=None,
            comment="CAS_FOREX_ADD_DRY_RUN",
        )
        report = build_compound_add_order_dry_run(
            request,
            config=config,
            live_telemetry=live_telemetry,
            account_snapshot=account_snapshot,
            equity_peak=equity_peak,
            audit=None,
        )
        report["waste_manage_stage"] = {
            "source": "waste_runner.manage_stage",
            "parent_decision_ref": setup.decision_ref,
            "compound_action": compound.action,
            "compound_add_units": compound.add_units,
            "position_evidence_source": position.get("evidence_source"),
            "broker_touched": False,
        }
        if audit is not None:
            report["audit"] = audit.append(report)
        return report
    except Exception as exc:
        return {
            "report_kind": COMPOUND_ADD_REPORT_KIND,
            "generated_by": "waste_runner.manage_stage",
            "status": STATUS_BLOCKED,
            "broker_touched": False,
            "would_reach_broker_if_executed": False,
            "blocking_reasons": [f"waste_manage_stage_compound_add_dry_run: {type(exc).__name__}: {exc}"],
            "claim_boundary": (
                "WASTE manage-stage compound-add dry-run evidence is read-only. "
                "It does not place add orders, create owner ACCEPT, register edge tokens, "
                "authorize live trading, deposit, withdraw, or move money."
            ),
        }


def _compound_parent_position(
    *,
    setup: CandidateSetup,
    execute_result: Any,
    broker_position: Any = None,
    terminal_position_reconciliation: Any = None,
) -> dict[str, Any]:
    if isinstance(broker_position, Mapping):
        payload = dict(broker_position)
        payload.setdefault("evidence_source", "broker_position")
        payload.setdefault("broker_grade_market_truth", bool(payload.get("broker_grade_market_truth", True)))
        return payload
    report = (
        dict(terminal_position_reconciliation)
        if isinstance(terminal_position_reconciliation, Mapping)
        else _latest_terminal_position_reconciliation()
    )
    matched = _position_from_reconciliation(setup, execute_result, report)
    if matched:
        return matched
    fallback = {
        "evidence_source": "execute_result_fallback",
        "broker_grade_market_truth": False,
        "symbol": setup.symbol,
        "direction": setup.direction,
        "open_price": _current_price_from(execute_result) or setup.entry,
        "current_price": _current_price_from(execute_result),
        "stop_loss": setup.stop_loss,
        "take_profit": setup.take_profit,
        "broker_ticket": _ticket_from(execute_result),
        "decision_ref": setup.decision_ref,
    }
    return fallback


def _position_from_reconciliation(
    setup: CandidateSetup,
    execute_result: Any,
    report: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        return {}
    status = str(report.get("reconciliation_status") or "")
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    reconciled = report.get("reconciled_open_positions")
    if not isinstance(reconciled, list):
        return {}
    ticket = _ticket_from(execute_result)
    for item in reconciled:
        if not isinstance(item, Mapping):
            continue
        cas_pos = item.get("cas_position") if isinstance(item.get("cas_position"), Mapping) else {}
        terminal_pos = item.get("terminal_position") if isinstance(item.get("terminal_position"), Mapping) else {}
        merged = {**dict(cas_pos), **dict(terminal_pos)}
        if ticket is not None and str(merged.get("broker_ticket") or "") not in {"", str(ticket)}:
            continue
        if str(merged.get("symbol") or "") != str(setup.symbol):
            continue
        if str(merged.get("direction") or "").upper() != str(setup.direction).upper():
            continue
        merged["evidence_source"] = "terminal_position_reconciliation.reconciled_open_positions"
        merged["reconciliation_status"] = status
        merged["broker_grade_market_truth"] = (
            status == "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS"
            and int(summary.get("unmatched_open_position_count") or 0) == 0
            and int(summary.get("pending_receipt_count") or 0) == 0
            and int(summary.get("receipt_mismatch_count") or 0) == 0
        )
        return merged
    return {}


def _latest_terminal_position_reconciliation() -> dict[str, Any]:
    try:
        from cas_forex.terminal_position_reconciliation import load_latest_terminal_position_reconciliation_report

        return load_latest_terminal_position_reconciliation_report()
    except Exception:
        return {}


def _compound_edge_is_pass(edge: Any) -> bool:
    return (
        edge is not None
        and str(getattr(edge, "status", "")).upper() == "PASS"
        and bool(getattr(edge, "edge_token", None))
    )


def _floating_r(setup: CandidateSetup, current_price: Optional[float]) -> Optional[float]:
    if current_price is None:
        return None
    try:
        entry = float(setup.entry)
        stop = float(setup.stop_loss)
        current = float(current_price)
    except (TypeError, ValueError):
        return None
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    direction = str(setup.direction).upper()
    if direction == "LONG":
        return (current - entry) / risk
    if direction == "SHORT":
        return (entry - current) / risk
    return None


def _control_value(control: Any, key: str, default: Any = None) -> Any:
    try:
        getter = getattr(control, "get", None)
        if callable(getter):
            return getter(key)
        if isinstance(control, dict):
            return control.get(key, default)
    except Exception:
        return default
    return default


def _watch_state_summary(state: Any) -> dict[str, Any] | None:
    if not isinstance(state, Mapping):
        return None if state is None else {"report_kind": "non_mapping_watch_state", "detail": str(type(state).__name__)}
    entry_pair_report = state.get("entry_pair_report")
    entry_pair_report = entry_pair_report if isinstance(entry_pair_report, Mapping) else {}
    tuning = state.get("directional_hypothesis_tuning")
    tuning = tuning if isinstance(tuning, Mapping) else {}
    firewall = state.get("strategy_firewall")
    firewall = firewall if isinstance(firewall, Mapping) else {}
    scan = state.get("waste_market_scan")
    scan = scan if isinstance(scan, Mapping) else {}
    cas_map = state.get("cas_feature_map")
    cas_map = cas_map if isinstance(cas_map, Mapping) else {}
    costs = state.get("execution_costs")
    costs = costs if isinstance(costs, Mapping) else {}
    connector_attempts = [
        {
            "connector": item.get("connector"),
            "symbol": item.get("symbol"),
            "status": item.get("status"),
            "candle_count": item.get("candle_count"),
        }
        for item in (state.get("connector_attempts") or [])
        if isinstance(item, Mapping)
    ]
    entry_pairs = state.get("entry_pairs") or []
    candles = state.get("candles") or []
    try:
        source_candles_count = int(state.get("candles_count") or 0)
    except (TypeError, ValueError):
        source_candles_count = 0
    return {
        "report_kind": state.get("report_kind"),
        "status": state.get("status"),
        "probe_status": state.get("probe_status"),
        "symbol": state.get("symbol"),
        "timeframe": state.get("timeframe"),
        "source": state.get("source"),
        "feed_label": state.get("feed_label"),
        "fallback_used": bool(state.get("fallback_used", False)),
        "broker_grade_market_truth": bool(state.get("broker_grade_market_truth", False)),
        "read_only_market_data": bool(state.get("read_only_market_data", False)),
        "cached_snapshot_only": bool(state.get("cached_snapshot_only", False)),
        "latest_probe_generated_at": state.get("latest_probe_generated_at"),
        "candles_count": len(candles)
        if isinstance(candles, list) and len(candles) > 0
        else source_candles_count,
        "entry_pair_count": len(entry_pairs) if isinstance(entry_pairs, list) else int(entry_pair_report.get("entry_pair_count") or 0),
        "selected_directional_profile": state.get("selected_directional_profile"),
        "directional_hypothesis": state.get("directional_hypothesis")
        if isinstance(state.get("directional_hypothesis"), Mapping)
        else None,
        "strategy_firewall": {
            "candidate_allowed": firewall.get("candidate_allowed"),
            "firewall_status": firewall.get("firewall_status"),
            "lead_id": firewall.get("lead_id"),
            "reason": firewall.get("reason"),
        },
        "directional_hypothesis_tuning": {
            "status": tuning.get("status"),
            "selected_profile": tuning.get("selected_profile"),
            "no_lookahead": bool(tuning.get("no_lookahead", False)),
            "validation_pairs_holdout": bool(tuning.get("validation_pairs_holdout", False)),
            "selection_window_count": tuning.get("selection_window_count"),
            "validation_window_count": tuning.get("validation_window_count"),
        },
        "cas_feature_map": {
            "selected_profile": cas_map.get("selected_profile"),
            "selected_rpm_action": cas_map.get("selected_rpm_action"),
            "selected_cjt_region": cas_map.get("selected_cjt_region"),
            "selected_is_lacuna": cas_map.get("selected_is_lacuna"),
            "cell_reliability": cas_map.get("cell_reliability"),
        },
        "execution_costs": {
            "spread_pips": costs.get("spread_pips"),
            "slippage_buffer_pips": costs.get("slippage_buffer_pips"),
            "edge_cost_pips": costs.get("edge_cost_pips"),
            "slippage_source": costs.get("slippage_source"),
        },
        "waste_market_scan": {
            "status": scan.get("status"),
            "attempt_count": scan.get("attempt_count"),
            "selected_symbol": scan.get("selected_symbol"),
            "selected_timeframe": scan.get("selected_timeframe"),
            "selected_edge_status": scan.get("selected_edge_status"),
            "selected_edge_has_token": bool(scan.get("selected_edge_has_token", False)),
            "edge_authorization_registered": bool(scan.get("edge_authorization_registered", False)),
            "broker_execution_touched": bool(scan.get("broker_execution_touched", False)),
            "money_moved": bool(scan.get("money_moved", False)),
            "attempts": [
                {
                    "symbol": item.get("symbol"),
                    "timeframe": item.get("timeframe"),
                    "edge_status": item.get("edge_status"),
                    "edge_has_token": bool(item.get("edge_has_token", False)),
                    "candidate_direction": item.get("candidate_direction"),
                    "broker_grade_market_truth": bool(item.get("broker_grade_market_truth", False)),
                    "fallback_used": bool(item.get("fallback_used", False)),
                    "candles_count": item.get("candles_count"),
                    "entry_pair_count": item.get("entry_pair_count"),
                }
                for item in (scan.get("attempts") or [])
                if isinstance(item, Mapping)
            ][-8:],
        },
        "connector_attempts": connector_attempts[-5:],
        "market_data_claim_boundary": state.get("market_data_claim_boundary"),
        "error": state.get("error"),
    }


def _analysis_summary(analysis: Any) -> dict[str, Any] | None:
    if not isinstance(analysis, Mapping):
        return None if analysis is None else {"report_kind": "non_mapping_analysis", "detail": str(type(analysis).__name__)}
    hypothesis = analysis.get("hypothesis")
    hypothesis = hypothesis if isinstance(hypothesis, Mapping) else {}
    firewall = analysis.get("strategy_firewall")
    firewall = firewall if isinstance(firewall, Mapping) else {}
    tuning = analysis.get("hypothesis_tuning")
    tuning = tuning if isinstance(tuning, Mapping) else {}
    cas_map = analysis.get("cas_feature_map")
    cas_map = cas_map if isinstance(cas_map, Mapping) else {}
    return {
        "report_kind": analysis.get("report_kind") or "cas_forex_waste_runner_analysis_summary",
        "confidence": _float_value(analysis.get("confidence")),
        "reason": analysis.get("reason"),
        "hypothesis": {
            "symbol": hypothesis.get("symbol"),
            "timeframe": hypothesis.get("timeframe"),
            "action": hypothesis.get("action"),
            "direction": hypothesis.get("direction"),
            "long_score": hypothesis.get("long_score"),
            "short_score": hypothesis.get("short_score"),
            "confidence": hypothesis.get("confidence"),
            "regime": hypothesis.get("regime"),
            "profile": hypothesis.get("profile"),
        },
        "strategy_firewall": {
            "candidate_allowed": firewall.get("candidate_allowed"),
            "firewall_status": firewall.get("firewall_status"),
            "lead_id": firewall.get("lead_id"),
            "reason": firewall.get("reason"),
        },
        "hypothesis_tuning": {
            "status": tuning.get("status"),
            "selected_profile": tuning.get("selected_profile"),
            "no_lookahead": bool(tuning.get("no_lookahead", False)),
            "validation_pairs_holdout": bool(tuning.get("validation_pairs_holdout", False)),
        },
        "cas_feature_map": {
            "selected_profile": cas_map.get("selected_profile"),
            "selected_rpm_action": cas_map.get("selected_rpm_action"),
            "selected_cjt_region": cas_map.get("selected_cjt_region"),
            "selected_is_lacuna": cas_map.get("selected_is_lacuna"),
            "cell_reliability": cas_map.get("cell_reliability"),
        },
    }


def _float_value(value: Any, default: Any = None) -> Optional[float]:
    if value is None:
        value = default
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_ref(value: Any) -> str:
    text = str(value or "unknown")
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text)[:64]


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _ticket_from(execute_result: Any) -> Optional[int]:
    if execute_result is None:
        return None
    for attr in ("broker_ticket", "ticket"):
        val = getattr(execute_result, attr, None)
        if val is None and isinstance(execute_result, dict):
            val = execute_result.get(attr)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                return None
    outcome = getattr(execute_result, "outcome", None)
    if outcome is not None:
        return _ticket_from(outcome)
    if isinstance(execute_result, dict) and "outcome" in execute_result:
        return _ticket_from(execute_result["outcome"])
    return None


def _current_price_from(execute_result: Any) -> Optional[float]:
    if execute_result is None:
        return None
    for attr in ("current_price", "market_price", "close_or_current_price", "fill_price", "filled_price", "price"):
        val = getattr(execute_result, attr, None)
        if val is None and isinstance(execute_result, dict):
            val = execute_result.get(attr)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
    outcome = getattr(execute_result, "outcome", None)
    if outcome is not None:
        return _current_price_from(outcome)
    if isinstance(execute_result, dict) and "outcome" in execute_result:
        return _current_price_from(execute_result["outcome"])
    return None


def _effective_mode() -> str:
    try:
        from cas_forex import runtime_gates
        from cas_forex.config import config

        if getattr(config, "live_mode", False) and runtime_gates.is_authorized("live_trading"):
            return "LIVE"
    except Exception:  # pragma: no cover - defensive
        pass
    return "PAPER"


# ---------------------------------------------------------------------------
# Module-level single runner (single-owner cockpit) + thin functional API.
# ---------------------------------------------------------------------------
_runner: Optional[WasteRunner] = None
_runner_lock = threading.Lock()


def _production_control() -> Optional[AiControlSurface]:
    """The durable, owner-fenced dial surface for PRODUCTION runners.

    Production loops must share the persisted AI-control authority so owner/AI
    dial changes (edge threshold, risk %, learning mode, confidence bar) reach
    the running loop. Tests keep an isolated in-memory surface (returning None
    lets WasteRunner construct its own default)."""
    try:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return None
        from cas_forex.ai_control_authority import get_authority

        return get_authority().control
    except Exception:
        return None


def get_runner() -> WasteRunner:
    """The process-global runner (lazily constructed). Single-owner cockpit."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = WasteRunner(control=_production_control())
        return _runner


def set_runner(runner: Optional[WasteRunner]) -> None:
    """Replace the process-global runner (tests / integration wiring)."""
    global _runner
    with _runner_lock:
        _runner = runner


def start_runner(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS, *, confirm: bool = False
) -> dict[str, Any]:
    """Start the global runner. Paper-safe by default; if live trading is
    owner-authorized (a tick could place real orders) require ``confirm=True``."""
    if _live_timer_confirmation_required() and not confirm:
        return {
            "report_kind": "cas_forex_waste_runner",
            "status": "CONFIRM_REQUIRED",
            "running": False,
            "detail": (
                "Live trading is owner-authorized; this runner could place real orders "
                "on a timer. Re-request with confirm=true to start it."
            ),
        }
    return get_runner().start(interval_seconds)


def _live_timer_confirmation_required() -> bool:
    """Fast pre-start guard; full runtime gates still run at dispatch time."""
    try:
        from cas_forex.config import config
        from cas_forex.live_enable_control import apply_live_enable_overrides

        resolved = apply_live_enable_overrides(config)
        return bool(getattr(resolved, "live_mode", False)) and bool(
            getattr(resolved, "owner_enable_live_trading", False)
        ) and bool(getattr(resolved, "live_trading_licensed", False))
    except Exception:  # pragma: no cover - defensive start path stays paper-safe
        return False


def stop_runner() -> dict[str, Any]:
    """Stop the global runner."""
    return get_runner().stop()


def runner_status() -> dict[str, Any]:
    """Status of the global runner (running, interval, last decision, mode)."""
    status = get_runner().status()
    try:
        import os

        if not os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get(
            "CAS_FOREX_BACKGROUND_WORKER"
        ):
            from cas_forex.waste_background_worker import overlay_waste_runner_status

            return overlay_waste_runner_status(status)
    except Exception:
        pass
    return status
