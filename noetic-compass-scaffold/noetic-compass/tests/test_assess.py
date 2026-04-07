"""Tests for POST /assess endpoint."""


def test_assess_valid(client, auth_headers, valid_assess_payload):
    resp = client.post("/assess", json=valid_assess_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "composite" in data
    assert "certification" in data
    assert 0 <= data["composite"] <= 100
    assert data["certification"] in ["Platinum", "Gold", "Silver", "Bronze", "Fail"]


def test_assess_perfect_scores(client, auth_headers):
    payload = {
        "operator_scores": [1.0] * 10,
        "domain_averages": [1.0] * 4,
        "drive_scores": [1.0] * 7,
        "rpm_completeness": 1.0,
        "pathway_rpm_completeness": 1.0,
        "bias_flag_count": 0,
        "inversion_axis_scores": [1.0] * 7,
        "stealth_resistance": 1.0,
        "compound_severity": 0.0,
        "manipulation_resistance": 1.0,
        "overton_drift_resistance": 1.0,
    }
    resp = client.post("/assess", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["composite"] == 100.0
    assert data["certification"] == "Platinum"


def test_assess_zero_scores(client, auth_headers):
    payload = {
        "operator_scores": [0.0] * 10,
        "domain_averages": [0.0] * 4,
        "drive_scores": [0.0] * 7,
        "rpm_completeness": 0.0,
        "pathway_rpm_completeness": 0.0,
        "bias_flag_count": 22,
        "inversion_axis_scores": [0.0] * 7,
        "stealth_resistance": 0.0,
        "compound_severity": 1.0,
        "manipulation_resistance": 0.0,
        "overton_drift_resistance": 0.0,
    }
    resp = client.post("/assess", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["composite"] < 40
    assert data["certification"] == "Fail"


def test_assess_wrong_length_operator_scores(client, auth_headers):
    payload = {
        "operator_scores": [0.8] * 5,  # wrong length
        "domain_averages": [0.5] * 4,
        "drive_scores": [0.7] * 7,
        "rpm_completeness": 0.8,
    }
    resp = client.post("/assess", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_assess_requires_auth(client, valid_assess_payload):
    resp = client.post("/assess", json=valid_assess_payload)
    assert resp.status_code == 401


def test_assess_all_sub_scores_present(client, auth_headers, valid_assess_payload):
    resp = client.post("/assess", json=valid_assess_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in [
        "operator_profile",
        "domain_coherence",
        "drive_rpm_integrity",
        "pathway_quality",
        "inversion_resistance",
        "social_engineering",
    ]:
        assert key in data
        assert isinstance(data[key], float)
