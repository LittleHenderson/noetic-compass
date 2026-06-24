"""CAS Permission/Risk Validator — Stage 3 of the LLM bot runtime pipeline.

Sits between LLM tool selection (Stage 2) and deterministic capability
dispatch (Stage 4). Reads the live `runtime_gates` and `authority_boundary`
state and decides whether the capability the model picked is allowed to run.
On REJECT, returns a structured message that feeds back to the model so it
explains the rejection in plain English instead of the operator seeing a
stack trace.

Design rules:
- Pure. `validate_capability` takes the capability and the gate state in,
  returns a `ValidationResult`. Network I/O lives in `fetch_runtime_gates`
  so tests can validate without HTTP.
- Conservative by default. An unknown danger level is treated as
  conservative (`caution`), never as `safe`.
- Does not replace the manual approval gate. `requires_confirm=True` still
  prompts the operator. The validator is a pre-filter that blocks closed
  runtime gates so the operator is never asked to confirm something that
  CAS itself would refuse.
- Structured rejection includes the gate that blocked, the gate's reason,
  and the next-action hint, so the model can summarize accurately.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple

from cas_forex.cas_forex_bot import BotCapability


DEFAULT_GATES_PATH = "/api/forex/settings/runtime-gates"
DEFAULT_BOUNDARY_PATH = "/api/forex/settings/authority-boundary"
DEFAULT_FETCH_TIMEOUT_SECONDS = 10

DECISION_PASS = "PASS"
DECISION_REJECT = "REJECT"
DECISION_DEGRADED = "DEGRADED"  # gate state unavailable; defer to manual confirm

# Map a capability's danger_level to the runtime gates that must be authorized.
# `safe` and `caution` require nothing — caution capabilities are MT5 demo /
# paper-proof / read-only operations whose runtime risk is bounded by the demo
# environment, and they are still hard-gated by `requires_confirm=True` at the
# manual approval stage. `dangerous` is reserved for capabilities that would
# touch live money or live broker state and is therefore conjunctively gated
# on every real-money runtime gate.
REQUIRED_GATES_BY_DANGER: Mapping[str, Tuple[str, ...]] = {
    "safe": (),
    "caution": (),
    "dangerous": (
        "live_trading",
        "broker_accept",
        "auto_deposit",
        "bank_card_movement",
        "payout_automation",
    ),
}

# Caps that touch broker/MT5 state in any way (demo or live). Even when no
# gate is required, the validator records them so the LLM can mention the
# capability was broker-touching and surface what the runtime state looks like.
BROKER_TOUCHING_GROUPS: Tuple[str, ...] = ("workflow", "mt5")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateBlock:
    """A single runtime gate that blocked a capability."""

    gate: str
    status: str
    missing_requirements: Tuple[str, ...] = ()
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "status": self.status,
            "missing_requirements": list(self.missing_requirements),
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one capability against current CAS state."""

    capability_key: str
    capability_label: str
    danger_level: str
    decision: str  # PASS | REJECT | DEGRADED
    blocking_gates: Tuple[GateBlock, ...] = ()
    advisory_notes: Tuple[str, ...] = ()
    requires_confirm: bool = False
    broker_touching: bool = False
    structured_message: str = ""

    @property
    def is_pass(self) -> bool:
        return self.decision == DECISION_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_key": self.capability_key,
            "capability_label": self.capability_label,
            "danger_level": self.danger_level,
            "decision": self.decision,
            "blocking_gates": [b.to_dict() for b in self.blocking_gates],
            "advisory_notes": list(self.advisory_notes),
            "requires_confirm": self.requires_confirm,
            "broker_touching": self.broker_touching,
            "structured_message": self.structured_message,
        }


# ---------------------------------------------------------------------------
# Pure validation
# ---------------------------------------------------------------------------


def _required_gates_for(cap: BotCapability) -> Tuple[str, ...]:
    level = cap.danger_level or "caution"
    # Unknown danger level → conservative (treat as caution, i.e. no auto gate
    # but still subject to requires_confirm).
    if level not in REQUIRED_GATES_BY_DANGER:
        level = "caution"
    return REQUIRED_GATES_BY_DANGER[level]


def _gate_block(gate_name: str, decision: Mapping[str, Any]) -> GateBlock:
    return GateBlock(
        gate=gate_name,
        status=str(decision.get("status") or "UNKNOWN"),
        missing_requirements=tuple(
            str(item) for item in (decision.get("missing_requirements") or ())
        ),
        next_action=str(decision.get("next_action") or ""),
    )


