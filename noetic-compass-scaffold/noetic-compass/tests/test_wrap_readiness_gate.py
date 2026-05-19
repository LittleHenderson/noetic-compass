"""Integration tests for the Stage 20 Generation Readiness Gate wired into
the Wrap Pipeline as an Output Gate companion.

The gate is opt-in. These tests verify:

  - Gate-disabled path: existing Wrap Pipeline behavior unchanged.
  - Gate-enabled + low risk → action `allow`, HTTP 200, no caveat.
  - Gate-enabled + medium risk → action `caveat`, HTTP 200, caveat metadata.
  - Gate-enabled + high risk → action `suppress`, HTTP 422, reason populated.
  - Per-request mode override changes the action where appropriate.
  - The Mode 7 trace surface (top-level `generation_readiness` field) carries
    the full `GenerationReadinessResult.as_dict()` packet.

The high/medium-risk scenarios are driven through the `verification` evidence
packet on the request; the gate's risk logic guarantees that an explicit
`accepted=False` rejection forces `suppress` (in HIGH_PRECISION/BALANCED
modes) and that `decision_tier="medium"` adds elevated risk. Driving the
risk via the verification packet keeps the test deterministic without
having to engineer the LLM/text path to produce specific operator scores.
"""

from __future__ import annotations

from api.middleware.auth import create_token


def _headers(tag: str) -> dict[str, str]:
    """Per-test auth headers with a unique api_key to isolate the monthly
    rate-limit counter from the shared `test-key`."""
    token = create_token(sub=f"test-user-{tag}", api_key=f"test-key-{tag}")
    return {"Authorization": f"Bearer {token}"}


_DEFAULT_TEXT = (
    "Analyze this text for cognitive operator patterns and drive alignment."
)


# ---------------------------------------------------------------------------
# Regression: gate disabled by default — existing behavior must be preserved.
# ---------------------------------------------------------------------------


def test_wrap_readiness_gate_disabled_by_default_response_unchanged(client):
    """Gate-disabled path: response shape is byte-for-byte v7.4-compatible
    aside from the new top-level keys, which must be present-but-null.

    Note: `generation_readiness` and `gate_action` are present as top-level
    fields in the schema. When the gate is disabled (the default), they
    are None. This is the contract: the keys may serialize as null but the
    decision packet itself is absent.
    """
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        # readiness_gate_enabled omitted → server-side default (False).
    }
    resp = client.post("/wrap", json=payload, headers=_headers("gate-default-off"))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # All 8 stages still ran.
    assert [s["stage"] for s in data["stages"]] == [
        "input_analyzer",
        "rpm_gate",
        "dial_adjustment",
        "base_llm_call",
        "operator_scoring",
        "domain_coherence",
        "inversion_scan",
        "output_gate",
    ]
    assert all(s["success"] for s in data["stages"])

    # Gate did not run → packet is null and action is null.
    assert data.get("generation_readiness") is None
    assert data.get("gate_action") is None
    # Provenance carries the explicit disabled flag for audit.
    assert data["provenance"]["readiness_gate_enabled"] is False
    assert data["provenance"]["readiness_gate_action"] is None


def test_wrap_readiness_gate_explicit_false_matches_default(client):
    """Explicit `readiness_gate_enabled=False` must match the default-off
    response shape exactly aside from request-derived provenance."""
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": False,
    }
    resp = client.post("/wrap", json=payload, headers=_headers("gate-explicit-off"))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("generation_readiness") is None
    assert data.get("gate_action") is None
    assert data["provenance"]["readiness_gate_enabled"] is False


# ---------------------------------------------------------------------------
# Gate-enabled paths
# ---------------------------------------------------------------------------


def test_wrap_readiness_gate_enabled_low_risk_allows_emission(client):
    """Enabled + low-risk Verification Stack packet → allow."""
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "BALANCED",
        "verification": {"accepted": True, "decision_tier": "high"},
    }
    resp = client.post("/wrap", json=payload, headers=_headers("gate-on-low"))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["gate_action"] == "allow"
    packet = data["generation_readiness"]
    assert packet is not None
    assert packet["generation_readiness"] == "allow"
    assert packet["mode"] == "BALANCED"
    assert isinstance(packet["risk_score"], (int, float))
    assert packet["risk_score"] <= 0.25  # BALANCED caveat threshold
    assert packet["policy_version"]
    # Mode 7 trace surface — full as_dict() lives at top level.
    for key in ("generation_readiness", "risk_score", "reasons",
                "recommended_mode", "mode", "evidence", "policy_version"):
        assert key in packet
    # Provenance carries the resolved verb.
    assert data["provenance"]["readiness_gate_enabled"] is True
    assert data["provenance"]["readiness_gate_action"] == "allow"


def test_wrap_readiness_gate_enabled_medium_risk_caveats(client):
    """Enabled + medium-tier verification → caveat (HTTP 200 with metadata).

    BALANCED thresholds: caveat 0.25, constrain 0.55, suppress 0.85.
    A `decision_tier="medium"` adds 0.25 risk on its own — exactly the
    caveat threshold, so the action lands on caveat (not constrain).
    """
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "BALANCED",
        "verification": {"accepted": True, "decision_tier": "medium"},
    }
    resp = client.post("/wrap", json=payload, headers=_headers("gate-on-medium"))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["gate_action"] == "caveat"
    packet = data["generation_readiness"]
    assert packet is not None
    assert packet["generation_readiness"] == "caveat"
    # Existing response text must be preserved — gate does not modify it.
    assert data["llm_response"] is not None
    assert len(data["llm_response"]["text"]) > 0
    # Reason from the verification packet must be surfaced.
    assert "verification_tier_medium" in packet["reasons"]


