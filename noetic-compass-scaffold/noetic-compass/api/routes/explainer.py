"""Gemini-backed public-safe CAS Harness explainer."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.config import settings
from api.dependencies.authz import current_tenant
from api.services.evidence_ownership import tenant_owns_trace
from api.services.explainer import (
    ExplainPacketResult,
    ExplainSegment,
    explain_evidence,
    explain_question,
)

router = APIRouter(tags=["explainer"])


class ExplainerChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1200)


class ExplainerChatResponse(BaseModel):
    answer: str
    sources: list[str]
    used_gemini: bool
    model: str
    safety_mode: str


@router.post("/explainer/chat", response_model=ExplainerChatResponse)
async def explainer_chat(body: ExplainerChatRequest) -> ExplainerChatResponse:
    """Answer a CAS Harness user-help question from the public-safe knowledge base."""

    result = await explain_question(body.question)
    return ExplainerChatResponse(
        answer=result.answer,
        sources=list(result.sources),
        used_gemini=result.used_gemini,
        model=result.model,
        safety_mode=result.safety_mode,
    )


# ===========================================================================
# Evidence Packet AI Explainer ("Explain this packet") — spec §7/§8.
#
# Verdict-fidelity + tenant-ownership core. The response contract below MUST match
# spec §7 byte-for-field (the frontend asserts ``verdict_echo === EP.verdict`` and
# renders ``segments`` / ``investigate_next`` ref-chips against it).
# ===========================================================================


class ExplainPacketSegment(BaseModel):
    """One cited interpretation segment (spec §6/§7). ``refs`` MUST be non-empty per segment."""

    text: str
    refs: list[str]


class ExplainPacketResponse(BaseModel):
    """Output contract — spec §7, exact shape.

    The UI asserts ``verdict_echo === EP.verdict``; on mismatch it discards the AI output and
    shows the raw EP verdict only. The API has already fail-closed-validated this match, so a
    rendered response either carries a faithful echo + cited segments, or a degraded response
    that carries only the raw verdict (empty segments) for the UI to surface as "unavailable".
    """

    trace_id: str
    verdict_echo: str
    segments: list[ExplainPacketSegment]
    investigate_next: list[ExplainPacketSegment]
    used_gemini: bool
    model: str
    safety_mode: str
    disclaimer: str


# 404 contract, identical to the evidence routes: a trace this tenant does not own is reported as
# "not found", never 403 — a cross-tenant probe is indistinguishable from a genuinely-absent trace.
_NOT_FOUND_DETAIL = "trace_id not found"


def _explainer_state_store(request: Request):
    """Return the durable ``StateStore`` the ownership ledger lives in, or ``None`` if absent.

    Resolved EXACTLY as ``api/routes/evidence.py`` does: off ``request.app.state.state_ledger.store``
    (a handle stashed at startup; ``None`` when the ledger is dark). Defensive ``getattr`` so a
    TestClient that never ran the lifespan, or a dark deployment, yields ``None`` rather than raising.
    """
    handle = getattr(request.app.state, "state_ledger", None)
    if handle is None:
        return None
    return getattr(handle, "store", None)


def _require_packet_ownership(request: Request, trace_id: str) -> None:
    """G3 tenant-ownership gate for the EP explainer — fail closed, 404 (never 403/500).

    Mirrors ``api/routes/evidence.py``'s ``_require_evidence_access``:

    * ``settings.accounts_enabled`` False (dark default) -> complete no-op. The legacy shared-secret
      posture is unchanged; the route is gated only by the JWT the auth middleware already validated.
    * ``settings.accounts_enabled`` True -> resolve the SERVER-set tenant (``current_tenant`` raises
      401 with no account-mode identity), obtain the ``StateStore``, and require that this tenant OWNS
      the trace. If not — including the fail-closed case where account mode is on but no store is
      installed — raise **404** (no existence leak, and the projection is NEVER built).
    """
    if not settings.accounts_enabled:
        return

    tenant_id = current_tenant(request)
    store = _explainer_state_store(request)
    if store is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
    if not tenant_owns_trace(store, tenant_id=tenant_id, trace_id=trace_id):
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)


def _load_owned_packet_payload(trace_id: str) -> dict[str, Any]:
    """Resolve the RAW Evidence Packet payload for ``trace_id``, preserving its recorded verdict.

    The explainer must echo the packet's OWN verdict, so we deliberately read the raw packet (the
    Stage 9 40E registry first, then the general builder) rather than the public-read-gated GET view
    that can downgrade ACCEPT->FLAG. Ownership is enforced by ``_require_packet_ownership`` BEFORE
    this is called; a trace that does not resolve raises ``FileNotFoundError`` (mapped to 404 by the
    caller).
    """
    # Imported here (not at module load) to avoid a heavy import chain on the chat-only path.
    from api.routes.evidence import (
        build_packet_for_trace,
        load_stage9_40e_packet_payload_for_trace,
    )

    try:
        # Raw Stage 9 40E payload — verdict preserved verbatim (no public-read gate).
        return load_stage9_40e_packet_payload_for_trace(trace_id)
    except FileNotFoundError:
        pass
    # General EvidencePacket builder (dev fixture, reference packet, merged-fleet, on-disk traces).
    return build_packet_for_trace(trace_id).model_dump(mode="json")


def _segment_models(segments: tuple[ExplainSegment, ...]) -> list[ExplainPacketSegment]:
    return [ExplainPacketSegment(text=seg.text, refs=list(seg.refs)) for seg in segments]


def _to_response(result: ExplainPacketResult) -> ExplainPacketResponse:
    return ExplainPacketResponse(
        trace_id=result.trace_id,
        verdict_echo=result.verdict_echo,
        segments=_segment_models(result.segments),
        investigate_next=_segment_models(result.investigate_next),
        used_gemini=result.used_gemini,
        model=result.model,
        safety_mode=result.safety_mode,
        disclaimer=result.disclaimer,
    )


@router.post("/explainer/evidence/{trace_id}", response_model=ExplainPacketResponse)
async def explain_evidence_packet(trace_id: str, request: Request) -> ExplainPacketResponse:
    """Return a cited, plain-English reading aid for the Evidence Packet ``trace_id`` (spec §7/§8).

    JWT-protected by the global auth middleware (like ``/explainer/chat``). Flow:
      1. G3 ownership gate — resolve the EP ONLY if the caller's tenant owns the trace, else 404
         (the projection is never built for a non-owned trace).
      2. Resolve the raw packet payload (verdict preserved).
      3. ``explain_evidence`` builds the redacted projection, calls Gemini under the strict system
         prompt, and validates fail-closed (verdict-echo match, cited segments, no deny-list leak).
      4. Map to the §7 contract. A degraded result (validation failed / no key) carries only the raw
         verdict with empty segments, which the UI surfaces as "AI summary unavailable".
    """
    # G3 FIRST — before any packet load or projection build.
    _require_packet_ownership(request, trace_id)

    try:
        packet_payload = _load_owned_packet_payload(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)

    result = await explain_evidence(packet_payload, trace_id=trace_id)
    return _to_response(result)
