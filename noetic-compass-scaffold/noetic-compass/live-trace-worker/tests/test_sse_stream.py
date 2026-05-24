"""Verify the SSE wire format end-to-end via the streaming endpoint."""

from __future__ import annotations

import json


def test_sse_stream_yields_typed_events(client):
    create = client.post(
        "/sessions",
        json={"prompt": "Stream check.", "seed": 99, "max_new_tokens": 3},
    ).json()
    sid = create["session_id"]

    # TestClient.stream consumes the response body, including SSE framing.
    with client.stream("GET", f"/sessions/{sid}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        raw = "".join(resp.iter_text())

    # Each event is `event: <type>\ndata: <json>\n\n`. Split on the blank
    # line and verify the structure.
    blocks = [b for b in raw.split("\n\n") if b.strip()]
    # manifest + covers + 3 tokens + word_spans + complete
    assert len(blocks) >= 6

    types: list[str] = []
    for block in blocks:
        lines = block.splitlines()
        event_line = next(L for L in lines if L.startswith("event: "))
        data_line = next(L for L in lines if L.startswith("data: "))
        event_type = event_line[len("event: ") :]
        payload = json.loads(data_line[len("data: ") :])
        assert payload["type"] == event_type
        types.append(event_type)

    assert types[0] == "manifest"
    assert types[1] == "neuron_covers"
    assert types[-2] == "word_spans"
    assert types[-1] == "complete"
    assert types.count("token") == 3
