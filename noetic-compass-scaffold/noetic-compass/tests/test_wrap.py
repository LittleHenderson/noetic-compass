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
    assert data["scoring_method"] in ["secondary_llm", "self_reported", "heuristic_fallback"]
    assert data["provenance"]["scoring_method"] == data["scoring_method"]
    assert data["provenance"]["requested_scoring_mode"] == "heuristic_fallback"

    # Check AI interpretation is present
    assert "interpretation" in data
    interp = data["interpretation"]
    assert interp is not None
    assert isinstance(interp["bottom_line"], str)
    assert len(interp["bottom_line"]) > 0
    assert isinstance(interp["findings"], list)
    assert len(interp["findings"]) >= 1
    assert isinstance(interp["recommendations"], list)
    assert len(interp["recommendations"]) >= 1


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


# ---------------------------------------------------------------------------
# CAS v7.5 Phenomenological Register data flow — end-to-end wrap tests.
# (Clarification 8, rollout track (j).)
# ---------------------------------------------------------------------------


class _RegisterAnnotatedMockConnector:
    """Test connector that emits CAS v7.5 register-annotated scores.

    Used to drive the `self_reported` scoring path through the wrap
    pipeline so the register data flow can be verified end-to-end
    (LLM output → parser → OperatorScoreResult → wrap API response).
    """

    provider_name = "mock"
    model = "mock-register-annotated-v1"
    max_retries = 1

    async def generate(self, prompt: str, system_prompt: str = "", **_: object):
        from api.llm_connectors.base import LLMResponse

        text = (
            "CAS Assessment Result:\n"
            "Operator Scores: [0.72|T, 0.81|A, 0.64|f, 0.55|E, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]\n"
            "Analysis: Register-annotated self-report for end-to-end test."
        )
        return LLMResponse(
            text=text,
            model="mock-register-annotated-v1",
            usage={},
        )


def _unique_auth_headers(tag: str) -> dict[str, str]:
    """Per-test auth headers with a unique `api_key` to isolate the monthly
    rate-limit counter. The suite-wide `test-key` accumulates across tests;
    new tests use their own keys so they don't push the shared counter past
    the community-tier cap (50 assessments per month).
    """
    from api.middleware.auth import create_token
    token = create_token(sub=f"test-user-{tag}", api_key=f"test-key-{tag}")
    return {"Authorization": f"Bearer {token}"}


def test_wrap_register_annotated_self_report_flows_to_api(client, monkeypatch):
    """End-to-end: register-annotated LLM output → wrap response carries score_registers."""
    from api.routes import wrap as wrap_route
    from api.pipeline import runner as runner_module

    connector = _RegisterAnnotatedMockConnector()

    def fake_get_connector(provider, model=None):
        return connector

    monkeypatch.setattr(wrap_route, "get_connector", fake_get_connector)
    monkeypatch.setattr(runner_module, "get_connector", fake_get_connector)

    headers = _unique_auth_headers("register-flow")
    payload = {
        "text": "Analyze text for register-annotated cognitive operator patterns.",
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "scoring_mode": "self_reported",
    }
    resp = client.post("/wrap", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Top-level `score_registers` is the canonical serialization point.
    assert "score_registers" in data
    assert data["score_registers"] == [
        "T", "A", "f", "E", None, None, None, None, None, None,
    ]

    # The operator_scoring stage carries score_registers too (defense-in-depth).
    op_stage = next(s for s in data["stages"] if s["stage"] == "operator_scoring")
    assert op_stage["data"].get("score_registers") == [
        "T", "A", "f", "E", None, None, None, None, None, None,
    ]
    # Scoring method must reflect the self-reported path that emitted registers.
    assert data["scoring_method"] == "self_reported"


def test_wrap_register_neutral_preserves_v74_shape(client):
    """Backward-compat: register-neutral assessment → score_registers is null/absent.

    The default mock connector emits plain v7.4 `Operator Scores: [...]`
    with no register annotations. Through the heuristic-fallback path we
    exercise the register-neutral output branch; `score_registers` is
    `None` at the Pydantic level and serialized as `null` in JSON.
    """
    headers = _unique_auth_headers("register-neutral")
    payload = {
        "text": "Analyze this text for v7.4-shape register-neutral assessment.",
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        # heuristic_fallback is the register-neutral path by construction.
        "scoring_mode": "heuristic_fallback",
    }
    resp = client.post("/wrap", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Register-neutral: the field is present but null (or equivalently absent).
    # Either shape is acceptable per the backward-compat contract.
    assert data.get("score_registers") in (None, [None] * 10)

    # The operator_scoring stage data MUST NOT contain score_registers at
    # all in the register-neutral path — preserving byte-for-byte v7.4
    # stage-data shape for clients that inspect stages directly.
    op_stage = next(s for s in data["stages"] if s["stage"] == "operator_scoring")
    assert "score_registers" not in op_stage["data"]
