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
    required_mode7_attrs = {
        "mode7_semantics",
        "activation_hooks",
        "activation_layers",
        "per_head_attribution",
        "load_bearing_tokens",
        "logits_summary",
        "copy_distribution_summary",
        "domain_descent_attention",
        "structural_commit_linkage",
    }
    for payload in head_payloads:
        attrs = payload["axis_attrs"]
        assert required_mode7_attrs <= set(attrs)

        assert attrs["mode7_semantics"]["mode"] == 7
        assert attrs["mode7_semantics"]["name"] == "Network Attribution / Mechanistic Trace"

        assert "hook_status" in attrs["activation_hooks"]
        assert attrs["activation_layers"]

        per_head = attrs["per_head_attribution"]
        assert {"noetic", "domain", "drive", "register"} <= set(per_head)
        assert all("top_tokens" in per_head[head] for head in ("noetic", "domain"))

        assert attrs["load_bearing_tokens"]
        assert attrs["logits_summary"]["per_head"]["domain"]["logit_count"] > 0
        assert "coverage" in attrs["copy_distribution_summary"]

        dda = attrs["domain_descent_attention"]
        assert dda["applicable"] is True
        assert dda["selected_domain"] == "C"
        assert "C" in dda["observed_domains"]

        linkage = attrs["structural_commit_linkage"]
        assert linkage["commit_event"] == "head_commit"
        assert linkage["turn_id"] == payload["turn_id"]
        assert linkage["trace_id"] == end["final_trace_id"]
        assert linkage["head_index"] == payload["head_index"]
        assert linkage["head_name"] == payload["head_name"]
        assert linkage["node_id"] == payload["node_id"]
        assert linkage["node_key"] == attrs["node_key"]
        assert linkage["parent_node_id"] == payload["parent_node_id"]
        assert isinstance(linkage["incoming_edges"], list)

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
