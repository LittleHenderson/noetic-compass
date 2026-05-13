"""SGGS streaming protocol — head-level structural commits over SSE.

Phase 2 of the SGGS product backlog
(`docs/working/sggs_v2_v3_product_feature_backlog_2026_05_06.md`, lines
91-108): deliver structural commits from the CAS-Native inference server
to the 3D viewer in real time so the dashboard can animate structural
assembly node-by-node, head-by-head.

**Granularity** — head-level, not token-level. Per spec line 105-106:
"target head-level (12 updates per turn) not token-level (hundreds per
turn). Token-level gets jittery; head-level is readable." Each commit
corresponds to one structural-prediction head firing
(noetic / domain / drive / register / etc.) or one edge being
materialized between previously-emitted nodes.

**Wire format** — Server-Sent Events (SSE) per the WHATWG / W3C HTML
spec. Each event is an `event:` line + `id:` line + `data:` line + a
blank-line terminator. SSE was chosen over WebSockets because the
inference→viewer channel is one-way (server pushes, client never
publishes), reconnect is built into the EventSource API, and SSE
travels cleanly through HTTP proxies without upgrade negotiation. The
client uses standard `Last-Event-ID` resume semantics (see
`sggs_stream_protocol_2026_05_13.md`).

**Public surface** — six pure `emit_*` helpers each return a
JSON-serializable SSE block as a string (no I/O), plus a `demo_stream`
generator that yields a fake-but-realistic 12-commit sequence mirroring
the Atlas `DEMO_TRACE_COMPLEX` Θ-recipe walkthrough. The CLI subcommand
`cas sggs-stream-demo` (registered in `cas_cli.py`) writes the demo
stream to stdout with explicit flushing so a downstream SSE proxy or
`curl --no-buffer` consumer sees each block in real time.

**Discipline** — no foreign deps (stdlib only); every emit takes
explicit args (no hidden state); JSON is dumped with `default=str` so
edge inputs never crash the encoder.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Iterator, Optional


SCHEMA_VERSION = "sggs_stream_v0"

# Event-kind literals — kept here so callers don't have to memorize the
# strings and tests can import them as constants.
EVENT_TURN_START = "turn_start"
EVENT_HEAD_COMMIT = "head_commit"
EVENT_EDGE_COMMIT = "edge_commit"
EVENT_TURN_END = "turn_end"
EVENT_WARNING = "warning"
EVENT_ERROR = "error"

EVENT_KINDS: tuple[str, ...] = (
    EVENT_TURN_START,
    EVENT_HEAD_COMMIT,
    EVENT_EDGE_COMMIT,
    EVENT_TURN_END,
    EVENT_WARNING,
    EVENT_ERROR,
)


def _iso_now() -> str:
    """UTC timestamp in ISO8601, stable across platforms."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _next_event_id() -> str:
    """Generate a per-event ID. Used in the SSE `id:` line so clients can
    resume from `Last-Event-ID` on reconnect. UUID4 is unique enough that
    a server-side replay cache can key on it without collision risk."""
    return uuid.uuid4().hex[:16]


def _format_sse_block(event: str, payload: dict[str, Any], event_id: Optional[str] = None) -> str:
    """Format a single SSE event block.

    Per the SSE spec each event is a sequence of `field: value` lines
    terminated by a blank line. We always emit:
      event: <event>
      id:    <event_id>
      data:  <json>

    The trailing blank line is critical — the EventSource parser only
    dispatches an event when it sees `\n\n`. Tests pin this.
    """
    if event not in EVENT_KINDS:
        # Don't crash on an unknown event — emit a defensive `error`
        # event instead so the client at least sees something it can
        # parse. This matches the discipline of `traceability_v0`: never
        # raise from a producer helper that's called inside a model loop.
        event = EVENT_ERROR
        payload = {
            "code": "unknown_event_kind",
            "message": f"unknown event kind {event!r}",
            "schema_version": SCHEMA_VERSION,
        }

    eid = event_id or _next_event_id()
    # `default=str` mirrors `traceability_v0.trace_to_json` — any non-JSON
    # value (Path, datetime, custom class) renders to str rather than
    # raising mid-stream.
    data = json.dumps(payload, default=str, sort_keys=False)
    return f"event: {event}\nid: {eid}\ndata: {data}\n\n"


