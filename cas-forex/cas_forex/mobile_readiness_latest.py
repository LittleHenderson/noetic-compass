"""Read the latest CAS Forex mobile readiness evidence for the app UI."""

from __future__ import annotations

import json
import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from cas_forex.docker_desktop_install import elevated_install_command_string
from cas_forex.mobile_apk_artifact import (
    android_release_signing_status,
    debug_apk_artifact_metadata,
    release_apk_artifact_metadata,
)
from cas_forex.mobile_apk_proof import (
    latest_android_apk_install_pairing_attempt,
    latest_android_apk_install_pairing_proof,
)
from cas_forex.mobile_phone_proof import (
    latest_apk_runtime_observation,
    latest_phone_runtime_observation,
    latest_phone_runtime_proof,
)


REPORT_KIND = "cas_forex_mobile_readiness_latest"
MOBILE_READINESS_SCOPE = (
    "Mobile readiness reports web/PWA/APK package, device, and Docker evidence. "
    "Live trading, broker, deposit, payout, and other money-moving actions remain "
    "governed by owner-authorized runtime gates, credentials, and broker state."
)
LATEST_CANDIDATES = (
    Path("evidence_runs") / "mobile_stack" / "latest" / "mobile_release_readiness.json",
    Path("evidence_runs") / "web_phone_release" / "latest" / "mobile_release_readiness.json",
)


