"""Tests for phone/PWA runtime proof evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cas_forex.mobile_phone_proof import (
    build_phone_runtime_proof,
    latest_apk_runtime_observation,
    latest_phone_runtime_observation,
    latest_phone_runtime_proof,
    record_phone_runtime_proof,
)


def _iphone_payload(**overrides):
    payload = {
        "source": "quick-start",
        "app_surface": "pwa",
        "url_origin": "http://10.0.0.6:4173",
        "url_path": "/",
        "display_mode": "standalone",
        "standalone_pwa": True,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        ),
        "platform": "iPhone",
        "language": "en-US",
        "timezone": "America/Los_Angeles",
        "viewport_width": 390,
        "viewport_height": 844,
        "screen_width": 390,
        "screen_height": 844,
        "device_pixel_ratio": 3,
        "max_touch_points": 5,
        "online": True,
    }
    payload.update(overrides)
    return payload


def test_record_phone_runtime_proof_promotes_phone_like_observation(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(url_path="/?cas_owner_token=secret-token"),
        workspace_root=tmp_path,
        client_host="10.0.0.55",
        client_api_base="http://10.0.0.6:4173/api/forex",
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)
    rendered = json.dumps(latest)

    assert proof["phone_browser_verified"] is True
    assert proof["installed_mode_detected"] is True
    assert proof["device_class"] == "phone"
    assert proof["api_base_host"] == "10.0.0.6"
    assert proof["api_base_source"] == "request-header"
    assert proof["api_base_network_path"] == "same_origin_proxy"
    assert proof["api_base_localhost_only"] is False
    assert latest is not None
    assert latest["phone_browser_verified"] is True
    assert latest["is_fresh"] is True
    assert latest["age_seconds"] >= 0
    assert latest["expires_at"]
    assert latest["max_age_hours"] == 24
    assert "owner-authorized runtime gates" in latest["claim_boundary"]
    assert "does not grant" not in latest["claim_boundary"]
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_loopback_phone_like_observation_is_not_verified(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="127.0.0.1",
    )
    observation = latest_phone_runtime_observation(workspace_root=tmp_path)
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert proof["phone_browser_observed"] is True
    assert proof["phone_browser_verified"] is False
    assert proof["local_runtime_only"] is True
    assert proof["effective_client_host"] == "127.0.0.1"
    assert "owner-authorized runtime gates" in proof["claim_boundary"]
    assert "does not grant" not in proof["claim_boundary"]
    assert observation is not None
    assert observation["phone_browser_observed"] is True
    assert observation["phone_browser_verified"] is False
    assert observation["is_fresh"] is True
    assert latest is None


def test_ipv4_mapped_loopback_phone_like_observation_is_not_verified(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="::ffff:127.0.0.1",
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert proof["phone_browser_observed"] is True
    assert proof["phone_browser_verified"] is False
    assert proof["local_runtime_only"] is True
    assert proof["effective_client_host"] == "127.0.0.1"
    assert latest is None


def test_forwarded_phone_observation_from_preview_proxy_is_verified(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="127.0.0.1",
        forwarded_for="10.0.0.55",
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert proof["phone_browser_observed"] is True
    assert proof["phone_browser_verified"] is True
    assert proof["local_runtime_only"] is False
    assert proof["effective_client_host"] == "10.0.0.55"
    assert proof["client_host_source"] == "x-forwarded-for"
    assert latest is not None
    assert latest["phone_browser_verified"] is True


def test_build_phone_runtime_proof_does_not_write_evidence(tmp_path: Path) -> None:
    proof = build_phone_runtime_proof(
        _iphone_payload(),
        client_host="127.0.0.1",
        forwarded_for="10.0.0.55",
        client_api_base="http://10.0.0.6:4173/api/forex",
    )

    assert proof["phone_browser_verified"] is True
    assert proof["client_host_source"] == "x-forwarded-for"
    assert proof["effective_client_host"] == "10.0.0.55"
    assert latest_phone_runtime_proof(workspace_root=tmp_path) is None
    assert latest_phone_runtime_observation(workspace_root=tmp_path) is None


def test_native_apk_phone_proof_records_direct_api_route(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(
            app_surface="apk",
            url_origin="capacitor://localhost",
            url_path="/?page=quick-start",
            display_mode="standalone",
        ),
        workspace_root=tmp_path,
        client_host="10.0.0.55",
        client_api_base="http://10.0.0.6:8765/api/forex",
    )

    assert proof["phone_browser_verified"] is True
    assert proof["app_surface"] == "apk"
    assert proof["api_base_host"] == "10.0.0.6"
    assert proof["api_base_network_path"] == "direct_api"
    assert proof["api_base_source"] == "request-header"
    apk_runtime = latest_apk_runtime_observation(workspace_root=tmp_path)
    assert apk_runtime is not None
    assert apk_runtime["app_surface"] == "apk"
    assert apk_runtime["phone_browser_observed"] is True
    assert apk_runtime["phone_browser_verified"] is True
    assert apk_runtime["is_fresh"] is True


def test_latest_apk_runtime_observation_survives_later_pwa_visit(tmp_path: Path) -> None:
    record_phone_runtime_proof(
        _iphone_payload(
            app_surface="apk",
            url_origin="capacitor://localhost",
            display_mode="standalone",
        ),
        workspace_root=tmp_path,
        client_host="127.0.0.1",
        client_api_base="http://127.0.0.1:8765/api/forex",
    )
    record_phone_runtime_proof(
        _iphone_payload(app_surface="pwa"),
        workspace_root=tmp_path,
        client_host="10.0.0.55",
        client_api_base="http://10.0.0.6:4173/api/forex",
    )

    apk_runtime = latest_apk_runtime_observation(workspace_root=tmp_path)

    assert apk_runtime is not None
    assert apk_runtime["app_surface"] == "apk"
    assert apk_runtime["phone_browser_observed"] is True
    assert apk_runtime["phone_browser_verified"] is False
    assert apk_runtime["local_runtime_only"] is True
    assert apk_runtime["api_base_network_path"] == "loopback_api"


def test_phone_proof_payload_api_base_is_recorded_when_header_absent(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(api_base="http://10.0.0.6:4173/api/forex"),
        workspace_root=tmp_path,
        client_host="10.0.0.55",
    )

    assert proof["phone_browser_verified"] is True
    assert proof["api_base_host"] == "10.0.0.6"
    assert proof["api_base_source"] == "payload"
    assert proof["api_base_network_path"] == "same_origin_proxy"


def test_forwarded_loopback_from_preview_proxy_is_not_verified(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="127.0.0.1",
        forwarded_for="[::ffff:127.0.0.1]:52344",
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert proof["phone_browser_observed"] is True
    assert proof["phone_browser_verified"] is False
    assert proof["local_runtime_only"] is True
    assert proof["effective_client_host"] == "127.0.0.1"
    assert proof["client_host_source"] == "x-forwarded-for"
    assert latest is None


def test_desktop_observation_does_not_overwrite_latest_phone_proof(tmp_path: Path) -> None:
    record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="10.0.0.55",
    )
    desktop = record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "browser",
            "standalone_pwa": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "platform": "Win32",
            "viewport_width": 1280,
            "screen_width": 1920,
            "max_touch_points": 0,
        },
        workspace_root=tmp_path,
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert desktop["phone_browser_verified"] is False
    assert latest is not None
    assert latest["device_class"] == "phone"
    assert latest["phone_browser_verified"] is True


def test_desktop_observation_does_not_hide_latest_phone_like_observation(tmp_path: Path) -> None:
    record_phone_runtime_proof(
        _iphone_payload(),
        workspace_root=tmp_path,
        client_host="127.0.0.1",
    )
    desktop = record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "browser",
            "standalone_pwa": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "platform": "Win32",
            "viewport_width": 1280,
            "screen_width": 1920,
            "max_touch_points": 0,
        },
        workspace_root=tmp_path,
    )
    observation = latest_phone_runtime_observation(workspace_root=tmp_path)
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert desktop["phone_browser_observed"] is False
    assert observation is not None
    assert observation["device_class"] == "phone"
    assert observation["phone_browser_observed"] is True
    assert observation["phone_browser_verified"] is False
    assert observation["is_fresh"] is True
    assert observation["source_path"].endswith("runtime_observations.jsonl")
    assert latest is None


def test_partial_observation_is_safe_desktop_unknown(tmp_path: Path) -> None:
    proof = record_phone_runtime_proof(
        {},
        workspace_root=tmp_path,
        request_user_agent="curl/8.20.0",
    )
    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert proof["phone_browser_verified"] is False
    assert proof["device_class"] == "desktop_or_unknown"
    assert proof["user_agent"] == "curl/8.20.0"
    assert proof["platform"] == ""
    assert latest is None


def test_latest_phone_runtime_proof_normalizes_legacy_scope_wording(tmp_path: Path) -> None:
    proof_dir = tmp_path / "evidence_runs" / "mobile_phone_proof" / "latest"
    proof_dir.mkdir(parents=True)
    (proof_dir / "phone_runtime_proof.json").write_text(
        json.dumps(
            {
                "report_kind": "cas_forex_phone_runtime_proof",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "phone_browser_observed": True,
                "phone_browser_verified": True,
                "device_class": "phone",
                "claim_boundary": "Legacy wording: it does not grant live-money authority.",
            }
        ),
        encoding="utf-8",
    )

    latest = latest_phone_runtime_proof(workspace_root=tmp_path)

    assert latest is not None
    assert "owner-authorized runtime gates" in latest["claim_boundary"]
    assert "does not grant" not in latest["claim_boundary"]
