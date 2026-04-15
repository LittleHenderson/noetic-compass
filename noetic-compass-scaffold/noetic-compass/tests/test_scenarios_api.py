"""Tests for scenarios API endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import create_token

client = TestClient(app)
TOKEN = create_token("test-user")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

CATALOG_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "catalog"


class TestScenariosAPI:
    def test_get_all_scenarios(self):
        res = client.get("/scenarios", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "scenarios" in data
        assert "total" in data
        assert data["total"] > 0

    def test_total_matches_length(self):
        res = client.get("/scenarios", headers=HEADERS)
        data = res.json()
        assert data["total"] == len(data["scenarios"])

    def test_filter_by_category(self):
        res = client.get("/scenarios?category=healthcare", headers=HEADERS)
        data = res.json()
        assert all(s["category"] == "healthcare" for s in data["scenarios"])
        assert data["total"] > 0

    def test_filter_by_difficulty(self):
        res = client.get("/scenarios?difficulty=hard", headers=HEADERS)
        data = res.json()
        assert all(s.get("difficulty") == "hard" for s in data["scenarios"])

    def test_filter_by_operator(self):
        res = client.get("/scenarios?co=3", headers=HEADERS)
        data = res.json()
        assert all(3 in s.get("target_operators", []) for s in data["scenarios"])

    def test_search(self):
        res = client.get("/scenarios?q=ventilator", headers=HEADERS)
        data = res.json()
        assert data["total"] > 0

    def test_get_categories(self):
        res = client.get("/scenarios/categories", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert len(data["categories"]) >= 10
        assert data["total"] > 200

    def test_get_by_id(self):
        res = client.get("/scenarios/hc-001", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "hc-001"
        assert "prompt_text" in data or "prompt" in data

    def test_get_by_id_not_found(self):
        res = client.get("/scenarios/nonexistent-999", headers=HEADERS)
        data = res.json()
        assert "error" in data

    def test_all_scenarios_have_required_fields(self):
        res = client.get("/scenarios", headers=HEADERS)
        for s in res.json()["scenarios"]:
            assert "id" in s, f"Missing id"
            assert "category" in s, f"Missing category in {s.get('id')}"
            assert ("prompt_text" in s or "prompt" in s), f"Missing prompt in {s.get('id')}"

    def test_adversarial_scenarios_expose_friendly_titles(self):
        res = client.get("/scenarios/cbr-04", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "cbr-04"
        assert data["title"] == "Reciprocity Exploitation"
        assert data["title"] != data["id"]

    def test_catalog_files_exist(self):
        expected = [
            "healthcare", "hiring", "finance", "governance", "education",
            "relationships", "ai_safety", "environmental", "adversarial_resilience",
            "life_execution", "cas_patterns",
        ]
        for name in expected:
            path = CATALOG_DIR / f"{name}.json"
            assert path.exists(), f"Missing catalog: {name}.json"
