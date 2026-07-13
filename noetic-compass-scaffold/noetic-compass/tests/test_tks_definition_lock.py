from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.services.cas_harness_tks_definition_lock import (
    DEFAULT_TKS_DEFINITION_PATH,
    LOCKED_TKS_DEFINITION_SHA256,
    TKSDefinitionLockError,
    assert_tks_definition_lock_for_audit,
    sha256_file,
    tks_definition_lock_status,
)


def test_packaged_tks_definitions_match_locked_hash():
    assert sha256_file(DEFAULT_TKS_DEFINITION_PATH) == LOCKED_TKS_DEFINITION_SHA256


def test_tks_definition_hash_is_checkout_line_ending_independent(tmp_path):
    payload = DEFAULT_TKS_DEFINITION_PATH.read_bytes()
    lf_payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf_payload = lf_payload.replace(b"\n", b"\r\n")

    lf_path = tmp_path / "definitions-lf.json"
    crlf_path = tmp_path / "definitions-crlf.json"
    lf_path.write_bytes(lf_payload)
    crlf_path.write_bytes(crlf_payload)

    assert sha256_file(lf_path) == LOCKED_TKS_DEFINITION_SHA256
    assert sha256_file(crlf_path) == LOCKED_TKS_DEFINITION_SHA256

    tampered_path = tmp_path / "definitions-tampered.json"
    tampered_path.write_bytes(lf_payload.replace(b'"element_count": 40', b'"element_count": 41', 1))
    assert sha256_file(tampered_path) != LOCKED_TKS_DEFINITION_SHA256


def test_tks_definition_lock_status_accepts_packaged_bundle():
    status = assert_tks_definition_lock_for_audit()

    assert status.locked is True
    assert status.definition_sha256 == LOCKED_TKS_DEFINITION_SHA256
    assert status.probe_bundle_definition_sha256 == LOCKED_TKS_DEFINITION_SHA256
    assert status.probe_bundle_id == "definition_locked_tks_fixture_20260603"
    assert status.probe_status == "definition_fixture_locked_no_trained_probe_claim"


def test_tks_definition_lock_rejects_wrong_probe_bundle_hash(tmp_path):
    manifest = {
        "schema_version": "cas_harness_tks_probe_bundle_definition_lock.v1",
        "bundle_id": "wrong-definitions",
        "definition_sha256": "0" * 64,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(TKSDefinitionLockError, match="active TKS probe bundle"):
        tks_definition_lock_status(probe_bundle_manifest_path=path)


def test_audit_session_creation_refuses_when_tks_lock_fails(client, auth_headers, monkeypatch):
    def _fail():
        raise TKSDefinitionLockError("wrong TKS definitions")

    monkeypatch.setattr("api.routes.cas_harness_audit.assert_tks_definition_lock_for_audit", _fail)

    resp = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "openai:gpt-4.1-mini",
            "audit_mode": "BALANCED",
            "prompt": "Assess whether this answer should be accepted or suppressed.",
            "selected_modules": ["cognitive_bias", "provenance_trace"],
            "license_key": "placeholder-license",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 503
    assert "TKS definition lock failed" in resp.text
    assert "wrong TKS definitions" in resp.text


def test_distributed_audit_creation_refuses_when_tks_lock_fails(client, auth_headers, monkeypatch):
    def _fail():
        raise TKSDefinitionLockError("wrong TKS definitions")

    monkeypatch.setattr("api.routes.cas_harness_audit.assert_tks_definition_lock_for_audit", _fail)

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "customer/open-weight-20b",
            "weight_access": "open_weight",
            "parameter_count_b": 20,
            "num_layers": 20,
            "accept_audit_data_capture": True,
        },
        headers=auth_headers,
    )

    assert resp.status_code == 503
    assert "TKS definition lock failed" in resp.text
    assert "wrong TKS definitions" in resp.text
