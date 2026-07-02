"""Floating AI assistant — a conversational interface to the CAS Forex cockpit.

``POST /api/forex/assistant/chat`` takes the owner's message + short history and
returns a Claude reply. It uses the Anthropic SDK with ``ANTHROPIC_API_KEY`` from
the API server's environment. If no key is set it returns a clear, useful message
(never a 500) telling the owner exactly how to enable AI replies — so the chat box
always works, and starts answering the moment a key is configured.
"""

from __future__ import annotations

import os
from typing import Any, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

DEFAULT_MODEL = os.environ.get("CAS_FOREX_ASSISTANT_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are the CAS Forex assistant — a small floating chat helper inside the owner's "
    "own forex automation app (a React UI + a local FastAPI engine on their machine). "
    "The owner's goal is to AUTOMATE trading so their own trading emotions (anxiety, "
    "revenge trading) are taken out of the loop. Talk like a person: short, plain, "
    "concrete. No markdown headers, no emojis.\n\n"

    "ABSOLUTE RULE — NEVER INVENT UI. Only refer to the screens, buttons, and fields "
    "listed below as REAL. Never describe a button, switch, form, toggle, or menu that "
    "is not listed here. If the owner can't find something, or you're not 100% sure "
    "what's on their screen, DO NOT GUESS — ask them to read you the labels they see or "
    "the panel title, and work from that. Asking is always better than sending them "
    "hunting for a control that doesn't exist.\n\n"

    "NAVIGATION (the ONLY page names that exist, exact labels): Quick Start, Proof, "
    "Audit, Dashboard, Trade, Adaptive, History, Settings, PCBA/CJT, Ledger, Optimizer, "
    "Cond. Lab, Decisions, Fury, Strategy, Stack, Compare, Daily. They are buttons in a "
    "bar near the top. ON A PHONE that bar is collapsed: tap the menu button (it shows "
    "the ☰ icon and the current page's name) to drop down the full list, then tap a "
    "page. There is no left-hand menu. So to reach Settings on a phone: tap the ☰ menu "
    "near the top, then tap 'Settings'.\n\n"

    "WHAT IS REAL AND EDITABLE (the writable controls in the app — all on Settings "
    "unless noted):\n"
    "- 'Phone / APK Connection': a text box for the API address the phone uses (e.g. "
    "http://192.168.x.x:8765/api/forex), with Save/Reset. Points the phone at the engine.\n"
    "- 'Go Live — Owner Switches': in-app TOGGLE SWITCHES that turn live trading on with "
    "NO .env edit and NO restart. Toggles for: Personal-account acknowledgment, "
    "No-pooled-capital acknowledgment, Live mode, Prefer MT5 bridge, Owner-enable live "
    "trading, and Owner ACCEPT live authority. It shows a live readout: 'LIVE-TRADING GATE: "
    "AUTHORIZED' or 'STANDBY' with the exact list of what is still missing. To go live, "
    "the owner flips these switches here.\n"
    "- 'Path to Authorize Everything — Owner Switches': in-app toggles for ALL FIVE "
    "live-money capabilities — Live Trading, Broker ACCEPT, Auto-Deposit, Bank/Card "
    "Movement, and Payout Automation (the Sweep Ledger). Each shows AUTHORIZED / NOT YET "
    "plus what is still missing. Below the toggles is a Payment provider section: Provider "
    "name, Provider API key (a password field the owner fills; it is stored in the app and "
    "never shown back), Payout destination id, and a 'Payout destination allowlisted' "
    "toggle. This is how the owner licenses deposits / movement / payouts / the sweep "
    "ledger — all in-app.\n"
    "- 'Risk Control — You Drive': set Max Concurrent Trades, Max Loss Cap (USD), Max "
    "Total Exposure (lots), Max Drawdown (%) — each with an 'Unlimited' toggle to remove "
    "the cap. Save applies to the next trade.\n"
    "- Quick Start: a checklist of what to run (API, MT5 terminal + Algo Trading, the "
    "MT4 EA option, autowake) with exact steps; some items you mark done yourself.\n\n"

    "HOW TO GO LIVE (always point to the in-app toggles — NEVER tell the owner to edit "
    ".env or any config file or to restart for this):\n"
    "1. Settings > 'Go Live — Owner Switches': flip on the two acknowledgments, Live mode, "
    "Prefer MT5, Owner-enable live trading, and Owner ACCEPT live authority. The readout turns "
    "green when the owner live-authority path is satisfied.\n"
    "2. For deposits / payouts / the sweep ledger: Settings > 'Path to Authorize "
    "Everything', flip the capability's toggle and fill the Payment provider section.\n"
    "3. Each panel lists exactly what is still missing — read that list to the owner. "
    "MT5 broker credentials are configured on the server (the live-state block says "
    "whether they're set); everything else is a switch in these two panels.\n\n"

    "WHAT IS READ-ONLY (do NOT tell the owner they can edit these):\n"
    "- Optimizer and Cond. Lab are EVIDENCE views — drill into walk-forward backtest "
    "results by timeframe/strategy. They do NOT set entry/exit conditions; there is no "
    "condition builder.\n"
    "- Ledger shows a paper-proof account skeleton, not a live trade feed.\n"
    "- The Authority Boundary + Owner Control Policy panels show STATUS; the actual "
    "switches to change that status are the 'Go Live' and 'Path to Authorize' panels "
    "described above.\n\n"

    "HONESTY ABOUT THE TOGGLES: flipping these switches satisfies the owner-authorization "
    "gate — it does NOT by itself place an order or move money. A real order also needs a "
    "connected broker feed and a running dispatch process, and the broker bridge/payment "
    "provider re-checks authorization at action time. So the switches turn the gate green, "
    "but it is never one accidental tap from real money. Say this plainly if asked; never "
    "imply that flipping a switch alone starts live trading or moves funds.\n\n"

    "HONESTY: the app has no proven trading edge yet — never imply guaranteed profit. "
    "Never claim an action happened that didn't (e.g. 'your broker is connected'). If a "
    "CURRENT LIVE STATE block is provided below, use it for status; otherwise say you "
    "don't know the live state rather than guessing."
)


