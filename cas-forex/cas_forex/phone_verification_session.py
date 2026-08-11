"""Owner-facing phone/PWA/APK verification session summary."""

from __future__ import annotations

import json
import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report


REPORT_KIND = "cas_forex_phone_verification_session"
DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "phone_verification_session" / "latest"
INSTALL_TEST_REQUIRED_ARTIFACT_IDS = ("android_debug_apk", "web_index", "pwa_manifest", "service_worker")
SIGNED_RELEASE_ARTIFACT_ID = "android_release_apk"
PHONE_VERIFICATION_SESSION_SCOPE = (
    "Phone verification session reports web/PWA/APK delivery, phone runtime, "
    "Android install/native-pairing, and Docker evidence. Live trading, broker, "
    "deposit, payout, and other money-moving actions remain governed by "
    "owner-authorized runtime gates, credentials, and broker state."
)
PHONE_VERIFICATION_PROOF_KEYS = (
    "phone_browser_observed",
    "phone_browser_verified",
    "phone_proof_fresh",
    "phone_proof_age_seconds",
    "phone_proof_expires_at",
    "phone_observation_fresh",
    "phone_observation_age_seconds",
    "phone_observation_expires_at",
    "phone_observation_local_runtime_only",
    "phone_observation_client_host_source",
    "phone_observation_effective_client_host",
    "apk_runtime_status",
    "apk_runtime_observed",
    "apk_runtime_verified",
    "apk_runtime_fresh",
    "apk_runtime_age_seconds",
    "apk_runtime_expires_at",
    "apk_install_pairing_verified",
    "apk_install_pairing_current_apk_sha256",
    "apk_install_pairing_apk_matches_current_artifact",
    "apk_install_pairing_attempt_status",
    "apk_install_pairing_attempt_fresh",
    "apk_install_pairing_attempt_age_seconds",
    "apk_install_pairing_attempt_message",
    "apk_install_pairing_attempt_apk_sha256",
    "apk_install_pairing_attempt_current_apk_sha256",
    "apk_install_pairing_attempt_apk_matches_current_artifact",
    "android_release_signing_ready",
    "android_release_signing_status",
    "android_release_signing_detail",
    "android_release_apk_exists",
    "android_release_apk_sha256",
    "paired_api_bases_reachable",
    "paired_api_bases_status",
    "paired_api_bases_detail",
    "android_device_ready",
    "android_device_count",
    "android_device_ready_count",
    "android_device_status",
    "android_device_detail",
    "android_adb_path",
    "docker_available",
    "docker_engine_status",
    "docker_engine_detail",
    "docker_server_version",
    "docker_wsl_checked",
    "docker_wsl_engine_available",
    "docker_wsl_warnings",
    "docker_desktop_winget_available",
    "docker_desktop_install_command",
    "docker_desktop_elevated_install_command",
    "docker_desktop_install_attempt_status",
    "docker_desktop_install_attempt_detail",
    "docker_desktop_install_attempt_returncode",
    "docker_desktop_install_attempt_installer_exit_code",
    "docker_desktop_install_attempt_generated_at",
    "docker_desktop_install_attempt_admin_elevation_required",
)


