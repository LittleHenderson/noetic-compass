"""The CAS Forex AI operator — an always-on strategy desk.

Each tick the operator: (1) gathers the learning evidence (direction ledger,
outcome binding, current dials, recent cycles) and a manifest of the tools it
may use; (2) asks the ACTIVE language model (Claude when tokens remain, else the
free local fallback) for a structured decision; (3) applies the decision ONLY
through the owner-fenced control surface (``ai_control_authority.ai_adjust``),
which clamps every value to the owner's bounds. Every action is logged.

Hard boundary — the operator can ONLY move the AI dials the owner exposed
(edge threshold, risk %, symbols, sessions, confidence bar, learning mode,
compound units). It has NO path to the live-money gate, broker/owner ACCEPT,
deposits, withdrawals, payouts, or edge-token minting: those live outside the
control surface entirely, so it cannot reach them by construction. The trading
engine keeps running on local math regardless of what the operator decides.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS_PATH = REPO_ROOT / "runtime" / "ai-operator-actions.jsonl"

REPORT_KIND = "cas_forex_ai_operator"

CLAIM_BOUNDARY = (
    "The AI operator adjusts only the owner-fenced AI dials (edge threshold, "
    "risk %, symbols, sessions, confidence, learning mode, compound units), each "
    "clamped to owner bounds. It cannot place orders, move money, create owner/"
    "broker ACCEPT, mint edge tokens, or authorize live trading — those are "
    "outside the control surface and unreachable from here."
)

# The exact tool catalogue the operator is told it can rely on. Kept explicit so
# the model is ALWAYS aware of what exists (owner ask 2026-07-02).
TOOL_MANIFEST = {
    "dials_you_can_set": {
        "edge_threshold": "min measured win-prob to authorize a REAL trade (paper learning ignores it)",
        "min_directional_confidence": "min hypothesis confidence before a candidate forms (lower = more trades)",
        "max_risk_pct_per_trade": "risk budget per trade, sizes the lots",
        "max_concurrent_trades": "how many positions may be open at once — ENFORCED at the dispatch chokepoint (what you set here is what the risk gate blocks on; an explicit owner override wins)",
        "max_positions_per_symbol": "how many positions ONE symbol may stack — ENFORCED at the chokepoint. This is your anti-blind-stacking lever: raise it only when you deliberately want to concentrate on a signal",
        "max_total_exposure_lots": "total lots across all open positions — ENFORCED at the chokepoint",
        "max_compound_units": "how many times a winner may be added to",
        "daily_loss_cap_usd": "stop trading for the day after this loss",
        "paper_learning_trades": "1 = trade on paper to learn even without an edge; 0 = block",
        "trailing_stop_enabled": "1 = trades exit via a TRAILING STOP that banks a share of the run on a pullback, instead of only holding to fixed SL/TP — the implementable 'bank winners early'. Turn ON when trailing_stop_analysis shows it beats holding.",
        "trailing_lock_fraction": "how much of the best run the trailing stop locks in (0.5 = half; higher = tighter/closer to the peak)",
        "symbols": "which markets to scan/trade (subset of owner-allowed — the universe is wide: majors, crosses, JPY pairs, metals, indices). SCOUT broadly: add markets to watch, then keep the ones that PROFIT in learning_outcomes and drop chronic losers.",
        "sessions": "which sessions to trade (Asian/London/NewYork)",
    },
    "evidence_you_can_read": [
        "direction-learning ledger (LONG/SHORT outcomes, edge-status counts, profile recommendation)",
        "outcome binding (closed-trade P&L bound to predictions)",
        "adaptation plan (proposed strategy changes once enough outcomes bind)",
        "recent WASTE cycles (what was watched/decided each 15s tick)",
    ],
    "offline_workbench_tools": {
        "PCBA / CJT": "CAS cognitive-state governance layer (already live in each cycle's feature map)",
        "Condition Lab": "re-parameterize price rules and stress-test settings",
        "Optimizer": "search strategy parameters",
        "adaptation pipeline": "plan -> preview -> owner review -> paper apply -> promotion rule",
    },
    "you_cannot": [
        "place or close orders",
        "move money / deposit / withdraw / payout",
        "create owner or broker ACCEPT",
        "authorize live trading or flip live_mode",
        "mint edge tokens",
    ],
}

_OPERATOR_SYSTEM_PROMPT = (
    "You are the CAS Forex AI operator: an always-on strategy desk. Your PRIMARY "
    "OBJECTIVE is to GROW THE ACCOUNT — increase realized net profit and the "
    "balance/principal. Everything you do serves that goal: keep what wins, cut "
    "what loses, protect gains. You do NOT place trades yourself — the trading "
    "engine does that; you steer it by tuning the owner-fenced dials (edge "
    "threshold, risk %, symbols, sessions, confidence, learning mode, "
    "compounding, and the trailing stop). Use profit_and_balance and "
    "learning_outcomes to decide: drop symbol/direction groups that keep losing, "
    "favour ones that profit, enable/tune the trailing stop when it banks more "
    "than it costs, size to grow the balance without breaching risk caps. Be "
    "honest: durable profit needs a real edge (still unproven) and REAL money "
    "needs the owner's go-live switches — you operate on PAPER and never move "
    "money or authorize live. You only propose dial values, clamped to the "
    "owner's bounds. The context may include owner_guidance: standing "
    "considerations from the owner — weigh them seriously and say so when they "
    "shape a decision, but they never override the fences or the evidence. "
    "EPISTEMIC STANCE (important): nothing here is random — every price move has "
    "a cause. When many near-identical clustered trades all win, that is ONE "
    "independent observation copied many times, NOT many wins — it overcounts "
    "evidence, it does not make the signal fake. Never dismiss a profitable "
    "pattern as 'luck'. Treat it as an UNCONFIRMED, promising lead: keep it in "
    "the watch and gather INDEPENDENT out-of-sample setups to test whether its "
    "cause repeats (real edge) or was specific to one moment. Cut a market for "
    "sustained INDEPENDENT losses, not because a winner came in a cluster. "
    "RISK CAPS ARE IN YOUR HANDS (owner directive 2026-07-03): "
    "max_concurrent_trades, max_positions_per_symbol and max_total_exposure_lots "
    "are enforced at the dispatch chokepoint — the gate blocks on whatever you "
    "set (an explicit owner override wins). Your capital is finite: many thin "
    "open positions dilute it and grow nothing. Measured on 1,434 resolved "
    "paper trades (2026-07-03): the burst loop stacked copies onto LOSERS as "
    "hard as winners (avg 1.21 vs 1.22 copies) and genuine stacking netted "
    "-$317, while nearly all real profit came from SINGLE deliberate trades. So "
    "run FEWER, DELIBERATE positions sized to matter; allow a symbol to stack "
    "only when you consciously choose to concentrate on a signal with "
    "independent supporting evidence, and watch the win/loss stack symmetry — "
    "if losers stack as deep as winners, the loop is stacking blindly and you "
    "should tighten max_positions_per_symbol. "
    "CONTINUITY: the context may include your_recent_dial_changes — YOUR OWN "
    "latest decisions with their reasons, newest first. Respect them: do not "
    "undo or contradict a recent change unless NEW evidence arrived since it "
    "was made (and if you do, say which evidence). Never describe a market or "
    "setting as unused/untried when your recent changes touched it. "
    "IMPORTANT — you are one of many operators over time. The context includes "
    "inherited_lessons: durable conclusions PRIOR operators learned from the "
    "trades so far. Read them FIRST; do not re-try what they found does not work. "
    "When THIS tick's evidence teaches something durable that future operators "
    "should inherit (a market's behaviour, an exit policy result, a data-quality "
    "trap, what is/isn't a real edge), record it in the 'lessons' field so the "
    "system's knowledge compounds. "
    "Respond with a single JSON object and nothing else, matching exactly:\n"
    '{"observations": "<what the evidence shows>", '
    '"actions": [{"type": "adjust_dial", "lever": "<one of the dials>", '
    '"value": <number or list>, "reason": "<why>"}], '
    '"lessons": [{"text": "<durable takeaway for future operators>", '
    '"category": "market|exit_policy|sizing_risk|data_quality|edge|general", '
    '"evidence": "<the numbers that support it>"}], '
    '"summary": "<one line>"}\n'
    "Use an empty lessons list if nothing durable was learned this tick.\n"
    "Use an empty actions list if no change is warranted. Only use lever names "
    "from the provided dial list. Be conservative: small, justified changes."
)


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _profit_and_balance() -> dict[str, Any]:
    """The operator's north-star scoreboard — TWO honest numbers, side by side.

    Two different questions get two different numbers (owner correction
    2026-07-03 — neither is a 'mirage'):

      * BALANCE GROWTH — how much did the paper balance actually move? Every
        filled lot counts: 49 stacked copies of a winner really do move the
        balance 49 times. This is the #1-goal number.
      * INDEPENDENT EVIDENCE — how sure are we the signals repeat? N correlated
        copies of one signal are ~ONE independent observation, so clusters are
        collapsed to their average. This is the edge-confidence number.

    Injected test/replay rows are quarantined out of the ledger entirely (a
    single 49-copy ':test' cluster was inflating the old headline by +$9,458 =
    90.4%); the quarantine badge below keeps that correction auditable."""
    seed = 2000.0
    try:
        thresholds = __import__("cas_forex.proof_control", fromlist=["build_profit_thresholds_report"]).build_profit_thresholds_report()
        seed = float(thresholds.get("seed_capital_usd") or 2000.0)
    except Exception:
        pass
    ledger = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["load_paper_outcome_history"]).load_paper_outcome_history(),
        {"history_records": []},
    )
    rows = [r for r in (ledger.get("history_records") or []) if isinstance(r, dict)]
    quarantined = [r for r in (ledger.get("quarantined_test_artifacts") or []) if isinstance(r, dict)]
    raw_net = round(sum(float(r.get("profit") or 0.0) for r in rows), 2)

    # Collapse correlated clusters: same (symbol, direction, entry, exit, reason)
    # is ONE unique signal, represented by its average P&L.
    clusters: dict[tuple, list[float]] = {}
    for r in rows:
        key = (
            r.get("symbol"), r.get("direction"),
            round(float(r.get("entry") or 0.0), 5),
            round(float(r.get("exit") or 0.0), 5),
            r.get("close_reason"),
        )
        clusters.setdefault(key, []).append(float(r.get("profit") or 0.0))
    unique = [sum(v) / len(v) for v in clusters.values()]
    unique_net = round(sum(unique), 2)
    uwins = len([x for x in unique if x > 0])
    ulosses = len([x for x in unique if x < 0])
    ugw = round(sum(x for x in unique if x > 0), 2)
    ugl = round(sum(x for x in unique if x < 0), 2)
    biggest_cluster = max((len(v) for v in clusters.values()), default=0)
    # Stack-symmetry monitor: are winners stacked deeper than losers? If losers
    # stack as deep (as measured 2026-07-03: 1.21 vs 1.22), the burst loop is
    # stacking blindly — concentration is variance, not conviction.
    win_sizes = [len(v) for v in clusters.values() if sum(v) > 0]
    loss_sizes = [len(v) for v in clusters.values() if sum(v) < 0]
    avg_win_stack = round(sum(win_sizes) / len(win_sizes), 3) if win_sizes else None
    avg_loss_stack = round(sum(loss_sizes) / len(loss_sizes), 3) if loss_sizes else None
    return {
        "objective": "GROW THE BALANCE — the #1 goal. Fewer, deliberate, well-sized positions; concentrate only on signals with independent supporting evidence (paper now; real needs owner go-live).",
        "seed_capital_usd": seed,
        # --- Question 1: how much did the balance actually move? -------------
        "balance_growth_net_pnl_usd": raw_net,
        "honest_paper_balance_usd": round(seed + raw_net, 2),
        "balance_question": "How much did the paper balance actually move? Every filled lot counts (stacked copies included).",
        # --- Question 2: how sure are we the signals repeat? ------------------
        "honest_unique_signal_net_pnl_usd": unique_net,
        "evidence_question": "One vote per independent signal (clusters collapsed): how sure are we the edge repeats?",
        "unique_signals": len(unique),
        "unique_win_rate": round(uwins / len(unique), 3) if unique else 0.0,
        "unique_profit_factor": round(ugw / abs(ugl), 3) if ugl else None,
        # --- Provenance + concentration telemetry ----------------------------
        "raw_net_pnl_usd": raw_net,
        "raw_trades": len(rows),
        "cluster_inflation_x": round(len(rows) / len(unique), 2) if unique else 1.0,
        "biggest_cluster_size": biggest_cluster,
        "avg_winning_stack_depth": avg_win_stack,
        "avg_losing_stack_depth": avg_loss_stack,
        "stacking_is_blind": (
            None
            if avg_win_stack is None or avg_loss_stack is None
            else bool(avg_loss_stack >= avg_win_stack)
        ),
        "test_artifacts_quarantined": len(quarantined),
        "test_artifacts_net_pnl_usd": round(sum(float(r.get("profit") or 0.0) for r in quarantined), 2),
        "data_class": "PAPER_SIM / paper_simulated_first_touch — simulated first-touch fills on real candles, not live broker money.",
        "caveats": [
            "TWO questions, TWO numbers: balance growth counts every filled lot (stacking a winner really grows the balance); independent evidence collapses correlated copies (49 copies = ~1 observation of whether the signal repeats). Neither number is a mirage — they answer different questions.",
            "A profitable clustered signal is NOT 'luck' — it happened for a reason. It is an UNCONFIRMED lead: investigate it with independent out-of-sample setups; do not dismiss it, and do not bet the principal on it before it confirms.",
            "Stacking multiplies wins AND losses by the same factor. Concentrate deliberately (your risk-cap dials are enforced at the chokepoint), never as a side effect of burst timing.",
            "Injected test/replay rows are quarantined out of both numbers (see test_artifacts_quarantined).",
            "Real money needs owner go-live regardless.",
        ],
    }


def _recent_cycles(limit: int = 40) -> dict[str, Any]:
    path = REPO_ROOT / "runtime" / "waste-runner-audit.jsonl"
    if not path.exists():
        return {"available": False}
    decisions: dict[str, int] = {}
    symbols: dict[str, int] = {}
    learning = 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return {"available": False}
    for line in lines:
        try:
            cycle = (json.loads(line).get("cycle")) or {}
        except (json.JSONDecodeError, AttributeError):
            continue
        d = str(cycle.get("decision") or "")
        decisions[d] = decisions.get(d, 0) + 1
        if cycle.get("learning_trade"):
            learning += 1
        w = cycle.get("watch_state") or {}
        sym = str(w.get("symbol") or "")
        if sym:
            symbols[sym] = symbols.get(sym, 0) + 1
    return {
        "available": True,
        "window": len(lines),
        "decision_counts": decisions,
        "symbol_counts": symbols,
        "learning_trade_count": learning,
    }


def gather_context(config: Any = None) -> dict[str, Any]:
    """Read every input the operator reasons over. All reads are defensive."""
    config = _resolve_config(config)
    from cas_forex.ai_control_authority import get_authority

    authority = get_authority()
    snapshot = _safe(authority.snapshot, {})

    learning = _safe(
        lambda: __import__("cas_forex.waste_direction_learning_ledger", fromlist=["build_waste_direction_learning_ledger"]).build_waste_direction_learning_ledger(),
        {"status": "UNAVAILABLE"},
    )
    outcome = _safe(
        lambda: __import__("cas_forex.waste_direction_outcome_binding", fromlist=["build_waste_direction_outcome_binding"]).build_waste_direction_outcome_binding(),
        {"status": "UNAVAILABLE"},
    )
    adaptation = _safe(
        lambda: __import__("cas_forex.waste_adaptation_plan", fromlist=["build_waste_adaptation_plan"]).build_waste_adaptation_plan(),
        {"status": "UNAVAILABLE"},
    )
    # Refresh realized paper outcomes first (guarded: at most once per 10 min),
    # so the operator reasons over fresh wins/losses. Best-effort by design.
    # Skipped under pytest — it does live candle fetches + ledger writes that
    # must not leak between tests.
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        _safe(
            lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["maybe_refresh_paper_outcomes"]).maybe_refresh_paper_outcomes(),
            None,
        )
    # The learn-from-mistakes ledger: realized paper win/loss per symbol x
    # direction x profile, including non-edge learning trades. This is what lets
    # the operator say "SHORT NAS100 keeps losing — raise its confidence bar".
    learning_outcomes = _safe(
        lambda: __import__("cas_forex.waste_direction_outcome_binding", fromlist=["build_waste_learning_outcomes"]).build_waste_learning_outcomes(),
        {"status": "UNAVAILABLE"},
    )
    # Early-banking analysis: directly tests the owner's "bank big winners early,
    # then restart WASTE" idea against realized max-favorable-excursion data.
    early_banking = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["build_early_banking_analysis"]).build_early_banking_analysis(),
        {"status": "UNAVAILABLE"},
    )
    # The IMPLEMENTABLE version: realized paper net under a trailing stop.
    trailing_stop = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["build_trailing_stop_analysis"]).build_trailing_stop_analysis(),
        {"status": "UNAVAILABLE"},
    )
    # Standing owner guidance — the owner's plain-language considerations,
    # weighed on every tick. Judgment-shaping only; every action stays clamped
    # to the owner fences regardless of what a note asks for.
    owner_guidance = _safe(
        lambda: __import__("cas_forex.operator_guidance", fromlist=["guidance_for_prompt"]).guidance_for_prompt(),
        [],
    )
    # Inherited knowledge: durable lessons prior operators learned from the
    # trades so far — read first so this operator builds on them, not from scratch.
    inherited_lessons = _safe(
        lambda: __import__("cas_forex.operator_lessons", fromlist=["lessons_for_prompt"]).lessons_for_prompt(),
        [],
    )
    return {
        "profit_and_balance": _profit_and_balance(),
        "inherited_lessons": inherited_lessons,
        "dials": (snapshot.get("control_surface") or {}).get("values") if isinstance(snapshot, dict) else None,
        "dial_bounds": (snapshot.get("control_surface") or {}).get("bounds") if isinstance(snapshot, dict) else None,
        "owner_guidance": owner_guidance,
        "learning": _compact(learning),
        "outcome_binding": _compact(outcome),
        "learning_outcomes": _compact_learning_outcomes(learning_outcomes),
        "early_banking_analysis": early_banking,
        "trailing_stop_analysis": trailing_stop,
        "adaptation": _compact(adaptation),
        "recent_cycles": _recent_cycles(),
        "tool_manifest": TOOL_MANIFEST,
    }


def _compact_learning_outcomes(obj: Any) -> Any:
    """Keep the operator-useful learning fields incl. the worst/best groups
    (small lists the model should reason over), dropping bulk sample rows."""
    if not isinstance(obj, dict):
        return obj
    keep = {
        k: obj.get(k)
        for k in (
            "bound_trade_count",
            "learning_ready",
            "overall",
            "direction_counts",
            "symbol_counts",
            "worst_groups",
            "best_groups",
            "next_action",
        )
        if k in obj
    }
    return keep or {"status": obj.get("status", "UNAVAILABLE")}


def _compact(obj: Any) -> Any:
    """Drop big/nested arrays so the prompt stays small and cheap."""
    if not isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if k in ("claim_boundary", "attempts", "rows", "cycles", "events"):
            continue
        if isinstance(v, list) and len(v) > 8:
            out[k] = {"count": len(v)}
        elif isinstance(v, dict):
            small = {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))}
            out[k] = small or {"nested": True}
        else:
            out[k] = v
    return out


def build_prompt(context: dict[str, Any]) -> str:
    return (
        "Here is the current state of the CAS Forex trading loop. Decide whether "
        "to adjust any owner-fenced dial to improve learning/edge, then reply with "
        "the JSON object described in the system prompt.\n\n"
        + json.dumps(context, indent=1, default=str)[:8000]
    )


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    # Prefer a fenced or first balanced object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_proposed_command(text: str) -> tuple[Optional[dict[str, Any]], str]:
    """Pull a proposed owner command out of a chat reply.

    The operator emits ```command {"command": "...", "params": {...}} ``` when it
    wants to ACT. Returns ``(proposed_or_None, display_text_without_the_block)``.
    The block is stripped from the display text so the chat bubble stays clean;
    the structured command is handed to the broker for a preview."""
    if not text:
        return None, text
    match = re.search(r"```(?:command|json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return None, text
    try:
        obj = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, text
    if not isinstance(obj, dict) or not obj.get("command"):
        return None, text
    display = (text[: match.start()] + text[match.end():]).strip()
    proposed = {"command": str(obj.get("command")), "params": obj.get("params") or {}}
    return proposed, display


@dataclass
class OperatorTick:
    ok: bool
    provider: Optional[str] = None
    provider_label: Optional[str] = None
    paid: bool = False
    failover: bool = False
    observations: str = ""
    summary: str = ""
    actions_applied: list = field(default_factory=list)
    actions_skipped: list = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": REPORT_KIND,
            "ok": self.ok,
            "provider": self.provider,
            "provider_label": self.provider_label,
            "paid": self.paid,
            "failover": self.failover,
            "observations": self.observations,
            "summary": self.summary,
            "actions_applied": self.actions_applied,
            "actions_skipped": self.actions_skipped,
            "error": self.error,
            "claim_boundary": CLAIM_BOUNDARY,
            "at": utc_now().isoformat(),
        }


class AIOperator:
    """One tick = gather -> ask active model -> apply fenced dial changes."""

    def __init__(self, config: Any = None, *, actions_path: Path | str = DEFAULT_ACTIONS_PATH):
        self.config = _resolve_config(config)
        self.actions_path = Path(actions_path)

    def _allowed_levers(self) -> set[str]:
        try:
            from cas_forex.ai_control_surface import LEVER_NAMES

            return set(LEVER_NAMES)
        except Exception:
            return set()

    def _apply(self, decision: dict[str, Any]) -> tuple[list, list]:
        from cas_forex.ai_control_authority import get_authority

        authority = get_authority()
        allowed = self._allowed_levers()
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for action in decision.get("actions") or []:
            if not isinstance(action, dict):
                continue
            if str(action.get("type")) != "adjust_dial":
                skipped.append({"action": action, "why": "unsupported action type (only adjust_dial applies)"})
                continue
            lever = str(action.get("lever") or "")
            if lever not in allowed:
                skipped.append({"action": action, "why": f"lever '{lever}' is not an owner-fenced dial"})
                continue
            try:
                result = authority.ai_adjust(
                    lever,
                    action.get("value"),
                    reason=f"AI operator: {action.get('reason') or 'no reason given'}",
                )
                applied.append(
                    {
                        "lever": lever,
                        "requested": action.get("value"),
                        "clamped": bool(result.get("owner_clamped") or result.get("clamped")),
                        "new_value": (result.get("snapshot") or {}).get("control_surface", {}).get("values", {}).get(lever),
                        "reason": action.get("reason"),
                    }
                )
            except Exception as exc:
                skipped.append({"action": action, "why": f"{type(exc).__name__}: {exc}"})
        return applied, skipped

    def _record(self, tick: OperatorTick, *, extra: Optional[dict[str, Any]] = None) -> None:
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)
        payload = tick.to_dict()
        if extra:
            payload.update(extra)
        try:
            with self.actions_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, default=str) + "\n")
        except OSError:
            pass

    def _recent_dial_changes(self, limit: int = 6) -> list[dict[str, Any]]:
        """The operator's OWN latest decisions, fed back into its next tick so
        it doesn't blindly undo what it just did (observed 2026-07-03: a tick
        re-added AUD/CAD 13 minutes after the prior tick cut it for 0/14
        losses, calling the market 'previously unused'). Compact on purpose:
        summaries + applied dial changes only, newest first."""
        out: list[dict[str, Any]] = []
        for row in self.recent_actions(limit=40):
            applied = row.get("actions_applied") or []
            if not applied:
                continue
            out.append(
                {
                    "at": row.get("at"),
                    "summary": str(row.get("summary") or "")[:220],
                    "dials_changed": [
                        {
                            "lever": a.get("lever"),
                            "new_value": a.get("new_value"),
                            "reason": str(a.get("reason") or "")[:180],
                        }
                        for a in applied
                        if isinstance(a, dict)
                    ],
                }
            )
            if len(out) >= limit:
                break
        return out

    def tick(self) -> OperatorTick:
        from cas_forex.model_provider import get_model_provider

        context = gather_context(self.config)
        # Self-continuity: put YOUR OWN recent dial changes FIRST in the
        # context (the prompt truncates the tail, never the head) so a new
        # tick always knows what the previous ticks just decided and why.
        recent_changes = self._recent_dial_changes()
        if recent_changes:
            context = {"your_recent_dial_changes": recent_changes, **context}
        prompt = build_prompt(context)
        gen = get_model_provider(self.config).generate(prompt, _OPERATOR_SYSTEM_PROMPT)
        if not gen.get("ok"):
            tick = OperatorTick(
                ok=False,
                provider=gen.get("provider"),
                failover=bool(gen.get("failover")),
                error=gen.get("error") or "model unavailable",
                summary="No model available this tick — dials unchanged (trading loop keeps running).",
            )
            self._record(tick)
            return tick
        decision = _extract_json(gen.get("text") or "")
        if decision is None:
            # Extended-thinking models occasionally spend the whole token budget
            # reasoning and truncate the JSON. Retry ONCE, terse: JSON only, one
            # sentence of observations, no long deliberation.
            terse_system = (
                _OPERATOR_SYSTEM_PROMPT
                + "\n\nIMPORTANT: Reply with ONLY the JSON object and nothing "
                "else. Keep 'observations' to a single sentence. Do not "
                "deliberate at length — decide quickly."
            )
            gen_retry = get_model_provider(self.config).generate(
                prompt + "\n\nRespond with ONLY the JSON object now.", terse_system
            )
            if gen_retry.get("ok"):
                gen = gen_retry
                decision = _extract_json(gen_retry.get("text") or "")
        if decision is None:
            tick = OperatorTick(
                ok=False,
                provider=gen.get("provider"),
                provider_label=gen.get("provider_label"),
                paid=bool(gen.get("paid")),
                failover=bool(gen.get("failover")),
                error="model reply was not parseable JSON — no dial change made",
                summary="Unparseable model reply; dials unchanged.",
            )
            self._record(tick)
            return tick
        applied, skipped = self._apply(decision)
        lessons_recorded = self._record_lessons(decision)
        tick = OperatorTick(
            ok=True,
            provider=gen.get("provider"),
            provider_label=gen.get("provider_label"),
            paid=bool(gen.get("paid")),
            failover=bool(gen.get("failover")),
            observations=str(decision.get("observations") or "")[:2000],
            summary=str(decision.get("summary") or "")[:500],
            actions_applied=applied,
            actions_skipped=skipped,
        )
        tick_dict = tick.to_dict()
        tick_dict["lessons_recorded"] = lessons_recorded
        self._record(tick, extra={"lessons_recorded": lessons_recorded})
        return tick

    def _record_lessons(self, decision: dict[str, Any]) -> list[dict[str, Any]]:
        """Persist any durable lessons the operator learned this tick so future
        operators inherit them. Never raises."""
        out: list[dict[str, Any]] = []
        try:
            from cas_forex.operator_lessons import record_lesson

            for item in (decision.get("lessons") or [])[:5]:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                stored = record_lesson(
                    text,
                    category=str(item.get("category") or "general"),
                    evidence=str(item.get("evidence") or ""),
                    source="operator",
                )
                if stored:
                    out.append({"text": stored["text"], "category": stored["category"]})
        except Exception:
            pass
        return out

    def chat(self, message: str) -> dict[str, Any]:
        """Talk to the strategy desk, and let it PROPOSE an action.

        The operator answers with the full context. When the owner asks it to DO
        something that maps to an owner command (set a dial/risk cap, LAN mode,
        arm a live switch, move money), it proposes that command — and the reply
        carries the command's PREVIEW (current state, exact change, effects,
        blockers, the phrase to type). Nothing changes here: execution is a
        SEPARATE step through the command broker with the typed confirmation, so
        the owner always sees and confirms the exact change first."""
        from cas_forex.model_provider import get_model_provider

        question = str(message or "").strip()
        if not question:
            return {"ok": False, "error": "empty message"}
        context = gather_context(self.config)
        context["recent_operator_actions"] = [
            {k: a.get(k) for k in ("at", "provider", "summary", "actions_applied") if k in a}
            for a in self.recent_actions(limit=5)
        ]
        catalog = _safe(
            lambda: __import__("cas_forex.owner_command_broker", fromlist=["catalog"]).catalog(),
            [],
        )
        system = (
            "You are the CAS Forex AI operator — the always-on strategy desk. The "
            "owner is talking to you directly. Answer in plain language, honestly "
            "and concretely, using the provided context. Be direct about "
            "trade-offs. Keep the answer under 250 words.\n"
            "You can ACT on the owner's behalf by PROPOSING an owner command. When "
            "the owner clearly asks you to DO something that matches one of the "
            "available commands (see COMMAND_CATALOG in context), append EXACTLY "
            "ONE fenced block on its own line:\n"
            "```command\n{\"command\": \"<name>\", \"params\": { ... }}\n```\n"
            "Only propose a command you are confident maps to the request; put "
            "real values in params. If the message is just a question, do NOT "
            "propose a command. You never execute — proposing shows the owner a "
            "preview and the exact confirmation phrase they must type; the change "
            "only happens when they confirm."
        )
        context["COMMAND_CATALOG"] = catalog
        prompt = (
            "CONTEXT:\n"
            + json.dumps(context, indent=1, default=str)[:9000]
            + "\n\nOWNER'S MESSAGE:\n"
            + question[:2000]
        )
        gen = get_model_provider(self.config).generate(prompt, system)
        text = (gen.get("text") or "").strip()
        proposed, display = _extract_proposed_command(text)
        preview = None
        if proposed is not None:
            preview = _safe(
                lambda: __import__("cas_forex.owner_command_broker", fromlist=["preview"]).preview(
                    proposed["command"], proposed.get("params") or {}
                ),
                None,
            )
        reply = {
            "ok": bool(gen.get("ok")),
            "reply": display,
            "provider": gen.get("provider"),
            "provider_label": gen.get("provider_label"),
            "paid": bool(gen.get("paid")),
            "error": gen.get("error"),
            "at": utc_now().isoformat(),
            "dials_changed": False,
            "proposed_command": proposed,
            "command_preview": preview,
            "claim_boundary": (
                "Chat can PROPOSE an action and show its preview; nothing changes "
                "until you confirm the exact typed phrase. Execution runs the same "
                "gated function the buttons use and writes a receipt."
            ),
        }
        try:
            chat_log = self.actions_path.parent / "ai-operator-chat.jsonl"
            with chat_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"question": question, **reply}, default=str) + "\n")
        except OSError:
            pass
        return reply

    def recent_actions(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.actions_path.exists():
            return []
        try:
            lines = self.actions_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))
