"""Owner-facing combined phone/APK/Docker proof session."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from cas_forex.mobile_phone_verifier import (
    PhoneProofWatchStatus,
    phone_proof_watch_status,
    wait_for_phone_proof,
)
from cas_forex.phone_verification_session import build_phone_verification_session


REPORT_KIND = "cas_forex_mobile_external_proof_session"


@dataclass(frozen=True)
class MobileProofGate:
    gate_id: str
    title: str
    satisfied: bool
    command: str | None
    target_url: str | None
    detail: str


@dataclass(frozen=True)
class MobileProofSession:
    report_kind: str
    generated_at: str
    status: str
    summary: str
    package_ready_for_phone_install: bool
    phone_quick_start_url: str | None
    tested_quick_start_url: str | None
    phone_proof_target_url: str | None
    phone_proof_target_kind: str
    pairing_context: dict
    phone_pairing_handoff: str | None
    phone_browser_verified: bool
    phone_browser_observed: bool
    apk_install_pairing_verified: bool
    apk_install_pairing_attempt_status: str | None
    paired_api_bases_reachable: bool
    paired_api_bases_status: str | None
    paired_api_bases_detail: str | None
    docker_available: bool
    docker_engine_status: str | None
    docker_engine_detail: str | None
    docker_desktop_install_command: str | None
    docker_desktop_elevated_install_command: str | None
    docker_desktop_install_attempt_status: str | None
    docker_desktop_install_attempt_detail: str | None
    docker_desktop_install_attempt_installer_exit_code: int | None
    phone_watch_status: dict
    proof_state: dict
    release_artifact_summary: dict
    owner_commands: dict[str, str]
    gates: tuple[MobileProofGate, ...]
    remaining_external_gates: tuple[str, ...]
    source_session_status: str
    source_session_summary: str


def build_mobile_proof_session(
    *,
    workspace_root: str | Path = ".",
    watch_phone: bool = False,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 2.0,
    status_reader: Callable[[], PhoneProofWatchStatus] | None = None,
) -> MobileProofSession:
    """Build a concise, current checklist for the external phone/Docker gates."""
    root = Path(workspace_root).resolve()
    phone_status = (
        wait_for_phone_proof(
            workspace_root=root,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
            status_reader=status_reader,
        )
        if watch_phone
        else (status_reader() if status_reader else phone_proof_watch_status(workspace_root=root))
    )
    session = build_phone_verification_session(workspace_root=root)
    commands = _owner_commands(session)
    package_ready = bool(session.get("package_ready_for_phone_install"))
    phone_verified = bool(session.get("phone_browser_verified")) or bool(phone_status.phone_browser_verified)
    phone_observed = bool(session.get("phone_browser_observed")) or bool(phone_status.phone_browser_observed)
    apk_verified = bool(session.get("apk_install_pairing_verified"))
    paired_api_bases_reachable = bool(session.get("paired_api_bases_reachable"))
    docker_available = bool(session.get("docker_available"))
    docker_detail = _string_or_none(session.get("docker_engine_detail"))
    docker_install_command = _string_or_none(session.get("docker_desktop_install_command"))
    docker_elevated_install_command = (
        _string_or_none(session.get("docker_desktop_elevated_install_command"))
        or commands.get("docker_desktop_install_elevated")
    )
    docker_install_attempt_status = _string_or_none(session.get("docker_desktop_install_attempt_status"))
    docker_install_attempt_detail = _string_or_none(session.get("docker_desktop_install_attempt_detail"))
    docker_install_attempt_installer_exit_code = session.get("docker_desktop_install_attempt_installer_exit_code")
    if not isinstance(docker_install_attempt_installer_exit_code, int):
        docker_install_attempt_installer_exit_code = None
    phone_quick_start_url = _string_or_none(session.get("phone_quick_start_url")) or phone_status.phone_quick_start_url
    pairing_context = _dict_or_empty(session.get("pairing_context"))
    phone_pairing_available = bool(_string_or_none(pairing_context.get("redacted_pairing_url")))
    phone_proof_target_kind = (
        "quick_start"
        if phone_verified or not phone_pairing_available
        else "quick_start_with_live_pairing_if_needed"
    )
    phone_pairing_handoff = _phone_pairing_handoff(
        pairing_context=pairing_context,
        phone_verified=phone_verified,
    )
    gates = (
        MobileProofGate(
            gate_id="phone_browser_proof",
            title="Real phone Quick Start proof",
            satisfied=phone_verified,
            command=commands.get("phone_proof_watcher"),
            target_url=phone_quick_start_url,
            detail=(
                "Fresh verified non-local phone proof is recorded."
                if phone_verified
                else _phone_proof_gate_detail(phone_pairing_available=phone_pairing_available)
            ),
        ),
        MobileProofGate(
            gate_id="android_apk_install_pairing",
            title="Android APK install and native pairing proof",
            satisfied=apk_verified,
            command=commands.get("apk_wait_install_pair"),
            target_url=None,
            detail=(
                "Fresh APK install/native-pairing proof is recorded."
                if apk_verified
                else "Start the wait/install command, then plug in, unlock, and authorize the Android phone."
            ),
        ),
        MobileProofGate(
            gate_id="docker_engine",
            title="Docker Engine proof",
            satisfied=docker_available,
            command=commands.get("docker_engine_diagnose") or commands.get("docker_engine_check"),
            target_url=None,
            detail=(
                "Docker Engine answered."
                if docker_available
                else docker_detail
                or docker_install_attempt_detail
                or "Run the Docker diagnosis, then install/start Docker Desktop or verify on another Docker host."
            ),
        ),
    )
    remaining_gates = tuple(gate.title for gate in gates if not gate.satisfied)
    if not package_ready:
        status = "package_not_ready"
        summary = "Phone package evidence is not ready; refresh the release bundle or mobile stack first."
    elif not remaining_gates:
        status = "verified"
        summary = "Phone package, real phone proof, APK/native pairing, and Docker Engine proof are green."
    else:
        status = "external_proof_pending"
        summary = f"Phone package is ready; {len(remaining_gates)} external proof gate(s) remain."
    return MobileProofSession(
        report_kind=REPORT_KIND,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        summary=summary,
        package_ready_for_phone_install=package_ready,
        phone_quick_start_url=phone_quick_start_url,
        tested_quick_start_url=_string_or_none(session.get("tested_quick_start_url")) or phone_status.tested_quick_start_url,
        phone_proof_target_url=phone_quick_start_url,
        phone_proof_target_kind=phone_proof_target_kind,
        pairing_context=pairing_context,
        phone_pairing_handoff=phone_pairing_handoff,
        phone_browser_verified=phone_verified,
        phone_browser_observed=phone_observed,
        apk_install_pairing_verified=apk_verified,
        apk_install_pairing_attempt_status=_string_or_none(session.get("apk_install_pairing_attempt_status")),
        paired_api_bases_reachable=paired_api_bases_reachable,
        paired_api_bases_status=_string_or_none(session.get("paired_api_bases_status")),
        paired_api_bases_detail=_string_or_none(session.get("paired_api_bases_detail")),
        docker_available=docker_available,
        docker_engine_status=_string_or_none(session.get("docker_engine_status")),
        docker_engine_detail=docker_detail,
        docker_desktop_install_command=docker_install_command,
        docker_desktop_elevated_install_command=docker_elevated_install_command,
        docker_desktop_install_attempt_status=docker_install_attempt_status,
        docker_desktop_install_attempt_detail=docker_install_attempt_detail,
        docker_desktop_install_attempt_installer_exit_code=docker_install_attempt_installer_exit_code,
        phone_watch_status=asdict(phone_status),
        proof_state=_dict_or_empty(session.get("proof_state")),
        release_artifact_summary=_dict_or_empty(session.get("release_artifact_summary")),
        owner_commands=commands,
        gates=gates,
        remaining_external_gates=remaining_gates,
        source_session_status=_string_or_none(session.get("status")) or "unknown",
        source_session_summary=_string_or_none(session.get("summary")) or "",
    )


def mobile_proof_session_to_dict(session: MobileProofSession) -> dict:
    return asdict(session)


def mobile_proof_session_to_json(session: MobileProofSession) -> str:
    return json.dumps(mobile_proof_session_to_dict(session), indent=2, sort_keys=True)


def render_mobile_proof_session(session: MobileProofSession) -> str:
    marker = "[OK]" if session.status == "verified" else f"[{session.status.upper()}]"
    lines = [
        "CAS Forex mobile external proof session",
        f"{marker} {session.summary}",
        "",
        f"Phone Quick Start URL: {session.phone_quick_start_url or 'unavailable'}",
        f"Tested Quick Start URL: {session.tested_quick_start_url or 'unavailable'}",
        f"Phone proof target: {session.phone_proof_target_url or 'unavailable'} ({session.phone_proof_target_kind})",
        f"Package ready: {str(session.package_ready_for_phone_install).lower()}",
        f"Phone browser observed: {str(session.phone_browser_observed).lower()}",
        f"Phone browser verified: {str(session.phone_browser_verified).lower()}",
        f"APK install/native pairing verified: {str(session.apk_install_pairing_verified).lower()}",
        f"APK last attempt: {session.apk_install_pairing_attempt_status or 'none'}",
        f"Paired API bases: {session.paired_api_bases_detail or session.paired_api_bases_status or 'unknown'}",
        f"Docker Engine: {session.docker_engine_status or 'unknown'}",
        f"Docker detail: {session.docker_engine_detail or 'unavailable'}",
        f"Docker install command: {session.docker_desktop_install_command or 'unavailable'}",
        f"Docker elevated install command: {session.docker_desktop_elevated_install_command or 'npm --prefix ui run mobile:docker-install-elevated'}",
        f"Docker install attempt: {_docker_install_attempt_line(session)}",
    ]
    artifact_summary = session.release_artifact_summary or {}
    if artifact_summary:
        lines.extend(
            [
                f"Debug APK: {_artifact_digest(artifact_summary, 'android_debug_apk')}",
                f"Release APK: {_artifact_digest(artifact_summary, 'android_release_apk')}",
                f"Web index: {artifact_summary.get('web_index_sha256') or 'unavailable'}",
                f"Service worker: {artifact_summary.get('service_worker_sha256') or 'unavailable'}",
            ]
        )
    if session.pairing_context or session.phone_pairing_handoff:
        pairing = session.pairing_context or {}
        lines.extend(
            [
                "",
                "Pairing Handoff:",
                f"- PWA/proxy API base: {pairing.get('pwa_api_base') or 'unavailable'}",
                f"- APK/direct API base: {pairing.get('direct_api_base') or 'unavailable'}",
                f"- Redacted PWA pairing URL: {pairing.get('redacted_pairing_url') or 'unavailable'}",
                f"- Redacted APK pairing URL: {pairing.get('redacted_native_pairing_url') or 'unavailable'}",
                f"- Note: {session.phone_pairing_handoff or 'Use the live desktop UI for copyable pairing links when the phone is unpaired.'}",
            ]
        )
    lines.extend(["", "External Proof Gates:"])
    for gate in session.gates:
        gate_marker = "[OK]" if gate.satisfied else "[PENDING]"
        lines.append(f"- {gate_marker} {gate.title}: {gate.detail}")
        if gate.target_url:
            lines.append(f"  Target: {gate.target_url}")
        if gate.command:
            lines.append(f"  Command: {gate.command}")
    if session.owner_commands:
        lines.extend(
            [
                "",
                "Owner Commands:",
                f"- Final verification: {session.owner_commands.get('mobile_final_verification') or 'npm --prefix ui run mobile:finish'}",
                f"- Watch all final gates: {session.owner_commands.get('mobile_final_verification_watch_all') or 'npm --prefix ui run mobile:finish -- --watch-all'}",
                f"- Watch all final gates with live links: {session.owner_commands.get('mobile_final_verification_watch_all_live_links') or 'npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links'}",
                f"- Proof session: {session.owner_commands.get('mobile_proof_session') or 'npm --prefix ui run mobile:proof-session'}",
                f"- Watch phone proof: {session.owner_commands.get('phone_proof_watcher') or 'npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing'}",
                f"- APK build-all: {session.owner_commands.get('apk_build_all') or 'npm --prefix ui run mobile:apk:build-all'}",
                f"- APK wait/install-pair: {session.owner_commands.get('apk_wait_install_pair') or 'npm --prefix ui run mobile:apk:wait-install-pair'}",
                f"- Docker diagnosis: {session.owner_commands.get('docker_engine_diagnose') or 'npm --prefix ui run mobile:docker-check'}",
                f"- Docker install: {session.owner_commands.get('docker_desktop_install') or 'npm --prefix ui run mobile:docker-install'}",
                f"- Docker elevated install: {session.owner_commands.get('docker_desktop_install_elevated') or 'npm --prefix ui run mobile:docker-install-elevated'}",
                f"- Refresh verification session: {session.owner_commands.get('phone_verification_session') or 'npm --prefix ui run mobile:verify-session'}",
            ]
        )
    return "\n".join(lines)


def _owner_commands(session: dict) -> dict[str, str]:
    raw = session.get("owner_commands") if isinstance(session.get("owner_commands"), dict) else {}
    commands = {str(key): str(value) for key, value in raw.items() if isinstance(value, str) and value.strip()}
    commands.setdefault("mobile_final_verification", "npm --prefix ui run mobile:finish")
    commands.setdefault("mobile_final_verification_watch", "npm --prefix ui run mobile:finish -- --watch-phone")
    commands.setdefault("mobile_final_verification_watch_all", "npm --prefix ui run mobile:finish -- --watch-all")
    commands.setdefault(
        "mobile_final_verification_watch_all_live_links",
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links",
    )
    commands.setdefault("mobile_proof_session", "npm --prefix ui run mobile:proof-session")
    commands.setdefault("phone_proof_watcher", "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing")
    commands.setdefault("apk_build_all", "npm --prefix ui run mobile:apk:build-all")
    commands.setdefault("apk_wait_install_pair", "npm --prefix ui run mobile:apk:wait-install-pair")
    commands.setdefault("docker_engine_diagnose", "npm --prefix ui run mobile:docker-check")
    commands.setdefault("docker_desktop_install", "npm --prefix ui run mobile:docker-install")
    commands.setdefault("docker_desktop_install_elevated", "npm --prefix ui run mobile:docker-install-elevated")
    commands.setdefault("phone_verification_session", "npm --prefix ui run mobile:verify-session")
    return commands


def _docker_install_attempt_line(session: MobileProofSession) -> str:
    if not session.docker_desktop_install_attempt_status:
        return "none"
    suffix = (
        f" (installer exit {session.docker_desktop_install_attempt_installer_exit_code})"
        if session.docker_desktop_install_attempt_installer_exit_code is not None
        else ""
    )
    if session.docker_desktop_install_attempt_detail:
        return f"{session.docker_desktop_install_attempt_status}: {session.docker_desktop_install_attempt_detail}{suffix}"
    return f"{session.docker_desktop_install_attempt_status}{suffix}"


def _dict_or_empty(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _artifact_digest(summary: dict, prefix: str) -> str:
    sha = summary.get(f"{prefix}_sha256")
    size = summary.get(f"{prefix}_size_bytes")
    if sha and size:
        return f"{size} bytes, sha256={sha}"
    if sha:
        return f"sha256={sha}"
    return "unavailable"


def _phone_proof_gate_detail(*, phone_pairing_available: bool) -> str:
    if not phone_pairing_available:
        return "Open Quick Start from the real phone over LAN, then leave the proof watcher running until it reports VERIFIED."
    return (
        "Open Quick Start from the real phone over LAN. If the phone is unpaired, "
        "use the live Owner Access/Quick Start pairing QR or link; saved proof-session "
        "pairing URLs are redacted by design."
    )


def _phone_pairing_handoff(*, pairing_context: dict, phone_verified: bool) -> str | None:
    has_pairing = bool(
        _string_or_none(pairing_context.get("redacted_pairing_url"))
        or _string_or_none(pairing_context.get("redacted_native_pairing_url"))
    )
    if not has_pairing:
        return None
    if phone_verified:
        return "Phone proof is already verified; the redacted pairing URLs are audit context only."
    return (
        "Use the live desktop Quick Start or Owner Access controls for a copyable "
        "pairing QR/link. The URLs in this saved proof session are redacted evidence "
        "and will not pair a fresh phone if copied directly."
    )


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None
