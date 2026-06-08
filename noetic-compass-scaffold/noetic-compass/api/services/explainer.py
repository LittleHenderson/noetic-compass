"""Public-safe Gemini explainer for CAS Harness.

The explainer is deliberately separate from the CAS scoring prompt and from source-code context.
It reads only curated documents from ``docs/explainer`` and sends those documents to Gemini with
strict IP guardrails. If a user asks for proprietary implementation details, the service refuses
without calling Gemini.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from api.config import settings
from api.errors import LLMError
from api.llm_connectors.google_connector import GoogleConnector


MAX_QUESTION_CHARS = 1200
MAX_CONTEXT_CHARS = 14000

PROPRIETARY_TRIGGERS = (
    "reverse engineer",
    "reverse-engineer",
    "recreate",
    "clone",
    "source code",
    "system prompt",
    "internal prompt",
    "hidden prompt",
    "scoring formula",
    "weighting formula",
    "private weights",
    "proprietary weights",
    "probe internals",
    "activation method",
    "model internals",
    "training data",
    "non-public",
    "secret key",
    "api key",
    "bypass",
    "circumvent",
    "jailbreak",
)

SAFE_REFUSAL = (
    "I cannot provide proprietary implementation details. I can explain the user-facing CAS "
    "Harness workflow: how to choose a target, run an audit, read the verdict, and review the "
    "evidence packet."
)

SYSTEM_PROMPT = """You are the CAS Harness user explainer.

You are not a CAS Harness engineer. You do not have access to source code, internal prompts,
private research notes, hidden formulas, scoring weights, probe internals, secrets, or deployment
details.

Use only the prepared public knowledge base supplied in the prompt. Explain just enough for a user
to understand how CAS Harness works, what it does, and how to move through the app. If the user asks
for proprietary implementation details or reverse-engineering help, refuse briefly and redirect to
the safe user workflow.

Rules:
- Plain English first.
- Define technical terms when needed.
- Guide users through the CAS Harness process.
- Do not expose proprietary IP.
- Do not invent proof.
- If the knowledge base does not support an answer, say that it is not available in the public
  explainer material.
