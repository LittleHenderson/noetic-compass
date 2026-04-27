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