def build_phone_verification_session(*, workspace_root: str | Path = ".") -> dict[str, Any]:
    """Build a concise handoff packet from the latest mobile readiness evidence."""
    root = Path(workspace_root).resolve()
    readiness = latest_mobile_readiness_report(workspace_root=root)
    commands = readiness.get("verification_commands") if isinstance(readiness.get("verification_commands"), dict) else {}
    next_actions = [
        action for action in readiness.get("next_verification_actions", [])
        if isinstance(action, dict)
    ] if isinstance(readiness.get("next_verification_actions"), list) else []
    remaining_gates = [
        gate for gate in readiness.get("remaining_external_gates", [])
        if isinstance(gate, str) and gate.strip()
    ] if isinstance(readiness.get("remaining_external_gates"), list) else []
    release_bundle_readme = root / "evidence_runs" / "web_phone_release" / "latest" / "README.md"
    release_bundle_manifest = root / "evidence_runs" / "web_phone_release" / "latest" / "phone_release_bundle.json"
    release_bundle = _read_json_object(release_bundle_manifest)
    release_artifacts = _release_artifacts(release_bundle)
    release_runbook = _release_runbook(release_bundle)
    proof_state = _proof_state(readiness)
    phone_quick_start_url = _phone_quick_start_url(readiness, release_bundle, release_runbook)
    tested_quick_start_url = (
        _string_or_none(release_bundle.get("tested_quick_start_url"))
        or _string_or_none(release_runbook.get("tested_quick_start_url"))
        or _string_or_none(readiness.get("phone_quick_start_url"))
    )
    next_actions = _rewrite_phone_action_targets(next_actions, phone_quick_start_url)
    report = {
        "report_kind": REPORT_KIND,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": _session_status(readiness, remaining_gates),
        "summary": _summary(readiness, remaining_gates),
        "web_base": _string_or_none(readiness.get("web_base")),
        "tested_quick_start_url": tested_quick_start_url,
        "phone_quick_start_url": phone_quick_start_url,
        "package_ready_for_phone_install": bool(readiness.get("package_ready_for_phone_install")),
        "proof_state": proof_state,
        "owner_commands": _owner_commands(commands, readiness),
        "next_verification_actions": next_actions,
        "remaining_external_gates": remaining_gates,
        "release_bundle_readme": str(release_bundle_readme) if release_bundle_readme.exists() else None,
        "release_bundle_manifest": str(release_bundle_manifest) if release_bundle_manifest.exists() else None,
        "release_artifacts": release_artifacts,
        "release_artifact_summary": _release_artifact_summary(release_artifacts),
        "pairing_context": _pairing_context(release_runbook),
        "phone_verification_steps": _phone_verification_steps(release_runbook),
        "copied_debug_apk": _string_or_none(release_runbook.get("copied_debug_apk")),
        "apk_install_pairing_proof_path": _string_or_none(release_runbook.get("apk_install_pairing_proof_path")),
        "verification_scope": _string_or_none(release_runbook.get("verification_scope")),
        "latest_mobile_readiness_source": _string_or_none(readiness.get("source_path")),
        "claim_boundary": PHONE_VERIFICATION_SESSION_SCOPE,
    }
    report.update(proof_state)
    return redact_phone_verification_session(report)


def redact_phone_verification_session(value: Any) -> Any:
    """Return a token-redacted copy of a phone verification session payload."""
    return _redact(value)