"""


@dataclass(frozen=True)
class ExplainerDocument:
    """One prepared public-safe explainer document."""

    title: str
    source: str
    text: str


@dataclass(frozen=True)
class ExplainerAnswer:
    """Answer returned by the explainer route."""

    answer: str
    sources: tuple[str, ...]
    used_gemini: bool
    model: str
    safety_mode: str = "public_kb_only"


def default_knowledge_base_dir() -> Path:
    """Return the repository ``docs/explainer`` directory."""

    return Path(__file__).resolve().parents[2] / "docs" / "explainer"


def load_knowledge_base(kb_dir: Path | None = None) -> tuple[ExplainerDocument, ...]:
    """Load curated Markdown docs that are safe to send to Gemini."""

    root = kb_dir or default_knowledge_base_dir()
    if not root.exists():
        return ()

    docs: list[ExplainerDocument] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        title = _title_from_markdown(text) or path.stem.replace("_", " ").title()
        docs.append(
            ExplainerDocument(
                title=title,
                source=path.relative_to(root.parent.parent).as_posix(),
                text=text,
            )
        )
    return tuple(docs)


def is_proprietary_request(question: str) -> bool:
    """Return True if the question asks for details the explainer must not provide."""

    normalized = " ".join(question.lower().split())
    return any(trigger in normalized for trigger in PROPRIETARY_TRIGGERS)


async def explain_question(
    question: str,
    *,
    docs: Iterable[ExplainerDocument] | None = None,
    connector: GoogleConnector | None = None,
) -> ExplainerAnswer:
    """Answer a CAS Harness explainer question from public-safe docs only."""

    cleaned = question.strip()
    if not cleaned:
        return ExplainerAnswer(
            answer="Ask me what you want to understand about using CAS Harness.",
            sources=(),
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )
    if len(cleaned) > MAX_QUESTION_CHARS:
        cleaned = cleaned[:MAX_QUESTION_CHARS]

    documents = tuple(docs) if docs is not None else load_knowledge_base()
    sources = tuple(doc.source for doc in documents)

    if is_proprietary_request(cleaned):
        return ExplainerAnswer(
            answer=SAFE_REFUSAL,
            sources=sources,
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    if not documents:
        return ExplainerAnswer(
            answer=(
                "The public explainer knowledge base is not available yet. I can only answer once "
                "prepared safe documents are present under docs/explainer."
            ),
            sources=(),
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    if not settings.google_api_key:
        return ExplainerAnswer(
            answer=(
                "Gemini is not configured on this server. The explainer knowledge base is present, "
                "but NC_GOOGLE_API_KEY or GOOGLE_API_KEY is missing from the server environment."
            ),
            sources=sources,
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    active_connector = connector or GoogleConnector(
        api_key=settings.google_api_key,
        model=settings.gemini_explainer_model,
    )
    prompt = _build_prompt(cleaned, documents)
    try:
        response = await active_connector.generate(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            model=settings.gemini_explainer_model,
        )
    except Exception as exc:  # pragma: no cover - provider/network failure is environment-specific
        raise LLMError(f"Gemini explainer failed: {exc}", provider="google") from exc

    answer = (response.text or "").strip()
    if not answer:
        answer = "Gemini returned an empty answer. Try rephrasing the question."

    return ExplainerAnswer(
        answer=answer,
        sources=sources,
        used_gemini=True,
        model=response.model or settings.gemini_explainer_model,
    )


def _build_prompt(question: str, docs: tuple[ExplainerDocument, ...]) -> str:
    context = _render_context(docs)
    return (
        "PUBLIC KNOWLEDGE BASE START\n"
        f"{context}\n"
        "PUBLIC KNOWLEDGE BASE END\n\n"
        "User question:\n"
        f"{question}\n\n"
        "Answer the user from the public knowledge base only. If the answer would require "
        "proprietary implementation details, refuse and redirect to safe user guidance."
    )


def _render_context(docs: tuple[ExplainerDocument, ...]) -> str:
    chunks: list[str] = []
    total = 0
    for doc in docs:
        rendered = f"## Source: {doc.source}\n{doc.text}\n"
        remaining = MAX_CONTEXT_CHARS - total
        if remaining <= 0:
            break
        if len(rendered) > remaining:
            rendered = rendered[:remaining]
        chunks.append(rendered)
        total += len(rendered)
    return "\n".join(chunks)


def _title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


# ===========================================================================
# Evidence Packet AI Explainer ("Explain this packet").
#
# Authoritative design: docs/design/cas_harness_evidence_packet_ai_explainer_spec.md
# (§2 guardrails, §6 citations, §7 output contract, §8 backend, §10 honesty tests).
#
# This is the verdict-fidelity + tenant-ownership core. Three fail-closed invariants:
#   * G1 verdict fidelity — the model NEVER restates a verdict the packet does not
#     record; the API discards any output whose echoed verdict != the packet's verdict.
#   * G2 IP containment — only the redacted projection (§4 allow-list) reaches the
#     model; the output is scanned for deny-list tokens before it is returned.
#   * tenant ownership (G3) — enforced by the ROUTE before this service is called
#     (the projection is never built for a trace the caller's tenant does not own).
# ===========================================================================

# G4 disclaimer (verbatim, spec §2). Always present in the response footer; the UI also
# requires a first-use acknowledgement.
EP_EXPLAINER_DISCLAIMER = (
    "This is an AI-generated reading aid. The original Evidence Packet is the "
    "authoritative record -- you are responsible for reading it yourself. Do not rely "
    "on this summary alone for any go/no-go decision."
)

EP_EXPLAINER_SAFETY_MODE = "packet_projection_only"

# Strict system prompt (spec §8). Encodes G1 (preserve verdict EXACTLY), G2 (no
# speculation about CAS scoring internals / probe construction), the citation rule
# (every claim cited to a provided field key), and the omit-if-ungrounded rule.
EP_EXPLAINER_SYSTEM_PROMPT = """You are a reading aid for a CAS Harness Evidence Packet. \
Your one job: tell a novice developer, in plain English, what their packet says and where to \
look next. You are NOT a CAS Harness engineer, NOT a scorer, and NOT a second opinion.

