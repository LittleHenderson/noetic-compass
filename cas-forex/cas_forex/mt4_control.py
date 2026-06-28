"""Owner-controlled MT4 mailbox bridge: enable the file route + point it at the
MT4 terminal's mailbox folder, all in-app (no env vars, no restart).

The MT4 Expert Advisor file-mailbox is the RELIABLE real-order route — it is
file-based, so it does not suffer the MetaTrader5 Python IPC instability. It
existed but was env-only (MT4_ENABLED, MT4_MAILBOX_DIR). This module is the
owner override for those two inputs plus a reader for the EA's heartbeat file so
the owner can see whether the EA is attached and writing.

Overrides are process-global (single-owner cockpit) and reset on restart; the
static config values remain the persistent defaults. Nothing here authorizes
live money — enabling writes PAPER_MT4 command intents the EA acknowledges.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# A heartbeat written within this many seconds counts as "fresh" (the EA rewrites
# heartbeat.json every couple of seconds; allow slack for slower timer settings).
HEARTBEAT_FRESH_SECONDS = 15.0

_OVERRIDES: Dict[str, Any] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class MT4Control:
    enabled: bool
    mailbox_dir: str


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def resolve_mt4_control(config: Any = None) -> MT4Control:
    """Effective MT4 route settings: owner override over static config."""

    config = _resolve_config(config)
    with _lock:
        enabled_override = _OVERRIDES.get("enabled")
        dir_override = _OVERRIDES.get("mailbox_dir")
    enabled = (
        bool(enabled_override)
        if enabled_override is not None
        else bool(getattr(config, "mt4_enabled", False))
    )
    mailbox_dir = (
        str(dir_override)
        if dir_override
        else str(getattr(config, "mt4_mailbox_dir", None) or "mt4_mailbox")
    )
    return MT4Control(enabled=enabled, mailbox_dir=mailbox_dir)


def set_mt4_control_overrides(
    *,
    enabled: Optional[bool] = None,
    mailbox_dir: Optional[str] = None,
) -> MT4Control:
    """Set owner MT4 overrides. Only the arguments you pass are changed."""

    with _lock:
        if enabled is not None:
            _OVERRIDES["enabled"] = bool(enabled)
        if mailbox_dir is not None:
            cleaned = str(mailbox_dir).strip()
            if not cleaned:
                raise ValueError("mailbox_dir must not be empty")
            _OVERRIDES["mailbox_dir"] = cleaned
    return resolve_mt4_control()


def clear_mt4_control_overrides() -> None:
    """Drop all MT4 overrides (revert to config / env defaults)."""

    with _lock:
        _OVERRIDES.clear()


def read_ea_heartbeat(mailbox_dir: str | Path) -> Dict[str, Any]:
    """Read + age the EA's heartbeat.json so the owner can see the link is alive.

    Freshness is measured from the file's modification time (the EA rewrites it
    every couple of seconds), which is robust to the EA's internal time format /
    timezone. The EA's reported fields are surfaced as informational.
    """

    path = Path(mailbox_dir) / "heartbeat.json"
    if not path.exists():
        return {
            "present": False,
            "fresh": False,
            "state": None,
            "account_id_hash": None,
            "server": None,
            "live_trading_allowed": None,
            "time": None,
            "age_seconds": None,
        }

    age_seconds: Optional[float] = None
    try:
        from cas_forex.time_utils import utc_now

        age_seconds = round(utc_now().timestamp() - path.stat().st_mtime, 1)
    except Exception:
        age_seconds = None

    data: Dict[str, Any] = {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    fresh = age_seconds is not None and 0 <= age_seconds <= HEARTBEAT_FRESH_SECONDS
    return {
        "present": True,
        "fresh": fresh,
        "state": data.get("state"),
        "account_id_hash": data.get("account_id_hash"),
        "server": data.get("server"),
        "live_trading_allowed": data.get("live_trading_allowed"),
        "time": data.get("time") or data.get("created_at") or data.get("timestamp"),
        "age_seconds": age_seconds,
        "schema": data.get("schema"),
    }


def build_mt4_control_report(config: Any = None) -> Dict[str, Any]:
    """Owner-facing report: enable state, mailbox dir, and EA heartbeat status."""

    ctrl = resolve_mt4_control(config)
    heartbeat = read_ea_heartbeat(ctrl.mailbox_dir)
    if not heartbeat["present"]:
        link = "NO_HEARTBEAT"
    elif heartbeat["fresh"]:
        link = "LIVE"
    else:
        link = "STALE"
    return {
        "report_kind": "cas_forex_mt4_control",
        "enabled": ctrl.enabled,
        "mailbox_dir": ctrl.mailbox_dir,
        "heartbeat": heartbeat,
        "link_status": link,
        "note": (
            "Enabling writes PAPER_MT4 command intents the EA acknowledges via the "
            "shared mailbox folder. Point the mailbox dir at the MT4 terminal's "
            "MQL4\\Files\\CASForexMailbox folder and attach CASForexBridgeEA. Then "
            "select platform 'mt4' in Broker Control so dispatch routes through it. "
            "This is the stable, file-based real-order route (not the flaky MT5 IPC)."
        ),
        "claim_boundary": (
            "Enabling the MT4 route does not authorize live money. Live MT4 also "
            "requires the EA's own LiveTradingAllowed input and per-command "
            "authorization; this toggle stays paper/demo."
        ),
    }