def write_phone_verification_session(
    report: dict[str, Any],
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    """Write the session summary as JSON and Markdown."""
    root = Path(workspace_root).resolve()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "phone_verification_session.json"
    readme_path = out / "README.md"
    paths = {"json_path": str(json_path), "readme_path": str(readme_path)}
    payload = dict(report)
    payload["written_paths"] = paths
    payload = redact_phone_verification_session(payload)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    readme_path.write_text(render_phone_verification_session(payload), encoding="utf-8")
    return paths


def render_phone_verification_session(report: dict[str, Any]) -> str:
    """Render a terminal-friendly owner handoff."""
    proof = report.get("proof_state") if isinstance(report.get("proof_state"), dict) else {}
    commands = report.get("owner_commands") if isinstance(report.get("owner_commands"), dict) else {}
    actions = report.get("next_verification_actions") if isinstance(report.get("next_verification_actions"), list) else []
    gates = report.get("remaining_external_gates") if isinstance(report.get("remaining_external_gates"), list) else []
    artifacts = report.get("release_artifacts") if isinstance(report.get("release_artifacts"), list) else []
    pairing = report.get("pairing_context") if isinstance(report.get("pairing_context"), dict) else {}
    steps = report.get("phone_verification_steps") if isinstance(report.get("phone_verification_steps"), list) else []
    written_paths = report.get("written_paths") if isinstance(report.get("written_paths"), dict) else {}
    lines = [
        "# CAS Forex Phone Verification Session",
        "",
        f"Generated: `{report.get('generated_at') or 'unknown'}`",
        f"Status: `{report.get('status') or 'unknown'}`",
        f"Summary: {report.get('summary') or 'No summary available.'}",
        "",
        "## Current Targets",
        "",
        f"- Phone Quick Start URL: `{report.get('phone_quick_start_url') or 'unavailable'}`",
        f"- Tested Quick Start URL: `{report.get('tested_quick_start_url') or report.get('phone_quick_start_url') or 'unavailable'}`",
        f"- Release bundle README: `{report.get('release_bundle_readme') or 'unavailable'}`",
        f"- Release bundle manifest: `{report.get('release_bundle_manifest') or 'unavailable'}`",
        f"- Session JSON: `{written_paths.get('json_path') or 'unavailable'}`",
        f"- Session README: `{written_paths.get('readme_path') or 'unavailable'}`",
        "",
        "## Current Proof State",
        "",
        f"- Package ready: `{_bool_text(report.get('package_ready_for_phone_install'))}`",
        f"- Phone browser: `{_phone_state(proof)}`",
        f"- Phone proof freshness: `{_freshness_line(proof, 'phone_proof')}`",
        f"- Phone observation freshness: `{_freshness_line(proof, 'phone_observation')}`",
        f"- APK runtime: `{_apk_runtime_line(proof)}`",
        f"- Android device: `{proof.get('android_device_detail') or proof.get('android_device_status') or 'unknown'}`",
        f"- Android APK install-pair: `{_apk_install_pairing_line(proof)}`",
        f"- Android release signing: `{_android_release_signing_line(proof)}`",
        f"- Paired API bases: `{proof.get('paired_api_bases_detail') or proof.get('paired_api_bases_status') or 'unknown'}`",
        f"- Docker Engine: `{_docker_line(proof)}`",
        f"- Docker install command: `{proof.get('docker_desktop_install_command') or 'unavailable'}`",
        f"- Docker elevated install command: `{proof.get('docker_desktop_elevated_install_command') or commands.get('docker_desktop_install_elevated') or 'npm --prefix ui run mobile:docker-install-elevated'}`",
        f"- Docker install attempt: `{_docker_install_attempt_line(proof)}`",
        "",
        "## Pairing Context",
        "",
        f"- PWA/proxy API base: `{pairing.get('pwa_api_base') or 'unavailable'}`",
        f"- APK/direct API base: `{pairing.get('direct_api_base') or 'unavailable'}`",
        f"- Redacted PWA pairing URL: `{pairing.get('redacted_pairing_url') or 'unavailable'}`",
        f"- Redacted APK pairing URL: `{pairing.get('redacted_native_pairing_url') or 'unavailable'}`",
        f"- Copied debug APK: `{report.get('copied_debug_apk') or 'unavailable'}`",
        f"- APK install-pair proof path: `{report.get('apk_install_pairing_proof_path') or 'unavailable'}`",
        "",
        "## Release Artifacts",
        "",
    ]
    if artifacts:
        lines.extend([
            "| Artifact | Exists | Size bytes | SHA-256 | Copied to |",
            "| --- | --- | ---: | --- | --- |",
        ])
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            lines.append(
                "| "
                f"`{artifact.get('artifact_id') or 'unknown'}` | "
                f"`{_bool_text(artifact.get('exists'))}` | "
                f"{artifact.get('size_bytes') if artifact.get('size_bytes') is not None else ''} | "
                f"`{artifact.get('sha256') or ''}` | "
                f"`{artifact.get('copied_to') or ''}` |"
            )
    else:
        lines.append("No release artifact manifest is available yet.")
    lines.extend([
        "",
        "## Commands",
        "",
        f"- Combined proof session: `{commands.get('mobile_proof_session') or 'npm --prefix ui run mobile:proof-session'}`",
        f"- Start/reuse stack: `{commands.get('mobile_stack') or 'npm --prefix ui run mobile:stack'}`",
        f"- Refresh this session: `{commands.get('phone_verification_session') or 'npm --prefix ui run mobile:verify-session'}`",
        f"- Watch phone proof: `{commands.get('phone_proof_watcher') or 'npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing'}`",
        f"- List Android devices: `{commands.get('apk_device_list') or 'npm --prefix ui run mobile:apk:devices'}`",
        f"- Build debug and release APKs serially: `{commands.get('apk_build_all') or 'npm --prefix ui run mobile:apk:build-all'}`",
        f"- Build signed release APK: `{commands.get('apk_release_build') or 'npm --prefix ui run mobile:apk:release'}`",
        f"- Wait/install APK and launch pairing: `{commands.get('apk_wait_install_pair') or 'npm --prefix ui run mobile:apk:wait-install-pair'}`",
        f"- Immediate install and pairing: `{commands.get('apk_install_pair') or 'npm --prefix ui run mobile:apk:install-pair'}`",
        f"- Diagnose Docker Engine: `{commands.get('docker_engine_diagnose') or 'npm --prefix ui run mobile:docker-check'}`",
        f"- Install Docker Desktop: `{commands.get('docker_desktop_install') or 'npm --prefix ui run mobile:docker-install'}`",
        f"- Install Docker Desktop elevated: `{commands.get('docker_desktop_install_elevated') or 'npm --prefix ui run mobile:docker-install-elevated'}`",
        f"- Check Docker Engine: `{commands.get('docker_engine_check') or 'docker version --format \"{{.Server.Version}}\"'}`",
        f"- Build Docker image: `{commands.get('docker_compose_build') or 'docker compose build'}`",
        f"- Refresh release bundle: `{commands.get('release_bundle') or 'python scripts/build_web_phone_release_bundle.py --exit-code-on-failure'}`",
        "",
        "## Next Actions",
        "",
    ])
    if actions:
        for index, action in enumerate(actions, start=1):
            title = action.get("title") or action.get("action_id") or "Action"
            command = action.get("command") if isinstance(action.get("command"), str) else None
            target = action.get("target_url") if isinstance(action.get("target_url"), str) else None
            lines.append(f"{index}. {title}")
            if target:
                lines.append(f"   Target: `{target}`")
            if command:
                lines.append(f"   Command: `{command}`")
    else:
        lines.append("1. No next action is currently reported by mobile readiness.")
    if steps:
        lines.extend(["", "## Phone Verification Steps", ""])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")
    if gates:
        lines.extend(["", "## Remaining External Gates", ""])
        for gate in gates:
            lines.append(f"- {gate}")
    lines.extend(["", f"Scope: {report.get('claim_boundary') or PHONE_VERIFICATION_SESSION_SCOPE}", ""])
    return "\n".join(lines)


def _session_status(readiness: dict[str, Any], gates: list[str]) -> str:
    if not readiness.get("package_ready_for_phone_install"):
        return "package_not_ready"
    if not gates:
        return "verified"
    return "external_proof_pending"


def _summary(readiness: dict[str, Any], gates: list[str]) -> str:
    if not readiness.get("package_ready_for_phone_install"):
        return "Phone package evidence is not ready; refresh the release bundle or mobile stack."
    if not gates:
        return "Phone package and all current verification gates are green."
    return f"Phone package is ready; {len(gates)} external verification gate(s) remain."


def _proof_state(readiness: dict[str, Any]) -> dict[str, Any]:
    return {key: readiness.get(key) for key in PHONE_VERIFICATION_PROOF_KEYS if key in readiness}


def _owner_commands(commands: dict[str, Any], readiness: dict[str, Any]) -> dict[str, str]:
    web_base = _string_or_none(readiness.get("web_base"))
    suffix = f" -- --web-base {web_base}" if web_base else ""
    return {
        "mobile_stack": _command(commands.get("mobile_stack"), f"npm --prefix ui run mobile:stack{suffix}"),
        "mobile_proof_session": _command(commands.get("mobile_proof_session"), "npm --prefix ui run mobile:proof-session"),
        "phone_verification_session": _command(commands.get("phone_verification_session"), "npm --prefix ui run mobile:verify-session"),
        "mobile_final_verification": _command(commands.get("mobile_final_verification"), "npm --prefix ui run mobile:finish"),
        "mobile_final_verification_watch": _command(commands.get("mobile_final_verification_watch"), "npm --prefix ui run mobile:finish -- --watch-phone"),
        "mobile_final_verification_watch_all": _command(commands.get("mobile_final_verification_watch_all"), "npm --prefix ui run mobile:finish -- --watch-all"),
        "mobile_final_verification_watch_all_live_links": _command(
            commands.get("mobile_final_verification_watch_all_live_links"),
            "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links",
        ),
        "mobile_readiness": _command(commands.get("mobile_readiness"), f"npm --prefix ui run mobile:readiness{suffix}"),
        "phone_proof_watcher": _command(commands.get("phone_proof_watcher"), "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"),
        "apk_debug_build": _command(commands.get("apk_debug_build"), "npm --prefix ui run mobile:apk:debug"),
        "apk_build_all": _command(commands.get("apk_build_all"), "npm --prefix ui run mobile:apk:build-all"),
        "apk_release_build": _command(commands.get("apk_release_build"), "npm --prefix ui run mobile:apk:release"),
        "apk_device_list": _command(commands.get("apk_device_list"), "npm --prefix ui run mobile:apk:devices"),
        "apk_install_pair": _command(commands.get("apk_install_pair"), "npm --prefix ui run mobile:apk:install-pair"),
        "apk_wait_install_pair": _command(commands.get("apk_wait_install_pair"), "npm --prefix ui run mobile:apk:wait-install-pair"),
        "docker_engine_diagnose": _command(commands.get("docker_engine_diagnose"), "npm --prefix ui run mobile:docker-check"),
        "docker_desktop_install": _command(commands.get("docker_desktop_install"), "npm --prefix ui run mobile:docker-install"),
        "docker_desktop_install_elevated": _command(commands.get("docker_desktop_install_elevated"), "npm --prefix ui run mobile:docker-install-elevated"),
        "docker_engine_check": _command(commands.get("docker_engine_check"), 'docker version --format "{{.Server.Version}}"'),
        "docker_compose_build": _command(commands.get("docker_compose_build"), "docker compose build"),
        "release_bundle": _command(commands.get("release_bundle"), "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure"),
    }


def _command(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _release_artifacts(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = bundle.get("artifacts") if isinstance(bundle, dict) else None
    if not isinstance(artifacts, list):
        return []
    out: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        out.append({
            "artifact_id": _string_or_none(artifact.get("artifact_id")) or "unknown",
            "exists": bool(artifact.get("exists")),
            "size_bytes": artifact.get("size_bytes") if isinstance(artifact.get("size_bytes"), int) else None,
            "sha256": _string_or_none(artifact.get("sha256")),
            "copied_to": _string_or_none(artifact.get("copied_to")),
            "path": _string_or_none(artifact.get("path")),
        })
    return out


def _release_artifact_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {
        artifact.get("artifact_id"): artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("artifact_id"), str)
    }
    missing = [
        artifact_id for artifact_id in INSTALL_TEST_REQUIRED_ARTIFACT_IDS
        if not bool((by_id.get(artifact_id) or {}).get("exists"))
    ]
    apk = by_id.get("android_debug_apk") or {}
    release_apk = by_id.get(SIGNED_RELEASE_ARTIFACT_ID) or {}
    web_index = by_id.get("web_index") or {}
    service_worker = by_id.get("service_worker") or {}
    return {
        "all_required_present": not missing,
        "install_test_required_artifact_ids": list(INSTALL_TEST_REQUIRED_ARTIFACT_IDS),
        "missing_required_artifacts": missing,
        "android_debug_apk_sha256": _string_or_none(apk.get("sha256")),
        "android_debug_apk_size_bytes": apk.get("size_bytes") if isinstance(apk.get("size_bytes"), int) else None,
        "android_release_apk_present": bool(release_apk.get("exists")),
        "android_release_apk_sha256": _string_or_none(release_apk.get("sha256")),
        "android_release_apk_size_bytes": release_apk.get("size_bytes") if isinstance(release_apk.get("size_bytes"), int) else None,
        "web_index_sha256": _string_or_none(web_index.get("sha256")),
        "service_worker_sha256": _string_or_none(service_worker.get("sha256")),
    }


def _release_runbook(bundle: dict[str, Any]) -> dict[str, Any]:
    runbook = bundle.get("phone_verification_runbook") if isinstance(bundle, dict) else None
    return runbook if isinstance(runbook, dict) else {}


def _phone_quick_start_url(
    readiness: dict[str, Any],
    release_bundle: dict[str, Any],
    release_runbook: dict[str, Any],
) -> str | None:
    readiness_phone = _string_or_none(readiness.get("phone_quick_start_url"))
    readiness_web = _quick_start_url(_string_or_none(readiness.get("web_base")))
    for candidate in (readiness_phone, readiness_web):
        if candidate and _is_private_lan_url(candidate):
            return candidate

    candidates = (
        _string_or_none(release_bundle.get("phone_quick_start_url")),
        _string_or_none(release_runbook.get("phone_quick_start_url")),
        _strip_fragment(_string_or_none(
            (release_runbook.get("pairing_context") or {}).get("redacted_pairing_url")
            if isinstance(release_runbook.get("pairing_context"), dict)
            else None
        )),
        _quick_start_from_api_base(_string_or_none(
            (release_runbook.get("pairing_context") or {}).get("pwa_api_base")
            if isinstance(release_runbook.get("pairing_context"), dict)
            else None
        )),
        readiness_phone,
        readiness_web,
    )
    fallback: str | None = None
    for candidate in candidates:
        if not candidate:
            continue
        if fallback is None:
            fallback = candidate
        if not _is_loopback_url(candidate):
            return candidate
    return fallback


def _quick_start_url(web_base: str | None) -> str | None:
    base = str(web_base or "").strip().rstrip("/")
    if not base:
        return None
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"


def _rewrite_phone_action_targets(actions: list[dict[str, Any]], phone_quick_start_url: str | None) -> list[dict[str, Any]]:
    if not phone_quick_start_url:
        return actions
    rewritten: list[dict[str, Any]] = []
    for action in actions:
        item = dict(action)
        if item.get("action_id") == "phone_browser_proof":
            item["target_url"] = phone_quick_start_url
        rewritten.append(item)
    return rewritten


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


def _pairing_context(runbook: dict[str, Any]) -> dict[str, str | None]:
    pairing = runbook.get("pairing_context") if isinstance(runbook, dict) else None
    pairing = pairing if isinstance(pairing, dict) else {}
    return {
        "pwa_api_base": _string_or_none(pairing.get("pwa_api_base")),
        "direct_api_base": _string_or_none(pairing.get("direct_api_base")),
        "redacted_pairing_url": _string_or_none(pairing.get("redacted_pairing_url")),
        "redacted_native_pairing_url": _string_or_none(pairing.get("redacted_native_pairing_url")),
    }


def _phone_verification_steps(runbook: dict[str, Any]) -> list[str]:
    steps = runbook.get("steps") if isinstance(runbook, dict) else None
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, str) and step.strip()]


