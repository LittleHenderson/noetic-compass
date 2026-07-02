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
        "max_concurrent_trades": "how many positions may be open at once",
        "max_compound_units": "how many times a winner may be added to",
        "daily_loss_cap_usd": "stop trading for the day after this loss",
        "paper_learning_trades": "1 = trade on paper to learn even without an edge; 0 = block",
        "symbols": "which markets to scan (subset of owner-allowed)",
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
    "You are the CAS Forex AI operator: an always-on strategy desk. You read the "
    "trading loop's learning evidence and tune ONLY the owner-fenced AI dials to "
    "improve paper learning and (eventually) real edge. You never trade, move "
    "money, or authorize anything — you only propose dial values, which are "
    "clamped to the owner's bounds before taking effect. The context may include "
    "owner_guidance: standing considerations from the owner — weigh them "
    "seriously in your reasoning and say so when they shape a decision, but they "
    "never override the fences or the evidence. Respond with a single "
    "JSON object and nothing else, matching exactly:\n"
    '{"observations": "<what the evidence shows>", '
    '"actions": [{"type": "adjust_dial", "lever": "<one of the dials>", '
    '"value": <number or list>, "reason": "<why>"}], '
    '"summary": "<one line>"}\n'
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
    # Standing owner guidance — the owner's plain-language considerations,
    # weighed on every tick. Judgment-shaping only; every action stays clamped
    # to the owner fences regardless of what a note asks for.
    owner_guidance = _safe(
        lambda: __import__("cas_forex.operator_guidance", fromlist=["guidance_for_prompt"]).guidance_for_prompt(),
        [],
    )
    return {
        "dials": (snapshot.get("control_surface") or {}).get("values") if isinstance(snapshot, dict) else None,
        "dial_bounds": (snapshot.get("control_surface") or {}).get("bounds") if isinstance(snapshot, dict) else None,
        "owner_guidance": owner_guidance,
        "learning": _compact(learning),
        "outcome_binding": _compact(outcome),
        "learning_outcomes": _compact_learning_outcomes(learning_outcomes),
        "early_banking_analysis": early_banking,
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

    def _record(self, tick: OperatorTick) -> None:
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.actions_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(tick.to_dict(), default=str) + "\n")
        except OSError:
            pass

    def tick(self) -> OperatorTick:
        from cas_forex.model_provider import get_model_provider

        context = gather_context(self.config)
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
        self._record(tick)
        return tick

    def chat(self, message: str) -> dict[str, Any]:
        """Talk to the strategy desk: answer the owner's question with the FULL
        operator context (learning ledger, dials, recent actions, standing
        guidance). Conversational only — chat NEVER moves a dial; if the owner
        wants something considered going forward, it is saved as standing
        guidance via the guidance store, and the next tick acts on it."""
        from cas_forex.model_provider import get_model_provider

        question = str(message or "").strip()
        if not question:
            return {"ok": False, "error": "empty message"}
        context = gather_context(self.config)
        context["recent_operator_actions"] = [
            {k: a.get(k) for k in ("at", "provider", "summary", "actions_applied") if k in a}
            for a in self.recent_actions(limit=5)
        ]
        system = (
            "You are the CAS Forex AI operator — the always-on strategy desk that "
            "tunes the owner-fenced dials of a paper-trading learning loop. The "
            "owner is talking to you directly. Answer in plain language, honestly "
            "and concretely, using the provided context (realized paper outcomes, "
            "dials, learning state, your own recent actions, standing owner "
            "guidance). Be direct about trade-offs and about what you can and "
            "cannot do: you tune dials within owner fences; you never place "
            "orders, move money, or authorize live trading. This chat does not "
            "change any dial — changes happen on your scheduled ticks. Keep the "
            "answer under 250 words."
        )
        prompt = (
            "CONTEXT:\n"
            + json.dumps(context, indent=1, default=str)[:9000]
            + "\n\nOWNER'S MESSAGE:\n"
            + question[:2000]
        )
        gen = get_model_provider(self.config).generate(prompt, system)
        reply = {
            "ok": bool(gen.get("ok")),
            "reply": (gen.get("text") or "").strip(),
            "provider": gen.get("provider"),
            "provider_label": gen.get("provider_label"),
            "paid": bool(gen.get("paid")),
            "error": gen.get("error"),
            "at": utc_now().isoformat(),
            "dials_changed": False,
            "claim_boundary": "Chat is conversational only; dials change only on scheduled operator ticks, always clamped to owner fences.",
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
