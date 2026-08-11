"""Durable Android APK install + native pairing proof for CAS Forex."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


REPORT_KIND = "cas_forex_android_apk_install_pairing_proof"
DEFAULT_PROOF_DIR = Path("evidence_runs") / "mobile_apk_proof" / "latest"
LATEST_ATTEMPT_FILE = "android_apk_install_pairing_attempt.json"
LATEST_PROOF_FILE = "android_apk_install_pairing_proof.json"
ATTEMPT_LOG_FILE = "android_apk_install_pairing_attempts.jsonl"
APK_PROOF_MAX_AGE_HOURS = 72
APK_PROOF_SCOPE = (
    "Android APK proof records an owner-run ADB install plus native pairing "
    "deep-link launch on an attached authorized Android phone. Live trading, "
    "broker, deposit, payout, and other money-moving actions remain governed "
    "by owner-authorized runtime gates, credentials, and broker state."
)


def record_android_apk_install_pairing_proof(
    *,
    install_report: Mapping[str, Any],
    native_pairing_launch: Mapping[str, Any],
    workspace_root: str | Path = ".",
) -> dict[str, Any]:
    """Persist an Android APK install/native-pairing attempt.

    The latest attempt is always written for diagnosis. The proof file is only
    promoted when install and native pairing both succeed in a non-dry-run pass.
    """
    root = Path(workspace_root).resolve()
    output_dir = root / DEFAULT_PROOF_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    proof = _build_proof(install_report=install_report, native_pairing_launch=native_pairing_launch)
    serialized = json.dumps(proof, indent=2, sort_keys=True)
    (output_dir / LATEST_ATTEMPT_FILE).write_text(serialized, encoding="utf-8")
    with (output_dir / ATTEMPT_LOG_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(proof, sort_keys=True) + "\n")
    if proof["android_apk_install_pairing_verified"]:
        (output_dir / LATEST_PROOF_FILE).write_text(serialized, encoding="utf-8")
    return proof


def latest_android_apk_install_pairing_proof(
    *,
    workspace_root: str | Path = ".",
    max_age_hours: int = APK_PROOF_MAX_AGE_HOURS,
) -> dict[str, Any] | None:
    path = Path(workspace_root).resolve() / DEFAULT_PROOF_DIR / LATEST_PROOF_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _with_freshness(payload, source_path=path, max_age_hours=max_age_hours)


def latest_android_apk_install_pairing_attempt(
    *,
    workspace_root: str | Path = ".",
    max_age_hours: int = APK_PROOF_MAX_AGE_HOURS,
) -> dict[str, Any] | None:
    path = Path(workspace_root).resolve() / DEFAULT_PROOF_DIR / LATEST_ATTEMPT_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _with_freshness(payload, source_path=path, max_age_hours=max_age_hours)


def _build_proof(*, install_report: Mapping[str, Any], native_pairing_launch: Mapping[str, Any]) -> dict[str, Any]:
    install_success = bool(install_report.get("success"))
    launch_success = bool(native_pairing_launch.get("success"))
    install_dry_run = bool(install_report.get("dry_run"))
    launch_dry_run = bool(native_pairing_launch.get("dry_run"))
    selected_serial = _safe_str(
        native_pairing_launch.get("selected_serial") or install_report.get("selected_serial"),
        120,
    )
    apk_path = _safe_str(install_report.get("apk_path"), 500)
    verified = bool(install_success and launch_success and not install_dry_run and not launch_dry_run)
    return _redact(
        {
            "report_kind": REPORT_KIND,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "android_apk_install_pairing_verified": verified,
            "install_success": install_success,
            "native_pairing_success": launch_success,
            "dry_run": bool(install_dry_run or launch_dry_run),
            "selected_serial": selected_serial,
            "adb_path": _safe_str(native_pairing_launch.get("adb_path") or install_report.get("adb_path"), 500),
            "apk_path": apk_path,
            "apk_sha256": _sha256_file(apk_path),
            "package_id": _safe_str(native_pairing_launch.get("package_id"), 160),
            "pairing_url": _safe_str(native_pairing_launch.get("pairing_url"), 800),
            "install_message": _safe_str(install_report.get("message"), 500),
            "native_pairing_message": _safe_str(native_pairing_launch.get("message"), 500),
            "install_command": _redact(install_report.get("command")),
            "native_pairing_command": _redact(native_pairing_launch.get("command")),
            "claim_boundary": APK_PROOF_SCOPE,
        }
    )


def _with_freshness(payload: dict[str, Any], *, source_path: Path, max_age_hours: int) -> dict[str, Any]:
    payload = _redact(payload)
    payload["claim_boundary"] = APK_PROOF_SCOPE
    generated_at = _parse_datetime(payload.get("generated_at"))
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    age_seconds = None
    expires_at = None
    if generated_at:
        age_seconds = max(0, int((now - generated_at).total_seconds()))
        expires_at = (generated_at + max_age).isoformat()
    is_fresh = bool(generated_at and now - generated_at <= max_age)
    payload["is_fresh"] = is_fresh
    payload["age_seconds"] = age_seconds
    payload["expires_at"] = expires_at
    payload["max_age_hours"] = max_age_hours
    payload["source_path"] = str(source_path)
    return payload


def _sha256_file(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_str(value: Any, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    return _redact_string(value[:max_len])


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
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
