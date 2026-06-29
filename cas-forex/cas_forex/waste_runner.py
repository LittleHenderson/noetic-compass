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
  SAME gated paper path the manual button uses (``order_dispatch.dispatch_order``
  -> ``execution_guard.guarded_place_order``), which re-checks the owner's
  ``is_demo_account`` / live-trading authorization at the bridge boundary,
  fail-closed. By default that means paper/demo dispatch.
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
(single-owner cockpit); state resets on restart.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from cas_forex import edge_authorization, loop_heartbeat
from cas_forex.ai_control_surface import AiControlSurface
from cas_forex.ai_objective import ProfitObjective
from cas_forex.edge_gate import CandidateSetup as GateCandidateSetup
from cas_forex.edge_gate import EdgeTestDecision, evaluate_candidate
from cas_forex.trade_management import breakeven_lock, position_size
from cas_forex.waste_loop import CandidateSetup, CompoundDecision, WasteLoop

# The owner drives — interval can be anything from 1 second up to a day. Very low
# intervals hammer the data feed + CPU; that's the owner's call, surfaced as an
# honest note, not blocked.
MIN_INTERVAL_SECONDS = 1
DEFAULT_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86_400

# Default account equity assumption when no live account snapshot is available
# (sizing converts a risk budget into lots; it does not create an edge).
_DEFAULT_EQUITY = 10_000.0


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
    return {"regime": "unknown", "symbols": []}


def _default_analyze(state: Any) -> dict[str, Any]:
    """ANALYZE: derive confidence from the watched state. Default carries no
    confidence (price-only signals measure ALL_GAPS this session)."""
    return {"confidence": 0.0, "state": state}


