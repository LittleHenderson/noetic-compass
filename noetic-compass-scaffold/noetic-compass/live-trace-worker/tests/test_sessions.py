from __future__ import annotations


def _create(client, **overrides) -> dict:
    body = {"prompt": "A warm coffee cup on the table.", "seed": 42}
    body.update(overrides)
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_session_returns_id_and_events_url(client):
    data = _create(client)
    assert "session_id" in data
    assert data["events_url"] == f"/sessions/{data['session_id']}/events"


def test_create_session_rejects_unknown_model(client):
    r = client.post(
        "/sessions",
        json={"prompt": "anything", "model_id": "EleutherAI/pythia-1.4b"},
    )
    assert r.status_code == 400
    assert "not supported" in r.text.lower()


def test_manifest_lookup_returns_full_manifest(client):
    data = _create(client)
    r = client.get(f"/sessions/{data['session_id']}/manifest")
    assert r.status_code == 200
    m = r.json()
    assert m["model_id"] == "EleutherAI/pythia-160m"
    assert m["model_arch"]["n_layers"] == 12
    assert m["model_arch"]["hidden_size"] == 768
    assert m["is_real_model"] is False


def test_manifest_lookup_unknown_session(client):
    r = client.get("/sessions/does-not-exist/manifest")
    assert r.status_code == 404


def test_dump_session_emits_full_event_sequence(client):
    # /sessions/dump is the non-SSE test/debug variant — returns the same
    # event list as the streamed endpoint but as one JSON payload.
    r = client.post(
        "/sessions/dump",
        json={"prompt": "Two short words.", "seed": 7, "max_new_tokens": 6},
    )
    assert r.status_code == 200
    events = r.json()["events"]

    # Manifest first, complete last, neuron_covers right after manifest.
    assert events[0]["type"] == "manifest"
    assert events[1]["type"] == "neuron_covers"
    assert events[-1]["type"] == "complete"

    # Token events in between, exact count == max_new_tokens.
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 6
    assert events[-1]["total_tokens"] == 6

    # Token indices are 0..N-1 and monotonic.
    for i, ev in enumerate(token_events):
        assert ev["token_index"] == i
        # Mode 7 attribution: first token has a single None-from edge, the
        # rest have edges pointing back to earlier indices.
        if i == 0:
            assert ev["mode7_attribution"][0]["from_token_index"] is None
        else:
            for edge in ev["mode7_attribution"]:
                assert edge["from_token_index"] is not None
                assert 0 <= edge["from_token_index"] < i
                assert edge["to_token_index"] == i

    # Cover sets present and conform to the offline trace shape.
    covers = events[1]["per_class_neuron_covers"]
    for cls in ("F1A", "F1T", "F1f", "F1E"):
        assert cls in covers
        assert all(label.startswith("L") and "N" in label for label in covers[cls])


def test_dump_session_is_deterministic_under_seed(client):
    body = {"prompt": "Stability check.", "seed": 1234, "max_new_tokens": 5}
    a = client.post("/sessions/dump", json=body).json()["events"]
    b = client.post("/sessions/dump", json=body).json()["events"]
    # Strip out the manifest (which is identical anyway) and compare the
    # token events directly — same seed must produce same activations.
    a_toks = [e for e in a if e["type"] == "token"]
    b_toks = [e for e in b if e["type"] == "token"]
    assert a_toks == b_toks
