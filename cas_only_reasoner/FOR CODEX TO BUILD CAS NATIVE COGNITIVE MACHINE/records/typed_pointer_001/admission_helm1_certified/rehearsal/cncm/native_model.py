"""Closed v0.2 native-procedure data contracts; no execution or write authority.

Only one bounded linear-equation call and the existing v0.1 reasoning packet
are admitted. Decoding a checked proof or a saved state establishes structure
and content identity, never qualification, historical authority, or permission
to install a procedure. The native coordinator must reconstruct those gates.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from functools import lru_cache
import json
import re
from types import UnionType
from typing import Union, get_args, get_origin, get_type_hints

from .canonical import canonical_json, digest, to_primitive
from .model import (
    BranchFrame, BudgetState, CommitmentState, ContractError, EpisodicRecord,
    EvidenceStatus, GlobalWorkspace, InferenceOperation, MachineState,
    ProblemPacket, ProofStep, Proposition, Provenance, RPMFrame, TerminalStatus,
)
from .procedural_substrate import (
    CAPABILITY_CONTRACT, ProcedureArtifact, ProcedureContractError, _parse_rational,
)

NATIVE_RUNTIME_VERSION = "0.2.0"
NATIVE_PROBLEM_SCHEMA = "cncm.native-problem/0.2"
NATIVE_PROOF_SCHEMA = "cncm.native-proof/0.2"
NATIVE_CONSTITUTION_REVISION = "cncm-constitution/0.2"
CAPABILITY = "cncm.solve-linear/0.1"
OUTPUT_CONTRACT = "cncm.checked-linear-solution/0.1"
RESULT_PREDICATE = "procedure_checked"
MAX_ARTIFACTS = 8
MAX_CALLS = 8
MAX_RECORDS = 128
MAX_NATIVE_INSTRUCTIONS = 1_000_000
MAX_NATIVE_CHECKERS = 100_000
MAX_RECORD_BYTES = 262_144
MAX_STATE_BYTES = 16_777_216
NATIVE_RECORD_KINDS = frozenset({"WORK_RESERVATION", "SELECTION", "QUALIFICATION",
    "INSTALLATION", "EXECUTION", "FAILURE", "ROLLBACK"})
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class NativeIntentType(str, Enum):
    REQUEST_PROCEDURE_CALL = "REQUEST_PROCEDURE_CALL"
    PUSH_ACQUISITION = "PUSH_ACQUISITION"
    SELECT_PROCEDURE = "SELECT_PROCEDURE"
    INSTALL_PROCEDURE = "INSTALL_PROCEDURE"
    RETURN_ACQUISITION = "RETURN_ACQUISITION"
    APPLY_PROCEDURE = "APPLY_PROCEDURE"
    ROLLBACK_PROCEDURE = "ROLLBACK_PROCEDURE"


class NativeInferenceOperation(str, Enum):
    CHECKED_PROCEDURE = "CHECKED_PROCEDURE"


def _require(condition, label):
    if not condition:
        raise ContractError(label)


def _keys(value, names, label):
    _require(type(value) is dict and set(value) == set(names), label + " fields invalid")


def _identifier(value, label):
    _require(type(value) is str and _IDENTIFIER.fullmatch(value) is not None,
             label + " identifier invalid")


def _sha(value, label, *, optional=False, empty=False):
    if (optional and value is None) or (empty and value == ""):
        return
    _require(type(value) is str and _SHA.fullmatch(value) is not None,
             label + " digest invalid")


def _counter(value, label, maximum=MAX_NATIVE_INSTRUCTIONS):
    _require(type(value) is int and 0 <= value <= maximum, label + " counter invalid")


def _list(value, label, maximum=4096):
    _require(type(value) is list and len(value) <= maximum, label + " list invalid")


def _wire(value):
    """Reject non-JSON types and excessive structure before any decoder coerces."""
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        _require(count <= 100_000 and depth <= 40, "native JSON structure bound exceeded")
        if type(item) is dict:
            _require(len(item) <= 4096 and all(type(key) is str for key in item),
                     "native JSON object invalid")
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            _require(len(item) <= 4096, "native JSON list bound exceeded")
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _require(len(item) <= MAX_RECORD_BYTES, "native JSON string bound exceeded")
        elif type(item) is int:
            _require(item.bit_length() <= 63, "native JSON integer bound exceeded")
        else:
            _require(item is None or type(item) is bool, "native JSON primitive invalid")


@lru_cache(maxsize=64)
def _hints(kind):
    return get_type_hints(kind)


def _typed(value, annotation):
    """Validate immutable dataclass trees without bool/int or subclass coercion."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        for choice in args:
            try:
                _typed(value, choice)
                return
            except ContractError:
                pass
        raise ContractError("native field union type invalid")
    if origin is tuple:
        _require(type(value) is tuple and len(value) <= 4096, "native tuple invalid")
        if len(args) == 2 and args[1] is Ellipsis:
            for child in value:
                _typed(child, args[0])
        else:
            _require(len(value) == len(args), "native tuple arity invalid")
            for child, choice in zip(value, args, strict=True):
                _typed(child, choice)
        return
    allowed = {
        ProofStep: (ProofStep, NativeProofStep),
        BranchFrame: (BranchFrame, NativeBranchFrame),
        RPMFrame: (RPMFrame, AcquisitionFrame),
    }.get(annotation, (annotation,))
    _require(type(value) in allowed, "native field type invalid")
    if hasattr(type(value), "__dataclass_fields__"):
        hints = _hints(type(value))
        for field in fields(value):
            _typed(getattr(value, field.name), hints[field.name])


