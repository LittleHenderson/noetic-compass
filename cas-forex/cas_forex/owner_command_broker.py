"""Owner command broker — preview → typed CONFIRM → receipt.

Chat (and the UI) proposes an owner action; the broker answers with a PREVIEW:
the current state, the exact change, its effects, any blockers, and the phrase
to type to confirm. On ``execute`` with the matching confirmation, it runs the
SAME gated service function the UI buttons already call — it never reimplements
or bypasses a gate — and writes a durable RECEIPT.

This lets chat ACT, not just talk, while keeping every existing safety gate in
place. For higher-stakes commands (arming live, moving money) the underlying
function keeps its own gates (owner live-authorization, ``?confirm``, edge PASS);
the typed CONFIRM here is an ADDITIONAL owner step, never a replacement. The
broker's job is to make the action legible (show exactly what will happen) and
auditable (receipt), and to require an explicit, change-specific confirmation.

Part A ships the settings commands (set_ai_dial, set_risk_cap, set_lan_mode).
The live-arm and money commands are registered in a later part and ride the same
engine.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPTS_PATH = REPO_ROOT / "runtime" / "owner-command-receipts.jsonl"

REPORT_KIND = "cas_forex_owner_command"

CLAIM_BOUNDARY = (
    "The owner command broker previews an owner action, requires a typed "
    "confirmation, then runs the SAME gated service function the UI buttons use "
    "and writes a receipt. It never bypasses a gate: arming live and moving money "
    "still pass their own owner-authorization / confirm / edge gates. The typed "
    "CONFIRM is an extra owner step, not a replacement for those gates."
)

_LOCK = threading.RLock()
_RECEIPTS_PATH = DEFAULT_RECEIPTS_PATH


def set_receipts_path_for_tests(path: Optional[Path]) -> None:
    global _RECEIPTS_PATH
    _RECEIPTS_PATH = Path(path) if path is not None else DEFAULT_RECEIPTS_PATH


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
@dataclass
class Preview:
    command: str
    params: dict[str, Any]
    title: str
    current: Any
    proposed: Any
    effects: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    confirm_phrase: str = "CONFIRM"

    @property
    def ready(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": REPORT_KIND,
            "command": self.command,
            "params": self.params,
            "title": self.title,
            "current": self.current,
            "proposed": self.proposed,
            "effects": self.effects,
            "blockers": self.blockers,
            "ready": self.ready,
            "confirm_phrase": self.confirm_phrase,
            "claim_boundary": CLAIM_BOUNDARY,
        }


@dataclass
class Command:
    name: str
    summary: str
    params: list[dict[str, str]]  # [{name, type, help}]
    build_preview: Callable[[dict[str, Any]], Preview]
    apply: Callable[[dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _authority():
    from cas_forex.ai_control_authority import get_authority

    return get_authority()


def _dial_value(lever: str) -> Any:
    snap = _authority().snapshot()
    values = (snap.get("control_surface") or {}).get("values") or {}
    return values.get(lever)


def _confirmation_matches(required: str, provided: Any) -> bool:
    return str(provided or "").strip().upper() == str(required or "").strip().upper()


# ---------------------------------------------------------------------------
# Command: set_ai_dial  ->  ai_control_authority.ai_adjust (owner-fenced dial)
# ---------------------------------------------------------------------------
def _preview_set_ai_dial(params: dict[str, Any]) -> Preview:
    from cas_forex.ai_control_surface import LEVER_NAMES

    lever = str(params.get("lever") or "")
    value = params.get("value")
    blockers: list[str] = []
    if lever not in LEVER_NAMES:
        blockers.append(f"Unknown dial '{lever}'. Known: {sorted(LEVER_NAMES)}")
    current = _dial_value(lever) if not blockers else None
    effects = []
    if not blockers:
        effects.append(
            f"Sets '{lever}' from {current!r} to {value!r} (clamped to your owner "
            "bounds; widen the envelope first to go beyond them)."
        )
    return Preview(
        command="set_ai_dial",
        params={"lever": lever, "value": value},
        title=f"Set AI dial '{lever}' to {value}",
        current=current,
        proposed=value,
        effects=effects,
        blockers=blockers,
        confirm_phrase="CONFIRM",
    )


def _apply_set_ai_dial(params: dict[str, Any]) -> dict[str, Any]:
    lever = str(params.get("lever") or "")
    value = params.get("value")
    before = _dial_value(lever)
    result = _authority().ai_adjust(lever, value, reason="owner command broker")
    return {
        "lever": lever,
        "requested": value,
        "before": before,
        "after": _dial_value(lever),
        "clamped": bool(result.get("owner_clamped") or result.get("clamped")),
        "reason": result.get("reason") or result.get("owner_reason"),
    }


# ---------------------------------------------------------------------------
# Command: set_risk_cap  ->  risk_control.set_risk_control_overrides
# ---------------------------------------------------------------------------
_RISK_CAPS = ("max_concurrent_trades", "max_total_exposure_lots", "max_loss_cap_usd", "max_drawdown_pct")


def _risk_snapshot() -> dict[str, Any]:
    from cas_forex.risk_control import resolve_risk_control

    return resolve_risk_control().to_dict()


def _preview_set_risk_cap(params: dict[str, Any]) -> Preview:
    cap = str(params.get("cap") or "")
    raw = params.get("value")
    # value may be a number (a cap) or null/None (UNLIMITED — remove the cap).
    value: Any = None if raw in (None, "", "null", "none", "unlimited") else raw
    blockers: list[str] = []
    if cap not in _RISK_CAPS:
        blockers.append(f"Unknown risk cap '{cap}'. Known: {list(_RISK_CAPS)}")
    if value is not None:
        try:
            value = float(value)
            if value < 0:
                blockers.append(f"{cap} must be >= 0 or null (unlimited)")
        except (TypeError, ValueError):
            blockers.append(f"{cap} needs a number or null (unlimited), got {raw!r}")
    current = _risk_snapshot().get(cap) if not blockers else None
    effect = (
        f"Removes the '{cap}' cap (UNLIMITED)."
        if value is None
        else f"Caps '{cap}' at {value}."
    ) + " Enforced at the dispatch chokepoint immediately (paper and live)."
    return Preview(
        command="set_risk_cap",
        params={"cap": cap, "value": value},
        title=(f"Set risk cap '{cap}' to " + ("UNLIMITED" if value is None else str(value))),
        current=current,
        proposed=("UNLIMITED" if value is None else value),
        effects=[] if blockers else [effect],
        blockers=blockers,
        confirm_phrase="CONFIRM",
    )


def _apply_set_risk_cap(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex.risk_control import set_risk_control_overrides

    cap = str(params.get("cap") or "")
    value = params.get("value")  # already normalized by preview caller
    before = _risk_snapshot().get(cap)
    set_risk_control_overrides(**{cap: value})
    return {"cap": cap, "requested": value, "before": before, "after": _risk_snapshot().get(cap)}


# ---------------------------------------------------------------------------
# Command: set_lan_mode  ->  owner_auth.set_lan_mode
# ---------------------------------------------------------------------------
def _preview_set_lan_mode(params: dict[str, Any]) -> Preview:
    from cas_forex import owner_auth

    enabled = bool(params.get("enabled"))
    current = owner_auth.lan_mode_enabled()
    effect = (
        "Turns ON authenticated LAN access — paired devices (your phone) may reach "
        "the cockpit. Your own PC always works regardless."
        if enabled
        else "Turns OFF LAN access — only this PC can reach the cockpit."
    )
    return Preview(
        command="set_lan_mode",
        params={"enabled": enabled},
        title=f"Turn LAN access {'ON' if enabled else 'OFF'}",
        current=current,
        proposed=enabled,
        effects=[effect],
        blockers=[],
        confirm_phrase="CONFIRM",
    )


def _apply_set_lan_mode(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex import owner_auth

    enabled = bool(params.get("enabled"))
    before = owner_auth.lan_mode_enabled()
    owner_auth.set_lan_mode(enabled)
    return {"before": before, "after": owner_auth.lan_mode_enabled()}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
COMMANDS: dict[str, Command] = {
    "set_ai_dial": Command(
        name="set_ai_dial",
        summary="Set an AI operator dial (edge threshold, risk %, max positions, trailing stop, symbols, …), clamped to your owner bounds.",
        params=[
            {"name": "lever", "type": "string", "help": "dial name, e.g. edge_threshold"},
            {"name": "value", "type": "number|list", "help": "the value to set"},
        ],
        build_preview=_preview_set_ai_dial,
        apply=_apply_set_ai_dial,
    ),
    "set_risk_cap": Command(
        name="set_risk_cap",
        summary="Set (or remove, with null) a risk cap enforced at the dispatch chokepoint.",
        params=[
            {"name": "cap", "type": "string", "help": "one of: " + ", ".join(_RISK_CAPS)},
            {"name": "value", "type": "number|null", "help": "a number, or null for UNLIMITED"},
        ],
        build_preview=_preview_set_risk_cap,
        apply=_apply_set_risk_cap,
    ),
    "set_lan_mode": Command(
        name="set_lan_mode",
        summary="Turn authenticated LAN (phone) access on or off.",
        params=[{"name": "enabled", "type": "boolean", "help": "true = allow paired devices"}],
        build_preview=_preview_set_lan_mode,
        apply=_apply_set_lan_mode,
    ),
}


def catalog() -> list[dict[str, Any]]:
    return [
        {"name": c.name, "summary": c.summary, "params": c.params}
        for c in COMMANDS.values()
    ]


def preview(command: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cmd = COMMANDS.get(str(command))
    if cmd is None:
        return {
            "report_kind": REPORT_KIND,
            "command": command,
            "ready": False,
            "blockers": [f"Unknown command '{command}'. Known: {sorted(COMMANDS)}"],
        }
    return cmd.build_preview(dict(params or {})).to_dict()


def execute(
    command: str,
    params: Optional[dict[str, Any]] = None,
    confirmation: str = "",
) -> dict[str, Any]:
    """Re-check the preview, verify the typed confirmation, apply, receipt."""
    params = dict(params or {})
    cmd = COMMANDS.get(str(command))
    if cmd is None:
        return {"ok": False, "applied": False, "reason": f"Unknown command '{command}'."}

    prev = cmd.build_preview(params)
    if not prev.ready:
        return {"ok": False, "applied": False, "reason": "blocked", "preview": prev.to_dict()}
    if not _confirmation_matches(prev.confirm_phrase, confirmation):
        return {
            "ok": False,
            "applied": False,
            "reason": "confirmation required",
            "need_confirmation": prev.confirm_phrase,
            "preview": prev.to_dict(),
        }
    # Use the preview's normalized params (e.g. null-coerced risk value) so the
    # applied change is exactly what was previewed and confirmed.
    result = cmd.apply(prev.params)
    receipt = _write_receipt(command=cmd.name, params=prev.params, title=prev.title, result=result)
    return {"ok": True, "applied": True, "receipt": receipt, "result": result}


# ---------------------------------------------------------------------------
# Receipts (append-only, durable)
# ---------------------------------------------------------------------------
def _write_receipt(*, command: str, params: dict[str, Any], title: str, result: dict[str, Any]) -> dict[str, Any]:
    receipt = {
        "report_kind": "cas_forex_owner_command_receipt",
        "receipt_id": f"cmd-{uuid.uuid4().hex[:12]}",
        "at": utc_now().isoformat(),
        "command": command,
        "title": title,
        "params": params,
        "result": result,
    }
    with _LOCK:
        _RECEIPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                with _RECEIPTS_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(receipt, default=str) + "\n")
                return receipt
            except OSError as exc:  # transient OneDrive/AV lock
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            # Never let a receipt-write failure undo an applied change; surface it.
            receipt["receipt_write_error"] = str(last_error)
    return receipt


def recent_receipts(limit: int = 25) -> list[dict[str, Any]]:
    with _LOCK:
        if not _RECEIPTS_PATH.exists():
            return []
        try:
            lines = _RECEIPTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
    out: list[dict[str, Any]] = []
    for line in lines[-max(1, limit):]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))


__all__ = [
    "CLAIM_BOUNDARY",
    "COMMANDS",
    "Command",
    "Preview",
    "catalog",
    "execute",
    "preview",
    "recent_receipts",
    "set_receipts_path_for_tests",
]
