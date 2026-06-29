"""WASTE loop controller — WATCH -> ANALYZE -> STRATEGIZE -> TEST -> EXECUTE.

This is the orchestrator that turns the no-edge verdict of this session into a
discipline: instead of trusting any static formula, the AI runs a fixed five-stage
cycle and is allowed to EXECUTE one and only one way — through a PASSED edge gate
carrying a fresh, non-empty edge token. Everything else terminates the tick at
``no_trade`` (or ``blocked`` on an internal fault), and the principal is never put
at risk on an unproven signal.

FAIL-CLOSED IS THE WHOLE POINT
------------------------------
``execute_fn`` is reachable from EXACTLY ONE branch of :meth:`WasteLoop.tick`:

    test_fn(setup) returns an EdgeTestDecision AND
        decision.status == 'PASS' AND
        decision.edge_token is a non-empty string

If any of those is false — a non-PASS status, a PASS with an empty/missing token,
``strategize_fn`` returning ``None``, or any injected stage raising — the loop does
NOT call ``execute_fn``. There is no other code path to the broker. The token that
the gate minted is the only key, and it is handed straight to ``execute_fn`` so the
executor can re-verify it at the broker boundary (fail-closed twice).

DEPENDENCY INJECTION
--------------------
The loop imports none of the in-flight stage modules at module load. Every stage is
a callable handed to the constructor, so the loop is unit-testable with plain fakes
and composes with the real watch/analyze/strategize/test/size/execute/manage
functions at integration time. This module only knows the SHAPE of the contracts
(:class:`CandidateSetup`, :class:`EdgeTestDecision`, :class:`CompoundDecision`,
:data:`AI_STAGES`), never the implementations.

The direction (LONG/SHORT) is decided ONLY inside ``strategize_fn``. The governors
that ``test_fn``/``size_fn``/``manage_fn`` wrap (lacunarity, RPM, CJT, cascade) gate
and size — they never predict direction here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Protocol

# ---------------------------------------------------------------------------
# AiStage — the UI heartbeat vocabulary.
# ---------------------------------------------------------------------------
# A string Literal-style enumeration kept as a plain tuple so callers (and the UI)
# can validate against it without importing typing.Literal machinery.
AI_STAGES = (
    "idle",
    "watch",
    "analyze",
    "strategize",
    "test",
    "execute",
    "compound",
    "locked",
    "no_trade",
    "blocked",
)

# Terminal stages a single tick can end on.
_TERMINAL_STAGES = ("execute", "no_trade", "blocked", "locked", "compound")


# ---------------------------------------------------------------------------
# Shared data contracts (plain dataclasses, field/type names per the spec).
# ---------------------------------------------------------------------------
@dataclass
class CandidateSetup:
    """A proposed trade. Direction is decided in STRATEGIZE and only there."""

    symbol: str
    timeframe: str
    direction: str  # 'LONG' | 'SHORT'
    entry: float
    stop_loss: float
    take_profit: float
    signal_strength: float
    regime: str
    decision_ref: str


@dataclass
class EdgeTestDecision:
    """Verdict of the null-test edge gate. Only status=='PASS' with a non-empty
    ``edge_token`` authorizes execution."""

    status: str  # PASS | NO_TRADE_NULL_FAILED | NO_TRADE_UNDERPOWERED | NO_TRADE_STALE_DATA | NO_TRADE_INSUFFICIENT_BARS
    measured_win_prob: float
    null_p95: float
    threshold: float
    edge_token: Optional[str]
    evaluated_at: str  # iso-utc
    reason: str


@dataclass
class CompoundDecision:
    """Post-execution money-management decision. Amplifies a confirmed edge only."""

    action: str  # 'ADD' | 'HOLD' | 'CUT'
    add_units: int
    reason: str


# The single status string that licenses a call to execute_fn.
PASS_STATUS = "PASS"


# ---------------------------------------------------------------------------
# Stage protocols (documentation of the injected callables' shapes).
# ---------------------------------------------------------------------------
class _WatchFn(Protocol):
    def __call__(self) -> Any: ...


class _AnalyzeFn(Protocol):
    def __call__(self, state: Any) -> Any: ...


class _StrategizeFn(Protocol):
    def __call__(self, state: Any, analysis: Any) -> Optional[CandidateSetup]: ...


class _TestFn(Protocol):
    def __call__(self, setup: CandidateSetup) -> EdgeTestDecision: ...


class _SizeFn(Protocol):
    def __call__(self, setup: CandidateSetup) -> float: ...


class _ExecuteFn(Protocol):
    def __call__(self, setup: CandidateSetup, lots: float, token: str) -> Any: ...


class _ManageFn(Protocol):
    def __call__(self, **kwargs: Any) -> str: ...


def _now_iso() -> str:
    try:
        from cas_forex.time_utils import utc_now

        return utc_now().isoformat()
    except Exception:  # pragma: no cover - defensive; tests inject their own clock
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def _is_pass(edge: Optional[EdgeTestDecision]) -> bool:
    """The ONLY predicate that licenses execution: PASS status + non-empty token.

    Kept as a single function so there is exactly one place in the codebase that
    decides whether the broker may be reached. Any change to the execution license
    happens here and nowhere else.
    """
    if edge is None:
        return False
    if getattr(edge, "status", None) != PASS_STATUS:
        return False
    token = getattr(edge, "edge_token", None)
    return isinstance(token, str) and token != ""


class WasteLoop:
    """The W->A->S->T->E orchestrator. Built with dependency injection; fail-closed.

    Construct with the stage callables. Call :meth:`tick` once per cycle. The loop
    runs WATCH -> ANALYZE -> STRATEGIZE -> TEST and only then, ONLY if the edge gate
    returned a fresh PASS with a non-empty token, calls ``execute_fn`` with that
    token. Optional ``manage_fn`` runs after a successful execute to drive the
    compound/hold/cut money-management step (it never creates an edge; it amplifies
    a confirmed one).
    """

    def __init__(
        self,
        watch_fn: _WatchFn,
        analyze_fn: _AnalyzeFn,
        strategize_fn: _StrategizeFn,
        test_fn: _TestFn,
        size_fn: _SizeFn,
        execute_fn: _ExecuteFn,
        manage_fn: Optional[_ManageFn] = None,
        objective: Any = None,
        control: Any = None,
    ) -> None:
        self.watch_fn = watch_fn
        self.analyze_fn = analyze_fn
        self.strategize_fn = strategize_fn
        self.test_fn = test_fn
        self.size_fn = size_fn
        self.execute_fn = execute_fn
        self.manage_fn = manage_fn
        # ``objective`` carries the pace target ($250/day); ``control`` is the owner
        # surface (e.g. is the loop allowed to run, threshold overrides). They are
        # opaque to the loop — read by the injected stages, not by the controller.
        self.objective = objective
        self.control = control
        self._stage: str = "idle"
        self._last_result: Optional[dict[str, Any]] = None

    # -- UI convenience ---------------------------------------------------
    def current_stage(self) -> str:
        """The stage the loop is currently / was last in (for the UI heartbeat)."""
        return self._stage

    @property
    def last_result(self) -> Optional[dict[str, Any]]:
        return self._last_result

    # -- internal ---------------------------------------------------------
    def _set_stage(self, stage: str, trace: List[str]) -> None:
        # Defensive: only ever publish a stage the UI vocabulary knows about.
        if stage not in AI_STAGES:  # pragma: no cover - guards programmer error
            stage = "blocked"
        self._stage = stage
        trace.append(stage)

    def _result(
        self,
        trace: List[str],
        decision: str,
        reason: str,
        setup: Optional[CandidateSetup] = None,
        edge: Optional[EdgeTestDecision] = None,
        execute_result: Any = None,
        compound: Optional[CompoundDecision] = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "stage_trace": list(trace),
            "decision": decision,
            "setup": setup,
            "edge": edge,
            "reason": reason,
            "execute_result": execute_result,
            "compound": compound,
            "evaluated_at": _now_iso(),
        }
        self._last_result = out
        return out

    # -- the loop ---------------------------------------------------------
    def tick(self, market_state: Any = None) -> dict[str, Any]:
        """Run one W->A->S->T->E cycle. Returns the trace + decision.

        ``decision`` is one of: 'EXECUTE', 'NO_TRADE', 'BLOCKED'. The ``stage_trace``
        always begins at 'watch' and ends at exactly one terminal stage. ``execute_fn``
        is called if and only if the edge gate returned PASS with a non-empty token.
        """
        trace: List[str] = []

        # ---- WATCH -----------------------------------------------------
        self._set_stage("watch", trace)
        try:
            state = market_state if market_state is not None else self.watch_fn()
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(trace, "BLOCKED", f"watch_fn failed: {type(exc).__name__}: {exc}")

        # ---- ANALYZE ---------------------------------------------------
        self._set_stage("analyze", trace)
        try:
            analysis = self.analyze_fn(state)
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(trace, "BLOCKED", f"analyze_fn failed: {type(exc).__name__}: {exc}")

        # ---- STRATEGIZE (decides direction, or None) -------------------
        self._set_stage("strategize", trace)
        try:
            setup = self.strategize_fn(state, analysis)
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(trace, "BLOCKED", f"strategize_fn failed: {type(exc).__name__}: {exc}")

        if setup is None:
            # No candidate this cycle — the AI is allowed to choose NO-TRADE.
            self._set_stage("no_trade", trace)
            return self._result(trace, "NO_TRADE", "strategize produced no candidate setup", setup=None)

        # ---- TEST (the edge gate) --------------------------------------
        self._set_stage("test", trace)
        try:
            edge = self.test_fn(setup)
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(
                trace, "BLOCKED", f"test_fn failed: {type(exc).__name__}: {exc}", setup=setup
            )

        # FAIL-CLOSED CHOKEPOINT: the one and only gate to execution.
        if not _is_pass(edge):
            status = getattr(edge, "status", "MISSING") if edge is not None else "MISSING"
            reason = getattr(edge, "reason", "") if edge is not None else "test_fn returned no decision"
            self._set_stage("no_trade", trace)
            return self._result(
                trace,
                "NO_TRADE",
                f"edge gate did not authorize ({status}): {reason}".strip(),
                setup=setup,
                edge=edge,
            )

        # From here: edge is a fresh PASS carrying a non-empty token.
        token = edge.edge_token  # guaranteed non-empty str by _is_pass
        assert isinstance(token, str) and token  # defensive contract restatement

        # ---- SIZE ------------------------------------------------------
        try:
            lots = self.size_fn(setup)
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(
                trace, "BLOCKED", f"size_fn failed: {type(exc).__name__}: {exc}", setup=setup, edge=edge
            )

        # ---- EXECUTE (token is mandatory and passed through) -----------
        self._set_stage("execute", trace)
        try:
            execute_result = self.execute_fn(setup, lots, token)
        except Exception as exc:
            self._set_stage("blocked", trace)
            return self._result(
                trace, "BLOCKED", f"execute_fn failed: {type(exc).__name__}: {exc}", setup=setup, edge=edge
            )

        # ---- COMPOUND (optional money management; amplifies only) ------
        compound: Optional[CompoundDecision] = None
        if self.manage_fn is not None:
            try:
                stage_or_decision = self.manage_fn(
                    setup=setup,
                    lots=lots,
                    edge=edge,
                    execute_result=execute_result,
                    objective=self.objective,
                    control=self.control,
                )
                if isinstance(stage_or_decision, CompoundDecision):
                    compound = stage_or_decision
            except Exception:  # management must never undo a placed trade
                compound = None

        return self._result(
            trace,
            "EXECUTE",
            f"PASS token authorized execution (win_prob={edge.measured_win_prob} "
            f">= threshold={edge.threshold}, beats null_p95={edge.null_p95})",
            setup=setup,
            edge=edge,
            execute_result=execute_result,
            compound=compound,
        )
