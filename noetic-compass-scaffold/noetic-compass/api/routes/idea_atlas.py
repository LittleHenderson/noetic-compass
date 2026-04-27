"""Idea Atlas — backend scaffolding (Sprint 1).

Personal cognitive mapping endpoints. The user submits a natural-language idea;
the casivenizer translates it to a CAS expression via an LLM connector and
validates it through the existing CAS notation compiler. Persisted ideas are
later rendered as a force-directed graph (later sprint, Agent F).

All routes require JWT auth (handled by JWTAuthMiddleware globally).
The user identity is read from request.state.user (the JWT `sub` claim).

Persistence: dual-path — uses SQLAlchemy + Postgres when NC_DATABASE_URL is set,
falls back to a per-process in-memory dict otherwise (matches api/store.py
pattern). The DB-backed path uses the Idea model in api/models_db.py.
"""

from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.config import settings
from api.llm_connectors.registry import get_connector
from api.notation.compiler import compile_expression
from api.notation.inversion import (
    AXIS_DESCRIPTIONS,
    DEFERRED_AXES,
    DeferredAxisError,
    UnknownAxisError,
    invert_expression,
)
from api.similarity.cosine import cas_similarity


router = APIRouter(prefix="/idea_atlas", tags=["idea_atlas"])

DEFAULT_SIMILARITY_THRESHOLD = 0.2


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CasivenizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class CasivenizeResponse(BaseModel):
    expression: str
    valid: bool
    ast: dict | None = None
    error: str | None = None


class IdeaCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    cas_expression: str | None = None


class IdeaRecord(BaseModel):
    id: str
    user_id: str
    text: str
    cas_expression: str | None
    ast_json: dict | None
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class EdgeRecord(BaseModel):
    """One similarity edge between two of the user's persisted ideas.

    Sprint 2: drives the dashboard force-directed graph view. The
    ``breakdown`` mirrors :func:`api.similarity.cosine.cas_similarity`'s
    per-axis decomposition (noetic / domain / drive / register / metaset)
    so the frontend can render the dominant overlap reason on hover.
    """

    source: str
    target: str
    score: float
    breakdown: dict[str, float]


class InvertRequest(BaseModel):
    idea_id: str = Field(min_length=1)
    axis: str = Field(min_length=1, max_length=2)


class InvertResponse(BaseModel):
    original_idea: IdeaRecord
    inverted_cas: str
    inverted_ast: dict | None
    axis: str
    axis_description: str


# ---------------------------------------------------------------------------
# Casivenizer — LLM-driven NL -> CAS expression translation
# ---------------------------------------------------------------------------


CASIVENIZE_SYSTEM_PROMPT = (
    "You are a CAS (Cognitive Architecture System) notation compiler. "
    "Translate the user's natural-language idea into a SINGLE valid CAS expression "
    "and emit nothing else. Do not explain, do not narrate, output only the "
    "expression on a single line.\n\n"
    "CAS notation cheat-sheet:\n"
    "  - 10 Noetics: CO-0 (Idea), CO-1 (Mind), CO-2 (Positive), CO-3 (Negative), "
    "CO-4 (Vibration), CO-5 (Female), CO-6 (Male), CO-7 (Rhythm), "
    "CO-8 (Above/Cause), CO-9 (Below/Effect).\n"
    "  - 4 Domains: P (Principled), C (Cognitive), E (Evaluative), O (Operational). "
    "Domain order: P > C > E > O.\n"
    "  - 7 Drives: F1 (Unity), F2 (Wisdom), F3 (Vitality), F4 (Connection), "
    "F5 (Agency), F6 (Structure), F7 (Purpose).\n"
    "  - State syntax: CO-n^D_{Fk}  (e.g., CO-2^C_{F2})\n"
    "  - Optional Register suffix: |T, |A, |f, |E (e.g., CO-3^P_{F2}|A)\n"
    "  - Relations use ->, integration uses x.\n\n"
    "Example translations:\n"
    "  'I want to deeply understand wisdom' -> CO-2^C_{F2}\n"
    "  'Practicing self-discipline daily'   -> CO-7^O_{F6}\n"
    "  'Feeling drawn to creative work'      -> CO-2^E_{F4}|f\n\n"
    "Output ONE expression only."
)