def _phone_state(proof: dict[str, Any]) -> str:
    if proof.get("phone_browser_verified"):
        return "verified"
    if proof.get("phone_browser_observed"):
        return "observed_local_only" if proof.get("phone_observation_local_runtime_only") else "observed_not_verified"
    return "not_observed"


def _apk_runtime_line(proof: dict[str, Any]) -> str:
    status = _string_or_none(proof.get("apk_runtime_status")) or "none"
    if status == "none":
        return "none"
    parts = [status]
    if proof.get("apk_runtime_fresh") is not None:
        parts.append("fresh" if proof.get("apk_runtime_fresh") else "stale")
    age = proof.get("apk_runtime_age_seconds")
    if isinstance(age, int):
        parts.append(_format_age(age))
    return ", ".join(parts)


def _apk_install_pairing_line(proof: dict[str, Any]) -> str:
    if proof.get("apk_install_pairing_verified"):
        return "verified"
    status = _string_or_none(proof.get("apk_install_pairing_attempt_status")) or "none"
    if status == "none":
        return "not_verified"
    parts = [status]
    parts.append("fresh" if proof.get("apk_install_pairing_attempt_fresh") else "stale")
    age = proof.get("apk_install_pairing_attempt_age_seconds")
    if isinstance(age, int):
        parts.append(_format_age(age))
    message = _string_or_none(proof.get("apk_install_pairing_attempt_message"))
    if message:
        parts.append(message)
    return ", ".join(parts)


