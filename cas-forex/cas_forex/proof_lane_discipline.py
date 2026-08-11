"""Proof-lane discipline: while the 30-day proof runs, only the proof may trade.

Post-mortem context (docs/operations/LOSS_POSTMORTEM_2026-07.md): the -$55,069
June-July loss was not the proof strategy - the autonomous M1 scalp lane traded
the receipt-bearing demo terminal at 191 trades/day, 97.6% of it in one day,
with every order intent stop-less. The proof plan allows US30/NAS100, D1,
max 3 trades/day.

This module is that fence, enforced at the dispatch chokepoint
(execution_guard.guarded_place_order), fail-closed:

  - symbol must be in the proof plan's allowlist;
  - the intent's decision_ref/proposal lineage must carry the proof plan's
    prefix (which encodes strategy and timeframe);
  - at most MAX_DISPATCHES_PER_UTC_DAY bridge-touching dispatches per UTC day;
  - every intent must carry a nonzero stop_loss ("no stop, no order" - the
    per-trade risk gate can only compute risk_at_stop when a stop exists, and
    in June it silently passed 2,634 stop-less intents).

Activation is owner-fenced via runtime/proof-lane-discipline.json
({"enabled": true}). The CODE default is disabled so simulators, CI, and the
test suite keep their existing behavior; the machine accumulating proof days
arms the fence by writing the state file (the day-1 setup does this). Disarm
by setting {"enabled": false} - a deliberate owner action, one file, no code.

Boundary: this module only ever BLOCKS dispatches. It cannot place orders,
cannot authorize anything, and does not touch live gates.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "proof-lane-discipline.json"

PROOF_SYMBOLS = frozenset({"US30", "NAS100"})
PROOF_REF_PREFIXES = ("index-tsmom-126", "index_tsmom_126")
MAX_DISPATCHES_PER_UTC_DAY = 3

CLAIM_BOUNDARY = (
    "Proof-lane discipline blocks dispatches that are not part of the active "
    "paper proof. It places no orders, authorizes nothing, and never relaxes "
    "any other gate."
)

_LOCK = threading.Lock()


@dataclass(frozen=True)
class LaneDecision:
    blocked: bool
    plain_english_reason: str
    rule: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "plain_english_reason": self.plain_english_reason,
            "rule": self.rule,
            "claim_boundary": CLAIM_BOUNDARY,
        }


def _read_state(state_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def discipline_enabled(state_path: Path | None = None) -> bool:
    return bool(_read_state(state_path or DEFAULT_STATE_PATH).get("enabled", False))


def _intent_text(intent: Mapping[str, Any] | Any, key: str) -> str:
    if isinstance(intent, Mapping):
        return str(intent.get(key) or "")
    return str(getattr(intent, key, "") or "")


def _intent_number(intent: Mapping[str, Any] | Any, key: str) -> Optional[float]:
    raw = intent.get(key) if isinstance(intent, Mapping) else getattr(intent, key, None)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value


def evaluate_proof_lane(
    intent: Mapping[str, Any] | Any,
    *,
    state_path: Path | None = None,
) -> LaneDecision:
    """Fail-closed lane check for one dispatch intent. Never raises."""
    path = state_path or DEFAULT_STATE_PATH
    state = _read_state(path)
    if not bool(state.get("enabled", False)):
        return LaneDecision(blocked=False, plain_english_reason="Proof-lane discipline is not armed.")

    symbol = _intent_text(intent, "symbol").upper().replace("/", "")
    if symbol not in PROOF_SYMBOLS:
        return LaneDecision(
            blocked=True,
            rule="symbol_allowlist",
            plain_english_reason=(
                f"Proof-lane discipline: symbol {symbol or 'UNKNOWN'} is not in the proof plan "
                f"({', '.join(sorted(PROOF_SYMBOLS))}). The June loss came from a lane the proof never sanctioned."
            ),
        )

    ref = _intent_text(intent, "decision_ref") or _intent_text(intent, "proposal_id") or _intent_text(intent, "order_id")
    if not any(prefix in ref for prefix in PROOF_REF_PREFIXES):
        return LaneDecision(
            blocked=True,
            rule="strategy_lineage",
            plain_english_reason=(
                f"Proof-lane discipline: dispatch lineage {ref[:60] or 'UNKNOWN'!r} does not carry the "
                "proof plan's prefix; only index_tsmom_126 proof dispatches may trade during the proof."
            ),
        )

    stop = _intent_number(intent, "stop_loss") or _intent_number(intent, "sl")
    if not stop:
        return LaneDecision(
            blocked=True,
            rule="no_stop_no_order",
            plain_english_reason=(
                "Proof-lane discipline: intent carries no stop-loss, so risk at the stop is "
                "not computable. No stop, no order."
            ),
        )

    # Daily dispatch counter - stored beside the state so the fence and its
    # ledger travel together; counted only when the intent passes every other
    # rule (a blocked attempt must not consume proof capacity).
    today = utc_now().strftime("%Y-%m-%d")
    with _LOCK:
        state = _read_state(path)
        counts = state.get("dispatch_counts") if isinstance(state.get("dispatch_counts"), dict) else {}
        used = int(counts.get(today, 0) or 0)
        if used >= MAX_DISPATCHES_PER_UTC_DAY:
            return LaneDecision(
                blocked=True,
                rule="daily_dispatch_ceiling",
                plain_english_reason=(
                    f"Proof-lane discipline: {used} dispatches already used today; the proof plan "
                    f"allows at most {MAX_DISPATCHES_PER_UTC_DAY} per UTC day."
                ),
            )
        counts = {today: used + 1}  # prior days are irrelevant once the date changes
        state["dispatch_counts"] = counts
        state.setdefault("enabled", True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    return LaneDecision(blocked=False, plain_english_reason="Proof-lane dispatch admitted.")