# ---------------------------------------------------------------------------
# Producer-side helpers — each returns one SSE block as a string. No I/O.
# ---------------------------------------------------------------------------

def emit_turn_start(turn_id: str, user_text: str) -> str:
    """Begin a new model turn.

    Carries the user's prompt verbatim so the client can render the root
    node (the user query) before any structural heads commit.
    """
    payload: dict[str, Any] = {
        "kind": EVENT_TURN_START,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "user_text": str(user_text),
        "created_at": _iso_now(),
    }
    return _format_sse_block(EVENT_TURN_START, payload)


def emit_head_commit(
    turn_id: str,
    head_index: int,
    head_name: str,
    node_id: str,
    node_kind: str,
    node_label: str,
    parent_node_id: Optional[str] = None,
    axis_attrs: Optional[dict[str, Any]] = None,
) -> str:
    """Emit one structural-prediction-head commit.

    `head_index` is 0-based and stable across the turn so the client can
    reorder commits that arrived out-of-band (e.g. via reconnect). The
    node payload mirrors the `traceability_v0.thought_tree` node shape
    (kind / label / axis_attrs) so SGGS commits and saved Atlas traces
    speak the same vocabulary.

    `axis_attrs` is treated as an arbitrary key-value bag and dumped
    as-is. Empty / None becomes `{}`.
    """
    payload: dict[str, Any] = {
        "kind": EVENT_HEAD_COMMIT,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "head_index": int(head_index),
        "head_name": str(head_name),
        "node_id": str(node_id),
        "node_kind": str(node_kind),
        "node_label": str(node_label),
        "parent_node_id": str(parent_node_id) if parent_node_id is not None else None,
        "axis_attrs": dict(axis_attrs) if axis_attrs else {},
    }
    return _format_sse_block(EVENT_HEAD_COMMIT, payload)


def emit_edge_commit(
    turn_id: str,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    kind: str = "parent_child",
) -> str:
    """Emit a structural edge between two previously-emitted nodes.

    Caller is responsible for ensuring `source_node_id` and
    `target_node_id` were already emitted via `emit_head_commit`. The
    client tolerates forward references (it queues edges until the
    referenced node arrives), but the demo stream and well-behaved
    producers should emit edges in dependency order.
    """
    payload: dict[str, Any] = {
        "kind": EVENT_EDGE_COMMIT,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "edge_id": str(edge_id),
        "source_node_id": str(source_node_id),
        "target_node_id": str(target_node_id),
        "edge_kind": str(kind),
    }
    return _format_sse_block(EVENT_EDGE_COMMIT, payload)


def emit_turn_end(
    turn_id: str,
    final_trace_id: str,
    total_heads: int,
    duration_ms: int,
) -> str:
    """Signal a complete turn.

    `final_trace_id` resolves to a full `traceability_v0` trace the
    client can fetch (or load from disk via `cas atlas-save`) for
    post-hoc replay / rewind / slow-motion. `total_heads` and
    `duration_ms` are diagnostic only.
    """
    payload: dict[str, Any] = {
        "kind": EVENT_TURN_END,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "final_trace_id": str(final_trace_id),
        "total_heads": int(total_heads),
        "duration_ms": int(duration_ms),
        "ended_at": _iso_now(),
    }
    return _format_sse_block(EVENT_TURN_END, payload)


