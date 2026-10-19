"""tks_meta_valve_controller.py -- the HELM valve, as a WRITTEN DETERMINISTIC RULE.

STATUS: ENGINEERED-NOT-VALIDATED. The rule below is written by hand. It has not passed a frozen test, and no
claim about its quality is made. Owner approval 2026-10-18 ("plain-rule valve"): the trained 5-weight logistic
aperture is replaced by a written rule; learned parts stay out of the deciding path until they pass a frozen test.

WHAT CHANGED
------------
  * The learned aperture sigma*(x) = sigmoid(w^T x + b) is GONE from the deciding path. The weights file
    `tks_meta_valve_weights_v0_4.json` is kept in the repo as a HISTORICAL record only. This module never opens it.
  * The old Flour/Water hard-code is GONE. The essential reagents are whatever the recipe's OWN prerequisite list
    says (the caller passes it; the live loop passes the canonical brain's support for that product).
  * G-ABSENT stays: if any essential reagent is absent, the valve clamps shut.

THE RULE (two written tables, no fitted numbers)
------------------------------------------------
Table 1 -- the aperture, from the missing ratio (missing essentials / all essentials):

    | missing_ratio            | aperture                          | interlock |
    |--------------------------|-----------------------------------|-----------|
    | 0                        | the dial setting (default 0.75)   | --        |
    | greater than 0           | 0                                 | G-ABSENT  |
    | no prerequisite list     | 0                                 | G-ABSENT  |

Table 2 -- the declared noise level of what is flowing in, as a number:

    | noise level | value |
    |-------------|-------|
    | EXACT       | 0.00  |   (checked form: the round-trip passed, amounts are exact)
    | LOW         | 0.25  |
    | MEDIUM      | 0.50  |
    | HIGH        | 1.00  |

Decision: G-ABSENT when Table 1 says so. Otherwise GATE_PASS when noise value <= aperture, else G-LIMIT.
The valve is an operating-point check (station S4). It never decides what is missing -- the RPM gate does that
-- and it never invents a quantity.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

STATUS_WORD = "ENGINEERED-NOT-VALIDATED"
#: Kept for the record. NEVER loaded by this module.
HISTORICAL_WEIGHTS_FILENAME = "tks_meta_valve_weights_v0_4.json"
DEFAULT_WEIGHTS_FILENAME = HISTORICAL_WEIGHTS_FILENAME   # backwards-compatible name; still never loaded

NOISE_LEVELS: Dict[str, Decimal] = {
    "EXACT": Decimal("0.00"),
    "LOW": Decimal("0.25"),
    "MEDIUM": Decimal("0.50"),
    "HIGH": Decimal("1.00"),
}
CLAMPED_APERTURE = Decimal("0")


@dataclass
class ValveTelemetry:
    tick: int
    aperture_sigma: Decimal
    inflow_entropy: Decimal
    backpressure: Decimal
    status: str             # 'OPEN', 'RESTRICTED', 'RESTRICTED_DROP', 'CLAMPED_HALT'
    gate_interlock: str     # 'GATE_PASS', 'G-ABSENT', 'G-LIMIT'
    admitted_to_held: bool
    reason: str
    missing_reagents: Optional[List[str]] = None
    rule: str = "written table (ENGINEERED-NOT-VALIDATED)"

    def as_dict(self) -> Dict[str, Any]:
        return {"tick": self.tick, "aperture_sigma": str(self.aperture_sigma),
                "inflow_entropy": str(self.inflow_entropy), "backpressure": str(self.backpressure),
                "status": self.status, "gate_interlock": self.gate_interlock,
                "admitted_to_held": self.admitted_to_held, "reason": self.reason,
                "missing_reagents": list(self.missing_reagents or []), "rule": self.rule}


def aperture_by_table(missing_ratio: Optional[Decimal], dial: Decimal) -> Tuple[Decimal, Optional[str]]:
    """Table 1. Returns (aperture, interlock or None)."""
    if missing_ratio is None or missing_ratio > 0:
        return CLAMPED_APERTURE, "G-ABSENT"
    return dial, None


class TKSMetaValveController:
    """The written-rule valve. `aperture_sigma` is the dial (an owner/eye setting), not a learned value."""

    status_word = STATUS_WORD

    def __init__(self, default_aperture: Any = Decimal("0.7"), weights_path: Optional[str] = None):
        self.aperture_sigma = Decimal(str(default_aperture))
        self.telemetry_history: List[ValveTelemetry] = []
        self.total_proposals_received = 0
        self.total_admitted_to_held = 0
        self.total_clamped_halts = 0
        #: Always None: the learned weights are never loaded. `weights_path` is accepted and ignored.
        self.weights_model = None
        self.ignored_weights_path = weights_path

    def set_aperture(self, sigma: Any) -> Decimal:
        val = Decimal(str(sigma))
        if not (Decimal("0.0") <= val <= Decimal("1.0")):
            raise ValueError(f"Valve aperture sigma must be between 0.0 and 1.0, got {sigma}")
        self.aperture_sigma = val
        return self.aperture_sigma

    def _record(self, telem: ValveTelemetry, allowed: bool) -> Tuple[bool, ValveTelemetry]:
        self.total_proposals_received += 1
        if telem.gate_interlock == "G-ABSENT":
            self.total_clamped_halts += 1
        if allowed:
            self.total_admitted_to_held += 1
        self.telemetry_history.append(telem)
        return allowed, telem

    def _decide(self, tick: int, name: str, aperture: Decimal, interlock: Optional[str], noise: Decimal,
                missing: Optional[List[str]], absent_reason: str) -> Tuple[bool, ValveTelemetry]:
        if interlock == "G-ABSENT":
            return self._record(ValveTelemetry(
                tick=tick, aperture_sigma=aperture, inflow_entropy=noise, backpressure=Decimal("1.0"),
                status="CLAMPED_HALT", gate_interlock="G-ABSENT", admitted_to_held=False,
                reason=absent_reason, missing_reagents=missing), False)
        backpressure = max(Decimal("0.0"), Decimal("1.0") - aperture)
        if noise <= aperture:
            return self._record(ValveTelemetry(
                tick=tick, aperture_sigma=aperture, inflow_entropy=noise, backpressure=backpressure,
                status="OPEN" if aperture >= Decimal("0.5") else "RESTRICTED", gate_interlock="GATE_PASS",
                admitted_to_held=True, missing_reagents=missing or [],
                reason=f"'{name}' passed: noise {noise} <= aperture {aperture} (written table)."), True)
        return self._record(ValveTelemetry(
            tick=tick, aperture_sigma=aperture, inflow_entropy=noise, backpressure=backpressure,
            status="RESTRICTED_DROP", gate_interlock="G-LIMIT", admitted_to_held=False,
            missing_reagents=missing or [],
            reason=f"'{name}' throttled: noise {noise} > aperture {aperture} (written table)."), False)

    def evaluate_reagents(self, tick: int, proposal_name: str, essential_reagents: Iterable[str],
                          present_reagents: Iterable[str], noise_level: str = "EXACT") -> Tuple[bool, ValveTelemetry]:
        """The live loop's call. `essential_reagents` = the recipe's own prerequisite list."""
        if noise_level not in NOISE_LEVELS:
            raise ValueError(f"noise level must be one of {sorted(NOISE_LEVELS)}, got {noise_level!r}")
        essential = list(dict.fromkeys(essential_reagents))
        present = set(present_reagents)
        noise = NOISE_LEVELS[noise_level]
        if not essential:
            aperture, interlock = aperture_by_table(None, self.aperture_sigma)
            return self._decide(tick, proposal_name, aperture, interlock, noise, [],
                                f"G-ABSENT: '{proposal_name}' has no prerequisite list; nothing can be checked.")
        missing = [r for r in essential if r not in present]
        ratio = Decimal(len(missing)) / Decimal(len(essential))
        aperture, interlock = aperture_by_table(ratio, self.aperture_sigma)
        return self._decide(tick, proposal_name, aperture, interlock, noise, missing,
                            f"G-ABSENT: '{proposal_name}' is missing {', '.join(missing)} "
                            f"({len(missing)} of {len(essential)} prerequisites).")

    def evaluate_proposal_flow(self, tick: int, proposal_name: str, prerequisites_present: bool,
                               novelty_entropy: Any, is_internal_daydream: bool = False,
                               proposal_features: Optional[Dict[str, float]] = None) -> Tuple[bool, ValveTelemetry]:
        """Older call shape, kept for callers that pass a yes/no prerequisite flag and an entropy number.
        `proposal_features` is accepted and IGNORED: the learned aperture is retired."""
        del is_internal_daydream, proposal_features
        ratio = Decimal("0") if prerequisites_present else Decimal("1")
        aperture, interlock = aperture_by_table(ratio, self.aperture_sigma)
        return self._decide(tick, proposal_name, aperture, interlock, Decimal(str(novelty_entropy)), None,
                            f"RPM Gate Interlock: Essential prerequisite missing for proposal '{proposal_name}'.")

    def status_summary(self) -> Dict[str, Any]:
        return {
            "subsystem": "tks_meta_valve_controller",
            "rule": "written deterministic table",
            "status_word": STATUS_WORD,
            "current_aperture_sigma": str(self.aperture_sigma),
            "proposals_received": self.total_proposals_received,
            "admitted_to_held": self.total_admitted_to_held,
            "clamped_halts": self.total_clamped_halts,
            "safety_interlock": "RPM_GATE_G_ABSENT_ACTIVE",
            "weights_loaded": False,
            "historical_weights_file_not_loaded": HISTORICAL_WEIGHTS_FILENAME,
        }


def self_test() -> None:
    valve = TKSMetaValveController(default_aperture="0.75")
    ok, t = valve.evaluate_reagents(1, "Bread", ["Flour", "Water"], ["Flour", "Water"])
    assert ok and t.gate_interlock == "GATE_PASS" and t.aperture_sigma == Decimal("0.75")
    ok, t = valve.evaluate_reagents(2, "Bread", ["Flour", "Water"], ["Flour"])
    assert not ok and t.gate_interlock == "G-ABSENT" and t.missing_reagents == ["Water"]
    ok, t = valve.evaluate_reagents(3, "Bread", ["Flour", "Water"], ["Flour", "Water"], noise_level="HIGH")
    assert not ok and t.gate_interlock == "G-LIMIT"
    assert valve.weights_model is None
    print("valve self-test: 3 written-rule cases PASS (", STATUS_WORD, ")")


if __name__ == "__main__":
    self_test()
