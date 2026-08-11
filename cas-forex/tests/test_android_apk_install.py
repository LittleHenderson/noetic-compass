"""Tests for Android debug APK install helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from cas_forex.android_apk_install import (
    AndroidInstallReport,
    find_adb,
    install_android_debug_apk,
    launch_android_native_pairing_deep_link,
    parse_adb_devices,
    probe_android_devices,
    render_device_probe,
)


def _completed(args: Sequence[str], returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(args), returncode=returncode, stdout=stdout, stderr=stderr)


def test_parse_adb_devices_captures_ready_and_blocked_devices() -> None:
    output = """List of devices attached
ZY22DEVICE        device product:pixel model:Pixel_8 device:shiba
ZY22BLOCKED       unauthorized usb:1-2
emulator-5554     offline
"""

    devices = parse_adb_devices(output)

    assert [device.serial for device in devices] == ["ZY22DEVICE", "ZY22BLOCKED", "emulator-5554"]
    assert [device.state for device in devices] == ["device", "unauthorized", "offline"]
    assert devices[0].is_ready is True
    assert devices[1].is_ready is False


def test_find_adb_prefers_configured_android_sdk(tmp_path: Path) -> None:
    platform_tools = tmp_path / "sdk" / "platform-tools"
    platform_tools.mkdir(parents=True)
    adb_exe = platform_tools / "adb.exe"
    adb = platform_tools / "adb"
    adb_exe.write_text("", encoding="utf-8")
    adb.write_text("", encoding="utf-8")

    found = find_adb({"ANDROID_HOME": str(tmp_path / "sdk")})

    assert found is not None
    assert found.parent == platform_tools
    assert found.name in {"adb.exe", "adb"}


def test_install_android_debug_apk_dry_run_selects_single_ready_device(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    adb = tmp_path / "adb.exe"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk")
    adb.write_text("", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        calls.append(tuple(args))
        return _completed(args, 0, "List of devices attached\nZY22DEVICE device product:pixel\n")

    report = install_android_debug_apk(workspace_root=root, adb_path=adb, runner=runner, dry_run=True)

    assert report.success is True
    assert report.selected_serial == "ZY22DEVICE"
    assert report.command == (str(adb), "-s", "ZY22DEVICE", "install", "-r", str(apk))
    assert calls == [(str(adb), "devices", "-l")]


def test_install_android_debug_apk_reports_no_ready_device(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    adb = tmp_path / "adb.exe"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk")
    adb.write_text("", encoding="utf-8")

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        return _completed(args, 0, "List of devices attached\nZY22BLOCKED unauthorized usb:1-2\n")

    report = install_android_debug_apk(workspace_root=root, adb_path=adb, runner=runner)

    assert report.success is False
    assert "No ready Android device" in report.message
    assert report.devices[0].state == "unauthorized"


def test_install_android_debug_apk_waits_until_phone_is_authorized(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    adb = tmp_path / "adb.exe"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk")
    adb.write_text("", encoding="utf-8")
    calls: list[tuple[str, ...]] = []
    sleeps: list[float] = []

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        calls.append(tuple(args))
        if args[1:] == ("devices", "-l"):
            if len(calls) == 1:
                return _completed(args, 0, "List of devices attached\nZY22BLOCKED unauthorized usb:1-2\n")
            return _completed(args, 0, "List of devices attached\nZY22BLOCKED device product:pixel\n")
        return _completed(args, 0, "Success\n")

    report = install_android_debug_apk(
        workspace_root=root,
        adb_path=adb,
        runner=runner,
        wait_for_device=True,
        wait_timeout_seconds=5.0,
        wait_poll_seconds=0.25,
        sleeper=sleeps.append,
    )

    assert report.success is True
    assert report.selected_serial == "ZY22BLOCKED"
    assert calls[0] == (str(adb), "devices", "-l")
    assert calls[1] == (str(adb), "devices", "-l")
    assert calls[2] == (str(adb), "-s", "ZY22BLOCKED", "install", "-r", str(apk))
    assert sleeps == [0.25]


def test_install_android_debug_apk_wait_timeout_preserves_adb_detail(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    adb = tmp_path / "adb.exe"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk")
    adb.write_text("", encoding="utf-8")

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        return _completed(args, 0, "List of devices attached\nZY22BLOCKED unauthorized usb:1-2\n")

    report = install_android_debug_apk(
        workspace_root=root,
        adb_path=adb,
        runner=runner,
        wait_for_device=True,
        wait_timeout_seconds=0.0,
    )

    assert report.success is False
    assert "Timed out after 0s waiting for a ready Android device" in report.message
    assert "USB debugging is not authorized" in report.message
    assert report.devices[0].serial == "ZY22BLOCKED"


def test_probe_android_devices_includes_adb_error_detail(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    adb.write_text("", encoding="utf-8")

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        return _completed(args, 1, stderr="error: protocol fault (couldn't read status): No error\n")

    probe = probe_android_devices(adb_path=adb, runner=runner)
    rendered = render_device_probe(probe)

    assert probe.success is False
    assert "adb devices failed: error: protocol fault" in probe.message
    assert "stderr:" in rendered
    assert "protocol fault" in rendered


def test_probe_android_devices_explains_unauthorized_phone(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    adb.write_text("", encoding="utf-8")

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        return _completed(args, 0, "List of devices attached\nZY22BLOCKED unauthorized usb:1-2\n")

    probe = probe_android_devices(adb_path=adb, runner=runner)

    assert probe.success is True
    assert "USB debugging is not authorized" in probe.message
    assert "ZY22BLOCKED=unauthorized" in probe.message
    assert "approve the RSA debugging prompt" in probe.message


def test_install_android_debug_apk_runs_install_for_selected_device(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    adb = tmp_path / "adb.exe"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk")
    adb.write_text("", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        calls.append(tuple(args))
        if args[1:] == ("devices", "-l"):
            return _completed(args, 0, "List of devices attached\nZY22A device\nZY22B device\n")
        return _completed(args, 0, "Success\n")

    report = install_android_debug_apk(workspace_root=root, adb_path=adb, runner=runner, serial="ZY22B")

    assert report.success is True
    assert report.selected_serial == "ZY22B"
    assert calls[-1] == (str(adb), "-s", "ZY22B", "install", "-r", str(apk))
    assert "Success" in report.stdout


def test_launch_android_native_pairing_deep_link_uses_activity_manager_and_redacts_token(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    adb.write_text("", encoding="utf-8")
    pairing_url = (
        "casforex://pair?cas_owner_token=secret-token"
        "&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex&page=quick-start"
    )
    calls: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        calls.append(tuple(args))
        if args[1:] == ("devices", "-l"):
            return _completed(args, 0, "List of devices attached\nZY22DEVICE device product:pixel\n")
        return _completed(
            args,
            0,
            "Starting: Intent { act=android.intent.action.VIEW dat="
            f"{pairing_url} pkg=com.casforex.cockpit }}\nStatus: ok\nComplete\n",
        )

    report = launch_android_native_pairing_deep_link(adb_path=adb, pairing_url=pairing_url, runner=runner)

    assert report.success is True
    assert calls[-1] == (
        str(adb),
        "-s",
        "ZY22DEVICE",
        "shell",
        "am",
        "start",
        "-W",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        pairing_url,
        "com.casforex.cockpit",
    )
    assert "secret-token" not in " ".join(report.command)
    assert "secret-token" not in report.pairing_url
    assert "secret-token" not in report.stdout
    assert "cas_owner_token=REDACTED" in report.pairing_url
    assert "cas_owner_token=REDACTED" in report.stdout


def test_launch_android_native_pairing_deep_link_dry_run_skips_activity_manager(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    adb.write_text("", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        calls.append(tuple(args))
        return _completed(args, 0, "List of devices attached\nZY22DEVICE device\n")

    report = launch_android_native_pairing_deep_link(
        adb_path=adb,
        pairing_url="casforex://pair?cas_owner_token=secret-token&page=quick-start",
        runner=runner,
        dry_run=True,
    )

    assert report.success is True
    assert calls == [(str(adb), "devices", "-l")]
    assert report.command[:10] == (
        str(adb),
        "-s",
        "ZY22DEVICE",
        "shell",
        "am",
        "start",
        "-W",
        "-a",
        "android.intent.action.VIEW",
        "-d",
    )
    assert "secret-token" not in " ".join(report.command)


def test_launch_android_native_pairing_deep_link_detects_activity_manager_failure(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    adb.write_text("", encoding="utf-8")

    def runner(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        if args[1:] == ("devices", "-l"):
            return _completed(args, 0, "List of devices attached\nZY22DEVICE device\n")
        return _completed(args, 0, "Error: Activity not started, unable to resolve Intent\n")

    report = launch_android_native_pairing_deep_link(
        adb_path=adb,
        pairing_url="casforex://pair?cas_owner_token=secret-token&page=quick-start",
        runner=runner,
    )

    assert report.success is False
    assert "launch failed" in report.message


def test_install_pair_script_records_attempt_when_install_fails(monkeypatch) -> None:
    from scripts import install_android_debug_apk as install_script

    captured: dict[str, object] = {}

    def fake_install_android_debug_apk(**kwargs) -> AndroidInstallReport:  # noqa: ANN003, ARG001
        return AndroidInstallReport(
            success=False,
            dry_run=False,
            adb_path="C:/Android/adb.exe",
            apk_path="C:/repo/app-debug.apk",
            devices=(),
            selected_serial=None,
            command=(),
            returncode=None,
            stdout="",
            stderr="",
            message="No ready Android device is attached.",
        )

    def fake_record_android_apk_install_pairing_proof(**kwargs) -> dict:  # noqa: ANN003
        captured.update(kwargs)
        return {"android_apk_install_pairing_verified": False}

    monkeypatch.setattr(install_script, "install_android_debug_apk", fake_install_android_debug_apk)
    monkeypatch.setattr(install_script, "record_android_apk_install_pairing_proof", fake_record_android_apk_install_pairing_proof)

    rc = install_script.main(["--launch-native-pairing", "--exit-code-on-failure", "--json"])

    assert rc == 1
    launch_payload = captured["native_pairing_launch"]
    assert isinstance(launch_payload, dict)
    assert launch_payload["success"] is False
    assert launch_payload["message"] == "Native pairing launch was not attempted because APK install did not succeed."
