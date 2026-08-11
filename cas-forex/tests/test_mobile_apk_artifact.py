from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from api.routes import mobile as mobile_route
from api.server import app
from cas_forex.mobile_apk_artifact import (
    android_release_signing_status,
    debug_apk_artifact_metadata,
    release_apk_artifact_metadata,
    setup_android_release_signing,
)


def test_debug_apk_artifact_metadata_hashes_existing_apk(tmp_path: Path) -> None:
    apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"cas-forex-apk")

    metadata = debug_apk_artifact_metadata(workspace_root=tmp_path)

    assert metadata["report_kind"] == "cas_forex_android_debug_apk_artifact"
    assert metadata["exists"] is True
    assert metadata["transfer_ready"] is True
    assert metadata["size_bytes"] == len(b"cas-forex-apk")
    assert metadata["sha256"] == hashlib.sha256(b"cas-forex-apk").hexdigest()
    assert metadata["download_url_path"] == "/api/forex/mobile/apk/debug/download"
    assert metadata["wait_install_pair_command"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert "does not prove the APK was installed" in metadata["claim_boundary"]


def test_debug_apk_artifact_metadata_reports_missing_apk(tmp_path: Path) -> None:
    metadata = debug_apk_artifact_metadata(workspace_root=tmp_path)

    assert metadata["exists"] is False
    assert metadata["transfer_ready"] is False
    assert metadata["size_bytes"] is None
    assert metadata["sha256"] is None
    assert "missing" in metadata["summary"].lower()


def test_android_release_signing_status_reports_missing_config(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    status = android_release_signing_status(workspace_root=tmp_path)

    assert status["report_kind"] == "cas_forex_android_release_signing_status"
    assert status["ready"] is False
    assert status["status"] == "missing_config"
    assert status["inputs_present"]["storeFile"] is False
    assert status["store_file_exists"] is False
    assert status["release_apk_exists"] is False
    assert status["build_command"] == "npm --prefix ui run mobile:apk:release"
    assert "does not expose keystore secrets" in status["claim_boundary"]


def test_android_release_signing_status_hashes_release_apk_without_leaking_secrets(tmp_path: Path) -> None:
    android = tmp_path / "ui" / "android"
    android.mkdir(parents=True)
    (android / "keystore.properties").write_text(
        "\n".join(
            [
                "storeFile=cas-forex-release.jks",
                "storePassword=top-secret-store",
                "keyAlias=cas-forex",
                "keyPassword=top-secret-key",
            ]
        ),
        encoding="utf-8",
    )
    (android / "cas-forex-release.jks").write_bytes(b"fake-keystore")
    release_apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
    release_apk.parent.mkdir(parents=True)
    release_apk.write_bytes(b"signed-release-apk")

    status = android_release_signing_status(workspace_root=tmp_path)
    rendered = json.dumps(status)

    assert status["ready"] is True
    assert status["status"] == "ready"
    assert status["store_file_configured"] is True
    assert status["store_file_exists"] is True
    assert status["release_apk_exists"] is True
    assert status["release_apk_size_bytes"] == len(b"signed-release-apk")
    assert status["release_apk_sha256"] == hashlib.sha256(b"signed-release-apk").hexdigest()
    assert status["input_sources"]["storeFile"] == "keystore.properties"
    assert "top-secret" not in rendered


def test_release_apk_artifact_metadata_reports_signed_release(tmp_path: Path) -> None:
    android = tmp_path / "ui" / "android"
    android.mkdir(parents=True)
    (android / "keystore.properties").write_text(
        "\n".join(
            [
                "storeFile=cas-forex-release.jks",
                "storePassword=store-secret",
                "keyAlias=cas-forex",
                "keyPassword=key-secret",
            ]
        ),
        encoding="utf-8",
    )
    (android / "cas-forex-release.jks").write_bytes(b"fake-keystore")
    release_apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
    release_apk.parent.mkdir(parents=True)
    release_apk.write_bytes(b"signed-release-apk")

    metadata = release_apk_artifact_metadata(workspace_root=tmp_path)
    rendered = json.dumps(metadata)

    assert metadata["report_kind"] == "cas_forex_android_release_apk_artifact"
    assert metadata["artifact_id"] == "android_release_apk"
    assert metadata["exists"] is True
    assert metadata["transfer_ready"] is True
    assert metadata["download_url_path"] == "/api/forex/mobile/apk/release/download"
    assert metadata["filename"] == "cas-forex-release.apk"
    assert metadata["sha256"] == hashlib.sha256(b"signed-release-apk").hexdigest()
    assert "store-secret" not in rendered
    assert "key-secret" not in rendered


def test_setup_android_release_signing_creates_local_files_without_leaking_secrets(tmp_path: Path) -> None:
    def fake_keytool(command, cwd, text, capture_output, check):  # noqa: ARG001
        keystore_path = Path(command[command.index("-keystore") + 1])
        keystore_path.parent.mkdir(parents=True, exist_ok=True)
        keystore_path.write_bytes(b"fake-release-keystore")
        return subprocess.CompletedProcess(command, 0, stdout="created", stderr="")

    report = setup_android_release_signing(
        workspace_root=tmp_path,
        keytool_path="keytool",
        run_command=fake_keytool,
    )
    rendered = json.dumps(report)
    properties_path = tmp_path / "ui" / "android" / "keystore.properties"
    keystore_path = tmp_path / "ui" / "android" / "cas-forex-release.jks"
    properties = properties_path.read_text(encoding="utf-8")

    assert report["status"] == "created"
    assert report["created"] is True
    assert report["store_file_exists"] is True
    assert report["inputs_present"] == {
        "storeFile": True,
        "storePassword": True,
        "keyAlias": True,
        "keyPassword": True,
    }
    assert properties_path.exists()
    assert keystore_path.exists()
    assert "storePassword=" in properties
    assert "keyPassword=" in properties
    secrets = [
        line.split("=", 1)[1].strip()
        for line in properties.splitlines()
        if line.startswith(("storePassword=", "keyPassword="))
    ]
    assert secrets
    assert all(secret not in rendered for secret in secrets)
    assert "fake-release-keystore" not in rendered


def test_setup_android_release_signing_is_idempotent_without_force(tmp_path: Path) -> None:
    android = tmp_path / "ui" / "android"
    android.mkdir(parents=True)
    (android / "keystore.properties").write_text("storeFile=cas-forex-release.jks\n", encoding="utf-8")
    (android / "cas-forex-release.jks").write_bytes(b"existing")

    def unexpected_keytool(*_args, **_kwargs):
        raise AssertionError("keytool should not run when signing files already exist")

    report = setup_android_release_signing(
        workspace_root=tmp_path,
        keytool_path="keytool",
        run_command=unexpected_keytool,
    )

    assert report["status"] == "already_exists"
    assert report["created"] is False
    assert sorted(report["existing_targets"]) == [
        str(Path("ui") / "android" / "cas-forex-release.jks"),
        str(Path("ui") / "android" / "keystore.properties"),
    ]


def test_setup_android_release_signing_reports_missing_keytool(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("cas_forex.mobile_apk_artifact.shutil.which", lambda _name: None)

    report = setup_android_release_signing(workspace_root=tmp_path)

    assert report["status"] == "keytool_missing"
    assert report["created"] is False
    assert "keytool" in report["summary"].lower()


def test_mobile_debug_apk_metadata_and_download_routes(monkeypatch, tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    apk.write_bytes(b"downloadable-apk")
    digest = hashlib.sha256(b"downloadable-apk").hexdigest()

    def fake_metadata(**_kwargs):
        return {
            "report_kind": "cas_forex_android_debug_apk_artifact",
            "artifact_id": "android_debug_apk",
            "path": str(apk),
            "filename": "cas-forex-debug.apk",
            "content_type": "application/vnd.android.package-archive",
            "exists": True,
            "transfer_ready": True,
            "size_bytes": apk.stat().st_size,
            "sha256": digest,
            "modified_at": "2026-07-05T00:00:00+00:00",
            "download_url_path": "/api/forex/mobile/apk/debug/download",
            "build_command": "npm --prefix ui run mobile:apk:debug",
            "install_command": "npm --prefix ui run mobile:apk:install",
            "install_pair_command": "npm --prefix ui run mobile:apk:install-pair",
            "summary": "Android debug APK is present and ready for authenticated transfer.",
            "claim_boundary": "download does not prove install",
        }

    monkeypatch.setattr(mobile_route, "debug_apk_artifact_metadata", fake_metadata)
    client = TestClient(app)

    metadata_response = client.get("/api/forex/mobile/apk/debug/metadata")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["exists"] is True
    assert metadata["sha256"] == digest

    download_response = client.get("/api/forex/mobile/apk/debug/download")
    assert download_response.status_code == 200
    assert download_response.content == b"downloadable-apk"
    assert download_response.headers["x-cas-apk-sha256"] == digest
    assert "cas-forex-debug.apk" in download_response.headers["content-disposition"]


def test_mobile_release_apk_metadata_and_download_routes(monkeypatch, tmp_path: Path) -> None:
    apk = tmp_path / "app-release.apk"
    apk.write_bytes(b"downloadable-release-apk")
    digest = hashlib.sha256(b"downloadable-release-apk").hexdigest()

    def fake_metadata(**_kwargs):
        return {
            "report_kind": "cas_forex_android_release_apk_artifact",
            "artifact_id": "android_release_apk",
            "path": str(apk),
            "filename": "cas-forex-release.apk",
            "content_type": "application/vnd.android.package-archive",
            "exists": True,
            "transfer_ready": True,
            "size_bytes": apk.stat().st_size,
            "sha256": digest,
            "modified_at": "2026-07-05T00:00:00+00:00",
            "download_url_path": "/api/forex/mobile/apk/release/download",
            "build_command": "npm --prefix ui run mobile:apk:release",
            "setup_command": "npm --prefix ui run mobile:apk:setup-release-signing",
            "setup_json_command": "npm --prefix ui run mobile:apk:setup-release-signing -- --json",
            "signing_ready": True,
            "signing_status": "ready",
            "summary": "Android signed release APK is present and ready for authenticated transfer.",
            "claim_boundary": "download does not prove install",
        }

    monkeypatch.setattr(mobile_route, "release_apk_artifact_metadata", fake_metadata)
    client = TestClient(app)

    metadata_response = client.get("/api/forex/mobile/apk/release/metadata")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["exists"] is True
    assert metadata["sha256"] == digest

    download_response = client.get("/api/forex/mobile/apk/release/download")
    assert download_response.status_code == 200
    assert download_response.content == b"downloadable-release-apk"
    assert download_response.headers["x-cas-apk-sha256"] == digest
    assert "cas-forex-release.apk" in download_response.headers["content-disposition"]
