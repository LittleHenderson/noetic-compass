"""Closed one/two-call programs over a pinned six-instruction primitive.

This substrate has no installation authority and performs no equation solving.
All candidate outputs come from execute_procedure. Content hashes bind data;
they do not establish that a primitive or compound program was qualified.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
import re

from .canonical import digest
from .model import ContractError
from .nested_verification import _parse_rational
from .procedural_substrate import ProcedureArtifact, execute_procedure

PROGRAM_SCHEMA = "cncm.compound-call-program/0.1"
EXECUTION_SCHEMA = "cncm.compound-call-execution/0.1"
INPUT_NAMES = ("a", "b", "c", "d", "e")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class CompoundContractError(ContractError):
    """Unsupported, malformed, or unbound compound program data."""


def _require(condition, reason):
    if not condition:
        raise CompoundContractError(reason)


def _keys(value, keys, label):
    _require(type(value) is dict and set(value) == set(keys), label + "_FIELDS_INVALID")


def validate_inputs(inputs):
    """Admit exactly five canonical 128-bit rationals, before execution."""
    _keys(inputs, INPUT_NAMES, "COMPOUND_INPUT")
    for name in INPUT_NAMES:
        _parse_rational(inputs[name], 128, name)
    return {name: inputs[name] for name in INPUT_NAMES}


def _primitive(primitive):
    _require(type(primitive) is ProcedureArtifact, "TYPED_PRIMITIVE_REQUIRED")
    ProcedureArtifact.from_dict(primitive.to_dict())
    _require(primitive.limits.input_bits == 128 and primitive.limits.intermediate_bits == 512,
             "COMPOUND_PRIMITIVE_LIMITS_MISMATCH")
    return primitive


@dataclass(frozen=True, slots=True)
class CallStep:
    a_ref: str
    b_ref: str
    c_ref: str

    def __post_init__(self):
        refs = self.references
        _require(all(type(value) is str and value in (*INPUT_NAMES, "r0") for value in refs)
                 and len(set(refs)) == 3, "CALL_STEP_REFERENCES_INVALID")

    @property
    def references(self):
        return self.a_ref, self.b_ref, self.c_ref

    def to_dict(self):
        return dict(zip(("a_ref", "b_ref", "c_ref"), self.references, strict=True))

    @classmethod
    def from_dict(cls, value):
        _keys(value, ("a_ref", "b_ref", "c_ref"), "CALL_STEP")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class CallProgram:
    primitive_sha256: str
    steps: tuple[CallStep, ...]

    def __post_init__(self):
        _require(type(self.primitive_sha256) is str and _SHA.fullmatch(self.primitive_sha256) is not None,
                 "PRIMITIVE_DIGEST_INVALID")
        _require(type(self.steps) is tuple and len(self.steps) in (1, 2)
                 and all(type(step) is CallStep for step in self.steps), "CALL_PROGRAM_SHAPE_INVALID")
        for step in self.steps:
            CallStep.from_dict(step.to_dict())
        first = set(self.steps[0].references)
        _require(first <= set(INPUT_NAMES), "FIRST_CALL_MUST_USE_INPUTS")
        if len(self.steps) == 2:
            _require(set(self.steps[1].references) == (set(INPUT_NAMES) - first) | {"r0"},
                     "SECOND_CALL_MUST_USE_REMAINING_INPUTS_AND_RESULT")

    def _body(self):
        return {"schema_version": PROGRAM_SCHEMA, "primitive_sha256": self.primitive_sha256,
                "steps": [step.to_dict() for step in self.steps]}

    @property
    def program_digest(self):
        return digest(self._body())

    @property
    def artifact_sha256(self):
        return self.program_digest

    def to_dict(self):
        return {**self._body(), "program_digest": self.program_digest}

    @classmethod
    def from_dict(cls, value):
        _keys(value, ("schema_version", "primitive_sha256", "steps", "program_digest"), "CALL_PROGRAM")
        _require(value["schema_version"] == PROGRAM_SCHEMA, "CALL_PROGRAM_SCHEMA_INVALID")
        _require(type(value["steps"]) is list and len(value["steps"]) in (1, 2), "CALL_PROGRAM_SHAPE_INVALID")
        program = cls(value["primitive_sha256"], tuple(CallStep.from_dict(step) for step in value["steps"]))
        _require(type(value["program_digest"]) is str and value["program_digest"] == program.program_digest,
                 "CALL_PROGRAM_DIGEST_MISMATCH")
        return program


def enumerate_programs(primitive):
    """Return the complete 60+360 grammar in stable shape-then-reference order."""
    primitive = _primitive(primitive)
    first_steps = tuple(CallStep(*refs) for refs in permutations(INPUT_NAMES, 3))
    one = tuple(CallProgram(primitive.artifact_sha256, (first,)) for first in first_steps)
    two = tuple(CallProgram(primitive.artifact_sha256, (first, CallStep(*refs)))
                for first in first_steps
                for refs in permutations(sorted((set(INPUT_NAMES) - set(first.references)) | {"r0"})))
    return one + two


def execute_program(program, primitive, inputs, *, instruction_budget=12):
    """Execute only primitive calls; admission is not mathematical qualification.

    The entire program's instruction allowance is required before its first
    call. Each completed primitive receipt remains present after any refusal.
    A first output which cannot be admitted as a 128-bit second input refuses
    before the second primitive executes.
    """
    _require(type(program) is CallProgram, "TYPED_CALL_PROGRAM_REQUIRED")
    CallProgram.from_dict(program.to_dict())
    primitive = _primitive(primitive)
    _require(program.primitive_sha256 == primitive.artifact_sha256, "PINNED_PRIMITIVE_MISMATCH")
    values = validate_inputs(inputs)
    _require(type(instruction_budget) is int and 0 <= instruction_budget <= 12, "INSTRUCTION_BUDGET_INVALID")
    body = {"schema_version": EXECUTION_SCHEMA, "program_digest": program.program_digest,
            "primitive_sha256": primitive.artifact_sha256, "inputs": dict(values),
            "instruction_budget": instruction_budget, "status": "BUDGET_EXHAUSTED",
            "output": None, "instructions_executed": 0, "subcalls": []}
    if instruction_budget >= len(program.steps) * 6:
        for index, step in enumerate(program.steps):
            if index:
                try:
                    _parse_rational(values["r0"], 128, "composition input")
                except ContractError:
                    body["status"] = "COMPOSITION_INPUT_LIMIT"
                    break
            call_inputs = dict(zip(("a", "b", "c"), (values[ref] for ref in step.references), strict=True))
            execution = execute_procedure(primitive, call_inputs, instruction_budget=6)
            body["subcalls"].append({"step": index, "inputs": call_inputs, "execution": execution.to_dict()})
            body["instructions_executed"] += execution.instructions_executed
            if execution.status != "SUCCESS":
                body["status"] = execution.status
                break
            if index == len(program.steps) - 1:
                body.update(status="SUCCESS", output=execution.output)
            else:
                values["r0"] = execution.output
    return {**body, "report_digest": digest(body)}
