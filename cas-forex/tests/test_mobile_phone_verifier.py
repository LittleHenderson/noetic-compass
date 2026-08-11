"""Tests for the one-command phone proof watcher."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cas_forex.mobile_phone_proof import record_phone_runtime_proof
from cas_forex.mobile_phone_verifier import (
    PhoneProofWatchStatus,
    phone_proof_watch_status,
    render_phone_proof_watch_status,
)


def _iphone_payload() -> dict:
    return {
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


def _desktop_payload() -> dict:
    payload = _iphone_payload()
    payload.update(
        {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
            "platform": "Win32",
            "display_mode": "browser",
            "standalone_pwa": False,
            "max_touch_points": 0,
            "device_pixel_ratio": 1,
        }
    )
    return payload


def _script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "watch_mobile_phone_proof.py"
    spec = importlib.util.spec_from_file_location("watch_mobile_phone_proof_for_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _watch_status(*, verified: bool = False) -> PhoneProofWatchStatus:
    return PhoneProofWatchStatus(
        status="VERIFIED" if verified else "MISSING",
        phone_browser_verified=verified,
        phone_browser_observed=verified,
        phone_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        tested_quick_start_url="http://127.0.0.1:4173/?page=quick-start",
        phone_proof_watcher_command="npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
        mobile_readiness_command="npm --prefix ui run mobile:readiness -- --web-base http://127.0.0.1:4173",
        active_evidence_kind="verified_phone_proof" if verified else "none",
        installed_mode_detected=verified,
        effective_client_host="10.0.0.55" if verified else None,
        client_host_source="request-client" if verified else None,
        generated_at="2026-07-05T00:00:00+00:00" if verified else None,
        phone_proof_fresh=verified,
        phone_proof_age_seconds=5 if verified else None,
        phone_proof_expires_at="2026-07-06T00:00:00+00:00" if verified else None,
        phone_observation_fresh=False,
        phone_observation_age_seconds=None,
        phone_observation_expires_at=None,
        readiness_source_path="evidence_runs/web_phone_release/latest/mobile_release_readiness.json",
        summary="Verified." if verified else "No fresh phone-like Quick Start runtime proof is recorded.",
        next_steps=("Open Quick Start from the real phone.",),
    )


def test_phone_proof_watcher_reports_missing_with_actionable_steps(tmp_path: Path) -> None:
    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "MISSING"
    assert status.phone_browser_verified is False
    assert status.phone_quick_start_url is None
    assert status.active_evidence_kind == "none"
    assert "No fresh phone-like Quick Start runtime proof" in status.summary
    assert "Phone proof freshness: none" in rendered
    assert "Scan the phone PWA pairing QR" in rendered


def test_phone_proof_script_prints_initial_handoff_before_wait(monkeypatch, capsys) -> None:
    script = _script_module()
    initial = _watch_status(verified=False)
    final = _watch_status(verified=False)

    monkeypatch.setattr(script, "phone_proof_watch_status", lambda **_: initial)
    monkeypatch.setattr(script, "wait_for_phone_proof", lambda **_: final)

    assert script.main(["--timeout-seconds", "0", "--poll-seconds", "0.1"]) == 0

    out = capsys.readouterr().out
    assert "Initial phone proof status:" in out
    assert "Waiting up to 0s for verified real-phone proof" in out
    assert "Final phone proof status:" in out
    assert out.count("CAS Forex phone proof watcher") == 2
    assert "Phone Quick Start URL: http://10.0.0.6:4173/?page=quick-start" in out


def test_phone_proof_script_json_mode_stays_machine_readable(monkeypatch, capsys) -> None:
    script = _script_module()
    final = _watch_status(verified=True)

    monkeypatch.setattr(script, "wait_for_phone_proof", lambda **_: final)

    assert script.main(["--json", "--timeout-seconds", "0"]) == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["phone_browser_verified"] is True
    assert "Initial phone proof status" not in out
    assert "Final phone proof status" not in out


def test_phone_proof_watcher_separates_local_observation_from_verified_proof(tmp_path: Path) -> None:
    record_phone_runtime_proof(_iphone_payload(), workspace_root=tmp_path, client_host="127.0.0.1")

    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "OBSERVED_NOT_VERIFIED"
    assert status.phone_browser_observed is True
    assert status.phone_browser_verified is False
    assert status.phone_quick_start_url is None
    assert status.active_evidence_kind == "phone_observation"
    assert status.phone_observation_fresh is True
    assert status.phone_observation_age_seconds is not None
    assert status.installed_mode_detected is True
    assert status.effective_client_host == "127.0.0.1"
    assert "localhost/local-only" in status.summary
    assert "Phone observation freshness: fresh" in rendered
    assert "not desktop emulation" in rendered


def test_phone_proof_watcher_labels_fresh_desktop_observation_without_calling_it_stale(tmp_path: Path) -> None:
    record_phone_runtime_proof(_desktop_payload(), workspace_root=tmp_path, client_host="127.0.0.1")

    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "LOCAL_DESKTOP_ONLY"
    assert status.phone_browser_observed is False
    assert status.phone_browser_verified is False
    assert status.active_evidence_kind == "local_desktop_observation"
    assert status.phone_observation_fresh is True
    assert "desktop_or_unknown/local-only" in status.summary
    assert "does not count as real-phone proof" in status.summary
    assert "[LOCAL_DESKTOP_ONLY]" in rendered
    assert "Phone observation freshness: fresh" in rendered
    assert "expired" not in status.summary
    assert "not the PC browser" in rendered


def test_phone_proof_watcher_reports_verified_lan_phone_proof(tmp_path: Path) -> None:
    record_phone_runtime_proof(_iphone_payload(), workspace_root=tmp_path, client_host="10.0.0.55")

    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "VERIFIED"
    assert status.phone_browser_observed is True
    assert status.phone_browser_verified is True
    assert status.phone_quick_start_url is None
    assert status.active_evidence_kind == "verified_phone_proof"
    assert status.phone_proof_fresh is True
    assert status.phone_proof_age_seconds is not None
    assert status.installed_mode_detected is True
    assert status.effective_client_host == "10.0.0.55"
    assert status.client_host_source == "request-client"
    assert "[OK]" in rendered
    assert "Phone proof freshness: fresh" in rendered
    assert "Regenerate mobile readiness evidence" in rendered
    assert "npm --prefix ui run mobile:apk:wait-install-pair" in rendered


def test_phone_proof_watcher_reports_stale_phone_proof_age_and_expiry(tmp_path: Path) -> None:
    proof_dir = tmp_path / "evidence_runs" / "mobile_phone_proof" / "latest"
    proof_dir.mkdir(parents=True)
    generated_at = datetime.now(timezone.utc) - timedelta(hours=25)
    (proof_dir / "phone_runtime_proof.json").write_text(
        json.dumps(
            {
                "report_kind": "cas_forex_phone_runtime_proof",
                "generated_at": generated_at.isoformat(),
                "phone_browser_observed": True,
                "phone_browser_verified": True,
                "installed_mode_detected": True,
                "device_class": "phone",
                "effective_client_host": "10.0.0.55",
                "client_host_source": "request-client",
            }
        ),
        encoding="utf-8",
    )

    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "STALE"
    assert status.phone_browser_verified is False
    assert status.phone_browser_observed is False
    assert status.active_evidence_kind == "stale_phone_proof"
    assert status.phone_proof_fresh is False
    assert status.phone_proof_age_seconds is not None
    assert status.phone_proof_age_seconds >= 25 * 60 * 60
    assert status.phone_proof_expires_at is not None
    assert "expired" in status.summary
    assert "Phone proof freshness: expired" in rendered
    assert "Reopen Quick Start from the real phone" in rendered


def test_phone_proof_watcher_prints_lan_target_from_readiness(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://127.0.0.1:4173",
                "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
                "verification_commands": {
                    "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                    "mobile_readiness": "npm --prefix ui run mobile:readiness -- --web-base http://127.0.0.1:4173",
                },
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "checks": [],
                "remaining_external_gates": [],
            }
        ),
        encoding="utf-8",
    )

    status = phone_proof_watch_status(workspace_root=tmp_path)
    rendered = render_phone_proof_watch_status(status)

    assert status.status == "MISSING"
    assert status.phone_quick_start_url == "http://10.0.0.6:4173/?page=quick-start"
    assert status.tested_quick_start_url == "http://127.0.0.1:4173/?page=quick-start"
    assert status.phone_proof_watcher_command == "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    assert status.mobile_readiness_command == "npm --prefix ui run mobile:readiness -- --web-base http://127.0.0.1:4173"
    assert "Phone Quick Start URL: http://10.0.0.6:4173/?page=quick-start" in rendered
    assert "Tested Quick Start URL: http://127.0.0.1:4173/?page=quick-start" in rendered
    assert "Watch phone proof: npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing" in rendered
    assert "open http://10.0.0.6:4173/?page=quick-start from the phone" in rendered
