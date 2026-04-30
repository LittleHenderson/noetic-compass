"""Turn-type admissibility hooks for CAS Transformer transitions.

This module is compiler-adjacent: it does not parse CAS notation, but it gives
service/model code a deterministic gate for deciding whether a proposed
conversational transition is admissible in the prior CAS state.

The compiler validates expression structure. These hooks validate behavioral
preconditions for surface acts such as CLARIFY, REFUSE, REPAIR, and ANSWER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


TURN_TYPES = (
    "OPEN",
    "ACK",
    "MIRROR",
    "CLARIFY",
    "EMPATHIZE",
    "ANSWER",
    "PLAN",
    "REFUSE",
    "REFUSE_CLAIM",
    "REPAIR",
    "CLOSE",
)

BLOCKED_AUTHORITY_LICENSES = {
    ("UserRequestSet", "SystemInstructionSet"),
    ("UserRequestSet", "DeveloperInstructionSet"),
    ("ToolObservationSet", "SystemInstructionSet"),
    ("RenderedResponseSet", "SystemInstructionSet"),
}

ADMITTED_AUTHORITY_LICENSES = {
    ("ToolObservationSet", "EvidenceSet"),
    ("EvidenceSet", "ValidatedClaimSet"),
    ("ValidatedClaimSet", "RenderedResponseSet"),
    ("UserRequestSet", "TaskIntentSet"),
    ("TaskIntentSet", "CASActionSet"),
    ("SystemInstructionSet", "CASActionSet"),
    ("DeveloperInstructionSet", "CASActionSet"),
}


@dataclass(frozen=True)
class TurnAdmissibilityRule:
    """One turn-type rule."""

    turn_type: str
    required_facts: frozenset[str]
    valid_effects: tuple[str, ...]
    description: str
    tight: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_type": self.turn_type,
            "required_facts": sorted(self.required_facts),
            "valid_effects": list(self.valid_effects),
            "description": self.description,
            "tight": self.tight,
        }


TURN_ADMISSIBILITY_RULES: dict[str, TurnAdmissibilityRule] = {
    "OPEN": TurnAdmissibilityRule(
        "OPEN",
        frozenset({"channel_idle"}),
        ("attention_oriented", "dialogue_opened"),
        "Opening is admissible only when the channel is idle or unopened.",
    ),
    "ACK": TurnAdmissibilityRule(
        "ACK",
        frozenset({"input_received"}),
        ("receipt_stabilized",),
        "Acknowledgment requires a received input.",
    ),
    "MIRROR": TurnAdmissibilityRule(
        "MIRROR",
        frozenset({"user_intent_present"}),
        ("intent_restated", "trace_aligned"),
        "Mirroring requires a recoverable user intent.",
    ),
    "CLARIFY": TurnAdmissibilityRule(
        "CLARIFY",
        frozenset({"lacunarity_detected", "unfilled_slot_present"}),
        ("missing_constraint_requested",),
        "Clarification requires detected lacunarity and a concrete unfilled slot.",
        tight=True,
    ),
    "EMPATHIZE": TurnAdmissibilityRule(
        "EMPATHIZE",
        frozenset({"affect_detected"}),
        ("affect_acknowledged",),
        "Empathy requires an affective signal in the prior state.",
    ),
    "ANSWER": TurnAdmissibilityRule(
        "ANSWER",
        frozenset({"task_active", "claim_supported"}),
        ("supported_response_rendered",),
        "Answering requires an active task and support for the claim.",
        tight=True,
    ),
    "PLAN": TurnAdmissibilityRule(
        "PLAN",
        frozenset({"task_active"}),
        ("next_actions_decomposed",),
        "Planning requires an active task.",
    ),
    "REFUSE": TurnAdmissibilityRule(
        "REFUSE",
        frozenset({"boundary_violation"}),
        ("boundary_preserved", "alternative_path_available"),
        "Refusal requires an authority, capability, or typed boundary violation.",
        tight=True,
    ),
    "REFUSE_CLAIM": TurnAdmissibilityRule(
        "REFUSE_CLAIM",
        frozenset({"evidence_gap"}),
        ("unsupported_claim_blocked",),
        "Claim-refusal requires an evidence gap or failed evidence-to-claim path.",
        tight=True,
    ),
    "REPAIR": TurnAdmissibilityRule(
        "REPAIR",
        frozenset({"prior_error_detected"}),
        ("trace_repaired",),
        "Repair requires a detected prior error.",
        tight=True,
    ),
    "CLOSE": TurnAdmissibilityRule(
        "CLOSE",
        frozenset({"response_delivered"}),
        ("dialogue_turn_closed",),
        "Closing requires a delivered response or completed trace pass.",
    ),
}


@dataclass(frozen=True)
class MetaLogicRelation:
    """Minimal relation representation for admissibility hooks."""

    source: str
    relation: str
    target: str

    @classmethod
    def from_value(cls, value: Any) -> "MetaLogicRelation":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                str(value.get("source", "")),
                str(value.get("relation", "")),
                str(value.get("target", "")),
            )
        if isinstance(value, (tuple, list)) and len(value) == 3:
            return cls(str(value[0]), str(value[1]), str(value[2]))
        raise TypeError(f"cannot build MetaLogicRelation from {value!r}")

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
        }


@dataclass(frozen=True)
class TurnAdmissibilityContext:
    """Prior state facts and meta-logic relations for a proposed turn."""

    facts: frozenset[str] = frozenset()
    unfilled_slots: tuple[str, ...] = ()
    meta_relations: tuple[MetaLogicRelation, ...] = ()
    evidence_paths: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None = None, **overrides: Any) -> "TurnAdmissibilityContext":
        data: dict[str, Any] = dict(payload or {})
        data.update(overrides)
        facts = frozenset(str(item) for item in data.get("facts", ()) if str(item))
        unfilled_slots = tuple(
            str(item) for item in data.get("unfilled_slots", ()) if str(item)
        )
        meta_relations = tuple(
            MetaLogicRelation.from_value(item)
            for item in data.get("meta_relations", ())
        )
        evidence_paths = tuple(
            (str(item[0]), str(item[1]))
            for item in data.get("evidence_paths", ())
            if isinstance(item, (tuple, list)) and len(item) == 2
        )
        return cls(
            facts=facts,
            unfilled_slots=unfilled_slots,
            meta_relations=meta_relations,
            evidence_paths=evidence_paths,
        )

    def derived_facts(self) -> frozenset[str]:
        facts = set(self.facts)
        if self.unfilled_slots:
            facts.add("unfilled_slot_present")
        if _has_blocked_authority_relation(self.meta_relations):
            facts.add("boundary_violation")
            facts.add("authority_violation")
        if _has_evidence_gap(self.meta_relations, self.evidence_paths, self.facts):
            facts.add("evidence_gap")
        return frozenset(facts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": sorted(self.facts),
            "derived_facts": sorted(self.derived_facts() - self.facts),
            "unfilled_slots": list(self.unfilled_slots),
            "meta_relations": [relation.to_dict() for relation in self.meta_relations],
            "evidence_paths": [
                {"source": source, "target": target}
                for source, target in self.evidence_paths
            ],
        }


@dataclass(frozen=True)
class TurnAdmissibilityResult:
    """Structured compiler-hook result for a proposed turn type."""

    turn_type: str
    admissible: bool
    required_facts: tuple[str, ...]
    observed_facts: tuple[str, ...]
    missing_facts: tuple[str, ...]
    valid_effects: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    tight: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_type": self.turn_type,
            "admissible": self.admissible,
            "required_facts": list(self.required_facts),
            "observed_facts": list(self.observed_facts),
            "missing_facts": list(self.missing_facts),
            "valid_effects": list(self.valid_effects),
            "diagnostics": list(self.diagnostics),
            "tight": self.tight,
        }


def validate_turn_admissibility(
    turn_type: str,
    context: TurnAdmissibilityContext | Mapping[str, Any] | None = None,
) -> TurnAdmissibilityResult:
    """Validate whether a conversational turn is admissible in prior state."""

    normalized = str(turn_type).upper()
    rule = TURN_ADMISSIBILITY_RULES.get(normalized)
    ctx = (
        context
        if isinstance(context, TurnAdmissibilityContext)
        else TurnAdmissibilityContext.from_payload(context)
    )
    observed = ctx.derived_facts()
    if rule is None:
        return TurnAdmissibilityResult(
            turn_type=normalized,
            admissible=False,
            required_facts=(),
            observed_facts=tuple(sorted(observed)),
            missing_facts=(),
            diagnostics=(f"unknown turn_type {turn_type!r}",),
        )

    missing = tuple(sorted(rule.required_facts - observed))
    diagnostics = _diagnostics_for(normalized, ctx, missing)
    return TurnAdmissibilityResult(
        turn_type=normalized,
        admissible=not missing and not any(_is_error_diag(item) for item in diagnostics),
        required_facts=tuple(sorted(rule.required_facts)),
        observed_facts=tuple(sorted(observed)),
        missing_facts=missing,
        valid_effects=rule.valid_effects,
        diagnostics=diagnostics,
        tight=rule.tight,
    )


def turn_admissibility_artifact(
    turn_type: str,
    context: TurnAdmissibilityContext | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a JSON-ready compiler artifact for service/model logging."""

    result = validate_turn_admissibility(turn_type, context)
    return {
        "kind": "turn_admissibility",
        "version": "turn_admissibility_v0",
        "result": result.to_dict(),
    }