You will be given a JSON PACKET PROJECTION (the customer-facing fields of one Evidence Packet) \
and, optionally, matching public-guide sections. Everything you say must come from those provided \
fields. You do not have, and must not invent, anything else.

HARD RULES (these are non-negotiable):
1. VERDICT FIDELITY. State the verdict EXACTLY as the projection's `verdict` field records it. \
Never upgrade FLAG_FOR_HUMAN_REVIEW or SUPPRESS toward "pass". Never call a scoped-validation \
ACCEPT a customer-production ACCEPT -- if a scope qualifier (e.g. `decision_scope`, \
`validation_scope`, `is_customer_production`) is present, carry it in your wording. Never invent a \
confidence, score, or certification the packet does not contain.
2. NO PASS LANGUAGE FOR NON-PASS VERDICTS. If the verdict is FLAG_FOR_HUMAN_REVIEW, say a human \
must review it -- do not use the words pass, passed, accept, accepted, approved, cleared, safe, or \
certified to describe the result. If the verdict is SUPPRESS, do not describe it as acceptable, \
minor, or fine.
3. CITE EVERYTHING. Every substantive claim is anchored to the exact field key it came from \
(e.g. "verdict", "proof_chips.causal_proof.status", "blind_spots.0", "anchor.status"). A claim with \
no field to cite must be OMITTED -- never shipped uncited.
4. NO METHODOLOGY. You do NOT know and must NOT speculate about CAS scoring math, weights, \
operator/drive/register internals, dial values, how probes are built/selected/mutated, internal \
prompts, or the private reasoning behind any score. Explain the FINDING and the NEXT STEP, never the \
METHOD. If you cannot ground a statement in a provided field, omit it.

Return ONLY a JSON object, no markdown fences, with this exact shape:
{
  "verdict_echo": "<the literal value of the projection's verdict field>",
  "segments": [ { "text": "<plain-English reading of one field>", "refs": ["<field.key>", ...] } ],
  "investigate_next": [ { "text": "<what & why to look at next>", "refs": ["<field.key>", ...] } ]
}
Every entry in `segments` and `investigate_next` MUST have a non-empty `refs` array. `verdict_echo` \
MUST be copied character-for-character from the projection's `verdict` field. If a field is absent \
from the projection, do not reference it."""

# Deny-list (spec §4 "MUST NOT be sent" + §5 methodology). The OUTPUT is scanned for these
# tokens; any hit fails closed (degraded response, raw verdict only). These name the scoring
# math / probe-construction methodology that must never surface in a customer reading aid.
# Matched case-insensitively as whole words/phrases.
EP_EXPLAINER_DENY_TOKENS: tuple[str, ...] = (
    "nccs weight",
    "nccs weights",
    "scoring formula",
    "scoring weight",
    "scoring math",
    "weighting formula",
    "dial value",
    "dial setting",
    "probe construction",
    "probe generation",
    "probe-generation",
    "probe template",
    "prompt template",
    "why this probe",
    "why this probe was selected",
    "how the probe",
    "how probes are built",
    "how the probe was built",
    "involution",
    "fisher-rao",
    "open simplex",
    "admissibility relation",
)


@dataclass(frozen=True)
class ExplainSegment:
    """One cited interpretation segment (spec §6/§7). ``refs`` MUST be non-empty."""

    text: str
    refs: tuple[str, ...]