def _legacy(value, kind):
    """Use legacy semantics, but reject every coercion/default/unknown wire key."""
    _wire(value)
    try:
        result = kind.from_dict(value)
        _typed(result, kind)
        _require(canonical_json(result.to_dict()) == canonical_json(value),
                 kind.__name__ + " wire is not exact")
        return result
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ContractError(kind.__name__ + " wire invalid: " + str(exc)) from exc


def _rational(value, bits=128):
    try:
        _parse_rational(value, bits)
    except ProcedureContractError as exc:
        raise ContractError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class NativeBudget:
    instructions_remaining: int = 512
    checker_calls_remaining: int = 128

    def __post_init__(self):
        _counter(self.instructions_remaining, "native instructions", MAX_NATIVE_INSTRUCTIONS)
        _counter(self.checker_calls_remaining, "native checkers", MAX_NATIVE_CHECKERS)

    def to_dict(self):
        return to_primitive(self)

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "NativeBudget")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class CallSpec:
    call_id: str
    goal_id: str
    inputs: tuple[tuple[str, str], ...]
    branch_id: str = "branch-main"
    capability: str = CAPABILITY
    result_predicate: str = RESULT_PREDICATE
    output_contract: str = OUTPUT_CONTRACT
    result_scope: str = "global"

    def __post_init__(self):
        _identifier(self.call_id, "call")
        _identifier(self.goal_id, "call goal")
        _identifier(self.result_scope, "call result scope")
        _require(type(self.branch_id) is str and self.branch_id == "branch-main",
                 "native calls require branch-main")
        _require(type(self.capability) is str and self.capability == CAPABILITY
                 and type(self.result_predicate) is str and self.result_predicate == RESULT_PREDICATE
                 and type(self.output_contract) is str and self.output_contract == OUTPUT_CONTRACT,
                 "native call contract invalid")
        _typed(self.inputs, tuple[tuple[str, str], ...])
        _require(tuple(key for key, _ in self.inputs) == ("a", "b", "c"),
                 "native inputs must contain exactly ordered a/b/c")
        for _, value in self.inputs:
            _rational(value)

    @classmethod
    def create(cls, *, call_id, goal_id, inputs, **kwargs):
        _keys(inputs, {"a", "b", "c"}, "call inputs")
        return cls(call_id, goal_id, tuple((key, inputs[key]) for key in ("a", "b", "c")), **kwargs)

    def inputs_dict(self):
        return dict(self.inputs)

    @property
    def inputs_digest(self):
        return digest({"input_contract": CAPABILITY_CONTRACT, "inputs": self.inputs_dict()})

    @property
    def result_key(self):
        return f"{self.result_predicate}({self.call_id})@{self.result_scope}"

    def to_dict(self):
        return {**to_primitive(self), "inputs": self.inputs_dict()}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "CallSpec")
        body = dict(value)
        inputs = body.pop("inputs")
        return cls.create(inputs=inputs, **body)


