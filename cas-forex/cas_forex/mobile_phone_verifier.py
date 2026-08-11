"""Small phone-proof watcher for the CAS Forex mobile/PWA flow."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report


@dataclass(frozen=True)
class PhoneProofWatchStatus:
    status: str
    phone_browser_verified: bool
    phone_browser_observed: bool
    phone_quick_start_url: str | None
    tested_quick_start_url: str | None
    phone_proof_watcher_command: str | None
    mobile_readiness_command: str | None
    active_evidence_kind: str
    installed_mode_detected: bool
    effective_client_host: str | None
    client_host_source: str | None
    generated_at: str | None
    phone_proof_fresh: bool
    phone_proof_age_seconds: int | None
    phone_proof_expires_at: str | None
    phone_observation_fresh: bool
    phone_observation_age_seconds: int | None
    phone_observation_expires_at: str | None
    readiness_source_path: str | None
    summary: str
    next_steps: tuple[str, ...]


def phone_proof_watch_status(*, workspace_root: str | Path = ".") -> PhoneProofWatchStatus:
    """Read the latest app-facing mobile evidence and classify phone proof."""
    latest = latest_mobile_readiness_report(workspace_root=workspace_root)
    phone_verified = bool(latest.get("phone_browser_verified"))
    phone_observed = bool(latest.get("phone_browser_observed"))
    proof = latest.get("phone_proof") if isinstance(latest.get("phone_proof"), dict) else None
    observation = latest.get("phone_observation") if isinstance(latest.get("phone_observation"), dict) else None
    commands = latest.get("verification_commands") if isinstance(latest.get("verification_commands"), dict) else {}
    phone_quick_start_url = _string_or_none(latest.get("phone_quick_start_url"))
    tested_quick_start_url = _tested_quick_start_url(latest)
    phone_proof_watcher_command = _string_or_none(commands.get("phone_proof_watcher"))
    mobile_readiness_command = _string_or_none(commands.get("mobile_readiness"))
    phone_proof_fresh = bool(latest.get("phone_proof_fresh"))
    phone_observation_fresh = bool(latest.get("phone_observation_fresh"))
    phone_proof_age_seconds = _int_or_none(latest.get("phone_proof_age_seconds"))
    phone_observation_age_seconds = _int_or_none(latest.get("phone_observation_age_seconds"))
    phone_proof_expires_at = _string_or_none(latest.get("phone_proof_expires_at"))
    phone_observation_expires_at = _string_or_none(latest.get("phone_observation_expires_at"))
    if phone_verified and proof:
        evidence = proof
        active_evidence_kind = "verified_phone_proof"
    elif phone_observed and observation:
        evidence = observation
        active_evidence_kind = "phone_observation"
    elif observation and phone_observation_fresh:
        evidence = observation
        active_evidence_kind = "local_desktop_observation"
    elif proof and phone_proof_fresh:
        evidence = proof
        active_evidence_kind = "unverified_phone_proof"
    elif proof:
        evidence = proof
        active_evidence_kind = "stale_phone_proof"
    elif observation:
        evidence = observation
        active_evidence_kind = "stale_phone_observation"
    else:
        evidence = {}
        active_evidence_kind = "none"
    installed_mode = bool(
        latest.get("phone_proof_installed_mode")
        or latest.get("phone_observation_installed_mode")
        or evidence.get("installed_mode_detected")
    )
    effective_host = _string_or_none(
        evidence.get("effective_client_host")
        or latest.get("phone_observation_effective_client_host")
    )
    host_source = _string_or_none(
        evidence.get("client_host_source")
        or latest.get("phone_observation_client_host_source")
    )
    generated_at = _string_or_none(
        evidence.get("generated_at")
        or latest.get("phone_proof_generated_at")
        or latest.get("phone_observation_generated_at")
    )
    if phone_verified:
        status = "VERIFIED"
        summary = (
            f"Fresh verified phone browser/PWA proof recorded from {effective_host or 'phone'}"
            f" via {host_source or 'network evidence'}."
        )
        next_steps = (
            "Regenerate mobile readiness evidence so the release packet snapshots this proof.",
            "For the Android APK gate, run npm --prefix ui run mobile:apk:wait-install-pair, then plug in/unlock the phone and approve USB debugging.",
        )
    elif phone_observed:
        status = "OBSERVED_NOT_VERIFIED"
        summary = (
            "A fresh phone-like runtime was observed, but the network evidence is still "
            f"localhost/local-only{_age_suffix(phone_observation_age_seconds)}."
        )
        next_steps = (
            f"Open Quick Start from the real phone at {phone_quick_start_url or 'the LAN URL shown in Owner Access'}, not desktop emulation.",
            "Use Owner Access on the PC to show the phone pairing QR/link if the phone is not paired yet.",
        )
    elif observation and phone_observation_fresh:
        status = "LOCAL_DESKTOP_ONLY"
        device_class = _string_or_none(observation.get("device_class")) or "desktop_or_unknown"
        summary = (
            "Fresh runtime evidence exists, but it is "
            f"{device_class}/local-only and does not count as real-phone proof"
            f"{_age_suffix(phone_observation_age_seconds)}."
        )
        next_steps = (
            f"Open Quick Start from the real phone at {phone_quick_start_url or 'the LAN URL shown in Owner Access'}, not the PC browser.",
            "Use Owner Access on the PC to show the phone pairing QR/link if the phone is not paired yet.",
            "Leave this watcher running until it reports VERIFIED.",
        )
    elif proof and phone_proof_fresh:
        status = "UNVERIFIED_PHONE_PROOF"
        summary = (
            "Fresh phone proof evidence exists, but it does not satisfy the verified "
            f"real-phone criteria{_age_suffix(phone_proof_age_seconds)}."
        )
        next_steps = (
            f"Reopen Quick Start from the real phone at {phone_quick_start_url or 'the LAN URL shown in Owner Access'}.",
            "Leave this watcher running until fresh verified phone proof appears.",
        )
    elif proof or observation:
        status = "STALE"
        age = phone_proof_age_seconds if proof else phone_observation_age_seconds
        expires_at = phone_proof_expires_at if proof else phone_observation_expires_at
        summary = (
            f"Phone runtime evidence exists but is expired{_age_suffix(age)}"
            f"{_expiry_suffix(expires_at)}."
        )
        next_steps = (
            f"Reopen Quick Start from the real phone at {phone_quick_start_url or 'the LAN preview or direct API base'}.",
            "Leave this watcher running until fresh verified phone proof appears.",
        )
    else:
        status = "MISSING"
        summary = "No fresh phone-like Quick Start runtime proof is recorded."
        next_steps = (
            "Start the API and mobile preview, then open Owner Access on the PC and show the pairing token.",
            f"Scan the phone PWA pairing QR or open {phone_quick_start_url or 'the LAN URL shown in Owner Access'} from the phone.",
            "Open Quick Start on the phone and leave it open until this watcher reports VERIFIED.",
        )
    return PhoneProofWatchStatus(
        status=status,
        phone_browser_verified=phone_verified,
        phone_browser_observed=phone_observed,
        phone_quick_start_url=phone_quick_start_url,
        tested_quick_start_url=tested_quick_start_url,
        phone_proof_watcher_command=phone_proof_watcher_command,
        mobile_readiness_command=mobile_readiness_command,
        active_evidence_kind=active_evidence_kind,
        installed_mode_detected=installed_mode,
        effective_client_host=effective_host,
        client_host_source=host_source,
        generated_at=generated_at,
        phone_proof_fresh=phone_proof_fresh,
        phone_proof_age_seconds=phone_proof_age_seconds,
        phone_proof_expires_at=phone_proof_expires_at,
        phone_observation_fresh=phone_observation_fresh,
        phone_observation_age_seconds=phone_observation_age_seconds,
        phone_observation_expires_at=phone_observation_expires_at,
        readiness_source_path=_string_or_none(latest.get("source_path")),
        summary=summary,
        next_steps=next_steps,
    )


def wait_for_phone_proof(
    *,
    workspace_root: str | Path = ".",
    timeout_seconds: float = 180.0,
    poll_seconds: float = 2.0,
    status_reader: Callable[[], PhoneProofWatchStatus] | None = None,
) -> PhoneProofWatchStatus:
    """Wait until verified phone proof appears, then return the final status."""
    read_status = status_reader or (lambda: phone_proof_watch_status(workspace_root=workspace_root))
    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    final_status = read_status()
    while not final_status.phone_browser_verified and time.monotonic() < deadline:
        time.sleep(max(poll_seconds, 0.1))
        final_status = read_status()
    return final_status


def phone_proof_watch_status_to_dict(status: PhoneProofWatchStatus) -> dict:
    return asdict(status)


def phone_proof_watch_status_to_json(status: PhoneProofWatchStatus) -> str:
    return json.dumps(phone_proof_watch_status_to_dict(status), indent=2)


def render_phone_proof_watch_status(status: PhoneProofWatchStatus) -> str:
    marker = "[OK]" if status.phone_browser_verified else f"[{status.status}]"
    lines = [
        "CAS Forex phone proof watcher",
        f"{marker} {status.summary}",
        "",
        f"Phone browser observed: {str(status.phone_browser_observed).lower()}",
        f"Phone browser verified: {str(status.phone_browser_verified).lower()}",
        f"Phone Quick Start URL: {status.phone_quick_start_url or 'unknown'}",
        f"Tested Quick Start URL: {status.tested_quick_start_url or status.phone_quick_start_url or 'unknown'}",
        f"Active evidence: {status.active_evidence_kind}",
        f"Phone proof freshness: {_freshness_label(status.phone_proof_fresh, status.phone_proof_age_seconds, status.phone_proof_expires_at)}",
        f"Phone observation freshness: {_freshness_label(status.phone_observation_fresh, status.phone_observation_age_seconds, status.phone_observation_expires_at)}",
        f"Installed app mode detected: {str(status.installed_mode_detected).lower()}",
        f"Client host: {status.effective_client_host or 'unknown'}",
        f"Client host source: {status.client_host_source or 'unknown'}",
        f"Generated at: {status.generated_at or 'none'}",
        f"Readiness source: {status.readiness_source_path or 'none'}",
    ]
    if status.phone_proof_watcher_command or status.mobile_readiness_command:
        lines.extend([
            "",
            "Commands:",
            f"- Watch phone proof: {status.phone_proof_watcher_command or 'npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing'}",
            f"- Refresh readiness: {status.mobile_readiness_command or 'npm --prefix ui run mobile:readiness'}",
        ])
    if status.next_steps:
        lines.extend(["", "Next steps:"])
        lines.extend(f"- {step}" for step in status.next_steps)
    return "\n".join(lines)


def _tested_quick_start_url(latest: dict) -> str | None:
    source = _string_or_none(latest.get("web_base"))
    if not source:
        return _string_or_none(latest.get("phone_quick_start_url"))
    base = source.rstrip("/")
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _freshness_label(is_fresh: bool, age_seconds: int | None, expires_at: str | None) -> str:
    if age_seconds is None and not expires_at:
        return "none"
    state = "fresh" if is_fresh else "expired"
    parts = [state]
    age = _format_age(age_seconds)
    if age:
        parts.append(age)
    if expires_at:
        parts.append(f"{'expires' if is_fresh else 'expired'} at {expires_at}")
    return ", ".join(parts)


def _age_suffix(age_seconds: int | None) -> str:
    age = _format_age(age_seconds)
    return f" ({age})" if age else ""


def _expiry_suffix(expires_at: str | None) -> str:
    return f"; expired at {expires_at}" if expires_at else ""


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
