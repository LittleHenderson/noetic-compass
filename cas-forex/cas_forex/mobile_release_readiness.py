"""Consolidated web/PWA/APK readiness checks for CAS Forex mobile release."""

from __future__ import annotations

import json
import ipaddress
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

from cas_forex.android_apk_install import (
    AndroidDeepLinkLaunchReport,
    AndroidDeviceProbe,
    deep_link_launch_report_to_dict,
    device_probe_to_dict,
    launch_android_native_pairing_deep_link,
    probe_android_devices,
)
from cas_forex.docker_desktop_install import (
    elevated_install_command_string,
    latest_docker_desktop_install_attempt,
)
from cas_forex.mobile_phone_proof import (
    latest_apk_runtime_observation,
    latest_phone_runtime_observation,
    latest_phone_runtime_proof,
)
from cas_forex.mobile_apk_proof import (
    latest_android_apk_install_pairing_attempt,
    latest_android_apk_install_pairing_proof,
)
from cas_forex.mobile_apk_artifact import android_release_signing_status, debug_apk_artifact_metadata
from cas_forex.web_phone_smoke import (
    HttpSmokeResponse,
    Transport,
    report_to_dict,
    run_web_phone_smoke,
)

_PROBE_MAX_ATTEMPTS = 2
_RETRYABLE_STATUS_CODES = {502, 503, 504}


@dataclass(frozen=True)
class MobileReadinessCheck:
    check_id: str
    status: str
    success: bool
    detail: str
    evidence: dict[str, Any]
    elapsed_ms: float = 0.0
    attempts: int = 1


@dataclass(frozen=True)
class MobileReleaseReadinessReport:
    generated_at: str
    web_base: str
    phone_quick_start_url: str | None
    verification_commands: dict[str, str]
    next_verification_actions: tuple[dict[str, Any], ...]
    package_ready_for_phone_install: bool
    physical_phone_verified: bool
    docker_available: bool
    checks: tuple[MobileReadinessCheck, ...]
    smoke_report: dict[str, Any]
    device_probe: dict[str, Any] | None
    native_pairing_launch: dict[str, Any] | None
    summary: str
    remaining_external_gates: tuple[str, ...]
    phone_proof_checked: bool = True
    phone_browser_observed: bool = False
    phone_browser_verified: bool = False
    phone_proof_fresh: bool = False
    phone_proof_age_seconds: int | None = None
    phone_proof_expires_at: str | None = None
    phone_proof_max_age_hours: int | None = None
    phone_observation_fresh: bool = False
    phone_observation_age_seconds: int | None = None
    phone_observation_expires_at: str | None = None
    phone_observation_max_age_hours: int | None = None
    phone_observation: dict[str, Any] | None = None
    phone_proof: dict[str, Any] | None = None
    apk_runtime_observation: dict[str, Any] | None = None
    apk_runtime_observed: bool = False
    apk_runtime_verified: bool = False
    apk_runtime_fresh: bool = False
    apk_runtime_age_seconds: int | None = None
    apk_runtime_expires_at: str | None = None
    apk_install_pairing_proof: dict[str, Any] | None = None
    apk_install_pairing_verified: bool = False
    apk_install_pairing_generated_at: str | None = None
    apk_install_pairing_selected_serial: str | None = None
    apk_install_pairing_package_id: str | None = None
    apk_install_pairing_apk_sha256: str | None = None
    apk_install_pairing_current_apk_sha256: str | None = None
    apk_install_pairing_apk_matches_current_artifact: bool | None = None
    apk_install_pairing_attempt: dict[str, Any] | None = None
    apk_install_pairing_attempt_recorded: bool = False
    apk_install_pairing_attempt_status: str | None = None
    apk_install_pairing_attempt_fresh: bool = False
    apk_install_pairing_attempt_age_seconds: int | None = None
    apk_install_pairing_attempt_expires_at: str | None = None
    apk_install_pairing_attempt_generated_at: str | None = None
    apk_install_pairing_attempt_install_success: bool = False
    apk_install_pairing_attempt_native_pairing_success: bool = False
    apk_install_pairing_attempt_dry_run: bool = False
    apk_install_pairing_attempt_selected_serial: str | None = None
    apk_install_pairing_attempt_package_id: str | None = None
    apk_install_pairing_attempt_apk_sha256: str | None = None
    apk_install_pairing_attempt_current_apk_sha256: str | None = None
    apk_install_pairing_attempt_apk_matches_current_artifact: bool | None = None
    apk_install_pairing_attempt_message: str | None = None
    android_release_signing: dict[str, Any] | None = None
    android_release_signing_ready: bool = False
    android_release_signing_status: str | None = None
    android_release_signing_detail: str | None = None
    android_release_apk_exists: bool = False
    android_release_apk_sha256: str | None = None
    paired_api_bases_reachable: bool = False
    paired_api_bases_status: str | None = None
    paired_api_bases_detail: str | None = None
    docker_engine_status: str | None = None
    docker_engine_detail: str | None = None
    docker_cli_path: str | None = None
    docker_server_version: str | None = None
    docker_wsl_checked: bool = False
    docker_wsl_engine_available: bool = False
    docker_wsl_warnings: tuple[str, ...] = ()
    docker_desktop_winget_available: bool = False
    docker_desktop_install_command: str | None = None
    docker_desktop_elevated_install_command: str | None = None
    docker_desktop_install_attempt_status: str | None = None
    docker_desktop_install_attempt_detail: str | None = None
    docker_desktop_install_attempt_returncode: int | None = None
    docker_desktop_install_attempt_installer_exit_code: int | None = None
    docker_desktop_install_attempt_generated_at: str | None = None
    docker_desktop_install_attempt_admin_elevation_required: bool = False


