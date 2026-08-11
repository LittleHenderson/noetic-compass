"""Android APK install helpers for the CAS Forex phone build."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence


DEFAULT_APK_PATH = Path("ui") / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
DEFAULT_ANDROID_PACKAGE_ID = "com.casforex.cockpit"
Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class AndroidDevice:
    serial: str
    state: str
    detail: str = ""

    @property
    def is_ready(self) -> bool:
        return self.state == "device"


@dataclass(frozen=True)
class AndroidDeviceProbe:
    success: bool
    adb_path: str | None
    devices: tuple[AndroidDevice, ...]
    returncode: int | None
    stdout: str
    stderr: str
    message: str


@dataclass(frozen=True)
class AndroidInstallReport:
    success: bool
    dry_run: bool
    adb_path: str | None
    apk_path: str
    devices: tuple[AndroidDevice, ...]
    selected_serial: str | None
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    message: str


@dataclass(frozen=True)
class AndroidDeepLinkLaunchReport:
    success: bool
    dry_run: bool
    adb_path: str | None
    package_id: str
    devices: tuple[AndroidDevice, ...]
    selected_serial: str | None
    pairing_url: str | None
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    message: str


def adb_candidates(env: dict[str, str] | None = None) -> tuple[Path, ...]:
    """Return likely adb executable paths, ordered by owner intent."""
    env = dict(os.environ if env is None else env)
    executable_names = ("adb.exe", "adb") if os.name == "nt" else ("adb", "adb.exe")
    candidates: list[Path] = []

    explicit_adb = env.get("CAS_FOREX_ADB")
    if explicit_adb:
        candidates.append(Path(explicit_adb))

    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk_root = env.get(key)
        if sdk_root:
            candidates.extend(Path(sdk_root) / "platform-tools" / name for name in executable_names)

    local_app_data = env.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / name for name in executable_names)

    user_profile = env.get("USERPROFILE")
    if user_profile:
        candidates.extend(Path(user_profile) / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / name for name in executable_names)

    try:
        home = Path.home()
    except RuntimeError:
        home = None
    if home is not None:
        candidates.extend(home / "Android" / "Sdk" / "platform-tools" / name for name in executable_names)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        marker = str(candidate).lower()
        if marker not in seen:
            unique.append(candidate)
            seen.add(marker)
    return tuple(unique)


def find_adb(env: dict[str, str] | None = None) -> Path | None:
    for candidate in adb_candidates(env):
        if candidate.exists():
            return candidate
    from_path = shutil.which("adb")
    return Path(from_path) if from_path else None


def parse_adb_devices(output: str) -> tuple[AndroidDevice, ...]:
    devices: list[AndroidDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        devices.append(AndroidDevice(serial=parts[0], state=parts[1], detail=" ".join(parts[2:])))
    return tuple(devices)


def probe_android_devices(
    *,
    adb_path: str | Path | None = None,
    runner: Runner | None = None,
    timeout_seconds: float = 10.0,
) -> AndroidDeviceProbe:
    resolved_adb = Path(adb_path) if adb_path is not None else find_adb()
    if resolved_adb is None:
        return AndroidDeviceProbe(
            success=False,
            adb_path=None,
            devices=(),
            returncode=None,
            stdout="",
            stderr="",
            message="adb was not found. Install Android SDK platform-tools or set CAS_FOREX_ADB.",
        )

    run = runner or _run_command
    completed = run((str(resolved_adb), "devices", "-l"), timeout_seconds)
    devices = parse_adb_devices(completed.stdout)
    success = completed.returncode == 0
    if not success:
        message = _adb_failure_message(completed)
    elif any(device.is_ready for device in devices):
        message = "Android device ready for install."
    elif devices:
        message = _not_ready_device_message(devices)
    else:
        message = "No Android devices are attached."
    return AndroidDeviceProbe(
        success=success,
        adb_path=str(resolved_adb),
        devices=devices,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        message=message,
    )


def wait_for_ready_android_device(
    *,
    serial: str | None = None,
    adb_path: str | Path | None = None,
    runner: Runner | None = None,
    timeout_seconds: float = 600.0,
    poll_seconds: float = 2.0,
    probe_timeout_seconds: float = 10.0,
    sleeper: Sleeper | None = None,
) -> AndroidDeviceProbe:
    """Poll adb until a selectable ready device appears or the wait expires."""
    wait_timeout = max(0.0, float(timeout_seconds))
    poll_interval = max(0.1, float(poll_seconds))
    deadline = time.monotonic() + wait_timeout
    sleep = sleeper or time.sleep
    attempts = 0
    last_probe: AndroidDeviceProbe | None = None

    while True:
        attempts += 1
        probe = probe_android_devices(
            adb_path=adb_path,
            runner=runner,
            timeout_seconds=probe_timeout_seconds,
        )
        last_probe = probe
        if _probe_is_terminal_for_wait(probe, serial):
            return _probe_with_wait_message(probe, attempts=attempts, timeout_seconds=None)
        if wait_timeout <= 0:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sleep(min(poll_interval, remaining))

    assert last_probe is not None
    return _probe_with_wait_message(last_probe, attempts=attempts, timeout_seconds=wait_timeout)


def install_android_debug_apk(
    *,
    workspace_root: str | Path = ".",
    apk_path: str | Path = DEFAULT_APK_PATH,
    serial: str | None = None,
    adb_path: str | Path | None = None,
    dry_run: bool = False,
    runner: Runner | None = None,
    timeout_seconds: float = 120.0,
    wait_for_device: bool = False,
    wait_timeout_seconds: float = 600.0,
    wait_poll_seconds: float = 2.0,
    sleeper: Sleeper | None = None,
) -> AndroidInstallReport:
    root = Path(workspace_root).resolve()
    resolved_apk = _resolve_under_root(root, apk_path)
    if wait_for_device:
        probe = wait_for_ready_android_device(
            serial=serial,
            adb_path=adb_path,
            runner=runner,
            timeout_seconds=wait_timeout_seconds,
            poll_seconds=wait_poll_seconds,
            probe_timeout_seconds=min(timeout_seconds, 10.0),
            sleeper=sleeper,
        )
    else:
        probe = probe_android_devices(adb_path=adb_path, runner=runner, timeout_seconds=min(timeout_seconds, 10.0))
    command: tuple[str, ...] = ()

    if probe.adb_path is None:
        return _install_report(False, dry_run, probe, resolved_apk, None, command, None, "", "", probe.message)
    if not resolved_apk.exists():
        return _install_report(
            False,
            dry_run,
            probe,
            resolved_apk,
            None,
            command,
            None,
            "",
            "",
            f"APK not found: {resolved_apk}",
        )
    if not probe.success:
        return _install_report(False, dry_run, probe, resolved_apk, None, command, probe.returncode, probe.stdout, probe.stderr, probe.message)

    ready_devices = [device for device in probe.devices if device.is_ready]
    selected = _select_device(ready_devices, serial)
    if selected is None:
        if serial:
            message = f"Requested Android device is not ready or attached: {serial}"
        elif not ready_devices:
            message = (
                probe.message
                if wait_for_device
                else "No ready Android device is attached. Plug in the phone, enable USB debugging, and approve the RSA prompt."
            )
        else:
            message = "Multiple Android devices are attached. Pass --serial to choose one."
        return _install_report(False, dry_run, probe, resolved_apk, None, command, None, "", "", message)

    command = (probe.adb_path, "-s", selected.serial, "install", "-r", str(resolved_apk))
    if dry_run:
        return _install_report(
            True,
            dry_run,
            probe,
            resolved_apk,
            selected.serial,
            command,
            None,
            "",
            "",
            "Dry run passed. The debug APK is ready to install on the selected Android device.",
        )

    run = runner or _run_command
    completed = run(command, timeout_seconds)
    success = completed.returncode == 0
    message = "Debug APK installed successfully." if success else "Debug APK install failed."
    return _install_report(
        success,
        dry_run,
        probe,
        resolved_apk,
        selected.serial,
        command,
        completed.returncode,
        completed.stdout,
        completed.stderr,
        message,
    )


def default_native_pairing_url() -> str | None:
    from cas_forex.owner_auth import get_or_create_token, phone_native_pairing_urls

    urls = phone_native_pairing_urls(get_or_create_token())
    return urls[0] if urls else None


def launch_android_native_pairing_deep_link(
    *,
    pairing_url: str | None = None,
    serial: str | None = None,
    adb_path: str | Path | None = None,
    package_id: str = DEFAULT_ANDROID_PACKAGE_ID,
    dry_run: bool = False,
    runner: Runner | None = None,
    timeout_seconds: float = 30.0,
    wait_for_device: bool = False,
    wait_timeout_seconds: float = 600.0,
    wait_poll_seconds: float = 2.0,
    sleeper: Sleeper | None = None,
) -> AndroidDeepLinkLaunchReport:
    if wait_for_device:
        probe = wait_for_ready_android_device(
            serial=serial,
            adb_path=adb_path,
            runner=runner,
            timeout_seconds=wait_timeout_seconds,
            poll_seconds=wait_poll_seconds,
            probe_timeout_seconds=min(timeout_seconds, 10.0),
            sleeper=sleeper,
        )
    else:
        probe = probe_android_devices(adb_path=adb_path, runner=runner, timeout_seconds=min(timeout_seconds, 10.0))
    command: tuple[str, ...] = ()

    if probe.adb_path is None:
        return _launch_report(False, dry_run, probe, package_id, None, None, command, None, "", "", probe.message)
    if not probe.success:
        return _launch_report(False, dry_run, probe, package_id, None, None, command, probe.returncode, probe.stdout, probe.stderr, probe.message)

    ready_devices = [device for device in probe.devices if device.is_ready]
    selected = _select_device(ready_devices, serial)
    if selected is None:
        if serial:
            message = f"Requested Android device is not ready or attached: {serial}"
        elif not ready_devices:
            message = (
                probe.message
                if wait_for_device
                else "No ready Android device is attached. Plug in the phone, enable USB debugging, and approve the RSA prompt."
            )
        else:
            message = "Multiple Android devices are attached. Pass --serial to choose one."
        return _launch_report(False, dry_run, probe, package_id, None, None, command, None, "", "", message)

    resolved_url = pairing_url or default_native_pairing_url()
    if not resolved_url:
        return _launch_report(
            False,
            dry_run,
            probe,
            package_id,
            selected.serial,
            None,
            command,
            None,
            "",
            "",
            "No native pairing URL could be generated.",
        )

    launch_command = (
        probe.adb_path,
        "-s",
        selected.serial,
        "shell",
        "am",
        "start",
        "-W",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        resolved_url,
        package_id,
    )
    redacted_command = _redact_args(launch_command)
    if dry_run:
        return _launch_report(
            True,
            dry_run,
            probe,
            package_id,
            selected.serial,
            _redact_pairing_url(resolved_url),
            redacted_command,
            None,
            "",
            "",
            "Dry run passed. Native pairing deep link is ready to launch on the selected Android device.",
        )

    run = runner or _run_command
    completed = run(launch_command, timeout_seconds)
    success = _activity_launch_succeeded(completed)
    message = (
        "Native pairing deep link launched successfully."
        if success
        else "Native pairing deep link launch failed."
    )
    return _launch_report(
        success,
        dry_run,
        probe,
        package_id,
        selected.serial,
        _redact_pairing_url(resolved_url),
        redacted_command,
        completed.returncode,
        _redact_pairing_url(completed.stdout),
        _redact_pairing_url(completed.stderr),
        message,
    )


def install_report_to_dict(report: AndroidInstallReport) -> dict[str, object]:
    out = asdict(report)
    out["devices"] = [asdict(device) for device in report.devices]
    return out


def deep_link_launch_report_to_dict(report: AndroidDeepLinkLaunchReport) -> dict[str, object]:
    out = asdict(report)
    out["devices"] = [asdict(device) for device in report.devices]
    return out


def device_probe_to_dict(probe: AndroidDeviceProbe) -> dict[str, object]:
    out = asdict(probe)
    out["devices"] = [asdict(device) for device in probe.devices]
    return out


def render_device_probe(probe: AndroidDeviceProbe) -> str:
    lines = ["CAS Forex Android device probe", "", probe.message]
    lines.append(f"adb: {probe.adb_path or 'not found'}")
    if probe.devices:
        lines.append("")
        lines.append("Devices:")
        for device in probe.devices:
            suffix = f" {device.detail}" if device.detail else ""
            lines.append(f"- {device.serial}: {device.state}{suffix}")
    if probe.stdout.strip():
        lines.append("")
        lines.append("stdout:")
        lines.append(probe.stdout.strip())
    if probe.stderr.strip():
        lines.append("")
        lines.append("stderr:")
        lines.append(probe.stderr.strip())
    return "\n".join(lines)


def render_install_report(report: AndroidInstallReport) -> str:
    lines = ["CAS Forex Android APK install", "", report.message]
    lines.append(f"APK: {report.apk_path}")
    lines.append(f"adb: {report.adb_path or 'not found'}")
    if report.selected_serial:
        lines.append(f"device: {report.selected_serial}")
    if report.command:
        lines.append(f"command: {' '.join(report.command)}")
    if report.devices:
        lines.append("")
        lines.append("Devices:")
        for device in report.devices:
            suffix = f" {device.detail}" if device.detail else ""
            lines.append(f"- {device.serial}: {device.state}{suffix}")
    if report.stdout.strip():
        lines.append("")
        lines.append("stdout:")
        lines.append(report.stdout.strip())
    if report.stderr.strip():
        lines.append("")
        lines.append("stderr:")
        lines.append(report.stderr.strip())
    return "\n".join(lines)


def render_deep_link_launch_report(report: AndroidDeepLinkLaunchReport) -> str:
    lines = ["CAS Forex Android native pairing launch", "", report.message]
    lines.append(f"adb: {report.adb_path or 'not found'}")
    lines.append(f"package: {report.package_id}")
    if report.selected_serial:
        lines.append(f"device: {report.selected_serial}")
    if report.pairing_url:
        lines.append(f"pairing_url: {report.pairing_url}")
    if report.command:
        lines.append(f"command: {' '.join(report.command)}")
    if report.devices:
        lines.append("")
        lines.append("Devices:")
        for device in report.devices:
            suffix = f" {device.detail}" if device.detail else ""
            lines.append(f"- {device.serial}: {device.state}{suffix}")
    if report.stdout.strip():
        lines.append("")
        lines.append("stdout:")
        lines.append(report.stdout.strip())
    if report.stderr.strip():
        lines.append("")
        lines.append("stderr:")
        lines.append(report.stderr.strip())
    return "\n".join(lines)


def install_report_to_json(report: AndroidInstallReport) -> str:
    return json.dumps(install_report_to_dict(report), indent=2)


def deep_link_launch_report_to_json(report: AndroidDeepLinkLaunchReport) -> str:
    return json.dumps(deep_link_launch_report_to_dict(report), indent=2)


def device_probe_to_json(probe: AndroidDeviceProbe) -> str:
    return json.dumps(device_probe_to_dict(probe), indent=2)


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _select_device(devices: Sequence[AndroidDevice], serial: str | None) -> AndroidDevice | None:
    if serial:
        return next((device for device in devices if device.serial == serial), None)
    if len(devices) == 1:
        return devices[0]
    return None


def _probe_is_terminal_for_wait(probe: AndroidDeviceProbe, serial: str | None) -> bool:
    if probe.adb_path is None or not probe.success:
        return True
    ready_devices = [device for device in probe.devices if device.is_ready]
    if serial:
        return any(device.serial == serial for device in ready_devices)
    return bool(ready_devices)


def _probe_with_wait_message(
    probe: AndroidDeviceProbe,
    *,
    attempts: int,
    timeout_seconds: float | None,
) -> AndroidDeviceProbe:
    if attempts <= 1 and timeout_seconds is None:
        return probe
    if timeout_seconds is None:
        prefix = f"Android device became ready after {attempts} adb probe(s)."
    else:
        prefix = (
            f"Timed out after {_format_seconds(timeout_seconds)} waiting for a ready Android device "
            f"({attempts} adb probe(s))."
        )
    return AndroidDeviceProbe(
        success=probe.success,
        adb_path=probe.adb_path,
        devices=probe.devices,
        returncode=probe.returncode,
        stdout=probe.stdout,
        stderr=probe.stderr,
        message=f"{prefix} {probe.message}",
    )


def _format_seconds(value: float) -> str:
    if value.is_integer():
        return f"{int(value)}s"
    return f"{value:.1f}s"


def _adb_failure_message(completed: subprocess.CompletedProcess[str]) -> str:
    detail = _first_nonempty_line(completed.stderr) or _first_nonempty_line(completed.stdout)
    if detail:
        return f"adb devices failed: {detail}"
    return f"adb devices failed with exit code {completed.returncode}."


def _not_ready_device_message(devices: Sequence[AndroidDevice]) -> str:
    states = ", ".join(
        f"{device.serial}={device.state}"
        for device in devices[:3]
    )
    suffix = f" ({states})" if states else ""
    if any(device.state == "unauthorized" for device in devices):
        return (
            "Android device found, but USB debugging is not authorized"
            f"{suffix}. Unlock the phone and approve the RSA debugging prompt."
        )
    if any(device.state == "offline" for device in devices):
        return (
            "Android device found, but adb reports it offline"
            f"{suffix}. Reconnect USB or restart adb, then approve debugging on the phone."
        )
    return f"Android device found, but it is not ready{suffix}. Check authorization or connection state."


def _first_nonempty_line(value: str) -> str | None:
    for line in value.splitlines():
        line = line.strip()
        if line:
            return line[:240]
    return None


def _install_report(
    success: bool,
    dry_run: bool,
    probe: AndroidDeviceProbe,
    apk_path: Path,
    selected_serial: str | None,
    command: tuple[str, ...],
    returncode: int | None,
    stdout: str,
    stderr: str,
    message: str,
) -> AndroidInstallReport:
    return AndroidInstallReport(
        success=success,
        dry_run=dry_run,
        adb_path=probe.adb_path,
        apk_path=str(apk_path),
        devices=probe.devices,
        selected_serial=selected_serial,
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        message=message,
    )


def _launch_report(
    success: bool,
    dry_run: bool,
    probe: AndroidDeviceProbe,
    package_id: str,
    selected_serial: str | None,
    pairing_url: str | None,
    command: tuple[str, ...],
    returncode: int | None,
    stdout: str,
    stderr: str,
    message: str,
) -> AndroidDeepLinkLaunchReport:
    return AndroidDeepLinkLaunchReport(
        success=success,
        dry_run=dry_run,
        adb_path=probe.adb_path,
        package_id=package_id,
        devices=probe.devices,
        selected_serial=selected_serial,
        pairing_url=pairing_url,
        command=command,
        returncode=returncode,
        stdout=_redact_pairing_url(stdout),
        stderr=_redact_pairing_url(stderr),
        message=message,
    )


def _activity_launch_succeeded(completed: subprocess.CompletedProcess[str]) -> bool:
    combined = f"{completed.stdout}\n{completed.stderr}".lower()
    if completed.returncode != 0:
        return False
    failure_markers = (
        "error:",
        "exception",
        "unable to resolve",
        "activity not started",
        "security exception",
        "permission denial",
    )
    return not any(marker in combined for marker in failure_markers)


def _redact_args(args: Sequence[str]) -> tuple[str, ...]:
    return tuple(_redact_pairing_url(arg) for arg in args)


def _redact_pairing_url(value: str) -> str:
    if not value:
        return value
    import re
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    value = re.sub(r"(cas_owner_token=)[^&#\s}]+", r"\1REDACTED", value)
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if not parts.scheme:
        return value
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not query:
        return value
    redacted = [
        (key, "REDACTED" if key == "cas_owner_token" else val)
        for key, val in query
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))


def _run_command(args: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
