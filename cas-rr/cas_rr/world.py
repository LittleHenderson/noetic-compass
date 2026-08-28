"""WorldState: the environment-facing side of the runtime.

Facts are the current world model (mutated only by executed actions).
Actions are the problem's available operational moves; an action applies
only through the ACT phase of the domain-descent sequencer, never directly
from a conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from .terms import Atom


@dataclass
class WorldState:
    facts: Set[Atom] = field(default_factory=set)
    actions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    applied_actions: List[str] = field(default_factory=list)

    def has_fact(self, atom: Atom) -> bool:
        return atom in self.facts

    def add_fact(self, atom: Atom) -> None:
        self.facts.add(atom)

    def apply_action(self, name: str) -> Dict[str, Any]:
        """Execute an available action; return its effect spec for the
        runtime to fold into the acquisition bank and trace."""
        spec = self.actions.get(name)
        if spec is None:
            raise KeyError(f"action {name} not available")
        for a in spec.get("add_facts", []):
            self.facts.add(a)
        for a in spec.get("remove_facts", []):
            self.facts.discard(a)
        self.applied_actions.append(name)
        return spec

    def sorted_facts(self) -> List[Atom]:
        return sorted(self.facts, key=str)
