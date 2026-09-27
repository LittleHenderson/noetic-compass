"""Immutable semantic, kernel-state, intent, and trace types."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .canonical import content_id, digest, to_primitive


RUNTIME_VERSION = "0.1.0"
PROBLEM_SCHEMA_VERSION = "cncm.problem/0.1"
EVIDENCE_SCHEMA_VERSION = "cncm.evidence/0.1"
CANONICAL_NOETICS = tuple(range(10))
CANONICAL_DOMAINS = ("P", "C", "E", "O")
CANONICAL_DRIVES = tuple(f"F{index}" for index in range(1, 8))
CANONICAL_REGISTERS = ("T", "A", "f", "E")
FOUNDATION_REFERENCES = tuple(f"TF{index}" for index in range(1, 8)) + tuple(
    f"TF{index}{world}" for index in range(1, 8) for world in "abcd"
)
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
OPAQUE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.:-]*$")


class ContractError(ValueError):
    """A typed input or invariant contract was violated."""


class EvidenceStatus(str, Enum):
    ASSERTED = "asserted"
    DERIVED = "derived"
    HYPOTHETICAL = "hypothetical"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class BranchStatus(str, Enum):
    OPEN = "OPEN"
    BLOCKED = "BLOCKED"
    CONTRADICTED = "CONTRADICTED"
    DOMINATED = "DOMINATED"
    ADMISSIBLE = "ADMISSIBLE"
    SELECTED = "SELECTED"
    COMMITTED = "COMMITTED"
    DISCARDED = "DISCARDED"
    FAULTED = "FAULTED"


class TerminalStatus(str, Enum):
    RUNNING = "RUNNING"
    CONCLUDED = "CONCLUDED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    NEEDS_CAPABILITY = "NEEDS_CAPABILITY"
    CONFLICT_UNRESOLVED = "CONFLICT_UNRESOLVED"
    INADMISSIBLE = "INADMISSIBLE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    LOOP_LIMIT_REACHED = "LOOP_LIMIT_REACHED"
    DEADLOCK = "DEADLOCK"
    FAULT = "FAULT"


class IntentType(str, Enum):
    FORK_BRANCH = "FORK_BRANCH"
    DERIVE_PROPOSITION = "DERIVE_PROPOSITION"
    RECORD_DECOMPOSITION = "RECORD_DECOMPOSITION"
    RECORD_CONTRADICTION = "RECORD_CONTRADICTION"
    SET_BRANCH_STATUS = "SET_BRANCH_STATUS"
    DISCARD_BRANCH = "DISCARD_BRANCH"
    RECORD_COMPARISON = "RECORD_COMPARISON"
    PUSH_RPM = "PUSH_RPM"
    RETURN_RPM = "RETURN_RPM"
    DECISION_COMMIT = "DECISION_COMMIT"
    WRITE_EPISODE = "WRITE_EPISODE"
    HALT = "HALT"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    PROTECTED_PATCH = "PROTECTED_PATCH"


class InferenceOperation(str, Enum):
    RECALL = "RECALL"
    ASSOCIATE = "ASSOCIATE"
    DECOMPOSE = "DECOMPOSE"
    INFER_MODUS_PONENS = "INFER_MODUS_PONENS"
    INFER_TRANSITIVE = "INFER_TRANSITIVE"
    RPM_CHILD_RESULT = "RPM_CHILD_RESULT"


class RejectionReason(str, Enum):
    UNAUTHORIZED_ISSUER = "UNAUTHORIZED_ISSUER"
    INTENT_TYPE_PROHIBITED = "INTENT_TYPE_PROHIBITED"
    INVALID_TARGET_SCOPE = "INVALID_TARGET_SCOPE"
    STALE_SNAPSHOT = "STALE_SNAPSHOT"
    INTENT_CONFLICT = "INTENT_CONFLICT"
    BRANCH_NOT_FOUND = "BRANCH_NOT_FOUND"
    BRANCH_NOT_WRITABLE = "BRANCH_NOT_WRITABLE"
    INVALID_PROOF = "INVALID_PROOF"
    DUPLICATE_ID = "DUPLICATE_ID"
    BRANCH_BUDGET_EXHAUSTED = "BRANCH_BUDGET_EXHAUSTED"
    INFERENCE_BUDGET_EXHAUSTED = "INFERENCE_BUDGET_EXHAUSTED"
    MEMORY_BUDGET_EXHAUSTED = "MEMORY_BUDGET_EXHAUSTED"
    STACK_FAULT = "STACK_FAULT"
    RPM_DEPTH_EXHAUSTED = "RPM_DEPTH_EXHAUSTED"
    RPM_CYCLE = "RPM_CYCLE"
    COMMITMENT_GATES_FAILED = "COMMITMENT_GATES_FAILED"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    UNSEALED_TRACE = "UNSEALED_TRACE"
    UNCOMMITTED_LEARNING_SOURCE = "UNCOMMITTED_LEARNING_SOURCE"
    DISCARDED_BRANCH_REFERENCE = "DISCARDED_BRANCH_REFERENCE"
    INVALID_TERMINAL_STATUS = "INVALID_TERMINAL_STATUS"
    MALFORMED_MUTATION = "MALFORMED_MUTATION"


def _strict_keys(data: Mapping[str, Any], required: set[str], optional: set[str], label: str) -> None:
    keys = set(data)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ContractError(f"{label} missing keys: {sorted(missing)}")
    if extra:
        raise ContractError(f"{label} unknown keys: {sorted(extra)}")


def _identifier(value: Any, label: str, *, allow_variable: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a nonempty string")
    if allow_variable and value.startswith("?"):
        if not IDENTIFIER.fullmatch(value[1:]):
            raise ContractError(f"{label} has invalid variable syntax")
        return value
    if not IDENTIFIER.fullmatch(value):
        raise ContractError(f"{label} has invalid identifier syntax")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a nonempty string")
    return value


def _strict_integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ContractError(f"{label} must be at least {minimum}")
    return value


def _opaque_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not OPAQUE_IDENTIFIER.fullmatch(value):
        raise ContractError(f"{label} has invalid opaque identifier syntax")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ContractError(f"{label} must be a list of strings")
    return tuple(value)


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ContractError("intent objects require string keys")
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise ContractError(f"unsupported intent value type: {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Provenance:
    source_type: str
    source_id: str
    detail: str = ""

    def __post_init__(self) -> None:
        _identifier(self.source_type, "source_type")
        _opaque_identifier(self.source_id, "source_id")
        if not isinstance(self.detail, str):
            raise ContractError("Provenance.detail must be a string")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Provenance":
        _strict_keys(data, {"source_type", "source_id"}, {"detail"}, "Provenance")
        detail = data.get("detail", "")
        if not isinstance(detail, str):
            raise ContractError("Provenance.detail must be a string")
        return cls(
            _identifier(data["source_type"], "source_type"),
            _opaque_identifier(data["source_id"], "source_id"),
            detail,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class EntityDecl:
    entity_id: str
    entity_type: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EntityDecl":
        _strict_keys(data, {"entity_id", "entity_type"}, set(), "EntityDecl")
        return cls(
            entity_id=_identifier(data["entity_id"], "entity_id"),
            entity_type=_identifier(data["entity_type"], "entity_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class PredicateDecl:
    predicate_id: str
    argument_types: tuple[str, ...]
    transitive: bool = False

    def __post_init__(self) -> None:
        _identifier(self.predicate_id, "predicate_id")
        if not self.argument_types:
            raise ContractError("PredicateDecl.argument_types must not be empty")
        for argument_type in self.argument_types:
            _identifier(argument_type, "argument_type")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PredicateDecl":
        _strict_keys(data, {"predicate_id", "argument_types"}, {"transitive"}, "PredicateDecl")
        argument_types = data["argument_types"]
        if not isinstance(argument_types, list) or not argument_types:
            raise ContractError("PredicateDecl.argument_types must be a nonempty list")
        transitive = data.get("transitive", False)
        if not isinstance(transitive, bool):
            raise ContractError("PredicateDecl.transitive must be boolean")
        return cls(
            predicate_id=_identifier(data["predicate_id"], "predicate_id"),
            argument_types=tuple(_identifier(item, "argument_type") for item in argument_types),
            transitive=transitive,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class Proposition:
    predicate: str
    arguments: tuple[str, ...]
    polarity: bool = True
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    provenance: tuple[Provenance, ...] = ()
    scope: str = "global"

    def __post_init__(self) -> None:
        _identifier(self.predicate, "predicate")
        _identifier(self.scope, "scope")
        if not self.arguments:
            raise ContractError("a proposition requires at least one argument")
        for argument in self.arguments:
            _identifier(
                argument,
                "argument",
                allow_variable=isinstance(argument, str) and argument.startswith("?"),
            )
        if not isinstance(self.polarity, bool):
            raise ContractError("Proposition.polarity must be boolean")
        if not isinstance(self.evidence_status, EvidenceStatus):
            raise ContractError("Proposition.evidence_status must be typed")
        if any(not isinstance(item, Provenance) for item in self.provenance):
            raise ContractError("Proposition.provenance must contain Provenance values")

    @property
    def atom_key(self) -> str:
        return f"{self.predicate}({','.join(self.arguments)})@{self.scope}"

    @property
    def key(self) -> str:
        return ("" if self.polarity else "not:") + self.atom_key

    def with_status(self, status: EvidenceStatus, provenance: Iterable[Provenance] | None = None) -> "Proposition":
        return replace(
            self,
            evidence_status=status,
            provenance=tuple(provenance) if provenance is not None else self.provenance,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, allow_variables: bool = False) -> "Proposition":
        _strict_keys(
            data,
            {"predicate", "arguments"},
            {"polarity", "evidence_status", "provenance", "scope"},
            "Proposition",
        )
        arguments_raw = data["arguments"]
        if not isinstance(arguments_raw, list) or not arguments_raw:
            raise ContractError("Proposition.arguments must be a nonempty list")
        arguments = tuple(
            _identifier(item, "argument", allow_variable=allow_variables) for item in arguments_raw
        )
        provenance_raw = data.get("provenance", [])
        if not isinstance(provenance_raw, list):
            raise ContractError("Proposition.provenance must be a list")
        try:
            status = EvidenceStatus(data.get("evidence_status", EvidenceStatus.UNKNOWN.value))
        except ValueError as exc:
            raise ContractError("invalid evidence_status") from exc
        polarity = data.get("polarity", True)
        if not isinstance(polarity, bool):
            raise ContractError("Proposition.polarity must be boolean")
        return cls(
            predicate=_identifier(data["predicate"], "predicate"),
            arguments=arguments,
            polarity=polarity,
            evidence_status=status,
            provenance=tuple(
                sorted(
                    (Provenance.from_dict(item) for item in provenance_raw),
                    key=lambda item: (item.source_type, item.source_id, item.detail),
                )
            ),
            scope=_identifier(data.get("scope", "global"), "scope"),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    operation: InferenceOperation
    antecedents: tuple[Proposition, ...]
    consequent: Proposition
    provenance: tuple[Provenance, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Rule":
        _strict_keys(
            data,
            {"rule_id", "operation", "antecedents", "consequent"},
            {"provenance"},
            "Rule",
        )
        antecedents_raw = data["antecedents"]
        if not isinstance(antecedents_raw, list) or not antecedents_raw:
            raise ContractError("Rule.antecedents must be a nonempty list")
        try:
            operation = InferenceOperation(data["operation"])
        except ValueError as exc:
            raise ContractError("unsupported Rule.operation") from exc
        if operation not in {
            InferenceOperation.INFER_MODUS_PONENS,
            InferenceOperation.INFER_TRANSITIVE,
        }:
            raise ContractError("rules may use only declared inference operations")
        provenance_raw = data.get("provenance", [])
        return cls(
            rule_id=_identifier(data["rule_id"], "rule_id"),
            operation=operation,
            antecedents=tuple(
                sorted(
                    (Proposition.from_dict(item, allow_variables=True) for item in antecedents_raw),
                    key=lambda item: item.key,
                )
            ),
            consequent=Proposition.from_dict(data["consequent"], allow_variables=True),
            provenance=tuple(
                sorted(
                    (Provenance.from_dict(item) for item in provenance_raw),
                    key=lambda item: (item.source_type, item.source_id, item.detail),
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_id: str
    facts: tuple[Proposition, ...] = ()
    assumptions: tuple[Proposition, ...] = ()
    hard_constraints: tuple[Proposition, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateSpec":
        _strict_keys(data, {"candidate_id"}, {"facts", "assumptions", "hard_constraints"}, "CandidateSpec")
        return cls(
            candidate_id=_identifier(data["candidate_id"], "candidate_id"),
            facts=tuple(sorted((Proposition.from_dict(item) for item in data.get("facts", [])), key=lambda item: item.key)),
            assumptions=tuple(
                sorted((Proposition.from_dict(item) for item in data.get("assumptions", [])), key=lambda item: item.key)
            ),
            hard_constraints=tuple(
                sorted((Proposition.from_dict(item) for item in data.get("hard_constraints", [])), key=lambda item: item.key)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class ResolverSpec:
    target: Proposition
    facts: tuple[Proposition, ...]
    rules: tuple[Rule, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResolverSpec":
        _strict_keys(data, {"target", "facts"}, {"rules"}, "ResolverSpec")
        return cls(
            target=Proposition.from_dict(data["target"]),
            facts=tuple(sorted((Proposition.from_dict(item) for item in data["facts"]), key=lambda item: item.key)),
            rules=tuple(sorted((Rule.from_dict(item) for item in data.get("rules", [])), key=lambda item: item.rule_id)),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class BudgetLimits:
    max_ticks: int = 128
    max_branches: int = 8
    max_rpm_depth: int = 4
    max_inference_steps: int = 64
    max_memory_queries: int = 8
    max_repeat_states: int = 3

    def __post_init__(self) -> None:
        for name in (
            "max_ticks",
            "max_branches",
            "max_rpm_depth",
            "max_inference_steps",
            "max_memory_queries",
            "max_repeat_states",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ContractError(f"{name} must be a positive integer")
        if self.max_ticks < 2:
            raise ContractError("max_ticks must reserve at least one transition and one traced halt")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BudgetLimits":
        allowed = {
            "max_ticks",
            "max_branches",
            "max_rpm_depth",
            "max_inference_steps",
            "max_memory_queries",
            "max_repeat_states",
        }
        _strict_keys(data, set(), allowed, "BudgetLimits")
        return cls(**{key: data[key] for key in data})

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class ProblemPacket:
    schema_version: str
    problem_id: str
    goal_id: str
    seed: int
    entities: tuple[EntityDecl, ...]
    predicates: tuple[PredicateDecl, ...]
    facts: tuple[Proposition, ...]
    rules: tuple[Rule, ...]
    query: Proposition
    candidates: tuple[CandidateSpec, ...] = ()
    rpm_resolvers: tuple[ResolverSpec, ...] = ()
    foundation_ref: str | None = None
    budgets: BudgetLimits = field(default_factory=BudgetLimits)

    def __post_init__(self) -> None:
        if self.schema_version != PROBLEM_SCHEMA_VERSION:
            raise ContractError(f"schema_version must be {PROBLEM_SCHEMA_VERSION}")
        _identifier(self.problem_id, "problem_id")
        _identifier(self.goal_id, "goal_id")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ContractError("seed must be a nonnegative integer")
        if self.foundation_ref is not None and self.foundation_ref not in FOUNDATION_REFERENCES:
            raise ContractError("foundation_ref must be an opaque TF1-TF7 or TF1a-TF7d identifier")
        entity_map = {item.entity_id: item.entity_type for item in self.entities}
        if len(entity_map) != len(self.entities):
            raise ContractError("entity_id values must be unique")
        predicate_map = {item.predicate_id: item for item in self.predicates}
        if len(predicate_map) != len(self.predicates):
            raise ContractError("predicate_id values must be unique")
        candidate_ids = [item.candidate_id for item in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ContractError("candidate_id values must be unique")
        if "root" in candidate_ids:
            raise ContractError("candidate_id 'root' is reserved for the structural root branch")
        fact_keys = [item.key for item in self.facts]
        if len(fact_keys) != len(set(fact_keys)):
            raise ContractError("input facts must have unique semantic keys")
        rule_ids = [item.rule_id for item in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ContractError("rule_id values must be unique")
        resolver_targets = [item.target.key for item in self.rpm_resolvers]
        if len(resolver_targets) != len(set(resolver_targets)):
            raise ContractError("RPM resolver target keys must be unique")
        for fact in self.facts:
            if fact.evidence_status is not EvidenceStatus.ASSERTED:
                raise ContractError("input facts must have asserted evidence_status")
            if not fact.provenance:
                raise ContractError("input facts must carry provenance")
        if any(not rule.provenance for rule in self.rules):
            raise ContractError("input rules must carry provenance")
        for candidate in self.candidates:
            candidate_evidence_keys = [item.key for item in (*candidate.facts, *candidate.assumptions)]
            if len(candidate_evidence_keys) != len(set(candidate_evidence_keys)):
                raise ContractError("candidate facts and assumptions must have unique semantic keys")
            constraint_keys = [item.key for item in candidate.hard_constraints]
            if len(constraint_keys) != len(set(constraint_keys)):
                raise ContractError("candidate hard constraints must have unique semantic keys")
            if any(item.evidence_status is not EvidenceStatus.ASSERTED for item in candidate.facts):
                raise ContractError("candidate facts must have asserted evidence_status")
            if any(not item.provenance for item in candidate.facts):
                raise ContractError("candidate facts must carry provenance")
            if any(item.evidence_status is not EvidenceStatus.HYPOTHETICAL for item in candidate.assumptions):
                raise ContractError("candidate assumptions must have hypothetical evidence_status")
            if any(not item.provenance for item in candidate.assumptions):
                raise ContractError("candidate assumptions must carry provenance")
        for resolver in self.rpm_resolvers:
            resolver_fact_keys = [item.key for item in resolver.facts]
            if len(resolver_fact_keys) != len(set(resolver_fact_keys)):
                raise ContractError("RPM resolver facts must have unique semantic keys")
            resolver_rule_ids = [item.rule_id for item in resolver.rules]
            if len(resolver_rule_ids) != len(set(resolver_rule_ids)):
                raise ContractError("RPM resolver rule_id values must be unique within a resolver")
            if any(item.evidence_status is not EvidenceStatus.ASSERTED for item in resolver.facts):
                raise ContractError("RPM resolver facts must have asserted evidence_status")
            if any(not item.provenance for item in resolver.facts):
                raise ContractError("RPM resolver facts must carry provenance")
            if any(not rule.provenance for rule in resolver.rules):
                raise ContractError("RPM resolver rules must carry provenance")
        for proposition in (
            *self.facts,
            self.query,
            *(item for candidate in self.candidates for item in candidate.facts),
            *(item for candidate in self.candidates for item in candidate.assumptions),
            *(item for candidate in self.candidates for item in candidate.hard_constraints),
            *(resolver.target for resolver in self.rpm_resolvers),
            *(item for resolver in self.rpm_resolvers for item in resolver.facts),
        ):
            self._validate_ground_proposition(proposition, entity_map, predicate_map)
        for rule in (*self.rules, *(item for resolver in self.rpm_resolvers for item in resolver.rules)):
            variables_in_antecedents = {
                argument
                for antecedent in rule.antecedents
                for argument in antecedent.arguments
                if argument.startswith("?")
            }
            variables_in_consequent = {argument for argument in rule.consequent.arguments if argument.startswith("?")}
            if not variables_in_consequent <= variables_in_antecedents:
                raise ContractError(f"rule {rule.rule_id} is not range-restricted")
            variable_types: dict[str, str] = {}
            for proposition in (*rule.antecedents, rule.consequent):
                self._validate_pattern_proposition(proposition, entity_map, predicate_map)
                declaration = predicate_map[proposition.predicate]
                for term, expected_type in zip(proposition.arguments, declaration.argument_types, strict=True):
                    if term.startswith("?"):
                        prior = variable_types.setdefault(term, expected_type)
                        if prior != expected_type:
                            raise ContractError(f"variable {term} has inconsistent types in rule {rule.rule_id}")
            if rule.operation is InferenceOperation.INFER_TRANSITIVE:
                declaration = predicate_map.get(rule.consequent.predicate)
                predicates = {item.predicate for item in (*rule.antecedents, rule.consequent)}
                structural_match = False
                if len(rule.antecedents) == 2 and all(len(item.arguments) == 2 for item in (*rule.antecedents, rule.consequent)):
                    for first, second in (
                        (rule.antecedents[0], rule.antecedents[1]),
                        (rule.antecedents[1], rule.antecedents[0]),
                    ):
                        x, y = first.arguments
                        y_again, z = second.arguments
                        structural_match = structural_match or (
                            y == y_again
                            and rule.consequent.arguments == (x, z)
                            and len({x, y, z}) == 3
                            and all(item.startswith("?") for item in (x, y, z))
                        )
                if (
                    declaration is None
                    or not declaration.transitive
                    or len(predicates) != 1
                    or len(declaration.argument_types) != 2
                    or declaration.argument_types[0] != declaration.argument_types[1]
                    or not structural_match
                ):
                    raise ContractError("INFER_TRANSITIVE requires one explicitly transitive predicate")

    @staticmethod
    def _validate_ground_proposition(
        proposition: Proposition,
        entity_map: Mapping[str, str],
        predicate_map: Mapping[str, PredicateDecl],
    ) -> None:
        declaration = predicate_map.get(proposition.predicate)
        if declaration is None:
            raise ContractError(f"undeclared predicate: {proposition.predicate}")
        if len(proposition.arguments) != len(declaration.argument_types):
            raise ContractError(f"predicate arity mismatch: {proposition.predicate}")
        for entity_id, expected_type in zip(proposition.arguments, declaration.argument_types, strict=True):
            if entity_id.startswith("?"):
                raise ContractError("ground propositions cannot contain variables")
            if entity_map.get(entity_id) != expected_type:
                raise ContractError(f"entity type mismatch for {entity_id} in {proposition.predicate}")

    @staticmethod
    def _validate_pattern_proposition(
        proposition: Proposition,
        entity_map: Mapping[str, str],
        predicate_map: Mapping[str, PredicateDecl],
    ) -> None:
        declaration = predicate_map.get(proposition.predicate)
        if declaration is None:
            raise ContractError(f"undeclared predicate: {proposition.predicate}")
        if len(proposition.arguments) != len(declaration.argument_types):
            raise ContractError(f"predicate arity mismatch: {proposition.predicate}")
        for term, expected_type in zip(proposition.arguments, declaration.argument_types, strict=True):
            if term.startswith("?"):
                continue
            if entity_map.get(term) != expected_type:
                raise ContractError(f"entity type mismatch for {term} in {proposition.predicate}")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProblemPacket":
        _strict_keys(
            data,
            {
                "schema_version",
                "problem_id",
                "goal_id",
                "seed",
                "entities",
                "predicates",
                "facts",
                "rules",
                "query",
            },
            {"candidates", "rpm_resolvers", "foundation_ref", "budgets"},
            "ProblemPacket",
        )
        if any(not isinstance(data[key], list) for key in ("entities", "predicates", "facts", "rules")):
            raise ContractError("entities, predicates, facts, and rules must be lists")
        return cls(
            schema_version=str(data["schema_version"]),
            problem_id=_identifier(data["problem_id"], "problem_id"),
            goal_id=_identifier(data["goal_id"], "goal_id"),
            seed=data["seed"],
            entities=tuple(EntityDecl.from_dict(item) for item in data["entities"]),
            predicates=tuple(PredicateDecl.from_dict(item) for item in data["predicates"]),
            facts=tuple(Proposition.from_dict(item) for item in data["facts"]),
            rules=tuple(Rule.from_dict(item) for item in data["rules"]),
            query=Proposition.from_dict(data["query"]),
            candidates=tuple(CandidateSpec.from_dict(item) for item in data.get("candidates", [])),
            rpm_resolvers=tuple(ResolverSpec.from_dict(item) for item in data.get("rpm_resolvers", [])),
            foundation_ref=data.get("foundation_ref"),
            budgets=BudgetLimits.from_dict(data.get("budgets", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "problem_id": self.problem_id,
            "goal_id": self.goal_id,
            "seed": self.seed,
            "entities": [item.to_dict() for item in sorted(self.entities, key=lambda item: item.entity_id)],
            "predicates": [item.to_dict() for item in sorted(self.predicates, key=lambda item: item.predicate_id)],
            "facts": [item.to_dict() for item in sorted(self.facts, key=lambda item: item.key)],
            "rules": [item.to_dict() for item in sorted(self.rules, key=lambda item: item.rule_id)],
            "query": self.query.to_dict(),
            "candidates": [item.to_dict() for item in sorted(self.candidates, key=lambda item: item.candidate_id)],
            "rpm_resolvers": [
                item.to_dict() for item in sorted(self.rpm_resolvers, key=lambda item: item.target.key)
            ],
            "foundation_ref": self.foundation_ref,
            "budgets": self.budgets.to_dict(),
        }

    @property
    def input_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ProofStep:
    step_id: str
    operation: InferenceOperation
    premise_keys: tuple[str, ...]
    rule_id: str | None
    conclusion: Proposition
    substitution: tuple[tuple[str, str], ...]
    branch_id: str
    verified: bool
    provenance: tuple[Provenance, ...]

    @classmethod
    def create(
        cls,
        *,
        operation: InferenceOperation,
        premise_keys: Iterable[str],
        rule_id: str | None,
        conclusion: Proposition,
        substitution: Mapping[str, str],
        branch_id: str,
        verified: bool,
        provenance: Iterable[Provenance],
    ) -> "ProofStep":
        normalized_provenance = tuple(
            sorted(
                provenance,
                key=lambda item: (item.source_type, item.source_id, item.detail),
            )
        )
        body = {
            "operation": operation.value,
            "premise_keys": sorted(premise_keys),
            "rule_id": rule_id,
            "conclusion": conclusion.to_dict(),
            "substitution": sorted(substitution.items()),
            "branch_id": branch_id,
        }
        return cls(
            step_id=content_id("proof", body),
            operation=operation,
            premise_keys=tuple(sorted(premise_keys)),
            rule_id=rule_id,
            conclusion=conclusion,
            substitution=tuple(sorted(substitution.items())),
            branch_id=branch_id,
            verified=verified,
            provenance=normalized_provenance,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProofStep":
        _strict_keys(
            data,
            {
                "step_id",
                "operation",
                "premise_keys",
                "rule_id",
                "conclusion",
                "substitution",
                "branch_id",
                "verified",
                "provenance",
            },
            set(),
            "ProofStep",
        )
        rule_id = data["rule_id"]
        if rule_id is not None:
            rule_id = _identifier(rule_id, "ProofStep.rule_id")
        substitution_raw = data["substitution"]
        if (
            not isinstance(substitution_raw, list)
            or any(
                not isinstance(item, list)
                or len(item) != 2
                or not all(isinstance(value, str) for value in item)
                for item in substitution_raw
            )
        ):
            raise ContractError("ProofStep.substitution must be a list of string pairs")
        verified = data["verified"]
        if not isinstance(verified, bool):
            raise ContractError("ProofStep.verified must be boolean")
        provenance_raw = data["provenance"]
        if not isinstance(provenance_raw, list):
            raise ContractError("ProofStep.provenance must be a list")
        return cls(
            step_id=_identifier(data["step_id"], "ProofStep.step_id"),
            operation=InferenceOperation(data["operation"]),
            premise_keys=_string_list(data["premise_keys"], "ProofStep.premise_keys"),
            rule_id=rule_id,
            conclusion=Proposition.from_dict(data["conclusion"]),
            substitution=tuple((item[0], item[1]) for item in substitution_raw),
            branch_id=_identifier(data["branch_id"], "ProofStep.branch_id"),
            verified=verified,
            provenance=tuple(Provenance.from_dict(item) for item in provenance_raw),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class DecompositionRecord:
    candidate_id: str
    premises: tuple[str, ...]
    assumptions: tuple[str, ...]
    dependencies: tuple[str, ...]
    contradictions: tuple[str, ...]
    unknowns: tuple[str, ...]
    required_prerequisites: tuple[str, ...]
    predicted_effects: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DecompositionRecord":
        fields = {
            "candidate_id",
            "premises",
            "assumptions",
            "dependencies",
            "contradictions",
            "unknowns",
            "required_prerequisites",
            "predicted_effects",
        }
        _strict_keys(data, fields, set(), "DecompositionRecord")
        return cls(
            candidate_id=_identifier(data["candidate_id"], "DecompositionRecord.candidate_id"),
            premises=_string_list(data["premises"], "DecompositionRecord.premises"),
            assumptions=_string_list(data["assumptions"], "DecompositionRecord.assumptions"),
            dependencies=_string_list(data["dependencies"], "DecompositionRecord.dependencies"),
            contradictions=_string_list(data["contradictions"], "DecompositionRecord.contradictions"),
            unknowns=_string_list(data["unknowns"], "DecompositionRecord.unknowns"),
            required_prerequisites=_string_list(
                data["required_prerequisites"], "DecompositionRecord.required_prerequisites"
            ),
            predicted_effects=_string_list(
                data["predicted_effects"], "DecompositionRecord.predicted_effects"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class BranchFrame:
    branch_id: str
    parent_branch_id: str | None
    active_goal_id: str
    candidate_id: str
    assumptions: tuple[Proposition, ...]
    propositions: tuple[Proposition, ...]
    recalled_memory_ids: tuple[str, ...]
    proof_steps: tuple[ProofStep, ...]
    decompositions: tuple[DecompositionRecord, ...]
    hard_constraints: tuple[Proposition, ...]
    contradictions: tuple[str, ...]
    unknowns: tuple[str, ...]
    status: BranchStatus
    created_at_tick: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BranchFrame":
        fields = {
            "branch_id",
            "parent_branch_id",
            "active_goal_id",
            "candidate_id",
            "assumptions",
            "propositions",
            "recalled_memory_ids",
            "proof_steps",
            "decompositions",
            "hard_constraints",
            "contradictions",
            "unknowns",
            "status",
            "created_at_tick",
        }
        _strict_keys(data, fields, set(), "BranchFrame")
        for name in (
            "assumptions",
            "propositions",
            "recalled_memory_ids",
            "proof_steps",
            "decompositions",
            "hard_constraints",
            "contradictions",
            "unknowns",
        ):
            if not isinstance(data[name], list):
                raise ContractError(f"BranchFrame.{name} must be a list")
        parent_branch_id = data["parent_branch_id"]
        if parent_branch_id is not None:
            parent_branch_id = _identifier(parent_branch_id, "BranchFrame.parent_branch_id")
        return cls(
            branch_id=_identifier(data["branch_id"], "BranchFrame.branch_id"),
            parent_branch_id=parent_branch_id,
            active_goal_id=_identifier(data["active_goal_id"], "BranchFrame.active_goal_id"),
            candidate_id=_identifier(data["candidate_id"], "BranchFrame.candidate_id"),
            assumptions=tuple(Proposition.from_dict(item) for item in data["assumptions"]),
            propositions=tuple(Proposition.from_dict(item) for item in data["propositions"]),
            recalled_memory_ids=_string_list(
                data["recalled_memory_ids"], "BranchFrame.recalled_memory_ids"
            ),
            proof_steps=tuple(ProofStep.from_dict(item) for item in data["proof_steps"]),
            decompositions=tuple(
                DecompositionRecord.from_dict(item) for item in data["decompositions"]
            ),
            hard_constraints=tuple(
                Proposition.from_dict(item) for item in data["hard_constraints"]
            ),
            contradictions=_string_list(data["contradictions"], "BranchFrame.contradictions"),
            unknowns=_string_list(data["unknowns"], "BranchFrame.unknowns"),
            status=BranchStatus(data["status"]),
            created_at_tick=_strict_integer(
                data["created_at_tick"], "BranchFrame.created_at_tick", minimum=0
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    def proposition_map(self) -> dict[str, Proposition]:
        return {item.key: item for item in self.propositions}


@dataclass(frozen=True, slots=True)
class RPMFrame:
    frame_id: str
    goal_id: str
    parent_goal_id: str
    branch_id: str
    target_foundation: str | None
    blocked_prerequisite: str
    return_address: str
    resume_stage: str
    expected_result_key: str
    depth: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RPMFrame":
        fields = {
            "frame_id",
            "goal_id",
            "parent_goal_id",
            "branch_id",
            "target_foundation",
            "blocked_prerequisite",
            "return_address",
            "resume_stage",
            "expected_result_key",
            "depth",
        }
        _strict_keys(data, fields, set(), "RPMFrame")
        target_foundation = data["target_foundation"]
        if target_foundation is not None and target_foundation not in FOUNDATION_REFERENCES:
            raise ContractError("RPMFrame.target_foundation must be an opaque Foundation reference or null")
        return cls(
            frame_id=_identifier(data["frame_id"], "RPMFrame.frame_id"),
            goal_id=_identifier(data["goal_id"], "RPMFrame.goal_id"),
            parent_goal_id=_identifier(data["parent_goal_id"], "RPMFrame.parent_goal_id"),
            branch_id=_identifier(data["branch_id"], "RPMFrame.branch_id"),
            target_foundation=target_foundation,
            blocked_prerequisite=_nonempty_string(
                data["blocked_prerequisite"], "RPMFrame.blocked_prerequisite"
            ),
            return_address=_nonempty_string(data["return_address"], "RPMFrame.return_address"),
            resume_stage=_identifier(data["resume_stage"], "RPMFrame.resume_stage"),
            expected_result_key=_nonempty_string(
                data["expected_result_key"], "RPMFrame.expected_result_key"
            ),
            depth=_strict_integer(data["depth"], "RPMFrame.depth", minimum=1),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    report_id: str
    evaluation_frame_hash: str
    ordered_branch_ids: tuple[str, ...]
    metrics: tuple[tuple[str, tuple[int, ...]], ...]
    shared_features: tuple[str, ...]
    differences: tuple[str, ...]
    winner_branch_id: str | None
    single_candidate_reason: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ComparisonReport":
        fields = {
            "report_id",
            "evaluation_frame_hash",
            "ordered_branch_ids",
            "metrics",
            "shared_features",
            "differences",
            "winner_branch_id",
            "single_candidate_reason",
        }
        _strict_keys(data, fields, set(), "ComparisonReport")
        metrics_raw = data["metrics"]
        if (
            not isinstance(metrics_raw, list)
            or any(
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], list)
                or any(not isinstance(value, int) or isinstance(value, bool) for value in item[1])
                for item in metrics_raw
            )
        ):
            raise ContractError("ComparisonReport.metrics must be branch/integer-list pairs")
        winner = data["winner_branch_id"]
        if winner is not None and not isinstance(winner, str):
            raise ContractError("ComparisonReport.winner_branch_id must be a string or null")
        reason = data["single_candidate_reason"]
        if reason is not None and not isinstance(reason, str):
            raise ContractError("ComparisonReport.single_candidate_reason must be a string or null")
        frame_hash = data["evaluation_frame_hash"]
        if not isinstance(frame_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", frame_hash):
            raise ContractError("ComparisonReport.evaluation_frame_hash must be a lowercase SHA-256")
        return cls(
            report_id=_identifier(data["report_id"], "ComparisonReport.report_id"),
            evaluation_frame_hash=frame_hash,
            ordered_branch_ids=_string_list(
                data["ordered_branch_ids"], "ComparisonReport.ordered_branch_ids"
            ),
            metrics=tuple((item[0], tuple(item[1])) for item in metrics_raw),
            shared_features=_string_list(
                data["shared_features"], "ComparisonReport.shared_features"
            ),
            differences=_string_list(data["differences"], "ComparisonReport.differences"),
            winner_branch_id=winner,
            single_candidate_reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class EpisodicRecord:
    episode_id: str
    problem_id: str
    goal_id: str
    conclusion: Proposition
    branch_id: str
    proof_digest: str
    trace_head: str
    final_state_hash: str
    verified: bool

    def __post_init__(self) -> None:
        _identifier(self.episode_id, "EpisodicRecord.episode_id")
        _identifier(self.problem_id, "EpisodicRecord.problem_id")
        _identifier(self.goal_id, "EpisodicRecord.goal_id")
        _identifier(self.branch_id, "EpisodicRecord.branch_id")
        if not isinstance(self.conclusion, Proposition):
            raise ContractError("EpisodicRecord.conclusion must be a Proposition")
        for name in ("proof_digest", "trace_head", "final_state_hash"):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ContractError(f"EpisodicRecord.{name} must be a lowercase SHA-256")
        if not isinstance(self.verified, bool):
            raise ContractError("EpisodicRecord.verified must be boolean")
        expected_id = content_id(
            "episode",
            {
                "problem_id": self.problem_id,
                "goal_id": self.goal_id,
                "conclusion": self.conclusion.to_dict(),
                "branch_id": self.branch_id,
                "proof_digest": self.proof_digest,
                "trace_head": self.trace_head,
                "final_state_hash": self.final_state_hash,
            },
        )
        if self.episode_id != expected_id:
            raise ContractError("EpisodicRecord.episode_id is not content-derived")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EpisodicRecord":
        fields = {
            "episode_id",
            "problem_id",
            "goal_id",
            "conclusion",
            "branch_id",
            "proof_digest",
            "trace_head",
            "final_state_hash",
            "verified",
        }
        _strict_keys(data, fields, set(), "EpisodicRecord")
        for name in ("proof_digest", "trace_head", "final_state_hash"):
            value = data[name]
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ContractError(f"EpisodicRecord.{name} must be a lowercase SHA-256")
        if not isinstance(data["verified"], bool):
            raise ContractError("EpisodicRecord.verified must be boolean")
        return cls(
            episode_id=_identifier(data["episode_id"], "EpisodicRecord.episode_id"),
            problem_id=_identifier(data["problem_id"], "EpisodicRecord.problem_id"),
            goal_id=_identifier(data["goal_id"], "EpisodicRecord.goal_id"),
            conclusion=Proposition.from_dict(data["conclusion"]),
            branch_id=_identifier(data["branch_id"], "EpisodicRecord.branch_id"),
            proof_digest=data["proof_digest"],
            trace_head=data["trace_head"],
            final_state_hash=data["final_state_hash"],
            verified=data["verified"],
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class CommitmentState:
    decision_status: str = "UNCOMMITTED"
    selected_branch_id: str | None = None
    conclusion: Proposition | None = None
    gate_results: tuple[tuple[str, bool], ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CommitmentState":
        conclusion = data.get("conclusion")
        return cls(
            decision_status=str(data.get("decision_status", "UNCOMMITTED")),
            selected_branch_id=data.get("selected_branch_id"),
            conclusion=Proposition.from_dict(conclusion) if conclusion else None,
            gate_results=tuple((str(k), bool(v)) for k, v in data.get("gate_results", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class GlobalWorkspace:
    problem_id: str
    query: Proposition
    recalled_memory_ids: tuple[str, ...] = ()
    comparison_reports: tuple[ComparisonReport, ...] = ()
    conclusion: Proposition | None = None
    lacunae: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GlobalWorkspace":
        conclusion = data.get("conclusion")
        return cls(
            problem_id=str(data["problem_id"]),
            query=Proposition.from_dict(data["query"]),
            recalled_memory_ids=tuple(data.get("recalled_memory_ids", [])),
            comparison_reports=tuple(ComparisonReport.from_dict(item) for item in data.get("comparison_reports", [])),
            conclusion=Proposition.from_dict(conclusion) if conclusion else None,
            lacunae=tuple(data.get("lacunae", [])),
            diagnostics=tuple(data.get("diagnostics", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class BudgetState:
    ticks_remaining: int
    branches_remaining: int
    rpm_depth_limit: int
    inference_steps_remaining: int
    memory_queries_remaining: int

    @classmethod
    def from_limits(cls, limits: BudgetLimits) -> "BudgetState":
        return cls(
            ticks_remaining=limits.max_ticks,
            branches_remaining=limits.max_branches,
            rpm_depth_limit=limits.max_rpm_depth,
            inference_steps_remaining=limits.max_inference_steps,
            memory_queries_remaining=limits.max_memory_queries,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BudgetState":
        return cls(**{key: int(value) for key, value in data.items()})

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class MachineState:
    runtime_version: str
    logical_tick: int
    run_id: str
    seed: int
    constitution_revision: str
    foundation_state: tuple[tuple[str, str], ...]
    drive_state: tuple[tuple[str, str], ...]
    domain_power_state: tuple[tuple[str, str], ...]
    global_workspace: GlobalWorkspace
    working_memory: tuple[Proposition, ...]
    episodic_memory: tuple[EpisodicRecord, ...]
    episodic_memory_revision: int
    active_goal_id: str
    rpm_stack: tuple[RPMFrame, ...]
    branch_table: tuple[BranchFrame, ...]
    pending_intents: tuple[str, ...]
    commitment_state: CommitmentState
    learning_queue: tuple[str, ...]
    halt_status: TerminalStatus
    trace_head: str
    state_hash: str
    budget: BudgetState

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    def hash_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("state_hash", None)
        payload.pop("trace_head", None)
        return payload

    def computed_hash(self) -> str:
        return digest(self.hash_payload())

    def with_computed_hash(self) -> "MachineState":
        return replace(self, state_hash=self.computed_hash())

    def branch_map(self) -> dict[str, BranchFrame]:
        return {branch.branch_id: branch for branch in self.branch_table}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MachineState":
        return cls(
            runtime_version=str(data["runtime_version"]),
            logical_tick=int(data["logical_tick"]),
            run_id=str(data["run_id"]),
            seed=int(data["seed"]),
            constitution_revision=str(data["constitution_revision"]),
            foundation_state=tuple((str(k), str(v)) for k, v in data["foundation_state"]),
            drive_state=tuple((str(k), str(v)) for k, v in data["drive_state"]),
            domain_power_state=tuple((str(k), str(v)) for k, v in data["domain_power_state"]),
            global_workspace=GlobalWorkspace.from_dict(data["global_workspace"]),
            working_memory=tuple(Proposition.from_dict(item) for item in data["working_memory"]),
            episodic_memory=tuple(EpisodicRecord.from_dict(item) for item in data["episodic_memory"]),
            episodic_memory_revision=int(data["episodic_memory_revision"]),
            active_goal_id=str(data["active_goal_id"]),
            rpm_stack=tuple(RPMFrame.from_dict(item) for item in data["rpm_stack"]),
            branch_table=tuple(BranchFrame.from_dict(item) for item in data["branch_table"]),
            pending_intents=tuple(data["pending_intents"]),
            commitment_state=CommitmentState.from_dict(data["commitment_state"]),
            learning_queue=tuple(data["learning_queue"]),
            halt_status=TerminalStatus(data["halt_status"]),
            trace_head=str(data["trace_head"]),
            state_hash=str(data["state_hash"]),
            budget=BudgetState.from_dict(data["budget"]),
        )


@dataclass(frozen=True, slots=True)
class Intent:
    intent_id: str
    intent_type: IntentType
    issuer_subsystem: str
    required_capability: str
    target_scope: str
    branch_id: str | None
    goal_id: str | None
    precondition: tuple[tuple[str, Any], ...]
    proposed_mutation: tuple[tuple[str, Any], ...]
    created_at_tick: int
    provenance: tuple[Provenance, ...]

    @classmethod
    def create(
        cls,
        *,
        intent_type: IntentType,
        issuer_subsystem: str,
        required_capability: str,
        target_scope: str,
        branch_id: str | None,
        goal_id: str | None,
        precondition: Mapping[str, Any],
        proposed_mutation: Mapping[str, Any],
        created_at_tick: int,
        provenance: Iterable[Provenance] = (),
    ) -> "Intent":
        normalized_provenance = tuple(
            sorted(
                provenance,
                key=lambda item: (item.source_type, item.source_id, item.detail),
            )
        )
        body = {
            "intent_type": intent_type.value,
            "issuer_subsystem": issuer_subsystem,
            "required_capability": required_capability,
            "target_scope": target_scope,
            "branch_id": branch_id,
            "goal_id": goal_id,
            "precondition": precondition,
            "proposed_mutation": proposed_mutation,
            "created_at_tick": created_at_tick,
            "provenance": [item.to_dict() for item in normalized_provenance],
        }
        return cls(
            intent_id=content_id("intent", body),
            intent_type=intent_type,
            issuer_subsystem=issuer_subsystem,
            required_capability=required_capability,
            target_scope=target_scope,
            branch_id=branch_id,
            goal_id=goal_id,
            precondition=tuple(
                (str(key), _freeze_json(value)) for key, value in sorted(precondition.items())
            ),
            proposed_mutation=tuple(
                (str(key), _freeze_json(value)) for key, value in sorted(proposed_mutation.items())
            ),
            created_at_tick=created_at_tick,
            provenance=normalized_provenance,
        )

    def precondition_dict(self) -> dict[str, Any]:
        return {key: _thaw_json(value) for key, value in self.precondition}

    def mutation_dict(self) -> dict[str, Any]:
        return {key: _thaw_json(value) for key, value in self.proposed_mutation}

    def immutable_copy(self) -> "Intent":
        return replace(
            self,
            precondition=tuple((key, _freeze_json(value)) for key, value in self.precondition),
            proposed_mutation=tuple(
                (key, _freeze_json(value)) for key, value in self.proposed_mutation
            ),
            provenance=tuple(self.provenance),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type.value,
            "issuer_subsystem": self.issuer_subsystem,
            "required_capability": self.required_capability,
            "target_scope": self.target_scope,
            "branch_id": self.branch_id,
            "goal_id": self.goal_id,
            "precondition": to_primitive(dict(self.precondition)),
            "proposed_mutation": to_primitive(dict(self.proposed_mutation)),
            "created_at_tick": self.created_at_tick,
            "provenance": [item.to_dict() for item in self.provenance],
        }


@dataclass(frozen=True, slots=True)
class RejectedIntent:
    intent_id: str
    reason: RejectionReason
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class TraceEvent:
    event_id: str
    parent_event_id: str | None
    logical_tick: int
    run_id: str
    runtime_version: str
    pre_state_hash: str
    enabled_components: tuple[str, ...]
    scheduled_components: tuple[str, ...]
    proposed_intents: tuple[Intent, ...]
    authorized_intent_ids: tuple[str, ...]
    rejected_intents: tuple[RejectedIntent, ...]
    committed_mutations: tuple[str, ...]
    post_state_hash: str
    terminal_status: TerminalStatus
    previous_event_hash: str
    event_hash: str
    sealed: bool

    def hash_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("event_hash", None)
        return payload

    def computed_hash(self) -> str:
        return digest(self.hash_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "parent_event_id": self.parent_event_id,
            "logical_tick": self.logical_tick,
            "run_id": self.run_id,
            "runtime_version": self.runtime_version,
            "pre_state_hash": self.pre_state_hash,
            "enabled_components": list(self.enabled_components),
            "scheduled_components": list(self.scheduled_components),
            "proposed_intents": [item.to_dict() for item in self.proposed_intents],
            "authorized_intent_ids": list(self.authorized_intent_ids),
            "rejected_intents": [item.to_dict() for item in self.rejected_intents],
            "committed_mutations": list(self.committed_mutations),
            "post_state_hash": self.post_state_hash,
            "terminal_status": self.terminal_status.value,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash,
            "sealed": self.sealed,
        }