def emit_warning(turn_id: str, severity: str, message: str) -> str:
    """Non-fatal advisory. Stream continues. `severity` is one of
    `info` / `warning` / `error` (mirrors `traceability_v0` severity
    bands); unknown values pass through verbatim so the producer can
    add a new band without an upstream-side code change."""
    payload: dict[str, Any] = {
        "kind": EVENT_WARNING,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "severity": str(severity),
        "message": str(message),
    }
    return _format_sse_block(EVENT_WARNING, payload)


def emit_error(turn_id: str, code: str, message: str) -> str:
    """Fatal-for-this-turn error. The server may close the stream after
    emitting this; the client should treat any subsequent reconnect as a
    fresh subscription. `code` is a stable short identifier suitable for
    metric labels (`decode_crash`, `compiler_invalid`, etc.); `message`
    is human-readable."""
    payload: dict[str, Any] = {
        "kind": EVENT_ERROR,
        "schema_version": SCHEMA_VERSION,
        "turn_id": str(turn_id),
        "code": str(code),
        "message": str(message),
    }
    return _format_sse_block(EVENT_ERROR, payload)


# ---------------------------------------------------------------------------
# Demo stream — 14-block sequence mirroring DEMO_TRACE_COMPLEX
# ---------------------------------------------------------------------------

# Per-event delay (seconds). 0.15s ≈ 6.7Hz, which gives the client
# enough time to render each commit without the user feeling lag.
# Matches the spec's "12 updates per turn" cadence reading.
DEMO_INTER_EVENT_DELAY_SECONDS = 0.15

# Stable turn id for the demo so tests can pin it. UUID-shaped for
# realism. Don't use this in production code.
DEMO_TURN_ID = "demo-theta-recipe-001"

# Stable final-trace id matching the Atlas DEMO_TRACE_COMPLEX trace_id
# so a viewer can stitch a live demo to the saved trace.
DEMO_FINAL_TRACE_ID = "00000000-0000-4000-8000-00000000c0c0"