@dataclass(frozen=True, slots=True)
class NativeProblem:
    reasoning: ProblemPacket
    call: CallSpec
    budget: NativeBudget = NativeBudget()

    def __post_init__(self):
        _require(type(self.reasoning) is ProblemPacket and type(self.call) is CallSpec
                 and type(self.budget) is NativeBudget, "native problem types invalid")
        _legacy(self.reasoning.to_dict(), ProblemPacket)
        _require(not self.reasoning.candidates and not self.reasoning.rpm_resolvers,
                 "native v0.2 forbids declared candidates and RPM resolvers")
        _require(self.call.goal_id == self.reasoning.goal_id, "native call goal mismatch")
        _require(self.call.result_scope == self.reasoning.query.scope, "native result scope mismatch")
        _require(all(item.predicate != RESULT_PREDICATE for item in self.reasoning.facts)
                 and all(rule.consequent.predicate != RESULT_PREDICATE for rule in self.reasoning.rules),
                 "procedure_checked is reserved for native checked results")
        entities = {item.entity_id: item.entity_type for item in self.reasoning.entities}
        declaration = next((item for item in self.reasoning.predicates
                            if item.predicate_id == RESULT_PREDICATE), None)
        _require(self.call.call_id in entities and declaration is not None
                 and declaration.argument_types == (entities[self.call.call_id],)
                 and not declaration.transitive, "native result declaration invalid")

    def to_dict(self):
        return {"schema_version": NATIVE_PROBLEM_SCHEMA, "reasoning": self.reasoning.to_dict(),
                "call": self.call.to_dict(), "budget": self.budget.to_dict()}

    @property
    def input_hash(self):
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"schema_version", "reasoning", "call", "budget"}, "NativeProblem")
        _require(type(value["schema_version"]) is str and value["schema_version"] == NATIVE_PROBLEM_SCHEMA,
                 "native problem version invalid")
        return cls(_legacy(value["reasoning"], ProblemPacket), CallSpec.from_dict(value["call"]),
                   NativeBudget.from_dict(value["budget"]))


