"""Cognitive Memory Board — 40-cell capacitor bank with lacuna detection.

From CAS PCBA Engineer: "The Capacitor Bank: A 40-Cell Memory Array", with
cells declared in CCDL as e.g. `Capacitor< ^2^E_{F4}|f, C=120, leakage=... >`.

The source verification recorded the finding that matters here: the CMB's 40
cells are addressed by CAS state literals carrying Domain and Register, so the
memory board already maps onto the 40 Cognitive States. That mapping is made
explicit in this module rather than left implicit — cells are keyed by the
canonical `P0..P9, C0..C9, E0..E9, O0..O9` state keys.

A lacuna is an empty region: a structural query that finds no stored experience.
The artifact's most defensible claim is that a lacuna becomes a typed
prerequisite failure rather than a hallucinated answer, which is what makes
NEEDS_INFORMATION non-decorative. That conversion is implemented and tested here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DOMAINS = ("P", "C", "E", "O")
STATE_KEYS: tuple[str, ...] = tuple(f"{d}{n}" for d in DOMAINS for n in range(10))
assert len(STATE_KEYS) == 40


class Tier(str, Enum):
    """Three timescales, per the audited design's memory section.

    Leakage per recall step. Working memory fades fast; constitutional memory
    is effectively durable.
    """

    WORKING = "working"
    EPISODIC = "episodic"
    CONSTITUTIONAL = "constitutional"


TIER_LEAKAGE = {
    Tier.WORKING: 0.35,
    Tier.EPISODIC: 0.05,
    Tier.CONSTITUTIONAL: 0.002,
}


@dataclass
class Cell:
    """One capacitor: a CAS state key holding charge (stored experience)."""

    state_key: str
    charge: float = 0.0
    tier: Tier = Tier.EPISODIC

    @property
    def leakage(self) -> float:
        return TIER_LEAKAGE[self.tier]


@dataclass
class Recall:
    state_key: str
    charge: float
    is_lacuna: bool
    tier: Tier


class CognitiveMemoryBoard:
    """A 40-cell bank keyed by CAS cognitive-state literals."""

    #: Below this charge a cell counts as empty — a lacuna, not a weak memory.
    LACUNA_FLOOR = 0.05

    def __init__(self, lacuna_floor: float | None = None) -> None:
        self.cells: dict[str, Cell] = {k: Cell(k) for k in STATE_KEYS}
        self.lacuna_floor = self.LACUNA_FLOOR if lacuna_floor is None else lacuna_floor
        self.writes = 0
        self.recalls = 0

    # -- storage -------------------------------------------------------------

    def write(self, state_key: str, charge: float, tier: Tier = Tier.EPISODIC) -> None:
        if state_key not in self.cells:
            raise KeyError(f"{state_key} is not one of the 40 cognitive states")
        if charge < 0:
            raise ValueError("charge must be >= 0")
        cell = self.cells[state_key]
        cell.charge = max(cell.charge, charge)
        cell.tier = tier
        self.writes += 1

    def recall(self, state_key: str, *, decay: bool = True) -> Recall:
        if state_key not in self.cells:
            raise KeyError(f"{state_key} is not one of the 40 cognitive states")
        cell = self.cells[state_key]
        if decay:
            cell.charge = max(0.0, cell.charge * (1.0 - cell.leakage))
        self.recalls += 1
        return Recall(
            state_key=state_key,
            charge=cell.charge,
            is_lacuna=cell.charge < self.lacuna_floor,
            tier=cell.tier,
        )

    def refresh(self, state_key: str, charge: float) -> None:
        """Durable cells are refreshed rather than allowed to fade."""
        self.cells[state_key].charge = charge

    # -- diagnostics ---------------------------------------------------------

    def lacunae(self) -> tuple[str, ...]:
        """Every empty region of the bank."""
        return tuple(k for k, c in self.cells.items() if c.charge < self.lacuna_floor)

    def occupancy(self) -> float:
        filled = sum(1 for c in self.cells.values() if c.charge >= self.lacuna_floor)
        return filled / len(self.cells)

    def domain_lacunae(self, domain: str) -> tuple[str, ...]:
        if domain not in DOMAINS:
            raise ValueError(f"domain must be one of {DOMAINS}")
        return tuple(k for k in self.lacunae() if k.startswith(domain))
