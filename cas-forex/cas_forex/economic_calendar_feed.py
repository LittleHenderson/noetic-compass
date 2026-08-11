"""Configurable economic-calendar feed for macro blackout checks.

The dispatch macro gate already knows how to block on timestamped event
payloads. This module supplies those payloads from an owner-configured local
file or HTTP(S) JSON/CSV feed, with a local cache so dispatch can keep reporting
source status without pretending a missing feed is fresh market truth.
"""

from __future__ import annotations

import csv
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from cas_forex.time_utils import ensure_utc


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_economic_calendar_feed"
DEFAULT_CACHE_PATH = REPO_ROOT / "runtime" / "economic_calendar" / "economic_calendar_cache.json"
CLAIM_BOUNDARY = (
    "Economic calendar feed loading is read-only market-event context. It may "
    "supply macro blackout evidence to dispatch, but it does not place orders, "
    "close positions, move money, change settings, authorize live trading, or "
    "promise returns."
)

Transport = Callable[[str, float], str | bytes]


def build_economic_calendar_feed_report(
    *,
    config: Any = None,
    now: datetime | None = None,
    refresh: bool = False,
    root: Path | str | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Return normalized economic-calendar events and feed/cache status.

    Supported configured sources:
      * ``economic_calendar_feed_path``: local JSON/CSV file path
      * ``economic_calendar_feed_url``: ``file://``, ``http://``, or ``https://``

    The return shape is plain JSON data so it can be embedded directly in
    dispatch evidence and settings/status routes.
    """
    base = Path(root) if root is not None else REPO_ROOT
    cfg = _resolve_config(config)
    checked_at = ensure_utc(now) if now is not None else datetime.now(timezone.utc)
    source = _configured_source(cfg)
    cache_path = _cache_path(cfg, base)
    ttl_seconds = _positive_int(getattr(cfg, "economic_calendar_ttl_seconds", 900), 900)
    timeout_seconds = _positive_float(getattr(cfg, "economic_calendar_timeout_seconds", 1.5), 1.5)
    fail_closed = bool(getattr(cfg, "economic_calendar_fail_closed", False))

    if source is None:
        return _report(
            status="UNCONFIGURED",
            checked_at=checked_at,
            source_kind="none",
            source="",
            cache_path=cache_path,
            ttl_seconds=ttl_seconds,
            fail_closed=fail_closed,
            events=[],
            raw_event_count=0,
            unusable_event_count=0,
            detail=(
                "No external economic-calendar feed is configured. Dispatch will "
                "fall back to timestamped telemetry events and the static seed calendar."
            ),
        )

    cached = _read_cache(cache_path, checked_at=checked_at)
    if cached is not None and not refresh and _cache_is_fresh(cached, ttl_seconds):
        events = _rows(cached.get("events"))
        return _report(
            status="CACHE_FRESH",
            checked_at=checked_at,
            source_kind=str(cached.get("source_kind") or source["kind"]),
            source=str(cached.get("source") or source["value"]),
            cache_path=cache_path,
            ttl_seconds=ttl_seconds,
            fail_closed=fail_closed,
            events=events,
            raw_event_count=int(cached.get("raw_event_count") or len(events)),
            unusable_event_count=int(cached.get("unusable_event_count") or 0),
            cache_written_at_epoch=_float_or_none(cached.get("written_at_epoch")),
            detail="Using fresh economic-calendar cache.",
        )

    try:
        raw_text = _load_source(source, base=base, timeout_seconds=timeout_seconds, transport=transport)
        raw_rows = _extract_rows(raw_text, source_hint=source["value"])
        normalized = _normalize_events(raw_rows, source_label=source["value"])
        _write_cache(
            cache_path,
            checked_at=checked_at,
            source=source,
            events=normalized["events"],
            raw_event_count=normalized["raw_event_count"],
            unusable_event_count=normalized["unusable_event_count"],
        )
        return _report(
            status="LOADED",
            checked_at=checked_at,
            source_kind=source["kind"],
            source=source["value"],
            cache_path=cache_path,
            ttl_seconds=ttl_seconds,
            fail_closed=fail_closed,
            events=normalized["events"],
            raw_event_count=normalized["raw_event_count"],
            unusable_event_count=normalized["unusable_event_count"],
            cache_written_at_epoch=checked_at.timestamp(),
            detail="Loaded configured economic-calendar feed.",
        )
    except Exception as exc:
        if cached is not None:
            events = _rows(cached.get("events"))
            status = "CACHE_STALE"
            if _cache_is_fresh(cached, ttl_seconds):
                status = "CACHE_FRESH_AFTER_REFRESH_ERROR"
            return _report(
                status=status,
                checked_at=checked_at,
                source_kind=str(cached.get("source_kind") or source["kind"]),
                source=str(cached.get("source") or source["value"]),
                cache_path=cache_path,
                ttl_seconds=ttl_seconds,
                fail_closed=fail_closed,
                events=events,
                raw_event_count=int(cached.get("raw_event_count") or len(events)),
                unusable_event_count=int(cached.get("unusable_event_count") or 0),
                cache_written_at_epoch=_float_or_none(cached.get("written_at_epoch")),
                detail=f"Feed refresh failed; using cached economic-calendar events: {type(exc).__name__}: {exc}",
                error=f"{type(exc).__name__}: {exc}",
            )
        return _report(
            status="FETCH_FAILED",
            checked_at=checked_at,
            source_kind=source["kind"],
            source=source["value"],
            cache_path=cache_path,
            ttl_seconds=ttl_seconds,
            fail_closed=fail_closed,
            events=[],
            raw_event_count=0,
            unusable_event_count=0,
            detail=f"Configured economic-calendar feed could not be loaded: {type(exc).__name__}: {exc}",
            error=f"{type(exc).__name__}: {exc}",
        )


def economic_calendar_events_for_dispatch(
    *,
    config: Any = None,
    now: datetime | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Small wrapper used by dispatch to make the call site explicit."""
    return build_economic_calendar_feed_report(config=config, now=now, refresh=refresh)


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _configured_source(cfg: Any) -> dict[str, str] | None:
    url = str(getattr(cfg, "economic_calendar_feed_url", "") or "").strip()
    path = str(getattr(cfg, "economic_calendar_feed_path", "") or "").strip()
    if url:
        parsed = urllib.parse.urlparse(url)
        kind = parsed.scheme.lower() if parsed.scheme else "path"
        return {"kind": kind, "value": url}
    if path:
        return {"kind": "path", "value": path}
    return None


def _cache_path(cfg: Any, base: Path) -> Path:
    raw = str(getattr(cfg, "economic_calendar_cache_path", "") or "").strip()
    if not raw:
        return DEFAULT_CACHE_PATH if base == REPO_ROOT else base / "runtime" / "economic_calendar_cache.json"
    path = Path(raw)
    return path if path.is_absolute() else base / path


def _load_source(
    source: Mapping[str, str],
    *,
    base: Path,
    timeout_seconds: float,
    transport: Transport | None,
) -> str:
    value = source["value"]
    kind = source["kind"].lower()
    if kind in {"http", "https"}:
        if transport is not None:
            data = transport(value, timeout_seconds)
            return data.decode("utf-8") if isinstance(data, bytes) else str(data)
        request = urllib.request.Request(value, headers={"Accept": "application/json,text/csv,*/*"})
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError) as exc:
            raise RuntimeError(f"HTTP economic calendar fetch failed for {value}") from exc
    if kind == "file":
        parsed = urllib.parse.urlparse(value)
        path = Path(urllib.request.url2pathname(parsed.path))
    else:
        path = Path(value)
        if not path.is_absolute():
            path = base / path
    return path.read_text(encoding="utf-8")