# Match a CAS expression starting with CO-n. Permissive — the compiler is the
# real validator.
_CAS_EXPR_RE = re.compile(
    r"CO-\d[^\n\r]*",
)


def _extract_expression(raw: str) -> str:
    """Pluck the most plausible CAS expression out of an LLM response."""
    text = raw.strip()
    # Strip leading/trailing markdown fences or quote chars if present
    text = re.sub(r"^[`'\"]+|[`'\"]+$", "", text).strip()
    # If the model emitted just a state, return as-is
    if text.startswith("CO-"):
        # take the first line only
        return text.splitlines()[0].strip()
    match = _CAS_EXPR_RE.search(text)
    if match:
        return match.group(0).strip()
    # Last resort — return the trimmed text and let the compiler reject it
    return text.splitlines()[0].strip() if text else ""


def _resolve_casivenizer_provider() -> tuple[str, str | None]:
    """Resolve LLM provider/model for casivenize.

    Honors NC_CASIVENIZER_MODEL env var (format: "provider" or "provider:model").
    Defaults to "mock" so tests and unconfigured environments work out of the box.
    """
    raw = os.getenv("NC_CASIVENIZER_MODEL", "").strip()
    if not raw:
        return ("mock", None)
    if ":" in raw:
        provider, model = raw.split(":", 1)
        return (provider.strip() or "mock", model.strip() or None)
    return (raw, None)


async def _casivenize_via_llm(text: str) -> str:
    """Call the configured LLM connector to translate text -> CAS expression.

    For the mock connector (tests, default dev) the mock does not natively
    emit CAS expressions, so we fall back to the existing signal-analyzer +
    synthesizer pipeline used by /notation/analyze. This keeps the round-trip
    deterministic without a live LLM.
    """
    provider, model = _resolve_casivenizer_provider()
    if provider == "mock":
        return _synthesize_from_signals(text)

    connector = get_connector(provider, model=model)
    response = await connector.generate(
        prompt=text,
        system_prompt=CASIVENIZE_SYSTEM_PROMPT,
    )
    expression = _extract_expression(response.text)
    if not expression:
        # If the LLM was unhelpful, fall back to deterministic synthesis so
        # the caller always gets *something* parseable to inspect.
        return _synthesize_from_signals(text)
    return expression


def _synthesize_from_signals(text: str) -> str:
    """Deterministic fallback: derive a CAS expression from text signals."""
    from api.pipeline.notation_synthesizer import synthesize_notation
    from api.pipeline.text_signal_analyzer import analyze_text_signals

    signals = analyze_text_signals(text)
    drive_chains = []
    for score in signals.drive_scores:
        d = score
        w = round(d * 0.8, 4)
        p = round(w * 0.7, 4)
        drive_chains.append([d, w, p])

    result = synthesize_notation(
        operator_scores=[s / 10.0 for s in signals.operator_scores],
        raw_scores_0_to_10=signals.operator_scores,
        domain_averages=signals.domain_scores,
        drive_chains=drive_chains,
        a0_score=min(1.0, signals.word_count / 100.0),
        rpm_completeness=signals.rpm_signal,
        inversion_axis_scores=[0.8] * 7,
        fractal_sequence=None,
        fractal_classification=None,
    )
    # If the synthesizer produced nothing usable, emit a safe identity-state
    # so the compiler always has a chance to succeed. Otherwise return the
    # full synthesized source — the compiler accepts multi-statement CAS
    # programs (e.g., a state expression plus a Phi<...> activation summary).
    return result.source.strip() if result.source else "CO-0^C_{F1}"


def casivenize(text: str) -> CasivenizeResponse:
    """Synchronous fallback used by tests and the /ideas POST path.

    Note: this wrapper is sync because the heavy lifting is the synthesizer
    in the mock path. Real LLM providers are async; the route handler awaits
    _casivenize_via_llm directly.
    """
    raise NotImplementedError  # not used; route handlers call _casivenize_via_llm