def list_turn_admissibility_rules() -> dict[str, dict[str, Any]]:
    """Expose the current rule table for docs/tests/UI."""

    return {
        turn_type: rule.to_dict()
        for turn_type, rule in sorted(TURN_ADMISSIBILITY_RULES.items())
    }


def _has_blocked_authority_relation(relations: Iterable[MetaLogicRelation]) -> bool:
    for relation in relations:
        if relation.relation == "licenses" and (relation.source, relation.target) in BLOCKED_AUTHORITY_LICENSES:
            return True
    return False


def _has_evidence_gap(
    relations: Iterable[MetaLogicRelation],
    evidence_paths: Iterable[tuple[str, str]],
    facts: frozenset[str],
) -> bool:
    claim_attempted = bool(
        {"claim_attempted", "unsupported_claim_present", "claim_support_requested"}
        & facts
    )
    unsupported_license_attempt = any(
        relation.relation == "licenses"
        and relation.target == "ValidatedClaimSet"
        and relation.source != "EvidenceSet"
        for relation in relations
    )
    if not claim_attempted and not unsupported_license_attempt:
        return False
    if any((source, target) == ("EvidenceSet", "ValidatedClaimSet") for source, target in evidence_paths):
        return False
    for relation in relations:
        if (
            relation.relation == "licenses"
            and (relation.source, relation.target) == ("EvidenceSet", "ValidatedClaimSet")
        ):
            return False
    return True


def _diagnostics_for(
    turn_type: str,
    context: TurnAdmissibilityContext,
    missing: tuple[str, ...],
) -> tuple[str, ...]:
    diagnostics = [f"missing required fact {fact!r}" for fact in missing]
    if turn_type == "CLARIFY" and "unfilled_slot_present" in missing:
        diagnostics.append("CLARIFY requires at least one named unfilled slot")
    if turn_type == "REFUSE" and _has_blocked_authority_relation(context.meta_relations):
        diagnostics.append("blocked authority relation detected and preserved")
    if turn_type == "REFUSE_CLAIM" and "evidence_gap" not in missing:
        diagnostics.append("evidence gap detected; claim refusal is licensed")
    return tuple(diagnostics)


def _is_error_diag(diagnostic: str) -> bool:
    return not diagnostic.endswith("detected and preserved") and not diagnostic.endswith("is licensed")
