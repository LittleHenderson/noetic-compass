"""Phases 5-6: ^6 Male decomposition and ^9 Below/Effect inference.

The reasoning spine. ^6 takes each candidate apart at UNITY GAIN into its
premises, unknowns, and contradictions. ^9 lands a conclusion only when a
complete rule path exists - every conclusion carries its originating
path (the provenance invariant). Both stages are constitution-locked to
beta = 1.0 (the truth firewall).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cjt import BiasRef, CJTConfig, transfer
from .memory import MemorySet
from .ontology import GAIN_EVAL
from .terms import Atom, Rule, instantiate, match, negated_base, prove, unify_conclusion


@dataclass
class DecompositionRecord:
    candidate_id: str
    premises_matched: List[str] = field(default_factory=list)
    premises_missing: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    required_prerequisites: List[Tuple[str, bool]] = field(default_factory=list)
    predicted_effects: Dict[str, float] = field(default_factory=dict)
    support_fraction: float = 0.0
    probe: Optional[dict] = None

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "premises_matched": list(self.premises_matched),
            "premises_missing": list(self.premises_missing),
            "assumptions": list(self.assumptions),
            "dependencies": list(self.dependencies),
            "contradictions": list(self.contradictions),
            "unknowns": list(self.unknowns),
            "required_prerequisites": [[p, ok] for p, ok in self.required_prerequisites],
            "predicted_effects": dict(self.predicted_effects),
            "support_fraction": round(self.support_fraction, 4),
            "probe": self.probe,
        }


@dataclass
class InferenceRecord:
    candidate_id: str
    conclusion: Atom
    success: bool = False
    premises_used: List[str] = field(default_factory=list)
    rules_used: List[str] = field(default_factory=list)
    assumptions_used: List[str] = field(default_factory=list)
    unresolved_unknowns: List[str] = field(default_factory=list)
    confidence: float = 0.0
    contradiction_status: str = "NONE"   # NONE | FALSIFIED | CONTRADICTED
    probe: Optional[dict] = None

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "conclusion": str(self.conclusion),
            "success": self.success,
            "premises_used": list(self.premises_used),
            "rules_used": list(self.rules_used),
            "assumptions_used": list(self.assumptions_used),
            "unresolved_unknowns": list(self.unresolved_unknowns),
            "confidence": round(self.confidence, 4),
            "contradiction_status": self.contradiction_status,
            "probe": self.probe,
        }


def ground_premise_support(rule: Rule, target: Atom, facts: List[Atom]):
    """Extend the rule-conclusion bindings through the premises, reporting
    which premises have fact support and which are missing."""
    bindings = unify_conclusion(rule.conclusion, target)
    if bindings is None:
        return None
    current = dict(bindings)
    matched: List[str] = []
    missing: List[str] = []
    for prem in rule.premises:
        grounded = instantiate(prem, current)
        found = False
        for fact in facts:
            b = match(grounded, fact, current)
            if b is not None:
                current = b
                matched.append(str(instantiate(prem, current)))
                found = True
                break
        if not found:
            missing.append(str(grounded))
    return matched, missing, current


class ReasoningStage:
    def __init__(self, bias_bank: Dict[str, float], probe_tick: callable) -> None:
        self.bias_bank = bias_bank
        self.probe_tick = probe_tick

    def _cfg(self, role: str, label: str, bias: BiasRef) -> CJTConfig:
        return CJTConfig(
            label=label,
            noetic="^6" if role == "decompose" else "^9",
            domain="C",
            drive="F2",
            register="A",
            role=role,
            beta=GAIN_EVAL,
            cutoff=0.2,
            sat=0.95,
            breakdown=1.2,
            bias=bias,
        )

    def decompose(self, candidate, facts: List[Atom], rules: List[Rule], tick: int) -> DecompositionRecord:
        rec = DecompositionRecord(candidate_id=candidate.candidate_id)
        rec.assumptions = list(candidate.assumptions)
        rec.predicted_effects = dict(candidate.authored_effects)
        rec.required_prerequisites = []

        for rule in rules:
            support = ground_premise_support(rule, candidate.target, facts)
            if support is None:
                continue
            matched, missing, _ = support
            rec.premises_matched.extend(matched)
            rec.premises_missing.extend(missing)
            rec.dependencies.append(rule.rule_id)

        rec.unknowns = list(rec.premises_missing)
        total = len(rec.premises_matched) + len(rec.premises_missing)
        rec.support_fraction = (len(rec.premises_matched) / total) if total else 0.0

        # Contradiction check: a stored fact whose predicate negates the target.
        base = negated_base(candidate.target)
        if base is not None:
            for fact in facts:
                if fact.pred == base:
                    rec.contradictions.append(str(fact))

        cfg = self._cfg("decompose", "^6_decomposition_bank",
                        BiasRef("charter_bias", "^5", "P", "F7", "T"))
        bias = self.bias_bank.get("charter_bias", 0.9)
        res = transfer(cause=rec.support_fraction, bias=bias, cfg=cfg, tick=tick)
        rec.probe = res.probe.to_dict()
        return rec

    def infer(self, candidate, decomposition: DecompositionRecord,
              facts: List[Atom], rules: List[Rule], tick: int) -> InferenceRecord:
        rec = InferenceRecord(candidate_id=candidate.candidate_id,
                              conclusion=candidate.target)

        proof = prove(candidate.target, facts, rules)
        rec.success = proof.success
        rec.rules_used = list(proof.rules_used)
        rec.premises_used = [str(f) for f in proof.facts_used]
        rec.unresolved_unknowns = list(decomposition.unknowns)
        rec.confidence = 1.0 if proof.success else 0.0

        # Negation probe: can the opposite of the target be proven?
        base = negated_base(candidate.target)
        opp_proof = None
        if base is not None:
            opp_atom = Atom(base, candidate.target.args)
            opp_proof = prove(opp_atom, facts, rules)
        elif not candidate.target.pred.startswith("not_"):
            opp_atom = Atom("not_" + candidate.target.pred, candidate.target.args)
            opp_proof = prove(opp_atom, facts, rules)

        if opp_proof is not None:
            if opp_proof.success and rec.success:
                rec.contradiction_status = "CONTRADICTED"
            elif opp_proof.success:
                rec.contradiction_status = "FALSIFIED"

        cfg = self._cfg("infer", "^9_inference_bank",
                        BiasRef("memory_bias", "^5", "C", "F2", "A"))
        bias = self.bias_bank.get("memory_bias", 0.7)
        cause = 1.0 if rec.success else decomposition.support_fraction
        res = transfer(cause=cause, bias=bias, cfg=cfg, tick=tick)
        rec.probe = res.probe.to_dict()
        return rec
