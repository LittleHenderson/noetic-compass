"""Closed v0.3 equation-dependency records; parsing grants no execution authority.

The supplied equations describe a finite dependency problem, never a caller's
execution plan. Missing references and cycles remain representable so the live
coordinator can diagnose them. Only replayed coordinator transitions establish
the authority of retained calls, procedure installations and checked results.
Versions 0.1 and 0.2 are imported as immutable contracts and are not widened.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import json

from .canonical import canonical_json, digest, to_primitive
from .model import (BranchFrame, BudgetLimits, BudgetState, CommitmentState,
    ContractError, EntityDecl, EpisodicRecord, EvidenceStatus, GlobalWorkspace,
    InferenceOperation, MachineState, PredicateDecl, ProblemPacket, ProofStep,
    Proposition, RPMFrame, TerminalStatus)
from .native_model import (NativeBudget, _counter, _identifier, _keys, _legacy,
    _list, _rational, _require, _sha, _typed)
from .procedural_substrate import CAPABILITY_CONTRACT, ProcedureArtifact

NESTED_RUNTIME_VERSION = "0.3.0"
NESTED_CONSTITUTION_REVISION = "cncm-constitution/nested-0.3"
NESTED_PROBLEM_SCHEMA = "cncm.nested-problem/0.3"
NESTED_EQUATION_SCHEMA = "cncm.nested-equation/0.3"
NESTED_CALL_SCHEMA = "cncm.nested-call/0.3"
NESTED_FRAME_SCHEMA = "cncm.nested-frame/0.3"
NESTED_RECORD_SCHEMA = "cncm.nested-record/0.3"
NESTED_PROOF_SCHEMA = "cncm.nested-proof/0.3"
NESTED_STATE_SCHEMA = "cncm.nested-state/0.3"
RESULT_PREDICATE = "nested_checked"
CAPABILITY = "cncm.solve-linear/0.1"
OUTPUT_CONTRACT = "cncm.checked-linear-solution/0.1"
MAX_EQUATIONS = 16
MAX_TERMS = 4
MAX_CALLS = 16
MAX_ARTIFACTS = 8
MAX_RECORDS = 512
MAX_RECORD_BYTES = 262144
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_PROBLEM_BYTES = 1024 * 1024
MAX_DEPTH = 8
NESTED_RECORD_KINDS = frozenset({"DECOMPOSITION", "BINDING", "SELECTION",
    "QUALIFICATION", "INSTALLATION", "EXECUTION", "FAILURE",
    "WORK_RESERVATION", "ROLLBACK", "RETURN"})


class NestedIntentType(str, Enum):
    REQUEST_EQUATION = "REQUEST_EQUATION"
    DECOMPOSE_EQUATION = "DECOMPOSE_EQUATION"
    PUSH_DEPENDENCY = "PUSH_DEPENDENCY"
    RETURN_DEPENDENCY = "RETURN_DEPENDENCY"
    BIND_EQUATION = "BIND_EQUATION"
    PUSH_PROCEDURE = "PUSH_PROCEDURE"
    SELECT_PROCEDURE = "SELECT_PROCEDURE"
    INSTALL_PROCEDURE = "INSTALL_PROCEDURE"
    RETURN_PROCEDURE = "RETURN_PROCEDURE"
    APPLY_EQUATION = "APPLY_EQUATION"
    FAIL_CALL = "FAIL_CALL"
    ROLLBACK_PROCEDURE = "ROLLBACK_PROCEDURE"


class NestedInferenceOperation(str, Enum):
    CHECKED_NESTED_EQUATION = "CHECKED_NESTED_EQUATION"


def _wire(value):
    """Bound JSON, including legitimate exact-math receipt integer payloads.

    This is a structural ceiling, not a counter or arithmetic input contract.
    Typed counters retain their smaller explicit bounds; procedure inputs remain
    canonical rational strings with 128-bit parts. Frozen v0.2 is unchanged.
    """
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(count <= 100000 and depth <= 40, "nested JSON structure bound exceeded")
        if type(item) is dict:
            _require(len(item) <= 4096 and all(type(key) is str for key in item), "nested JSON object invalid")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            _require(len(item) <= 4096, "nested JSON list bound exceeded")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _require(len(item) <= MAX_RECORD_BYTES, "nested JSON string bound exceeded")
        elif type(item) is int:
            _require(item.bit_length() <= 512, "nested JSON integer bound exceeded")
        else:
            _require(item is None or type(item) is bool, "nested JSON primitive invalid")


def _decode(value, kind, schema):
    _keys(value, {field.name for field in fields(kind)} | {"schema_version"}, kind.__name__)
    _wire(value)
    _require(type(value["schema_version"]) is str and value["schema_version"] == schema,
             kind.__name__ + " version invalid")
    return {key: item for key, item in value.items() if key != "schema_version"}


def _bounded_json(value, maximum, label):
    """Bound total text before allocating the complete canonical JSON string."""
    _wire(value)
    pending, text_size = [value], 0
    while pending:
        item = pending.pop()
        if type(item) is str:
            text_size += len(item)
        elif type(item) is dict:
            text_size += sum(len(key) for key in item)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        _require(text_size <= maximum, label + " aggregate text bound exceeded")
    encoded = canonical_json(value)
    _require(len(encoded.encode()) <= maximum, label + " byte bound exceeded")
    return encoded


def _pairs(value, label, maximum):
    _list(value, label, maximum)
    _require(all(type(row) is list and len(row) == 2 for row in value), label + " pairs invalid")
    return tuple(tuple(row) for row in value)


def _ids(value, label, maximum):
    _require(type(value) is tuple and len(value) <= maximum, label + " tuple bound/type invalid")
    for item in value:
        _identifier(item, label)
    _require(value == tuple(sorted(set(value))), label + " must be sorted and unique")


@dataclass(frozen=True, slots=True)
class Equation:
    variable: str
    a: str
    b: str
    rhs_constant: str = "0"
    rhs_terms: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _typed(self, Equation)
        _identifier(self.variable, "equation variable")
        for value in (self.a, self.b, self.rhs_constant):
            _rational(value)
        _require(len(self.rhs_terms) <= MAX_TERMS, "equation term bound exceeded")
        _ids(tuple(variable for variable, _ in self.rhs_terms), "equation dependencies", MAX_TERMS)
        for _, coefficient in self.rhs_terms:
            _rational(coefficient)
            _require(coefficient != "0", "zero dependency coefficient is not canonical")

    @property
    def dependencies(self):
        return tuple(variable for variable, _ in self.rhs_terms)

    def to_dict(self):
        return {"schema_version": NESTED_EQUATION_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, NESTED_EQUATION_SCHEMA)
        body["rhs_terms"] = _pairs(body["rhs_terms"], "equation terms", MAX_TERMS)
        return cls(**body)


@dataclass(frozen=True, slots=True)
class NestedProblem:
    reasoning: ProblemPacket
    query_variable: str
    equations: tuple[Equation, ...]
    budget: NativeBudget = NativeBudget()

    def __post_init__(self):
        _typed(self, NestedProblem)
        _identifier(self.query_variable, "query variable")
        _require(len(self.equations) <= MAX_EQUATIONS, "equation count bound exceeded")
        _require(len({row.variable for row in self.equations}) == len(self.equations),
                 "duplicate equation producer")
        _legacy(self.reasoning.to_dict(), ProblemPacket)
        _require(not self.reasoning.candidates and not self.reasoning.rpm_resolvers,
                 "nested problems forbid supplied candidates and RPM resolvers")
        _require(all(item.predicate != RESULT_PREDICATE for item in self.reasoning.facts)
                 and all(rule.consequent.predicate != RESULT_PREDICATE for rule in self.reasoning.rules),
                 "nested_checked is reserved for coordinator checked results")
        query = self.reasoning.query
        _require(query.predicate == RESULT_PREDICATE and query.arguments == (self.query_variable,)
                 and query.polarity is True, "nested query must bind the queried variable")
        entities = {item.entity_id: item.entity_type for item in self.reasoning.entities}
        declaration = next((item for item in self.reasoning.predicates
                            if item.predicate_id == RESULT_PREDICATE), None)
        _require(self.query_variable in entities and declaration is not None
                 and declaration.argument_types == (entities[self.query_variable],)
                 and not declaration.transitive, "nested result declaration invalid")
        variables = {self.query_variable} | {row.variable for row in self.equations}
        variables.update(variable for row in self.equations for variable in row.dependencies)
        _require(all(entities.get(variable) == entities[self.query_variable] for variable in variables),
                 "equation variable/reference entity missing or differently typed")
        _counter(self.reasoning.budgets.max_ticks, "nested max ticks", 1024)
        _require(1 <= self.reasoning.budgets.max_rpm_depth <= MAX_DEPTH, "nested RPM depth invalid")
        _bounded_json(self.to_dict(), MAX_PROBLEM_BYTES, "nested problem")

    def equation_map(self):
        return {row.variable: row for row in self.equations}

    @property
    def input_hash(self):
        return digest(self.to_dict())

    @property
    def result_key(self):
        return self.reasoning.query.key

    def to_dict(self):
        return {"schema_version": NESTED_PROBLEM_SCHEMA, "reasoning": self.reasoning.to_dict(),
                "query_variable": self.query_variable,
                "equations": [row.to_dict() for row in sorted(self.equations, key=lambda row: row.variable)],
                "budget": self.budget.to_dict()}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, NESTED_PROBLEM_SCHEMA)
        _bounded_json(value, MAX_PROBLEM_BYTES, "nested problem")
        _list(body["equations"], "equations", MAX_EQUATIONS)
        return cls(_legacy(body["reasoning"], ProblemPacket), body["query_variable"],
                   tuple(Equation.from_dict(row) for row in body["equations"]),
                   NativeBudget.from_dict(body["budget"]))


def create_problem(equations, query_variable, problem_id="nested-equations", goal_id="goal-nested",
                   budget=NativeBudget(), max_ticks=128, rpm_depth_limit=8):
    _require(type(equations) is tuple and len(equations) <= MAX_EQUATIONS
             and all(type(row) is Equation for row in equations), "typed equation tuple required")
    _identifier(query_variable, "query variable")
    _counter(max_ticks, "max ticks", 1024)
    _counter(rpm_depth_limit, "RPM depth", MAX_DEPTH)
    variables = {query_variable} | {row.variable for row in equations}
    variables.update(variable for row in equations for variable in row.dependencies)
    reasoning = ProblemPacket(schema_version="cncm.problem/0.1", problem_id=problem_id,
        goal_id=goal_id, seed=0, entities=tuple(EntityDecl(name, "variable") for name in sorted(variables)),
        predicates=(PredicateDecl(RESULT_PREDICATE, ("variable",)),), facts=(), rules=(),
        query=Proposition(RESULT_PREDICATE, (query_variable,)),
        budgets=BudgetLimits(max_ticks=max_ticks, max_rpm_depth=rpm_depth_limit))
    return NestedProblem(reasoning, query_variable, equations, budget)


@dataclass(frozen=True, slots=True)
class GraphCall:
    call_id: str
    goal_id: str
    variable: str
    status: str = "NEW"
    planned_dependencies: tuple[str, ...] = ()
    dependency_records: tuple[tuple[str, str], ...] = ()
    inputs: tuple[tuple[str, str], ...] = ()
    artifact_sha256: str | None = None
    execution_digest: str | None = None
    output: str | None = None
    failure: str | None = None

    def __post_init__(self):
        _typed(self, GraphCall)
        for name in ("call_id", "goal_id", "variable"):
            _identifier(getattr(self, name), name)
        _require(self.status in {"NEW", "OPEN", "WAITING_DEPENDENCY", "WAITING_PROCEDURE",
                 "BOUND", "READY", "COMPLETE", "FAILED"}, "graph call status invalid")
        _ids(self.planned_dependencies, "planned dependencies", MAX_TERMS)
        keys = tuple(key for key, _ in self.dependency_records)
        _ids(keys, "dependency records", MAX_TERMS)
        _require(set(keys) <= set(self.planned_dependencies), "record for unplanned dependency")
        for _, value in self.dependency_records:
            _sha(value, "dependency execution")
        _sha(self.artifact_sha256, "call artifact", optional=True)
        _sha(self.execution_digest, "call execution", optional=True)
        bound = self.status in {"BOUND", "READY", "WAITING_PROCEDURE", "COMPLETE"}
        if bound or self.inputs:
            _require(tuple(key for key, _ in self.inputs) == ("a", "b", "c"), "bound call inputs must be exact a/b/c")
            for _, value in self.inputs:
                _rational(value)
            _require(keys == self.planned_dependencies, "bound call has unresolved dependency records")
        if self.status in {"NEW", "OPEN", "WAITING_DEPENDENCY"}:
            _require(not self.inputs and self.artifact_sha256 is None, "unbound call cannot pin inputs or artifact")
        if self.status == "NEW":
            _require(not self.planned_dependencies and not self.dependency_records, "new call cannot contain a plan")
        if self.status == "WAITING_DEPENDENCY":
            _require(bool(self.planned_dependencies) and keys != self.planned_dependencies,
                     "dependency wait requires unresolved planned input")
        if self.status in {"READY", "COMPLETE"}:
            _require(self.artifact_sha256 is not None, "ready call needs a pinned artifact")
        if self.status == "COMPLETE":
            _require(self.output is not None and self.execution_digest is not None,
                     "complete call needs checked execution and output")
            _rational(self.output, 512)
        else:
            _require(self.output is None and self.execution_digest is None,
                     "incomplete call cannot carry an answer or execution digest")
        if self.status == "FAILED":
            _identifier(self.failure, "call failure")
        else:
            _require(self.failure is None, "nonfailed call cannot carry failure")

    def inputs_dict(self):
        return dict(self.inputs)

    @property
    def inputs_digest(self):
        return digest({"input_contract": CAPABILITY_CONTRACT, "inputs": self.inputs_dict()})

    @property
    def call_digest(self):
        return digest(self.to_dict())

    def to_dict(self):
        return {"schema_version": NESTED_CALL_SCHEMA, **to_primitive(self), "inputs": self.inputs_dict()}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, NESTED_CALL_SCHEMA)
        _list(body["planned_dependencies"], "planned dependencies", MAX_TERMS)
        body["planned_dependencies"] = tuple(body["planned_dependencies"])
        body["dependency_records"] = _pairs(body["dependency_records"], "dependency records", MAX_TERMS)
        _require(type(body["inputs"]) is dict and set(body["inputs"]) in (set(), {"a", "b", "c"}),
                 "graph input fields invalid")
        body["inputs"] = tuple(sorted(body["inputs"].items()))
        return cls(**body)


@dataclass(frozen=True, slots=True)
class NestedFrame(RPMFrame):
    kind: str
    call_id: str
    child_call_id: str | None
    dependency_variable: str | None
    parent_call_digest: str
    parent_branch_digest: str
    entry_instruction_budget: int
    entry_checker_budget: int

    def __post_init__(self):
        _typed(self, NestedFrame)
        for name in ("frame_id", "goal_id", "parent_goal_id", "call_id"):
            _identifier(getattr(self, name), name)
        _require(self.kind in {"DEPENDENCY", "PROCEDURE_ACQUISITION"}, "nested frame kind invalid")
        _require(self.branch_id == "branch-main" and self.target_foundation is None
                 and self.parent_goal_id != self.goal_id and 1 <= self.depth <= MAX_DEPTH,
                 "nested frame branch/goal/depth invalid")
        _sha(self.parent_call_digest, "suspended parent call")
        _sha(self.parent_branch_digest, "suspended parent branch")
        NativeBudget(self.entry_instruction_budget, self.entry_checker_budget)
        if self.kind == "DEPENDENCY":
            _identifier(self.child_call_id, "dependency child call")
            _identifier(self.dependency_variable, "dependency variable")
            _require(self.child_call_id != self.call_id, "dependency child cannot be parent call")
            expected_return, expected_stage = f"call:{self.call_id}:dependencies", "DEPENDENCY_BIND"
        else:
            _require(self.child_call_id is None and self.dependency_variable is None,
                     "procedure frame cannot impersonate dependency child")
            expected_return, expected_stage = f"call:{self.call_id}:procedure", "PROCEDURE_APPLY"
        _require(self.return_address == expected_return and self.resume_stage == expected_stage,
                 "nested frame return/resume mismatch")
        for value in (self.blocked_prerequisite, self.expected_result_key):
            _require(type(value) is str and 1 <= len(value) <= 512, "nested frame scope text invalid")
        _legacy({field.name: getattr(self, field.name) for field in fields(RPMFrame)}, RPMFrame)

    def to_dict(self):
        return {"schema_version": NESTED_FRAME_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, NESTED_FRAME_SCHEMA))


@dataclass(frozen=True, slots=True)
class NestedRecord:
    kind: str
    body_json: str
    record_digest: str

    def __post_init__(self):
        _require(type(self.kind) is str and self.kind in NESTED_RECORD_KINDS, "unknown nested record kind")
        _require(type(self.body_json) is str and len(self.body_json) <= MAX_RECORD_BYTES,
                 "nested record character bound exceeded")
        _require(len(self.body_json.encode()) <= MAX_RECORD_BYTES, "nested record byte bound exceeded")
        try:
            body = json.loads(self.body_json)
        except (ValueError, RecursionError) as exc:
            raise ContractError("nested record JSON invalid") from exc
        _require(type(body) is dict, "nested record must contain an object")
        _wire(body)
        _require(canonical_json(body) == self.body_json, "nested record JSON is not canonical")
        _sha(self.record_digest, "nested record")
        _require(self.record_digest == digest(self._body(body)), "nested record digest mismatch")

    def _body(self, body):
        return {"schema_version": NESTED_RECORD_SCHEMA, "kind": self.kind, "body": body}

    @classmethod
    def create(cls, kind, body):
        _require(type(body) is dict, "nested record must contain an object")
        encoded = _bounded_json(body, MAX_RECORD_BYTES, "nested record")
        return cls(kind, encoded, digest({"schema_version": NESTED_RECORD_SCHEMA,
                                                     "kind": kind, "body": body}))

    def body_dict(self):
        return json.loads(self.body_json)

    def to_dict(self):
        return {"schema_version": NESTED_RECORD_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, NESTED_RECORD_SCHEMA))


@dataclass(frozen=True, slots=True)
class NestedProofStep(ProofStep):
    operation: NestedInferenceOperation
    execution_digest: str

    def __post_init__(self):
        _typed(self, NestedProofStep)
        _require(self.operation is NestedInferenceOperation.CHECKED_NESTED_EQUATION,
                 "nested proof operation invalid")
        _identifier(self.branch_id, "nested proof branch")
        _sha(self.execution_digest, "nested proof execution")
        _require(self.rule_id is None and not self.substitution and not self.premise_keys
                 and self.verified is True, "nested checked proof shape invalid")
        _require(self.conclusion.predicate == RESULT_PREDICATE and len(self.conclusion.arguments) == 1
                 and self.conclusion.polarity is True and self.conclusion.evidence_status is EvidenceStatus.DERIVED,
                 "nested checked conclusion invalid")
        _legacy(self.conclusion.to_dict(), Proposition)
        _require(self.provenance == tuple(sorted(self.provenance,
                 key=lambda item: (item.source_type, item.source_id, item.detail))), "nested proof provenance not canonical")
        _require(self.step_id == "nested-proof-" + digest(self._body()), "nested proof digest mismatch")

    def _body(self):
        body = to_primitive(self)
        body.pop("step_id")
        return {"schema_version": NESTED_PROOF_SCHEMA, **body}

    def to_dict(self):
        return {"step_id": self.step_id, **self._body()}

    @classmethod
    def create_checked(cls, *, conclusion, branch_id, execution_digest, provenance=()):
        body = {"schema_version": NESTED_PROOF_SCHEMA,
            "operation": NestedInferenceOperation.CHECKED_NESTED_EQUATION.value,
            "premise_keys": [], "rule_id": None, "conclusion": conclusion.to_dict(),
            "substitution": [], "branch_id": branch_id, "verified": True,
            "provenance": [item.to_dict() for item in sorted(provenance,
                key=lambda item: (item.source_type, item.source_id, item.detail))],
            "execution_digest": execution_digest}
        return cls.from_dict({"step_id": "nested-proof-" + digest(body), **body})

    create = create_checked

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, NESTED_PROOF_SCHEMA)
        _require(body["operation"] == NestedInferenceOperation.CHECKED_NESTED_EQUATION.value,
                 "nested proof operation invalid")
        base = {field.name: body[field.name] for field in fields(ProofStep)}
        base["operation"] = InferenceOperation.RPM_CHILD_RESULT.value
        decoded = _legacy(base, ProofStep)
        return cls(**{field.name: getattr(decoded, field.name) for field in fields(ProofStep)
                      if field.name != "operation"}, operation=NestedInferenceOperation.CHECKED_NESTED_EQUATION,
                   execution_digest=body["execution_digest"])


def nested_branch_to_dict(branch):
    body = to_primitive(branch)
    body["proof_steps"] = [proof.to_dict() for proof in branch.proof_steps]
    return body


@dataclass(frozen=True, slots=True)
class NestedBranchFrame(BranchFrame):
    proof_steps: tuple[ProofStep | NestedProofStep, ...]

    def __post_init__(self):
        _typed(self, NestedBranchFrame)
        _require(all(type(item) in (ProofStep, NestedProofStep) for item in self.proof_steps),
                 "foreign proof type in nested branch")

    def to_dict(self):
        return nested_branch_to_dict(self)

    @classmethod
    def from_dict(cls, value):
        return nested_branch_from_dict(value)


def nested_branch_from_dict(value):
    _keys(value, {field.name for field in fields(BranchFrame)}, "NestedBranchFrame")
    _list(value["proof_steps"], "nested branch proofs", 512)
    proofs = []
    for item in value["proof_steps"]:
        _require(type(item) is dict, "nested branch proof invalid")
        if item.get("operation") == NestedInferenceOperation.CHECKED_NESTED_EQUATION.value:
            proofs.append(NestedProofStep.from_dict(item))
        else:
            proofs.append(_legacy(item, ProofStep))
    base = _legacy({**value, "proof_steps": []}, BranchFrame)
    result = NestedBranchFrame(**{field.name: getattr(base, field.name) for field in fields(BranchFrame)
                                  if field.name != "proof_steps"}, proof_steps=tuple(proofs))
    _require(canonical_json(result.to_dict()) == canonical_json(value), "nested branch roundtrip mismatch")
    return result


@dataclass(frozen=True, slots=True)
class NestedState(MachineState):
    rpm_stack: tuple[NestedFrame, ...]
    branch_table: tuple[BranchFrame | NestedBranchFrame, ...]
    procedural_artifacts: tuple[ProcedureArtifact, ...]
    procedure_heads: tuple[tuple[str, str], ...]
    native_records: tuple[NestedRecord, ...]
    native_calls: tuple[GraphCall, ...]
    native_budget: NativeBudget
    native_contract_digest: str
    prior_episode_state_hash: str | None = None

    def __post_init__(self):
        _typed(self, NestedState)
        _require(self.runtime_version == NESTED_RUNTIME_VERSION
                 and self.constitution_revision == NESTED_CONSTITUTION_REVISION, "nested state version invalid")
        _counter(self.logical_tick, "logical tick")
        _counter(self.episodic_memory_revision, "episodic revision")
        _counter(self.seed, "seed", 2**63 - 1)
        for name in ("run_id", "active_goal_id"):
            _identifier(getattr(self, name), name)
        _sha(self.state_hash, "state", empty=True)
        _sha(self.trace_head, "trace head", empty=True)
        _sha(self.native_contract_digest, "nested contract")
        _sha(self.prior_episode_state_hash, "prior state", optional=True)
        _require(len(self.procedural_artifacts) <= MAX_ARTIFACTS and len(self.native_calls) <= MAX_CALLS
                 and len(self.native_records) <= MAX_RECORDS, "nested state collection bound exceeded")
        _require(sum(len(row.body_json) for row in self.native_records) <= MAX_STATE_BYTES,
                 "nested record text exceeds state bound before serialization")
        artifacts = {item.artifact_sha256 for item in self.procedural_artifacts}
        _require(len(artifacts) == len(self.procedural_artifacts), "duplicate nested artifact")
        _require(len({row.record_digest for row in self.native_records}) == len(self.native_records),
                 "duplicate nested record")
        _require(self.procedure_heads == tuple(sorted(self.procedure_heads))
                 and len({key for key, _ in self.procedure_heads}) == len(self.procedure_heads)
                 and all(key == CAPABILITY and value in artifacts for key, value in self.procedure_heads),
                 "nested procedure heads invalid")
        _require(len({call.call_id for call in self.native_calls}) == len(self.native_calls)
                 and len({call.variable for call in self.native_calls}) == len(self.native_calls),
                 "duplicate nested call or variable")
        _require(all(call.artifact_sha256 is None or call.artifact_sha256 in artifacts for call in self.native_calls),
                 "call pin references absent artifact")
        for field in fields(BudgetState):
            _counter(getattr(self.budget, field.name), "legacy " + field.name)
        _require(1 <= self.budget.rpm_depth_limit <= MAX_DEPTH, "nested RPM limit invalid")
        _require(len(self.branch_table) <= 8 and len(self.rpm_stack) <= MAX_DEPTH
                 and len(self.episodic_memory) <= 128, "nested legacy collection bound exceeded")
        _require(len({branch.branch_id for branch in self.branch_table}) == len(self.branch_table), "duplicate branch")
        _require(all(type(proof) in (ProofStep, NestedProofStep) for branch in self.branch_table
                     for proof in branch.proof_steps), "foreign proof in nested state")
        _require(len({frame.frame_id for frame in self.rpm_stack}) == len(self.rpm_stack), "duplicate nested frame")
        _bounded_json(self.to_dict(), MAX_STATE_BYTES, "nested state")

    def to_dict(self):
        body = {"schema_version": NESTED_STATE_SCHEMA, **to_primitive(self)}
        body["procedural_artifacts"] = [item.to_dict() for item in self.procedural_artifacts]
        body["branch_table"] = [nested_branch_to_dict(branch) for branch in self.branch_table]
        body["rpm_stack"] = [frame.to_dict() for frame in self.rpm_stack]
        body["native_records"] = [record.to_dict() for record in self.native_records]
        body["native_calls"] = [call.to_dict() for call in self.native_calls]
        return body

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, NESTED_STATE_SCHEMA)
        _bounded_json(value, MAX_STATE_BYTES, "nested state")
        for name, maximum in (("procedural_artifacts", MAX_ARTIFACTS), ("native_calls", MAX_CALLS),
            ("native_records", MAX_RECORDS), ("branch_table", 8), ("rpm_stack", MAX_DEPTH), ("episodic_memory", 128)):
            _list(body[name], name, maximum)
        for name in ("foundation_state", "drive_state", "domain_power_state", "procedure_heads"):
            body[name] = _pairs(body[name], name, 32)
        for name in ("working_memory", "pending_intents", "learning_queue"):
            _list(body[name], name)
            body[name] = tuple(body[name])
        body["working_memory"] = tuple(_legacy(item, Proposition) for item in body["working_memory"])
        body["global_workspace"] = _legacy(body["global_workspace"], GlobalWorkspace)
        body["commitment_state"] = _legacy(body["commitment_state"], CommitmentState)
        body["budget"] = _legacy(body["budget"], BudgetState)
        body["episodic_memory"] = tuple(_legacy(item, EpisodicRecord) for item in body["episodic_memory"])
        body["branch_table"] = tuple(nested_branch_from_dict(item) for item in body["branch_table"])
        body["rpm_stack"] = tuple(NestedFrame.from_dict(item) for item in body["rpm_stack"])
        try:
            _require(type(body["halt_status"]) is str, "nested halt wire type invalid")
            body["halt_status"] = TerminalStatus(body["halt_status"])
            body["procedural_artifacts"] = tuple(ProcedureArtifact.from_dict(item) for item in body["procedural_artifacts"])
        except (ValueError, TypeError) as exc:
            raise ContractError("nested state artifact/status invalid") from exc
        body["native_records"] = tuple(NestedRecord.from_dict(item) for item in body["native_records"])
        body["native_calls"] = tuple(GraphCall.from_dict(item) for item in body["native_calls"])
        body["native_budget"] = NativeBudget.from_dict(body["native_budget"])
        result = cls(**body)
        _require(result.state_hash == result.computed_hash(), "nested state hash mismatch")
        _require(canonical_json(result.to_dict()) == canonical_json(value), "nested state roundtrip mismatch")
        return result
