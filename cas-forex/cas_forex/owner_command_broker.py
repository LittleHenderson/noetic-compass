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
    binding: dict[str, Any] | None = None
    contract_rows: list[dict[str, Any]] = field(default_factory=list)
    journal_required: bool = False
    journal_prompt: str = ""
    journal_minimum_length: int | None = None

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
            "binding": self.binding,
            "contract_rows": self.contract_rows,
            "journal_required": self.journal_required,
            "journal_prompt": self.journal_prompt,
            "journal_minimum_length": self.journal_minimum_length,
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


def _norm_confirm(text: Any) -> str:
    # Upper-case, trim, and collapse internal whitespace so "send  $500  withdraw"
    # matches "SEND $500 WITHDRAW".
    return " ".join(str(text or "").strip().upper().split())


def _confirmation_matches(required: str, provided: Any) -> bool:
    return _norm_confirm(provided) == _norm_confirm(required)


# ---------------------------------------------------------------------------
# Command: set_ai_dial  ->  ai_control_authority.ai_adjust (owner-fenced dial)
# ---------------------------------------------------------------------------
def _preview_set_ai_dial(params: dict[str, Any]) -> Preview:
    lever = str(params.get("lever") or "")
    value = params.get("value")
    journal_reason = str(params.get("journal_reason") or params.get("reason") or "")
    preview = _authority().preview_ai_adjust(lever, value, reason=journal_reason)
    blockers = [str(item) for item in (preview.get("blockers") or [])]
    effects = [str(item) for item in (preview.get("effects") or [])]
    current = preview.get("current")
    proposed = preview.get("proposed", value)
    impact = preview.get("impact") if isinstance(preview.get("impact"), dict) else {}
    binding = preview.get("binding") if isinstance(preview.get("binding"), dict) else None
    contract_rows = (
        [row for row in (preview.get("contract_rows") or []) if isinstance(row, dict)]
        if isinstance(preview.get("contract_rows"), list)
        else []
    )
    journal = preview.get("anti_impulse_journal") if isinstance(preview.get("anti_impulse_journal"), dict) else {}
    label = str(impact.get("label") or lever)
    return Preview(
        command="set_ai_dial",
        params={"lever": lever, "value": value, "journal_reason": journal_reason},
        title=f"Set AI dial '{label}' to {proposed}",
        current=current,
        proposed=proposed,
        effects=effects,
        blockers=blockers,
        confirm_phrase="CONFIRM",
        binding=binding,
        contract_rows=contract_rows,
        journal_required=bool(preview.get("journal_prompt_required")),
        journal_prompt=str(preview.get("journal_prompt") or ""),
        journal_minimum_length=(
            int(journal.get("minimum_reason_length"))
            if journal.get("minimum_reason_length") is not None
            else None
        ),
    )


def _apply_set_ai_dial(params: dict[str, Any]) -> dict[str, Any]:
    lever = str(params.get("lever") or "")
    value = params.get("value")
    journal_reason = str(params.get("journal_reason") or params.get("reason") or "")
    before = _dial_value(lever)
    result = _authority().ai_adjust(
        lever,
        value,
        reason=journal_reason,
        source="owner_command_broker.set_ai_dial",
    )
    return {
        "lever": lever,
        "requested": value,
        "before": before,
        "after": _dial_value(lever),
        "clamped": bool(result.get("owner_clamped") or result.get("clamped")),
        "reason": result.get("reason") or result.get("owner_reason"),
        "journal_recorded": bool(journal_reason),
    }


# ---------------------------------------------------------------------------
# Command: set_risk_cap  ->  risk_control.set_risk_control_overrides
# ---------------------------------------------------------------------------
_RISK_CAPS = ("max_concurrent_trades", "max_total_exposure_lots", "max_loss_cap_usd", "max_drawdown_pct")


def _risk_snapshot() -> dict[str, Any]:
    from cas_forex.risk_control import resolve_risk_control

    return resolve_risk_control().to_dict()


