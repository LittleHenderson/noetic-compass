"""Tests for the Idea Atlas adapter — POST predict_cas output to live API or fall back locally."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cas_native.inference import atlas_adapter
from cas_native.inference.atlas_adapter import (
    AtlasPostResult,
    _build_cas_expression_from_prediction,
    list_local_fallback,
    post_prediction,
)


@pytest.fixture
def isolated_fallback(tmp_path, monkeypatch):
    fallback = tmp_path / "atlas_local.jsonl"
    monkeypatch.setattr(atlas_adapter, "LOCAL_FALLBACK_PATH", fallback)
    yield fallback


def test_build_cas_expression_full():
    pred = {"noetic": "^3", "domain": "E", "drive": "F4", "register": "f"}
    assert _build_cas_expression_from_prediction(pred) == "^3^E_{F4}|f"


def test_build_cas_expression_no_register():
    pred = {"noetic": "^2", "domain": "P", "drive": "F2", "register": None}
    assert _build_cas_expression_from_prediction(pred) == "^2^P_{F2}"


def test_build_cas_expression_neutral_register():
    pred = {"noetic": "^7", "domain": "O", "drive": "F6", "register": "neutral"}
    assert _build_cas_expression_from_prediction(pred) == "^7^O_{F6}"


def test_build_cas_expression_bare_noetic_digit():
    pred = {"noetic": "5", "domain": "C", "drive": "F1"}
    assert _build_cas_expression_from_prediction(pred) == "^5^C_{F1}"


def test_post_prediction_no_jwt_falls_back_locally(isolated_fallback, monkeypatch):
    monkeypatch.delenv("NC_DEV_JWT", raising=False)
    monkeypatch.delenv("NC_API_JWT", raising=False)
    result = post_prediction(
        "I keep practicing the same scale every day",
        {"noetic": "^7", "domain": "O", "drive": "F6", "register": "E"},
    )
    assert result.posted_to_api is False
    assert result.cas_expression == "^7^O_{F6}|E"
    assert result.fallback_path == isolated_fallback
    assert "no jwt" in result.error.lower()
    assert isolated_fallback.exists()


def test_local_fallback_records_have_expected_shape(isolated_fallback, monkeypatch):
    monkeypatch.delenv("NC_DEV_JWT", raising=False)
    monkeypatch.delenv("NC_API_JWT", raising=False)
    post_prediction(
        "The thought just popped into my head",
        {"noetic": "^9", "domain": "C", "drive": "F1"},
    )
    records = list_local_fallback()
    assert len(records) == 1
    rec = records[0]
    assert rec["prompt"] == "The thought just popped into my head"
    assert rec["prediction"]["noetic"] == "^9"
    assert "logged_at" in rec
    assert "reason" in rec


def test_post_prediction_connect_error_falls_back_locally(isolated_fallback, monkeypatch):
    monkeypatch.setenv("NC_DEV_JWT", "fake-jwt")
    monkeypatch.setenv("NC_ATLAS_API_BASE", "http://127.0.0.1:1")  # unreachable port

    result = post_prediction(
        "Drawn to it like a moth to a flame",
        {"noetic": "^2", "domain": "E", "drive": "F4", "register": "f"},
    )
    assert result.posted_to_api is False
    assert result.fallback_path == isolated_fallback
    assert "unreachable" in result.error.lower() or "logged to local fallback" in result.error.lower()


def test_list_local_fallback_empty_when_no_file(tmp_path, monkeypatch):
    fallback = tmp_path / "does_not_exist.jsonl"
    monkeypatch.setattr(atlas_adapter, "LOCAL_FALLBACK_PATH", fallback)
    assert list_local_fallback() == []


def test_list_local_fallback_skips_malformed_lines(isolated_fallback):
    isolated_fallback.parent.mkdir(parents=True, exist_ok=True)
    isolated_fallback.write_text(
        '{"prompt": "ok", "prediction": {"noetic": "^0"}}\n'
        'not json at all\n'
        '{"prompt": "also ok", "prediction": {"noetic": "^1"}}\n',
        encoding="utf-8",
    )
    records = list_local_fallback()
    assert len(records) == 2
    assert records[0]["prompt"] == "ok"
    assert records[1]["prompt"] == "also ok"


def test_atlas_post_result_dataclass_shape():
    r = AtlasPostResult(
        posted_to_api=True,
        idea_id="abc-123",
        cas_expression="^3^P_{F2}|A",
        dashboard_url="http://example/atlas?focus=abc-123",
        fallback_path=None,
        error=None,
    )
    assert r.posted_to_api is True
    assert r.idea_id == "abc-123"
