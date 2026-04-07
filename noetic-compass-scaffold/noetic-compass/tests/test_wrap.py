"""Tests for POST /wrap endpoint (end-to-end pipeline)."""


def test_wrap_mock(client, auth_headers, valid_wrap_payload):
    resp = client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    # Check NCCS result
    assert "nccs" in data
    nccs = data["nccs"]
    assert 0 <= nccs["composite"] <= 100
    assert nccs["certification"] in ["Platinum", "Gold", "Silver", "Bronze", "Fail"]

    # Check all 8 stages ran
    assert "stages" in data
    assert len(data["stages"]) == 8
    stage_names = [s["stage"] for s in data["stages"]]
    assert stage_names == [
        "input_analyzer",
        "rpm_gate",
        "dial_adjustment",
        "base_llm_call",
        "operator_scoring",
        "domain_coherence",
        "inversion_scan",
        "output_gate",
    ]
    for stage in data["stages"]:
        assert stage["success"] is True

    # Check LLM response present
    assert data["llm_response"] is not None
    assert data["llm_response"]["model"] == "mock-cas-v1"


def test_wrap_with_custom_dials(client, auth_headers):
    payload = {
        "text": "Test text for assessment with custom dials.",
        "provider": "mock",
        "dial_config": {"values": [4, 5, 6, 7, 8, 5, 6, 7, 4, 5]},
        "mock": True,
    }
    resp = client.post("/wrap", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nccs"]["composite"] > 0


def test_wrap_invalid_dials_422(client, auth_headers):
    """Involution pair divergence > 4 should return 422."""
    payload = {
        "text": "Test text.",
        "provider": "mock",
        "dial_config": {"values": [6, 6, 3, 9, 6, 6, 6, 6, 6, 6]},  # CO-2=3, CO-3=9 => divergence 6
        "mock": True,
    }
    resp = client.post("/wrap", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_wrap_empty_text_422(client, auth_headers):
    payload = {"text": "", "mock": True}
    resp = client.post("/wrap", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_wrap_requires_auth(client, valid_wrap_payload):
    resp = client.post("/wrap", json=valid_wrap_payload)
    assert resp.status_code == 401
