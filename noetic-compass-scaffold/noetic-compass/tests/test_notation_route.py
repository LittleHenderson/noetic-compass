"""Tests for the notation compiler API route."""


def test_compile_route_returns_artifact(client, auth_headers):
    resp = client.post(
        "/notation/compile",
        json={"expression": "CO-2^C_{F2} -> CO-5^E_{F4}"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["type"]["kind"] == "relation"
    assert data["result"]["kind"] == "relation"
    assert data["bytecode"][-1]["opcode"] == "ARROW"


def test_compile_route_rejects_invalid_expression(client, auth_headers):
    resp = client.post(
        "/notation/compile",
        json={"expression": "CO-5^E_{F4} -> CO-2^C_{F2}"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "domain descent violated" in resp.json()["detail"]


def test_grammar_route_returns_bnf(client, auth_headers):
    resp = client.get("/notation/grammar", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "<program>" in data["grammar"]
    assert "<export_stmt>" in data["grammar"]
    assert "state" in data["notes"]
    assert "types" in data["notes"]


def test_analyze_route_passes_text_to_rich_synthesizer(client, auth_headers):
    resp = client.post(
        "/notation/analyze",
        json={
            "text": (
                "Create an insight recipe from analytical evidence and "
                "affective feeling; deadline support is a catalyst, fatigue "
                "is an inhibitor."
            )
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["valid"] is True
    assert "Theta(Omega_insight)" in data["source"]
    assert "|A" in data["source"]
    assert "|f" in data["source"]
    assert "kappa_deadline" in data["source"]
    assert "iota_fatigue" in data["source"]