def _android_release_signing_line(proof: dict[str, Any]) -> str:
    status = _string_or_none(proof.get("android_release_signing_status")) or "unknown"
    if proof.get("android_release_signing_ready"):
        apk = "release APK present" if proof.get("android_release_apk_exists") else "release APK build pending"
        digest = _string_or_none(proof.get("android_release_apk_sha256"))
        return f"ready, {apk}, {digest}" if digest else f"ready, {apk}"
    detail = _string_or_none(proof.get("android_release_signing_detail"))
    return f"{status}: {detail}" if detail else status


def _docker_line(proof: dict[str, Any]) -> str:
    if proof.get("docker_available"):
        version = _string_or_none(proof.get("docker_server_version"))
        return f"available, server {version}" if version else "available"
    status = _string_or_none(proof.get("docker_engine_status")) or "unknown"
    detail = _string_or_none(proof.get("docker_engine_detail"))
    install = _string_or_none(proof.get("docker_desktop_install_command"))
    suffix = f" Next: {install}" if install and install not in (detail or "") else ""
    return f"{status}: {detail}{suffix}" if detail else f"{status}{suffix}"


def _docker_install_attempt_line(proof: dict[str, Any]) -> str:
    status = _string_or_none(proof.get("docker_desktop_install_attempt_status"))
    if not status:
        return "none"
    detail = _string_or_none(proof.get("docker_desktop_install_attempt_detail"))
    installer_exit_code = proof.get("docker_desktop_install_attempt_installer_exit_code")
    suffix = f" (installer exit {installer_exit_code})" if isinstance(installer_exit_code, int) else ""
    return f"{status}: {detail}{suffix}" if detail else f"{status}{suffix}"


def _freshness_line(proof: dict[str, Any], prefix: str) -> str:
    fresh = proof.get(f"{prefix}_fresh")
    age = proof.get(f"{prefix}_age_seconds")
    expires = _string_or_none(proof.get(f"{prefix}_expires_at"))
    if fresh is None and age is None and not expires:
        return "none"
    parts = ["fresh" if fresh else "expired"]
    if isinstance(age, int):
        parts.append(_format_age(age))
    if expires:
        parts.append(f"{'expires' if fresh else 'expired'} at {expires}")
    return ", ".join(parts)


def _format_age(age_seconds: int) -> str:
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


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
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