def _format_message(
    *,
    cap: BotCapability,
    decision: str,
    blocking_gates: Sequence[GateBlock],
    advisory_notes: Sequence[str],
) -> str:
    header_decision_word = {
        DECISION_PASS: "ALLOWED",
        DECISION_REJECT: "REJECTED",
        DECISION_DEGRADED: "DEGRADED",
    }.get(decision, decision)
    lines = [
        f"[cas-validator:{header_decision_word}] capability=`{cap.key}` "
        f"({cap.label}) danger={cap.danger_level}"
    ]
    if blocking_gates:
        lines.append("Blocked by runtime gates:")
        for block in blocking_gates:
            lines.append(f"  - `{block.gate}` → {block.status}")
            if block.next_action:
                lines.append(f"    next: {block.next_action}")
    if advisory_notes:
        lines.append("Advisory:")
        for note in advisory_notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def validate_capability(
    cap: BotCapability,
    runtime_gates: Optional[Mapping[str, Any]],
    *,
    authority_boundary: Optional[Mapping[str, Any]] = None,
) -> ValidationResult:
    """Decide whether `cap` is permitted to dispatch given current CAS state.

    `runtime_gates` is the body of `/api/forex/settings/runtime-gates`.
    When `None` (e.g. the API is down), the validator returns `DEGRADED`:
    safe and caution capabilities still pass (so the deterministic bot keeps
    working offline), but dangerous capabilities are rejected because we
    cannot prove the gates are open.
    """
    danger = cap.danger_level or "caution"
    broker_touching = cap.group in BROKER_TOUCHING_GROUPS
    advisory: list[str] = []
    blocking: list[GateBlock] = []

    if runtime_gates is None:
        if danger == "dangerous":
            advisory.append("runtime-gates endpoint unavailable; refusing dangerous capability")
            result = ValidationResult(
                capability_key=cap.key,
                capability_label=cap.label,
                danger_level=danger,
                decision=DECISION_REJECT,
                blocking_gates=(),
                advisory_notes=tuple(advisory),
                requires_confirm=cap.requires_confirm,
                broker_touching=broker_touching,
            )
            return _attach_message(result, cap)
        advisory.append("runtime-gates endpoint unavailable; passing under degraded check")
        result = ValidationResult(
            capability_key=cap.key,
            capability_label=cap.label,
            danger_level=danger,
            decision=DECISION_DEGRADED,
            blocking_gates=(),
            advisory_notes=tuple(advisory),
            requires_confirm=cap.requires_confirm,
            broker_touching=broker_touching,
        )
        return _attach_message(result, cap)

    decisions = runtime_gates.get("decisions") or {}

    required = _required_gates_for(cap)
    for gate_name in required:
        decision = decisions.get(gate_name) or {}
        if not bool(decision.get("authorized", False)):
            blocking.append(_gate_block(gate_name, decision))

    if authority_boundary is not None and danger == "dangerous":
        if not bool(authority_boundary.get("can_place_live_orders", False)):
            advisory.append("authority_boundary.can_place_live_orders=False")

    if cap.requires_confirm:
        advisory.append("operator confirmation required at Stage 5")
    if broker_touching and danger != "dangerous" and not blocking:
        advisory.append("broker/MT5-touching capability on demo lane (paper/demo)")

    if blocking:
        decision_value = DECISION_REJECT
    else:
        decision_value = DECISION_PASS

    result = ValidationResult(
        capability_key=cap.key,
        capability_label=cap.label,
        danger_level=danger,
        decision=decision_value,
        blocking_gates=tuple(blocking),
        advisory_notes=tuple(advisory),
        requires_confirm=cap.requires_confirm,
        broker_touching=broker_touching,
    )
    return _attach_message(result, cap)


def _attach_message(result: ValidationResult, cap: BotCapability) -> ValidationResult:
    message = _format_message(
        cap=cap,
        decision=result.decision,
        blocking_gates=result.blocking_gates,
        advisory_notes=result.advisory_notes,
    )
    # Frozen dataclass — recreate with message attached.
    return ValidationResult(
        capability_key=result.capability_key,
        capability_label=result.capability_label,
        danger_level=result.danger_level,
        decision=result.decision,
        blocking_gates=result.blocking_gates,
        advisory_notes=result.advisory_notes,
        requires_confirm=result.requires_confirm,
        broker_touching=result.broker_touching,
        structured_message=message,
    )


# ---------------------------------------------------------------------------
# Fetch helpers (HTTP isolated so the pure validator can be tested standalone)
# ---------------------------------------------------------------------------


def fetch_runtime_gates(
    api_base: str,
    *,
    timeout: int = DEFAULT_FETCH_TIMEOUT_SECONDS,
    path: str = DEFAULT_GATES_PATH,
    transport: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """GET the runtime-gates JSON. Returns None on any network/parse failure
    so the caller can route through the DEGRADED path."""
    url = f"{api_base.rstrip('/')}{path}"
    try:
        if transport is not None:
            return transport(url, timeout=timeout)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — local API
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def fetch_authority_boundary(
    api_base: str,
    *,
    timeout: int = DEFAULT_FETCH_TIMEOUT_SECONDS,
    path: str = DEFAULT_BOUNDARY_PATH,
    transport: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """GET the authority-boundary JSON. Returns None on any failure."""
    url = f"{api_base.rstrip('/')}{path}"
    try:
        if transport is not None:
            return transport(url, timeout=timeout)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — local API
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# Convenience: validate by capability key against live API
# ---------------------------------------------------------------------------


def validate_by_key(
    capability_key: str,
    *,
    api_base: str,
    capabilities: Sequence[BotCapability],
) -> ValidationResult:
    """Look up a capability by key, fetch live gate state, validate."""
    cap = next((c for c in capabilities if c.key == capability_key), None)
    if cap is None:
        return ValidationResult(
            capability_key=capability_key,
            capability_label="<unknown>",
            danger_level="caution",
            decision=DECISION_REJECT,
            advisory_notes=("capability key not found",),
            structured_message=(
                f"[cas-validator:REJECTED] capability=`{capability_key}` not found"
            ),
        )
    runtime_gates = fetch_runtime_gates(api_base)
    return validate_capability(cap, runtime_gates)
