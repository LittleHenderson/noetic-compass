"""The coherence checker: the six laws over a semantic document.

A document binds entities, ideas (claims), events, references, and time
assertions. The checker reports typed violations; the proof kernel
re-proves every DERIVED claim's derivation.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from .entity import EntityRegistry, UnknownEntity
from .idea import entity_refs, walk_ideas
from .reference import Resolver, UnresolvedReference
from .relation import RelationSchema, RoleError
from .time import TimeError, Timeline
from .truth import check_claim, check_pairwise, TRUTH_STATUSES

_KERNEL_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "CAS_RRK_v0.1"))
if _KERNEL_ROOT not in sys.path:
    sys.path.insert(0, _KERNEL_ROOT)

from kernel.cas_sem import Proposition, Rule, prove  # noqa: E402


@dataclass
class Violation:
    law: str
    detail: str

    def to_json(self) -> Dict:
        return {"law": self.law, "detail": self.detail}


class CoherenceChecker:
    def __init__(self, doc: Dict, registry: Optional[EntityRegistry] = None) -> None:
        self.doc = doc
        # A registry override makes ablation visible: the document can be
        # checked against the CMB's live entity state.
        self.registry = registry or EntityRegistry(doc.get("entities", []))
        self.resolver = Resolver(self.registry)
        self.timeline = Timeline()
        self.schemas = RelationSchema(doc.get("relation_schemas", {}))
        self.types = doc.get("types", [])

    # ------------------------------------------------------------------
    def check(self) -> List[Violation]:
        violations: List[Violation] = []
        self._check_references(violations)
        self._check_temporal(violations)
        self._check_claims(violations)
        self._check_types(violations)
        self._check_relations(violations)
        self._check_derivations(violations)
        return violations

    # ------------------------------------------------------------------
    def _check_references(self, out: List[Violation]) -> None:
        for ref in self.doc.get("references", []):
            try:
                self.resolver.resolve(ref)
            except UnresolvedReference as exc:
                out.append(Violation("referential_integrity", str(exc)))
        for claim_record in self.doc.get("claims", []):
            for entity_id in entity_refs(claim_record.get("idea", {})):
                if not self.registry.has(entity_id):
                    out.append(Violation(
                        "referential_integrity",
                        f"idea references unknown entity '{entity_id}'"))
        for event in self.doc.get("events", []):
            for entity_id in entity_refs(event):
                if not self.registry.has(entity_id):
                    out.append(Violation(
                        "referential_integrity",
                        f"event references unknown entity '{entity_id}'"))

    def _check_temporal(self, out: List[Violation]) -> None:
        for assertion in self.doc.get("time_assertions", []):
            try:
                self.timeline.assert_order(assertion["earlier"],
                                           assertion["later"])
            except TimeError as exc:
                out.append(Violation("temporal_consistency", str(exc)))

    def _check_claims(self, out: List[Violation]) -> None:
        seen: List[Dict] = []
        for record in self.doc.get("claims", []):
            try:
                check_claim(record)
            except Exception as exc:
                out.append(Violation("truth_discipline", str(exc)))
            for prior in seen:
                try:
                    check_pairwise(prior, record)
                except Exception as exc:
                    out.append(Violation("truth_discipline", str(exc)))
            seen.append(record)
            if "provenance" not in record:
                out.append(Violation(
                    "provenance_completeness",
                    f"claim about {record.get('idea')} has no provenance"))

    def _check_types(self, out: List[Violation]) -> None:
        for record in self.doc.get("claims", []):
            idea = record.get("idea", {})
            if idea.get("kind") == "property" and self.types:
                try:
                    entity_type = self.registry.type_of(idea["entity"])
                except UnknownEntity:
                    continue
                allowed = self.doc.get("property_domain", {}).get(
                    idea["property"])
                if allowed is not None and entity_type not in allowed:
                    out.append(Violation(
                        "type_discipline",
                        f"property '{idea['property']}' does not apply to "
                        f"type '{entity_type}'"))

    def _check_relations(self, out: List[Violation]) -> None:
        for record in self.doc.get("claims", []):
            node = record.get("idea", {})
            if node.get("kind") == "relation":
                try:
                    self.schemas.check(node["pred"], node["roles"])
                except RoleError as exc:
                    out.append(Violation("relation_schema", str(exc)))
        for event in self.doc.get("events", []):
            try:
                self.schemas.check(event["pred"], event["roles"])
            except RoleError as exc:
                out.append(Violation("relation_schema", str(exc)))

    def _check_derivations(self, out: List[Violation]) -> None:
        for record in self.doc.get("claims", []):
            if record.get("truth") != "DERIVED":
                continue
            derivation = record.get("derivation", {})
            props = [Proposition(p["pred"], tuple(p.get("args", [])))
                     for p in derivation.get("propositions", [])]
            rules = [Rule(r["rule_id"],
                          tuple(Proposition(p["pred"], tuple(p.get("args", [])))
                                for p in r.get("premises", [])),
                          Proposition(r["conclusion"]["pred"],
                                      tuple(r["conclusion"].get("args", []))),
                          r.get("source", ""))
                     for r in derivation.get("rules", [])]
            goal = Proposition(derivation["conclusion"]["pred"],
                               tuple(derivation["conclusion"].get("args", [])))
            proof = prove(goal, props, rules)
            if not proof.success:
                out.append(Violation(
                    "derivation_validity",
                    f"DERIVED claim {record.get('idea')} does not re-prove "
                    "through the proof kernel"))