def _preview_set_risk_cap(params: dict[str, Any]) -> Preview:
    from cas_forex.risk_control import RISK_LOOSEN_CONFIRM_PHRASE, assess_risk_control_update

    cap = str(params.get("cap") or "")
    raw = params.get("value")
    journal_reason = str(params.get("journal_reason") or params.get("reason") or "")
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
    assessment = assess_risk_control_update({cap: value}, journal_reason=journal_reason) if not blockers else {}
    cooldown = assessment.get("cooldown") if isinstance(assessment.get("cooldown"), dict) else {}
    journal = assessment.get("journal") if isinstance(assessment.get("journal"), dict) else {}
    if bool(assessment.get("requires_journal_reason")) and not bool(journal.get("satisfied")):
        blockers.extend(str(item) for item in (journal.get("blockers") or []))
    if bool(cooldown.get("active")):
        blockers.append(
            "Risk loosening cooldown is active after a recent loosening; "
            f"try again in {int(cooldown.get('remaining_seconds') or 0)} seconds, or tighten caps now."
        )
    effect = (
        f"Removes the '{cap}' cap (UNLIMITED)."
        if value is None
        else f"Caps '{cap}' at {value}."
    ) + " Enforced at the dispatch chokepoint immediately (paper and live)."
    if assessment.get("requires_confirmation"):
        effect += " Because real-money controls are armed, this loosen/remove action needs the stronger confirmation phrase."
    if assessment.get("requires_journal_reason"):
        effect += " This loosen/remove action also requires an anti-impulse journal reason."
    return Preview(
        command="set_risk_cap",
        params={"cap": cap, "value": value, "journal_reason": journal_reason},
        title=(f"Set risk cap '{cap}' to " + ("UNLIMITED" if value is None else str(value))),
        current=current,
        proposed=("UNLIMITED" if value is None else value),
        effects=[] if blockers else [effect],
        blockers=blockers,
        confirm_phrase=RISK_LOOSEN_CONFIRM_PHRASE if assessment.get("requires_confirmation") else "CONFIRM",
        journal_required=bool(assessment.get("requires_journal_reason")),
        journal_prompt=str(journal.get("prompt") or assessment.get("journal_prompt") or ""),
        journal_minimum_length=(
            int(journal.get("minimum_reason_length"))
            if journal.get("minimum_reason_length") is not None
            else None
        ),
    )


