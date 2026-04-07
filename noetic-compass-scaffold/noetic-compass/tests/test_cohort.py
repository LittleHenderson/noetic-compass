"""Tests for POST /batch/compare — cohort comparison endpoint."""


def test_cohort_compare_two_profiles(client, auth_headers):
    payload = {
        "profiles": [
            {
                "label": "Alice",
                "operator_scores": [0.8] * 10,
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
            },
            {
                "label": "Bob",
                "operator_scores": [0.6] * 10,
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
            },
        ]
    }
    resp = client.post("/batch/compare", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["distances"]) == 1
    assert data["labels"] == ["Alice", "Bob"]
    d = data["distances"][0]
    assert d["from_label"] == "Alice"
    assert d["to_label"] == "Bob"
    assert 0 <= d["alignment_pct"] <= 100
    assert 0 <= d["similarity_pct"] <= 100
    assert d["geodesic_distance"] >= 0


def test_cohort_compare_identical_profiles(client, auth_headers):
    """Identical profiles should have 100% alignment."""
    scores = [0.7] * 10
    avgs = [0.25, 0.25, 0.25, 0.25]
    payload = {
        "profiles": [
            {"label": "A", "operator_scores": scores, "domain_averages": avgs},
            {"label": "B", "operator_scores": scores, "domain_averages": avgs},
        ]
    }
    resp = client.post("/batch/compare", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    d = data["distances"][0]
    assert d["alignment_pct"] == 100.0
    assert d["similarity_pct"] == 100.0
    assert d["geodesic_distance"] < 0.001
    # Identical profiles should cluster together
    assert data["clusters"][0]["cluster"] == data["clusters"][1]["cluster"]


def test_cohort_compare_three_profiles(client, auth_headers):
    """Three profiles should produce 3 pairwise distances."""
    payload = {
        "profiles": [
            {"label": "X", "operator_scores": [0.9] * 10, "domain_averages": [0.25] * 4},
            {"label": "Y", "operator_scores": [0.5] * 10, "domain_averages": [0.25] * 4},
            {"label": "Z", "operator_scores": [0.9] * 10, "domain_averages": [0.25] * 4},
        ]
    }
    resp = client.post("/batch/compare", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["distances"]) == 3  # C(3,2) = 3
    assert len(data["clusters"]) == 3
    # X and Z are identical, Y is different
    xz = next(d for d in data["distances"] if {d["from_label"], d["to_label"]} == {"X", "Z"})
    assert xz["alignment_pct"] == 100.0


def test_cohort_compare_requires_two(client, auth_headers):
    """Must have at least 2 profiles."""
    payload = {
        "profiles": [
            {"label": "Solo", "operator_scores": [0.7] * 10, "domain_averages": [0.25] * 4},
        ]
    }
    resp = client.post("/batch/compare", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_cohort_compare_bad_simplex(client, auth_headers):
    """Domain averages that don't sum to 1 should be rejected."""
    payload = {
        "profiles": [
            {"label": "A", "operator_scores": [0.7] * 10, "domain_averages": [1.0, 1.0, 1.0, 1.0]},
            {"label": "B", "operator_scores": [0.7] * 10, "domain_averages": [0.25] * 4},
        ]
    }
    resp = client.post("/batch/compare", json=payload, headers=auth_headers)
    assert resp.status_code == 422