# The 12 head commits mirror the 14 nodes of the Atlas DEMO_TRACE_COMPLEX
# tree (skipping the user_prompt root which is delivered via
# turn_start, and the nl_bridge node which is already implicit in the
# user_text → cas_expression transition). Order = dependency order so
# the client can render each node as soon as it arrives.
_DEMO_HEAD_COMMITS: tuple[dict[str, Any], ...] = (
    {
        "head_index": 0,
        "head_name": "nl_bridge",
        "node_id": "n1",
        "node_kind": "nl_bridge",
        "node_label": "safety refusal recipe",
        "parent_node_id": "n0",
        "axis_attrs": {"confidence": 0.78, "pattern": "safety refusal recipe"},
    },
    {
        "head_index": 1,
        "head_name": "cas_expression",
        "node_id": "n2",
        "node_kind": "cas_expression",
        "node_label": "Θ(refuse_harmful_request) = 2·(…) + 1·(…) + 0.5·…",
        "parent_node_id": "n1",
        "axis_attrs": {"production_target": "refuse_harmful_request"},
    },
    {
        "head_index": 2,
        "head_name": "slot_pattern",
        "node_id": "n3",
        "node_kind": "slot_pattern",
        "node_label": "recipe prerequisites",
        "parent_node_id": "n2",
        "axis_attrs": {"prereq_count": 3},
    },
    {
        "head_index": 3,
        "head_name": "cas_expression",
        "node_id": "n4",
        "node_kind": "cas_expression",
        "node_label": "principled aversion (×3 registers)",
        "parent_node_id": "n3",
        "axis_attrs": {"coefficient": 2, "register_count": 3},
    },
    {
        "head_index": 4,
        "head_name": "register",
        "node_id": "n5",
        "node_kind": "identifier_attempt",
        "node_label": "^3^P|A",
        "parent_node_id": "n4",
        "axis_attrs": {"noetic": 3, "domain": "P", "register": "A"},
    },
    {
        "head_index": 5,
        "head_name": "register",
        "node_id": "n6",
        "node_kind": "identifier_attempt",
        "node_label": "^3^P|f",
        "parent_node_id": "n4",
        "axis_attrs": {"noetic": 3, "domain": "P", "register": "f"},
    },
    {
        "head_index": 6,
        "head_name": "register",
        "node_id": "n7",
        "node_kind": "identifier_attempt",
        "node_label": "^3^P|T",
        "parent_node_id": "n4",
        "axis_attrs": {"noetic": 3, "domain": "P", "register": "T"},
    },
    {
        "head_index": 7,
        "head_name": "emergent",
        "node_id": "n8",
        "node_kind": "model_generation",
        "node_label": "^3^P|Ω — fused refusal",
        "parent_node_id": "n4",
        "axis_attrs": {"noetic": 3, "domain": "P", "register": "Ω", "emergent": True},
    },
    {
        "head_index": 8,
        "head_name": "cas_expression",
        "node_id": "n9",
        "node_kind": "cas_expression",
        "node_label": "^6^P × ^9^O — composition → effect",
        "parent_node_id": "n3",
        "axis_attrs": {"coefficient": 1},
    },
    {
        "head_index": 9,
        "head_name": "cas_expression",
        "node_id": "n10",
        "node_kind": "cas_expression",
        "node_label": "^7^C_{F2|A} — analytical wisdom rhythm",
        "parent_node_id": "n3",
        "axis_attrs": {"coefficient": 0.5, "drive": "F2", "register": "A"},
    },
    {
        "head_index": 10,
        "head_name": "model_generation",
        "node_id": "n11",
        "node_kind": "model_generation",
        "node_label": "plain-English explanation",
        "parent_node_id": "n2",
        "axis_attrs": {"n_tokens": 92},
    },
    {
        "head_index": 11,
        "head_name": "confidence_marker",
        "node_id": "n13",
        "node_kind": "confidence_marker",
        "node_label": "coefficients unfit",
        "parent_node_id": "n11",
        "axis_attrs": {"band": "warning", "kind": "recipe_coefficient_unfit"},
    },
)

# Edges that materialize structural relationships between previously
# emitted nodes. We deliberately emit fewer than the full Atlas trace
# has (which is one edge per parent_node_id reference) so the client
# can demonstrate it tolerates implicit parenting via head_commit
# `parent_node_id` AND explicit edge_commit events.
_DEMO_EDGE_COMMITS: tuple[dict[str, Any], ...] = (
    # Parent-child between root user_prompt (delivered via turn_start)
    # and the nl_bridge head_commit.
    {"edge_id": "e_root_nl", "source_node_id": "n0", "target_node_id": "n1"},
    # Decomposition fan-out — three prereq edges off the slot_pattern node.
    {"edge_id": "e_decomp_p1", "source_node_id": "n3", "target_node_id": "n4"},
    {"edge_id": "e_decomp_p2", "source_node_id": "n3", "target_node_id": "n9"},
    {"edge_id": "e_decomp_p3", "source_node_id": "n3", "target_node_id": "n10"},
    # Cross-register fusion: the emergent node depends on the three register
    # instantiations, not just on the prereq1 wrapper. Demonstrate edges that
    # do not match parent_node_id.
    {"edge_id": "e_fuse_a", "source_node_id": "n5", "target_node_id": "n8"},
    {"edge_id": "e_fuse_f", "source_node_id": "n6", "target_node_id": "n8"},
)