def _apply_set_risk_cap(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex.risk_control import assess_risk_control_update, set_risk_control_overrides

    cap = str(params.get("cap") or "")
    value = params.get("value")  # already normalized by preview caller
    journal_reason = str(params.get("journal_reason") or "")
    before = _risk_snapshot().get(cap)
    assessment = assess_risk_control_update({cap: value}, journal_reason=journal_reason)
    set_risk_control_overrides(
        **{cap: value},
        audit_source="owner_command_broker.set_risk_cap",
        audit_assessment=assessment,
        audit_confirm_supplied=True,
        audit_journal_reason=journal_reason,
    )
    return {
        "cap": cap,
        "requested": value,
        "before": before,
        "after": _risk_snapshot().get(cap),
        "journal_recorded": bool(journal_reason),
    }


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
# Command: set_profit_target  ->  ai_control_authority.owner_update
# The owner's daily reporting objective (and cap + monthly objective). A target
# deficit is never trade authority: it cannot manufacture edge or loosen risk.
# The daily cap may suppress new entries after it is reached.
# ---------------------------------------------------------------------------
def _owner_envelope() -> dict[str, Any]:
    return dict(_authority().snapshot().get("owner_envelope") or {})


def _preview_set_profit_target(params: dict[str, Any]) -> Preview:
    env = _owner_envelope()
    field_map = {
        "daily_target": "daily_profit_floor_usd",
        "daily_cap": "daily_profit_cap_usd",
        "monthly_target": "monthly_profit_target_usd",
    }
    changes: dict[str, float] = {}
    blockers: list[str] = []
    for key, envelope_key in field_map.items():
        if params.get(key) is None:
            continue
        try:
            val = float(params[key])
        except (TypeError, ValueError):
            blockers.append(f"{key} must be a number, got {params[key]!r}")
            continue
        if val < 0:
            blockers.append(f"{key} must be >= 0")
            continue
        changes[envelope_key] = val
    if not changes and not blockers:
        blockers.append("Nothing to set — provide daily_target, daily_cap, and/or monthly_target.")
    # Effective daily floor/cap after the change: floor must not exceed cap.
    eff_floor = changes.get("daily_profit_floor_usd", float(env.get("daily_profit_floor_usd") or 0.0))
    eff_cap = changes.get("daily_profit_cap_usd", float(env.get("daily_profit_cap_usd") or 0.0))
    if eff_cap and eff_floor > eff_cap:
        blockers.append(f"daily target ${eff_floor:g} can't exceed the daily cap ${eff_cap:g}.")
    current = {
        "daily_target_usd": env.get("daily_profit_floor_usd"),
        "daily_cap_usd": env.get("daily_profit_cap_usd"),
        "monthly_target_usd": env.get("monthly_profit_target_usd"),
    }
    effects = []
    if not blockers:
        if "daily_profit_floor_usd" in changes:
            effects.append(f"Daily profit objective → ${changes['daily_profit_floor_usd']:g} (reporting reference only; never a trade quota or reason to loosen risk).")
        if "daily_profit_cap_usd" in changes:
            effects.append(f"Daily cap → ${changes['daily_profit_cap_usd']:g} (once hit, it stops opening new trades that day).")
        if "monthly_profit_target_usd" in changes:
            effects.append(f"Monthly target → ${changes['monthly_profit_target_usd']:g} (sets the daily pace).")
    return Preview(
        command="set_profit_target",
        params={k: v for k, v in {"daily_target": params.get("daily_target"), "daily_cap": params.get("daily_cap"), "monthly_target": params.get("monthly_target")}.items() if v is not None},
        title="Set daily profit objective",
        current=current,
        proposed={k.replace("_usd", ""): v for k, v in changes.items()},
        effects=effects,
        blockers=blockers,
        confirm_phrase="CONFIRM",
    )


def _apply_set_profit_target(params: dict[str, Any]) -> dict[str, Any]:
    field_map = {
        "daily_target": "daily_profit_floor_usd",
        "daily_cap": "daily_profit_cap_usd",
        "monthly_target": "monthly_profit_target_usd",
    }
    changes = {field_map[k]: float(params[k]) for k in field_map if params.get(k) is not None}
    before = _owner_envelope()
    _authority().owner_update(source="owner_command_broker.set_profit_target", **changes)
    after = _owner_envelope()
    return {
        "changed": list(changes),
        "before": {k: before.get(k) for k in changes},
        "after": {k: after.get(k) for k in changes},
    }


# ---------------------------------------------------------------------------
# Command: arm_live_switch  ->  live_enable_control.set_live_enable_overrides
# Arms/disarms an owner authorization switch. This authorizes a CAPABILITY; it
# does not itself place a trade or move money — the dispatch/movement chokepoints
# still require this plus their own gates (edge PASS, ?confirm, provider config).
# ---------------------------------------------------------------------------
_LIVE_SWITCHES = (
    "personal_account_ack",
    "no_pooled_capital_ack",
    "live_mode",
    "prefer_mt5",
    "owner_enable_live_trading",
    "live_trading_licensed",
    "owner_enable_broker_accept",
    "owner_enable_auto_deposit",
    "owner_enable_bank_card_movement",
    "owner_enable_payout_automation",
)


def _live_switch_current(switch: str) -> Any:
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return bool(getattr(apply_live_enable_overrides(None), switch, False))
    except Exception:
        return None


def _preview_arm_live_switch(params: dict[str, Any]) -> Preview:
    switch = str(params.get("switch") or "")
    enabled = bool(params.get("enabled"))
    blockers: list[str] = []
    if switch not in _LIVE_SWITCHES:
        blockers.append(f"Unknown live switch '{switch}'. Known: {list(_LIVE_SWITCHES)}")
    current = _live_switch_current(switch) if not blockers else None
    consequence = ""
    try:
        from cas_forex.live_enable_control import _FLAG_META  # noqa: SLF001 (same-package read)

        consequence = str((_FLAG_META.get(switch) or {}).get("consequence") or "")
    except Exception:
        pass
    verb = "ARM" if enabled else "DISARM"
    effects = []
    if not blockers:
        effects.append(
            f"{verb}s owner switch '{switch}'."
            + (f" {consequence}" if consequence else "")
            + " This AUTHORIZES the capability; the trade/money chokepoints still "
            "enforce their own gates (edge PASS, ?confirm, provider config)."
        )
    return Preview(
        command="arm_live_switch",
        params={"switch": switch, "enabled": enabled},
        title=f"{verb} live switch '{switch}'",
        current=current,
        proposed=enabled,
        effects=effects,
        blockers=blockers,
        # Deliberate, switch-specific confirmation for a higher-stakes action.
        confirm_phrase=f"{verb} {switch}",
    )


def _apply_arm_live_switch(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex.live_enable_control import set_live_enable_overrides

    switch = str(params.get("switch") or "")
    enabled = bool(params.get("enabled"))
    before = _live_switch_current(switch)
    set_live_enable_overrides(
        audit_source="owner_command_broker.arm_live_switch",
        confirm_supplied=True,
        **{switch: enabled},
    )
    after = _live_switch_current(switch)
    _notify_live_switch_changed(switch=switch, before=before, after=after, source="owner_command_broker.arm_live_switch")
    return {"switch": switch, "before": before, "after": after}


# ---------------------------------------------------------------------------
# Command: disarm_real_money  ->  live_enable_control.disarm_real_money_overrides
# Turns OFF every live/money capability switch while preserving setup/credentials.
# ---------------------------------------------------------------------------
def _preview_disarm_real_money(params: dict[str, Any]) -> Preview:
    from cas_forex.live_enable_control import REAL_MONEY_DISARM_CONFIRM_PHRASE, REAL_MONEY_DISARM_KEYS

    current = {key: _live_switch_current(key) for key in REAL_MONEY_DISARM_KEYS}
    already_off = all(value is False for value in current.values())
    effects = [
        "Turns OFF live_mode, live trading authority, broker ACCEPT, auto-deposit, bank/card movement, and payout automation.",
        "Keeps broker credentials, provider setup, account acknowledgments, evidence, and paper/demo operation intact.",
    ]
    if already_off:
        effects.append("All real-money capability switches are already off; running this is idempotent.")
    return Preview(
        command="disarm_real_money",
        params={},
        title="Disarm real-money switches",
        current=current,
        proposed={key: False for key in REAL_MONEY_DISARM_KEYS},
        effects=effects,
        blockers=[],
        confirm_phrase=REAL_MONEY_DISARM_CONFIRM_PHRASE,
    )


def _apply_disarm_real_money(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex.live_enable_control import disarm_real_money_overrides

    before = _preview_disarm_real_money({}).current
    result = disarm_real_money_overrides(
        audit_source="owner_command_broker.disarm_real_money",
        confirm_supplied=True,
    )
    after = result.get("after") if isinstance(result, dict) else {}
    if isinstance(before, dict) and isinstance(after, dict):
        for switch, before_value in before.items():
            after_value = after.get(switch)
            if before_value != after_value:
                _notify_live_switch_changed(
                    switch=str(switch),
                    before=before_value,
                    after=after_value,
                    source="owner_command_broker.disarm_real_money",
                )
    return result


def _notify_live_switch_changed(*, switch: str, before: Any, after: Any, source: str) -> None:
    try:
        from cas_forex.critical_notifications import (
            build_live_switch_changed_event,
            emit_critical_notification,
        )

        emit_critical_notification(
            build_live_switch_changed_event(switch=switch, before=before, after=after, source=source),
            source=source,
        )
    except Exception:
        return


# ---------------------------------------------------------------------------
# Command: move_money  ->  MovementEngine (deposit / withdraw / payout)
# The engine gate-checks fail-closed: the payment provider is only touched if the
# matching owner capability gate authorizes it, and the default provider is the
# SIMULATED one unless the owner configured a real provider. This command's
# strong typed confirmation is the broker's equivalent of the route's ?confirm.
# ---------------------------------------------------------------------------
_MONEY_ACTIONS = {
    "deposit": "auto_deposit",
    "withdraw": "bank_card_movement",
    "payout": "payout_automation",
}


def _preview_move_money(params: dict[str, Any]) -> Preview:
    action = str(params.get("action") or "").lower()
    raw_amount = params.get("amount_usd")
    blockers: list[str] = []
    if action not in _MONEY_ACTIONS:
        blockers.append(f"Unknown action '{action}'. Known: {sorted(_MONEY_ACTIONS)}")
    amount = 0.0
    try:
        amount = float(raw_amount)
        if amount <= 0:
            blockers.append("amount_usd must be > 0")
    except (TypeError, ValueError):
        blockers.append(f"amount_usd must be a number, got {raw_amount!r}")

    gate_status: Any = None
    if action in _MONEY_ACTIONS:
        try:
            from cas_forex import runtime_gates

            decision = runtime_gates.evaluate_capability(_MONEY_ACTIONS[action]).to_dict()
            gate_status = {
                "capability": _MONEY_ACTIONS[action],
                "authorized": bool(decision.get("authorized")),
                "missing": decision.get("missing_requirements") or decision.get("missing") or [],
            }
            if not gate_status["authorized"]:
                miss = gate_status["missing"]
                blockers.append(
                    f"'{_MONEY_ACTIONS[action]}' is not authorized yet — arm it first "
                    f"(arm_live_switch). Missing: {miss or 'owner enablement'}."
                )
        except Exception as exc:
            blockers.append(f"could not read money gate: {exc}")

    effects = []
    if not blockers:
        effects.append(
            f"Moves ${amount:g} ({action}). Uses the configured payment provider — "
            "SIMULATED unless you've set a real provider. Fail-closed: the engine "
            "re-checks the gate before touching any provider."
        )
    return Preview(
        command="move_money",
        params={"action": action, "amount_usd": amount, "destination_id": params.get("destination_id"), "source_id": params.get("source_id")},
        title=f"{action.title()} ${amount:g}",
        current=gate_status,
        proposed=f"${amount:g} {action}",
        effects=effects,
        blockers=blockers,
        # Strong, amount-and-action-specific confirmation for moving money.
        confirm_phrase=f"SEND ${amount:g} {action.upper()}",
    )


def _apply_move_money(params: dict[str, Any]) -> dict[str, Any]:
    from cas_forex.money_movement_dispatch import dispatch_money_movement

    action = str(params.get("action") or "").lower()
    amount = float(params.get("amount_usd") or 0.0)
    kind = "withdrawal" if action == "withdraw" else action
    key = f"owner-command-{uuid.uuid4().hex}"
    dispatch = dispatch_money_movement(
        kind=kind,
        amount_usd=amount,
        idempotency_key=key,
        source_id=params.get("source_id"),
        destination_id=params.get("destination_id"),
        purpose="owner_command_move_money",
        authority_mode="MANUAL",
        require_real_provider=False,
    )
    movement = dispatch.get("movement")
    payload = dict(movement) if isinstance(movement, dict) else {
        "status": dispatch.get("status"),
        "reason": dispatch.get("detail"),
        "provider_touched": dispatch.get("provider_touched", False),
    }
    payload["idempotency_key"] = key
    payload["money_movement_dispatch"] = dispatch
    return payload


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
    "set_profit_target": Command(
        name="set_profit_target",
        summary="Set a daily profit objective, daily cap, and monthly objective. A deficit never creates a trade or loosens risk; the cap may suppress new entries.",
        params=[
            {"name": "daily_target", "type": "number?", "help": "daily reporting objective in USD; not a trade quota"},
            {"name": "daily_cap", "type": "number?", "help": "stop opening new trades once the day hits this USD"},
            {"name": "monthly_target", "type": "number?", "help": "monthly target in USD (sets the pace)"},
        ],
        build_preview=_preview_set_profit_target,
        apply=_apply_set_profit_target,
    ),
    "arm_live_switch": Command(
        name="arm_live_switch",
        summary="Arm/disarm an owner authorization switch (live trading, broker accept, deposit/withdraw/payout enablement). Authorizes a capability; the chokepoints still enforce their own gates.",
        params=[
            {"name": "switch", "type": "string", "help": "one of: " + ", ".join(_LIVE_SWITCHES)},
            {"name": "enabled", "type": "boolean", "help": "true = arm, false = disarm"},
        ],
        build_preview=_preview_arm_live_switch,
        apply=_apply_arm_live_switch,
    ),
    "disarm_real_money": Command(
        name="disarm_real_money",
        summary="Turn OFF every live/money capability switch immediately while preserving paper/demo operation and saved setup.",
        params=[],
        build_preview=_preview_disarm_real_money,
        apply=_apply_disarm_real_money,
    ),
    "move_money": Command(
        name="move_money",
        summary="Deposit, withdraw, or pay out funds. Fail-closed: only moves if the matching owner capability is armed; provider is SIMULATED unless a real one is configured.",
        params=[
            {"name": "action", "type": "string", "help": "deposit | withdraw | payout"},
            {"name": "amount_usd", "type": "number", "help": "amount in USD (> 0)"},
            {"name": "destination_id", "type": "string?", "help": "for withdraw/payout"},
            {"name": "source_id", "type": "string?", "help": "for deposit"},
        ],
        build_preview=_preview_move_money,
        apply=_apply_move_money,
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
