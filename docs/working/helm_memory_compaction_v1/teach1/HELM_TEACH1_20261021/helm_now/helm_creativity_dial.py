"""helm_creativity_dial.py -- Interactive Creativity & Ideation Controls for HELM.

Governs the five architectural dials of HELM's creativity without compromising
zero-hallucination guarantees or RPM Gate conservation laws.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, Optional

PRECISION = 40


@dataclass
class CreativityDial:
    """HELM Creativity Control Panel.
    
    Dial 1: Breadth (K in [1, 32]) - Structural hypothesis generation budget.
    Dial 2: Elasticity (rho in [-4.0, 1.0]) - CES substitution willingness.
    Dial 3: Search Radius (R in {1, 2, 4, 8}) - Spatial radius over RPA Atlas & TKS grid.
    Dial 4: Idle Pondering Intensity (ticks in [0, 100]) - Background residual refit budget.
    Dial 5: Phase 3 Valve Saliency (sigma in [0.0, 1.0]) - Novelty permeability in tks_meta_valve_controller.
    """
    breadth_K: int = 8
    curvature_rho: Decimal = Decimal("0.5")
    search_radius_R: int = 1
    idle_ponder_budget: int = 16
    valve_novelty_sigma: Decimal = Decimal("0.7")

    def __post_init__(self):
        self.set_breadth(self.breadth_K)
        self.set_curvature(self.curvature_rho)
        self.set_search_radius(self.search_radius_R)
        self.set_idle_ponder(self.idle_ponder_budget)
        self.set_valve_saliency(self.valve_novelty_sigma)

    def set_breadth(self, K: int) -> int:
        """Dial 1: Set exploration candidate breadth (K in [1, 32])."""
        k_val = int(K)
        if not (1 <= k_val <= 32):
            raise ValueError(f"Breadth K must be between 1 and 32, got {K}")
        self.breadth_K = k_val
        return self.breadth_K

    def set_curvature(self, rho: Any) -> Decimal:
        """Dial 2: Set CES substitution curvature (rho in [-4.0, 1.0]).
        -4.0 = Rigid traditionalist (strictly fixed proportions)
        0.0  = Cobb-Douglas geometric mean limit
        0.5  = Pragmatic balanced substitution (default)
        1.0  = Radical innovator (linear perfect substitution)
        """
        r_val = Decimal(str(rho))
        if not (Decimal("-4.0") <= r_val <= Decimal("1.0")):
            raise ValueError(f"Curvature rho must be between -4.0 and 1.0, got {rho}")
        self.curvature_rho = r_val
        return self.curvature_rho

    def set_search_radius(self, R: int) -> int:
        """Dial 3: Set bounded RPA searchlight radius (R in {1, 2, 4, 8})."""
        r_val = int(R)
        if r_val not in (1, 2, 4, 8):
            raise ValueError(f"Search radius R must be 1, 2, 4, or 8, got {R}")
        self.search_radius_R = r_val
        return self.search_radius_R

    def set_idle_ponder(self, budget: int) -> int:
        """Dial 4: Set idle residual pondering budget (ticks in [0, 100])."""
        b_val = int(budget)
        if not (0 <= b_val <= 100):
            raise ValueError(f"Idle pondering budget must be between 0 and 100, got {budget}")
        self.idle_ponder_budget = b_val
        return self.idle_ponder_budget

    def set_valve_saliency(self, sigma: Any) -> Decimal:
        """Dial 5: Set Phase 3 Meta Valve Saliency (sigma in [0.0, 1.0]).
        0.0 = Surgical precision (zero speculative proposals admitted)
        0.7 = Standard creative ideation (default)
        1.0 = Wide open brainstorming mode
        """
        s_val = Decimal(str(sigma))
        if not (Decimal("0.0") <= s_val <= Decimal("1.0")):
            raise ValueError(f"Valve saliency sigma must be between 0.0 and 1.0, got {sigma}")
        self.valve_novelty_sigma = s_val
        return self.valve_novelty_sigma

    def preset_surgical(self):
        """Preset: Strict, zero-drift execution for high-stakes calculations."""
        self.breadth_K = 1
        self.curvature_rho = Decimal("-1.0")
        self.search_radius_R = 1
        self.idle_ponder_budget = 0
        self.valve_novelty_sigma = Decimal("0.1")
        return self

    def preset_balanced(self):
        """Preset: Standard autonomous reasoning."""
        self.breadth_K = 8
        self.curvature_rho = Decimal("0.5")
        self.search_radius_R = 2
        self.idle_ponder_budget = 16
        self.valve_novelty_sigma = Decimal("0.7")
        return self

    def preset_brainstorm(self):
        """Preset: Maximum creative synthesis and cross-plane discovery."""
        self.breadth_K = 32
        self.curvature_rho = Decimal("1.0")
        self.search_radius_R = 8
        self.idle_ponder_budget = 64
        self.valve_novelty_sigma = Decimal("0.95")
        return self

    def status_card(self) -> str:
        """Return formatted ASCII status card for the HELM Creativity Panel."""
        mode = "BALANCED"
        if self.breadth_K == 1 and self.valve_novelty_sigma <= Decimal("0.2"):
            mode = "SURGICAL / CONSERVATIVE"
        elif self.breadth_K >= 24 or self.valve_novelty_sigma >= Decimal("0.9"):
            mode = "MAXIMUM BRAINSTORMING / SYNTHESIS"

        card = f"""
┌────────────────────────────────────────────────────────────────────────┐
│                      HELM CREATIVITY CONTROL PANEL                     │
│                           Mode: {mode:<30} │
├────────────────────────────────────────────────────────────────────────┤
│ Dial 1: Candidate Breadth (K)     : {self.breadth_K:<2}  [1: Conservative .. 32: Wild]
│ Dial 2: Substitution Curvature (ρ): {str(self.curvature_rho):<4} [-4: Strict .. 1: Perfect Sub]
│ Dial 3: RPA Search Radius (R)     : {self.search_radius_R:<2}  [1, 2, 4, 8 bounded horizon]
│ Dial 4: Idle Pondering Budget     : {self.idle_ponder_budget:<2}  [unexplained residual refits]
│ Dial 5: Phase 3 Valve Saliency (σ): {str(self.valve_novelty_sigma):<4} [0.0: Closed .. 1.0: Wide Open]
├────────────────────────────────────────────────────────────────────────┤
│ GOVERNANCE: Dials govern proposal sampling width (K, rho, R, sigma).   │
│ Truth is determined exclusively by RPM Gate (G-ABSENT) & Rule P.       │
└────────────────────────────────────────────────────────────────────────┘
"""
        return card.strip()


def self_test():
    dial = CreativityDial()
    assert dial.breadth_K == 8
    assert dial.curvature_rho == Decimal("0.5")
    assert dial.search_radius_R == 1
    
    dial.preset_brainstorm()
    assert dial.breadth_K == 32
    assert dial.curvature_rho == Decimal("1.0")
    assert dial.search_radius_R == 8
    
    dial.preset_surgical()
    assert dial.breadth_K == 1
    assert dial.curvature_rho == Decimal("-1.0")
    
    dial.preset_balanced()
    card = dial.status_card()
    assert "HELM CREATIVITY CONTROL PANEL" in card
    print("[PASS] CreativityDial self-test passed cleanly.")
    print(card)


if __name__ == "__main__":
    self_test()
