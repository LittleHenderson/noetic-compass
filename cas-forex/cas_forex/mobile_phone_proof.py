"""Runtime phone/PWA proof evidence for CAS Forex."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


REPORT_KIND = "cas_forex_phone_runtime_proof"
DEFAULT_PROOF_DIR = Path("evidence_runs") / "mobile_phone_proof" / "latest"
LATEST_OBSERVATION_FILE = "runtime_observation.json"
LATEST_PHONE_FILE = "phone_runtime_proof.json"
LATEST_APK_RUNTIME_FILE = "apk_runtime_observation.json"
OBSERVATION_LOG_FILE = "runtime_observations.jsonl"
PHONE_PROOF_MAX_AGE_HOURS = 24
PHONE_PROOF_SCOPE = (
    "Phone runtime proof records browser/app session evidence. Verified phone proof "
    "requires a phone-like runtime plus non-localhost client/proxy evidence. Live "
    "trading, broker, deposit, payout, and other money-moving actions remain governed "
    "by owner-authorized runtime gates, credentials, and broker state."
)


def build_phone_runtime_proof(
    payload: dict[str, Any],
    *,
    client_host: str | None = None,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
    request_user_agent: str | None = None,
    client_api_base: str | None = None,
) -> dict[str, Any]:
    """Build bounded phone runtime proof without writing it to evidence files."""
    return _build_proof(
        payload,
        client_host=client_host,
        forwarded_for=forwarded_for,
        real_ip=real_ip,
        request_user_agent=request_user_agent,
        client_api_base=client_api_base,
    )


def record_phone_runtime_proof(
    payload: dict[str, Any],
    *,
    workspace_root: str | Path = ".",
    client_host: str | None = None,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
    request_user_agent: str | None = None,
    client_api_base: str | None = None,
) -> dict[str, Any]:
    """Persist a bounded browser/device observation from the web or APK UI."""
    root = Path(workspace_root).resolve()
    output_dir = root / DEFAULT_PROOF_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    proof = build_phone_runtime_proof(
        payload,
        client_host=client_host,
        forwarded_for=forwarded_for,
        real_ip=real_ip,
        request_user_agent=request_user_agent,
        client_api_base=client_api_base,
    )
    serialized = json.dumps(proof, indent=2, sort_keys=True)
    (output_dir / LATEST_OBSERVATION_FILE).write_text(serialized, encoding="utf-8")
    with (output_dir / OBSERVATION_LOG_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(proof, sort_keys=True) + "\n")
    if proof["phone_browser_verified"]:
        (output_dir / LATEST_PHONE_FILE).write_text(serialized, encoding="utf-8")
    if proof.get("app_surface") == "apk" and proof.get("phone_browser_observed"):
        (output_dir / LATEST_APK_RUNTIME_FILE).write_text(serialized, encoding="utf-8")
    return proof


def latest_phone_runtime_proof(
    *,
    workspace_root: str | Path = ".",
    max_age_hours: int = PHONE_PROOF_MAX_AGE_HOURS,
) -> dict[str, Any] | None:
    """Return the latest fresh phone-like browser proof, if one exists."""
    path = Path(workspace_root).resolve() / DEFAULT_PROOF_DIR / LATEST_PHONE_FILE
    return _read_payload_with_freshness(path, max_age_hours=max_age_hours)


def latest_phone_runtime_observation(
    *,
    workspace_root: str | Path = ".",
    max_age_hours: int = PHONE_PROOF_MAX_AGE_HOURS,
) -> dict[str, Any] | None:
    """Return the latest bounded runtime observation, verified or not."""
    output_dir = Path(workspace_root).resolve() / DEFAULT_PROOF_DIR
    phone_like = _latest_fresh_phone_like_observation_from_log(
        output_dir / OBSERVATION_LOG_FILE,
        max_age_hours=max_age_hours,
    )
    if phone_like:
        return phone_like
    path = output_dir / LATEST_OBSERVATION_FILE
    return _read_payload_with_freshness(path, max_age_hours=max_age_hours)


def latest_apk_runtime_observation(
    *,
    workspace_root: str | Path = ".",
    max_age_hours: int = PHONE_PROOF_MAX_AGE_HOURS,
) -> dict[str, Any] | None:
    """Return the latest observed APK phone runtime, verified or local-only."""
    output_dir = Path(workspace_root).resolve() / DEFAULT_PROOF_DIR
    from_log = _latest_matching_phone_observation_from_log(
        output_dir / OBSERVATION_LOG_FILE,
        max_age_hours=max_age_hours,
        app_surface="apk",
        fresh_only=False,
    )
    if from_log:
        return from_log
    path = output_dir / LATEST_APK_RUNTIME_FILE
    payload = _read_payload_with_freshness(path, max_age_hours=max_age_hours)
    if payload and payload.get("app_surface") == "apk" and payload.get("phone_browser_observed"):
        return payload
    return None


def _read_payload_with_freshness(
    path: Path,
    *,
    max_age_hours: int,
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _with_freshness(payload, source_path=path, max_age_hours=max_age_hours)


def _latest_fresh_phone_like_observation_from_log(
    path: Path,
    *,
    max_age_hours: int,
) -> dict[str, Any] | None:
    return _latest_matching_phone_observation_from_log(
        path,
        max_age_hours=max_age_hours,
        fresh_only=True,
    )


def _latest_matching_phone_observation_from_log(
    path: Path,
    *,
    max_age_hours: int,
    app_surface: str | None = None,
    fresh_only: bool,
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in reversed(lines[-500:]):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict) or not payload.get("phone_browser_observed"):
            continue
        if app_surface and payload.get("app_surface") != app_surface:
            continue
        enriched = _with_freshness(payload, source_path=path, max_age_hours=max_age_hours)
        if fresh_only and not enriched.get("is_fresh"):
            continue
        return enriched
    return None


def _with_freshness(
    payload: dict[str, Any],
    *,
    source_path: Path,
    max_age_hours: int,
) -> dict[str, Any]:
    payload = _redact(payload)
    payload["claim_boundary"] = PHONE_PROOF_SCOPE
    generated_at = _parse_datetime(payload.get("generated_at"))
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    age_seconds = int(max(0.0, (now - generated_at).total_seconds())) if generated_at else None
    expires_at = generated_at + max_age if generated_at else None
    is_fresh = bool(generated_at and now - generated_at <= max_age)
    payload["is_fresh"] = is_fresh
    payload["age_seconds"] = age_seconds
    payload["expires_at"] = expires_at.isoformat() if expires_at else None
    payload["max_age_hours"] = max_age_hours
    payload["source_path"] = str(source_path)
    return payload


def _build_proof(
    payload: dict[str, Any],
    *,
    client_host: str | None,
    forwarded_for: str | None,
    real_ip: str | None,
    request_user_agent: str | None,
    client_api_base: str | None,
) -> dict[str, Any]:
    user_agent = _safe_str(payload.get("user_agent") or request_user_agent, 320) or ""
    platform = _safe_str(payload.get("platform"), 120) or ""
    app_surface = _safe_choice(payload.get("app_surface"), {"pwa", "apk", "web"}, "web")
    display_mode = _safe_choice(
        payload.get("display_mode"),
        {"browser", "standalone", "fullscreen", "minimal-ui", "unknown"},
        "unknown",
    )
    viewport_width = _safe_int(payload.get("viewport_width"), 0, 10000)
    viewport_height = _safe_int(payload.get("viewport_height"), 0, 10000)
    screen_width = _safe_int(payload.get("screen_width"), 0, 10000)
    screen_height = _safe_int(payload.get("screen_height"), 0, 10000)
    max_touch_points = _safe_int(payload.get("max_touch_points"), 0, 64)
    standalone_pwa = _safe_bool(payload.get("standalone_pwa"))
    installed_mode = standalone_pwa or display_mode in {"standalone", "fullscreen"}
    device_class = _infer_device_class(
        user_agent=user_agent,
        platform=platform,
        viewport_width=viewport_width,
        screen_width=screen_width,
        max_touch_points=max_touch_points,
    )
    phone_observed = device_class == "phone"
    effective_client_host, client_host_source = _effective_client_host(
        client_host=client_host,
        forwarded_for=forwarded_for,
        real_ip=real_ip,
    )
    url_origin = _safe_str(payload.get("url_origin"), 180)
    url_origin_host = _origin_host(url_origin)
    api_base_source = "request-header" if _safe_str(client_api_base, 240) else "payload"
    api_base = _safe_str(client_api_base, 240) or _safe_str(payload.get("api_base"), 240)
    api_base_host = _origin_host(api_base)
    local_runtime_only = _is_local_runtime_only(
        effective_client_host=effective_client_host,
    )
    phone_verified = phone_observed and not local_runtime_only
    return _redact(
        {
            "report_kind": REPORT_KIND,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": _safe_str(payload.get("source"), 80),
            "app_surface": app_surface,
            "client_host": _safe_str(client_host, 120),
            "forwarded_for": _safe_str(forwarded_for, 180),
            "real_ip": _safe_str(real_ip, 120),
            "effective_client_host": effective_client_host,
            "client_host_source": client_host_source,
            "url_origin": url_origin,
            "url_origin_host": url_origin_host,
            "url_path": _safe_str(payload.get("url_path"), 180),
            "api_base": api_base,
            "api_base_host": api_base_host,
            "api_base_source": api_base_source if api_base else None,
            "api_base_network_path": _api_base_network_path(
                api_base_host=api_base_host,
                url_origin_host=url_origin_host,
            ),
            "api_base_localhost_only": _is_loopback_host(api_base_host) if api_base_host else None,
            "display_mode": display_mode,
            "standalone_pwa": standalone_pwa,
            "installed_mode_detected": installed_mode,
            "phone_browser_observed": phone_observed,
            "phone_browser_verified": phone_verified,
            "local_runtime_only": local_runtime_only,
            "device_class": device_class,
            "user_agent": user_agent,
            "platform": platform,
            "language": _safe_str(payload.get("language"), 40),
            "timezone": _safe_str(payload.get("timezone"), 80),
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "device_pixel_ratio": _safe_float(payload.get("device_pixel_ratio"), 0.0, 10.0),
            "max_touch_points": max_touch_points,
            "online": _safe_bool(payload.get("online")),
            "claim_boundary": PHONE_PROOF_SCOPE,
        }
    )


def _infer_device_class(
    *,
    user_agent: str,
    platform: str,
    viewport_width: int | None,
    screen_width: int | None,
    max_touch_points: int | None,
) -> str:
    ua = user_agent.lower()
    plat = platform.lower()
    narrow_width = min(
        value for value in (viewport_width, screen_width) if isinstance(value, int) and value > 0
    ) if any(isinstance(value, int) and value > 0 for value in (viewport_width, screen_width)) else None
    has_touch = bool(max_touch_points and max_touch_points > 0)
    tablet_hint = any(token in ua or token in plat for token in ("ipad", "tablet"))
    phone_hint = any(token in ua for token in ("mobile", "iphone", "ipod", "android"))
    if tablet_hint and has_touch:
        return "tablet"
    if phone_hint and has_touch and (narrow_width is None or narrow_width <= 820):
        return "phone"
    if phone_hint and narrow_width is not None and narrow_width <= 480:
        return "phone"
    return "desktop_or_unknown"


def _effective_client_host(
    *,
    client_host: str | None,
    forwarded_for: str | None,
    real_ip: str | None,
) -> tuple[str | None, str]:
    direct = _safe_host(client_host)
    forwarded = _first_forwarded_host(forwarded_for)
    real = _safe_host(real_ip)
    if direct and _is_loopback_host(direct):
        if forwarded:
            return forwarded, "x-forwarded-for"
        if real:
            return real, "x-real-ip"
    if direct:
        return direct, "request-client"
    if forwarded:
        return forwarded, "x-forwarded-for"
    if real:
        return real, "x-real-ip"
    return None, "missing"


def _is_local_runtime_only(*, effective_client_host: str | None) -> bool:
    return not (effective_client_host and not _is_loopback_host(effective_client_host))


def _first_forwarded_host(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    for part in value.split(","):
        host = _safe_host(part)
        if host:
            return host
    return None


def _origin_host(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return _safe_host(parsed.hostname)


def _api_base_network_path(
    *,
    api_base_host: str | None,
    url_origin_host: str | None,
) -> str:
    if not api_base_host:
        return "unknown"
    if _is_loopback_host(api_base_host):
        return "loopback_api"
    if url_origin_host and api_base_host == url_origin_host:
        return "same_origin_proxy"
    return "direct_api"


def _safe_host(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().strip('"').strip("'").lower()
    if not cleaned:
        return None
    if "://" in cleaned:
        try:
            parsed = urlsplit(cleaned)
            cleaned = parsed.hostname or cleaned
        except ValueError:
            return None
    elif cleaned.startswith("[") and "]" in cleaned:
        cleaned = cleaned[1 : cleaned.index("]")]
    if ":" in cleaned and cleaned.count(":") == 1:
        host_part, port_part = cleaned.rsplit(":", 1)
        if port_part.isdigit():
            cleaned = host_part
    if cleaned.startswith("::ffff:"):
        cleaned = cleaned.removeprefix("::ffff:")
    return _redact_string(cleaned[:120])


def _is_loopback_host(host: str) -> bool:
    cleaned = _safe_host(host) or ""
    if cleaned in {"localhost", "::1"}:
        return True
    try:
        parsed = ip_address(cleaned)
    except ValueError:
        return False
    mapped = getattr(parsed, "ipv4_mapped", None)
    if mapped is not None:
        return mapped.is_loopback
    return parsed.is_loopback


def _safe_str(value: Any, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return _redact_string(cleaned[:max_len])


def _safe_choice(value: Any, allowed: set[str], fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.strip().lower()
    return cleaned if cleaned in allowed else fallback


def _safe_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _safe_int(value: Any, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < minimum or parsed > maximum:
        return None
    return parsed


def _safe_float(value: Any, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < minimum or parsed > maximum:
        return None
    return parsed


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