def demo_stream(
    turn_id: str = DEMO_TURN_ID,
    user_text: str = "show me how an AI refuses a harmful request, structurally",
    inter_event_delay: Optional[float] = None,
) -> Iterator[str]:
    """Yield a 12-head SSE stream that mirrors `DEMO_TRACE_COMPLEX`.

    The yielded shape:
      1× turn_start
      12× head_commit (one per structural-prediction head)
      6× edge_commit (cross-register fusion + decomposition fan-out)
      1× turn_end

    Total: 20 blocks. Per spec line 105-106 the headline cadence is
    "head-level (12 updates per turn)" — counted as `head_commit`
    events; edges and turn boundaries are infrastructure.

    `inter_event_delay` overrides `DEMO_INTER_EVENT_DELAY_SECONDS`.
    Pass `0` from tests so the iterator returns immediately. The
    `cas sggs-stream-demo` CLI invokes this with the default to give
    the dashboard a realistic ~6Hz cadence.
    """
    delay = (
        DEMO_INTER_EVENT_DELAY_SECONDS if inter_event_delay is None else float(inter_event_delay)
    )
    started = time.time()

    yield emit_turn_start(turn_id=turn_id, user_text=user_text)
    if delay > 0:
        time.sleep(delay)

    for commit in _DEMO_HEAD_COMMITS:
        yield emit_head_commit(
            turn_id=turn_id,
            head_index=int(commit["head_index"]),
            head_name=str(commit["head_name"]),
            node_id=str(commit["node_id"]),
            node_kind=str(commit["node_kind"]),
            node_label=str(commit["node_label"]),
            parent_node_id=(
                str(commit["parent_node_id"])
                if commit.get("parent_node_id") is not None
                else None
            ),
            axis_attrs=dict(commit.get("axis_attrs") or {}),
        )
        if delay > 0:
            time.sleep(delay)

    for edge in _DEMO_EDGE_COMMITS:
        yield emit_edge_commit(
            turn_id=turn_id,
            edge_id=str(edge["edge_id"]),
            source_node_id=str(edge["source_node_id"]),
            target_node_id=str(edge["target_node_id"]),
        )
        if delay > 0:
            time.sleep(delay)

    duration_ms = int((time.time() - started) * 1000)
    yield emit_turn_end(
        turn_id=turn_id,
        final_trace_id=DEMO_FINAL_TRACE_ID,
        total_heads=len(_DEMO_HEAD_COMMITS),
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# CLI entry point — invoked by `cas sggs-stream-demo` in cas_cli.py and as
# a standalone fallback (`python -m cas_native.inference.sggs_stream`).
# Writes the demo stream to stdout with explicit flushing so a downstream
# SSE proxy (`curl --no-buffer`, nginx with proxy_buffering off, etc.)
# sees each block in real time.
# ---------------------------------------------------------------------------

def run_demo_stream_cli(argv: Optional[list[str]] = None) -> int:
    """Write `demo_stream()` to stdout, flushing between blocks.

    Returns 0 on success. Catches `KeyboardInterrupt` so Ctrl-C exits
    cleanly without a stack trace.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="cas sggs-stream-demo",
        description=(
            "Stream a fake-but-realistic 12-head SGGS commit sequence to "
            "stdout in Server-Sent Events format. Pipe through a local "
            "SSE proxy or `curl --no-buffer` to test the SGGS dashboard "
            "client without a running model."
        ),
    )
    parser.add_argument(
        "--no-delay",
        action="store_true",
        help="Emit all events immediately (skip the 0.15s inter-event delay). "
             "Useful for piping into a file or for fast tests.",
    )
    parser.add_argument(
        "--turn-id",
        default=DEMO_TURN_ID,
        help=f"Turn id for the demo stream (default: {DEMO_TURN_ID}).",
    )
    args = parser.parse_args(argv or [])

    delay: Optional[float] = 0.0 if args.no_delay else None
    try:
        for block in demo_stream(turn_id=args.turn_id, inter_event_delay=delay):
            sys.stdout.write(block)
            sys.stdout.flush()
    except KeyboardInterrupt:
        return 130  # POSIX SIGINT convention
    return 0


if __name__ == "__main__":  # pragma: no cover — entry-point wiring
    import sys
    raise SystemExit(run_demo_stream_cli(sys.argv[1:]))