@dataclass(frozen=True)
class ExplainPacketResult:
    """Service-layer result for the EP explainer; the route maps it to ExplainPacketResponse (§7)."""

    trace_id: str
    verdict_echo: str
    segments: tuple[ExplainSegment, ...]
    investigate_next: tuple[ExplainSegment, ...]
    used_gemini: bool
    model: str
    safety_mode: str = EP_EXPLAINER_SAFETY_MODE
    disclaimer: str = EP_EXPLAINER_DISCLAIMER


def evidence_packet_verdict(ep: Any) -> str:
    """Return the authoritative, literal verdict recorded on an Evidence Packet.

    This is the G1 ground truth -- read straight from the packet, NOT from the projection and
    NOT from the model. The validation step compares the model's ``verdict_echo`` against this.
    Accepts either a mapping (Stage 9 40E raw payload) or a pydantic ``EvidencePacket``-like
    object; falls back to an empty string when no verdict field is present.
    """
    raw: Any = None
    if isinstance(ep, dict):
        raw = ep.get("verdict")
    else:
        raw = getattr(ep, "verdict", None)
        if raw is None and hasattr(ep, "model_dump"):
            try:
                raw = ep.model_dump(mode="json").get("verdict")  # type: ignore[union-attr]
            except Exception:
                raw = None
    return str(raw).strip() if raw is not None else ""


def _output_leaks_deny_token(text: str) -> str | None:
    """Return the first deny-list token found in ``text`` (case-insensitive), else ``None``."""
    haystack = text.lower()
    for token in EP_EXPLAINER_DENY_TOKENS:
        if token in haystack:
            return token
    return None