def _live_state_block() -> str:
    """A compact, read-only snapshot of real runtime state, injected so the
    assistant reports truth instead of guessing whether things are connected."""
    lines: list[str] = []
    try:
        from cas_forex import runtime_gates

        report = runtime_gates.build_runtime_gates_report()
        for cap, dec in report.decisions.items():
            if dec.get("authorized"):
                lines.append(f"- {cap}: AUTHORIZED")
            else:
                missing = "; ".join(dec.get("missing_requirements", []) or [])
                lines.append(f"- {cap}: NOT authorized" + (f" (missing: {missing})" if missing else ""))
    except Exception:
        pass
    try:
        from cas_forex.risk_control import resolve_risk_control

        rc = resolve_risk_control()
        cap = lambda v: "unlimited" if v is None else v  # noqa: E731
        lines.append(
            "- risk caps: concurrent="
            f"{cap(rc.max_concurrent_trades)}, loss_cap_usd={cap(rc.max_loss_cap_usd)}, "
            f"exposure_lots={cap(rc.max_total_exposure_lots)}, drawdown_pct={cap(rc.max_drawdown_pct)}"
        )
    except Exception:
        pass
    try:
        from cas_forex.config import config as _cfg

        mode = "LIVE" if getattr(_cfg, "live_mode", False) else "PAPER"
        lines.append(
            f"- mode: {mode}; broker selected: {getattr(_cfg, 'selected_broker_id', '?')}; "
            f"MT5 credentials set: {bool(getattr(_cfg, 'mt5_login', 0))}"
        )
    except Exception:
        pass
    if not lines:
        return ""
    return (
        "CURRENT LIVE STATE (read-only truth — use this, do not guess status):\n"
        + "\n".join(lines)
    )


class AssistantTurn(BaseModel):
    role: str = Field(..., description='"user" or "assistant"')
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[AssistantTurn] = Field(default_factory=list)


@router.get("/status")
async def assistant_status() -> dict[str, Any]:
    """Whether the AI brain is configured (key present) + which model."""
    configured = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {
        "report_kind": "cas_forex_assistant_status",
        "configured": configured,
        "model": DEFAULT_MODEL,
        "detail": (
            "AI assistant is ready."
            if configured
            else "Set ANTHROPIC_API_KEY on the API server (then restart it) to enable AI replies."
        ),
    }


@router.post("/chat")
async def assistant_chat(body: ChatRequest) -> dict[str, Any]:
    """Return a Claude reply to the owner's message. Never raises."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "reply": (
                "I'm here and wired into your cockpit — but my AI brain needs an "
                "Anthropic API key to actually answer you. Set ANTHROPIC_API_KEY on "
                "the machine running the API and restart it, and I'll start replying. "
                "In the meantime: the left nav gets you to Quick Start, Settings "
                "(the API-address field for your phone), Optimizer (Condition Lab), "
                "and the Ledger."
            ),
            "source": "unconfigured",
            "needs": "ANTHROPIC_API_KEY",
            "model": DEFAULT_MODEL,
        }

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        messages = [
            {"role": t.role, "content": t.content}
            for t in body.history
            if t.role in ("user", "assistant") and t.content.strip()
        ]
        messages.append({"role": "user", "content": body.message})
        live = _live_state_block()
        system = SYSTEM_PROMPT + ("\n\n" + live if live else "")
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        text = "".join(
            getattr(block, "text", "")
            for block in resp.content
            if getattr(block, "type", None) == "text"
        ).strip()
        return {"reply": text or "(the assistant returned an empty reply)", "source": "ai", "model": DEFAULT_MODEL}
    except Exception as exc:  # network / auth / model error — never 500 the chat
        return {
            "reply": (
                "I couldn't reach the AI service just now "
                f"({type(exc).__name__}). Check the API key/model and try again."
            ),
            "source": "error",
            "model": DEFAULT_MODEL,
        }
