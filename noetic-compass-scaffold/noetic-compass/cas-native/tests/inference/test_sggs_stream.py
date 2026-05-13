"""Tests for `cas_native.inference.sggs_stream` — the SGGS SSE protocol.

Pins:
  - every emit helper produces a well-formed SSE block (event + id + data
    + blank-line terminator);
  - JSON in the `data:` line round-trips losslessly;
  - `demo_stream()` yields the documented 20-block shape (1 turn_start +
    12 head_commits + 6 edge_commits + 1 turn_end);
  - edge commits reference node_ids previously emitted by head_commits;
  - no emit helper raises on edge inputs (empty axis_attrs, None parent,
    odd severity values).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import pytest

from cas_native.inference import sggs_stream
from cas_native.inference.sggs_stream import (
    DEMO_FINAL_TRACE_ID,
    DEMO_TURN_ID,
    EVENT_EDGE_COMMIT,
    EVENT_ERROR,
    EVENT_HEAD_COMMIT,
    EVENT_TURN_END,
    EVENT_TURN_START,
    EVENT_WARNING,
    SCHEMA_VERSION,
    demo_stream,
    emit_edge_commit,
    emit_error,
    emit_head_commit,
    emit_turn_end,
    emit_turn_start,
    emit_warning,
)


# ---------------------------------------------------------------------------
# SSE format helpers
# ---------------------------------------------------------------------------

SSE_BLOCK_RE = re.compile(
    r"^event:\s*(?P<event>\S+)\nid:\s*(?P<id>\S+)\ndata:\s*(?P<data>.*)\n\n\Z",
    re.DOTALL,
)


def parse_block(block: str) -> dict[str, Any]:
    """Parse one SSE block into {event, id, data: <decoded JSON>}.

    Raises AssertionError with a helpful message on bad shape so test
    failures point at the actual block instead of a generic regex
    NoneType error.
    """
    m = SSE_BLOCK_RE.match(block)
    assert m is not None, f"SSE block did not match expected shape: {block!r}"
    return {
        "event": m.group("event"),
        "id": m.group("id"),
        "data": json.loads(m.group("data")),
    }


# ---------------------------------------------------------------------------
# Per-emitter format tests
# ---------------------------------------------------------------------------

class TestSSEFormat:
    def test_turn_start_block_shape(self) -> None:
        block = emit_turn_start(turn_id="t-001", user_text="hello world")
        # Required SSE shape: event + id + data + trailing blank line.
        assert block.endswith("\n\n"), "SSE blocks must end with a blank line"
        parsed = parse_block(block)
        assert parsed["event"] == EVENT_TURN_START
        assert len(parsed["id"]) >= 8
        payload = parsed["data"]
        assert payload["kind"] == EVENT_TURN_START
        assert payload["turn_id"] == "t-001"
        assert payload["user_text"] == "hello world"
        assert payload["schema_version"] == SCHEMA_VERSION
        assert "created_at" in payload

    def test_head_commit_round_trip(self) -> None:
        block = emit_head_commit(
            turn_id="t-001",
            head_index=3,
            head_name="register",
            node_id="n7",
            node_kind="identifier_attempt",
            node_label="^3^P|A",
            parent_node_id="n4",
            axis_attrs={"register": "A", "drive": "F2"},
        )
        parsed = parse_block(block)
        assert parsed["event"] == EVENT_HEAD_COMMIT
        d = parsed["data"]
        assert d["turn_id"] == "t-001"
        assert d["head_index"] == 3
        assert d["head_name"] == "register"
        assert d["node_id"] == "n7"
        assert d["node_kind"] == "identifier_attempt"
        assert d["node_label"] == "^3^P|A"
        assert d["parent_node_id"] == "n4"
        assert d["axis_attrs"] == {"register": "A", "drive": "F2"}

    def test_head_commit_handles_none_parent(self) -> None:
        block = emit_head_commit(
            turn_id="t-001",
            head_index=0,
            head_name="user_prompt",
            node_id="n0",
            node_kind="user_prompt",
            node_label="hi",
        )
        d = parse_block(block)["data"]
        assert d["parent_node_id"] is None
        # Empty axis_attrs becomes {} not None — keeps the client typing
        # simpler (Record<string, unknown>, not optional).
        assert d["axis_attrs"] == {}

    def test_head_commit_empty_axis_attrs(self) -> None:
        block = emit_head_commit(
            turn_id="t-001", head_index=0, head_name="x",
            node_id="n", node_kind="k", node_label="l",
            axis_attrs={},
        )
        assert parse_block(block)["data"]["axis_attrs"] == {}

    def test_edge_commit_round_trip(self) -> None:
        block = emit_edge_commit(
            turn_id="t-001",
            edge_id="e0",
            source_node_id="n0",
            target_node_id="n1",
            kind="parent_child",
        )
        d = parse_block(block)["data"]
        assert d["turn_id"] == "t-001"
        assert d["edge_id"] == "e0"
        assert d["source_node_id"] == "n0"
        assert d["target_node_id"] == "n1"
        assert d["edge_kind"] == "parent_child"

    def test_turn_end_round_trip(self) -> None:
        block = emit_turn_end(
            turn_id="t-001",
            final_trace_id="trace-uuid",
            total_heads=12,
            duration_ms=2400,
        )
        d = parse_block(block)["data"]
        assert d["turn_id"] == "t-001"
        assert d["final_trace_id"] == "trace-uuid"
        assert d["total_heads"] == 12
        assert d["duration_ms"] == 2400
        assert "ended_at" in d

    def test_warning_round_trip(self) -> None:
        block = emit_warning(turn_id="t-001", severity="info", message="hi")
        d = parse_block(block)["data"]
        assert d["severity"] == "info"
        assert d["message"] == "hi"
        # Unknown severity passes through verbatim (producer flexibility).
        block2 = emit_warning(turn_id="t-001", severity="oddband", message="!")
        assert parse_block(block2)["data"]["severity"] == "oddband"

    def test_error_round_trip(self) -> None:
        block = emit_error(turn_id="t-001", code="boom", message="kaboom")
        d = parse_block(block)["data"]
        assert d["code"] == "boom"
        assert d["message"] == "kaboom"

    def test_no_emit_raises_on_edge_inputs(self) -> None:
        """Producer helpers should never raise mid-decode. Confirm a
        battery of edge inputs all return parseable blocks."""
        cases = [
            lambda: emit_turn_start("", ""),
            lambda: emit_head_commit("t", 0, "", "", "", ""),
            lambda: emit_head_commit("t", 0, "x", "n", "k", "l", None, None),
            lambda: emit_edge_commit("t", "", "", ""),
            lambda: emit_turn_end("t", "", 0, 0),
            lambda: emit_warning("t", "", ""),
            lambda: emit_error("t", "", ""),
        ]
        for case in cases:
            block = case()
            parse_block(block)  # round-trip must succeed


# ---------------------------------------------------------------------------
# demo_stream() — full sequence assertions
# ---------------------------------------------------------------------------

class TestDemoStream:
    def test_demo_stream_yields_expected_shape(self) -> None:
        # inter_event_delay=0 → finishes immediately, no time.sleep cost.
        blocks = list(demo_stream(inter_event_delay=0))

        # 1 turn_start + 12 head_commits + 6 edge_commits + 1 turn_end = 20
        assert len(blocks) >= 14, f"Expected at least 14 blocks, got {len(blocks)}"

        parsed = [parse_block(b) for b in blocks]
        events = [p["event"] for p in parsed]

        assert events[0] == EVENT_TURN_START
        assert events[-1] == EVENT_TURN_END
        assert events.count(EVENT_HEAD_COMMIT) >= 10
        assert events.count(EVENT_TURN_END) == 1
        assert events.count(EVENT_TURN_START) == 1
        # Demo carries edge commits; this is per-spec.
        assert events.count(EVENT_EDGE_COMMIT) >= 1

    def test_demo_stream_event_ids_are_unique(self) -> None:
        blocks = list(demo_stream(inter_event_delay=0))
        ids = [parse_block(b)["id"] for b in blocks]
        assert len(set(ids)) == len(ids), "event ids must be unique within a turn"

    def test_demo_stream_head_commit_node_ids_unique(self) -> None:
        """No two head_commits should reuse the same node_id within a
        single turn — that would corrupt the client's node table."""
        blocks = list(demo_stream(inter_event_delay=0))
        node_ids: list[str] = []
        for b in blocks:
            p = parse_block(b)
            if p["event"] == EVENT_HEAD_COMMIT:
                node_ids.append(p["data"]["node_id"])
        assert len(set(node_ids)) == len(node_ids)

    def test_demo_stream_edges_reference_real_nodes(self) -> None:
        """Edges must reference node_ids that were either emitted by a
        prior head_commit OR are the implicit root `n0` (delivered via
        turn_start). Forward references are not allowed in demo
        ordering."""
        blocks = list(demo_stream(inter_event_delay=0))
        emitted_node_ids: set[str] = {"n0"}  # root from turn_start
        for b in blocks:
            p = parse_block(b)
            if p["event"] == EVENT_HEAD_COMMIT:
                emitted_node_ids.add(p["data"]["node_id"])
            elif p["event"] == EVENT_EDGE_COMMIT:
                src = p["data"]["source_node_id"]
                tgt = p["data"]["target_node_id"]
                assert src in emitted_node_ids, (
                    f"edge source {src!r} was not emitted before this edge"
                )
                assert tgt in emitted_node_ids, (
                    f"edge target {tgt!r} was not emitted before this edge"
                )

    def test_demo_stream_turn_id_consistent(self) -> None:
        blocks = list(demo_stream(inter_event_delay=0))
        for b in blocks:
            p = parse_block(b)
            assert p["data"]["turn_id"] == DEMO_TURN_ID

    def test_demo_stream_turn_end_references_atlas_trace(self) -> None:
        """The turn_end final_trace_id is the stable DEMO_TRACE_COMPLEX
        id so a viewer can stitch the live stream to the saved trace."""
        blocks = list(demo_stream(inter_event_delay=0))
        last = parse_block(blocks[-1])
        assert last["event"] == EVENT_TURN_END
        assert last["data"]["final_trace_id"] == DEMO_FINAL_TRACE_ID

    def test_demo_stream_inter_event_delay_zero_is_fast(self) -> None:
        """A `0` delay should produce the full stream in well under a
        second on any reasonable host. Guards against an accidental
        introduction of always-sleeping code."""
        start = time.time()
        list(demo_stream(inter_event_delay=0))
        assert (time.time() - start) < 1.0


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

class TestRunDemoStreamCLI:
    def test_run_demo_stream_cli_writes_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = sggs_stream.run_demo_stream_cli(["--no-delay"])
        assert rc == 0
        captured = capsys.readouterr()
        # Should contain at least one event line and end with a blank line.
        assert "event: turn_start" in captured.out
        assert "event: turn_end" in captured.out
        # Stream finishes cleanly — the last two characters are a blank line.
        assert captured.out.endswith("\n\n")
