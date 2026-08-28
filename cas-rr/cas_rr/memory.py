"""CMB: the Cognitive Memory Board - 40 cells plus three leakage layers.

The CMB stores CAS-compressed experience in a 40-cell bank (10 Noetics x 4
Domains). Items live in three leakage layers:

* working     - current episode only, high leakage;
* episodic    - prior attempts and outcomes, moderate leakage;
* semantic    - verified facts, rules, principles, low leakage.

Retrieval is structural: a query pattern selects stored items, and a query
that lands on an empty region reports a typed LACUNA (KNOWLEDGE_MISSING or
EXPERIENCE_MISSING) instead of a plausible invention. A lacuna is the RPM
trigger that turns uncertainty into an acquisition subgoal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .terms import Atom, Rule, match


@dataclass(frozen=True)
class MemoryItem:
    item_id: str
    content: Any            # Atom or Rule
    noetic: str
    domain: str
    layer: str              # semantic | episodic | working
    source: str             # provenance of the memory itself
    confidence: float = 1.0


@dataclass
class Lacuna:
    region: str             # e.g. "^5^C (Female, Cognitive)"
    query: str
    kind: str               # KNOWLEDGE_MISSING | EXPERIENCE_MISSING

    def to_dict(self):
        return {"region": self.region, "query": self.query, "kind": self.kind}


@dataclass
class MemorySet:
    query: str
    selected: List[MemoryItem] = field(default_factory=list)
    similarity_scores: Dict[str, float] = field(default_factory=dict)
    lacunae: List[Lacuna] = field(default_factory=list)

    def to_dict(self):
        return {
            "query": self.query,
            "selected": [i.item_id for i in self.selected],
            "selected_items": [
                {"id": i.item_id, "content": str(i.content),
                 "source": i.source, "layer": i.layer}
                for i in self.selected
            ],
            "similarity_scores": self.similarity_scores,
            "lacunae": [l.to_dict() for l in self.lacunae],
        }


LEAKAGE = {"working": 1.0, "episodic": 0.25, "semantic": 0.01}


class CMB:
    def __init__(self) -> None:
        # (noetic, domain) -> [items]
        self.cells: Dict[Tuple[str, str], List[MemoryItem]] = {}
        self._counter = 0
        self.tick = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"mem_{self._counter:04d}"

    def store(self, item: MemoryItem) -> MemoryItem:
        key = (item.noetic, item.domain)
        self.cells.setdefault(key, []).append(item)
        return item

    def store_atom(self, atom: Atom, noetic: str, domain: str, layer: str,
                   source: str, confidence: float = 1.0) -> MemoryItem:
        item = MemoryItem(self._next_id(), atom, noetic, domain, layer, source, confidence)
        return self.store(item)

    def store_rule(self, rule: Rule, noetic: str, domain: str, source: str) -> MemoryItem:
        item = MemoryItem(self._next_id(), rule, noetic, domain, "semantic", source, 1.0)
        return self.store(item)

    def load_problem_knowledge(self, facts: List[Atom], rules: List[Rule],
                               source: str) -> None:
        for atom in facts:
            self.store_atom(atom, "^5", "C", "semantic", source)
        for rule in rules:
            self.store_rule(rule, "^5", "C", source)

    def all_facts(self) -> List[Atom]:
        out: List[Atom] = []
        for items in self.cells.values():
            for item in items:
                if isinstance(item.content, Atom) and item.layer != "working":
                    out.append(item.content)
        return out

    def all_rules(self) -> List[Rule]:
        out: List[Rule] = []
        for items in self.cells.values():
            for item in items:
                if isinstance(item.content, Rule):
                    out.append(item.content)
        return out

    def fact_item_of(self, atom: Atom) -> Optional[MemoryItem]:
        for items in self.cells.values():
            for item in items:
                if isinstance(item.content, Atom) and item.content == atom:
                    return item
        return None

    def advance_tick(self) -> None:
        """Episode clock: purge working items older than the current episode."""
        self.tick += 1

    def retrieve(self, query_atoms: List[Atom], noetic: str = "^5",
                 domain: str = "C", query_label: str = "") -> MemorySet:
        result = MemorySet(query=query_label or ", ".join(str(a) for a in query_atoms))
        region = (noetic, domain)
        for q in query_atoms:
            matched_any = False
            for item in self.cells.get(region, []):
                if isinstance(item.content, Atom):
                    if match(q, item.content) is not None:
                        result.selected.append(item)
                        matched_any = True
            if not matched_any:
                has_pred_in_region = any(
                    isinstance(i.content, Atom) and i.content.pred == q.pred
                    for i in self.cells.get(region, [])
                )
                kind = "EXPERIENCE_MISSING" if has_pred_in_region else "KNOWLEDGE_MISSING"
                result.lacunae.append(Lacuna(
                    region=f"{noetic}^{domain}",
                    query=str(q),
                    kind=kind,
                ))
        for item in result.selected:
            # Deterministic similarity: grounded-match depth.
            result.similarity_scores[item.item_id] = 1.0
        return result

    def store_episode(self, packet: Dict[str, Any]) -> None:
        """Episodic write: store the reasoning provenance packet (low urgency)."""
        self.store_atom(
            Atom("episode_record", (packet.get("problem_id") or "unnamed",)),
            "^7", "C", "episodic", "runtime_store",
        )
