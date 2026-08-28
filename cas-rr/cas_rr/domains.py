"""Domain descent: P -> C -> E -> O, power sequencing, and diodes.

Principles govern reasoning, reasoning governs evaluation, evaluation
governs action. Diodes make that direction STRUCTURAL: an operational
result may not climb directly back to P and retroactively justify itself.
The only O -> P path is the deliberate, low-gain learning channel.

Also enforced: no Operational output until P, C, and E are power-good
("no action without principle"), and conclusions leave the |A Analytical
register only through a validated conversion before becoming |E Embodied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


class DomainPowerError(Exception):
    """Raised when a domain-descent law is violated."""


@dataclass
class DomainPowerState:
    P_GOOD: bool = False
    C_GOOD: bool = False
    E_GOOD: bool = False
    O_ENABLED: bool = False

    def update(self, p: bool, c: bool, e: bool) -> None:
        self.P_GOOD = p
        self.C_GOOD = c
        self.E_GOOD = e
        self.O_ENABLED = p and c and e

    def to_dict(self):
        return {"P_GOOD": self.P_GOOD, "C_GOOD": self.C_GOOD,
                "E_GOOD": self.E_GOOD, "O_ENABLED": self.O_ENABLED}


class PowerSequencer:
    @staticmethod
    def boot(state: DomainPowerState) -> List[Dict]:
        """Boot invariant: O_ENABLED only if P_GOOD and C_GOOD and E_GOOD."""
        records = []
        state.update(True, False, False)
        records.append({"stage": "P_POWERED", "state": state.to_dict()})
        state.update(True, True, False)
        records.append({"stage": "C_POWERED", "state": state.to_dict()})
        state.update(True, True, True)
        records.append({"stage": "E_POWERED", "state": state.to_dict()})
        records.append({"stage": "O_ENABLED", "state": state.to_dict()})
        return records


class DomainDescent:
    def __init__(self, state: DomainPowerState, learning_channel) -> None:
        self.state = state
        self.learning_channel = learning_channel
        self.records: List[Dict] = []

    def descend(self, conclusion, kind: str) -> Dict:
        """Analytical conclusion -> validated conversion -> Embodied output."""
        if not self.state.O_ENABLED:
            raise DomainPowerError("O domain not enabled: no action without principle")
        record = {
            "from_register": "|A",
            "to_register": "|E",
            "conversion": "validated_DAC",
            "conclusion": str(conclusion),
            "kind": kind,
        }
        self.records.append(record)
        return record

    def forbid_feedback(self) -> None:
        """Diodes: a direct O -> P causal edge is structurally forbidden."""
        raise DomainPowerError(
            "direct O -> P feedback is blocked by diodes; operational results "
            "may inform principles only through the governed learning channel")

    def request_feedback(self, outcome) -> Dict:
        """The sanctioned exception: downstream -> upstream through the
        deliberate, low-gain, filtered learning path."""
        return self.learning_channel.dispose(outcome)