@dataclass(frozen=True, slots=True)
class CallState:
    call_id: str
    status: str = "REQUESTED"
    artifact_sha256: str | None = None
    execution_digest: str | None = None
    output: str | None = None

    def __post_init__(self):
        _identifier(self.call_id, "call state")
        _require(type(self.status) is str and self.status in
                 {"REQUESTED", "SUSPENDED", "READY", "COMPLETE", "FAILED"}, "call status invalid")
        _sha(self.artifact_sha256, "call artifact", optional=True)
        _sha(self.execution_digest, "call execution", optional=True)
        if self.status in {"READY", "COMPLETE"}:
            _require(self.artifact_sha256 is not None, "ready call needs pinned artifact")
        if self.status == "COMPLETE":
            _require(self.execution_digest is not None and self.output is not None,
                     "complete call needs execution and output")
            _rational(self.output, 512)
        else:
            _require(self.output is None and self.execution_digest is None,
                     "incomplete call cannot carry output or execution")

    def to_dict(self):
        return to_primitive(self)

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "CallState")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    kind: str
    body_json: str
    record_digest: str

    def __post_init__(self):
        _identifier(self.kind, "record kind")
        _require(self.kind in NATIVE_RECORD_KINDS, "unsupported native record kind")
        _require(type(self.body_json) is str and len(self.body_json) <= MAX_RECORD_BYTES,
                 "record body bound exceeded")
        _require(len(self.body_json.encode("utf-8")) <= MAX_RECORD_BYTES, "record byte bound exceeded")
        try:
            body = json.loads(self.body_json)
        except (ValueError, RecursionError) as exc:
            raise ContractError("record body JSON invalid") from exc
        _require(type(body) is dict, "record body must be an object")
        _wire(body)
        _require(canonical_json(body) == self.body_json, "record body JSON is not canonical")
        _sha(self.record_digest, "record")
        _require(self.record_digest == digest({"kind": self.kind, "body": body}),
                 "record digest mismatch")

    @classmethod
    def create(cls, kind, body):
        _require(type(body) is dict, "record body must be an object")
        _wire(body)
        return cls(kind, canonical_json(body), digest({"kind": kind, "body": body}))

    def body_dict(self):
        return json.loads(self.body_json)

    def to_dict(self):
        return to_primitive(self)

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "CanonicalRecord")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class AcquisitionFrame(RPMFrame):
    call_id: str
    inputs_digest: str
    parent_branch_digest: str
    capability: str
    output_contract: str
    entry_instruction_budget: int
    entry_checker_budget: int
    kind: str = "PROCEDURE_ACQUISITION"

    def __post_init__(self):
        _typed(self, AcquisitionFrame)
        for name in ("frame_id", "goal_id", "parent_goal_id", "call_id"):
            _identifier(getattr(self, name), name)
        _require(self.kind == "PROCEDURE_ACQUISITION" and self.capability == CAPABILITY
                 and self.output_contract == OUTPUT_CONTRACT, "acquisition contract invalid")
        _require(self.branch_id == "branch-main" and self.parent_goal_id != self.goal_id
                 and self.blocked_prerequisite == self.capability
                 and self.expected_result_key == self.output_contract
                 and self.return_address == f"branch:{self.branch_id}:procedure:{self.call_id}"
                 and self.resume_stage == "PROCEDURE_CALL", "acquisition frame scope invalid")
        _require(1 <= self.depth <= 8, "acquisition depth invalid")
        _sha(self.inputs_digest, "acquisition inputs")
        _sha(self.parent_branch_digest, "acquisition parent")
        NativeBudget(self.entry_instruction_budget, self.entry_checker_budget)
        base = {field.name: getattr(self, field.name) for field in fields(RPMFrame)}
        _legacy(to_primitive(base), RPMFrame)

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "AcquisitionFrame")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class NativeProofStep(ProofStep):
    operation: NativeInferenceOperation
    execution_digest: str

    def __post_init__(self):
        _typed(self, NativeProofStep)
        _require(self.operation is NativeInferenceOperation.CHECKED_PROCEDURE,
                 "native proof operation invalid")
        _identifier(self.branch_id, "native proof branch")
        _sha(self.execution_digest, "native proof execution")
        _require(self.rule_id is None and not self.substitution and self.verified is True,
                 "native proof shape invalid")
        _require(self.conclusion.predicate == RESULT_PREDICATE
                 and len(self.conclusion.arguments) == 1
                 and self.conclusion.polarity is True
                 and self.conclusion.evidence_status is EvidenceStatus.DERIVED,
                 "native proof conclusion invalid")
        _legacy(self.conclusion.to_dict(), Proposition)
        _require(not self.premise_keys, "native proof root cannot carry external premises")
        _require(self.provenance == tuple(sorted(self.provenance,
                 key=lambda item: (item.source_type, item.source_id, item.detail))),
                 "native proof provenance is not canonical")
        _require(self.step_id == "native-proof-" + digest(self._body()), "native proof digest mismatch")

    def _body(self):
        body = to_primitive(self)
        body.pop("step_id")
        return {"schema_version": NATIVE_PROOF_SCHEMA, **body}

    def to_dict(self):
        return {"step_id": self.step_id, **self._body()}

    @classmethod
    def create_checked(cls, *, conclusion, branch_id, execution_digest, provenance=()):
        body = {"schema_version": NATIVE_PROOF_SCHEMA,
                "operation": NativeInferenceOperation.CHECKED_PROCEDURE.value,
                "premise_keys": [], "rule_id": None,
                "conclusion": conclusion.to_dict(), "substitution": [],
                "branch_id": branch_id, "verified": True,
                "provenance": [item.to_dict() for item in sorted(provenance,
                    key=lambda item: (item.source_type, item.source_id, item.detail))],
                "execution_digest": execution_digest}
        return cls.from_dict({"step_id": "native-proof-" + digest(body), **to_primitive(body)})

    create = create_checked

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)} | {"schema_version"}, "NativeProofStep")
        _wire(value)
        _require(value["schema_version"] == NATIVE_PROOF_SCHEMA
                 and type(value["operation"]) is str
                 and value["operation"] == NativeInferenceOperation.CHECKED_PROCEDURE.value,
                 "native proof version/operation invalid")
        base = {field.name: value[field.name] for field in fields(ProofStep)}
        base["operation"] = InferenceOperation.RPM_CHILD_RESULT.value
        decoded = _legacy(base, ProofStep)
        return cls(**{field.name: getattr(decoded, field.name) for field in fields(ProofStep)
                      if field.name != "operation"},
                   operation=NativeInferenceOperation.CHECKED_PROCEDURE,
                   execution_digest=value["execution_digest"])


