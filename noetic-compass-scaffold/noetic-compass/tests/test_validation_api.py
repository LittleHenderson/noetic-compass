"""Tests for /validation/* API endpoints."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import create_token

client = TestClient(app)
TOKEN = create_token("test-user")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def temp_data():
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
    with patch("api.validation.correlation.load_machine_results") as mock_m, \
         patch("api.validation.correlation.load_labels") as mock_l, \
         patch("api.validation.correlation.save_labels") as mock_s, \
         patch("api.routes.validation.load_machine_results") as mock_m2, \
         patch("api.routes.validation.load_labels") as mock_l2, \
         patch("api.routes.validation.save_labels") as mock_s2, \
         patch("api.routes.validation.load_calibration_sessions") as mock_calibration_load, \
         patch("api.routes.validation.append_calibration_session") as mock_calibration_append, \
         patch("api.routes.validation.load_evidence") as mock_evidence_load, \
         patch("api.routes.validation.append_evidence_entry") as mock_evidence_append, \
         patch("api.routes.validation.seed_evidence_from_artifacts") as mock_evidence_seed:

        loaded_labels = list(labels)
        calibration_sessions: list[dict] = []
        loaded_evidence = {
            "scorer_agreement": [],
            "benchmark_suites": [],
            "error_cases": [],
        }

        def _load_m(*a, **k):
            return machine["results"]

        def _load_l(*a, **k):
            return loaded_labels

        def _save(new_labels, *a, **k):
            snapshot = list(new_labels)
            loaded_labels.clear()
            loaded_labels.extend(snapshot)

        def _load_evidence(*a, **k):
            return loaded_evidence

        def _load_calibration(*a, **k):
            return calibration_sessions

        def _append_calibration(entry, *a, **k):
            calibration_sessions.append(entry)
            return calibration_sessions

        def _append_evidence(kind, entry, *a, **k):
            loaded_evidence[kind].append(entry)
            return loaded_evidence

        def _seed_evidence(*a, **k):
            loaded_evidence["scorer_agreement"] = [
                {
                    "generator_provider": "mock",
                    "generator_model": "mock-cas-v1",
                    "scorer_provider": "human_panel",
                    "scorer_model": "human_panel_v1",
                    "prompt_excerpt": "First test prompt",
                    "machine_score": 6.9,
                    "scorer_score": 6.5,
                    "item_index": 0,
                    "timestamp": "2026-04-10T12:30:00+00:00",
                    "notes": "seeded scorer agreement",
                }
            ]
            loaded_evidence["benchmark_suites"] = [
                {
                    "suite_name": "baseline-study-mock",
                    "provider": "mock",
                    "model": "mock-cas-v1",
                    "cases_run": 3,
                    "mean_score": 66.4,
                    "variance": 5.2,
                    "timestamp": "2026-04-10T12:35:00+00:00",
                    "notes": "seeded benchmark",
                }
            ]
            loaded_evidence["error_cases"] = [
                {
                    "kind": "false_negative",
                    "provider": "mock",
                    "model": "mock-cas-v1",
                    "prompt_excerpt": "Third test prompt",
                    "expected_tier": "Silver Research Tier",
                    "observed_tier": "Bronze Research Tier",
                    "item_index": 2,
                    "timestamp": "2026-04-10T12:40:00+00:00",
                    "notes": "seeded error case",
                }
            ]
            return loaded_evidence

        mock_m.side_effect = _load_m
        mock_l.side_effect = _load_l
        mock_s.side_effect = _save
        mock_m2.side_effect = _load_m
        mock_l2.side_effect = _load_l
        mock_s2.side_effect = _save
        mock_calibration_load.side_effect = _load_calibration
        mock_calibration_append.side_effect = _append_calibration
        mock_evidence_load.side_effect = _load_evidence
        mock_evidence_append.side_effect = _append_evidence
        mock_evidence_seed.side_effect = _seed_evidence

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
        assert "calibration" in data
        assert "evidence_summary" in data

    def test_calibration_endpoint(self, temp_data):
        res = client.get("/validation/calibration", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "raters" in data
        assert "operators" in data
        assert "items" in data

    def test_calibration_session_endpoint(self, temp_data):
        client.post(
            "/validation/label",
            headers=HEADERS,
            json={
                "item_index": 0,
                "rater": "Bob",
                "operator_scores": [4, 6, 8, 7, 9, 5, 6, 7, 8, 9],
                "domain_scores": [7, 7, 8, 6],
                "notes": "second opinion",
            },
        )
        res = client.get("/validation/calibration/session", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "queue" in data
        assert "recent_sessions" in data
        assert data["queue"][0]["item_index"] == 0
        assert len(data["queue"][0]["labels"]) == 2

    def test_save_calibration_session_endpoint(self, temp_data):
        res = client.post(
            "/validation/calibration/session",
            headers=HEADERS,
            json={
                "item_index": 0,
                "reconciler": "LeadReviewer",
                "disposition": "rubric_clarification",
                "notes": "CO-3 wording needs tightening for policy refusals.",
                "resolved_operator_scores": [5, 6, 7, 8, 9, 5, 6, 7, 8, 9],
                "resolved_domain_scores": [6, 7, 8, 5],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["count"] == 1
        assert data["entry"]["reconciler"] == "LeadReviewer"

    def test_add_scorer_agreement(self, temp_data):
        res = client.post(
            "/validation/evidence/scorer-agreement",
            headers=HEADERS,
            json={
                "generator_provider": "openai",
                "scorer_provider": "anthropic",
                "prompt_excerpt": "Assess this refusal",
                "machine_score": 6.2,
                "scorer_score": 5.8,
                "notes": "close agreement",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["count"] == 1

    def test_add_benchmark_case(self, temp_data):
        res = client.post(
            "/validation/evidence/benchmark-case",
            headers=HEADERS,
            json={
                "suite_name": "safety-redteam-v1",
                "provider": "openai",
                "cases_run": 25,
                "mean_score": 71.4,
                "variance": 3.8,
                "notes": "baseline suite",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["count"] == 1

    def test_add_error_case(self, temp_data):
        res = client.post(
            "/validation/evidence/error-case",
            headers=HEADERS,
            json={
                "kind": "false_negative",
                "prompt_excerpt": "phishing prompt",
                "expected_tier": "Below Prototype Threshold",
                "observed_tier": "Silver",
                "notes": "unsafe response scored too high",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["count"] == 1

    def test_evidence_review_endpoint(self, temp_data):
        client.post(
            "/validation/evidence/scorer-agreement",
            headers=HEADERS,
            json={
                "generator_provider": "openai",
                "generator_model": "gpt-4o-mini",
                "scorer_provider": "anthropic",
                "scorer_model": "claude",
                "prompt_excerpt": "Assess this refusal",
                "machine_score": 6.2,
                "scorer_score": 5.8,
                "notes": "close agreement",
            },
        )
        res = client.get("/validation/evidence?kind=scorer_agreement&provider=openai", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "review" in data
        assert data["review"]["total"] == 1
        assert data["review"]["entries"][0]["provider"] == "openai"

    def test_evidence_trends_endpoint(self, temp_data):
        client.post(
            "/validation/evidence/benchmark-case",
            headers=HEADERS,
            json={
                "suite_name": "safety-redteam-v1",
                "provider": "openai",
                "model": "gpt-4o",
                "cases_run": 25,
                "mean_score": 71.4,
                "variance": 3.8,
                "notes": "baseline suite",
            },
        )
        res = client.get("/validation/evidence/trends", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "timeline" in data
        assert "by_provider" in data
        assert any(row["provider"] == "openai" for row in data["by_provider"])

    def test_seed_evidence_endpoint(self, temp_data):
        res = client.post("/validation/evidence/seed?replace=true", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "seeded"
        assert data["counts"]["scorer_agreement"] == 1

    def test_catalog_endpoint(self, temp_data):
        with patch("api.routes.validation.available_prompt_collections") as mock_catalog:
            mock_catalog.return_value = [{"id": "sample_prompts", "label": "Sample Prompts", "path": "scenarios/sample_prompts.json", "kind": "sample"}]
            res = client.get("/validation/admin/catalog", headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["collections"][0]["id"] == "sample_prompts"

    def test_studies_endpoint(self, temp_data):
        with patch("api.routes.validation.list_study_artifacts") as mock_studies:
            mock_studies.return_value = [{"filename": "study.json", "provider": "mock", "status": "success"}]
            res = client.get("/validation/admin/studies", headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["studies"][0]["provider"] == "mock"

    def test_run_baseline_endpoint(self, temp_data):
        with patch("api.routes.validation.resolve_prompt_collection") as mock_resolve, \
             patch("api.routes.validation.run_and_archive_study", new_callable=AsyncMock) as mock_run, \
             patch("api.routes.validation.seed_evidence_from_artifacts") as mock_seed, \
             patch("api.routes.validation.build_evidence_summary") as mock_summary:
            mock_resolve.return_value = "scenarios/sample_prompts.json"
            mock_run.return_value = {
                "bundle": {
                    "summary": {
                        "provider": "openai",
                        "study_label": "sample_prompts",
                        "status": "failed",
                        "successes": 0,
                        "failures": 1,
                    }
                },
                "archive_path": "validation/studies/openai.json",
                "output_path": "validation/baseline_results.json",
            }
            mock_seed.return_value = {"scorer_agreement": [], "benchmark_suites": [], "error_cases": []}
            mock_summary.return_value = {"scorer_agreement": {"count": 0}, "benchmark_suites": {"count": 0}, "error_cases": {"count": 0}}
            res = client.post(
                "/validation/admin/run-baseline",
                headers=HEADERS,
                json={"provider": "openai", "prompt_collection": "sample_prompts", "count": 1, "reseed": True},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["provider"] == "openai"
        assert data["summary"]["status"] == "failed"
        assert "evidence_summary" in data

    def test_run_suite_matrix_endpoint(self, temp_data):
        with patch("api.routes.validation.run_suite_matrix", new_callable=AsyncMock) as mock_matrix, \
             patch("api.routes.validation.seed_evidence_from_artifacts") as mock_seed, \
             patch("api.routes.validation.build_evidence_summary") as mock_summary:
            mock_matrix.return_value = {
                "provider": "mock",
                "suite_count": 2,
                "success_count": 2,
                "partial_count": 0,
                "failed_count": 0,
                "runs": [],
            }
            mock_seed.return_value = {"scorer_agreement": [], "benchmark_suites": [], "error_cases": []}
            mock_summary.return_value = {"scorer_agreement": {"count": 0}, "benchmark_suites": {"count": 2}, "error_cases": {"count": 0}}
            res = client.post(
                "/validation/admin/run-suite-matrix",
                headers=HEADERS,
                json={"provider": "mock", "suite_ids": ["sample_prompts", "ai_safety"], "count_per_suite": 2, "reseed": True},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["suite_count"] == 2
        assert data["success_count"] == 2

    def test_export_evidence_csv(self, temp_data):
        client.post(
            "/validation/evidence/error-case",
            headers=HEADERS,
            json={
                "kind": "false_positive",
                "provider": "mock",
                "model": "mock-cas-v1",
                "prompt_excerpt": "third prompt",
                "expected_tier": "Bronze Research Tier",
                "observed_tier": "Gold Research Tier",
                "notes": "unsafe overrating",
            },
        )
        res = client.get("/validation/evidence/export?format=csv&kind=error_cases", headers=HEADERS)
        assert res.status_code == 200
        assert "expected_tier" in res.text
        assert "false_positive" in res.text

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
