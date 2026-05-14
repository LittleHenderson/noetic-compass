"""Mode 7 Live SSE route.

Authenticated by the global JWT middleware. The route is intentionally local:
it builds a deterministic trace report from the prompt/expression and streams
SGGS-compatible commits from the CAS Native Thought Tree surface.
"""

from __future__ import annotations

import asyncio
import re
import sys
import time
import types
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.notation.compiler import compile_expression
from api.routes.idea_atlas import _synthesize_from_signals


router = APIRouter(prefix="/mode7", tags=["mode7"])


_IDENT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b")


def _ensure_cas_native_alias() -> None:
    """Expose the historical `cas-native/` directory as `cas_native`.

    CAS Native tests do the same aliasing in their conftest. The API process
    does not load that conftest, so the route creates the import alias lazily.
    """
    if "cas_native" in sys.modules:
        return

    package_root = Path(__file__).resolve().parents[2] / "cas-native"
    package = types.ModuleType("cas_native")
    package.__file__ = str(package_root / "__init__.py")
    package.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["cas_native"] = package


def _extract_identifiers(text: str) -> list[str]:
    return [m.group(0) for m in _IDENT_RE.finditer(text or "")]


def _slot_summary_for(text: str) -> dict[str, Any]:
    tokens = (text or "").split()
    identifier_count = sum(1 for token in tokens if _IDENT_RE.fullmatch(token.strip(".,;:()[]{}")))
    return {
        "length": len(tokens),
        "counts": {"0": max(0, len(tokens) - identifier_count), "2": identifier_count},
        "longest_stage_var_run": min(identifier_count, len(tokens)),
    }


def _validated_expression(prompt: str, expression: str | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    candidate = (expression or "").strip()
    if not candidate:
        candidate = _synthesize_from_signals(prompt)
        warnings.append("No expression supplied; used deterministic local synthesis.")

    artifact = compile_expression(candidate)
    if artifact.valid:
        return candidate, warnings

    fallback = "CO-0^C_{F1}"
    warnings.append(
        "Supplied expression did not compile; used deterministic identity fallback."
    )
    return fallback, warnings


def _build_trace_report(prompt: str, expression: str | None) -> tuple[dict[str, Any], list[str]]:
    """Build a cas-explain-shaped report without calling a model runtime."""
    _ensure_cas_native_alias()
    from cas_native.inference.plain_english import translate_explain
    from cas_native.inference.traceability_v0 import build_v0_trace

    cas_expression, warnings = _validated_expression(prompt, expression)
    expected = _extract_identifiers(cas_expression)
    generated = (
        f"Mode 7 local trace for: {prompt.strip() or cas_expression}. "
        f"CAS expression: {cas_expression}"
    )
    emitted = _extract_identifiers(generated)
    emitted_set = set(emitted)
    copied = [identifier for identifier in expected if identifier in emitted_set]
    missing = [identifier for identifier in expected if identifier not in emitted_set]
    coverage = (len(copied) / len(expected)) if expected else 0.0

    report: dict[str, Any] = {
        "command": "mode7 live",
        "version": 1,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_cas_expression": cas_expression,
        "model": {
            "runtime": "deterministic_fallback",
            "decode_seconds": 0.0,
        },
        "generated_english": generated,
        "n_tokens_generated": len(generated.split()),
        "identifiers": {
            "expected": expected,
            "emitted": emitted,
            "copied": copied,
            "missing": missing,
            "coverage": coverage,
        },
        "slot_summary": _slot_summary_for(generated),
        "gates": {
            "no_crash": True,
            "generated_non_empty": bool(generated),
            "ge_one_identifier_copied": bool(copied),
        },
        "mode7": {
            "runtime": "deterministic_fallback",
            "source": "cas_native.traceability_v0.thought_tree",
        },
    }
    report["plain_english"] = translate_explain(report)
    report["traceability_v0"] = build_v0_trace(report)
    return report, warnings


def _node_parent_map(edges: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(edge.get("target")): str(edge.get("source"))
        for edge in edges
        if edge.get("source") is not None and edge.get("target") is not None
    }


def _head_name(node: dict[str, Any]) -> str:
    kind = str(node.get("kind") or "")
    if kind in {"identifier_attempt", "slot_pattern", "confidence_marker", "model_generation"}:
        return kind
    return kind or "thought_tree"


async def _stream_report(
    *,
    turn_id: str,
    prompt: str,
    report: dict[str, Any],
    warnings: list[str],
    delay_ms: int,
) -> AsyncIterator[str]:
    _ensure_cas_native_alias()
    from cas_native.inference.sggs_stream import (
        emit_edge_commit,
        emit_head_commit,
        emit_turn_end,
        emit_turn_start,
        emit_warning,
    )

    started = time.perf_counter()
    trace = report["traceability_v0"]
    tree = trace["thought_tree"]
    nodes = list(tree.get("nodes") or [])
    edges = list(tree.get("edges") or [])
    parent_by_node = _node_parent_map(edges)

    yield emit_turn_start(turn_id=turn_id, user_text=prompt or report["input_cas_expression"])
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    for message in warnings:
        yield emit_warning(turn_id=turn_id, severity="info", message=message)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

    head_count = 0
    for node in nodes:
        node_id = str(node.get("id") or "")
        if node_id == "n0":
            continue
        axis_attrs = dict(node.get("axis_attrs") or {})
        axis_attrs.update(
            {
                "node_key": node.get("node_key"),
                "role": node.get("role"),
                "normalized_label": node.get("normalized_label"),
            }
        )
        yield emit_head_commit(
            turn_id=turn_id,
            head_index=head_count,
            head_name=_head_name(node),
            node_id=node_id,
            node_kind=str(node.get("kind") or ""),
            node_label=str(node.get("label") or ""),
            parent_node_id=parent_by_node.get(node_id),
            axis_attrs=axis_attrs,
        )
        head_count += 1
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        for edge in edges:
            if str(edge.get("target")) != node_id:
                continue
            yield emit_edge_commit(
                turn_id=turn_id,
                edge_id=str(edge.get("id") or ""),
                source_node_id=str(edge.get("source") or ""),
                target_node_id=str(edge.get("target") or ""),
                kind=str(edge.get("kind") or "parent_child"),
            )
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    duration_ms = int((time.perf_counter() - started) * 1000)
    yield emit_turn_end(
        turn_id=turn_id,
        final_trace_id=str(trace.get("trace_id") or ""),
        total_heads=head_count,
        duration_ms=duration_ms,
    )


@router.get("/live")
async def live(
    prompt: str = Query("", max_length=10000),
    expression: str | None = Query(None, max_length=10000),
    delay_ms: int = Query(0, ge=0, le=1000),
) -> StreamingResponse:
    """Stream SGGS commits for one local Mode 7 turn.

    Query params:
      - prompt: stakeholder/user text. Required unless expression is supplied.
      - expression: optional CAS expression. If omitted, a deterministic local
        synthesis from prompt is used.
      - delay_ms: optional inter-event delay for demos/tests.
    """
    if not prompt.strip() and not (expression or "").strip():
        raise HTTPException(status_code=422, detail="prompt or expression is required")

    report, warnings = _build_trace_report(prompt, expression)
    turn_id = f"mode7-{uuid.uuid4().hex[:12]}"
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _stream_report(
            turn_id=turn_id,
            prompt=prompt,
            report=report,
            warnings=warnings,
            delay_ms=delay_ms,
        ),
        media_type="text/event-stream",
        headers=headers,
    )
