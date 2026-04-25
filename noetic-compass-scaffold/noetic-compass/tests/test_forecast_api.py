"""Tests for Predictive Lacunarity Risk API."""


def balanced_payload() -> dict:
    return {
        "context_label": "balanced reference",
        "source": "manual",
        "operator_scores": [6.0] * 10,
        "domain_scores": [0.25, 0.25, 0.25, 0.25],
        "drive_scores": [0.55] * 7,
        "rpm_completeness": 0.9,
        "fractal_sequence": [0, 2, 3, 5, 6, 8, 9],
    }


def high_lacunarity_payload() -> dict:
    return {
        "context_label": "agency without grounding",
        "source": "research",
        "operator_scores": [1.0, 1.0, 2.0, 2.5, 1.0, 2.0, 8.0, 1.0, 9.0, 1.0],
        "domain_scores": [0.48, 0.35, 0.08, 0.09],
        "drive_scores": [0.2, 0.05, 0.2, 0.1, 0.95, 0.1, 0.15],
        "rpm_completeness": 0.25,
        "fractal_sequence": [8, 6, 8, 6, 8],
        "resolution_details": [],
    }


def test_forecast_requires_auth(client):
    resp = client.post("/forecast", json=balanced_payload())
    assert resp.status_code == 401


def test_balanced_profile_returns_low_or_watch_risk(client, auth_headers):
    resp = client.post("/forecast", json=balanced_payload(), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "predictive_lacunarity_risk"
    assert data["risk_band"] in {"low", "watch"}
    assert data["lacunarity"]["gap_map"]["absent_domains"] == []
    assert data["validation_status"] == "heuristic_preview_not_prospectively_validated"
    assert len(data["forecasts"]) == 6


def test_high_lacunarity_profile_returns_ranked_structural_risks(client, auth_headers):
    resp = client.post("/forecast", json=high_lacunarity_payload(), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_band"] in {"elevated", "high"}
    assert data["forecasts"][0]["risk_score"] >= data["forecasts"][-1]["risk_score"]
    ids = {item["id"] for item in data["forecasts"]}
    assert "action_before_understanding" in ids
    assert "causal_drift" in ids
    assert data["dominant_structural_gaps"]["weak_domains"] == ["E", "O"]
    assert "deterministic predictions" in data["limitations"][0]


def test_forecast_rejects_out_of_range_scores(client, auth_headers):
    payload = balanced_payload()
    payload["operator_scores"][0] = 11.0
    resp = client.post("/forecast", json=payload, headers=auth_headers)
    assert resp.status_code == 422
