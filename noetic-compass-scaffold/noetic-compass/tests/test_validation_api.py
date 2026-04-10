"""Tests for /validation/* API endpoints."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import create_token

client = TestClient(app)
TOKEN = create_token("test-user")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def temp_data(tmp_path):
    """Create temporary baseline_results.json and human_labels.json."""
    machine = {
        "summary": {"prompt_count": 3},
        "results": [
            {
                "index": 0,
                "prompt": "First test prompt",
                "operator_scores": [0.5, 0.6, 0.7, 0.8, 0.9, 0.5, 0.6, 0.7, 0.8, 0.9],
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
                "llm_response": {"text": "First AI response", "model": "mock"},
            },
            {
                "index": 1,
                "prompt": "Second test prompt",
                "operator_scores": [0.4, 0.5, 0.6, 0.7, 0.8, 0.4, 0.5, 0.6, 0.7, 0.8],
                "domain_averages": [0.3, 0.2, 0.25, 0.25],
                "llm_response": {"text": "Second AI response", "model": "mock"},
            },
            {
                "index": 2,
                "prompt": "Third test prompt",
                "operator_scores": [0.3, 0.4, 0.5, 0.6, 0.7, 0.3, 0.4, 0.5, 0.6, 0.7],
                "domain_averages": [0.2, 0.3, 0.25, 0.25],
                "llm_response": {"text": "Third AI response", "model": "mock"},
            },
        ],
    }
    labels = [
        {
            "item_index": 0,
            "rater": "Alice",
            "timestamp": "2026-04-10T12:00:00+00:00",
            "operator_scores": [5, 6, 7, 8, 9, 5, 6, 7, 8, 9],
            "domain_scores": [6, 7, 8, 5],
            "prompt": "First test prompt",
        },
    ]

    machine_path = tmp_path / "baseline_results.json"
    labels_path = tmp_path / "human_labels.json"
    machine_path.write_text(json.dumps(machine))
    labels_path.write_text(json.dumps(labels))

    with patch("api.validation.correlation.load_machine_results") as mock_m, \
         patch("api.validation.correlation.load_labels") as mock_l, \
         patch("api.validation.correlation.save_labels") as mock_s, \
         patch("api.routes.validation.load_machine_results") as mock_m2, \
         patch("api.routes.validation.load_labels") as mock_l2, \
         patch("api.routes.validation.save_labels") as mock_s2:

        loaded_labels = list(labels)

        def _load_m(*a, **k):
            return machine["results"]

        def _load_l(*a, **k):
            return loaded_labels

        def _save(new_labels, *a, **k):
            loaded_labels.clear()
            loaded_labels.extend(new_labels)

        mock_m.side_effect = _load_m
        mock_l.side_effect = _load_l
        mock_s.side_effect = _save
        mock_m2.side_effect = _load_m
        mock_l2.side_effect = _load_l
        mock_s2.side_effect = _save

        yield {"machine": machine, "labels": loaded_labels}


class TestValidationAPI:
    def test_list_items(self, temp_data):
        res = client.get("/validation/items", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert data["labeled"] == 1

    def test_get_next_item_for_new_rater(self, temp_data):
        res = client.get("/validation/next?rater=Bob", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        # Bob hasn't labeled anything — should get item 0
        assert data["item_index"] == 0
        assert "First test prompt" in data["prompt"]
        assert data["response"] == "First AI response"
        assert data["model"] == "mock"
        assert data["rater_progress"] == 0

    def test_get_next_item_for_alice_skips_labeled(self, temp_data):
        res = client.get("/validation/next?rater=Alice", headers=HEADERS)
        data = res.json()
        # Alice already labeled item 0 → should get item 1
        assert data["item_index"] == 1
        assert "Second" in data["prompt"]

    def test_submit_label(self, temp_data):
        res = client.post(
            "/validation/label",
            headers=HEADERS,
            json={
                "item_index": 1,
                "rater": "Bob",
                "operator_scores": [4, 5, 6, 7, 8, 4, 5, 6, 7, 8],
                "domain_scores": [5, 6, 7, 4],
                "notes": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["machine_scores"] is not None
        assert len(data["machine_scores"]) == 10
        # Machine score 0.4 scaled to 4.0
        assert data["machine_scores"][0] == 4.0

    def test_submit_label_invalid_operator_count(self, temp_data):
        res = client.post(
            "/validation/label",
            headers=HEADERS,
            json={
                "item_index": 0,
                "rater": "Bob",
                "operator_scores": [5, 5, 5],  # wrong length
                "domain_scores": [5, 5, 5, 5],
            },
        )
        assert res.status_code == 422

    def test_submit_label_out_of_range(self, temp_data):
        res = client.post(
            "/validation/label",
            headers=HEADERS,
            json={
                "item_index": 0,
                "rater": "Bob",
                "operator_scores": [15, 5, 5, 5, 5, 5, 5, 5, 5, 5],
                "domain_scores": [5, 5, 5, 5],
            },
        )
        assert res.status_code == 422

    def test_stats_endpoint(self, temp_data):
        res = client.get("/validation/stats", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "total_labels" in data
        assert "num_raters" in data
        assert "overall_pearson_r" in data

    def test_leaderboard_endpoint(self, temp_data):
        res = client.get("/validation/leaderboard", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "stats" in data
        assert "operator_correlations" in data
        assert len(data["operator_correlations"]) == 10
        assert "recommendations" in data
        assert "inter_rater" in data

    def test_export_json(self, temp_data):
        res = client.get("/validation/export?format=json", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "labels" in data

    def test_export_csv(self, temp_data):
        res = client.get("/validation/export?format=csv", headers=HEADERS)
        assert res.status_code == 200
        # CSV header should contain the operator columns
        assert "CO-0" in res.text
        assert "item_index" in res.text

    def test_no_auth_rejected(self, temp_data):
        res = client.get("/validation/items")
        assert res.status_code == 401