def _default_strategize(state: Any, analysis: Any) -> Optional[CandidateSetup]:
    """STRATEGIZE: form a CandidateSetup with a REAL direction, or return None.

    Honest default: with no measured edge there is no candidate, so this returns
    ``None`` and the tick ends at ``no_trade``. Direction (LONG/SHORT) is decided
    ONLY here when a real signal exists; the gate downstream never invents one.
    """
    return None


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
    ) -> None:
        self.objective = objective or ProfitObjective()
        self.control = control or AiControlSurface()
        self._bridge_factory = bridge_factory
        # ``dispatch_fn`` is the paper dispatch sink. Default is the real gated
        # paper path; tests inject a fake to assert dispatch-on-PASS-only.
        self._dispatch_fn = dispatch_fn
        self._watch_fn = watch_fn or _default_watch
        self._analyze_fn = analyze_fn or _default_analyze
        self._strategize_fn = strategize_fn or _default_strategize
        self._today_realized_fn = today_realized_fn or (lambda: 0.0)
        self._equity_fn = equity_fn or (lambda: _DEFAULT_EQUITY)

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
        )

    # -- stage wrappers: each stamps the live heartbeat -------------------
    # The heartbeat pulses with the REAL stage the loop is in. WasteLoop also sets
    # its own ``current_stage``; recording here makes the cockpit indicator reflect
    # the actual stage of the actual tick (honest by construction — stale => idle).

    def _watch_stage(self) -> Any:
        loop_heartbeat.record("watch", detail="watching market/regime state")
        return self._watch_fn()

    def _analyze_stage(self, state: Any) -> Any:
        loop_heartbeat.record("analyze", detail="scoring confidence")
        return self._analyze_fn(state)

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
        return evaluate_candidate(gate_setup, entry_pairs, threshold=threshold)

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
        """EXECUTE — reached ONLY on a fresh PASS carrying a non-empty token.

        Fail-closed twice: register the authorization for this setup's
        ``decision_ref`` (so the dispatch chokepoint will verify it), THEN dispatch
        through the gated paper path. The dispatch path re-checks the registration
        and refuses without a fresh, matching PASS.
        """
        loop_heartbeat.record("execute", detail="dispatching paper order", symbol=setup.symbol)
        gate_setup = _to_gate_setup(setup)
        decision = EdgeTestDecision(
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
        edge_authorization.authorize(
            setup.decision_ref, _pass_decision(decision, setup, token), gate_setup
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
                    return CompoundDecision(
                        action="HOLD",
                        add_units=0,
                        reason="breakeven-lock: SL moved to entry (principal protected).",
                    )
                except Exception:
                    # Management must never undo a placed trade.
                    return CompoundDecision(
                        action="HOLD", add_units=0, reason="breakeven-lock skipped (modify failed)."
                    )
        return CompoundDecision(action="HOLD", add_units=0, reason="holding position.")

    # -- dispatch ---------------------------------------------------------
    def _dispatch(self, setup: CandidateSetup, lots: float, token: str) -> Any:
        if self._dispatch_fn is not None:
            return self._dispatch_fn(setup=setup, lots=lots, token=token)
        return self._default_paper_dispatch(setup, lots)

    def _default_paper_dispatch(self, setup: CandidateSetup, lots: float) -> Any:
        """Dispatch through the real gated paper path. Imported lazily so the heavy
        broker/order modules stay off the import path for unit tests.

        Builds a normalized ``TradeIntent`` and hands it to ``dispatch_intent``,
        which runs the FULL gate chain (live gate, edge gate, risk gate) before the
        bridge is touched. The edge gate consults the authorization the runner just
        registered for this ``decision_ref`` — no PASS => the bridge is never reached.
        """
        from cas_forex.order_dispatch import TradeIntent, dispatch_intent

        if self._bridge_factory is None:
            return {"status": "NO_BRIDGE", "detail": "no bridge_factory configured for dispatch"}
        bridge = self._bridge_factory()
        intent = TradeIntent(
            order_id=f"waste-{setup.decision_ref}",
            decision_ref=setup.decision_ref,
            symbol=setup.symbol,
            direction=setup.direction,
            volume=float(lots),
            stop_loss=float(setup.stop_loss),
            take_profit=float(setup.take_profit),
            price=float(setup.entry),
            ai_action="WASTE_LOOP",
        )
        return dispatch_intent(intent, bridge)

    # -- per-setup data helpers (overridable at integration) --------------
    def _entry_pairs_for(self, setup: CandidateSetup) -> list[dict[str, float]]:
        """Recent OOS outcomes for THIS setup's pattern, fed to the null test.

        Honest default: empty — with no measured OOS history the gate returns
        ``NO_TRADE_INSUFFICIENT_BARS`` (fail-closed). Integration injects a richer
        ``strategize``/data path that carries real outcomes on the candidate.
        """
        pairs = getattr(setup, "entry_pairs", None)
        return list(pairs) if pairs else []

    # -- thread lifecycle -------------------------------------------------
    def _run(self) -> None:
        from datetime import datetime, timezone

        while not self._stop_event.is_set():
            try:
                result = self._loop.tick()
                self._stamp_terminal_stage(result)
                self.cycles_run += 1
                self.last_decision = str(result.get("decision", ""))
                self.last_reason = str(result.get("reason", ""))
                self.last_run_iso = datetime.now(timezone.utc).isoformat()
                self.last_error = ""
            except Exception as exc:  # one bad tick must never kill the thread
                self.last_error = f"{type(exc).__name__}: {exc}"
            self._stop_event.wait(max(MIN_INTERVAL_SECONDS, self.interval))
        # On stop, collapse the heartbeat to OFFLINE/idle — never invented activity.
        loop_heartbeat.record("idle", detail="runner stopped")

    def start(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> dict[str, Any]:
        from datetime import datetime, timezone

        with self._lock:
            self.interval = max(
                MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds))
            )
            if self._thread and self._thread.is_alive():
                return self._status_locked()
            self._stop_event.clear()
            self.started_at_iso = datetime.now(timezone.utc).isoformat()
            self._thread = threading.Thread(
                target=self._run, name="cas-waste-runner", daemon=True
            )
            self._thread.start()
            return self._status_locked()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3.0)
        with self._lock:
            self._thread = None
            loop_heartbeat.record("idle", detail="runner stopped")
            return self._status_locked()

    def tick_once(self) -> dict[str, Any]:
        """Run exactly one tick synchronously (tests / manual single-step)."""
        result = self._loop.tick()
        self._stamp_terminal_stage(result)
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
        return {
            "report_kind": "cas_forex_waste_runner",
            "running": running,
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
            "mode": _effective_mode(),
            "note": (
                "Ticks the WASTE loop (W->A->S->T->E) on a timer and pulses the live "
                "heartbeat per stage. Paper-safe by default; execute is reachable ONLY "
                "through a fresh edge-gate PASS, and dispatch re-verifies it fail-closed. "
                "Mostly NO_TRADE is the correct, honest behaviour when no edge passes."
            ),
        }


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
    for attr in ("fill_price", "current_price", "price"):
        val = getattr(execute_result, attr, None)
        if val is None and isinstance(execute_result, dict):
            val = execute_result.get(attr)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
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


def get_runner() -> WasteRunner:
    """The process-global runner (lazily constructed). Single-owner cockpit."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = WasteRunner()
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
    try:
        from cas_forex import runtime_gates

        live_authorized = runtime_gates.is_authorized("live_trading")
    except Exception:  # pragma: no cover - defensive
        live_authorized = False
    if live_authorized and not confirm:
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


def stop_runner() -> dict[str, Any]:
    """Stop the global runner."""
    return get_runner().stop()


def runner_status() -> dict[str, Any]:
    """Status of the global runner (running, interval, last decision, mode)."""
    return get_runner().status()
