"""Tests for durable Android APK install/native pairing proof."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.mobile_apk_proof import (
    latest_android_apk_install_pairing_attempt,
    latest_android_apk_install_pairing_proof,
    record_android_apk_install_pairing_proof,
)


def _install_report(apk: Path, *, success: bool = True, dry_run: bool = False) -> dict:
    return {
        "success": success,
        "dry_run": dry_run,
        "adb_path": "C:/Android/adb.exe",
        "apk_path": str(apk),
        "selected_serial": "ZY22DEVICE",
        "command": ("adb", "-s", "ZY22DEVICE", "install", "-r", str(apk)),
        "message": "Debug APK installed successfully." if success else "Debug APK install failed.",
    }


def _launch_report(*, success: bool = True, dry_run: bool = False) -> dict:
    url = "casforex://pair?cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex"
    return {
        "success": success,
        "dry_run": dry_run,
        "adb_path": "C:/Android/adb.exe",
        "package_id": "com.casforex.cockpit",
        "selected_serial": "ZY22DEVICE",
        "pairing_url": url,
        "command": ("adb", "-s", "ZY22DEVICE", "shell", "am", "start", "-d", url),
        "message": "Native pairing deep link launched successfully." if success else "Native pairing deep link launch failed.",
    }


def test_record_android_apk_install_pairing_proof_promotes_real_success(tmp_path: Path) -> None:
    apk = tmp_path / "repo" / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk-v1")

    proof = record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report=_install_report(apk),
        native_pairing_launch=_launch_report(),
    )
    latest = latest_android_apk_install_pairing_proof(workspace_root=tmp_path)
    rendered = json.dumps(latest)

    assert proof["android_apk_install_pairing_verified"] is True
    assert proof["dry_run"] is False
    assert proof["selected_serial"] == "ZY22DEVICE"
    assert proof["apk_sha256"]
    assert latest is not None
    assert latest["android_apk_install_pairing_verified"] is True
    assert latest["is_fresh"] is True
    assert latest["age_seconds"] >= 0
    assert latest["expires_at"]
    assert "owner-authorized runtime gates" in latest["claim_boundary"]
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_dry_run_attempt_does_not_promote_apk_proof(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    apk.write_bytes(b"apk-v1")

    attempt = record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report=_install_report(apk, dry_run=True),
        native_pairing_launch=_launch_report(dry_run=True),
    )
    latest_attempt = latest_android_apk_install_pairing_attempt(workspace_root=tmp_path)
    latest_proof = latest_android_apk_install_pairing_proof(workspace_root=tmp_path)

    assert attempt["android_apk_install_pairing_verified"] is False
    assert attempt["dry_run"] is True
    assert latest_attempt is not None
    assert latest_attempt["android_apk_install_pairing_verified"] is False
    assert latest_attempt["age_seconds"] >= 0
    assert latest_attempt["expires_at"]
    assert latest_proof is None


def test_failed_install_attempt_is_recorded_without_promoting_proof(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    apk.write_bytes(b"apk-v1")

    attempt = record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report=_install_report(apk, success=False),
        native_pairing_launch={
            "success": False,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "package_id": "com.casforex.cockpit",
            "selected_serial": None,
            "pairing_url": None,
            "command": (),
            "message": "Native pairing launch was not attempted because APK install did not succeed.",
        },
    )
    latest_attempt = latest_android_apk_install_pairing_attempt(workspace_root=tmp_path)
    latest_proof = latest_android_apk_install_pairing_proof(workspace_root=tmp_path)

    assert attempt["android_apk_install_pairing_verified"] is False
    assert attempt["install_success"] is False
    assert attempt["native_pairing_success"] is False
    assert latest_attempt is not None
    assert latest_attempt["install_message"] == "Debug APK install failed."
    assert latest_attempt["is_fresh"] is True
    assert latest_proof is None
