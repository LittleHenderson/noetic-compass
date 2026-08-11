"""Final owner-facing mobile verification handoff for CAS Forex."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cas_forex.mobile_proof_session import (
    MobileProofSession,
    build_mobile_proof_session,
    mobile_proof_session_to_dict,
)
from cas_forex.phone_verification_session import redact_phone_verification_session


REPORT_KIND = "cas_forex_mobile_final_verification"
DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "mobile_final_verification" / "latest"


@dataclass(frozen=True)
class MobileFinalVerificationReport:
    report_kind: str
    generated_at: str
    status: str
    summary: str
    package_ready_for_phone_install: bool
    phone_quick_start_url: str | None
    phone_browser_verified: bool
    apk_install_pairing_verified: bool
    docker_available: bool
    next_owner_step: str
    owner_commands: dict[str, str]
    gates: tuple[dict[str, Any], ...]
    remaining_external_gates: tuple[str, ...]
    proof_session: dict[str, Any]


def build_mobile_final_verification(
    *,
    workspace_root: str | Path = ".",
    watch_phone: bool = False,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 2.0,
) -> MobileFinalVerificationReport:
    """Return the final phone/APK/Docker verification state and next action."""
    root = Path(workspace_root).resolve()
    proof_session = build_mobile_proof_session(
        workspace_root=root,
        watch_phone=watch_phone,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    payload = mobile_proof_session_to_dict(proof_session)
    commands = _owner_commands(proof_session)
    gates = tuple(_gate_dict(gate) for gate in payload.get("gates", ()) if isinstance(gate, dict))
    remaining = tuple(
        str(gate.get("title") or gate.get("gate_id"))
        for gate in gates
        if gate and not bool(gate.get("satisfied"))
    )
    status = _status(proof_session=proof_session, remaining=remaining)
    summary = _summary(proof_session=proof_session, remaining=remaining)
    return MobileFinalVerificationReport(
        report_kind=REPORT_KIND,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        summary=summary,
        package_ready_for_phone_install=proof_session.package_ready_for_phone_install,
        phone_quick_start_url=proof_session.phone_quick_start_url,
        phone_browser_verified=proof_session.phone_browser_verified,
        apk_install_pairing_verified=proof_session.apk_install_pairing_verified,
        docker_available=proof_session.docker_available,
        next_owner_step=_next_owner_step(proof_session=proof_session, commands=commands),
        owner_commands=commands,
        gates=gates,
        remaining_external_gates=remaining,
        proof_session=payload,
    )


def mobile_final_verification_to_dict(report: MobileFinalVerificationReport) -> dict[str, Any]:
    payload = _json_compatible(asdict(report))
    return redact_phone_verification_session(payload)


def mobile_final_verification_to_json(report: MobileFinalVerificationReport) -> str:
    return json.dumps(mobile_final_verification_to_dict(report), indent=2, sort_keys=True)


def write_mobile_final_verification(
    report: MobileFinalVerificationReport,
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    """Write redacted final verification JSON and README artifacts."""
    root = Path(workspace_root).resolve()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "mobile_final_verification.json"
    readme_path = out / "README.md"
    payload = mobile_final_verification_to_dict(report)
    paths = {"json_path": str(json_path), "readme_path": str(readme_path)}
    payload["written_paths"] = paths
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    readme_path.write_text(render_mobile_final_verification(report), encoding="utf-8")
    return paths


def render_mobile_final_verification(report: MobileFinalVerificationReport) -> str:
    safe_payload = mobile_final_verification_to_dict(report)
    safe_gates = [gate for gate in safe_payload.get("gates", []) if isinstance(gate, dict)]
    lines = [
        "CAS Forex final mobile verification",
        f"Status: {report.status}",
        f"Summary: {report.summary}",
        f"Phone Quick Start URL: {report.phone_quick_start_url or 'unavailable'}",
        f"Package ready: {_yes_no(report.package_ready_for_phone_install)}",
        f"Phone browser verified: {_yes_no(report.phone_browser_verified)}",
        f"APK install/native pairing verified: {_yes_no(report.apk_install_pairing_verified)}",
        f"Docker available: {_yes_no(report.docker_available)}",
        "",
        f"Next owner step: {report.next_owner_step}",
    ]
    if safe_gates:
        lines.extend(["", "Final gates:"])
        for gate in safe_gates:
            marker = "[OK]" if gate.get("satisfied") else "[PENDING]"
            title = gate.get("title") or gate.get("gate_id") or "Gate"
            lines.append(f"- {marker} {title}: {gate.get('detail') or 'unavailable'}")
            if gate.get("target_url"):
                lines.append(f"  Target: {gate.get('target_url')}")
            if gate.get("command"):
                lines.append(f"  Command: {gate.get('command')}")
    commands = report.owner_commands
    lines.extend(
        [
            "",
            "Owner commands:",
            f"- Final verification: {commands.get('mobile_final_verification') or 'npm --prefix ui run mobile:finish'}",
            f"- Watch all final gates: {commands.get('mobile_final_verification_watch_all') or 'npm --prefix ui run mobile:finish -- --watch-all'}",
            f"- Watch all final gates with live links: {commands.get('mobile_final_verification_watch_all_live_links') or 'npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links'}",
            f"- Watch phone proof: {commands.get('phone_proof_watcher') or 'npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing'}",
            f"- APK wait/install-pair: {commands.get('apk_wait_install_pair') or 'npm --prefix ui run mobile:apk:wait-install-pair'}",
            f"- Refresh readiness: {commands.get('mobile_readiness') or 'npm --prefix ui run mobile:readiness'}",
            f"- Refresh release bundle: {commands.get('release_bundle') or 'python scripts/build_web_phone_release_bundle.py --exit-code-on-failure'}",
        ]
    )
    return "\n".join(lines)


def _owner_commands(proof_session: MobileProofSession) -> dict[str, str]:
    commands = dict(proof_session.owner_commands or {})
    commands.setdefault("mobile_final_verification", "npm --prefix ui run mobile:finish")
    commands.setdefault("mobile_final_verification_watch", "npm --prefix ui run mobile:finish -- --watch-phone")
    commands.setdefault("mobile_final_verification_watch_all", "npm --prefix ui run mobile:finish -- --watch-all")
    commands.setdefault(
        "mobile_final_verification_watch_all_live_links",
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links",
    )
    commands.setdefault("mobile_readiness", "npm --prefix ui run mobile:readiness")
    commands.setdefault("release_bundle", "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure")
    commands.setdefault("phone_proof_watcher", "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing")
    commands.setdefault("apk_wait_install_pair", "npm --prefix ui run mobile:apk:wait-install-pair")
    return commands


def _gate_dict(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": gate.get("gate_id"),
        "title": gate.get("title"),
        "satisfied": bool(gate.get("satisfied")),
        "command": gate.get("command") if isinstance(gate.get("command"), str) else None,
        "target_url": gate.get("target_url") if isinstance(gate.get("target_url"), str) else None,
        "detail": gate.get("detail") if isinstance(gate.get("detail"), str) else None,
    }


def _status(*, proof_session: MobileProofSession, remaining: tuple[str, ...]) -> str:
    if not proof_session.package_ready_for_phone_install:
        return "package_not_ready"
    if not remaining:
        return "verified"
    return "external_proof_pending"


def _summary(*, proof_session: MobileProofSession, remaining: tuple[str, ...]) -> str:
    if not proof_session.package_ready_for_phone_install:
        return "Phone package is not ready; refresh the release bundle before final device proof."
    if not remaining:
        return "Final mobile verification is complete."
    return f"Phone package is ready; {len(remaining)} final external gate(s) remain."


def _next_owner_step(*, proof_session: MobileProofSession, commands: dict[str, str]) -> str:
    if not proof_session.package_ready_for_phone_install:
        return commands.get("release_bundle") or "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure"
    if not proof_session.phone_browser_verified:
        target = proof_session.phone_quick_start_url or "the Quick Start LAN URL"
        command = commands.get("phone_proof_watcher") or "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
        return f"Open {target} on the real phone, then run `{command}`."
    if not proof_session.apk_install_pairing_verified:
        command = commands.get("apk_wait_install_pair") or "npm --prefix ui run mobile:apk:wait-install-pair"
        return f"Attach/unlock/authorize the Android phone, then run `{command}`."
    if not proof_session.docker_available:
        command = commands.get("docker_engine_diagnose") or "npm --prefix ui run mobile:docker-check"
        return f"Start or install Docker Desktop, then run `{command}`."
    return "All final mobile gates are verified; refresh the verification plan for the final evidence packet."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _json_compatible(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_compatible(item) for item in value]
    if isinstance(value, list):
        return [_json_compatible(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_compatible(item) for key, item in value.items()}
    return value