def _extract_rows(raw_text: str, *, source_hint: str = "") -> list[Mapping[str, Any]]:
    stripped = raw_text.lstrip()
    if not stripped:
        return []
    if stripped[0] in "[{":
        payload = json.loads(raw_text)
        return _rows(_event_container(payload))
    reader = csv.DictReader(raw_text.splitlines())
    return [dict(row) for row in reader]


def _event_container(payload: Any) -> Any:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in ("events", "macro_events", "calendar_events", "economic_events", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        nested = payload.get("calendar")
        if isinstance(nested, Mapping):
            return _event_container(nested)
    return []


def _normalize_events(rows: Sequence[Mapping[str, Any]], *, source_label: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    unusable = 0
    for row in rows:
        event = _normalize_event(row, source_label=source_label)
        if event is None:
            unusable += 1
        else:
            events.append(event)
    return {
        "events": sorted(events, key=lambda item: (str(item.get("scheduled_at_utc")), str(item.get("event_id")))),
        "raw_event_count": len(rows),
        "unusable_event_count": unusable,
    }


def _normalize_event(row: Mapping[str, Any], *, source_label: str) -> dict[str, Any] | None:
    scheduled = _parse_scheduled_at(row)
    if scheduled is None:
        return None
    name = str(
        row.get("event_type")
        or row.get("type")
        or row.get("event")
        or row.get("name")
        or row.get("title")
        or "macro_event"
    ).strip()
    currency = str(row.get("currency") or row.get("country") or row.get("ccy") or "USD").strip().upper()[:3] or "USD"
    impact = _normalize_impact(row.get("impact") or row.get("importance") or row.get("priority"))
    event_type = _normalize_event_type(name)
    event_id = str(row.get("event_id") or row.get("id") or "").strip()
    if not event_id:
        event_id = _stable_event_id(source_label, name, currency, scheduled.isoformat())
    before = _optional_int(row.get("blackout_before_minutes") or row.get("before_minutes"))
    after = _optional_int(row.get("blackout_after_minutes") or row.get("after_minutes"))
    out: dict[str, Any] = {
        "event_id": event_id,
        "event_type": event_type,
        "name": name,
        "currency": currency,
        "scheduled_at_utc": scheduled.isoformat(),
        "impact": impact,
        "source": "economic_calendar_feed",
        "source_label": source_label,
    }
    if before is not None:
        out["blackout_before_minutes"] = before
    if after is not None:
        out["blackout_after_minutes"] = after
    for key in ("expected", "actual", "previous", "release_status"):
        value = row.get(key)
        if value not in (None, ""):
            out[key] = value
    return out


def _parse_scheduled_at(row: Mapping[str, Any]) -> datetime | None:
    for key in ("scheduled_at_utc", "scheduled_at", "datetime", "date_time", "event_time_iso", "release_time", "time"):
        parsed = _parse_datetime(row.get(key))
        if parsed is not None:
            return parsed
    date_value = row.get("date") or row.get("Date")
    time_value = row.get("time") or row.get("Time")
    if date_value:
        combined = f"{date_value} {time_value or '00:00'}"
        return _parse_datetime(combined)
    return None


def _parse_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    variants = [raw, raw.replace("Z", "+00:00")]
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return ensure_utc(datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc))
        except ValueError:
            pass
    for candidate in variants:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return ensure_utc(parsed)
        except ValueError:
            pass
    return None


def _normalize_event_type(name: str) -> str:
    token = name.upper().replace("-", " ")
    if "NFP" in token or "NON FARM" in token or "NONFARM" in token:
        return "NFP"
    if "CPI" in token or "INFLATION" in token:
        return "CPI"
    if "FOMC" in token:
        return "FOMC"
    if "GDP" in token:
        return "GDP"
    if "UNEMPLOYMENT" in token or "JOBLESS" in token:
        return "UNEMPLOYMENT"
    if "SPEECH" in token or "POWELL" in token or "LAGARDE" in token:
        return "CENTRAL_BANK_SPEECH"
    if "RATE" in token or "INTEREST" in token or "CENTRAL BANK" in token:
        return "RATE_DECISION"
    return token[:48] or "MACRO_EVENT"


def _normalize_impact(value: Any) -> str:
    token = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if token in {"3", "HIGH", "HIGH_IMPACT", "RED"} or "HIGH" in token:
        return "HIGH"
    if token in {"2", "MED", "MEDIUM", "ORANGE"} or "MED" in token:
        return "MEDIUM"
    if token in {"1", "LOW", "YELLOW"} or "LOW" in token:
        return "LOW"
    return "HIGH"


def _stable_event_id(source: str, name: str, currency: str, scheduled: str) -> str:
    digest = hashlib.sha256(f"{source}|{name}|{currency}|{scheduled}".encode("utf-8")).hexdigest()[:16]
    return f"econ-{digest}"


def _write_cache(
    cache_path: Path,
    *,
    checked_at: datetime,
    source: Mapping[str, str],
    events: Sequence[Mapping[str, Any]],
    raw_event_count: int,
    unusable_event_count: int,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "report_kind": "cas_forex_economic_calendar_cache",
        "written_at_epoch": checked_at.timestamp(),
        "written_at_iso": checked_at.isoformat(),
        "source_kind": source["kind"],
        "source": source["value"],
        "raw_event_count": raw_event_count,
        "unusable_event_count": unusable_event_count,
        "events": list(events),
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_cache(cache_path: Path, *, checked_at: datetime) -> dict[str, Any] | None:
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, Mapping):
        return None
    out = dict(payload)
    written = _float_or_none(out.get("written_at_epoch"))
    out["cache_age_seconds"] = None if written is None else max(0.0, checked_at.timestamp() - written)
    return out


def _cache_is_fresh(cache: Mapping[str, Any], ttl_seconds: int) -> bool:
    age = _float_or_none(cache.get("cache_age_seconds"))
    return age is not None and age <= ttl_seconds


def _report(
    *,
    status: str,
    checked_at: datetime,
    source_kind: str,
    source: str,
    cache_path: Path,
    ttl_seconds: int,
    fail_closed: bool,
    events: Sequence[Mapping[str, Any]],
    raw_event_count: int,
    unusable_event_count: int,
    detail: str,
    cache_written_at_epoch: float | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    age = None if cache_written_at_epoch is None else max(0.0, checked_at.timestamp() - cache_written_at_epoch)
    configured = bool(source)
    source_status = "CONFIGURED" if configured else "UNCONFIGURED"
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "source_status": source_status,
        "configured": configured,
        "checked_at_iso": checked_at.isoformat(),
        "source_kind": source_kind,
        "source": _mask_source(source),
        "source_is_http": source_kind in {"http", "https"},
        "cache_path": str(cache_path),
        "cache_ttl_seconds": ttl_seconds,
        "cache_written_at_epoch": cache_written_at_epoch,
        "cache_age_seconds": age,
        "cache_stale": bool(age is not None and age > ttl_seconds),
        "fail_closed_on_error": fail_closed,
        "event_count": len(events),
        "raw_event_count": raw_event_count,
        "unusable_event_count": unusable_event_count,
        "events": list(events),
        "detail": detail,
        "error": error,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _mask_source(source: str) -> str:
    if not source:
        return ""
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return source


def _rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
