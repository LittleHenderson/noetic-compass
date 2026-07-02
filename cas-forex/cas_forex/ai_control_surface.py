"""AI control surface: typed dials over every app lever, with owner-set bounds.

This is the surface the ADAPTIVE AI loop (WATCH -> ANALYZE -> STRATEGIZE -> TEST
-> EXECUTE) uses to READ and ADJUST the owner's levers as it chases the profit
objective. The AI owns these dials so it can press a confirmed edge harder or
pull back when there is none -- BUT every dial is fenced by an owner-set
``(min, max)`` guardrail. The AI may move within the fence; it can never move the
fence.

What is and is NOT a lever here:

  - IS a lever: edge_threshold, max_risk_pct_per_trade, max_concurrent_trades,
    daily_loss_cap_usd, symbols, sessions, max_compound_units. These shape HOW
    HARD the AI pursues the target, never WHETHER an edge exists.
  - NOT a lever: real-money / go-live. Flipping demo -> live money stays an
    explicit owner gate elsewhere in the stack (BRIDGE-level ``is_demo_account``
    check). It is deliberately absent from this surface. The AI cannot enable
    real-money trading by turning a dial; it can only operate within whatever
    mode the owner has already authorized.

Honesty posture: these dials AMPLIFY pursuit of the objective, they do not create
an edge. Raising ``max_risk_pct_per_trade`` or ``max_compound_units`` on a
zero/negative-expectancy signal still loses money; the null TEST gate (elsewhere)
remains the integrity core. This module only enforces bounds and reports clamps
honestly.

Pure / in-memory: the surface holds its own state and does NOT wire to the real
config. An optional ``persist`` callable hook is exposed so the caller can route
adjustments to durable storage at integration time -- this module never calls
config itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from cas_forex.instruments import SUPPORTED_SYMBOLS

# Canonical trading sessions the AI may enable/disable.
SUPPORTED_SESSIONS: Tuple[str, ...] = ("Asian", "London", "NewYork")


@dataclass(frozen=True)
class ScalarLever:
    """A numeric dial with an inclusive ``[min, max]`` guardrail."""

    name: str
    default: float
    minimum: float
    maximum: float
    is_int: bool = False

    def clamp(self, value: float) -> Tuple[float, bool]:
        """Return ``(clamped_value, was_clamped)``; coerce int levers to int."""
        coerced = int(round(value)) if self.is_int else float(value)
        lo, hi = self.minimum, self.maximum
        if coerced < lo:
            return (int(lo) if self.is_int else float(lo), True)
        if coerced > hi:
            return (int(hi) if self.is_int else float(hi), True)
        return (coerced, False)


@dataclass(frozen=True)
class SetLever:
    """A subset-of-allowed dial (e.g. symbols, sessions)."""

    name: str
    default: Tuple[str, ...]
    allowed: Tuple[str, ...]

    def normalize(self, value: Any) -> Tuple[List[str], List[str]]:
        """Return ``(kept, dropped)`` -- members not in ``allowed`` are dropped.

        Order follows ``allowed`` so the result is deterministic; duplicates are
        collapsed.
        """
        if isinstance(value, str):
            requested = {value}
        else:
            requested = {str(v) for v in value}
        kept = [a for a in self.allowed if a in requested]
        dropped = sorted(requested - set(self.allowed))
        return kept, dropped


# Scalar lever specifications. daily_loss_cap_usd has no upper guardrail
# (owner may run uncapped) -- represented as +inf so clamping never triggers high.
_SCALAR_LEVERS: Dict[str, ScalarLever] = {
    "edge_threshold": ScalarLever("edge_threshold", 0.65, 0.50, 0.95),
    "max_risk_pct_per_trade": ScalarLever("max_risk_pct_per_trade", 0.5, 0.0, 5.0),
    "max_concurrent_trades": ScalarLever(
        "max_concurrent_trades", 15, 1, 50, is_int=True
    ),
    "daily_loss_cap_usd": ScalarLever(
        "daily_loss_cap_usd", 0.0, 0.0, float("inf")
    ),
    "max_compound_units": ScalarLever(
        "max_compound_units", 4, 0, 8, is_int=True
    ),
    # Owner decision (2026-07-01): 1 = on PAPER/DEMO a non-PASS candidate still
    # executes as a token-less paper LEARNING trade (the edge verdict becomes the
    # training label); 0 = the edge gate blocks paper execution too (the pre-
    # 2026-07-01 behaviour). Real money is untouched by this dial: a token-less
    # dispatch is refused at the chokepoint whenever the path is real.
    "paper_learning_trades": ScalarLever(
        "paper_learning_trades", 1, 0, 1, is_int=True
    ),
    # Minimum directional-hypothesis confidence before a candidate may form.
    # 0.18 is the historic hardcoded default; scalp/learning mode may lower it
    # (more candidates, weaker directional basis). This shapes HYPOTHESIS
    # formation only — the edge gate / learning-label semantics are unchanged.
    "min_directional_confidence": ScalarLever(
        "min_directional_confidence", 0.18, 0.0, 0.90
    ),
}

_SET_LEVERS: Dict[str, SetLever] = {
    "symbols": SetLever(
        "symbols",
        default=tuple(sorted(SUPPORTED_SYMBOLS)),
        allowed=tuple(sorted(SUPPORTED_SYMBOLS)),
    ),
    "sessions": SetLever(
        "sessions",
        default=SUPPORTED_SESSIONS,
        allowed=SUPPORTED_SESSIONS,
    ),
}

LEVER_NAMES: Tuple[str, ...] = tuple(_SCALAR_LEVERS) + tuple(_SET_LEVERS)


def _scalar_default(lever: ScalarLever) -> Any:
    return int(lever.default) if lever.is_int else float(lever.default)


class AiControlSurface:
    """Typed dials over every app lever, fenced by owner-set bounds.

    The AI owns these dials to chase the >= $250/day objective, but the bounds
    are owner guardrails the AI cannot move. Real-money / go-live is NOT a lever
    here -- it stays owner-gated at the bridge level.

    All state is in-memory. Pass ``persist`` to mirror adjustments to durable
    storage; it is called as ``persist(snapshot_dict)`` after every successful
    ``adjust`` and after ``reset``. The hook is best-effort: this surface never
    reads its state back from the hook and never touches the real config.
    """

    def __init__(self, persist: Optional[Callable[[Dict[str, Any]], None]] = None):
        self._persist = persist
        self._values: Dict[str, Any] = {}
        self._set_defaults()

    # -- state ----------------------------------------------------------------

    def _set_defaults(self) -> None:
        for name, lever in _SCALAR_LEVERS.items():
            self._values[name] = _scalar_default(lever)
        for name, lever in _SET_LEVERS.items():
            self._values[name] = list(lever.default)

    def reset(self) -> Dict[str, Any]:
        """Restore every lever to its owner default; fire the persist hook."""
        self._set_defaults()
        snap = self.snapshot()
        self._fire_persist(snap)
        return snap

    # -- reads ----------------------------------------------------------------

    def get(self, lever: str) -> Any:
        """Return the current value of ``lever`` (raises KeyError if unknown)."""
        if lever not in self._values:
            raise KeyError(f"Unknown lever '{lever}'. Known: {sorted(LEVER_NAMES)}")
        value = self._values[lever]
        return list(value) if isinstance(value, list) else value

    def snapshot(self) -> Dict[str, Any]:
        """A plain-dict view of every lever plus its bounds, for the UI/AI."""
        bounds: Dict[str, Any] = {}
        for name, lever in _SCALAR_LEVERS.items():
            bounds[name] = {"min": lever.minimum, "max": lever.maximum}
        for name, lever in _SET_LEVERS.items():
            bounds[name] = {"allowed": list(lever.allowed)}
        return {
            "values": {
                k: (list(v) if isinstance(v, list) else v)
                for k, v in self._values.items()
            },
            "bounds": bounds,
            "guardrail_note": (
                "Bounds are owner-set guardrails the AI cannot move. "
                "Real-money / go-live is NOT a lever here; it stays owner-gated."
            ),
        }

    # -- writes ---------------------------------------------------------------

    def adjust(self, lever: str, value: Any) -> Dict[str, Any]:
        """Set ``lever`` to ``value`` within bounds.

        Returns ``{ok, clamped, old, new, reason}``:
          - unknown lever      -> ok=False, reason names it, no state change.
          - scalar out of range -> clamped=True, new is the boundary value.
          - set with members outside ``allowed`` -> clamped=True, drops reported.
          - ``daily_loss_cap_usd`` below 0 -> clamped to 0.
        Fires the persist hook only on a successful (ok=True) adjustment.
        """
        if lever in _SCALAR_LEVERS:
            return self._adjust_scalar(_SCALAR_LEVERS[lever], value)
        if lever in _SET_LEVERS:
            return self._adjust_set(_SET_LEVERS[lever], value)
        return {
            "ok": False,
            "clamped": False,
            "old": None,
            "new": None,
            "reason": (
                f"Unknown lever '{lever}'. Known levers: {sorted(LEVER_NAMES)}"
            ),
        }

    def _adjust_scalar(self, lever: ScalarLever, value: Any) -> Dict[str, Any]:
        old = self._values[lever.name]
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "clamped": False,
                "old": old,
                "new": old,
                "reason": (
                    f"Lever '{lever.name}' needs a number, got {value!r}."
                ),
            }
        new, clamped = lever.clamp(numeric)
        self._values[lever.name] = new
        if clamped:
            hi = "+inf" if lever.maximum == float("inf") else lever.maximum
            reason = (
                f"Clamped to owner guardrail [{lever.minimum}, {hi}]: "
                f"requested {numeric}, set {new}."
            )
        else:
            reason = f"Set '{lever.name}' to {new}."
        result = {
            "ok": True,
            "clamped": clamped,
            "old": old,
            "new": new,
            "reason": reason,
        }
        self._fire_persist(self.snapshot())
        return result

    def _adjust_set(self, lever: SetLever, value: Any) -> Dict[str, Any]:
        old = list(self._values[lever.name])
        kept, dropped = lever.normalize(value)
        if not kept:
            # Refuse to empty the set -- an empty symbol/session list silently
            # disables all trading, which the AI should do via an explicit lever,
            # not as a side effect of a bad subset request.
            return {
                "ok": False,
                "clamped": bool(dropped),
                "old": old,
                "new": old,
                "reason": (
                    f"Refused: '{lever.name}' would be empty. "
                    f"None of {sorted(set(value)) if not isinstance(value, str) else [value]} "
                    f"are in allowed {list(lever.allowed)}."
                ),
            }
        self._values[lever.name] = kept
        clamped = bool(dropped)
        if clamped:
            reason = (
                f"Set '{lever.name}' to {kept}; dropped (not allowed): {dropped}."
            )
        else:
            reason = f"Set '{lever.name}' to {kept}."
        result = {
            "ok": True,
            "clamped": clamped,
            "old": old,
            "new": list(kept),
            "reason": reason,
        }
        self._fire_persist(self.snapshot())
        return result

    # -- internals ------------------------------------------------------------

    def _fire_persist(self, snap: Dict[str, Any]) -> None:
        if self._persist is None:
            return
        try:
            self._persist(snap)
        except Exception:
            # Persist is best-effort: the in-memory surface stays authoritative
            # even if durable storage hiccups. Never let a hook failure corrupt
            # a successful in-memory adjustment.
            pass
