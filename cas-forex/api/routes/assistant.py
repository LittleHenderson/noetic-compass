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
    "You are the CAS Forex assistant — a floating helper embedded in the owner's "
    "forex automation cockpit (a React app backed by a local FastAPI engine). The "
    "owner's whole goal is to AUTOMATE trading so their own trading psychology "
    "(anxiety, revenge trading) is taken out of the loop. Be concise, plain-spoken, "
    "and concrete — talk like a person, not a manual.\n\n"
    "You can explain what the app does and where things are: Quick Start, Settings "
    "(including the API-address field for phone access), Optimizer / Condition Lab "
    "(strategy conditions by timeframe, incl. M1/M5 scalping), the Ledger, runtime "
    "gates, broker setup (MT5 native / MT4 file-mailbox EA), timeframes, risk "
    "controls (concurrent trades, loss caps), and money movement (deposit/withdraw/"
    "payout).\n\n"
    "Hard rules: never claim an action happened that didn't. Moving real money or "
    "placing live orders is gated behind owner-controlled switches + real broker / "
    "payment credentials — when asked to DO such a thing, explain the exact steps and "
    "which gate/credential is required, don't pretend to execute it. Be honest that "
    "the app has no proven trading edge yet. If you don't know live runtime state, "
    "say so plainly."
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
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
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