def latest_mobile_readiness_report(*, workspace_root: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    phone_proof = latest_phone_runtime_proof(workspace_root=root)
    phone_observation = latest_phone_runtime_observation(workspace_root=root)
    apk_runtime_observation = latest_apk_runtime_observation(workspace_root=root)
    apk_artifact = debug_apk_artifact_metadata(workspace_root=root)
    apk_install_pairing_proof = _current_apk_record(
        latest_android_apk_install_pairing_proof(workspace_root=root),
        apk_artifact,
    )
    apk_install_pairing_attempt = _current_apk_record(
        latest_android_apk_install_pairing_attempt(workspace_root=root),
        apk_artifact,
    )
    apk_install_pairing_verified = _android_apk_install_pairing_verified(apk_install_pairing_proof)
    release_apk_artifact = release_apk_artifact_metadata(workspace_root=root)
    release_signing = android_release_signing_status(workspace_root=root)
    latest_candidate = _latest_candidate(root)
    if latest_candidate:
        path = latest_candidate["path"]
        payload = latest_candidate.get("payload")
        if latest_candidate.get("status") == "EVIDENCE_UNREADABLE":
            return {
                "report_kind": REPORT_KIND,
                "status": "EVIDENCE_UNREADABLE",
                "source_path": str(path),
                "web_base": None,
                "phone_quick_start_url": None,
                "verification_commands": _verification_commands(None),
                "next_verification_actions": _next_verification_actions(
                    web_base=None,
                    package_ready=False,
                    phone_browser_verified=_phone_browser_verified(phone_proof),
                    phone_browser_observed=_phone_browser_observed(phone_observation),
                    physical_phone_verified=apk_install_pairing_verified,
                    docker_available=False,
                ),
                "package_ready_for_phone_install": False,
                "physical_phone_verified": apk_install_pairing_verified,
                "phone_browser_observed": _phone_browser_observed(phone_observation),
                "phone_browser_verified": _phone_browser_verified(phone_proof),
                "phone_proof_generated_at": phone_proof.get("generated_at") if phone_proof else None,
                **_phone_freshness_fields("phone_proof", phone_proof),
                "phone_proof_device_class": phone_proof.get("device_class") if phone_proof else None,
                "phone_proof_installed_mode": bool(phone_proof.get("installed_mode_detected")) if phone_proof else False,
                **_phone_api_base_fields("phone_proof", phone_proof),
                "phone_proof": phone_proof,
                "phone_observation_generated_at": phone_observation.get("generated_at") if phone_observation else None,
                **_phone_freshness_fields("phone_observation", phone_observation),
                "phone_observation_device_class": phone_observation.get("device_class") if phone_observation else None,
                "phone_observation_installed_mode": bool(phone_observation.get("installed_mode_detected")) if phone_observation else False,
                "phone_observation_local_runtime_only": bool(phone_observation.get("local_runtime_only")) if phone_observation else False,
                "phone_observation_client_host_source": phone_observation.get("client_host_source") if phone_observation else None,
                "phone_observation_effective_client_host": phone_observation.get("effective_client_host") if phone_observation else None,
                **_phone_api_base_fields("phone_observation", phone_observation),
                "phone_observation": phone_observation,
                "apk_runtime_observation": apk_runtime_observation,
                **_apk_runtime_fields(apk_runtime_observation),
                "apk_install_pairing_proof": apk_install_pairing_proof,
                **_apk_proof_fields(apk_install_pairing_proof, apk_install_pairing_verified),
                "apk_install_pairing_attempt": apk_install_pairing_attempt,
                **_apk_attempt_fields(apk_install_pairing_attempt),
                "apk_artifact": apk_artifact,
                "release_apk_artifact": release_apk_artifact,
                "android_release_signing": release_signing,
                **_android_release_signing_fields(release_signing),
                **_paired_api_base_fields(None, []),
                **_android_device_probe_fields([]),
                **_docker_check_fields([]),
                "docker_available": False,
                "summary": latest_candidate["summary"],
                "remaining_external_gates": [
                    "Regenerate mobile readiness evidence with python scripts/run_mobile_stack_readiness.py.",
                ],
                "checks": [],
                "claim_boundary": MOBILE_READINESS_SCOPE,
            }
        if latest_candidate.get("status") == "EVIDENCE_MALFORMED" or not isinstance(payload, dict):
            return _missing_or_malformed(path, latest_candidate["summary"], root)
        payload = _redact(payload)
        phone_verified = _phone_browser_verified(phone_proof)
        phone_observed = _phone_browser_observed(phone_observation)
        physical_phone_verified = bool(payload.get("physical_phone_verified")) or apk_install_pairing_verified
        remaining_gates = _current_remaining_gates(
            payload.get("remaining_external_gates"),
            phone_verified=phone_verified,
            phone_observed=phone_observed,
            physical_phone_verified=physical_phone_verified,
        )
        web_base = _string_or_none(payload.get("web_base"))
        phone_quick_start_url = _phone_reachable_quick_start_url(payload, web_base)
        checks = _current_checks(
            payload.get("checks"),
            phone_verified=phone_verified,
            phone_observed=phone_observed,
            phone_proof=phone_proof,
            phone_observation=phone_observation,
            apk_install_pairing_proof=apk_install_pairing_proof,
            apk_install_pairing_attempt=apk_install_pairing_attempt,
            apk_runtime_observation=apk_runtime_observation,
            android_release_signing=release_signing,
        )
        return {
            "report_kind": REPORT_KIND,
            "status": "LATEST_EVIDENCE_FOUND",
            "source_path": str(path),
            "generated_at": payload.get("generated_at"),
            "web_base": web_base,
            "phone_quick_start_url": phone_quick_start_url,
            "verification_commands": _verification_commands(web_base),
            "next_verification_actions": _next_verification_actions(
                web_base=web_base,
                phone_quick_start_url=phone_quick_start_url,
                package_ready=bool(payload.get("package_ready_for_phone_install")),
                phone_browser_verified=phone_verified,
                phone_browser_observed=phone_observed,
                physical_phone_verified=physical_phone_verified,
                docker_available=bool(payload.get("docker_available")),
            ),
            "package_ready_for_phone_install": bool(payload.get("package_ready_for_phone_install")),
            "physical_phone_verified": physical_phone_verified,
            "phone_browser_observed": phone_observed,
            "phone_browser_verified": phone_verified,
            "phone_proof_generated_at": phone_proof.get("generated_at") if phone_proof else None,
            **_phone_freshness_fields("phone_proof", phone_proof),
            "phone_proof_device_class": phone_proof.get("device_class") if phone_proof else None,
            "phone_proof_installed_mode": bool(phone_proof.get("installed_mode_detected")) if phone_proof else False,
            **_phone_api_base_fields("phone_proof", phone_proof),
            "phone_proof": phone_proof,
            "phone_observation_generated_at": phone_observation.get("generated_at") if phone_observation else None,
            **_phone_freshness_fields("phone_observation", phone_observation),
            "phone_observation_device_class": phone_observation.get("device_class") if phone_observation else None,
            "phone_observation_installed_mode": bool(phone_observation.get("installed_mode_detected")) if phone_observation else False,
            "phone_observation_local_runtime_only": bool(phone_observation.get("local_runtime_only")) if phone_observation else False,
            "phone_observation_client_host_source": phone_observation.get("client_host_source") if phone_observation else None,
            "phone_observation_effective_client_host": phone_observation.get("effective_client_host") if phone_observation else None,
            **_phone_api_base_fields("phone_observation", phone_observation),
            "phone_observation": phone_observation,
            "apk_runtime_observation": apk_runtime_observation,
            **_apk_runtime_fields(apk_runtime_observation),
            "apk_install_pairing_proof": apk_install_pairing_proof,
            **_apk_proof_fields(apk_install_pairing_proof, apk_install_pairing_verified),
            "apk_install_pairing_attempt": apk_install_pairing_attempt,
            **_apk_attempt_fields(apk_install_pairing_attempt),
            "apk_artifact": apk_artifact,
            "release_apk_artifact": release_apk_artifact,
            "android_release_signing": release_signing,
            **_android_release_signing_fields(release_signing),
            **_paired_api_base_fields(payload, checks),
            **_android_device_probe_fields(checks),
            **_docker_check_fields(checks),
            "docker_available": bool(payload.get("docker_available")),
            "summary": _summary_with_runtime_evidence(
                payload.get("summary"),
                phone_verified,
                phone_observed,
                _apk_runtime_status(apk_runtime_observation),
            ),
            "remaining_external_gates": remaining_gates,
            "checks": checks,
            "claim_boundary": MOBILE_READINESS_SCOPE,
        }
    return {
        "report_kind": REPORT_KIND,
        "status": "EVIDENCE_MISSING",
        "source_path": None,
        "web_base": None,
        "phone_quick_start_url": None,
        "verification_commands": _verification_commands(None),
        "next_verification_actions": _next_verification_actions(
            web_base=None,
            package_ready=False,
            phone_browser_verified=_phone_browser_verified(phone_proof),
            phone_browser_observed=_phone_browser_observed(phone_observation),
            physical_phone_verified=apk_install_pairing_verified,
            docker_available=False,
        ),
        "package_ready_for_phone_install": False,
        "physical_phone_verified": apk_install_pairing_verified,
        "phone_browser_observed": _phone_browser_observed(phone_observation),
        "phone_browser_verified": _phone_browser_verified(phone_proof),
        "phone_proof_generated_at": phone_proof.get("generated_at") if phone_proof else None,
        **_phone_freshness_fields("phone_proof", phone_proof),
        "phone_proof_device_class": phone_proof.get("device_class") if phone_proof else None,
        "phone_proof_installed_mode": bool(phone_proof.get("installed_mode_detected")) if phone_proof else False,
        **_phone_api_base_fields("phone_proof", phone_proof),
        "phone_proof": phone_proof,
        "phone_observation_generated_at": phone_observation.get("generated_at") if phone_observation else None,
        **_phone_freshness_fields("phone_observation", phone_observation),
        "phone_observation_device_class": phone_observation.get("device_class") if phone_observation else None,
        "phone_observation_installed_mode": bool(phone_observation.get("installed_mode_detected")) if phone_observation else False,
        "phone_observation_local_runtime_only": bool(phone_observation.get("local_runtime_only")) if phone_observation else False,
        "phone_observation_client_host_source": phone_observation.get("client_host_source") if phone_observation else None,
        "phone_observation_effective_client_host": phone_observation.get("effective_client_host") if phone_observation else None,
        **_phone_api_base_fields("phone_observation", phone_observation),
        "phone_observation": phone_observation,
        "apk_runtime_observation": apk_runtime_observation,
        **_apk_runtime_fields(apk_runtime_observation),
        "apk_install_pairing_proof": apk_install_pairing_proof,
        **_apk_proof_fields(apk_install_pairing_proof, apk_install_pairing_verified),
        "apk_install_pairing_attempt": apk_install_pairing_attempt,
        **_apk_attempt_fields(apk_install_pairing_attempt),
        "apk_artifact": apk_artifact,
        "release_apk_artifact": release_apk_artifact,
        "android_release_signing": release_signing,
        **_android_release_signing_fields(release_signing),
        **_paired_api_base_fields(None, []),
        **_android_device_probe_fields([]),
        **_docker_check_fields([]),
        "docker_available": False,
        "summary": "No mobile readiness evidence has been written yet.",
        "remaining_external_gates": [
            "Run python scripts/run_mobile_stack_readiness.py to create mobile readiness evidence.",
        ],
        "checks": [],
        "claim_boundary": MOBILE_READINESS_SCOPE,
    }


def _latest_candidate(root: Path) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for rel_path in LATEST_CANDIDATES:
        path = root / rel_path
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            candidates.append(
                {
                    "path": path,
                    "sort_key": _candidate_sort_key(path, None),
                    "status": "EVIDENCE_UNREADABLE",
                    "summary": f"Mobile readiness evidence exists but could not be read: {type(exc).__name__}.",
                }
            )
            continue
        sort_key = _candidate_sort_key(path, payload if isinstance(payload, dict) else None)
        if not isinstance(payload, dict):
            candidates.append(
                {
                    "path": path,
                    "sort_key": sort_key,
                    "status": "EVIDENCE_MALFORMED",
                    "summary": "Mobile readiness evidence was not a JSON object.",
                }
            )
            continue
        candidates.append(
            {
                "path": path,
                "sort_key": sort_key,
                "status": "LATEST_EVIDENCE_FOUND",
                "payload": payload,
                "summary": "",
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate["sort_key"])


def _candidate_sort_key(path: Path, payload: dict[str, Any] | None) -> float:
    if payload:
        generated_at = payload.get("generated_at")
        if isinstance(generated_at, str) and generated_at.strip():
            parsed = _parse_datetime(generated_at)
            if parsed:
                return parsed.timestamp()
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _missing_or_malformed(path: Path, summary: str, root: Path) -> dict[str, Any]:
    apk_runtime_observation = latest_apk_runtime_observation(workspace_root=root)
    release_signing = android_release_signing_status(workspace_root=root)
    return {
        "report_kind": REPORT_KIND,
        "status": "EVIDENCE_MALFORMED",
        "source_path": str(path),
        "web_base": None,
        "phone_quick_start_url": None,
        "verification_commands": _verification_commands(None),
        "next_verification_actions": _next_verification_actions(
            web_base=None,
            package_ready=False,
            phone_browser_verified=False,
            phone_browser_observed=False,
            physical_phone_verified=False,
            docker_available=False,
        ),
        "package_ready_for_phone_install": False,
        "physical_phone_verified": False,
        "phone_browser_observed": False,
        "phone_browser_verified": False,
        "phone_proof_generated_at": None,
        **_phone_freshness_fields("phone_proof", None),
        "phone_proof_device_class": None,
        "phone_proof_installed_mode": False,
        **_phone_api_base_fields("phone_proof", None),
        "phone_proof": None,
        "phone_observation_generated_at": None,
        **_phone_freshness_fields("phone_observation", None),
        "phone_observation_device_class": None,
        "phone_observation_installed_mode": False,
        "phone_observation_local_runtime_only": False,
        "phone_observation_client_host_source": None,
        "phone_observation_effective_client_host": None,
        **_phone_api_base_fields("phone_observation", None),
        "phone_observation": None,
        "apk_runtime_observation": apk_runtime_observation,
        **_apk_runtime_fields(apk_runtime_observation),
        "apk_install_pairing_proof": None,
        "apk_install_pairing_verified": False,
        "apk_install_pairing_generated_at": None,
        "apk_install_pairing_selected_serial": None,
        "apk_install_pairing_package_id": None,
        "apk_install_pairing_apk_sha256": None,
        "apk_install_pairing_attempt": None,
        **_apk_attempt_fields(None),
        "apk_artifact": debug_apk_artifact_metadata(workspace_root=root),
        "release_apk_artifact": release_apk_artifact_metadata(workspace_root=root),
        "android_release_signing": release_signing,
        **_android_release_signing_fields(release_signing),
        **_paired_api_base_fields(None, []),
        **_android_device_probe_fields([]),
        **_docker_check_fields([]),
        "docker_available": False,
        "summary": summary,
        "remaining_external_gates": [
            "Regenerate mobile readiness evidence with python scripts/run_mobile_stack_readiness.py.",
        ],
        "checks": [],
        "claim_boundary": MOBILE_READINESS_SCOPE,
    }


def _phone_browser_verified(phone_proof: dict[str, Any] | None) -> bool:
    if not phone_proof:
        return False
    return bool(phone_proof.get("phone_browser_verified") and phone_proof.get("is_fresh"))


def _phone_browser_observed(phone_observation: dict[str, Any] | None) -> bool:
    if not phone_observation:
        return False
    return bool(phone_observation.get("phone_browser_observed") and phone_observation.get("is_fresh"))


def _summary_with_runtime_evidence(
    summary: Any,
    phone_verified: bool,
    phone_observed: bool,
    apk_runtime_status: str,
) -> str:
    base = summary if isinstance(summary, str) and summary.strip() else "Mobile readiness evidence is available."
    if phone_verified:
        base = f"{base} Fresh phone browser/PWA runtime proof is also recorded."
    elif phone_observed:
        base = f"{base} Phone-like runtime was observed, but verified phone network evidence is still missing."
    if apk_runtime_status == "verified":
        return f"{base} Fresh APK runtime evidence is also recorded from a verified non-local phone/API path."
    if apk_runtime_status == "local_only":
        return f"{base} APK runtime was observed locally, but verified non-local APK network evidence is still missing."
    if apk_runtime_status == "observed":
        return f"{base} APK runtime was observed, but it has not satisfied verified non-local phone/API proof."
    if apk_runtime_status == "stale":
        return f"{base} APK runtime evidence exists but is stale."
    return base


def _summary_with_phone_proof(summary: Any, phone_verified: bool, phone_observed: bool) -> str:
    if phone_verified:
        base = summary if isinstance(summary, str) and summary.strip() else "Mobile readiness evidence is available."
        return f"{base} Fresh phone browser/PWA runtime proof is also recorded."
    if phone_observed:
        base = summary if isinstance(summary, str) and summary.strip() else "Mobile readiness evidence is available."
        return f"{base} Phone-like runtime was observed, but verified phone network evidence is still missing."
    return summary if isinstance(summary, str) and summary.strip() else "Mobile readiness evidence is available."


def _current_remaining_gates(
    value: Any,
    *,
    phone_verified: bool,
    phone_observed: bool,
    physical_phone_verified: bool,
) -> list[str]:
    gates = [gate for gate in value if isinstance(gate, str)] if isinstance(value, list) else []
    normalized_gates: list[str] = []
    for gate in gates:
        if phone_verified and _is_phone_browser_proof_gate(gate):
            continue
        if physical_phone_verified and _is_android_apk_gate(gate):
            continue
        if gate.strip().lower() == "phone":
            if phone_verified:
                continue
            normalized_gates.append(
                (
                    "Open Quick Start from a real phone over the LAN preview or direct API base so verified "
                    "non-localhost phone browser/PWA runtime proof is recorded."
                )
                if phone_observed
                else "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof."
            )
            continue
        normalized_gates.append(gate)
    return normalized_gates


def _is_phone_browser_proof_gate(gate: str) -> bool:
    normalized = gate.lower()
    if "mobile:apk" in normalized or "native pairing" in normalized or "android phone" in normalized:
        return False
    return (
        normalized.strip() == "phone"
        or "phone browser/pwa runtime proof" in normalized
        or "non-localhost phone browser/pwa" in normalized
        or "open quick start from a real phone" in normalized
    )


def _is_android_apk_gate(gate: str) -> bool:
    normalized = gate.lower()
    return (
        normalized.strip() in {"apk", "android"}
        or "mobile:apk:wait-install-pair" in normalized
        or "mobile:apk:install-pair" in normalized
        or "native pairing launch" in normalized
        or "apk install" in normalized
        or "attach an android phone" in normalized
    )


def _current_checks(
    value: Any,
    *,
    phone_verified: bool,
    phone_observed: bool,
    phone_proof: dict[str, Any] | None,
    phone_observation: dict[str, Any] | None,
    apk_install_pairing_proof: dict[str, Any] | None,
    apk_install_pairing_attempt: dict[str, Any] | None,
    apk_runtime_observation: dict[str, Any] | None,
    android_release_signing: dict[str, Any],
) -> list[Any]:
    checks = [check for check in value if isinstance(check, dict)] if isinstance(value, list) else []
    apk_verified = _android_apk_install_pairing_verified(apk_install_pairing_proof)
    apk_runtime_status = _apk_runtime_status(apk_runtime_observation)
    apk_runtime_present = apk_runtime_status != "none"
    release_check = _current_android_release_signing_check(android_release_signing)
    apk_attempt_present = bool(apk_install_pairing_attempt)
    if not checks and not (phone_verified or phone_observed or apk_verified or apk_runtime_present or apk_attempt_present):
        return [release_check]
    out: list[Any] = []
    phone_replaced = False
    apk_replaced = False
    apk_runtime_replaced = False
    release_replaced = False
    for check in checks:
        if check.get("check_id") == "android_release_signing":
            out.append(release_check)
            release_replaced = True
            continue
        if check.get("check_id") == "phone_runtime_proof" and (phone_verified or phone_observed):
            out.append(_current_phone_runtime_check(
                original=check,
                phone_verified=phone_verified,
                phone_proof=phone_proof,
                phone_observation=phone_observation,
            ))
            phone_replaced = True
            continue
        if check.get("check_id") == "android_apk_install_pairing_proof" and apk_verified:
            out.append(_current_android_apk_install_pairing_check(
                original=check,
                apk_install_pairing_proof=apk_install_pairing_proof,
            ))
            apk_replaced = True
            continue
        if check.get("check_id") == "android_apk_install_pairing_attempt" and apk_attempt_present and not apk_verified:
            out.append(_current_android_apk_install_pairing_attempt_check(
                original=check,
                apk_install_pairing_attempt=apk_install_pairing_attempt,
            ))
            apk_replaced = True
            continue
        if check.get("check_id") == "native_pairing_launch" and apk_verified:
            out.append(dict(check))
            continue
        if check.get("check_id") == "apk_runtime_observation" and apk_runtime_present:
            out.append(_current_apk_runtime_check(
                original=check,
                apk_runtime_observation=apk_runtime_observation,
            ))
            apk_runtime_replaced = True
            continue
        out.append(check)
    if (phone_verified or phone_observed) and not phone_replaced:
        out.append(_current_phone_runtime_check(
            original={},
            phone_verified=phone_verified,
            phone_proof=phone_proof,
            phone_observation=phone_observation,
        ))
    if apk_verified and not apk_replaced:
        out.append(_current_android_apk_install_pairing_check(
            original={},
            apk_install_pairing_proof=apk_install_pairing_proof,
        ))
    if apk_attempt_present and not apk_verified and not apk_replaced:
        out.append(_current_android_apk_install_pairing_attempt_check(
            original={},
            apk_install_pairing_attempt=apk_install_pairing_attempt,
        ))
    if apk_runtime_present and not apk_runtime_replaced:
        out.append(_current_apk_runtime_check(
            original={},
            apk_runtime_observation=apk_runtime_observation,
        ))
    if not release_replaced:
        out.append(release_check)
    return out


def _current_phone_runtime_check(
    *,
    original: dict[str, Any],
    phone_verified: bool,
    phone_proof: dict[str, Any] | None,
    phone_observation: dict[str, Any] | None,
) -> dict[str, Any]:
    evidence = phone_proof if phone_verified and phone_proof else phone_observation or {}
    updated = dict(original)
    updated["check_id"] = "phone_runtime_proof"
    updated["status"] = "pass" if phone_verified else "external"
    updated["success"] = phone_verified
    updated["detail"] = (
        "Fresh verified phone browser/PWA runtime proof is recorded."
        if phone_verified
        else (
            "Phone-like runtime was observed, but verified phone network proof is missing; "
            "open Quick Start from a real phone over the LAN preview or direct API base."
        )
    )
    updated["evidence"] = evidence
    return updated


def _current_android_apk_install_pairing_check(
    *,
    original: dict[str, Any],
    apk_install_pairing_proof: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(original)
    updated["check_id"] = "android_apk_install_pairing_proof"
    updated["status"] = "pass"
    updated["success"] = True
    updated["detail"] = "Fresh Android APK install plus native pairing proof is recorded."
    updated["evidence"] = apk_install_pairing_proof or {}
    return updated


def _current_android_apk_install_pairing_attempt_check(
    *,
    original: dict[str, Any],
    apk_install_pairing_attempt: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(original)
    updated["check_id"] = "android_apk_install_pairing_attempt"
    updated["status"] = "external"
    updated["success"] = False
    updated["detail"] = _apk_attempt_detail(apk_install_pairing_attempt or {})
    updated["evidence"] = apk_install_pairing_attempt or {}
    return updated


def _current_apk_runtime_check(
    *,
    original: dict[str, Any],
    apk_runtime_observation: dict[str, Any] | None,
) -> dict[str, Any]:
    status = _apk_runtime_status(apk_runtime_observation)
    updated = dict(original)
    updated["check_id"] = "apk_runtime_observation"
    updated["status"] = "pass" if status == "verified" else "external"
    updated["success"] = status == "verified"
    updated["detail"] = _apk_runtime_detail(status)
    updated["evidence"] = apk_runtime_observation or {}
    return updated


def _current_android_release_signing_check(signing: dict[str, Any]) -> dict[str, Any]:
    ready = bool(signing.get("ready"))
    return {
        "check_id": "android_release_signing",
        "status": "pass" if ready else "external",
        "success": ready,
        "detail": _string_or_none(signing.get("summary")) or "Android release signing status is unknown.",
        "evidence": signing,
    }


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


def _android_apk_install_pairing_verified(apk_install_pairing_proof: dict[str, Any] | None) -> bool:
    if not apk_install_pairing_proof:
        return False
    return bool(
        apk_install_pairing_proof.get("android_apk_install_pairing_verified")
        and apk_install_pairing_proof.get("is_fresh")
    )


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


def _apk_proof_fields(
    apk_install_pairing_proof: dict[str, Any] | None,
    verified: bool,
) -> dict[str, Any]:
    proof = apk_install_pairing_proof or {}
    return {
        "apk_install_pairing_verified": verified,
        "apk_install_pairing_generated_at": proof.get("generated_at") if proof else None,
        "apk_install_pairing_selected_serial": proof.get("selected_serial") if proof else None,
        "apk_install_pairing_package_id": proof.get("package_id") if proof else None,
        "apk_install_pairing_apk_sha256": proof.get("apk_sha256") if proof else None,
        "apk_install_pairing_current_apk_sha256": proof.get("current_apk_sha256") if proof else None,
        "apk_install_pairing_apk_matches_current_artifact": proof.get("apk_matches_current_artifact") if proof else None,
    }


def _apk_attempt_fields(apk_install_pairing_attempt: dict[str, Any] | None) -> dict[str, Any]:
    attempt = apk_install_pairing_attempt or {}
    return {
        "apk_install_pairing_attempt_recorded": bool(attempt),
        "apk_install_pairing_attempt_status": _apk_attempt_status(attempt),
        "apk_install_pairing_attempt_fresh": bool(attempt.get("is_fresh")) if attempt else False,
        "apk_install_pairing_attempt_age_seconds": attempt.get("age_seconds") if isinstance(attempt.get("age_seconds"), int) else None,
        "apk_install_pairing_attempt_expires_at": _string_or_none(attempt.get("expires_at")),
        "apk_install_pairing_attempt_generated_at": attempt.get("generated_at") if attempt else None,
        "apk_install_pairing_attempt_install_success": bool(attempt.get("install_success")) if attempt else False,
        "apk_install_pairing_attempt_native_pairing_success": bool(attempt.get("native_pairing_success")) if attempt else False,
        "apk_install_pairing_attempt_dry_run": bool(attempt.get("dry_run")) if attempt else False,
        "apk_install_pairing_attempt_selected_serial": attempt.get("selected_serial") if attempt else None,
        "apk_install_pairing_attempt_package_id": attempt.get("package_id") if attempt else None,
        "apk_install_pairing_attempt_apk_sha256": attempt.get("apk_sha256") if attempt else None,
        "apk_install_pairing_attempt_current_apk_sha256": attempt.get("current_apk_sha256") if attempt else None,
        "apk_install_pairing_attempt_apk_matches_current_artifact": attempt.get("apk_matches_current_artifact") if attempt else None,
        "apk_install_pairing_attempt_message": _apk_attempt_message(attempt),
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


def _apk_runtime_fields(apk_runtime_observation: dict[str, Any] | None) -> dict[str, Any]:
    observation = apk_runtime_observation or {}
    status = _apk_runtime_status(observation)
    return {
        "apk_runtime_status": status,
        "apk_runtime_observed": status in {"verified", "local_only", "observed"},
        "apk_runtime_verified": status == "verified",
        "apk_runtime_fresh": bool(observation.get("is_fresh")) if observation else False,
        "apk_runtime_generated_at": observation.get("generated_at") if observation else None,
        "apk_runtime_age_seconds": observation.get("age_seconds") if isinstance(observation.get("age_seconds"), int) else None,
        "apk_runtime_expires_at": _string_or_none(observation.get("expires_at")),
        "apk_runtime_device_class": observation.get("device_class") if observation else None,
        "apk_runtime_installed_mode": bool(observation.get("installed_mode_detected")) if observation else False,
        "apk_runtime_local_runtime_only": bool(observation.get("local_runtime_only")) if observation else False,
        "apk_runtime_client_host_source": observation.get("client_host_source") if observation else None,
        "apk_runtime_effective_client_host": observation.get("effective_client_host") if observation else None,
        **_phone_api_base_fields("apk_runtime", observation),
    }


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


def _android_device_probe_fields(checks: list[Any]) -> dict[str, Any]:
    probe = next(
        (
            check for check in checks
            if isinstance(check, dict) and check.get("check_id") == "android_device_probe"
        ),
        None,
    )
    if not probe:
        return {
            "android_device_ready": False,
            "android_device_count": 0,
            "android_device_ready_count": 0,
            "android_device_status": "unknown",
            "android_device_detail": None,
            "android_adb_path": None,
        }
    evidence = probe.get("evidence") if isinstance(probe.get("evidence"), dict) else {}
    devices = evidence.get("devices") if isinstance(evidence.get("devices"), list) else []
    device_dicts = [device for device in devices if isinstance(device, dict)]
    ready_count = sum(1 for device in device_dicts if str(device.get("state") or "") == "device")
    return {
        "android_device_ready": bool(probe.get("success")) or ready_count > 0,
        "android_device_count": len(device_dicts),
        "android_device_ready_count": ready_count,
        "android_device_status": _string_or_none(probe.get("status")) or "unknown",
        "android_device_detail": _string_or_none(probe.get("detail")) or _string_or_none(evidence.get("message")),
        "android_adb_path": _string_or_none(evidence.get("adb_path")),
    }


def _docker_check_fields(checks: list[Any]) -> dict[str, Any]:
    check = next(
        (
            item for item in checks
            if isinstance(item, dict) and item.get("check_id") == "docker_cli"
        ),
        None,
    )
    if not check:
        return {
            "docker_engine_status": "unknown",
            "docker_engine_detail": None,
            "docker_cli_path": None,
            "docker_server_version": None,
            "docker_wsl_checked": False,
            "docker_wsl_engine_available": False,
            "docker_wsl_warnings": [],
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
    evidence = check.get("evidence") if isinstance(check.get("evidence"), dict) else {}
    wsl = evidence.get("wsl_docker") if isinstance(evidence.get("wsl_docker"), dict) else {}
    wsl_warnings = evidence.get("wsl_warnings") if isinstance(evidence.get("wsl_warnings"), list) else []
    install_attempt = (
        evidence.get("docker_desktop_install_attempt")
        if isinstance(evidence.get("docker_desktop_install_attempt"), dict)
        else {}
    )
    return {
        "docker_engine_status": _string_or_none(check.get("status")) or "unknown",
        "docker_engine_detail": _string_or_none(check.get("detail")),
        "docker_cli_path": _string_or_none(evidence.get("docker_path")),
        "docker_server_version": _string_or_none(evidence.get("docker_server_version")) or _string_or_none(wsl.get("server_version")),
        "docker_wsl_checked": bool(wsl.get("checked")),
        "docker_wsl_engine_available": bool(wsl.get("engine_available")),
        "docker_wsl_warnings": [item for item in wsl_warnings if isinstance(item, str)],
        "docker_desktop_winget_available": bool(evidence.get("docker_desktop_winget_available")),
        "docker_desktop_install_command": _string_or_none(evidence.get("docker_desktop_install_command")),
        "docker_desktop_elevated_install_command": (
            _string_or_none(evidence.get("docker_desktop_elevated_install_command"))
            or elevated_install_command_string()
        ),
        "docker_desktop_install_attempt_status": _string_or_none(install_attempt.get("status")),
        "docker_desktop_install_attempt_detail": _string_or_none(install_attempt.get("detail")),
        "docker_desktop_install_attempt_returncode": install_attempt.get("returncode") if isinstance(install_attempt.get("returncode"), int) else None,
        "docker_desktop_install_attempt_installer_exit_code": install_attempt.get("installer_exit_code") if isinstance(install_attempt.get("installer_exit_code"), int) else None,
        "docker_desktop_install_attempt_generated_at": _string_or_none(install_attempt.get("generated_at")),
        "docker_desktop_install_attempt_admin_elevation_required": bool(install_attempt.get("admin_elevation_required")),
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


def _paired_api_base_fields(payload: dict[str, Any] | None, checks: list[Any]) -> dict[str, Any]:
    payload = payload or {}
    check = next(
        (
            item for item in checks
            if isinstance(item, dict) and item.get("check_id") == "paired_api_bases"
        ),
        None,
    )
    payload_has_verdict = (
        isinstance(payload.get("paired_api_bases_reachable"), bool)
        or _string_or_none(payload.get("paired_api_bases_status")) is not None
        or _string_or_none(payload.get("paired_api_bases_detail")) is not None
    )
    if payload_has_verdict:
        return {
            "paired_api_bases_reachable": bool(payload.get("paired_api_bases_reachable")),
            "paired_api_bases_status": _string_or_none(payload.get("paired_api_bases_status")) or "unknown",
            "paired_api_bases_detail": _string_or_none(payload.get("paired_api_bases_detail")),
        }
    if check:
        return {
            "paired_api_bases_reachable": bool(check.get("success")),
            "paired_api_bases_status": _string_or_none(check.get("status")) or "unknown",
            "paired_api_bases_detail": _string_or_none(check.get("detail")),
        }
    return {
        "paired_api_bases_reachable": False,
        "paired_api_bases_status": "not_run",
        "paired_api_bases_detail": "Paired PWA/proxy and APK/direct API bases have not been verified yet.",
    }


def _phone_api_base_fields(prefix: str, proof: dict[str, Any] | None) -> dict[str, Any]:
    proof = proof or {}
    return {
        f"{prefix}_api_base_host": proof.get("api_base_host") if proof else None,
        f"{prefix}_api_base_network_path": proof.get("api_base_network_path") if proof else None,
        f"{prefix}_api_base_source": proof.get("api_base_source") if proof else None,
    }


def _phone_freshness_fields(prefix: str, proof: dict[str, Any] | None) -> dict[str, Any]:
    proof = proof or {}
    max_age_hours = proof.get("max_age_hours")
    return {
        f"{prefix}_fresh": bool(proof.get("is_fresh")) if proof else False,
        f"{prefix}_age_seconds": proof.get("age_seconds") if isinstance(proof.get("age_seconds"), int) else None,
        f"{prefix}_expires_at": _string_or_none(proof.get("expires_at")),
        f"{prefix}_max_age_hours": max_age_hours if isinstance(max_age_hours, int) else None,
    }


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _quick_start_url(web_base: str | None) -> str | None:
    base = str(web_base or "").strip().rstrip("/")
    if not base:
        return None
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"


def _phone_reachable_quick_start_url(payload: dict[str, Any], web_base: str | None) -> str | None:
    from_web_base = _quick_start_url(web_base)
    from_payload = _string_or_none(payload.get("phone_quick_start_url"))
    pairing = _owner_pairing_evidence(payload)
    from_pairing = _strip_fragment(
        _string_or_none(pairing.get("selected_pairing_url"))
        or _string_or_none(pairing.get("first_pairing_url"))
    )
    if from_pairing and not _is_loopback_url(from_pairing):
        return from_pairing
    from_api_base = _quick_start_from_api_base(
        _string_or_none(pairing.get("selected_pairing_api_base"))
        or _string_or_none(pairing.get("first_pairing_api_base"))
    )
    if from_api_base and not _is_loopback_url(from_api_base):
        return from_api_base
    if from_web_base and _is_private_lan_url(from_web_base):
        return from_web_base
    if from_payload and not _is_loopback_url(from_payload):
        return from_payload
    return from_payload or from_web_base


def _owner_pairing_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return {}
    for check in checks:
        if not isinstance(check, dict) or check.get("check_id") != "owner_pairing_payload":
            continue
        evidence = check.get("evidence")
        return evidence if isinstance(evidence, dict) else {}
    return {}


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


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        value = re.sub(r"(cas_owner_token=)[^&#\s}]+", r"\1REDACTED", value)
        value = re.sub(r"([?&]owner_token=)[^&#\s}]+", r"\1REDACTED", value)
        return value
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {
            key: ("REDACTED" if key in {"owner_token", "cas_owner_token"} else _redact(item))
            for key, item in value.items()
        }
    return value