# ---------------------------------------------------------------------------
# Storage layer — DB-backed when configured, else in-memory
# ---------------------------------------------------------------------------


_memory_ideas: dict[str, list[dict[str, Any]]] = defaultdict(list)


def _use_db() -> bool:
    return bool(settings.database_url)


def _record_to_dict(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize an in-memory record (datetimes are already strings)."""
    return {**record}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _inmem_create(
    user_id: str, text: str, cas_expression: str | None, ast_json: dict | None
) -> dict[str, Any]:
    record_id = str(uuid.uuid4())
    now = _now_iso()
    record = {
        "id": record_id,
        "user_id": user_id,
        "text": text,
        "cas_expression": cas_expression,
        "ast_json": ast_json,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _memory_ideas[user_id].append(record)
    return record


def _inmem_list(user_id: str) -> list[dict[str, Any]]:
    return [r for r in _memory_ideas.get(user_id, []) if r.get("deleted_at") is None]


def _inmem_get(user_id: str, idea_id: str) -> dict[str, Any] | None:
    for r in _memory_ideas.get(user_id, []):
        if r["id"] == idea_id and r.get("deleted_at") is None:
            return r
    return None


def _inmem_delete(user_id: str, idea_id: str) -> bool:
    for r in _memory_ideas.get(user_id, []):
        if r["id"] == idea_id and r.get("deleted_at") is None:
            r["deleted_at"] = _now_iso()
            r["updated_at"] = r["deleted_at"]
            return True
    return False


def clear_memory_ideas() -> None:
    """Test helper — wipe the in-memory idea store."""
    _memory_ideas.clear()


# ---------------------------------------------------------------------------
# DB-backed implementations (only invoked when settings.database_url is set)
# ---------------------------------------------------------------------------


def _orm_to_dict(idea: Any) -> dict[str, Any]:
    return {
        "id": str(idea.id),
        "user_id": idea.user_id,
        "text": idea.text,
        "cas_expression": idea.cas_expression,
        "ast_json": idea.ast_json,
        "created_at": idea.created_at.isoformat() if idea.created_at else None,
        "updated_at": idea.updated_at.isoformat() if idea.updated_at else None,
        "deleted_at": idea.deleted_at.isoformat() if idea.deleted_at else None,
    }


async def _db_create(
    user_id: str, text: str, cas_expression: str | None, ast_json: dict | None
) -> dict[str, Any]:
    from api.db import async_session_factory
    from api.models_db import Idea

    record_id = uuid.uuid4()
    async with async_session_factory() as session:
        idea = Idea(
            id=record_id,
            user_id=user_id,
            text=text,
            cas_expression=cas_expression,
            ast_json=ast_json,
        )
        session.add(idea)
        await session.commit()
        await session.refresh(idea)
        return _orm_to_dict(idea)


async def _db_list(user_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import select

    from api.db import async_session_factory
    from api.models_db import Idea

    async with async_session_factory() as session:
        stmt = (
            select(Idea)
            .where(Idea.user_id == user_id, Idea.deleted_at.is_(None))
            .order_by(Idea.created_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [_orm_to_dict(r) for r in rows]


async def _db_get(user_id: str, idea_id: str) -> dict[str, Any] | None:
    from sqlalchemy import select

    from api.db import async_session_factory
    from api.models_db import Idea

    try:
        parsed_id = uuid.UUID(idea_id)
    except ValueError:
        return None

    async with async_session_factory() as session:
        stmt = select(Idea).where(
            Idea.id == parsed_id,
            Idea.user_id == user_id,
            Idea.deleted_at.is_(None),
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        return _orm_to_dict(row) if row else None


async def _db_delete(user_id: str, idea_id: str) -> bool:
    from sqlalchemy import select

    from api.db import async_session_factory
    from api.models_db import Idea

    try:
        parsed_id = uuid.UUID(idea_id)
    except ValueError:
        return False

    async with async_session_factory() as session:
        stmt = select(Idea).where(
            Idea.id == parsed_id,
            Idea.user_id == user_id,
            Idea.deleted_at.is_(None),
        )
        idea = (await session.execute(stmt)).scalar_one_or_none()
        if idea is None:
            return False
        idea.deleted_at = datetime.now(tz=timezone.utc)
        idea.updated_at = idea.deleted_at
        await session.commit()
        return True


# Public storage interface — picks DB or in-memory automatically.


async def create_idea(
    user_id: str, text: str, cas_expression: str | None, ast_json: dict | None
) -> dict[str, Any]:
    if _use_db():
        return await _db_create(user_id, text, cas_expression, ast_json)
    return _inmem_create(user_id, text, cas_expression, ast_json)


async def list_ideas(user_id: str) -> list[dict[str, Any]]:
    if _use_db():
        return await _db_list(user_id)
    return _inmem_list(user_id)


async def get_idea(user_id: str, idea_id: str) -> dict[str, Any] | None:
    if _use_db():
        return await _db_get(user_id, idea_id)
    return _inmem_get(user_id, idea_id)


async def delete_idea(user_id: str, idea_id: str) -> bool:
    if _use_db():
        return await _db_delete(user_id, idea_id)
    return _inmem_delete(user_id, idea_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _current_user(request: Request) -> str:
    user = getattr(getattr(request, "state", None), "user", None)
    if not user or user == "anonymous":
        # Should never happen — JWTAuthMiddleware enforces auth — but be defensive.
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.post("/casivenize", response_model=CasivenizeResponse)
async def casivenize_route(req: CasivenizeRequest, request: Request) -> CasivenizeResponse:
    """Translate natural-language text -> CAS expression via LLM, then validate."""
    _current_user(request)  # enforce auth (middleware already did, defensive)
    expression = await _casivenize_via_llm(req.text)
    artifact = compile_expression(expression)
    ast_dict: dict | None = None
    if artifact.valid and artifact.ast is not None:
        payload = artifact.to_dict()
        ast_dict = payload.get("ast")
    return CasivenizeResponse(
        expression=expression,
        valid=artifact.valid,
        ast=ast_dict,
        error=artifact.error,
    )


@router.post("/ideas", response_model=IdeaRecord)
async def create_idea_route(req: IdeaCreateRequest, request: Request) -> IdeaRecord:
    """Persist an idea. If cas_expression is null, casivenize first."""
    user_id = _current_user(request)

    cas_expression = req.cas_expression
    ast_dict: dict | None = None

    if cas_expression is None:
        cas_expression = await _casivenize_via_llm(req.text)

    if cas_expression:
        artifact = compile_expression(cas_expression)
        if artifact.valid and artifact.ast is not None:
            ast_dict = artifact.to_dict().get("ast")
        # We persist the expression even if invalid — the caller sees ast_json=None
        # and can decide to re-casivenize. Mirrors the "let the caller decide"
        # contract on /casivenize.

    record = await create_idea(
        user_id=user_id,
        text=req.text,
        cas_expression=cas_expression,
        ast_json=ast_dict,
    )
    return IdeaRecord(**record)


@router.get("/ideas", response_model=list[IdeaRecord])
async def list_ideas_route(request: Request) -> list[IdeaRecord]:
    """List ideas for the current authenticated user (newest first)."""
    user_id = _current_user(request)
    rows = await list_ideas(user_id)
    # Newest first
    rows = sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True)
    return [IdeaRecord(**r) for r in rows]


@router.get("/ideas/{idea_id}", response_model=IdeaRecord)
async def get_idea_route(idea_id: str, request: Request) -> IdeaRecord:
    """Single idea detail."""
    user_id = _current_user(request)
    record = await get_idea(user_id, idea_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return IdeaRecord(**record)


@router.delete("/ideas/{idea_id}")
async def delete_idea_route(idea_id: str, request: Request) -> dict:
    """Soft-delete an idea (sets deleted_at)."""
    user_id = _current_user(request)
    ok = await delete_idea(user_id, idea_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"id": idea_id, "deleted": True}


# ---------------------------------------------------------------------------
# Sprint 2: similarity-driven graph edges
# ---------------------------------------------------------------------------


@router.get("/edges", response_model=list[EdgeRecord])
async def list_edges_route(
    request: Request, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> list[EdgeRecord]:
    """Compute pairwise CAS similarity edges across the user's ideas.

    Returns a flat array of ``{source, target, score, breakdown}`` entries
    sorted by descending score. Pairs with ``score < similarity_threshold``
    are filtered out. The default is intentionally gentle enough to surface
    single-axis matches, such as two ideas sharing only a Domain, so first-use
    graphs do not look falsely disconnected. Ideas with no compiled CAS
    expression are skipped (they cannot participate in a similarity
    comparison).

    The threshold is clamped to ``[0, 1]``.
    """
    user_id = _current_user(request)
    threshold = max(0.0, min(1.0, float(similarity_threshold)))

    rows = await list_ideas(user_id)
    # Only ideas with a non-null cas_expression can produce a similarity
    # edge. The cosine module tolerates a non-compiling expression by
    # returning score=0, but we filter pre-emptively to skip wasted work.
    candidates = [r for r in rows if r.get("cas_expression")]

    edges: list[EdgeRecord] = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a = candidates[i]
            b = candidates[j]
            sim = cas_similarity(a["cas_expression"], b["cas_expression"])
            score = float(sim.get("score", 0.0))
            if score < threshold:
                continue
            edges.append(
                EdgeRecord(
                    source=a["id"],
                    target=b["id"],
                    score=score,
                    breakdown={k: float(v) for k, v in sim.get("breakdown", {}).items()},
                )
            )

    edges.sort(key=lambda e: e.score, reverse=True)
    return edges


# ---------------------------------------------------------------------------
# Sprint 3: 7-axis inversion preview
# ---------------------------------------------------------------------------


@router.post("/invert", response_model=InvertResponse)
async def invert_idea_route(req: InvertRequest, request: Request) -> InvertResponse:
    """Preview an axis-specific inversion of one persisted idea.

    Does NOT mutate or persist a new idea — that is the dashboard's job
    after the user reviews the preview. Returns the original idea record
    alongside the inverted CAS expression and AST.

    Failure modes:
      - 404 — idea not found / not owned by the caller.
      - 400 — idea has no compiled CAS expression to invert.
      - 422 — the inverted source did not compile cleanly (the axis
              transformation produced something the parser rejected).
      - 501 — axis is one of E / S / A (deferred to a later sprint).
    """
    user_id = _current_user(request)
    axis = req.axis.upper()

    record = await get_idea(user_id, req.idea_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    cas = record.get("cas_expression")
    if not cas:
        raise HTTPException(
            status_code=400,
            detail="Idea has no CAS expression to invert. Casivenize it first.",
        )

    if axis in DEFERRED_AXES:
        # 501 with a structured body so the frontend can render
        # "coming in a later sprint" rather than a generic error.
        raise HTTPException(
            status_code=501,
            detail={
                "axis": axis,
                "message": (
                    f"Inversion axis '{axis}' is not implemented in Sprint 3. "
                    "It is scheduled for a future sprint."
                ),
                "description": AXIS_DESCRIPTIONS.get(axis, ""),
                "implemented_axes": ["N", "W", "F", "P"],
                "deferred_axes": list(DEFERRED_AXES),
            },
        )

    try:
        result = invert_expression(cas, axis)
    except DeferredAxisError as exc:  # safety net — invert_expression already raises
        raise HTTPException(
            status_code=501,
            detail={
                "axis": exc.axis,
                "message": str(exc),
                "description": exc.description,
            },
        ) from exc
    except UnknownAxisError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown inversion axis '{axis}'. "
            f"Valid axes: N, W, F, E, S, A, P.",
        ) from exc

    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "axis": axis,
                "message": "Inverted expression failed to compile.",
                "inverted_source": result.inverted,
                "compiler_error": result.error,
            },
        )

    return InvertResponse(
        original_idea=IdeaRecord(**record),
        inverted_cas=result.inverted,
        inverted_ast=result.ast,
        axis=axis,
        axis_description=result.description,
    )
