"""Phase 12: the learning controller.

Outcome feedback is the governed exception to one-way flow. It must be
WEAK and FILTERED: feedback outcome -> bias at beta << 1 with a slow tau,
so one outcome cannot rewrite the machine's principles.

v0.1 scope: working updates (episode-local) and episodic writes are
enabled; procedural and constitutional updates are DISABLED - the newborn
processor must not rewrite its own skeleton while it is still learning
where its knees are.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .ontology import GAIN_LEARN


class LearningDisabled(Exception):
    """Raised when a disabled learning layer is asked to update."""


@dataclass
class LearningDisposition:
    layer: str              # WORKING | EPISODIC | PROCEDURAL | CONSTITUTIONAL
    applied: bool
    note: str
    beta: float = GAIN_LEARN
    tau: int = 5

    def to_dict(self):
        return {"layer": self.layer, "applied": self.applied,
                "note": self.note, "beta": self.beta, "tau": self.tau}


class LearningController:
    def __init__(self, episodic_enabled: bool = True,
                 procedural_enabled: bool = False,
                 constitutional_enabled: bool = False) -> None:
        self.episodic_enabled = episodic_enabled
        self.procedural_enabled = procedural_enabled
        self.constitutional_enabled = constitutional_enabled
        self.queue: List[Dict] = []

    def dispose(self, outcome, packet=None) -> LearningDisposition:
        """Classify and apply one outcome. Low-gain, slow-tau by design."""
        disposition = LearningDisposition(
            layer="EPISODIC",
            applied=False,
            note="episodic write enabled at low gain; procedural and "
                 "constitutional layers disabled in v0.1",
        )
        if not self.episodic_enabled:
            raise LearningDisabled("episodic learning disabled")
        self.queue.append({"outcome": outcome, "packet_id": id(packet)})
        disposition.applied = True
        return disposition

    def request_procedural(self, *args) -> None:
        if not self.procedural_enabled:
            raise LearningDisabled("procedural updates disabled in v0.1")
        raise LearningDisabled("procedural updates not implemented in v0.1")

    def request_constitutional(self, *args) -> None:
        if not self.constitutional_enabled:
            raise LearningDisabled("constitutional updates disabled in v0.1")
        raise LearningDisabled("constitutional updates not implemented in v0.1")
