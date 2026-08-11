"""Build a single owner-facing web/PWA/APK/Docker verification plan."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cas_forex.mobile_proof_session import build_mobile_proof_session, mobile_proof_session_to_dict
from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report
from cas_forex.phone_verification_session import (
    build_phone_verification_session,
    redact_phone_verification_session,
)


REPORT_KIND = "cas_forex_mobile_verification_plan"
DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "mobile_verification_plan" / "latest"
CLAIM_BOUNDARY = (
    "Mobile verification plan reports web/PWA/APK delivery, real-phone proof, Android install/native-pairing, "
    "and Docker evidence. Live trading, broker, deposit, payout, and other money-moving actions remain governed "
    "by owner-authorized runtime gates, credentials, and broker state."
)


def build_mobile_verification_plan(*, workspace_root: str | Path = ".") -> dict[str, Any]:
    """Return one redacted checklist shared by chat, API, Quick Start, and CLI."""
    root = Path(workspace_root).resolve()
    readiness = _dict_or_empty(latest_mobile_readiness_report(workspace_root=root))
    proof_session = _dict_or_empty(mobile_proof_session_to_dict(build_mobile_proof_session(workspace_root=root)))
    verification_session = _dict_or_empty(build_phone_verification_session(workspace_root=root))
    owner_commands = _owner_commands(readiness, proof_session, verification_session)
    next_actions = _next_actions(readiness, verification_session)
    remaining_gates = _remaining_gates(readiness, proof_session, verification_session)
    phone_quick_start_url = _first_string(
        readiness.get("phone_quick_start_url"),
        proof_session.get("phone_quick_start_url"),
        verification_session.get("phone_quick_start_url"),
    )
    plan = {
        "report_kind": REPORT_KIND,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": _first_string(proof_session.get("status"), verification_session.get("status"), readiness.get("status")) or "unknown",
        "summary": _first_string(proof_session.get("summary"), verification_session.get("summary"), readiness.get("summary")) or "",
        "package_ready_for_phone_install": bool(readiness.get("package_ready_for_phone_install")),
        "phone_browser_verified": bool(readiness.get("phone_browser_verified")),
        "physical_phone_verified": bool(readiness.get("physical_phone_verified")),
        "apk_install_pairing_verified": bool(readiness.get("apk_install_pairing_verified")),
        "apk_install_pairing_attempt_status": _first_string(readiness.get("apk_install_pairing_attempt_status")),
        "docker_available": bool(readiness.get("docker_available")),
        "docker_engine_status": _first_string(readiness.get("docker_engine_status")),
        "docker_desktop_install_attempt_status": _first_string(readiness.get("docker_desktop_install_attempt_status")),
        "phone_quick_start_url": phone_quick_start_url,
        "phone_proof_target_url": _first_string(proof_session.get("phone_proof_target_url"), phone_quick_start_url),
        "remaining_external_gates": remaining_gates,
        "next_verification_actions": next_actions,
        "owner_commands": owner_commands,
        "source_paths": {
            "readiness": readiness.get("source_path"),
            "phone_verification_session": verification_session.get("source_path"),
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    plan["text"] = render_mobile_verification_plan(plan)
    return redact_phone_verification_session(plan)


def mobile_verification_plan_to_json(plan: dict[str, Any]) -> str:
    return json.dumps(redact_phone_verification_session(plan), indent=2, sort_keys=True)


def write_mobile_verification_plan(
    plan: dict[str, Any],
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    """Write the current verification plan as redacted JSON and text."""
    root = Path(workspace_root).resolve()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "mobile_verification_plan.json"
    readme_path = out / "README.md"
    paths = {"json_path": str(json_path), "readme_path": str(readme_path)}
    payload = dict(plan)
    payload["written_paths"] = paths
    payload = redact_phone_verification_session(payload)
    json_path.write_text(mobile_verification_plan_to_json(payload), encoding="utf-8")
    readme_path.write_text(render_mobile_verification_plan(payload), encoding="utf-8")
    return paths


def render_mobile_verification_plan(plan: dict[str, Any]) -> str:
    """Render a compact copy/paste plan."""
    owner_commands = _dict_or_empty(plan.get("owner_commands"))
    lines = [
        "CAS Forex mobile/web verification plan",
        f"Status: {plan.get('status') or 'unknown'}",
        f"Summary: {plan.get('summary') or 'unavailable'}",
        f"Package ready: {_yes_no(plan.get('package_ready_for_phone_install'))}",
        f"Phone browser verified: {_yes_no(plan.get('phone_browser_verified'))}",
        f"Android APK/native pairing verified: {_yes_no(plan.get('apk_install_pairing_verified'))}",
        f"APK last attempt: {plan.get('apk_install_pairing_attempt_status') or 'none'}",
        f"Docker Engine available: {_yes_no(plan.get('docker_available'))}",
        f"Docker Engine status: {plan.get('docker_engine_status') or 'unknown'}",
        f"Docker install attempt: {plan.get('docker_desktop_install_attempt_status') or 'none'}",
        f"Phone Quick Start URL: {plan.get('phone_quick_start_url') or 'unavailable'}",
        f"Phone proof target URL: {plan.get('phone_proof_target_url') or plan.get('phone_quick_start_url') or 'unavailable'}",
    ]
    remaining = [str(item) for item in (plan.get("remaining_external_gates") or []) if str(item).strip()]
    if remaining:
        lines.extend(["", "Remaining gates:"])
        lines.extend(f"{index}. {gate}" for index, gate in enumerate(remaining, start=1))
    actions = [action for action in (plan.get("next_verification_actions") or []) if isinstance(action, dict)]
    if actions:
        lines.extend(["", "Next verification actions:"])
        for index, action in enumerate(actions, start=1):
            lines.append(f"{index}. {action.get('title') or action.get('action_id') or 'Action'}")
            if action.get("target_url"):
                lines.append(f"   Target: {action.get('target_url')}")
            if action.get("command"):
                lines.append(f"   Command: {action.get('command')}")
            secondary = [str(command) for command in (action.get("secondary_commands") or []) if str(command).strip()]
            if secondary:
                lines.append("   Secondary commands:")
                lines.extend(f"   - {command}" for command in secondary)
    lines.extend(
        [
            "",
            "Owner commands:",
            f"- Final verification: {owner_commands.get('mobile_final_verification') or 'npm --prefix ui run mobile:finish'}",
            f"- Watch all final gates: {owner_commands.get('mobile_final_verification_watch_all') or 'npm --prefix ui run mobile:finish -- --watch-all'}",
            f"- Watch all final gates with live links: {owner_commands.get('mobile_final_verification_watch_all_live_links') or 'npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links'}",
            f"- Verification plan: {owner_commands.get('mobile_verification_plan') or 'npm --prefix ui run mobile:verification-plan'}",
            f"- Proof session: {owner_commands.get('mobile_proof_session') or 'npm --prefix ui run mobile:proof-session'}",
            f"- Verification session: {owner_commands.get('phone_verification_session') or 'npm --prefix ui run mobile:verify-session'}",
            f"- Phone proof watcher: {owner_commands.get('phone_proof_watcher') or 'npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing'}",
            f"- Readiness refresh: {owner_commands.get('mobile_readiness') or 'npm --prefix ui run mobile:readiness'}",
            f"- Android device list: {owner_commands.get('apk_device_list') or 'npm --prefix ui run mobile:apk:devices'}",
            f"- APK wait/install-pair: {owner_commands.get('apk_wait_install_pair') or 'npm --prefix ui run mobile:apk:wait-install-pair'}",
            f"- Docker diagnosis: {owner_commands.get('docker_engine_diagnose') or 'npm --prefix ui run mobile:docker-check'}",
            f"- Docker install: {owner_commands.get('docker_desktop_install') or 'npm --prefix ui run mobile:docker-install'}",
            f"- Docker elevated install: {owner_commands.get('docker_desktop_install_elevated') or 'npm --prefix ui run mobile:docker-install-elevated'}",
            "",
            f"Scope: {plan.get('claim_boundary') or CLAIM_BOUNDARY}",
        ]
    )
    return "\n".join(lines)


def _owner_commands(*payloads: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for payload in payloads:
        commands = payload.get("verification_commands") or payload.get("owner_commands")
        if isinstance(commands, dict):
            out.update({str(key): str(value) for key, value in commands.items() if isinstance(value, str) and value.strip()})
    out.setdefault("mobile_proof_session", "npm --prefix ui run mobile:proof-session")
    out.setdefault("mobile_final_verification", "npm --prefix ui run mobile:finish")
    out.setdefault("mobile_final_verification_watch", "npm --prefix ui run mobile:finish -- --watch-phone")
    out.setdefault("mobile_final_verification_watch_all", "npm --prefix ui run mobile:finish -- --watch-all")
    out.setdefault(
        "mobile_final_verification_watch_all_live_links",
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links",
    )
    out.setdefault("mobile_verification_plan", "npm --prefix ui run mobile:verification-plan")
    out.setdefault("phone_verification_session", "npm --prefix ui run mobile:verify-session")
    out.setdefault("phone_proof_watcher", "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing")
    out.setdefault("mobile_readiness", "npm --prefix ui run mobile:readiness")
    out.setdefault("apk_device_list", "npm --prefix ui run mobile:apk:devices")
    out.setdefault("apk_wait_install_pair", "npm --prefix ui run mobile:apk:wait-install-pair")
    out.setdefault("docker_engine_diagnose", "npm --prefix ui run mobile:docker-check")
    out.setdefault("docker_desktop_install", "npm --prefix ui run mobile:docker-install")
    out.setdefault("docker_desktop_install_elevated", "npm --prefix ui run mobile:docker-install-elevated")
    out.setdefault("docker_engine_check", 'docker version --format "{{.Server.Version}}"')
    out.setdefault("docker_compose_build", "docker compose build")
    return out


def _next_actions(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    for payload in payloads:
        actions = payload.get("next_verification_actions")
        if isinstance(actions, list) and actions:
            return [dict(action) for action in actions if isinstance(action, dict)]
    return []


def _remaining_gates(*payloads: dict[str, Any]) -> list[str]:
    for payload in payloads:
        gates = payload.get("remaining_external_gates")
        if isinstance(gates, (list, tuple)) and gates:
            return [str(gate) for gate in gates if str(gate).strip()]
    return []


def _first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _dict_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"
