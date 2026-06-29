"""Edge-authorization registry — the fail-closed lock between the WASTE loop's
TEST gate and the broker.

An order may reach a broker bridge through ``execution_guard.guarded_place_order``
ONLY if a fresh PASS from the edge gate (``edge_gate``) has been registered for the
order's ``decision_ref`` AND the order's geometry still matches what was tested.

This closes the architecture audit's fail-closed hole: the requirement rides on the
order's ``decision_ref`` + this registry, NOT an opt-in call-site kwarg that every
existing caller would silently skip. Two rules at the chokepoint:

  * REAL-MONEY (live) dispatch ALWAYS requires a registered, fresh, matching PASS —
    no PASS => the bridge is never touched.
  * Any order whose ``decision_ref`` the WASTE loop registered (``is_required``) is
    likewise gated. The loop registers its PASS immediately before it builds the
    order, so it is structurally incapable of dispatching without a tested edge.

Legacy paper paths that never went through the loop and are not live are unaffected
(they carry no registration and are not real-money), so this does not retro-break the
existing paper-proof dispatch — it only governs real money and the autonomous loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, verify_token


class EdgeNotAuthorized(Exception):
    """Raised at the dispatch chokepoint when an order lacks a fresh, matching edge PASS."""


@dataclass(frozen=True)
class _Authorization:
    token: str
    setup: CandidateSetup
    evaluated_at: str
    max_age_seconds: float


# decision_ref -> the PASS authorization minted for it. Populated ONLY by the edge
# gate's PASS via ``authorize``; consulted by ``guarded_place_order`` via ``require``.
_REGISTRY: Dict[str, _Authorization] = {}


def authorize(
    decision_ref: str,
    decision: EdgeTestDecision,
    setup: CandidateSetup,
    *,
    max_age_seconds: float = 120.0,
) -> None:
    """Register a PASS so an order with this ``decision_ref`` may dispatch.

    Only a genuine PASS (status == 'PASS' AND a non-empty ``edge_token``) can be
    registered — you cannot authorize a NO_TRADE/underpowered verdict.
    """
    if not decision_ref:
        raise ValueError("decision_ref is required to authorize an edge")
    if decision.status != "PASS" or not decision.edge_token:
        raise EdgeNotAuthorized(
            f"cannot authorize a non-PASS edge (status={decision.status!r})"
        )
    _REGISTRY[str(decision_ref)] = _Authorization(
        token=str(decision.edge_token),
        setup=setup,
        evaluated_at=str(decision.evaluated_at),
        max_age_seconds=float(max_age_seconds),
    )


def is_required(decision_ref: Optional[str]) -> bool:
    """True iff this decision_ref has a registered edge authorization."""
    return bool(decision_ref) and str(decision_ref) in _REGISTRY


def clear(decision_ref: str) -> None:
    """Drop one authorization (call after a successful one-shot dispatch)."""
    _REGISTRY.pop(str(decision_ref), None)


def reset() -> None:
    """Clear the whole registry (tests / shutdown)."""
    _REGISTRY.clear()


def _norm_dir(d: Any) -> str:
    s = getattr(d, "name", None) or getattr(d, "value", None) or d
    s = str(s).strip().upper()
    if s in {"LONG", "BUY"}:
        return "LONG"
    if s in {"SHORT", "SELL"}:
        return "SHORT"
    return s


def _close(a: Any, b: Any) -> bool:
    try:
        a_f, b_f = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a_f - b_f) <= 1e-6 + 1e-9 * max(abs(a_f), abs(b_f))


def require(order: Any, *, is_real: bool, now_iso: Optional[str] = None) -> None:
    """Fail-closed gate: raise ``EdgeNotAuthorized`` unless a fresh, matching edge
    PASS is registered for this order's ``decision_ref``.

    Three independent checks, all must hold:
      1. an authorization exists for the order's decision_ref;
      2. its token is still authentic AND unexpired (delegated to
         ``edge_gate.verify_token``, which binds to the exact tested geometry+time);
      3. the ORDER's stable geometry (symbol, direction, stop-loss, take-profit)
         matches the authorized setup — no swapping the trade after the PASS.
    """
    now = now_iso or _now_iso()
    decision_ref = getattr(order, "decision_ref", None)
    record = _REGISTRY.get(str(decision_ref)) if decision_ref else None
    if record is None:
        raise EdgeNotAuthorized(
            f"no edge authorization for decision_ref={decision_ref!r}: the TEST gate must "
            f"PASS and register before dispatch ({'live' if is_real else 'loop'} order refused)"
        )
    if not verify_token(
        record.token, record.setup, record.evaluated_at,
        now_iso=now, max_age_seconds=record.max_age_seconds,
    ):
        raise EdgeNotAuthorized(
            f"edge token for decision_ref={decision_ref!r} is invalid or stale — re-test required"
        )
    s = record.setup
    if (
        str(getattr(order, "symbol", "")) != str(s.symbol)
        or _norm_dir(getattr(order, "direction", "")) != _norm_dir(s.direction)
        or not _close(getattr(order, "stop_loss", float("nan")), s.stop_loss)
        or not _close(getattr(order, "take_profit", float("nan")), s.take_profit)
    ):
        raise EdgeNotAuthorized(
            f"order geometry diverges from the authorized edge for decision_ref={decision_ref!r}"
        )