def test_wrap_readiness_gate_enabled_high_risk_suppresses_with_422(client):
    """Enabled + Verification Stack rejection → suppress, HTTP 422.

    `accepted=False` is the strongest forced-action signal in
    BALANCED/HIGH_PRECISION modes. The wrap pipeline must surface this as
    HTTP 422 with the full GenerationReadinessResult as `reason`, not as
    a 500 (which would imply server error rather than deliberate policy).
    """
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "BALANCED",
        "verification": {
            "accepted": False,
            "decision_tier": "low",
            "suppression_reasons": ["test_suppression_rationale"],
        },
    }
    resp = client.post("/wrap", json=payload, headers=_headers("gate-on-suppress"))
    assert resp.status_code == 422, resp.text
    data = resp.json()

    assert data["error_type"] == "generation_readiness_suppression"
    assert data["gate_action"] == "suppress"
    # Full readiness result is serialized as `reason` for audit.
    reason = data["reason"]
    assert reason["generation_readiness"] == "suppress"
    assert "verification_stack_rejected" in reason["reasons"]
    assert "verification:test_suppression_rationale" in reason["reasons"]
    # Reserved policy language — no "rejected", "failed", or "blocked"
    # in the human-facing detail.
    detail = data["detail"].lower()
    for forbidden in ("rejected", "failed", "blocked"):
        assert forbidden not in detail, (
            f"reserved-language violation: '{forbidden}' in detail={detail!r}"
        )


# ---------------------------------------------------------------------------
# Mode override
# ---------------------------------------------------------------------------


def test_wrap_readiness_gate_mode_override_changes_action(client):
    """Same Verification Stack input under MAX_COVERAGE_TRIAGE downgrades
    suppress→constrain. The Stage 20 gate documents this explicitly: in
    MAX_COVERAGE_TRIAGE mode an `accepted=False` rejection forces
    CONSTRAIN (not SUPPRESS). The Wrap Pipeline must propagate the mode
    override so the resolved action reflects the looser policy."""
    verification = {
        "accepted": False,
        "decision_tier": "low",
        "suppression_reasons": ["test_triage_downgrade"],
    }

    # BALANCED → suppress (HTTP 422 path).
    payload_balanced = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "BALANCED",
        "verification": verification,
    }
    resp_balanced = client.post(
        "/wrap", json=payload_balanced, headers=_headers("mode-balanced"),
    )
    assert resp_balanced.status_code == 422
    assert resp_balanced.json()["gate_action"] == "suppress"

    # MAX_COVERAGE_TRIAGE → constrain (HTTP 200, metadata flag).
    payload_triage = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "MAX_COVERAGE_TRIAGE",
        "verification": verification,
    }
    resp_triage = client.post(
        "/wrap", json=payload_triage, headers=_headers("mode-triage"),
    )
    assert resp_triage.status_code == 200, resp_triage.text
    data = resp_triage.json()
    assert data["gate_action"] == "constrain"
    packet = data["generation_readiness"]
    assert packet["mode"] == "MAX_COVERAGE_TRIAGE"
    assert packet["generation_readiness"] == "constrain"
    # Existing response text is preserved on the constrain path — the
    # gate does NOT modify the response; the renderer / referral layer
    # acts on the metadata flag.
    assert data["llm_response"] is not None
    assert len(data["llm_response"]["text"]) > 0


# ---------------------------------------------------------------------------
# Mode 7 trace-surface contract — full as_dict() exposure
# ---------------------------------------------------------------------------


def test_wrap_readiness_gate_mode7_trace_surface_carries_full_as_dict(client):
    """The Mode 7 trace surface contract: the top-level
    `generation_readiness` field carries the full
    `GenerationReadinessResult.as_dict()` output so downstream audit
    tooling (Evidence Packet, Mode 7 inspector) can read the complete
    decision without re-running the gate."""
    payload = {
        "text": _DEFAULT_TEXT,
        "provider": "mock",
        "dial_config": {"values": [6] * 10},
        "mock": True,
        "readiness_gate_enabled": True,
        "verification_mode": "HIGH_PRECISION",
        "verification": {"accepted": True, "decision_tier": "high"},
    }
    resp = client.post(
        "/wrap", json=payload, headers=_headers("trace-surface"),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    packet = data["generation_readiness"]
    assert packet is not None
    # Every field that GenerationReadinessResult.as_dict() produces must
    # be present at the top-level trace surface.
    for required_key in (
        "generation_readiness",
        "risk_score",
        "reasons",
        "recommended_mode",
        "mode",
        "evidence",
        "policy_version",
    ):
        assert required_key in packet, (
            f"Mode 7 trace surface missing required key {required_key!r}"
        )
    assert isinstance(packet["reasons"], list)
    assert isinstance(packet["evidence"], dict)
    assert packet["mode"] == "HIGH_PRECISION"
