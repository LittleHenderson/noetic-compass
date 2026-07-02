"""Tests for the always-on operator scheduler (ai_operator_runner) + routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cas_forex import ai_operator_runner


def test_desired_state_persists_and_restores(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        ai_operator_runner.set_desired_runner_state(1200, desired_running=True)
        control = ai_operator_runner.control_state()
        assert control["desired_running"] is True
        assert control["interval_seconds"] == 1200
    finally:
        ai_operator_runner.stop_runner(persist_desired=False)
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_off_by_default_restore_does_not_start(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        status = ai_operator_runner.restore_desired_state_on_startup()
        assert status["running"] is False
        assert status["desired_running"] is False
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_interval_is_clamped(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        status = ai_operator_runner.set_desired_runner_state(5, desired_running=False)  # below min
        assert status["interval_seconds"] >= ai_operator_runner.MIN_INTERVAL_SECONDS
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_route_state_exposes_provider_and_actions(tmp_path):
    from api.routes import ai_operator as route

    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    client = TestClient(app)
    try:
        resp = client.get("/api/forex/ai-operator/state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["report_kind"] == "cas_forex_ai_operator_runner"
        assert "model_provider" in body
        assert "recent_actions" in body
        assert "claim_boundary" in body
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)
