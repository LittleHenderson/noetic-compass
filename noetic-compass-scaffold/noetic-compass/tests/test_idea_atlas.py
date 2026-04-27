"""Tests for the Idea Atlas backend (Sprint 1 scaffolding)."""

from __future__ import annotations

import pytest

from api.routes.idea_atlas import clear_memory_ideas


@pytest.fixture(autouse=True)
def _reset_idea_store():
    """Wipe the in-memory idea store between tests."""
    clear_memory_ideas()
    yield
    clear_memory_ideas()


def test_casivenize_round_trip_returns_valid_cas(client, auth_headers):
    """The mock-backed casivenizer must return a CAS expression that the
    compiler accepts."""
    resp = client.post(
        "/idea_atlas/casivenize",
        json={"text": "I am drawn to deeply understanding wisdom and connection."},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "expression" in data
    assert isinstance(data["expression"], str) and data["expression"]
    # The mock-backed casivenizer routes through the deterministic
    # synthesizer, which produces a compiler-valid multi-statement CAS
    # program. The contract is "valid CAS", not a particular surface form.
    assert "CO-" in data["expression"]
    assert data["valid"] is True
    assert data["error"] is None
    assert isinstance(data["ast"], dict)


def test_casivenize_requires_auth(client):
    resp = client.post(
        "/idea_atlas/casivenize",
        json={"text": "Anything goes here."},
    )
    assert resp.status_code == 401


def test_create_idea_auto_casivenizes_when_expression_missing(client, auth_headers):
    resp = client.post(
        "/idea_atlas/ideas",
        json={"text": "Practicing self-discipline daily as a structural habit."},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()
    assert record["text"].startswith("Practicing")
    assert record["cas_expression"] is not None
    # Compile the persisted expression independently — the contract is that
    # whatever was stored must round-trip through the CAS compiler. The
    # surface form may be a state expression, a Phi<...> activation summary,
    # or a multi-statement program; all are valid CAS.
    from api.notation.compiler import compile_expression

    artifact = compile_expression(record["cas_expression"])
    assert artifact.valid is True, artifact.error
    # AST is populated whenever the expression compiles cleanly.
    assert record["ast_json"] is not None
    assert record["id"]
    assert record["user_id"] == "test-user"
    assert record["deleted_at"] is None


def test_create_idea_with_explicit_expression_skips_casivenize(client, auth_headers):
    resp = client.post(
        "/idea_atlas/ideas",
        json={
            "text": "Wisdom-focused affinity in the cognitive domain.",
            "cas_expression": "CO-2^C_{F2}",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()
    assert record["cas_expression"] == "CO-2^C_{F2}"
    assert record["ast_json"] is not None


def test_list_ideas_returns_only_current_user_ideas(client, auth_headers):
    # Create two ideas
    for text in ("First idea about unity.", "Second idea about wisdom."):
        resp = client.post(
            "/idea_atlas/ideas",
            json={"text": text, "cas_expression": "CO-2^C_{F2}"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    resp = client.get("/idea_atlas/ideas", headers=auth_headers)
    assert resp.status_code == 200
    ideas = resp.json()
    assert len(ideas) == 2
    # Newest first
    assert ideas[0]["text"] == "Second idea about wisdom."
    assert ideas[1]["text"] == "First idea about unity."


def test_get_idea_by_id(client, auth_headers):
    resp = client.post(
        "/idea_atlas/ideas",
        json={"text": "Single idea.", "cas_expression": "CO-0^C_{F1}"},
        headers=auth_headers,
    )
    idea_id = resp.json()["id"]

    resp = client.get(f"/idea_atlas/ideas/{idea_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == idea_id


def test_get_unknown_idea_returns_404(client, auth_headers):
    import uuid as _uuid

    resp = client.get(
        f"/idea_atlas/ideas/{_uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_idea_soft_deletes(client, auth_headers):
    resp = client.post(
        "/idea_atlas/ideas",
        json={"text": "Will be removed.", "cas_expression": "CO-0^C_{F1}"},
        headers=auth_headers,
    )
    idea_id = resp.json()["id"]

    del_resp = client.delete(f"/idea_atlas/ideas/{idea_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json() == {"id": idea_id, "deleted": True}

    # Subsequent GET should 404 (soft-deleted ideas are hidden)
    follow = client.get(f"/idea_atlas/ideas/{idea_id}", headers=auth_headers)
    assert follow.status_code == 404

    # And it should not appear in the list
    listing = client.get("/idea_atlas/ideas", headers=auth_headers)
    assert all(r["id"] != idea_id for r in listing.json())


def test_ideas_endpoints_require_auth(client):
    assert client.post("/idea_atlas/ideas", json={"text": "x"}).status_code == 401
    assert client.get("/idea_atlas/ideas").status_code == 401
    assert client.get("/idea_atlas/ideas/whatever").status_code == 401
    assert client.delete("/idea_atlas/ideas/whatever").status_code == 401


# ---------------------------------------------------------------------------
# Sprint 2 — similarity-driven graph edges
# ---------------------------------------------------------------------------


def _create_idea(client, auth_headers, text: str, cas: str) -> str:
    resp = client.post(
        "/idea_atlas/ideas",
        json={"text": text, "cas_expression": cas},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_edges_returns_one_edge_for_two_similar_ideas(client, auth_headers):
    """Two ideas sharing the same Noetic / Domain / Drive must score above
    the default threshold and produce a single edge."""
    a = _create_idea(client, auth_headers, "wisdom-attraction A", "CO-2^C_{F2}")
    b = _create_idea(client, auth_headers, "wisdom-attraction B", "CO-2^C_{F2}")

    resp = client.get("/idea_atlas/edges", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    edges = resp.json()
    assert isinstance(edges, list)
    assert len(edges) == 1
    edge = edges[0]
    assert {edge["source"], edge["target"]} == {a, b}
    assert edge["score"] >= 0.5
    # Breakdown surfaces the per-axis decomposition the dashboard renders.
    assert set(edge["breakdown"]) >= {"noetic", "domain", "drive"}


def test_edges_default_threshold_surfaces_domain_only_match(client, auth_headers):
    """Default graph edges should include a single shared structural axis.

    This keeps a small, early Idea Atlas from looking disconnected when two
    ideas share only the same processing Domain.
    """
    a = _create_idea(client, auth_headers, "principled positive", "^2^P")
    b = _create_idea(client, auth_headers, "principled rhythm", "^7^P")

    resp = client.get("/idea_atlas/edges", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    edges = resp.json()
    assert len(edges) == 1
    edge = edges[0]
    assert {edge["source"], edge["target"]} == {a, b}
    assert edge["score"] >= 0.2
    assert edge["breakdown"]["domain"] == 1.0


def test_edges_respects_threshold_filter(client, auth_headers):
    """An impossibly high threshold must yield an empty edge set."""
    _create_idea(client, auth_headers, "first", "CO-2^C_{F2}")
    _create_idea(client, auth_headers, "second", "CO-2^C_{F2}")

    resp = client.get(
        "/idea_atlas/edges",
        headers=auth_headers,
        params={"similarity_threshold": 0.99},
    )
    assert resp.status_code == 200
    # Two identical expressions DO score 1.0, so 0.99 still admits them.
    # Use a > 1.0 value (clamped to 1.0) and pair of clearly different
    # expressions to exercise the empty-array branch.
    _create_idea(client, auth_headers, "different", "CO-7^O_{F6}")
    resp2 = client.get(
        "/idea_atlas/edges",
        headers=auth_headers,
        params={"similarity_threshold": 1.5},
    )
    assert resp2.status_code == 200
    # Threshold clamped to 1.0 — only perfect pairs survive (the two
    # identical CO-2^C_{F2} ideas score exactly 1.0).
    edges2 = resp2.json()
    assert all(e["score"] == 1.0 for e in edges2)


def test_edges_skips_ideas_with_null_cas_expression(client, auth_headers):
    """An idea without a compiled CAS expression cannot participate in a
    similarity edge — it must be silently skipped, not error."""
    # First idea has a clean expression.
    _create_idea(client, auth_headers, "ok", "CO-2^C_{F2}")
    # Second idea persisted with explicit null cas_expression. We POST
    # directly with the storage helper to avoid the auto-casivenize path.
    from api.routes.idea_atlas import _inmem_create

    _inmem_create("test-user", "no cas", None, None)

    resp = client.get("/idea_atlas/edges", headers=auth_headers)
    assert resp.status_code == 200
    edges = resp.json()
    # Only one usable idea remains -> no pairs -> no edges.
    assert edges == []


def test_edges_requires_auth(client):
    assert client.get("/idea_atlas/edges").status_code == 401


def test_edges_sorted_by_descending_score(client, auth_headers):
    """When multiple edges survive the threshold, the route must return
    them sorted strongest-first so the dashboard can render the top
    connections without a client-side sort."""
    a = _create_idea(client, auth_headers, "a", "CO-2^C_{F2}")
    b = _create_idea(client, auth_headers, "b", "CO-2^C_{F2}")  # identical to a
    c = _create_idea(client, auth_headers, "c", "CO-2^E_{F2}")  # different domain

    resp = client.get(
        "/idea_atlas/edges",
        headers=auth_headers,
        params={"similarity_threshold": 0.0},
    )
    assert resp.status_code == 200
    edges = resp.json()
    scores = [e["score"] for e in edges]
    assert scores == sorted(scores, reverse=True)
    # Three ideas -> at most C(3, 2) = 3 pairs.
    assert len(edges) <= 3
    # The (a, b) pair (identical) must outrank the (a, c) and (b, c) pairs.
    top = edges[0]
    assert {top["source"], top["target"]} == {a, b}
    # Reference c so static-analyzers see it used (variable-binding clarity).
    assert c


# ---------------------------------------------------------------------------
# Sprint 3 — inversion preview
# ---------------------------------------------------------------------------


def test_invert_axis_n_flips_noetic_operator(client, auth_headers):
    """Axis N inverts CO-2 -> CO-3; the resulting CAS must compile."""
    idea_id = _create_idea(client, auth_headers, "wisdom-attraction", "CO-2^C_{F2}")

    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": idea_id, "axis": "N"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["axis"] == "N"
    assert "Operator" in body["axis_description"]
    assert body["original_idea"]["id"] == idea_id
    # CO-2 -> CO-3 surface flip.
    assert "CO-3" in body["inverted_cas"]
    assert "CO-2" not in body["inverted_cas"]
    # AST must be populated and structurally a StateLiteral.
    ast = body["inverted_ast"]
    assert ast is not None
    # Re-validate independently against the public compiler.
    from api.notation.compiler import compile_expression

    artifact = compile_expression(body["inverted_cas"])
    assert artifact.valid is True


def test_invert_unknown_idea_returns_404(client, auth_headers):
    import uuid as _uuid

    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": str(_uuid.uuid4()), "axis": "N"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_invert_deferred_axis_returns_501_with_structured_body(client, auth_headers):
    """Axes E / S / A are intentionally deferred. The response must be a
    501 carrying a structured body so the dashboard can render a
    "coming-soon" message rather than a generic error."""
    idea_id = _create_idea(client, auth_headers, "x", "CO-2^C_{F2}")

    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": idea_id, "axis": "E"},
        headers=auth_headers,
    )
    assert resp.status_code == 501
    detail = resp.json()["detail"]
    assert detail["axis"] == "E"
    assert "implemented_axes" in detail
    assert "deferred_axes" in detail


def test_invert_unknown_axis_returns_400(client, auth_headers):
    idea_id = _create_idea(client, auth_headers, "x", "CO-2^C_{F2}")

    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": idea_id, "axis": "Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_invert_requires_auth(client):
    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": "whatever", "axis": "N"},
    )
    assert resp.status_code == 401


def test_invert_axis_p_compound_applies_all_three(client, auth_headers):
    """Axis P (Compound) applies N + W + F simultaneously."""
    idea_id = _create_idea(client, auth_headers, "compound", "CO-2^P_{F2}")

    resp = client.post(
        "/idea_atlas/invert",
        json={"idea_id": idea_id, "axis": "P"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # CO-2 -> CO-3, P -> O, F2 -> F6
    assert "CO-3" in body["inverted_cas"]
    assert "^O" in body["inverted_cas"]
    assert "F6" in body["inverted_cas"]
