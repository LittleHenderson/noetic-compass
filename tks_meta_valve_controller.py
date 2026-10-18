"""tks_meta_valve_controller.py -- Phase 3 Meta Valve Controller for HELM & CAS.

CRITICAL ARCHITECTURAL ROLE (Phase 3 Valve System):
Acts as the dynamic thermodynamic/noetic pressure regulator between Level L4
open-domain proposals (sensory/language) and the Level L0-L3 Executive Recipe Brain.

Regulates information flow, novelty permeability, prerequisite backpressure,
and enforces RPM Gate safety interlocks:
- When prerequisites are missing, the valve clamps down (G-ABSENT interlock).
- When novel creative proposals arrive, the aperture (sigma) controls admittance into
  the Daydream store (held.py) while preserving the Rule P immutable barrier.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class ValveTelemetry:
    tick: int
    aperture_sigma: Decimal
    inflow_entropy: Decimal
    backpressure: Decimal
    status: str             # 'OPEN', 'RESTRICTED', 'CLAMPED_HALT'
    gate_interlock: str     # 'GATE_PASS', 'G-ABSENT', 'G-LIMIT', 'REFUSE:INTERNAL_WITNESS'
    admitted_to_held: bool
    reason: str


class TKSMetaValveController:
    """Phase 3 Meta Valve Controller.
    
    Controls information flow between high-entropy external proposers and
    the deterministic, verified CAS recipe ledger.
    """

    def __init__(self, default_aperture: Decimal = Decimal("0.7")):
        self.aperture_sigma = Decimal(str(default_aperture))
        self.telemetry_history: List[ValveTelemetry] = []
        self.total_proposals_received: int = 0
        self.total_admitted_to_held: int = 0
        self.total_clamped_halts: int = 0

    def set_aperture(self, sigma: Any) -> Decimal:
        """Set valve aperture sigma in [0.0, 1.0]."""
        val = Decimal(str(sigma))
        if not (Decimal("0.0") <= val <= Decimal("1.0")):
            raise ValueError(f"Valve aperture sigma must be between 0.0 and 1.0, got {sigma}")
        self.aperture_sigma = val
        return self.aperture_sigma

    def evaluate_proposal_flow(self,
                               tick: int,
                               proposal_name: str,
                               prerequisites_present: bool,
                               novelty_entropy: Decimal,
                               is_internal_daydream: bool = False) -> Tuple[bool, ValveTelemetry]:
        """Regulate a proposal's passage through the meta-valve.
        
        Returns:
            (allow_flow, telemetry_record)
        """
        self.total_proposals_received += 1
        entropy_d = Decimal(str(novelty_entropy))

        # Rule 1: The RPM Gate Safety Interlock
        # If essential prerequisites are missing, the valve triggers a pressure drop and clamps shut.
        if not prerequisites_present:
            self.total_clamped_halts += 1
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=self.aperture_sigma,
                inflow_entropy=entropy_d,
                backpressure=Decimal("1.0"),
                status="CLAMPED_HALT",
                gate_interlock="G-ABSENT",
                admitted_to_held=False,
                reason=f"RPM Gate Interlock: Essential prerequisite missing for proposal '{proposal_name}'."
            )
            self.telemetry_history.append(telem)
            return False, telem

        # Rule 2: Permeability check based on aperture (sigma)
        # Higher aperture permits higher-entropy (more unconventional/creative) ideas
        # Backpressure is inversely proportional to aperture
        backpressure = Decimal("1.0") - self.aperture_sigma

        # Proposal passes if its entropy does not exceed the allowed threshold
        # Max acceptable entropy = aperture_sigma
        if entropy_d <= self.aperture_sigma:
            self.total_admitted_to_held += 1
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=self.aperture_sigma,
                inflow_entropy=entropy_d,
                backpressure=backpressure,
                status="OPEN" if self.aperture_sigma >= Decimal("0.5") else "RESTRICTED",
                gate_interlock="GATE_PASS",
                admitted_to_held=True,
                reason=f"Proposal '{proposal_name}' passed valve aperture (entropy {entropy_d} <= sigma {self.aperture_sigma})."
            )
            self.telemetry_history.append(telem)
            return True, telem
        else:
            # Entropy too high for current aperture setting
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=self.aperture_sigma,
                inflow_entropy=entropy_d,
                backpressure=backpressure,
                status="RESTRICTED_DROP",
                gate_interlock="G-LIMIT",
                admitted_to_held=False,
                reason=f"Excess entropy ({entropy_d} > sigma {self.aperture_sigma}). Proposal throttled."
            )
            self.telemetry_history.append(telem)
            return False, telem

    def status_summary(self) -> Dict[str, Any]:
        """Return operational summary of the Phase 3 Valve System."""
        return {
            "subsystem": "tks_meta_valve_controller",
            "phase": "Phase 3 Scaffold",
            "current_aperture_sigma": str(self.aperture_sigma),
            "proposals_received": self.total_proposals_received,
            "admitted_to_held": self.total_admitted_to_held,
            "clamped_halts": self.total_clamped_halts,
            "admittance_rate": f"{(self.total_admitted_to_held / max(1, self.total_proposals_received)) * 100:.1f}%",
            "safety_interlock": "RPM_GATE_G_ABSENT_ACTIVE"
        }


def self_test():
    print("Testing TKSMetaValveController (Phase 3 Valve System)...")
    valve = TKSMetaValveController(default_aperture="0.7")
    assert valve.aperture_sigma == Decimal("0.7")

    # Test 1: Normal creative proposal with prerequisites present
    allowed, t1 = valve.evaluate_proposal_flow(
        tick=1,
        proposal_name="CROSS_PLANE_ANALOGY_2B_TO_4C",
        prerequisites_present=True,
        novelty_entropy=Decimal("0.45")
    )
    assert allowed is True
    assert t1.gate_interlock == "GATE_PASS"
    assert t1.admitted_to_held is True
    print(f"[PASS] Normal creative proposal admitted: {t1.reason}")

    # Test 2: Missing prerequisite triggers CLAMPED_HALT (Zero Hallucination)
    allowed_missing, t2 = valve.evaluate_proposal_flow(
        tick=2,
        proposal_name="MISSING_DATA_SPECULATION",
        prerequisites_present=False,
        novelty_entropy=Decimal("0.1")
    )
    assert allowed_missing is False
    assert t2.gate_interlock == "G-ABSENT"
    assert t2.status == "CLAMPED_HALT"
    print(f"[PASS] Missing prerequisite clamped by RPM Gate interlock: {t2.reason}")

    # Test 3: Tighten valve to Surgical Mode (sigma = 0.1)
    valve.set_aperture("0.1")
    allowed_high_entropy, t3 = valve.evaluate_proposal_flow(
        tick=3,
        proposal_name="WILD_METAPHOR_PROPOSAL",
        prerequisites_present=True,
        novelty_entropy=Decimal("0.65")
    )
    assert allowed_high_entropy is False
    assert t3.gate_interlock == "G-LIMIT"
    print(f"[PASS] Surgical mode throttles high entropy: {t3.reason}")

    summary = valve.status_summary()
    assert summary["proposals_received"] == 3
    assert summary["admitted_to_held"] == 1
    assert summary["clamped_halts"] == 1
    print("[PASS] TKSMetaValveController summary verified:", summary)
    print("ALL PHASE 3 META VALVE CONTROLLER TESTS PASSED.")


if __name__ == "__main__":
    self_test()