def native_branch_to_dict(branch):
    body = to_primitive(branch)
    body["proof_steps"] = [proof.to_dict() for proof in branch.proof_steps]
    return body


@dataclass(frozen=True, slots=True)
class NativeBranchFrame(BranchFrame):
    def to_dict(self):
        return native_branch_to_dict(self)

    @classmethod
    def from_dict(cls, value):
        return native_branch_from_dict(value)


def native_branch_from_dict(value):
    _keys(value, {field.name for field in fields(BranchFrame)}, "NativeBranchFrame")
    _list(value["proof_steps"], "native proofs", 512)
    proofs = []
    for item in value["proof_steps"]:
        _require(type(item) is dict, "native branch proof invalid")
        if item.get("operation") == NativeInferenceOperation.CHECKED_PROCEDURE.value:
            proofs.append(NativeProofStep.from_dict(item))
        else:
            proofs.append(_legacy(item, ProofStep))
    empty = {**value, "proof_steps": []}
    base = _legacy(empty, BranchFrame)
    result = NativeBranchFrame(**{field.name: getattr(base, field.name) for field in fields(BranchFrame)
                                 if field.name != "proof_steps"}, proof_steps=tuple(proofs))
    _typed(result, NativeBranchFrame)
    _require(canonical_json(result.to_dict()) == canonical_json(value), "native branch roundtrip mismatch")
    return result


