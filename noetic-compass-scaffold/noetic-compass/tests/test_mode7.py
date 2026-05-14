"""Tests for Mode 7 Live SSE route."""

from __future__ import annotations

import json
import re
from typing import Any


SSE_BLOCK_RE = re.compile(
    r"^event:\s*(?P<event>\S+)\nid:\s*(?P<id>\S+)\ndata:\s*(?P<data>.*)\n\n\Z",
    re.DOTALL,
)


def _parse_sse(body: str) -> list[dict[str, Any]]:
    blocks = [block + "\n\n" for block in body.split("\n\n") if block.strip()]
    parsed: list[dict[str, Any]] = []
    for block in blocks:
        match = SSE_BLOCK_RE.match(block)
        assert match is not None, f"bad SSE block: {block!r}"
        parsed.append(
            {
                "event": match.group("event"),
                "id": match.group("id"),
                "data": json.loads(match.group("data")),
            }
        )
    return parsed


def test_mode7_live_requires_auth(client):
    resp = client.get("/mode7/live", params={"prompt": "trace this"})
    assert resp.status_code == 401


def test_mode7_live_streams_sggs_events_from_expression(client, auth_headers):
    resp = client.get(
        "/mode7/live",
        params={
            "prompt": "show wisdom in cognitive mode",
            "expression": "CO-2^C_{F2}",
            "delay_ms": 0,
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    kinds = [event["event"] for event in events]
    assert kinds[0] == "turn_start"
    assert kinds[-1] == "turn_end"
    assert "head_commit" in kinds
    assert "edge_commit" in kinds

    turn_ids = {event["data"]["turn_id"] for event in events}
    assert len(turn_ids) == 1

    head_payloads = [event["data"] for event in events if event["event"] == "head_commit"]
    assert any(payload["node_kind"] == "model_generation" for payload in head_payloads)
    assert any(payload["node_kind"] == "slot_pattern" for payload in head_payloads)
    assert all(payload["schema_version"] == "sggs_stream_v0" for payload in head_payloads)
    assert all("node_key" in payload["axis_attrs"] for payload in head_payloads)

    end = events[-1]["data"]
    assert end["final_trace_id"]
    assert end["total_heads"] == len(head_payloads)


def test_mode7_live_prompt_only_uses_local_fallback(client, auth_headers):
    resp = client.get(
        "/mode7/live",
        params={"prompt": "I am drawn to disciplined structure.", "delay_ms": 0},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)
    warning_payloads = [event["data"] for event in events if event["event"] == "warning"]
    assert any("deterministic local synthesis" in payload["message"] for payload in warning_payloads)
    assert events[0]["data"]["user_text"] == "I am drawn to disciplined structure."