def run_mobile_release_readiness(
    *,
    workspace_root: str | Path = ".",
    web_base: str = "http://127.0.0.1:4173",
    apk_path: str | Path = "ui/android/app/build/outputs/apk/debug/app-debug.apk",
    timeout_seconds: float = 10.0,
    check_api_proxy: bool = True,
    check_apk: bool = True,
    check_pairing_payload: bool = True,
    check_paired_api_bases: bool = True,
    check_android_device: bool = True,
    check_docker: bool = True,
    check_phone_proof: bool = True,
    launch_native_pairing: bool = False,
    native_pairing_dry_run: bool = True,
    adb_path: str | Path | None = None,
    serial: str | None = None,
    transport: Transport | None = None,
) -> MobileReleaseReadinessReport:
    """Run a single readiness pass for the web app, PWA, APK, and phone gates."""
    root = Path(workspace_root).resolve()
    generated_at = datetime.now(timezone.utc).isoformat()
    smoke = run_web_phone_smoke(
        web_base=web_base,
        apk_path=apk_path,
        timeout_seconds=timeout_seconds,
        check_api_proxy=check_api_proxy,
        check_apk=check_apk,
        web_dist_dir=root / "ui" / "dist",
        transport=transport,
    )
    smoke_payload = _redact(report_to_dict(smoke))
    checks: list[MobileReadinessCheck] = [
        MobileReadinessCheck(
            check_id="web_phone_smoke",
            status="pass" if smoke.failed == 0 else "fail",
            success=smoke.failed == 0,
            detail=smoke.plain_english_summary,
            evidence={
                "passed": smoke.passed,
                "failed": smoke.failed,
                "total_checks": smoke.total_checks,
            },
            elapsed_ms=smoke.elapsed_ms,
        )
    ]

    pairing_check = None
    paired_api_bases_check = None
    if check_pairing_payload:
        pairing_check = _pairing_payload_check(
            web_base=web_base,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        checks.append(pairing_check)
        if check_paired_api_bases:
            paired_api_bases_check = _paired_api_bases_check(
                web_base=web_base,
                timeout_seconds=timeout_seconds,
                transport=transport,
            )
            checks.append(paired_api_bases_check)

    device_probe: AndroidDeviceProbe | None = None
    if check_android_device:
        started = time.perf_counter()
        device_probe = probe_android_devices(adb_path=adb_path, timeout_seconds=min(timeout_seconds, 10.0))
        ready_devices = [device for device in device_probe.devices if device.is_ready]
        if ready_devices:
            status = "pass"
            detail = f"{len(ready_devices)} Android device(s) ready."
            success = True
        elif device_probe.devices:
            status = "external"
            detail = "Android device is visible but not ready; check USB authorization or connection state."
            success = False
        else:
            status = "external"
            detail = "No ready Android device is attached."
            success = False
        checks.append(
            MobileReadinessCheck(
                check_id="android_device_probe",
                status=status,
                success=success,
                detail=detail,
                evidence=_redact(device_probe_to_dict(device_probe)),
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )
        )

    native_launch: AndroidDeepLinkLaunchReport | None = None
    if launch_native_pairing:
        started = time.perf_counter()
        native_launch = launch_android_native_pairing_deep_link(
            serial=serial,
            adb_path=adb_path,
            dry_run=native_pairing_dry_run,
            timeout_seconds=min(timeout_seconds, 30.0),
        )
        checks.append(
            MobileReadinessCheck(
                check_id="native_pairing_launch",
                status="pass" if native_launch.success else "external",
                success=native_launch.success,
                detail=native_launch.message,
                evidence=_redact(deep_link_launch_report_to_dict(native_launch)),
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )
        )
    else:
        checks.append(
            MobileReadinessCheck(
                check_id="native_pairing_launch",
                status="not_run",
                success=False,
                detail="Native pairing launch was not requested; run with --launch-native-pairing when a phone is attached.",
                evidence={},
            )
        )

    release_signing = android_release_signing_status(workspace_root=root)
    checks.append(_android_release_signing_check(release_signing))
    current_apk_artifact = debug_apk_artifact_metadata(workspace_root=root, apk_path=apk_path)

    docker_available = False
    docker_check = None
    if check_docker:
        docker_check = _docker_check()
        docker_available = docker_check.success
        checks.append(docker_check)

    phone_proof = latest_phone_runtime_proof(workspace_root=root) if check_phone_proof else None
    phone_observation = (
        latest_phone_runtime_observation(workspace_root=root) if check_phone_proof else None
    )
    phone_browser_observed = bool(
        phone_observation
        and phone_observation.get("phone_browser_observed")
        and phone_observation.get("is_fresh")
    )
    phone_browser_verified = bool(
        phone_proof
        and phone_proof.get("phone_browser_verified")
        and phone_proof.get("is_fresh")
    )
    if phone_browser_verified:
        phone_detail = "Fresh verified phone browser/PWA runtime proof is recorded."
        phone_evidence = phone_proof or {}
    elif phone_browser_observed:
        phone_detail = (
            "Phone-like runtime was observed, but verified phone network proof is missing; "
            "open Quick Start from a real phone over the LAN preview or direct API base."
        )
        phone_evidence = phone_observation or {}
    else:
        phone_detail = (
            "No fresh phone browser/PWA runtime proof is recorded; open Quick Start from a real phone."
        )
        phone_evidence = {}
    if check_phone_proof:
        checks.append(
            MobileReadinessCheck(
                check_id="phone_runtime_proof",
                status="pass" if phone_browser_verified else "external",
                success=phone_browser_verified,
                detail=phone_detail,
                evidence=_redact(phone_evidence),
            )
        )
    else:
        checks.append(
            MobileReadinessCheck(
                check_id="phone_runtime_proof",
                status="not_run",
                success=False,
                detail="Phone browser/PWA runtime proof check was skipped.",
                evidence={},
            )
        )

    apk_runtime_observation = latest_apk_runtime_observation(workspace_root=root)
    apk_runtime_status = _apk_runtime_status(apk_runtime_observation)
    if apk_runtime_status != "none":
        checks.append(
            MobileReadinessCheck(
                check_id="apk_runtime_observation",
                status="pass" if apk_runtime_status == "verified" else "external",
                success=apk_runtime_status == "verified",
                detail=_apk_runtime_detail(apk_runtime_status),
                evidence=_redact(apk_runtime_observation or {}),
            )
        )

    apk_install_pairing_proof = _current_apk_record(
        latest_android_apk_install_pairing_proof(workspace_root=root),
        current_apk_artifact,
    )
    apk_install_pairing_attempt = _current_apk_record(
        latest_android_apk_install_pairing_attempt(workspace_root=root),
        current_apk_artifact,
    )
    apk_install_pairing_verified = bool(
        apk_install_pairing_proof
        and apk_install_pairing_proof.get("android_apk_install_pairing_verified")
        and apk_install_pairing_proof.get("is_fresh")
    )
    if apk_install_pairing_verified:
        checks.append(
            MobileReadinessCheck(
                check_id="android_apk_install_pairing_proof",
                status="pass",
                success=True,
                detail="Fresh Android APK install plus native pairing proof is recorded.",
                evidence=_redact(apk_install_pairing_proof),
            )
        )
    elif apk_install_pairing_attempt:
        checks.append(
            MobileReadinessCheck(
                check_id="android_apk_install_pairing_attempt",
                status="external",
                success=False,
                detail=_apk_attempt_detail(apk_install_pairing_attempt),
                evidence=_redact(apk_install_pairing_attempt),
            )
        )

    package_ready = (
        smoke.failed == 0
        and (pairing_check.success if pairing_check else True)
        and (paired_api_bases_check.success if paired_api_bases_check else True)
    )
    phone_quick_start_url = _phone_reachable_quick_start_url(web_base, pairing_check)
    physical_phone_verified = bool(native_launch and native_launch.success and not native_launch.dry_run) or apk_install_pairing_verified
    remaining = _remaining_external_gates(
        phone_proof_checked=check_phone_proof,
        phone_browser_verified=phone_browser_verified,
        phone_browser_observed=phone_browser_observed,
        physical_phone_verified=physical_phone_verified,
        docker_available=docker_available,
    )
    summary = _summary(package_ready=package_ready, physical_phone_verified=physical_phone_verified, remaining=remaining)
    return MobileReleaseReadinessReport(
        generated_at=generated_at,
        web_base=web_base,
        phone_quick_start_url=phone_quick_start_url,
        verification_commands=_verification_commands(web_base),
        next_verification_actions=tuple(_next_verification_actions(
            web_base=web_base,
            phone_quick_start_url=phone_quick_start_url,
            package_ready=package_ready,
            phone_browser_verified=phone_browser_verified,
            phone_browser_observed=phone_browser_observed,
            physical_phone_verified=physical_phone_verified,
            docker_available=docker_available,
        )),
        package_ready_for_phone_install=package_ready,
        physical_phone_verified=physical_phone_verified,
        docker_available=docker_available,
        checks=tuple(checks),
        smoke_report=smoke_payload,
        device_probe=_redact(device_probe_to_dict(device_probe)) if device_probe else None,
        native_pairing_launch=_redact(deep_link_launch_report_to_dict(native_launch)) if native_launch else None,
        apk_install_pairing_proof=_redact(apk_install_pairing_proof) if apk_install_pairing_proof else None,
        **_apk_proof_fields(apk_install_pairing_proof, apk_install_pairing_verified),
        apk_install_pairing_attempt=_redact(apk_install_pairing_attempt) if apk_install_pairing_attempt else None,
        **_apk_attempt_fields(apk_install_pairing_attempt),
        summary=summary,
        remaining_external_gates=remaining,
        phone_proof_checked=check_phone_proof,
        phone_browser_observed=phone_browser_observed,
        phone_browser_verified=phone_browser_verified,
        **_phone_freshness_fields("phone_proof", phone_proof),
        **_phone_freshness_fields("phone_observation", phone_observation),
        phone_observation=_redact(phone_observation) if phone_observation else None,
        phone_proof=_redact(phone_proof) if phone_proof else None,
        apk_runtime_observation=_redact(apk_runtime_observation) if apk_runtime_observation else None,
        **_apk_runtime_fields(apk_runtime_observation),
        android_release_signing=_redact(release_signing),
        **_android_release_signing_fields(release_signing),
        **_docker_check_fields(docker_check),
        paired_api_bases_reachable=bool(paired_api_bases_check and paired_api_bases_check.success),
        paired_api_bases_status=paired_api_bases_check.status if paired_api_bases_check else "not_run",
        paired_api_bases_detail=paired_api_bases_check.detail if paired_api_bases_check else "Paired API base reachability check was skipped.",
    )


def readiness_to_dict(report: MobileReleaseReadinessReport) -> dict[str, Any]:
    out = asdict(report)
    out["checks"] = [asdict(check) for check in report.checks]
    return _redact(out)


def run_docker_engine_check() -> MobileReadinessCheck:
    """Run the same Docker Engine diagnosis used by mobile readiness."""
    return _docker_check()


def docker_check_to_dict(check: MobileReadinessCheck) -> dict[str, Any]:
    """Serialize a Docker Engine check without leaking unrelated local state."""
    return _redact(asdict(check))


def render_docker_engine_check(check: MobileReadinessCheck) -> str:
    """Render an owner-facing Docker diagnosis."""
    evidence = check.evidence if isinstance(check.evidence, dict) else {}
    wsl = evidence.get("wsl_docker") if isinstance(evidence.get("wsl_docker"), dict) else {}
    services = evidence.get("docker_windows_services") if isinstance(evidence.get("docker_windows_services"), list) else []
    data_roots = evidence.get("existing_docker_data_roots") if isinstance(evidence.get("existing_docker_data_roots"), list) else []
    install_attempt = evidence.get("docker_desktop_install_attempt") if isinstance(evidence.get("docker_desktop_install_attempt"), dict) else {}
    lines = [
        "CAS Forex Docker Engine diagnosis",
        f"Status: {check.status}",
        f"Ready: {str(check.success).lower()}",
        f"Detail: {check.detail}",
        f"Docker CLI path: {evidence.get('docker_path') or 'not found'}",
        f"Docker server version: {evidence.get('docker_server_version') or wsl.get('server_version') or 'unavailable'}",
        f"Docker Desktop app: {'present' if evidence.get('docker_desktop_app_exists') else 'not found'} ({evidence.get('docker_desktop_app_path') or 'unknown'})",
        f"Docker Desktop data: {'present' if evidence.get('docker_desktop_data_exists') else 'not found'} ({evidence.get('docker_desktop_data_path') or 'unknown'})",
        f"WSL checked: {str(bool(wsl.get('checked'))).lower()}",
        f"WSL engine available: {str(bool(wsl.get('engine_available'))).lower()}",
    ]
    if wsl.get("no_distros"):
        lines.append("WSL distributions: none installed")
    if evidence.get("docker_desktop_install_command"):
        lines.append(f"Docker Desktop install command: {evidence.get('docker_desktop_install_command')}")
    if evidence.get("docker_desktop_elevated_install_command"):
        lines.append(f"Docker Desktop elevated install command: {evidence.get('docker_desktop_elevated_install_command')}")
    if install_attempt:
        lines.append(f"Last Docker Desktop install attempt: {install_attempt.get('status') or 'unknown'}")
        if install_attempt.get("detail"):
            lines.append(f"Last install detail: {install_attempt.get('detail')}")
    wsl_warnings = evidence.get("wsl_warnings")
    if isinstance(wsl_warnings, list) and wsl_warnings:
        lines.append("WSL warnings:")
        lines.extend(f"- {warning}" for warning in wsl_warnings if isinstance(warning, str))
    if wsl.get("engine_distro"):
        lines.append(f"WSL engine distro: {wsl.get('engine_distro')}")
    if data_roots:
        lines.append("Docker data roots:")
        lines.extend(f"- {path}" for path in data_roots)
    if services:
        lines.append("Windows Docker services:")
        for service in services:
            if isinstance(service, dict):
                name = service.get("name") or "unknown"
                status = service.get("status") or "unknown"
                display = service.get("display_name") or name
                lines.append(f"- {name}: {status} ({display})")
    if not check.success:
        lines.append("Next command after installing or starting Docker: docker version --format \"{{.Server.Version}}\"")
    return "\n".join(lines)


def render_readiness_report(report: MobileReleaseReadinessReport) -> str:
    lines = [
        f"CAS Forex mobile readiness for {report.web_base}",
        report.summary,
        "",
        f"Phone Quick Start URL: {report.phone_quick_start_url or 'unavailable'}",
        f"Package ready for phone install: {str(report.package_ready_for_phone_install).lower()}",
        f"Paired API bases: {report.paired_api_bases_detail or report.paired_api_bases_status or 'unknown'}",
        f"Physical phone verified: {str(report.physical_phone_verified).lower()}",
        f"Phone browser observed: {str(report.phone_browser_observed).lower() if report.phone_proof_checked else 'skipped'}",
        f"Phone browser verified: {str(report.phone_browser_verified).lower() if report.phone_proof_checked else 'skipped'}",
        f"Phone proof freshness: {_freshness_label(report.phone_proof_fresh, report.phone_proof_age_seconds, report.phone_proof_expires_at) if report.phone_proof_checked else 'skipped'}",
        f"Phone observation freshness: {_freshness_label(report.phone_observation_fresh, report.phone_observation_age_seconds, report.phone_observation_expires_at) if report.phone_proof_checked else 'skipped'}",
        f"APK runtime observed: {str(report.apk_runtime_observed).lower()}",
        f"APK runtime verified: {str(report.apk_runtime_verified).lower()}",
        f"APK runtime freshness: {_freshness_label(report.apk_runtime_fresh, report.apk_runtime_age_seconds, report.apk_runtime_expires_at) if report.apk_runtime_observation else 'none'}",
        f"Android release signing: {report.android_release_signing_detail or report.android_release_signing_status or 'unknown'}",
        f"Docker available: {str(report.docker_available).lower()}",
        "",
        "Checks:",
    ]
    for check in report.checks:
        marker = "[OK]" if check.success else f"[{check.status.upper()}]"
        lines.append(f"{marker} {check.check_id}: {check.detail}")
    if report.remaining_external_gates:
        lines.extend(["", "Remaining external gates:"])
        for gate in report.remaining_external_gates:
            lines.append(f"- {gate}")
    if report.next_verification_actions:
        lines.extend(["", "Next verification actions:"])
        for action in report.next_verification_actions:
            command = action.get("command") if isinstance(action.get("command"), str) else None
            suffix = f" (`{command}`)" if command else ""
            lines.append(f"- {action.get('title', action.get('action_id', 'Action'))}{suffix}")
    return "\n".join(lines)


def _pairing_payload_check(
    *,
    web_base: str,
    timeout_seconds: float,
    transport: Transport | None,
) -> MobileReadinessCheck:
    started = time.perf_counter()
    attempts = 1
    try:
        response, _, attempts = _fetch_owner_pairing_payload_response(
            web_base=web_base,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        if response.status_code != 200:
            return MobileReadinessCheck(
                check_id="owner_pairing_payload",
                status="fail",
                success=False,
                detail=f"owner pairing payload returned HTTP {response.status_code}",
                evidence={"status_code": response.status_code},
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                attempts=attempts,
            )
        payload = json.loads(response.text)
    except Exception as exc:
        return MobileReadinessCheck(
            check_id="owner_pairing_payload",
            status="fail",
            success=False,
            detail=f"{type(exc).__name__}: {exc}",
            evidence={},
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            attempts=attempts,
        )

    pairing_urls = _string_list(payload.get("pairing_urls"))
    native_urls = _string_list(payload.get("native_pairing_urls"))
    pwa_bases = _string_list(payload.get("pairing_api_bases"))
    direct_bases = _string_list(payload.get("direct_api_bases"))
    selected_pairing_url = _select_url_for_web_base(pairing_urls, web_base)
    selected_native_pairing_url = _select_native_url_for_web_base(native_urls, web_base)
    selected_pwa_api_base = _select_url_for_web_base(pwa_bases, web_base)
    selected_direct_api_base = _select_url_for_web_base(direct_bases, web_base)
    failures: list[str] = []
    if payload.get("report_kind") != "cas_forex_owner_auth":
        failures.append("unexpected report_kind")
    if not pairing_urls or not all("#cas_owner_token=" in url and "cas_api_base=" in url for url in pairing_urls):
        failures.append("web pairing URL missing fragment token/API base")
    if not native_urls or not all(url.startswith("casforex://pair?") and "cas_api_base=" in url for url in native_urls):
        failures.append("native pairing URL missing casforex scheme/API base")
    if not pwa_bases or not all(base.endswith("/api/forex") for base in pwa_bases):
        failures.append("PWA API bases missing or malformed")
    if not direct_bases or not all(base.endswith("/api/forex") for base in direct_bases):
        failures.append("direct API bases missing or malformed")
    success = not failures
    return MobileReadinessCheck(
        check_id="owner_pairing_payload",
        status="pass" if success else "fail",
        success=success,
        detail="owner pairing payload includes web/native pairing URLs and API bases" if success else "; ".join(failures),
        evidence=_redact(
            {
                "pairing_url_count": len(pairing_urls),
                "native_pairing_url_count": len(native_urls),
                "pairing_api_base_count": len(pwa_bases),
                "direct_api_base_count": len(direct_bases),
                "first_pairing_url": pairing_urls[0] if pairing_urls else None,
                "first_native_pairing_url": native_urls[0] if native_urls else None,
                "first_pairing_api_base": pwa_bases[0] if pwa_bases else None,
                "first_direct_api_base": direct_bases[0] if direct_bases else None,
                "selected_pairing_url": selected_pairing_url,
                "selected_native_pairing_url": selected_native_pairing_url,
                "selected_pairing_api_base": selected_pwa_api_base,
                "selected_direct_api_base": selected_direct_api_base,
            }
        ),
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        attempts=attempts,
    )


def _paired_api_bases_check(
    *,
    web_base: str,
    timeout_seconds: float,
    transport: Transport | None,
) -> MobileReadinessCheck:
    started = time.perf_counter()
    attempts = 1
    try:
        response, pairing_source_url, attempts = _fetch_owner_pairing_payload_response(
            web_base=web_base,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        if response.status_code != 200:
            return MobileReadinessCheck(
                check_id="paired_api_bases",
                status="fail",
                success=False,
                detail=f"owner pairing payload returned HTTP {response.status_code}",
                evidence={"pairing_status_code": response.status_code, "pairing_source_url": pairing_source_url},
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                attempts=attempts,
            )
        payload = json.loads(response.text)
    except Exception as exc:
        return MobileReadinessCheck(
            check_id="paired_api_bases",
            status="fail",
            success=False,
            detail=f"{type(exc).__name__}: {exc}",
            evidence={},
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            attempts=attempts,
        )

    token = payload.get("owner_token")
    if not isinstance(token, str) or not token.strip():
        return MobileReadinessCheck(
            check_id="paired_api_bases",
            status="fail",
            success=False,
            detail="owner pairing payload did not include a token for paired API-base verification",
            evidence={},
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            attempts=attempts,
        )

    pwa_bases = _string_list(payload.get("pairing_api_bases"))
    direct_bases = _string_list(payload.get("direct_api_bases"))
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for kind, bases in (("pwa_proxy", pwa_bases), ("direct_api", direct_bases)):
        if not bases:
            failures.append(f"{kind} base missing")
            continue
        for base in bases[:3]:
            result = _paired_api_base_probe(
                kind=kind,
                base=base,
                token=token,
                timeout_seconds=timeout_seconds,
                transport=transport,
            )
            results.append(result)
            attempts += int(result.get("attempts") or 1)
            if not result.get("success"):
                failures.append(f"{kind} {base} {result.get('detail') or 'failed'}")
    success = not failures and bool(results)
    return MobileReadinessCheck(
        check_id="paired_api_bases",
        status="pass" if success else "fail",
        success=success,
        detail=(
            "paired PWA/proxy and APK/direct API bases answered with owner token"
            if success
            else "; ".join(failures) or "paired API bases were not verified"
        ),
        evidence=_redact({"results": results}),
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        attempts=attempts,
    )


def _fetch_owner_pairing_payload_response(
    *,
    web_base: str,
    timeout_seconds: float,
    transport: Transport | None,
) -> tuple[HttpSmokeResponse, str, int]:
    url = _join(web_base, "/api/forex/owner-auth/pairing")
    local_url = "http://127.0.0.1:8765/api/forex/owner-auth/pairing"
    http = transport or _default_transport
    total_attempts = 0
    last_exc: Exception | None = None
    for current_url in (url, local_url):
        try:
            response, attempts = _call_transport_with_retries(http, "GET", current_url, timeout_seconds, {})
        except Exception as exc:
            total_attempts += _PROBE_MAX_ATTEMPTS
            last_exc = exc
            if current_url == url:
                continue
            raise
        total_attempts += attempts
        if current_url == url and response.status_code in {401, 403}:
            continue
        return response, current_url, total_attempts
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("owner pairing payload probe did not run")


def _paired_api_base_probe(
    *,
    kind: str,
    base: str,
    token: str,
    timeout_seconds: float,
    transport: Transport | None,
) -> dict[str, Any]:
    http = transport or _default_transport
    url = _join(base, "/mobile/proof-session/latest")
    headers = {
        "X-CAS-Owner-Token": token,
        "X-CAS-Client-API-Base": base,
    }
    attempts = 1
    try:
        response, attempts = _call_transport_with_retries(http, "GET", url, timeout_seconds, headers)
    except Exception as exc:
        return {
            "kind": kind,
            "base": base,
            "url": url,
            "success": False,
            "status_code": None,
            "detail": f"{type(exc).__name__}: {exc}",
            "attempts": _PROBE_MAX_ATTEMPTS,
        }
    if response.status_code != 200:
        return {
            "kind": kind,
            "base": base,
            "url": url,
            "success": False,
            "status_code": response.status_code,
            "detail": f"returned HTTP {response.status_code}",
            "attempts": attempts,
        }
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        return {
            "kind": kind,
            "base": base,
            "url": url,
            "success": False,
            "status_code": response.status_code,
            "detail": f"response was not JSON: {exc}",
            "attempts": attempts,
        }
    report_kind = payload.get("report_kind")
    success = report_kind == "cas_forex_mobile_external_proof_session"
    return {
        "kind": kind,
        "base": base,
        "url": url,
        "success": success,
        "status_code": response.status_code,
        "detail": "proof session answered" if success else f"unexpected report_kind {report_kind!r}",
        "report_kind": report_kind,
        "status": payload.get("status") if isinstance(payload.get("status"), str) else None,
        "attempts": attempts,
    }


def _android_release_signing_check(signing: dict[str, Any]) -> MobileReadinessCheck:
    ready = bool(signing.get("ready"))
    return MobileReadinessCheck(
        check_id="android_release_signing",
        status="pass" if ready else "external",
        success=ready,
        detail=str(signing.get("summary") or "Android release signing status is unknown."),
        evidence=_redact(signing),
    )


def _docker_check() -> MobileReadinessCheck:
    started = time.perf_counter()
    candidate_paths = (
        Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
        Path.home() / ".docker" / "bin" / "docker.exe",
    )
    docker_desktop_app = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
    program_data = Path("C:/ProgramData/DockerDesktop")
    docker_data_roots = _docker_data_roots()
    existing_data_roots = [path for path in docker_data_roots if path.exists()]
    data_executables = _find_docker_data_executables(existing_data_roots)
    windows_services = _windows_docker_services()
    from_path = shutil.which("docker")
    winget_path = shutil.which("winget")
    existing_candidates = [str(path) for path in candidate_paths if path.exists()]
    docker_path = from_path or (existing_candidates[0] if existing_candidates else None)
    wsl_docker = None if docker_path else _wsl_docker_evidence()
    docker_desktop_install_command = _docker_desktop_install_command(winget_path)
    docker_desktop_elevated_install_command = elevated_install_command_string()
    wsl_warnings = _wsl_warning_lines(wsl_docker)
    install_attempt = latest_docker_desktop_install_attempt()
    evidence: dict[str, Any] = {
        "docker_path": docker_path,
        "path_lookup": from_path,
        "winget_path": winget_path,
        "docker_desktop_winget_available": bool(winget_path),
        "docker_desktop_winget_id": "Docker.DockerDesktop" if winget_path else None,
        "docker_desktop_install_command": docker_desktop_install_command,
        "docker_desktop_elevated_install_command": docker_desktop_elevated_install_command,
        "docker_desktop_install_attempt": install_attempt,
        "candidate_paths": [str(path) for path in candidate_paths],
        "existing_candidate_paths": existing_candidates,
        "docker_desktop_app_path": str(docker_desktop_app),
        "docker_desktop_app_exists": docker_desktop_app.exists(),
        "docker_desktop_data_path": str(program_data),
        "docker_desktop_data_exists": program_data.exists(),
        "docker_data_roots": [str(path) for path in docker_data_roots],
        "existing_docker_data_roots": [str(path) for path in existing_data_roots],
        "docker_data_executables": data_executables,
        "docker_windows_services": windows_services,
        "wsl_docker": wsl_docker,
        "wsl_warnings": wsl_warnings,
    }

    if not docker_path:
        if wsl_docker and wsl_docker.get("engine_available"):
            distro = str(wsl_docker.get("engine_distro") or "WSL")
            server_version = str(wsl_docker.get("server_version") or "unknown")
            return MobileReadinessCheck(
                check_id="docker_cli",
                status="pass",
                success=True,
                detail=(
                    f"Docker Engine answered inside WSL distro {distro}; "
                    f"server version {server_version}."
                ),
                evidence=evidence,
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )
        detail = "Docker CLI not found on PATH or standard Docker Desktop paths."
        if existing_data_roots:
            detail += " Docker Desktop data/log remnants exist"
            if not data_executables:
                detail += ", but no Docker .exe was found in those data folders"
            if not windows_services:
                detail += " and no Docker service is registered"
            detail += "; the CLI/app are not installed."
        if wsl_docker and wsl_docker.get("checked"):
            distro_count = len(wsl_docker.get("distros") or [])
            if wsl_docker.get("no_distros"):
                detail += " WSL is installed but has no Linux distributions to check for Docker Engine."
            else:
                detail += f" WSL Docker was also checked across {distro_count} distro(s) and no answering Docker Engine was found."
        if wsl_warnings:
            detail += f" WSL reported configuration warning(s): {'; '.join(wsl_warnings[:2])}."
        if docker_desktop_install_command:
            detail += f" Docker Desktop can be installed with: {docker_desktop_install_command}"
            detail += f" If Windows asks for administrator elevation, use: {docker_desktop_elevated_install_command}"
        if install_attempt:
            attempt_status = _string_or_none(install_attempt.get("status")) or "unknown"
            attempt_detail = _string_or_none(install_attempt.get("detail"))
            detail += f" Last Docker Desktop install attempt: {attempt_status}."
            if attempt_detail:
                detail += f" {attempt_detail}"
        return MobileReadinessCheck(
            check_id="docker_cli",
            status="external",
            success=False,
            detail=detail,
            evidence=evidence,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    try:
        result = subprocess.run(
            [docker_path, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5.0,
        )
    except FileNotFoundError as exc:
        evidence["docker_version_error"] = f"{type(exc).__name__}: {exc}"
        return MobileReadinessCheck(
            check_id="docker_cli",
            status="external",
            success=False,
            detail=f"Docker CLI path was found at {docker_path}, but the executable could not be launched.",
            evidence=evidence,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    except subprocess.TimeoutExpired:
        evidence["docker_version_timed_out"] = True
        return MobileReadinessCheck(
            check_id="docker_cli",
            status="external",
            success=False,
            detail=f"Docker CLI found at {docker_path}, but Docker Engine did not answer within 5 seconds.",
            evidence=evidence,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    server_version = result.stdout.strip()
    evidence.update(
        {
            "docker_version_returncode": result.returncode,
            "docker_server_version": server_version or None,
            "docker_version_stdout": _trim_output(result.stdout),
            "docker_version_stderr": _trim_output(result.stderr),
        }
    )
    if result.returncode == 0 and server_version:
        return MobileReadinessCheck(
            check_id="docker_cli",
            status="pass",
            success=True,
            detail=f"Docker Engine answered via CLI at {docker_path}; server version {server_version}.",
            evidence=evidence,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    return MobileReadinessCheck(
        check_id="docker_cli",
        status="external",
        success=False,
        detail=f"Docker CLI found at {docker_path}, but Docker Engine did not answer `docker version`.",
        evidence=evidence,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )


def _docker_data_roots() -> tuple[Path, ...]:
    roots = [
        Path("C:/ProgramData/DockerDesktop"),
        Path("C:/ProgramData/Docker"),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    roaming_app_data = os.environ.get("APPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "Docker")
    if roaming_app_data:
        roots.append(Path(roaming_app_data) / "Docker")
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).casefold()
        if key not in seen:
            seen.add(key)
            out.append(root)
    return tuple(out)


def _find_docker_data_executables(roots: list[Path], *, max_results: int = 20) -> list[str]:
    found: list[str] = []
    for root in roots:
        try:
            for path in root.rglob("*.exe"):
                if path.is_file():
                    found.append(str(path))
                    if len(found) >= max_results:
                        return found
        except OSError:
            continue
    return found


def _docker_desktop_install_command(winget_path: str | None) -> str | None:
    if not winget_path:
        return None
    return "winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements"


def _wsl_warning_lines(wsl_docker: dict[str, Any] | None) -> list[str]:
    if not isinstance(wsl_docker, dict):
        return []
    warnings: list[str] = []
    for key in ("wsl_list_stderr", "wsl_list_error"):
        value = _string_or_none(wsl_docker.get(key))
        if value:
            warnings.append(value)
    for distro in wsl_docker.get("distros") or []:
        if not isinstance(distro, dict):
            continue
        name = _string_or_none(distro.get("name")) or "WSL"
        for key in ("stderr", "error"):
            value = _string_or_none(distro.get(key))
            if value:
                warnings.append(f"{name}: {value}")
    out: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        compact = " ".join(str(warning).split())
        if compact and compact not in seen:
            seen.add(compact)
            out.append(compact)
    return out[:5]


def _windows_docker_services() -> list[dict[str, str]]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "$services = Get-Service -ErrorAction SilentlyContinue | "
                    "Where-Object { $_.Name -like '*docker*' -or $_.DisplayName -like '*Docker*' } | "
                    "Select-Object Name,DisplayName,Status; "
                    "$services | ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    services: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("Name")
        display = item.get("DisplayName")
        status = item.get("Status")
        services.append(
            {
                "name": str(name or ""),
                "display_name": str(display or ""),
                "status": str(status or ""),
            }
        )
    return services


def _wsl_docker_evidence() -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "checked": False,
        "wsl_path": None,
        "wsl_list_returncode": None,
        "wsl_list_stdout": "",
        "wsl_list_stderr": "",
        "distros": [],
        "engine_available": False,
    }
    if os.name != "nt":
        return evidence

    wsl_path = shutil.which("wsl.exe")
    if not wsl_path:
        system_root = os.environ.get("SystemRoot", "C:/Windows")
        candidate = Path(system_root) / "System32" / "wsl.exe"
        if candidate.exists():
            wsl_path = str(candidate)
    if not wsl_path:
        return evidence

    evidence["checked"] = True
    evidence["wsl_path"] = wsl_path
    try:
        listed = subprocess.run(
            [wsl_path, "-l", "-v"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        evidence["wsl_list_error"] = f"{type(exc).__name__}: {exc}"
        return evidence

    list_stdout = _clean_wsl_text(listed.stdout)
    list_stderr = _clean_wsl_text(listed.stderr)
    evidence.update(
        {
            "wsl_list_returncode": listed.returncode,
            "wsl_list_stdout": _trim_output(list_stdout),
            "wsl_list_stderr": _trim_output(list_stderr),
        }
    )

    if _wsl_output_says_no_distros(list_stdout) or _wsl_output_says_no_distros(list_stderr):
        evidence["no_distros"] = True
        return evidence

    distro_names = _parse_wsl_distro_names(list_stdout)
    distros: list[dict[str, Any]] = []
    for distro_name in distro_names[:3]:
        distro_evidence = _wsl_distro_docker_evidence(wsl_path, distro_name)
        distros.append(distro_evidence)
        if distro_evidence.get("engine_available"):
            evidence["engine_available"] = True
            evidence["engine_distro"] = distro_name
            evidence["server_version"] = distro_evidence.get("server_version")
            evidence["docker_path"] = distro_evidence.get("docker_path")
            break
    evidence["distros"] = distros
    return evidence


def _wsl_distro_docker_evidence(wsl_path: str, distro_name: str) -> dict[str, Any]:
    script = (
        "docker_path=$(command -v docker || true); "
        "compose_path=$(command -v docker-compose || true); "
        "podman_path=$(command -v podman || true); "
        "printf 'docker_path=%s\\ncompose_path=%s\\npodman_path=%s\\n' "
        '"$docker_path" "$compose_path" "$podman_path"; '
        "if [ -n \"$docker_path\" ]; then "
        "printf 'docker_server_version='; "
        "docker version --format '{{.Server.Version}}' 2>&1 || true; "
        "fi"
    )
    evidence: dict[str, Any] = {
        "name": distro_name,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "docker_path": None,
        "compose_path": None,
        "podman_path": None,
        "server_version": None,
        "engine_available": False,
    }
    try:
        result = subprocess.run(
            [wsl_path, "-d", distro_name, "--", "sh", "-lc", script],
            capture_output=True,
            check=False,
            text=True,
            timeout=20.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        return evidence

    stdout = _clean_wsl_text(result.stdout)
    stderr = _clean_wsl_text(result.stderr)
    parsed = _parse_key_value_lines(stdout)
    server_version = (parsed.get("docker_server_version") or "").strip()
    evidence.update(
        {
            "returncode": result.returncode,
            "stdout": _trim_output(stdout),
            "stderr": _trim_output(stderr),
            "docker_path": parsed.get("docker_path") or None,
            "compose_path": parsed.get("compose_path") or None,
            "podman_path": parsed.get("podman_path") or None,
            "server_version": server_version or None,
            "engine_available": bool(server_version and "Cannot connect" not in server_version),
        }
    )
    return evidence


def _clean_wsl_text(value: str) -> str:
    return value.replace("\x00", "").replace("\r\n", "\n").strip()


def _wsl_output_says_no_distros(value: str) -> bool:
    compact = " ".join(value.casefold().split())
    return any(
        marker in compact
        for marker in (
            "no installed distributions",
            "no distributions are installed",
            "there is no distribution with the supplied name",
            "wsl_e_distro_not_found",
        )
    )


def _parse_wsl_distro_names(value: str) -> list[str]:
    if _wsl_output_says_no_distros(value):
        return []
    names: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or line.upper().startswith("NAME"):
            continue
        lowered = line.casefold()
        if (
            lowered.startswith("windows subsystem for linux")
            or lowered.startswith("you can resolve")
            or lowered.startswith("use 'wsl.exe")
            or lowered.startswith("and 'wsl.exe")
            or lowered.startswith("error code:")
            or lowered.startswith("wsl:")
        ):
            continue
        if line.startswith("*"):
            line = line[1:].strip()
        parts = line.split()
        if not parts:
            continue
        names.append(parts[0])
    return names


def _parse_key_value_lines(value: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in value.splitlines():
        if "=" not in line:
            continue
        key, item = line.split("=", 1)
        parsed[key.strip()] = item.strip()
    return parsed


def _trim_output(value: str, limit: int = 800) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _remaining_external_gates(
    *,
    phone_proof_checked: bool,
    phone_browser_verified: bool,
    phone_browser_observed: bool,
    physical_phone_verified: bool,
    docker_available: bool,
) -> tuple[str, ...]:
    gates: list[str] = []
    if phone_proof_checked and not phone_browser_verified:
        gates.append(
            (
                "Open Quick Start from a real phone over the LAN preview or direct API base so verified "
                "non-localhost phone browser/PWA runtime proof is recorded."
            )
            if phone_browser_observed
            else "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof."
        )
    if not physical_phone_verified:
        gates.append(
            "Attach an Android phone and run npm --prefix ui run mobile:apk:wait-install-pair to prove APK install plus native pairing launch."
        )
    if not docker_available:
        gates.append("Install Docker Desktop or verify the container image on a host with Docker available.")
    return tuple(gates)


def _summary(*, package_ready: bool, physical_phone_verified: bool, remaining: tuple[str, ...]) -> str:
    if package_ready and physical_phone_verified and not remaining:
        return "Mobile web/PWA/APK package and physical phone launch are verified."
    if package_ready:
        return "Mobile web/PWA/APK package is ready; remaining external gates are listed below."
    return "Mobile web/PWA/APK package is not ready; inspect failing readiness checks."


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _join(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _call_transport(
    transport: Transport,
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str],
    body: bytes | None = None,
) -> HttpSmokeResponse:
    try:
        return transport(method, url, timeout_seconds, headers, body)
    except TypeError:
        legacy_transport = transport  # type: ignore[assignment]
        return legacy_transport(method, url, timeout_seconds, headers)  # type: ignore[misc]


def _call_transport_with_retries(
    transport: Transport,
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str],
    body: bytes | None = None,
    *,
    max_attempts: int = _PROBE_MAX_ATTEMPTS,
) -> tuple[HttpSmokeResponse, int]:
    last_exc: Exception | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            response = _call_transport(transport, method, url, timeout_seconds, headers, body)
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                _sleep_before_retry(attempt)
                continue
            break
        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_attempts:
            _sleep_before_retry(attempt)
            continue
        return response, attempt
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("transport probe did not complete")


def _sleep_before_retry(attempt: int) -> None:
    time.sleep(min(0.25 * max(1, attempt), 0.75))


def _quick_start_url(web_base: str | None) -> str | None:
    base = str(web_base or "").strip().rstrip("/")
    if not base:
        return None
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"


def _select_url_for_web_base(values: list[str], web_base: str | None) -> str | None:
    target_host = _url_host(web_base)
    if target_host:
        for value in values:
            if _url_host(value) == target_host:
                return value
    return values[0] if values else None


def _select_native_url_for_web_base(values: list[str], web_base: str | None) -> str | None:
    target_host = _url_host(web_base)
    if target_host:
        for value in values:
            if _url_host(_native_pairing_api_base(value)) == target_host:
                return value
    return values[0] if values else None


def _native_pairing_api_base(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != "casforex":
        return None
    values = parse_qs(parts.query).get("cas_api_base")
    return values[0] if values else None


def _url_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return (urlsplit(url).hostname or "").lower() or None
    except ValueError:
        return None


def _phone_reachable_quick_start_url(
    web_base: str | None,
    pairing_check: MobileReadinessCheck | None,
) -> str | None:
    evidence = pairing_check.evidence if pairing_check and isinstance(pairing_check.evidence, dict) else {}
    pairing_url = _string_or_none(evidence.get("selected_pairing_url")) or _string_or_none(evidence.get("first_pairing_url"))
    from_pairing = _strip_fragment(pairing_url)
    if from_pairing and not _is_loopback_url(from_pairing):
        return from_pairing
    from_api_base = _quick_start_from_api_base(
        _string_or_none(evidence.get("selected_pairing_api_base"))
        or _string_or_none(evidence.get("first_pairing_api_base"))
    )
    if from_api_base and not _is_loopback_url(from_api_base):
        return from_api_base
    from_web_base = _quick_start_url(web_base)
    if from_web_base and _is_private_lan_url(from_web_base):
        return from_web_base
    return from_web_base


def _strip_fragment(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _quick_start_from_api_base(api_base: str | None) -> str | None:
    if not api_base:
        return None
    try:
        parts = urlsplit(api_base)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, "/", "page=quick-start", ""))


def _is_loopback_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return host == "localhost" or host.startswith("127.") or host == "::1"


def _is_private_lan_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        host = urlsplit(url).hostname or ""
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private and not ip.is_loopback


def _verification_commands(web_base: str | None) -> dict[str, str]:
    base = str(web_base or "").strip().rstrip("/")
    readiness = "npm --prefix ui run mobile:readiness"
    stack = "npm --prefix ui run mobile:stack"
    release_bundle = "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure"
    if base:
        readiness = f"{readiness} -- --web-base {base}"
        stack = f"{stack} -- --web-base {base}"
        release_bundle = f"python scripts/build_web_phone_release_bundle.py --web-base {base} --exit-code-on-failure"
    return {
        "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
        "phone_verification_session": "npm --prefix ui run mobile:verify-session",
        "mobile_proof_session": "npm --prefix ui run mobile:proof-session",
        "mobile_final_verification": "npm --prefix ui run mobile:finish",
        "mobile_final_verification_watch": "npm --prefix ui run mobile:finish -- --watch-phone",
        "mobile_final_verification_watch_all": "npm --prefix ui run mobile:finish -- --watch-all",
        "mobile_final_verification_watch_all_live_links": (
            "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
        ),
        "mobile_readiness": readiness,
        "mobile_stack": stack,
        "release_bundle": release_bundle,
        "apk_debug_build": "npm --prefix ui run mobile:apk:debug",
        "apk_build_all": "npm --prefix ui run mobile:apk:build-all",
        "apk_release_signing_setup": "npm --prefix ui run mobile:apk:setup-release-signing",
        "apk_release_build": "npm --prefix ui run mobile:apk:release",
        "apk_device_list": "npm --prefix ui run mobile:apk:devices",
        "apk_install_pair": "npm --prefix ui run mobile:apk:install-pair",
        "apk_wait_install_pair": "npm --prefix ui run mobile:apk:wait-install-pair",
        "docker_engine_diagnose": "npm --prefix ui run mobile:docker-check",
        "docker_desktop_install": "npm --prefix ui run mobile:docker-install",
        "docker_desktop_install_elevated": elevated_install_command_string(),
        "docker_engine_check": 'docker version --format "{{.Server.Version}}"',
        "docker_compose_build": "docker compose build",
    }


def _next_verification_actions(
    *,
    web_base: str | None,
    package_ready: bool,
    phone_browser_verified: bool,
    phone_browser_observed: bool,
    physical_phone_verified: bool,
    docker_available: bool,
    phone_quick_start_url: str | None = None,
) -> list[dict[str, Any]]:
    commands = _verification_commands(web_base)
    phone_url = phone_quick_start_url or _quick_start_url(web_base)
    actions: list[dict[str, Any]] = []
    if not package_ready:
        actions.append(
            {
                "action_id": "release_bundle",
                "status": "pending",
                "title": "Refresh web/phone release evidence",
                "detail": "Run the release bundle check so the APK, PWA assets, API proxy, pairing payload, and external gates are snapshotted together.",
                "command": commands["release_bundle"],
                "target_url": None,
                "secondary_commands": [commands["mobile_stack"]],
                "blocks_completion": True,
            }
        )
    if not phone_browser_verified:
        actions.append(
            {
                "action_id": "phone_browser_proof",
                "status": "pending",
                "title": "Verify real phone Quick Start",
                "detail": (
                    "A phone-like runtime was observed locally; open the Quick Start URL from the real phone over LAN, or use the desktop pairing QR/link for a fresh phone, so non-localhost network proof is recorded."
                    if phone_browser_observed
                    else "Open or scan the Quick Start URL from the real phone over LAN, or use the desktop pairing QR/link for a fresh phone, then wait for the proof watcher to report VERIFIED."
                ),
                "command": commands["phone_proof_watcher"],
                "target_url": phone_url,
                "secondary_commands": [commands["mobile_readiness"]],
                "blocks_completion": True,
            }
        )
    if not physical_phone_verified:
        actions.append(
            {
                "action_id": "android_apk_install_pairing",
                "status": "pending",
                "title": "Verify APK install and native pairing",
                "detail": "Start the wait/install command, plug in and unlock the Android phone, approve USB debugging, then let it install the debug APK and launch the native pairing link.",
                "command": commands["apk_wait_install_pair"],
                "target_url": None,
                "secondary_commands": [commands["apk_device_list"], commands["apk_build_all"], commands["apk_install_pair"]],
                "blocks_completion": True,
            }
        )
    if not docker_available:
        actions.append(
            {
                "action_id": "docker_engine",
                "status": "pending",
                "title": "Verify Docker Engine",
                "detail": "Run the CAS Forex Docker diagnosis on this machine, then install/start Docker Desktop or verify on another Docker host before claiming container readiness.",
                "command": commands["docker_engine_diagnose"],
                "target_url": None,
                "secondary_commands": [
                    commands["docker_desktop_install"],
                    commands["docker_desktop_install_elevated"],
                    commands["docker_engine_check"],
                    commands["docker_compose_build"],
                ],
                "blocks_completion": True,
            }
        )
    return actions


def _default_transport(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str] | None = None,
) -> HttpSmokeResponse:
    from cas_forex.web_phone_smoke import _default_transport as default_transport

    return default_transport(method, url, timeout_seconds, headers or {})


def _phone_freshness_fields(prefix: str, proof: dict[str, Any] | None) -> dict[str, Any]:
    proof = proof or {}
    max_age_hours = proof.get("max_age_hours")
    return {
        f"{prefix}_fresh": bool(proof.get("is_fresh")) if proof else False,
        f"{prefix}_age_seconds": proof.get("age_seconds") if isinstance(proof.get("age_seconds"), int) else None,
        f"{prefix}_expires_at": _string_or_none(proof.get("expires_at")),
        f"{prefix}_max_age_hours": max_age_hours if isinstance(max_age_hours, int) else None,
    }


def _apk_runtime_fields(apk_runtime_observation: dict[str, Any] | None) -> dict[str, Any]:
    observation = apk_runtime_observation or {}
    status = _apk_runtime_status(observation)
    return {
        "apk_runtime_observed": status in {"verified", "local_only", "observed"},
        "apk_runtime_verified": status == "verified",
        "apk_runtime_fresh": bool(observation.get("is_fresh")) if observation else False,
        "apk_runtime_age_seconds": observation.get("age_seconds") if isinstance(observation.get("age_seconds"), int) else None,
        "apk_runtime_expires_at": _string_or_none(observation.get("expires_at")),
    }


def _apk_proof_fields(
    apk_install_pairing_proof: dict[str, Any] | None,
    verified: bool,
) -> dict[str, Any]:
    proof = apk_install_pairing_proof or {}
    return {
        "apk_install_pairing_verified": verified,
        "apk_install_pairing_generated_at": _string_or_none(proof.get("generated_at")),
        "apk_install_pairing_selected_serial": _string_or_none(proof.get("selected_serial")),
        "apk_install_pairing_package_id": _string_or_none(proof.get("package_id")),
        "apk_install_pairing_apk_sha256": _string_or_none(proof.get("apk_sha256")),
        "apk_install_pairing_current_apk_sha256": _string_or_none(proof.get("current_apk_sha256")),
        "apk_install_pairing_apk_matches_current_artifact": (
            proof.get("apk_matches_current_artifact")
            if isinstance(proof.get("apk_matches_current_artifact"), bool)
            else None
        ),
    }


def _apk_attempt_fields(apk_install_pairing_attempt: dict[str, Any] | None) -> dict[str, Any]:
    attempt = apk_install_pairing_attempt or {}
    return {
        "apk_install_pairing_attempt_recorded": bool(attempt),
        "apk_install_pairing_attempt_status": _apk_attempt_status(attempt),
        "apk_install_pairing_attempt_fresh": bool(attempt.get("is_fresh")) if attempt else False,
        "apk_install_pairing_attempt_age_seconds": attempt.get("age_seconds") if isinstance(attempt.get("age_seconds"), int) else None,
        "apk_install_pairing_attempt_expires_at": _string_or_none(attempt.get("expires_at")),
        "apk_install_pairing_attempt_generated_at": _string_or_none(attempt.get("generated_at")),
        "apk_install_pairing_attempt_install_success": bool(attempt.get("install_success")) if attempt else False,
        "apk_install_pairing_attempt_native_pairing_success": bool(attempt.get("native_pairing_success")) if attempt else False,
        "apk_install_pairing_attempt_dry_run": bool(attempt.get("dry_run")) if attempt else False,
        "apk_install_pairing_attempt_selected_serial": _string_or_none(attempt.get("selected_serial")),
        "apk_install_pairing_attempt_package_id": _string_or_none(attempt.get("package_id")),
        "apk_install_pairing_attempt_apk_sha256": _string_or_none(attempt.get("apk_sha256")),
        "apk_install_pairing_attempt_current_apk_sha256": _string_or_none(attempt.get("current_apk_sha256")),
        "apk_install_pairing_attempt_apk_matches_current_artifact": (
            attempt.get("apk_matches_current_artifact")
            if isinstance(attempt.get("apk_matches_current_artifact"), bool)
            else None
        ),
        "apk_install_pairing_attempt_message": _apk_attempt_message(attempt),
    }


def _android_release_signing_fields(signing: dict[str, Any] | None) -> dict[str, Any]:
    signing = signing or {}
    return {
        "android_release_signing_ready": bool(signing.get("ready")),
        "android_release_signing_status": _string_or_none(signing.get("status")),
        "android_release_signing_detail": _string_or_none(signing.get("summary")),
        "android_release_apk_exists": bool(signing.get("release_apk_exists")),
        "android_release_apk_sha256": _string_or_none(signing.get("release_apk_sha256")),
    }


def _docker_check_fields(check: MobileReadinessCheck | None) -> dict[str, Any]:
    if check is None:
        return {
            "docker_engine_status": "not_run",
            "docker_engine_detail": "Docker Engine check was skipped.",
            "docker_cli_path": None,
            "docker_server_version": None,
            "docker_wsl_checked": False,
            "docker_wsl_engine_available": False,
            "docker_wsl_warnings": (),
            "docker_desktop_winget_available": False,
            "docker_desktop_install_command": None,
            "docker_desktop_elevated_install_command": elevated_install_command_string(),
            "docker_desktop_install_attempt_status": None,
            "docker_desktop_install_attempt_detail": None,
            "docker_desktop_install_attempt_returncode": None,
            "docker_desktop_install_attempt_installer_exit_code": None,
            "docker_desktop_install_attempt_generated_at": None,
            "docker_desktop_install_attempt_admin_elevation_required": False,
        }
    evidence = check.evidence if isinstance(check.evidence, dict) else {}
    wsl = evidence.get("wsl_docker") if isinstance(evidence.get("wsl_docker"), dict) else {}
    warnings = evidence.get("wsl_warnings") if isinstance(evidence.get("wsl_warnings"), list) else []
    install_attempt = (
        evidence.get("docker_desktop_install_attempt")
        if isinstance(evidence.get("docker_desktop_install_attempt"), dict)
        else {}
    )
    return {
        "docker_engine_status": check.status,
        "docker_engine_detail": check.detail,
        "docker_cli_path": _string_or_none(evidence.get("docker_path")),
        "docker_server_version": _string_or_none(evidence.get("docker_server_version")) or _string_or_none(wsl.get("server_version")),
        "docker_wsl_checked": bool(wsl.get("checked")),
        "docker_wsl_engine_available": bool(wsl.get("engine_available")),
        "docker_wsl_warnings": tuple(item for item in warnings if isinstance(item, str)),
        "docker_desktop_winget_available": bool(evidence.get("docker_desktop_winget_available")),
        "docker_desktop_install_command": _string_or_none(evidence.get("docker_desktop_install_command")),
        "docker_desktop_elevated_install_command": (
            _string_or_none(evidence.get("docker_desktop_elevated_install_command"))
            or elevated_install_command_string()
        ),
        "docker_desktop_install_attempt_status": _string_or_none(install_attempt.get("status")),
        "docker_desktop_install_attempt_detail": _string_or_none(install_attempt.get("detail")),
        "docker_desktop_install_attempt_returncode": (
            install_attempt.get("returncode")
            if isinstance(install_attempt.get("returncode"), int)
            else None
        ),
        "docker_desktop_install_attempt_installer_exit_code": (
            install_attempt.get("installer_exit_code")
            if isinstance(install_attempt.get("installer_exit_code"), int)
            else None
        ),
        "docker_desktop_install_attempt_generated_at": _string_or_none(install_attempt.get("generated_at")),
        "docker_desktop_install_attempt_admin_elevation_required": bool(install_attempt.get("admin_elevation_required")),
    }


def _apk_attempt_status(attempt: dict[str, Any]) -> str:
    if not attempt:
        return "none"
    if attempt.get("apk_matches_current_artifact") is False:
        return "stale_apk"
    if not bool(attempt.get("is_fresh")):
        return "stale"
    if bool(attempt.get("android_apk_install_pairing_verified")):
        return "verified"
    if bool(attempt.get("dry_run")):
        return "dry_run"
    if not bool(attempt.get("install_success")):
        return "install_failed"
    if not bool(attempt.get("native_pairing_success")):
        return "pairing_failed"
    return "not_verified"


def _apk_attempt_message(attempt: dict[str, Any]) -> str | None:
    if not attempt:
        return None
    if _apk_attempt_status(attempt) == "stale_apk":
        return _string_or_none(attempt.get("stale_reason")) or (
            "Latest Android APK install/native-pairing attempt is for a different APK build."
        )
    native_message = _string_or_none(attempt.get("native_pairing_message"))
    install_message = _string_or_none(attempt.get("install_message"))
    if _apk_attempt_status(attempt) == "install_failed":
        return install_message or native_message
    return native_message or install_message


def _apk_runtime_status(apk_runtime_observation: dict[str, Any] | None) -> str:
    if not apk_runtime_observation:
        return "none"
    if apk_runtime_observation.get("app_surface") != "apk":
        return "none"
    if not apk_runtime_observation.get("phone_browser_observed"):
        return "none"
    if not apk_runtime_observation.get("is_fresh"):
        return "stale"
    if apk_runtime_observation.get("phone_browser_verified"):
        return "verified"
    if apk_runtime_observation.get("local_runtime_only"):
        return "local_only"
    return "observed"


def _apk_runtime_detail(status: str) -> str:
    if status == "verified":
        return (
            "Fresh APK runtime evidence is recorded from a verified non-local phone/API path; "
            "ADB install/native-pairing proof is still tracked separately."
        )
    if status == "local_only":
        return (
            "APK runtime was observed locally, but verified non-local phone/API evidence is missing; "
            "open the installed APK from the phone over LAN/direct API."
        )
    if status == "observed":
        return "APK runtime was observed, but it has not satisfied verified non-local phone/API proof."
    if status == "stale":
        return "APK runtime evidence exists but is stale; reopen the installed APK from the phone."
    return "No APK runtime evidence has been recorded."


def _current_apk_record(record: dict[str, Any] | None, current_apk_artifact: dict[str, Any]) -> dict[str, Any] | None:
    if not record:
        return None
    out = dict(record)
    expected_sha = _string_or_none(current_apk_artifact.get("sha256"))
    recorded_sha = _string_or_none(out.get("apk_sha256"))
    if not expected_sha:
        out["current_apk_sha256"] = None
        out["apk_matches_current_artifact"] = None
        return out
    out["current_apk_sha256"] = expected_sha
    matches = bool(recorded_sha and recorded_sha.lower() == expected_sha.lower())
    out["apk_matches_current_artifact"] = matches
    if not matches:
        out["is_fresh"] = False
        out["stale_reason"] = (
            "APK install/native-pairing evidence was recorded for a different APK build; "
            "rebuild/install/pair again so proof matches the current artifact."
        )
    return out


def _apk_attempt_detail(attempt: dict[str, Any]) -> str:
    if attempt.get("apk_matches_current_artifact") is False:
        return "Latest Android APK install/native-pairing attempt is for a different APK build; rerun npm --prefix ui run mobile:apk:wait-install-pair."
    if not attempt.get("is_fresh"):
        return "Latest Android APK install/native-pairing attempt is stale; rerun npm --prefix ui run mobile:apk:wait-install-pair."
    if attempt.get("dry_run"):
        return "Latest Android APK install/native-pairing attempt was a dry run; rerun without --dry-run for proof."
    if not attempt.get("install_success"):
        return _string_or_none(attempt.get("install_message")) or "Latest Android APK install attempt failed."
    if not attempt.get("native_pairing_success"):
        return _string_or_none(attempt.get("native_pairing_message")) or "Latest Android native pairing launch failed."
    return "Latest Android APK install/native-pairing attempt is not verified."


def _freshness_label(is_fresh: bool, age_seconds: int | None, expires_at: str | None) -> str:
    if age_seconds is None and not expires_at:
        return "none"
    parts = ["fresh" if is_fresh else "expired"]
    age = _format_age(age_seconds)
    if age:
        parts.append(age)
    if expires_at:
        parts.append(f"{'expires' if is_fresh else 'expired'} at {expires_at}")
    return ", ".join(parts)


def _format_age(age_seconds: int | None) -> str | None:
    if age_seconds is None:
        return None
    total = max(0, int(age_seconds))
    if total < 60:
        return f"{total}s old"
    if total < 3600:
        return f"{total // 60}m old"
    if total < 86400:
        hours = total // 3600
        minutes = (total % 3600) // 60
        return f"{hours}h {minutes}m old" if minutes else f"{hours}h old"
    days = total // 86400
    hours = (total % 86400) // 3600
    return f"{days}d {hours}h old" if hours else f"{days}d old"


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, dict):
        return {
            key: ("REDACTED" if key in {"owner_token", "cas_owner_token"} else _redact(item))
            for key, item in value.items()
        }
    return value


def _redact_string(value: str) -> str:
    value = re.sub(r"(cas_owner_token=)[^&#\s}]+", r"\1REDACTED", value)
    value = re.sub(r"([?&]owner_token=)[^&#\s}]+", r"\1REDACTED", value)
    return value