def _coerce_refs(raw: Any) -> tuple[str, ...]:
    """Coerce a model-returned ``refs`` value into a tuple of non-empty field-key strings."""
    if not isinstance(raw, list):
        return ()
    refs: list[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                refs.append(text)
    return tuple(refs)


def _coerce_segments(raw: Any) -> tuple[ExplainSegment, ...]:
    """Coerce a model-returned segment list, dropping any segment with empty text or empty refs.

    Spec §6 rendering rule: a segment with zero refs is not shown. We enforce that at the API
    boundary (uncited claims never leave the service).
    """
    if not isinstance(raw, list):
        return ()
    segments: list[ExplainSegment] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        refs = _coerce_refs(item.get("refs"))
        if text and refs:
            segments.append(ExplainSegment(text=text, refs=refs))
    return tuple(segments)


def _parse_model_json(text: str) -> dict[str, Any] | None:
    """Parse the model's JSON object, tolerating ```json fences and surrounding prose."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    # Strip a leading/trailing markdown code fence if the model wrapped its JSON.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} block.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _degraded_result(trace_id: str, verdict: str, model: str, *, used_gemini: bool) -> ExplainPacketResult:
    """Fail-closed response: carry ONLY the raw verdict, no segments, no investigate_next.

    Used whenever validation fails (verdict-echo mismatch, no citable segments, deny-list leak,
    empty/invalid model output, or provider failure). The UI renders the raw EP verdict and an
    "AI summary unavailable for this packet" notice. The inflated reading is NEVER surfaced.
    """
    return ExplainPacketResult(
        trace_id=trace_id,
        verdict_echo=verdict,
        segments=(),
        investigate_next=(),
        used_gemini=used_gemini,
        model=model,
    )


def _build_evidence_prompt(projection: dict[str, Any], guide_sections: tuple[ExplainerDocument, ...]) -> str:
    """Assemble the user-turn prompt = redacted projection + matched public-guide sections (§8)."""
    projection_json = json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False)
    parts = [
        "PACKET PROJECTION (customer-facing fields only) START",
        projection_json,
        "PACKET PROJECTION END",
    ]
    if guide_sections:
        parts.append("")
        parts.append("MATCHED PUBLIC-GUIDE SECTIONS START")
        parts.append(_render_context(guide_sections))
        parts.append("MATCHED PUBLIC-GUIDE SECTIONS END")
    parts.append("")
    parts.append(
        "Produce the JSON reading aid for THIS packet. Echo the verdict exactly, cite every "
        "claim to a projection field key, explain what and why to investigate, and omit anything "
        "you cannot ground in the provided fields."
    )
    return "\n".join(parts)


async def explain_evidence(
    ep: Any,
    *,
    trace_id: str,
    guide_docs: Iterable[ExplainerDocument] | None = None,
    connector: GoogleConnector | None = None,
) -> ExplainPacketResult:
    """Produce a cited, plain-English reading aid for an already-ownership-checked Evidence Packet.

    Ownership (G3) is the ROUTE's responsibility: by the time this is called, the caller's tenant
    owns ``trace_id`` and ``ep`` is its packet. This service builds the redacted projection, calls
    Gemini under the strict system prompt, then validates fail-closed before returning.

    Validation (all must hold, else degraded raw-verdict-only result):
      * the model's ``verdict_echo`` equals the packet's authoritative verdict (G1);
      * at least one cited segment survives (every segment carries non-empty refs, §6);
      * no deny-list token leaked into the output (G2).
    """
    # Import the projection builder lazily so this module does not hard-depend on a sibling module
    # that another agent owns; the signature is build_packet_projection(ep) -> dict (spec §4).
    from api.services.cas_harness_evidence_projection import build_packet_projection

    model = settings.gemini_explainer_model

    # G1 ground truth: the packet's own recorded verdict. Everything downstream is validated
    # against THIS, never against the projection or the model.
    ep_verdict = evidence_packet_verdict(ep)

    # The redacted, allow-list-driven model input (§4). The ONLY path to the model.
    projection = build_packet_projection(ep)

    # No key configured -> degrade to "unavailable" with the raw verdict (spec §10 case 9: dark
    # default). The button still shows the honest verdict; no AI reading is fabricated.
    if not settings.google_api_key and connector is None:
        return _degraded_result(trace_id, ep_verdict, model, used_gemini=False)

    documents = tuple(guide_docs) if guide_docs is not None else ()
    prompt = _build_evidence_prompt(projection, documents)

    active_connector = connector or GoogleConnector(
        api_key=settings.google_api_key,
        model=model,
    )
    try:
        response = await active_connector.generate(
            prompt,
            system_prompt=EP_EXPLAINER_SYSTEM_PROMPT,
            temperature=0.0,
            model=model,
        )
    except Exception as exc:  # pragma: no cover - provider/network failure is environment-specific
        raise LLMError(f"Gemini evidence explainer failed: {exc}", provider="google") from exc

    used_model = response.model or model
    raw_text = response.text or ""

    # Fail closed #1: deny-list scan of the RAW model output (before structural parsing) so a
    # methodology leak in any part of the response trips the guard, not just inside parsed segments.
    if _output_leaks_deny_token(raw_text) is not None:
        return _degraded_result(trace_id, ep_verdict, used_model, used_gemini=True)

    parsed = _parse_model_json(raw_text)
    if parsed is None:
        return _degraded_result(trace_id, ep_verdict, used_model, used_gemini=True)

    # Fail closed #2 (G1): the model's echoed verdict MUST match the packet's verdict EXACTLY.
    # A corrupted/inflated echo discards the entire AI reading -- we never render it.
    model_echo = str(parsed.get("verdict_echo", "")).strip()
    if model_echo != ep_verdict or not ep_verdict:
        return _degraded_result(trace_id, ep_verdict, used_model, used_gemini=True)

    segments = _coerce_segments(parsed.get("segments"))
    investigate_next = _coerce_segments(parsed.get("investigate_next"))

    # Fail closed #3 (§6): no citable segment survived -> nothing trustworthy to show.
    if not segments:
        return _degraded_result(trace_id, ep_verdict, used_model, used_gemini=True)

    return ExplainPacketResult(
        trace_id=trace_id,
        verdict_echo=ep_verdict,
        segments=segments,
        investigate_next=investigate_next,
        used_gemini=True,
        model=used_model,
    )