@dataclass(frozen=True, slots=True)
class NativeState(MachineState):
    procedural_artifacts: tuple[ProcedureArtifact, ...]
    procedure_heads: tuple[tuple[str, str], ...]
    native_records: tuple[CanonicalRecord, ...]
    native_calls: tuple[CallState, ...]
    native_budget: NativeBudget
    native_contract_digest: str
    prior_episode_state_hash: str | None = None

    def __post_init__(self):
        _typed(self, NativeState)
        _require(self.runtime_version == NATIVE_RUNTIME_VERSION
                 and self.constitution_revision == NATIVE_CONSTITUTION_REVISION,
                 "native state version invalid")
        _counter(self.logical_tick, "logical tick")
        _counter(self.episodic_memory_revision, "episode revision")
        _counter(self.seed, "seed", 2**63 - 1)
        for name in ("run_id", "active_goal_id"):
            _identifier(getattr(self, name), name)
        _sha(self.state_hash, "state", empty=True)
        _sha(self.trace_head, "trace head", empty=True)
        _sha(self.native_contract_digest, "native contract")
        _sha(self.prior_episode_state_hash, "prior episode state", optional=True)
        _require(len(self.procedural_artifacts) <= MAX_ARTIFACTS
                 and len(self.native_records) <= MAX_RECORDS and len(self.native_calls) <= MAX_CALLS,
                 "native state collection cap exceeded")
        artifacts = {item.artifact_sha256 for item in self.procedural_artifacts}
        _require(len({item.record_digest for item in self.native_records}) == len(self.native_records),
                 "duplicate native record")
        _require(len(artifacts) == len(self.procedural_artifacts), "duplicate native artifact")
        _require(self.procedure_heads == tuple(sorted(self.procedure_heads))
                 and len({key for key, _ in self.procedure_heads}) == len(self.procedure_heads),
                 "procedure heads are not canonical and unique")
        _require(all(key == CAPABILITY and value in artifacts for key, value in self.procedure_heads),
                 "procedure head references unsupported or absent artifact")
        _require(len({call.call_id for call in self.native_calls}) == len(self.native_calls),
                 "duplicate native call")
        _require(all(call.status not in {"READY", "COMPLETE"} or call.artifact_sha256 in artifacts
                     for call in self.native_calls), "call pin references absent artifact")
        for field in fields(BudgetState):
            _counter(getattr(self.budget, field.name), "legacy " + field.name)
        _require(self.budget.rpm_depth_limit >= 1, "RPM depth limit invalid")
        _require(len(self.branch_table) <= 8 and len(self.rpm_stack) <= 8
                 and len(self.episodic_memory) <= 128, "native legacy collection cap exceeded")
        _require(len({branch.branch_id for branch in self.branch_table}) == len(self.branch_table),
                 "duplicate branch")
        _require(len({frame.frame_id for frame in self.rpm_stack}) == len(self.rpm_stack),
                 "duplicate RPM frame")

    def to_dict(self):
        body = to_primitive(self)
        body["procedural_artifacts"] = [item.to_dict() for item in self.procedural_artifacts]
        body["branch_table"] = [native_branch_to_dict(branch) for branch in self.branch_table]
        return body

    @classmethod
    def from_dict(cls, value):
        _keys(value, {field.name for field in fields(cls)}, "NativeState")
        _wire(value)
        _require(len(canonical_json(value).encode("utf-8")) <= MAX_STATE_BYTES,
                 "native state byte bound exceeded")
        for name, maximum in (("procedural_artifacts", MAX_ARTIFACTS), ("native_calls", MAX_CALLS),
                              ("native_records", MAX_RECORDS), ("branch_table", 8), ("rpm_stack", 8),
                              ("episodic_memory", 128)):
            _list(value[name], name, maximum)
        body = dict(value)
        for name in ("foundation_state", "drive_state", "domain_power_state", "procedure_heads"):
            _list(body[name], name, 32)
            _require(all(type(item) is list and len(item) == 2 for item in body[name]),
                     name + " pair list invalid")
            body[name] = tuple(tuple(item) for item in body[name])
        for name in ("working_memory", "pending_intents", "learning_queue"):
            _list(body[name], name)
            body[name] = tuple(body[name])
        body["working_memory"] = tuple(_legacy(item, Proposition) for item in body["working_memory"])
        body["global_workspace"] = _legacy(body["global_workspace"], GlobalWorkspace)
        body["commitment_state"] = _legacy(body["commitment_state"], CommitmentState)
        body["budget"] = _legacy(body["budget"], BudgetState)
        body["episodic_memory"] = tuple(_legacy(item, EpisodicRecord) for item in body["episodic_memory"])
        body["branch_table"] = tuple(native_branch_from_dict(item) for item in body["branch_table"])
        body["rpm_stack"] = tuple(AcquisitionFrame.from_dict(item) if type(item) is dict and
                                  item.get("kind") == "PROCEDURE_ACQUISITION" else _legacy(item, RPMFrame)
                                  for item in body["rpm_stack"])
        try:
            body["halt_status"] = TerminalStatus(body["halt_status"])
            body["procedural_artifacts"] = tuple(ProcedureArtifact.from_dict(item)
                                                 for item in body["procedural_artifacts"])
        except (ValueError, TypeError) as exc:
            raise ContractError("native state artifact/status invalid") from exc
        body["native_records"] = tuple(CanonicalRecord.from_dict(item) for item in body["native_records"])
        body["native_calls"] = tuple(CallState.from_dict(item) for item in body["native_calls"])
        body["native_budget"] = NativeBudget.from_dict(body["native_budget"])
        result = cls(**body)
        _require(result.state_hash == result.computed_hash(), "native state hash mismatch")
        _require(canonical_json(result.to_dict()) == canonical_json(value), "native state roundtrip mismatch")
        return result
