"""Isolated deterministic CCB-T1 Cognitive Apprenticeship laboratory.

The board implemented here is domain-neutral and proposal-only.  Teachers may
offer typed knowledge or procedures through explicit transfer channels.  A
separate prerequisite registry, CAS-SDG identity, protected fixture custody,
held-out transfer checks, regression sentinels, and delayed retention checks
determine whether an artifact may enter this module's *local* capability
store.  Nothing in this module writes CNCM state or produces a CAS-RRK
promotion receipt.

The procedure interpreter is a finite straight-line instruction machine.  It
has no dynamic code execution, imports from lesson content, jumps, loops,
filesystem access, network access, or wall-clock inputs.  CAS-Ohm readings are
stored only as observations and never participate in promotion gates.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from fractions import Fraction
import re
from typing import Any, Iterable

from .canonical import content_id as canonical_content_id
from .canonical import digest as canonical_digest
from .canonical import to_primitive


class CognitiveApprenticeshipError(ValueError):
    """Base error for the isolated CCB-T1 laboratory."""


class ApprenticeshipValidationError(CognitiveApprenticeshipError):
    """A typed packet or record violates the bounded contract."""


class ApprenticeshipQualificationError(CognitiveApprenticeshipError):
    """Evidence custody, prerequisites, or qualification are invalid."""


class ApprenticeshipPromotionError(CognitiveApprenticeshipError):
    """A local promotion is not authorized by locally issued receipts."""


class ApprenticeshipLifecycleError(CognitiveApprenticeshipError):
    """A requested version or episode transition is invalid."""


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_REGISTER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_INTEGER_OR_RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
_MAX_TEXT = 1024
_MAX_INSTRUCTIONS = 32
_MAX_CASES = 64


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ApprenticeshipValidationError(f"{name} must be a bounded identifier")


def _require_register(name: str, value: str) -> None:
    if not isinstance(value, str) or _REGISTER.fullmatch(value) is None:
        raise ApprenticeshipValidationError(f"{name} must be a lowercase register name")


def _require_text(name: str, value: str, *, limit: int = _MAX_TEXT) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ApprenticeshipValidationError(
            f"{name} must be non-empty and at most {limit} characters"
        )
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise ApprenticeshipValidationError(f"{name} contains a control character")


def _require_tuple(name: str, value: object) -> None:
    if type(value) is not tuple:
        raise ApprenticeshipValidationError(f"{name} must be an immutable tuple")


def _require_unique(name: str, values: Iterable[str]) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ApprenticeshipValidationError(f"{name} must not contain duplicates")


def _require_digest(name: str, value: str) -> None:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ApprenticeshipValidationError(f"{name} must be a lowercase SHA-256 digest")


class TeacherRole(str, Enum):
    LECTURER = "CCB_T1_ROLE_LECTURER"
    DEMONSTRATOR = "CCB_T1_ROLE_DEMONSTRATOR"
    SOCRATIC_TUTOR = "CCB_T1_ROLE_SOCRATIC_TUTOR"
    CURRICULUM_DESIGNER = "CCB_T1_ROLE_CURRICULUM_DESIGNER"
    ADVERSARY = "CCB_T1_ROLE_ADVERSARY"
    CRITIC = "CCB_T1_ROLE_CRITIC"
    RESEARCH_MENTOR = "CCB_T1_ROLE_RESEARCH_MENTOR"


class TransferChannel(str, Enum):
    EXPLICIT_SYMBOLIC = "CCB_T1_CHANNEL_EXPLICIT_SYMBOLIC"
    PROCEDURAL_INDUCTION = "CCB_T1_CHANNEL_DEMONSTRATION_PROCEDURAL_INDUCTION"
    NEURAL_DISTILLATION = "CCB_T1_CHANNEL_NEURAL_DISTILLATION"
    RETRIEVAL_LINKED_KNOWLEDGE = "CCB_T1_CHANNEL_RETRIEVAL_LINKED_KNOWLEDGE"
    SYNTHETIC_EXPERIENCE = "CCB_T1_CHANNEL_SYNTHETIC_EXPERIENCE"


class LessonCategory(str, Enum):
    LANGUAGE = "CCB_T1_CATEGORY_LANGUAGE"
    EXACT_REASONING = "CCB_T1_CATEGORY_EXACT_REASONING"
    MATHEMATICS = "CCB_T1_CATEGORY_MATHEMATICS"
    CODING = "CCB_T1_CATEGORY_CODING"
    TOOL_USE = "CCB_T1_CATEGORY_TOOL_USE"
    SOURCE_GROUNDED_FACT = "CCB_T1_CATEGORY_SOURCE_GROUNDED_FACT"
    RESEARCH_METHOD = "CCB_T1_CATEGORY_RESEARCH_METHOD"
    MEMORY_PROCEDURE = "CCB_T1_CATEGORY_MEMORY_PROCEDURE"
    METACOGNITION = "CCB_T1_CATEGORY_METACOGNITION"
    DIALOGUE = "CCB_T1_CATEGORY_DIALOGUE"
    CREATIVE_PROCEDURE = "CCB_T1_CATEGORY_CREATIVE_PROCEDURE"
    BOARD_DESIGN = "CCB_T1_CATEGORY_BOARD_DESIGN"
    SELF_DIAGNOSIS = "CCB_T1_CATEGORY_SELF_DIAGNOSIS"
    AUTHORITY_CONTRACT = "CCB_T1_PROTECTED_AUTHORITY_CONTRACT"
    SOLE_WRITER_STATE_RULE = "CCB_T1_PROTECTED_SOLE_WRITER_RULE"
    PROOF_CHECKER = "CCB_T1_PROTECTED_PROOF_CHECKER"
    TRACE_VERIFIER = "CCB_T1_PROTECTED_TRACE_VERIFIER"
    PROTECTED_BENCHMARK = "CCB_T1_PROTECTED_BENCHMARKS"
    CONSTITUTIONAL_VALUE = "CCB_T1_PROTECTED_CONSTITUTIONAL_VALUES"
    DEPLOYMENT_PERMISSION = "CCB_T1_PROTECTED_DEPLOYMENT_PERMISSIONS"
    ROLLBACK_MACHINERY = "CCB_T1_PROTECTED_ROLLBACK_MACHINERY"
    DEFINITION_OF_IMPROVEMENT = "CCB_T1_PROTECTED_DEFINITION_OF_IMPROVEMENT"


PROTECTED_LESSON_CATEGORIES = frozenset(
    {
        LessonCategory.AUTHORITY_CONTRACT,
        LessonCategory.SOLE_WRITER_STATE_RULE,
        LessonCategory.PROOF_CHECKER,
        LessonCategory.TRACE_VERIFIER,
        LessonCategory.PROTECTED_BENCHMARK,
        LessonCategory.CONSTITUTIONAL_VALUE,
        LessonCategory.DEPLOYMENT_PERMISSION,
        LessonCategory.ROLLBACK_MACHINERY,
        LessonCategory.DEFINITION_OF_IMPROVEMENT,
    }
)


class ArtifactKind(str, Enum):
    PROCEDURE_PROGRAM = "CCB_T1_ARTIFACT_PROCEDURE_PROGRAM"
    SOURCE_LINKED_CLAIM = "CCB_T1_ARTIFACT_SOURCE_LINKED_CLAIM"
    POLICY_PROPOSAL = "CCB_T1_ARTIFACT_POLICY_PROPOSAL"


class InstructionOp(str, Enum):
    LOAD_INPUT = "CCB_T1_OP_LOAD_INPUT"
    LOAD_CONSTANT = "CCB_T1_OP_LOAD_CONSTANT"
    ADD_EXACT = "CCB_T1_OP_ADD_EXACT"
    SUBTRACT_EXACT = "CCB_T1_OP_SUBTRACT_EXACT"
    MULTIPLY_EXACT = "CCB_T1_OP_MULTIPLY_EXACT"
    DIVIDE_EXACT = "CCB_T1_OP_DIVIDE_EXACT"
    REQUIRE_TRUE = "CCB_T1_OP_REQUIRE_TRUE"
    EMIT_REGISTER = "CCB_T1_OP_EMIT_REGISTER"
    EMIT_LITERAL = "CCB_T1_OP_EMIT_LITERAL"
    COPY_INPUT_TO_OUTPUT = "CCB_T1_OP_COPY_INPUT_TO_OUTPUT"
    SOURCE_LOOKUP = "CCB_T1_OP_SOURCE_LOOKUP"


class ExecutionStatus(str, Enum):
    SUCCESS = "CCB_T1_EXEC_SUCCESS"
    MISSING_INPUT = "CCB_T1_EXEC_MISSING_INPUT"
    INVALID_INPUT = "CCB_T1_EXEC_INVALID_INPUT"
    DIVISION_BY_ZERO = "CCB_T1_EXEC_DIVISION_BY_ZERO"
    PERMISSION_REQUIRED = "CCB_T1_EXEC_PERMISSION_REQUIRED"
    SOURCE_OUTSIDE_VALIDITY_WINDOW = "CCB_T1_EXEC_SOURCE_OUTSIDE_VALIDITY_WINDOW"
    SOURCE_BINDING_INVALID = "CCB_T1_EXEC_SOURCE_BINDING_INVALID"
    UNSUPPORTED_ARTIFACT = "CCB_T1_EXEC_UNSUPPORTED_ARTIFACT"


class SuitePurpose(str, Enum):
    QUALIFICATION = "CCB_T1_SUITE_QUALIFICATION"
    DELAYED_RETENTION = "CCB_T1_SUITE_DELAYED_RETENTION"


class EpisodeStatus(str, Enum):
    PROPOSED = "CCB_T1_PROPOSED"
    PREREQUISITE_BLOCKED = "CCB_T1_PREREQUISITE_BLOCKED"
    QUALIFIED = "CCB_T1_QUALIFIED"
    PROVISIONAL_LOCAL = "CCB_T1_PROVISIONAL_LOCAL"
    DURABLE_LOCAL = "CCB_T1_DURABLE_LOCAL"
    QUARANTINED = "CCB_T1_QUARANTINED"
    PROTECTED_REJECTED = "CCB_T1_PROTECTED_REJECTED"
    SUPERSEDED = "CCB_T1_SUPERSEDED"
    ROLLED_BACK = "CCB_T1_ROLLED_BACK"


class VersionStatus(str, Enum):
    PROVISIONAL_LOCAL = "CCB_T1_VERSION_PROVISIONAL_LOCAL"
    ACTIVE_LOCAL = "CCB_T1_VERSION_ACTIVE_LOCAL"
    QUARANTINED = "CCB_T1_VERSION_QUARANTINED"
    SUPERSEDED = "CCB_T1_VERSION_SUPERSEDED"
    ROLLED_BACK = "CCB_T1_VERSION_ROLLED_BACK"


class HonestOutcome(str, Enum):
    PROPOSAL_RECORDED_ONLY = "CCB_T1_OUTCOME_PROPOSAL_RECORDED_ONLY"
    MISSING_PREREQUISITE = "CCB_T1_OUTCOME_MISSING_PREREQUISITE"
    QUALIFICATION_FAILED = "CCB_T1_OUTCOME_QUALIFICATION_FAILED"
    PROTECTED_REQUIRES_SEPARATE_AUTHORITY = (
        "CCB_T1_OUTCOME_PROTECTED_REQUIRES_SEPARATE_AUTHORITY"
    )
    PROVISIONAL_LOCAL_ONLY = "CCB_T1_OUTCOME_PROVISIONAL_LOCAL_ONLY"
    DURABLE_LOCAL_ONLY = "CCB_T1_OUTCOME_DURABLE_LOCAL_ONLY"
    SOURCE_GROUNDED_LOCAL_ONLY = "CCB_T1_OUTCOME_SOURCE_GROUNDED_LOCAL_ONLY"
    RETENTION_FAILED_ROLLED_BACK = "CCB_T1_OUTCOME_RETENTION_FAILED_ROLLED_BACK"
    ROLLED_BACK = "CCB_T1_OUTCOME_ROLLED_BACK"


class QualificationGate(str, Enum):
    PROPOSAL_ISOLATED = "CCB_T1_GATE_PROPOSAL_ISOLATED"
    PREREQUISITES_PASS = "CCB_T1_GATE_PREREQUISITES_PASS"
    PROTECTED_CATEGORY_ALLOWED = "CCB_T1_GATE_PROTECTED_CATEGORY_ALLOWED"
    ARTIFACT_VALID = "CCB_T1_GATE_ARTIFACT_VALID"
    TEACHER_EXAMPLES_PASS = "CCB_T1_GATE_TEACHER_EXAMPLES_PASS"
    CAS_SDG_EXPANSION_PASS = "CCB_T1_GATE_CAS_SDG_EXPANSION_PASS"
    HELD_OUT_TRANSFER_PASS = "CCB_T1_GATE_HELD_OUT_TRANSFER_PASS"
    COUNTEREXAMPLES_PASS = "CCB_T1_GATE_COUNTEREXAMPLES_PASS"
    REGRESSION_PASS = "CCB_T1_GATE_REGRESSION_PASS"
    DETERMINISTIC_REPLAY_PASS = "CCB_T1_GATE_DETERMINISTIC_REPLAY_PASS"
    DELAYED_RETENTION_PASS = "CCB_T1_GATE_DELAYED_RETENTION_PASS"


_QUALIFICATION_LADDER = (
    QualificationGate.PROPOSAL_ISOLATED,
    QualificationGate.PREREQUISITES_PASS,
    QualificationGate.PROTECTED_CATEGORY_ALLOWED,
    QualificationGate.ARTIFACT_VALID,
    QualificationGate.TEACHER_EXAMPLES_PASS,
    QualificationGate.CAS_SDG_EXPANSION_PASS,
    QualificationGate.HELD_OUT_TRANSFER_PASS,
    QualificationGate.COUNTEREXAMPLES_PASS,
    QualificationGate.REGRESSION_PASS,
    QualificationGate.DETERMINISTIC_REPLAY_PASS,
)


class EffectStatus(str, Enum):
    CORRECT = "CCB_T1_EFFECT_CORRECT"
    INCORRECT = "CCB_T1_EFFECT_INCORRECT"
    UNKNOWN = "CCB_T1_EFFECT_UNKNOWN"


@dataclass(frozen=True, slots=True)
class TeacherIdentity:
    principal: str
    revision: str

    def __post_init__(self) -> None:
        _require_identifier("teacher principal", self.principal)
        _require_identifier("teacher revision", self.revision)

    @property
    def identity_id(self) -> str:
        return canonical_content_id("ccb-t1-teacher", self)


@dataclass(frozen=True, slots=True)
class TeacherAssignment:
    role: TeacherRole
    teacher: TeacherIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.role, TeacherRole):
            raise ApprenticeshipValidationError("teacher role must be a TeacherRole")
        if not isinstance(self.teacher, TeacherIdentity):
            raise ApprenticeshipValidationError("teacher assignment requires TeacherIdentity")


@dataclass(frozen=True, slots=True)
class ExaminerIdentity:
    principal: str
    revision: str
    custody_channel: str

    def __post_init__(self) -> None:
        _require_identifier("examiner principal", self.principal)
        _require_identifier("examiner revision", self.revision)
        _require_identifier("examiner custody_channel", self.custody_channel)

    @property
    def identity_id(self) -> str:
        return canonical_content_id("ccb-t1-examiner", self)


@dataclass(frozen=True, slots=True)
class CASSDGIdentity:
    generator: str
    revision: str

    def __post_init__(self) -> None:
        _require_identifier("CAS-SDG generator", self.generator)
        _require_identifier("CAS-SDG revision", self.revision)

    @property
    def identity_id(self) -> str:
        return canonical_content_id("ccb-t1-cas-sdg", self)


@dataclass(frozen=True, slots=True, order=True)
class NamedValue:
    name: str
    value: str

    def __post_init__(self) -> None:
        _require_register("named value name", self.name)
        _require_text("named value", self.value, limit=512)


@dataclass(frozen=True, slots=True)
class Instruction:
    operation: InstructionOp
    target: str | None
    arguments: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.operation, InstructionOp):
            raise ApprenticeshipValidationError("instruction operation is invalid")
        _require_tuple("instruction arguments", self.arguments)
        for argument in self.arguments:
            _require_text("instruction argument", argument, limit=512)
        binary = {
            InstructionOp.ADD_EXACT,
            InstructionOp.SUBTRACT_EXACT,
            InstructionOp.MULTIPLY_EXACT,
            InstructionOp.DIVIDE_EXACT,
        }
        if self.operation in {InstructionOp.LOAD_INPUT, InstructionOp.LOAD_CONSTANT}:
            if self.target is None or len(self.arguments) != 1:
                raise ApprenticeshipValidationError(
                    "load instructions require a target and one argument"
                )
            _require_register("instruction target", self.target)
        elif self.operation in binary:
            if self.target is None or len(self.arguments) != 2:
                raise ApprenticeshipValidationError(
                    "exact arithmetic instructions require a target and two registers"
                )
            _require_register("instruction target", self.target)
            for register in self.arguments:
                _require_register("arithmetic source register", register)
        elif self.operation is InstructionOp.REQUIRE_TRUE:
            if self.target is not None or len(self.arguments) != 1:
                raise ApprenticeshipValidationError(
                    "REQUIRE_TRUE requires one input name and no target"
                )
            _require_register("required boolean input", self.arguments[0])
        elif self.operation in {
            InstructionOp.EMIT_REGISTER,
            InstructionOp.EMIT_LITERAL,
            InstructionOp.COPY_INPUT_TO_OUTPUT,
            InstructionOp.SOURCE_LOOKUP,
        }:
            if self.target is None or len(self.arguments) != 1:
                raise ApprenticeshipValidationError(
                    "output instructions require an output target and one argument"
                )
            _require_register("output target", self.target)
            if self.operation is not InstructionOp.EMIT_LITERAL:
                _require_register("output source", self.arguments[0])


@dataclass(frozen=True, slots=True)
class SourceLinkedClaim:
    claim_key: str
    claim_value: str
    source_locator: str
    observed_on: str
    valid_from: str
    valid_through: str
    source_digest: str

    def __post_init__(self) -> None:
        _require_identifier("claim_key", self.claim_key)
        _require_text("claim_value", self.claim_value, limit=512)
        _require_text("source_locator", self.source_locator, limit=512)
        if not (
            self.source_locator.startswith("https://")
            or self.source_locator.startswith("urn:")
        ):
            raise ApprenticeshipValidationError(
                "source_locator must be an https URL or explicit URN"
            )
        try:
            observed = date.fromisoformat(self.observed_on)
            valid_from = date.fromisoformat(self.valid_from)
            valid_through = date.fromisoformat(self.valid_through)
        except ValueError as exc:
            raise ApprenticeshipValidationError("source dates must be ISO-8601 dates") from exc
        if not valid_from <= observed <= valid_through:
            raise ApprenticeshipValidationError(
                "observed_on must fall inside the stated validity window"
            )
        _require_digest("source_digest", self.source_digest)
        if self.source_digest != canonical_digest(self._digest_payload()):
            raise ApprenticeshipValidationError("source_digest does not bind the claim payload")

    def _digest_payload(self) -> dict[str, str]:
        return {
            "claim_key": self.claim_key,
            "claim_value": self.claim_value,
            "source_locator": self.source_locator,
            "observed_on": self.observed_on,
            "valid_from": self.valid_from,
            "valid_through": self.valid_through,
        }

    @classmethod
    def create(
        cls,
        *,
        claim_key: str,
        claim_value: str,
        source_locator: str,
        observed_on: str,
        valid_from: str,
        valid_through: str,
    ) -> "SourceLinkedClaim":
        payload = {
            "claim_key": claim_key,
            "claim_value": claim_value,
            "source_locator": source_locator,
            "observed_on": observed_on,
            "valid_from": valid_from,
            "valid_through": valid_through,
        }
        return cls(source_digest=canonical_digest(payload), **payload)

    @property
    def claim_content_id(self) -> str:
        return canonical_content_id("ccb-t1-source-claim", self)


@dataclass(frozen=True, slots=True)
class CapabilityArtifact:
    capability_key: str
    revision: int
    kind: ArtifactKind
    program: tuple[Instruction, ...]
    source_claim: SourceLinkedClaim | None
    description: str

    def __post_init__(self) -> None:
        _require_identifier("capability_key", self.capability_key)
        if type(self.revision) is not int or self.revision < 1:
            raise ApprenticeshipValidationError("artifact revision must be a positive integer")
        if not isinstance(self.kind, ArtifactKind):
            raise ApprenticeshipValidationError("artifact kind is invalid")
        _require_tuple("artifact program", self.program)
        if not self.program or len(self.program) > _MAX_INSTRUCTIONS:
            raise ApprenticeshipValidationError(
                f"artifact program must contain 1..{_MAX_INSTRUCTIONS} instructions"
            )
        if any(not isinstance(instruction, Instruction) for instruction in self.program):
            raise ApprenticeshipValidationError("artifact program contains an invalid instruction")
        _require_text("artifact description", self.description, limit=512)
        if self.kind is ArtifactKind.SOURCE_LINKED_CLAIM:
            if not isinstance(self.source_claim, SourceLinkedClaim):
                raise ApprenticeshipValidationError(
                    "source-linked artifacts require SourceLinkedClaim"
                )
            if not any(
                instruction.operation is InstructionOp.SOURCE_LOOKUP
                for instruction in self.program
            ):
                raise ApprenticeshipValidationError(
                    "source-linked artifacts require a SOURCE_LOOKUP instruction"
                )
        elif self.source_claim is not None:
            raise ApprenticeshipValidationError(
                "only source-linked artifacts may carry a source claim"
            )

    @property
    def artifact_content_id(self) -> str:
        return canonical_content_id("ccb-t1-artifact", self)

    @property
    def artifact_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: ExecutionStatus
    outputs: tuple[NamedValue, ...]
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExecutionStatus):
            raise ApprenticeshipValidationError("execution status is invalid")
        _require_tuple("execution outputs", self.outputs)
        if any(not isinstance(output, NamedValue) for output in self.outputs):
            raise ApprenticeshipValidationError("execution outputs contain invalid values")
        if tuple(sorted(self.outputs)) != self.outputs:
            raise ApprenticeshipValidationError("execution outputs must be sorted canonically")
        _require_unique("execution output names", (output.name for output in self.outputs))
        _require_text("execution reason", self.reason, limit=512)

    @property
    def result_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    inputs: tuple[NamedValue, ...]
    expected_status: ExecutionStatus
    expected_outputs: tuple[NamedValue, ...]

    def __post_init__(self) -> None:
        _require_identifier("evaluation case_id", self.case_id)
        _require_tuple("evaluation inputs", self.inputs)
        _require_tuple("evaluation expected_outputs", self.expected_outputs)
        if any(not isinstance(value, NamedValue) for value in self.inputs):
            raise ApprenticeshipValidationError("evaluation inputs contain invalid values")
        if any(not isinstance(value, NamedValue) for value in self.expected_outputs):
            raise ApprenticeshipValidationError(
                "evaluation expected_outputs contain invalid values"
            )
        if tuple(sorted(self.inputs)) != self.inputs:
            raise ApprenticeshipValidationError("evaluation inputs must be sorted canonically")
        if tuple(sorted(self.expected_outputs)) != self.expected_outputs:
            raise ApprenticeshipValidationError(
                "evaluation expected_outputs must be sorted canonically"
            )
        _require_unique("evaluation input names", (value.name for value in self.inputs))
        _require_unique(
            "evaluation expected output names", (value.name for value in self.expected_outputs)
        )
        if not isinstance(self.expected_status, ExecutionStatus):
            raise ApprenticeshipValidationError("evaluation expected_status is invalid")

    @property
    def case_content_id(self) -> str:
        return canonical_content_id("ccb-t1-case", self)


class BoundedProcedureInterpreter:
    """Interpret a finite straight-line artifact without dynamic code."""

    interpreter_revision = "ccb-t1-bounded-interpreter-v0.1"

    @staticmethod
    def _fraction(value: str) -> Fraction:
        if _INTEGER_OR_RATIONAL.fullmatch(value) is None:
            raise ValueError("value is not a canonical exact number")
        return Fraction(value)

    @staticmethod
    def _fraction_text(value: Fraction) -> str:
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"

    def run(
        self, artifact: CapabilityArtifact, inputs: tuple[NamedValue, ...]
    ) -> ExecutionResult:
        if not isinstance(artifact, CapabilityArtifact):
            raise ApprenticeshipValidationError("interpreter requires CapabilityArtifact")
        _require_tuple("interpreter inputs", inputs)
        if any(not isinstance(value, NamedValue) for value in inputs):
            raise ApprenticeshipValidationError("interpreter inputs contain invalid values")
        input_map = {value.name: value.value for value in inputs}
        if len(input_map) != len(inputs):
            raise ApprenticeshipValidationError("interpreter input names must be unique")
        registers: dict[str, str] = {}
        outputs: dict[str, str] = {}

        def failure(status: ExecutionStatus, reason: str) -> ExecutionResult:
            return ExecutionResult(status, (), reason)

        for instruction in artifact.program:
            operation = instruction.operation
            target = instruction.target
            arguments = instruction.arguments
            if operation is InstructionOp.LOAD_INPUT:
                source_name = arguments[0]
                if source_name not in input_map:
                    return failure(
                        ExecutionStatus.MISSING_INPUT,
                        f"required input {source_name!r} is missing",
                    )
                assert target is not None
                registers[target] = input_map[source_name]
            elif operation is InstructionOp.LOAD_CONSTANT:
                assert target is not None
                registers[target] = arguments[0]
            elif operation in {
                InstructionOp.ADD_EXACT,
                InstructionOp.SUBTRACT_EXACT,
                InstructionOp.MULTIPLY_EXACT,
                InstructionOp.DIVIDE_EXACT,
            }:
                left_name, right_name = arguments
                if left_name not in registers or right_name not in registers:
                    return failure(
                        ExecutionStatus.INVALID_INPUT,
                        "arithmetic instruction references an unloaded register",
                    )
                try:
                    left = self._fraction(registers[left_name])
                    right = self._fraction(registers[right_name])
                except ValueError:
                    return failure(
                        ExecutionStatus.INVALID_INPUT,
                        "exact arithmetic received a non-canonical number",
                    )
                if operation is InstructionOp.ADD_EXACT:
                    result = left + right
                elif operation is InstructionOp.SUBTRACT_EXACT:
                    result = left - right
                elif operation is InstructionOp.MULTIPLY_EXACT:
                    result = left * right
                else:
                    if right == 0:
                        return failure(
                            ExecutionStatus.DIVISION_BY_ZERO,
                            "exact division denominator is zero",
                        )
                    result = left / right
                assert target is not None
                registers[target] = self._fraction_text(result)
            elif operation is InstructionOp.REQUIRE_TRUE:
                input_name = arguments[0]
                if input_name not in input_map:
                    return failure(
                        ExecutionStatus.MISSING_INPUT,
                        f"required permission input {input_name!r} is missing",
                    )
                if input_map[input_name] != "true":
                    return failure(
                        ExecutionStatus.PERMISSION_REQUIRED,
                        "tool procedure cannot pass the explicit permission gate",
                    )
            elif operation is InstructionOp.EMIT_REGISTER:
                register = arguments[0]
                if register not in registers:
                    return failure(
                        ExecutionStatus.INVALID_INPUT,
                        f"output references unloaded register {register!r}",
                    )
                assert target is not None
                outputs[target] = registers[register]
            elif operation is InstructionOp.EMIT_LITERAL:
                assert target is not None
                outputs[target] = arguments[0]
            elif operation is InstructionOp.COPY_INPUT_TO_OUTPUT:
                input_name = arguments[0]
                if input_name not in input_map:
                    return failure(
                        ExecutionStatus.MISSING_INPUT,
                        f"output source input {input_name!r} is missing",
                    )
                assert target is not None
                outputs[target] = input_map[input_name]
            elif operation is InstructionOp.SOURCE_LOOKUP:
                if artifact.kind is not ArtifactKind.SOURCE_LINKED_CLAIM:
                    return failure(
                        ExecutionStatus.UNSUPPORTED_ARTIFACT,
                        "SOURCE_LOOKUP used outside a source-linked artifact",
                    )
                source = artifact.source_claim
                assert source is not None and target is not None
                if source.source_digest != canonical_digest(source._digest_payload()):
                    return failure(
                        ExecutionStatus.SOURCE_BINDING_INVALID,
                        "source-linked claim digest does not match its payload",
                    )
                as_of_name = arguments[0]
                if as_of_name not in input_map:
                    return failure(
                        ExecutionStatus.MISSING_INPUT,
                        f"source query input {as_of_name!r} is missing",
                    )
                try:
                    as_of = date.fromisoformat(input_map[as_of_name])
                except ValueError:
                    return failure(
                        ExecutionStatus.INVALID_INPUT,
                        "source query as_of must be an ISO-8601 date",
                    )
                if not date.fromisoformat(source.valid_from) <= as_of <= date.fromisoformat(
                    source.valid_through
                ):
                    return failure(
                        ExecutionStatus.SOURCE_OUTSIDE_VALIDITY_WINDOW,
                        "source-linked claim is outside its declared validity window",
                    )
                outputs[target] = source.claim_value
        return ExecutionResult(
            ExecutionStatus.SUCCESS,
            tuple(sorted(NamedValue(name, value) for name, value in outputs.items())),
            "bounded deterministic procedure completed",
        )


@dataclass(frozen=True, slots=True)
class CapabilityPrerequisite:
    capability_key: str
    minimum_revision: int

    def __post_init__(self) -> None:
        _require_identifier("prerequisite capability_key", self.capability_key)
        if type(self.minimum_revision) is not int or self.minimum_revision < 1:
            raise ApprenticeshipValidationError(
                "prerequisite minimum_revision must be positive"
            )


@dataclass(frozen=True, slots=True)
class InstalledCapability:
    capability_key: str
    revision: int
    evidence_digest: str
    provenance: str

    def __post_init__(self) -> None:
        _require_identifier("installed capability_key", self.capability_key)
        if type(self.revision) is not int or self.revision < 1:
            raise ApprenticeshipValidationError(
                "installed capability revision must be positive"
            )
        _require_digest("installed capability evidence_digest", self.evidence_digest)
        _require_text("installed capability provenance", self.provenance, limit=512)


@dataclass(frozen=True, slots=True)
class PrerequisiteResult:
    requirement: CapabilityPrerequisite
    observed_revision: int | None
    observed_digest: str | None
    passed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.requirement, CapabilityPrerequisite):
            raise ApprenticeshipValidationError("prerequisite result requirement is invalid")
        if self.observed_revision is not None and (
            type(self.observed_revision) is not int or self.observed_revision < 1
        ):
            raise ApprenticeshipValidationError("observed prerequisite revision is invalid")
        if self.observed_digest is not None:
            _require_digest("observed prerequisite digest", self.observed_digest)
        computed = (
            self.observed_revision is not None
            and self.observed_revision >= self.requirement.minimum_revision
            and self.observed_digest is not None
        )
        if type(self.passed) is not bool or self.passed != computed:
            raise ApprenticeshipValidationError(
                "prerequisite pass flag contradicts observed capability"
            )


@dataclass(frozen=True, slots=True)
class PrerequisiteCheckReceipt:
    proposal_id: str
    registry_digest: str
    checks: tuple[PrerequisiteResult, ...]
    passed: bool

    def __post_init__(self) -> None:
        _require_identifier("prerequisite proposal_id", self.proposal_id)
        _require_digest("prerequisite registry_digest", self.registry_digest)
        _require_tuple("prerequisite checks", self.checks)
        if any(not isinstance(check, PrerequisiteResult) for check in self.checks):
            raise ApprenticeshipValidationError("prerequisite checks contain invalid records")
        computed = all(check.passed for check in self.checks)
        if type(self.passed) is not bool or self.passed != computed:
            raise ApprenticeshipValidationError("prerequisite receipt pass flag is invalid")

    @property
    def receipt_id(self) -> str:
        return canonical_content_id("ccb-t1-prerequisite-receipt", self)


@dataclass(frozen=True, slots=True)
class LessonProposal:
    lesson_id: str
    domain: str
    category: LessonCategory
    transfer_channel: TransferChannel
    teachers: tuple[TeacherAssignment, ...]
    artifact: CapabilityArtifact
    prerequisites: tuple[CapabilityPrerequisite, ...]
    positive_examples: tuple[EvaluationCase, ...]
    negative_examples: tuple[EvaluationCase, ...]
    counterexamples: tuple[EvaluationCase, ...]
    verification_method: str
    accepted_scope: str
    known_exceptions: tuple[str, ...]
    teacher_confidence_basis_points: int
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier("lesson_id", self.lesson_id)
        _require_identifier("lesson domain", self.domain)
        if not isinstance(self.category, LessonCategory):
            raise ApprenticeshipValidationError("lesson category is invalid")
        if not isinstance(self.transfer_channel, TransferChannel):
            raise ApprenticeshipValidationError("transfer channel is invalid")
        _require_tuple("lesson teachers", self.teachers)
        if not self.teachers or any(
            not isinstance(teacher, TeacherAssignment) for teacher in self.teachers
        ):
            raise ApprenticeshipValidationError("lesson requires typed teacher assignments")
        _require_unique("teacher roles", (teacher.role.value for teacher in self.teachers))
        if not isinstance(self.artifact, CapabilityArtifact):
            raise ApprenticeshipValidationError("lesson artifact is invalid")
        _require_tuple("lesson prerequisites", self.prerequisites)
        if any(
            not isinstance(prerequisite, CapabilityPrerequisite)
            for prerequisite in self.prerequisites
        ):
            raise ApprenticeshipValidationError("lesson prerequisites contain invalid records")
        _require_unique(
            "lesson prerequisite capabilities",
            (prerequisite.capability_key for prerequisite in self.prerequisites),
        )
        for name, cases, require_nonempty in (
            ("positive_examples", self.positive_examples, True),
            ("negative_examples", self.negative_examples, False),
            ("counterexamples", self.counterexamples, True),
        ):
            _require_tuple(name, cases)
            if require_nonempty and not cases:
                raise ApprenticeshipValidationError(f"{name} must not be empty")
            if len(cases) > _MAX_CASES or any(
                not isinstance(case, EvaluationCase) for case in cases
            ):
                raise ApprenticeshipValidationError(f"{name} is invalid or too large")
        all_case_ids = tuple(case.case_id for case in self.positive_examples) + tuple(
            case.case_id for case in self.negative_examples
        ) + tuple(case.case_id for case in self.counterexamples)
        _require_unique("teacher example ids", all_case_ids)
        _require_text("verification_method", self.verification_method, limit=512)
        _require_text("accepted_scope", self.accepted_scope, limit=512)
        _require_tuple("known_exceptions", self.known_exceptions)
        for exception in self.known_exceptions:
            _require_text("known exception", exception, limit=512)
        if (
            type(self.teacher_confidence_basis_points) is not int
            or not 0 <= self.teacher_confidence_basis_points <= 10_000
        ):
            raise ApprenticeshipValidationError(
                "teacher_confidence_basis_points must be an integer in [0, 10000]"
            )
        _require_tuple("lesson provenance", self.provenance)
        if not self.provenance:
            raise ApprenticeshipValidationError("lesson provenance must not be empty")
        for item in self.provenance:
            _require_text("lesson provenance item", item, limit=512)
        if (
            self.category is LessonCategory.SOURCE_GROUNDED_FACT
            and self.transfer_channel is not TransferChannel.RETRIEVAL_LINKED_KNOWLEDGE
        ):
            raise ApprenticeshipValidationError(
                "changing facts require the retrieval-linked transfer channel"
            )

    @property
    def proposal_id(self) -> str:
        return canonical_content_id("ccb-t1-proposal", self)

    @property
    def proposal_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class CASSDGExpansion:
    proposal_id: str
    generator: CASSDGIdentity
    independent_seed: str
    transfer_cases: tuple[EvaluationCase, ...]
    adversarial_cases: tuple[EvaluationCase, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier("CAS-SDG proposal_id", self.proposal_id)
        if not isinstance(self.generator, CASSDGIdentity):
            raise ApprenticeshipValidationError("CAS-SDG generator identity is invalid")
        _require_identifier("CAS-SDG independent_seed", self.independent_seed)
        for name, cases in (
            ("CAS-SDG transfer_cases", self.transfer_cases),
            ("CAS-SDG adversarial_cases", self.adversarial_cases),
        ):
            _require_tuple(name, cases)
            if not cases or len(cases) > _MAX_CASES or any(
                not isinstance(case, EvaluationCase) for case in cases
            ):
                raise ApprenticeshipValidationError(f"{name} must contain typed cases")
        _require_unique(
            "CAS-SDG case ids",
            tuple(case.case_id for case in self.transfer_cases)
            + tuple(case.case_id for case in self.adversarial_cases),
        )
        _require_tuple("CAS-SDG provenance", self.provenance)
        if not self.provenance:
            raise ApprenticeshipValidationError("CAS-SDG provenance must not be empty")
        for item in self.provenance:
            _require_text("CAS-SDG provenance item", item, limit=512)

    @property
    def expansion_id(self) -> str:
        return canonical_content_id("ccb-t1-cas-sdg-expansion", self)


@dataclass(frozen=True, slots=True)
class RegressionGuard:
    capability_key: str
    expected_revision: int
    expected_digest: str

    def __post_init__(self) -> None:
        _require_identifier("regression capability_key", self.capability_key)
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise ApprenticeshipValidationError("regression expected_revision must be positive")
        _require_digest("regression expected_digest", self.expected_digest)


@dataclass(frozen=True, slots=True)
class ExaminationSuite:
    suite_id: str
    purpose: SuitePurpose
    examiner: ExaminerIdentity
    custody_seed: str
    held_out_cases: tuple[EvaluationCase, ...]
    counterexamples: tuple[EvaluationCase, ...]
    regression_guards: tuple[RegressionGuard, ...]

    def __post_init__(self) -> None:
        _require_identifier("examination suite_id", self.suite_id)
        if not isinstance(self.purpose, SuitePurpose):
            raise ApprenticeshipValidationError("examination suite purpose is invalid")
        if not isinstance(self.examiner, ExaminerIdentity):
            raise ApprenticeshipValidationError("examination suite examiner is invalid")
        _require_identifier("examination custody_seed", self.custody_seed)
        for name, records, expected_type in (
            ("held_out_cases", self.held_out_cases, EvaluationCase),
            ("counterexamples", self.counterexamples, EvaluationCase),
            ("regression_guards", self.regression_guards, RegressionGuard),
        ):
            _require_tuple(name, records)
            if any(not isinstance(record, expected_type) for record in records):
                raise ApprenticeshipValidationError(f"{name} contains invalid records")
        if not self.held_out_cases:
            raise ApprenticeshipValidationError("every examination requires held-out cases")
        if self.purpose is SuitePurpose.QUALIFICATION and (
            not self.counterexamples or not self.regression_guards
        ):
            raise ApprenticeshipValidationError(
                "qualification requires counterexamples and regression guards"
            )
        if len(self.held_out_cases) + len(self.counterexamples) > _MAX_CASES:
            raise ApprenticeshipValidationError("examination suite contains too many cases")
        _require_unique(
            "examination case ids",
            tuple(case.case_id for case in self.held_out_cases)
            + tuple(case.case_id for case in self.counterexamples),
        )

    @property
    def suite_id_digest(self) -> str:
        return canonical_digest(self)

    @property
    def suite_content_id(self) -> str:
        return canonical_content_id("ccb-t1-examination-suite", self)


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: QualificationGate
    passed: bool
    details: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.gate, QualificationGate) or type(self.passed) is not bool:
            raise ApprenticeshipValidationError("qualification gate record is invalid")
        _require_tuple("gate details", self.details)
        if not self.details:
            raise ApprenticeshipValidationError("gate details must not be empty")
        for detail in self.details:
            _require_text("gate detail", detail, limit=512)


@dataclass(frozen=True, slots=True)
class QualificationReceipt:
    proposal_id: str
    prerequisite_receipt_id: str
    expansion_id: str
    suite_content_id: str
    suite_digest: str
    examiner: ExaminerIdentity
    custody_seed: str
    gates: tuple[GateResult, ...]
    passed: bool
    honest_outcome: HonestOutcome

    def __post_init__(self) -> None:
        for name, value in (
            ("qualification proposal_id", self.proposal_id),
            ("prerequisite_receipt_id", self.prerequisite_receipt_id),
            ("expansion_id", self.expansion_id),
            ("suite_content_id", self.suite_content_id),
        ):
            _require_identifier(name, value)
        _require_digest("qualification suite_digest", self.suite_digest)
        if not isinstance(self.examiner, ExaminerIdentity):
            raise ApprenticeshipValidationError("qualification examiner is invalid")
        _require_identifier("qualification custody_seed", self.custody_seed)
        _require_tuple("qualification gates", self.gates)
        if not self.gates or any(not isinstance(gate, GateResult) for gate in self.gates):
            raise ApprenticeshipValidationError("qualification gates contain invalid records")
        if tuple(gate.gate for gate in self.gates) != _QUALIFICATION_LADDER[: len(self.gates)]:
            raise ApprenticeshipValidationError("qualification gates are not a ladder prefix")
        computed_pass = len(self.gates) == len(_QUALIFICATION_LADDER) and all(
            gate.passed for gate in self.gates
        )
        if type(self.passed) is not bool or self.passed != computed_pass:
            raise ApprenticeshipValidationError("qualification pass flag contradicts gates")
        if not isinstance(self.honest_outcome, HonestOutcome):
            raise ApprenticeshipValidationError("qualification honest_outcome is invalid")
        if self.passed and self.honest_outcome is not HonestOutcome.PROVISIONAL_LOCAL_ONLY:
            raise ApprenticeshipValidationError("passing qualification must remain provisional")

    @property
    def receipt_id(self) -> str:
        return canonical_content_id("ccb-t1-qualification-receipt", self)


@dataclass(frozen=True, slots=True)
class RetentionReceipt:
    proposal_id: str
    qualification_receipt_id: str
    suite_content_id: str
    suite_digest: str
    examiner: ExaminerIdentity
    custody_seed: str
    gate: GateResult
    passed: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("retention proposal_id", self.proposal_id),
            ("qualification_receipt_id", self.qualification_receipt_id),
            ("retention suite_content_id", self.suite_content_id),
        ):
            _require_identifier(name, value)
        _require_digest("retention suite_digest", self.suite_digest)
        if not isinstance(self.examiner, ExaminerIdentity):
            raise ApprenticeshipValidationError("retention examiner is invalid")
        _require_identifier("retention custody_seed", self.custody_seed)
        if (
            not isinstance(self.gate, GateResult)
            or self.gate.gate is not QualificationGate.DELAYED_RETENTION_PASS
        ):
            raise ApprenticeshipValidationError(
                "retention receipt requires DELAYED_RETENTION_PASS"
            )
        if type(self.passed) is not bool or self.passed != self.gate.passed:
            raise ApprenticeshipValidationError("retention pass flag contradicts gate")

    @property
    def receipt_id(self) -> str:
        return canonical_content_id("ccb-t1-retention-receipt", self)


@dataclass(frozen=True, slots=True)
class CapabilityMetrics:
    p_cap_milliunits: int
    r_cap_milliunits: int
    i_attention_milliunits: int
    effect: EffectStatus

    def __post_init__(self) -> None:
        for name, value in (
            ("p_cap_milliunits", self.p_cap_milliunits),
            ("r_cap_milliunits", self.r_cap_milliunits),
            ("i_attention_milliunits", self.i_attention_milliunits),
        ):
            if type(value) is not int or not 0 <= value <= 1_000_000:
                raise ApprenticeshipValidationError(
                    f"{name} must be an integer in [0, 1000000]"
                )
        if not isinstance(self.effect, EffectStatus):
            raise ApprenticeshipValidationError("capability effect is invalid")


@dataclass(frozen=True, slots=True)
class CASOhmObservation:
    probe_id: str
    before: CapabilityMetrics
    after: CapabilityMetrics
    learning_gain_milliunits: int
    resistance_reduction_milliunits: int
    attention_change_milliunits: int
    observational_only: bool = True
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        _require_identifier("CAS-Ohm probe_id", self.probe_id)
        if not isinstance(self.before, CapabilityMetrics) or not isinstance(
            self.after, CapabilityMetrics
        ):
            raise ApprenticeshipValidationError("CAS-Ohm metrics are invalid")
        if self.learning_gain_milliunits != (
            self.after.p_cap_milliunits - self.before.p_cap_milliunits
        ):
            raise ApprenticeshipValidationError("CAS-Ohm learning gain is inconsistent")
        if self.resistance_reduction_milliunits != (
            self.before.r_cap_milliunits - self.after.r_cap_milliunits
        ):
            raise ApprenticeshipValidationError("CAS-Ohm resistance reduction is inconsistent")
        if self.attention_change_milliunits != (
            self.after.i_attention_milliunits - self.before.i_attention_milliunits
        ):
            raise ApprenticeshipValidationError("CAS-Ohm attention change is inconsistent")
        if self.observational_only is not True or self.promotion_authority is not False:
            raise ApprenticeshipValidationError(
                "CAS-Ohm observations must be non-authoritative"
            )

    @classmethod
    def create(
        cls,
        probe_id: str,
        before: CapabilityMetrics,
        after: CapabilityMetrics,
    ) -> "CASOhmObservation":
        return cls(
            probe_id=probe_id,
            before=before,
            after=after,
            learning_gain_milliunits=(
                after.p_cap_milliunits - before.p_cap_milliunits
            ),
            resistance_reduction_milliunits=(
                before.r_cap_milliunits - after.r_cap_milliunits
            ),
            attention_change_milliunits=(
                after.i_attention_milliunits - before.i_attention_milliunits
            ),
        )

    @property
    def observation_id(self) -> str:
        return canonical_content_id("ccb-t1-cas-ohm-observation", self)


@dataclass(frozen=True, slots=True)
class TeachingEpisode:
    episode_id: str
    proposal: LessonProposal
    status: EpisodeStatus
    honest_outcome: HonestOutcome
    logical_revision: int
    prerequisite_receipt_id: str | None = None
    cas_sdg_expansion_id: str | None = None
    qualification_receipt_id: str | None = None
    retention_receipt_id: str | None = None
    local_version_id: str | None = None
    rollback_pointer: str | None = None
    cas_ohm_observation: CASOhmObservation | None = None
    reason: str = "foreign lesson proposal recorded without local commitment"

    def __post_init__(self) -> None:
        _require_identifier("teaching episode_id", self.episode_id)
        if not isinstance(self.proposal, LessonProposal):
            raise ApprenticeshipValidationError("teaching episode proposal is invalid")
        if self.episode_id != canonical_content_id(
            "ccb-t1-teaching-episode", self.proposal.proposal_id
        ):
            raise ApprenticeshipValidationError("teaching episode_id is not canonical")
        if not isinstance(self.status, EpisodeStatus):
            raise ApprenticeshipValidationError("teaching episode status is invalid")
        if not isinstance(self.honest_outcome, HonestOutcome):
            raise ApprenticeshipValidationError("teaching episode outcome is invalid")
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise ApprenticeshipValidationError("teaching episode revision must be positive")
        for name, value in (
            ("prerequisite_receipt_id", self.prerequisite_receipt_id),
            ("cas_sdg_expansion_id", self.cas_sdg_expansion_id),
            ("qualification_receipt_id", self.qualification_receipt_id),
            ("retention_receipt_id", self.retention_receipt_id),
            ("local_version_id", self.local_version_id),
            ("rollback_pointer", self.rollback_pointer),
        ):
            if value is not None:
                _require_identifier(name, value)
        if self.cas_ohm_observation is not None and not isinstance(
            self.cas_ohm_observation, CASOhmObservation
        ):
            raise ApprenticeshipValidationError("teaching episode CAS-Ohm record is invalid")
        _require_text("teaching episode reason", self.reason, limit=512)

    @property
    def episode_record_id(self) -> str:
        return canonical_content_id("ccb-t1-episode-record", self)


@dataclass(frozen=True, slots=True)
class CapabilityVersion:
    version_id: str
    proposal_id: str
    artifact: CapabilityArtifact
    status: VersionStatus
    logical_revision: int
    qualification_receipt_id: str
    retention_receipt_id: str | None = None
    parent_version_id: str | None = None
    reason: str = "local receipt-gated provisional version"

    def __post_init__(self) -> None:
        for name, value in (
            ("capability version_id", self.version_id),
            ("capability proposal_id", self.proposal_id),
            ("capability qualification_receipt_id", self.qualification_receipt_id),
        ):
            _require_identifier(name, value)
        if not isinstance(self.artifact, CapabilityArtifact):
            raise ApprenticeshipValidationError("capability version artifact is invalid")
        expected = canonical_content_id(
            "ccb-t1-capability-version",
            {
                "proposal_id": self.proposal_id,
                "artifact_content_id": self.artifact.artifact_content_id,
            },
        )
        if self.version_id != expected:
            raise ApprenticeshipValidationError("capability version_id is not canonical")
        if not isinstance(self.status, VersionStatus):
            raise ApprenticeshipValidationError("capability version status is invalid")
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise ApprenticeshipValidationError("capability version revision must be positive")
        if self.retention_receipt_id is not None:
            _require_identifier("capability retention_receipt_id", self.retention_receipt_id)
        if self.parent_version_id is not None:
            _require_identifier("capability parent_version_id", self.parent_version_id)
        if (
            self.status is VersionStatus.ACTIVE_LOCAL
            and self.retention_receipt_id is None
        ):
            raise ApprenticeshipValidationError(
                "active local capabilities require delayed-retention evidence"
            )
        _require_text("capability version reason", self.reason, limit=512)

    @property
    def version_record_id(self) -> str:
        return canonical_content_id("ccb-t1-capability-version-record", self)


@dataclass(frozen=True, slots=True)
class EpisodeLineageEvent:
    logical_revision: int
    action: str
    target_id: str
    previous_state: str | None
    new_state: str
    reason: str

    def __post_init__(self) -> None:
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise ApprenticeshipValidationError("lineage revision must be positive")
        _require_identifier("lineage action", self.action)
        _require_identifier("lineage target_id", self.target_id)
        if self.previous_state is not None:
            _require_identifier("lineage previous_state", self.previous_state)
        _require_identifier("lineage new_state", self.new_state)
        _require_text("lineage reason", self.reason, limit=512)

    @property
    def event_id(self) -> str:
        return canonical_content_id("ccb-t1-lineage", self)


@dataclass(frozen=True, slots=True)
class ApprenticeshipStoreSnapshot:
    logical_revision: int
    episodes: tuple[TeachingEpisode, ...]
    versions: tuple[CapabilityVersion, ...]
    lineage: tuple[EpisodeLineageEvent, ...]

    @property
    def snapshot_digest(self) -> str:
        return canonical_digest(self)


class VersionedTeachingStore:
    """Append-only local TeachingEpisode and capability-version histories."""

    def __init__(self) -> None:
        self._logical_revision = 0
        self._episode_history: dict[str, list[TeachingEpisode]] = {}
        self._proposal_episode: dict[str, str] = {}
        self._version_history: dict[str, list[CapabilityVersion]] = {}
        self._proposal_version: dict[str, str] = {}
        self._lineage: list[EpisodeLineageEvent] = []

    def _next_revision(self) -> int:
        self._logical_revision += 1
        return self._logical_revision

    def _record_event(
        self,
        revision: int,
        action: str,
        target_id: str,
        previous_state: str | None,
        new_state: str,
        reason: str,
    ) -> None:
        self._lineage.append(
            EpisodeLineageEvent(
                revision,
                action,
                target_id,
                previous_state,
                new_state,
                reason,
            )
        )

    def submit(self, proposal: LessonProposal) -> TeachingEpisode:
        if not isinstance(proposal, LessonProposal):
            raise ApprenticeshipValidationError("only LessonProposal may be submitted")
        existing_id = self._proposal_episode.get(proposal.proposal_id)
        if existing_id is not None:
            return self._episode_history[existing_id][-1]
        episode_id = canonical_content_id("ccb-t1-teaching-episode", proposal.proposal_id)
        revision = self._next_revision()
        episode = TeachingEpisode(
            episode_id=episode_id,
            proposal=proposal,
            status=EpisodeStatus.PROPOSED,
            honest_outcome=HonestOutcome.PROPOSAL_RECORDED_ONLY,
            logical_revision=revision,
        )
        self._proposal_episode[proposal.proposal_id] = episode_id
        self._episode_history[episode_id] = [episode]
        self._record_event(
            revision,
            "CCB_T1_TEACHER_PROPOSAL_RECORDED",
            episode_id,
            None,
            episode.status.value,
            episode.reason,
        )
        return episode

    def episode_for_proposal(self, proposal_id: str) -> TeachingEpisode:
        try:
            episode_id = self._proposal_episode[proposal_id]
            return self._episode_history[episode_id][-1]
        except KeyError as exc:
            raise ApprenticeshipLifecycleError(f"unknown proposal: {proposal_id}") from exc

    def episode_history(self, episode_id: str) -> tuple[TeachingEpisode, ...]:
        try:
            return tuple(self._episode_history[episode_id])
        except KeyError as exc:
            raise ApprenticeshipLifecycleError(f"unknown episode: {episode_id}") from exc

    def _transition_episode(
        self,
        proposal_id: str,
        status: EpisodeStatus,
        outcome: HonestOutcome,
        reason: str,
        **updates: object,
    ) -> TeachingEpisode:
        prior = self.episode_for_proposal(proposal_id)
        revision = self._next_revision()
        episode = replace(
            prior,
            status=status,
            honest_outcome=outcome,
            logical_revision=revision,
            reason=reason,
            **updates,
        )
        self._episode_history[prior.episode_id].append(episode)
        self._record_event(
            revision,
            f"CCB_T1_EPISODE_{status.name}",
            prior.episode_id,
            prior.status.value,
            status.value,
            reason,
        )
        return episode

    def _create_provisional(
        self, proposal_id: str, qualification_receipt_id: str
    ) -> CapabilityVersion:
        episode = self.episode_for_proposal(proposal_id)
        artifact = episode.proposal.artifact
        version_id = canonical_content_id(
            "ccb-t1-capability-version",
            {
                "proposal_id": proposal_id,
                "artifact_content_id": artifact.artifact_content_id,
            },
        )
        if version_id in self._version_history:
            return self._version_history[version_id][-1]
        revision = self._next_revision()
        version = CapabilityVersion(
            version_id=version_id,
            proposal_id=proposal_id,
            artifact=artifact,
            status=VersionStatus.PROVISIONAL_LOCAL,
            logical_revision=revision,
            qualification_receipt_id=qualification_receipt_id,
        )
        self._version_history[version_id] = [version]
        self._proposal_version[proposal_id] = version_id
        self._record_event(
            revision,
            "CCB_T1_CAPABILITY_PROVISIONAL_LOCAL",
            version_id,
            None,
            version.status.value,
            version.reason,
        )
        return version

    def version(self, version_id: str) -> CapabilityVersion:
        try:
            return self._version_history[version_id][-1]
        except KeyError as exc:
            raise ApprenticeshipLifecycleError(
                f"unknown capability version: {version_id}"
            ) from exc

    def version_for_proposal(self, proposal_id: str) -> CapabilityVersion:
        try:
            return self.version(self._proposal_version[proposal_id])
        except KeyError as exc:
            raise ApprenticeshipLifecycleError(
                f"proposal has no local capability version: {proposal_id}"
            ) from exc

    def version_history(self, version_id: str) -> tuple[CapabilityVersion, ...]:
        try:
            return tuple(self._version_history[version_id])
        except KeyError as exc:
            raise ApprenticeshipLifecycleError(
                f"unknown capability version: {version_id}"
            ) from exc

    def _transition_version(
        self,
        version_id: str,
        status: VersionStatus,
        reason: str,
        *,
        retention_receipt_id: str | None = None,
        parent_version_id: str | None = None,
    ) -> CapabilityVersion:
        prior = self.version(version_id)
        revision = self._next_revision()
        version = replace(
            prior,
            status=status,
            logical_revision=revision,
            reason=reason,
            retention_receipt_id=(
                retention_receipt_id
                if retention_receipt_id is not None
                else prior.retention_receipt_id
            ),
            parent_version_id=(
                parent_version_id if parent_version_id is not None else prior.parent_version_id
            ),
        )
        self._version_history[version_id].append(version)
        self._record_event(
            revision,
            f"CCB_T1_VERSION_{status.name}",
            version_id,
            prior.status.value,
            status.value,
            reason,
        )
        return version

    def active_versions(self) -> tuple[CapabilityVersion, ...]:
        return tuple(
            sorted(
                (
                    history[-1]
                    for history in self._version_history.values()
                    if history[-1].status is VersionStatus.ACTIVE_LOCAL
                ),
                key=lambda version: version.version_id,
            )
        )

    def provisional_versions(self) -> tuple[CapabilityVersion, ...]:
        return tuple(
            sorted(
                (
                    history[-1]
                    for history in self._version_history.values()
                    if history[-1].status is VersionStatus.PROVISIONAL_LOCAL
                ),
                key=lambda version: version.version_id,
            )
        )

    def snapshot(self) -> ApprenticeshipStoreSnapshot:
        episodes = tuple(
            sorted(
                (history[-1] for history in self._episode_history.values()),
                key=lambda episode: episode.episode_id,
            )
        )
        versions = tuple(
            sorted(
                (history[-1] for history in self._version_history.values()),
                key=lambda version: version.version_id,
            )
        )
        return ApprenticeshipStoreSnapshot(
            self._logical_revision,
            episodes,
            versions,
            tuple(self._lineage),
        )


class CognitiveApprenticeship:
    """Local CCB-T1 orchestration with no CNCM or CAS-RRK write path."""

    def __init__(self, installed_capabilities: tuple[InstalledCapability, ...]) -> None:
        _require_tuple("installed_capabilities", installed_capabilities)
        if any(
            not isinstance(capability, InstalledCapability)
            for capability in installed_capabilities
        ):
            raise ApprenticeshipValidationError(
                "installed_capabilities must contain InstalledCapability values"
            )
        _require_unique(
            "installed capability keys",
            (capability.capability_key for capability in installed_capabilities),
        )
        self._installed = {
            capability.capability_key: capability for capability in installed_capabilities
        }
        self.interpreter = BoundedProcedureInterpreter()
        self.store = VersionedTeachingStore()
        self._prerequisite_receipts: dict[str, PrerequisiteCheckReceipt] = {}
        self._expansions: dict[str, CASSDGExpansion] = {}
        self._qualification_receipts: dict[str, QualificationReceipt] = {}
        self._retention_receipts: dict[str, RetentionReceipt] = {}

    @property
    def installed_registry_digest(self) -> str:
        return canonical_digest(
            tuple(sorted(self._installed.values(), key=lambda value: value.capability_key))
        )

    @property
    def active_local_digest(self) -> str:
        return canonical_digest(
            tuple(
                version.artifact.artifact_content_id
                for version in self.store.active_versions()
            )
        )

    def submit_teacher_proposal(self, proposal: LessonProposal) -> TeachingEpisode:
        """Record a foreign proposal without creating a local capability version."""

        return self.store.submit(proposal)

    def _resolved_capability(
        self, capability_key: str
    ) -> tuple[int, str] | None:
        active = tuple(
            version
            for version in self.store.active_versions()
            if version.artifact.capability_key == capability_key
        )
        if active:
            selected = max(active, key=lambda version: version.artifact.revision)
            return selected.artifact.revision, selected.artifact.artifact_digest
        installed = self._installed.get(capability_key)
        if installed is None:
            return None
        return installed.revision, installed.evidence_digest

    def check_prerequisites(self, proposal_id: str) -> PrerequisiteCheckReceipt:
        episode = self.store.episode_for_proposal(proposal_id)
        checks: list[PrerequisiteResult] = []
        for requirement in episode.proposal.prerequisites:
            observed = self._resolved_capability(requirement.capability_key)
            checks.append(
                PrerequisiteResult(
                    requirement=requirement,
                    observed_revision=observed[0] if observed is not None else None,
                    observed_digest=observed[1] if observed is not None else None,
                    passed=(
                        observed is not None
                        and observed[0] >= requirement.minimum_revision
                    ),
                )
            )
        receipt = PrerequisiteCheckReceipt(
            proposal_id=proposal_id,
            registry_digest=canonical_digest(
                {
                    "installed": self.installed_registry_digest,
                    "active_local": self.active_local_digest,
                }
            ),
            checks=tuple(checks),
            passed=all(check.passed for check in checks),
        )
        self._prerequisite_receipts[receipt.receipt_id] = receipt
        if not receipt.passed:
            missing = tuple(
                check.requirement.capability_key for check in checks if not check.passed
            )
            self.store._transition_episode(
                proposal_id,
                EpisodeStatus.PREREQUISITE_BLOCKED,
                HonestOutcome.MISSING_PREREQUISITE,
                f"missing or insufficient prerequisites: {missing}",
                prerequisite_receipt_id=receipt.receipt_id,
            )
        return receipt

    @staticmethod
    def _teacher_principals(proposal: LessonProposal) -> frozenset[tuple[str, str]]:
        return frozenset(
            (assignment.teacher.principal, assignment.teacher.revision)
            for assignment in proposal.teachers
        )

    def register_cas_sdg_expansion(self, expansion: CASSDGExpansion) -> str:
        episode = self.store.episode_for_proposal(expansion.proposal_id)
        proposal = episode.proposal
        if (expansion.generator.generator, expansion.generator.revision) in (
            self._teacher_principals(proposal)
        ):
            raise ApprenticeshipQualificationError(
                "CAS-SDG expansion identity must be separate from teacher identities"
            )
        teacher_case_ids = {
            case.case_id
            for cases in (
                proposal.positive_examples,
                proposal.negative_examples,
                proposal.counterexamples,
            )
            for case in cases
        }
        expansion_case_ids = {
            case.case_id
            for cases in (expansion.transfer_cases, expansion.adversarial_cases)
            for case in cases
        }
        if teacher_case_ids.intersection(expansion_case_ids):
            raise ApprenticeshipQualificationError(
                "CAS-SDG cases must not reuse teacher case identifiers"
            )
        self._expansions[expansion.expansion_id] = expansion
        return expansion.expansion_id

    @staticmethod
    def _case_failure(
        interpreter: BoundedProcedureInterpreter,
        artifact: CapabilityArtifact,
        case: EvaluationCase,
    ) -> str | None:
        result = interpreter.run(artifact, case.inputs)
        if result.status is not case.expected_status:
            return (
                f"{case.case_id}: expected {case.expected_status.value}, "
                f"got {result.status.value}"
            )
        if result.outputs != case.expected_outputs:
            return f"{case.case_id}: output mismatch"
        return None

    def _regression_failures(
        self, guards: tuple[RegressionGuard, ...]
    ) -> tuple[str, ...]:
        failures: list[str] = []
        for guard in guards:
            observed = self._resolved_capability(guard.capability_key)
            if observed is None:
                failures.append(f"{guard.capability_key}: capability missing")
            elif observed != (guard.expected_revision, guard.expected_digest):
                failures.append(f"{guard.capability_key}: revision or digest changed")
        return tuple(failures)

    def qualify(
        self,
        proposal_id: str,
        prerequisite_receipt_id: str,
        expansion_id: str,
        suite: ExaminationSuite,
    ) -> QualificationReceipt:
        episode = self.store.episode_for_proposal(proposal_id)
        proposal = episode.proposal
        if episode.status is not EpisodeStatus.PROPOSED:
            raise ApprenticeshipQualificationError(
                f"episode must be PROPOSED, not {episode.status.value}"
            )
        try:
            prerequisites = self._prerequisite_receipts[prerequisite_receipt_id]
            expansion = self._expansions[expansion_id]
        except KeyError as exc:
            raise ApprenticeshipQualificationError(
                "qualification requires locally recorded prerequisite and CAS-SDG evidence"
            ) from exc
        if prerequisites.proposal_id != proposal_id or expansion.proposal_id != proposal_id:
            raise ApprenticeshipQualificationError("evidence does not bind this proposal")
        if suite.purpose is not SuitePurpose.QUALIFICATION:
            raise ApprenticeshipQualificationError(
                "qualification requires a QUALIFICATION suite"
            )
        teacher_principals = self._teacher_principals(proposal)
        if (suite.examiner.principal, suite.examiner.revision) in teacher_principals:
            raise ApprenticeshipQualificationError(
                "a teacher cannot hold examiner custody for its own lesson"
            )
        if (
            suite.examiner.principal == expansion.generator.generator
            and suite.examiner.revision == expansion.generator.revision
        ):
            raise ApprenticeshipQualificationError(
                "CAS-SDG generator cannot also hold protected examiner custody"
            )
        prior_case_ids = {
            case.case_id
            for cases in (
                proposal.positive_examples,
                proposal.negative_examples,
                proposal.counterexamples,
                expansion.transfer_cases,
                expansion.adversarial_cases,
            )
            for case in cases
        }
        examination_case_ids = {
            case.case_id
            for cases in (suite.held_out_cases, suite.counterexamples)
            for case in cases
        }
        if prior_case_ids.intersection(examination_case_ids):
            raise ApprenticeshipQualificationError(
                "protected examination cases must be held out from teachers and CAS-SDG"
            )
        gates: list[GateResult] = []

        def gate(
            name: QualificationGate,
            failures: tuple[str, ...],
            success: str,
        ) -> bool:
            result = GateResult(name, not failures, failures or (success,))
            gates.append(result)
            return result.passed

        gate(
            QualificationGate.PROPOSAL_ISOLATED,
            (),
            "teacher proposal remains outside the active local capability store",
        )
        if not gate(
            QualificationGate.PREREQUISITES_PASS,
            () if prerequisites.passed else ("prerequisite receipt did not pass",),
            "all typed prerequisites are present at sufficient revisions",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        protected = proposal.category in PROTECTED_LESSON_CATEGORIES
        if not gate(
            QualificationGate.PROTECTED_CATEGORY_ALLOWED,
            (
                (
                    f"{proposal.category.value} cannot receive autonomous or local "
                    "CCB-T1 promotion"
                ),
            )
            if protected
            else (),
            "lesson category is eligible for isolated local qualification",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        artifact_failures: tuple[str, ...] = ()
        if (
            proposal.category is LessonCategory.SOURCE_GROUNDED_FACT
            and proposal.artifact.kind is not ArtifactKind.SOURCE_LINKED_CLAIM
        ):
            artifact_failures = (
                "source-grounded changing fact lacks a source-linked artifact",
            )
        if not gate(
            QualificationGate.ARTIFACT_VALID,
            artifact_failures,
            "typed bounded artifact is valid",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        teacher_failures = tuple(
            failure
            for failure in (
                self._case_failure(self.interpreter, proposal.artifact, case)
                for case in (
                    proposal.positive_examples
                    + proposal.negative_examples
                    + proposal.counterexamples
                )
            )
            if failure is not None
        )
        if not gate(
            QualificationGate.TEACHER_EXAMPLES_PASS,
            teacher_failures,
            "teacher examples were reproduced but grant no authority",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        sdg_failures = tuple(
            failure
            for failure in (
                self._case_failure(self.interpreter, proposal.artifact, case)
                for case in expansion.transfer_cases + expansion.adversarial_cases
            )
            if failure is not None
        )
        if not gate(
            QualificationGate.CAS_SDG_EXPANSION_PASS,
            sdg_failures,
            "independently identified CAS-SDG variants passed",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        held_out_failures = tuple(
            failure
            for failure in (
                self._case_failure(self.interpreter, proposal.artifact, case)
                for case in suite.held_out_cases
            )
            if failure is not None
        )
        if not gate(
            QualificationGate.HELD_OUT_TRANSFER_PASS,
            held_out_failures,
            "protected held-out transfer cases passed",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        counterexample_failures = tuple(
            failure
            for failure in (
                self._case_failure(self.interpreter, proposal.artifact, case)
                for case in suite.counterexamples
            )
            if failure is not None
        )
        if not gate(
            QualificationGate.COUNTEREXAMPLES_PASS,
            counterexample_failures,
            "protected counterexamples produced honest bounded outcomes",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        regression_failures = self._regression_failures(suite.regression_guards)
        if not gate(
            QualificationGate.REGRESSION_PASS,
            regression_failures,
            "protected capability revision and digest sentinels remained unchanged",
        ):
            return self._seal_qualification(
                proposal, prerequisites, expansion, suite, tuple(gates)
            )
        replay_failures: list[str] = []
        for case in suite.held_out_cases:
            first = self.interpreter.run(proposal.artifact, case.inputs)
            second = self.interpreter.run(proposal.artifact, case.inputs)
            if canonical_digest(first) != canonical_digest(second):
                replay_failures.append(f"{case.case_id}: replay digest changed")
        gate(
            QualificationGate.DETERMINISTIC_REPLAY_PASS,
            tuple(replay_failures),
            "canonical replay digests are identical",
        )
        return self._seal_qualification(
            proposal, prerequisites, expansion, suite, tuple(gates)
        )

    def _seal_qualification(
        self,
        proposal: LessonProposal,
        prerequisites: PrerequisiteCheckReceipt,
        expansion: CASSDGExpansion,
        suite: ExaminationSuite,
        gates: tuple[GateResult, ...],
    ) -> QualificationReceipt:
        passed = len(gates) == len(_QUALIFICATION_LADDER) and all(
            gate.passed for gate in gates
        )
        if passed:
            outcome = HonestOutcome.PROVISIONAL_LOCAL_ONLY
            status = EpisodeStatus.QUALIFIED
        elif proposal.category in PROTECTED_LESSON_CATEGORIES:
            outcome = HonestOutcome.PROTECTED_REQUIRES_SEPARATE_AUTHORITY
            status = EpisodeStatus.PROTECTED_REJECTED
        elif not prerequisites.passed:
            outcome = HonestOutcome.MISSING_PREREQUISITE
            status = EpisodeStatus.PREREQUISITE_BLOCKED
        else:
            outcome = HonestOutcome.QUALIFICATION_FAILED
            status = EpisodeStatus.QUARANTINED
        receipt = QualificationReceipt(
            proposal_id=proposal.proposal_id,
            prerequisite_receipt_id=prerequisites.receipt_id,
            expansion_id=expansion.expansion_id,
            suite_content_id=suite.suite_content_id,
            suite_digest=suite.suite_id_digest,
            examiner=suite.examiner,
            custody_seed=suite.custody_seed,
            gates=gates,
            passed=passed,
            honest_outcome=outcome,
        )
        self._qualification_receipts[receipt.receipt_id] = receipt
        self.store._transition_episode(
            proposal.proposal_id,
            status,
            outcome,
            (
                "independent qualification passed for local provisional use"
                if passed
                else gates[-1].details[0]
            ),
            prerequisite_receipt_id=prerequisites.receipt_id,
            cas_sdg_expansion_id=expansion.expansion_id,
            qualification_receipt_id=receipt.receipt_id,
        )
        return receipt

    def promote_provisionally(
        self, proposal_id: str, qualification_receipt_id: str
    ) -> CapabilityVersion:
        episode = self.store.episode_for_proposal(proposal_id)
        if episode.proposal.category in PROTECTED_LESSON_CATEGORIES:
            raise ApprenticeshipPromotionError(
                "protected categories can never autonomously promote"
            )
        try:
            receipt = self._qualification_receipts[qualification_receipt_id]
        except KeyError as exc:
            raise ApprenticeshipPromotionError(
                "qualification receipt was not issued by this CCB-T1 laboratory"
            ) from exc
        if not receipt.passed or receipt.proposal_id != proposal_id:
            raise ApprenticeshipPromotionError(
                "qualification receipt does not authorize this proposal"
            )
        if episode.status is not EpisodeStatus.QUALIFIED:
            raise ApprenticeshipPromotionError(
                f"episode is {episode.status.value}, not QUALIFIED"
            )
        version = self.store._create_provisional(proposal_id, qualification_receipt_id)
        self.store._transition_episode(
            proposal_id,
            EpisodeStatus.PROVISIONAL_LOCAL,
            HonestOutcome.PROVISIONAL_LOCAL_ONLY,
            "local qualification permits shadow-only provisional capability",
            local_version_id=version.version_id,
        )
        return version

    def evaluate_delayed_retention(
        self,
        proposal_id: str,
        qualification_receipt_id: str,
        suite: ExaminationSuite,
    ) -> RetentionReceipt:
        episode = self.store.episode_for_proposal(proposal_id)
        if episode.status is not EpisodeStatus.PROVISIONAL_LOCAL:
            raise ApprenticeshipQualificationError(
                "delayed retention requires a local provisional episode"
            )
        try:
            qualification = self._qualification_receipts[qualification_receipt_id]
        except KeyError as exc:
            raise ApprenticeshipQualificationError(
                "unknown local qualification receipt"
            ) from exc
        if not qualification.passed or qualification.proposal_id != proposal_id:
            raise ApprenticeshipQualificationError(
                "qualification receipt does not bind this proposal"
            )
        if suite.purpose is not SuitePurpose.DELAYED_RETENTION:
            raise ApprenticeshipQualificationError(
                "retention requires a DELAYED_RETENTION suite"
            )
        if suite.custody_seed == qualification.custody_seed:
            raise ApprenticeshipQualificationError(
                "retention requires a fresh protected custody seed"
            )
        if (
            suite.examiner.principal,
            suite.examiner.revision,
        ) in self._teacher_principals(episode.proposal):
            raise ApprenticeshipQualificationError(
                "a teacher cannot hold delayed-retention custody"
            )
        failures = tuple(
            failure
            for failure in (
                self._case_failure(self.interpreter, episode.proposal.artifact, case)
                for case in suite.held_out_cases + suite.counterexamples
            )
            if failure is not None
        ) + self._regression_failures(suite.regression_guards)
        gate = GateResult(
            QualificationGate.DELAYED_RETENTION_PASS,
            not failures,
            failures or ("fresh delayed-retention and regression cases passed",),
        )
        receipt = RetentionReceipt(
            proposal_id=proposal_id,
            qualification_receipt_id=qualification_receipt_id,
            suite_content_id=suite.suite_content_id,
            suite_digest=suite.suite_id_digest,
            examiner=suite.examiner,
            custody_seed=suite.custody_seed,
            gate=gate,
            passed=gate.passed,
        )
        self._retention_receipts[receipt.receipt_id] = receipt
        if not receipt.passed:
            version = self.store.version_for_proposal(proposal_id)
            self.store._transition_version(
                version.version_id,
                VersionStatus.ROLLED_BACK,
                "delayed retention failed; provisional capability rolled back",
                retention_receipt_id=receipt.receipt_id,
            )
            self.store._transition_episode(
                proposal_id,
                EpisodeStatus.ROLLED_BACK,
                HonestOutcome.RETENTION_FAILED_ROLLED_BACK,
                "delayed retention failed; no local active capability remains",
                retention_receipt_id=receipt.receipt_id,
                rollback_pointer=version.parent_version_id,
            )
        return receipt

    def promote_durably(
        self,
        proposal_id: str,
        qualification_receipt_id: str,
        retention_receipt_id: str,
        *,
        parent_version_id: str | None = None,
    ) -> CapabilityVersion:
        episode = self.store.episode_for_proposal(proposal_id)
        if episode.proposal.category in PROTECTED_LESSON_CATEGORIES:
            raise ApprenticeshipPromotionError(
                "protected categories can never autonomously promote"
            )
        if episode.status is not EpisodeStatus.PROVISIONAL_LOCAL:
            raise ApprenticeshipPromotionError(
                "durable local promotion requires a provisional episode"
            )
        try:
            qualification = self._qualification_receipts[qualification_receipt_id]
            retention = self._retention_receipts[retention_receipt_id]
        except KeyError as exc:
            raise ApprenticeshipPromotionError(
                "promotion receipts were not issued by this CCB-T1 laboratory"
            ) from exc
        if (
            not qualification.passed
            or not retention.passed
            or qualification.proposal_id != proposal_id
            or retention.proposal_id != proposal_id
            or retention.qualification_receipt_id != qualification_receipt_id
        ):
            raise ApprenticeshipPromotionError(
                "receipts do not authorize durable local promotion"
            )
        version = self.store.version_for_proposal(proposal_id)
        same_key = tuple(
            active
            for active in self.store.active_versions()
            if active.artifact.capability_key == episode.proposal.artifact.capability_key
        )
        parent: CapabilityVersion | None = None
        if parent_version_id is not None:
            parent = self.store.version(parent_version_id)
            if parent.status is not VersionStatus.ACTIVE_LOCAL:
                raise ApprenticeshipPromotionError("parent version is not active locally")
            if parent.artifact.capability_key != episode.proposal.artifact.capability_key:
                raise ApprenticeshipPromotionError(
                    "only revisions of the same capability may supersede"
                )
            if any(active.version_id != parent.version_id for active in same_key):
                raise ApprenticeshipPromotionError(
                    "another active local version has the same capability key"
                )
        elif same_key:
            raise ApprenticeshipPromotionError(
                "existing active local capability must be explicitly named as parent"
            )
        active = self.store._transition_version(
            version.version_id,
            VersionStatus.ACTIVE_LOCAL,
            "independent transfer, regression, and retention receipts passed locally",
            retention_receipt_id=retention_receipt_id,
            parent_version_id=parent_version_id,
        )
        if parent is not None:
            self.store._transition_version(
                parent.version_id,
                VersionStatus.SUPERSEDED,
                f"superseded locally by {active.version_id}",
            )
            self.store._transition_episode(
                parent.proposal_id,
                EpisodeStatus.SUPERSEDED,
                HonestOutcome.DURABLE_LOCAL_ONLY,
                f"local capability superseded by {active.version_id}",
                rollback_pointer=parent.version_id,
            )
        outcome = (
            HonestOutcome.SOURCE_GROUNDED_LOCAL_ONLY
            if episode.proposal.category is LessonCategory.SOURCE_GROUNDED_FACT
            else HonestOutcome.DURABLE_LOCAL_ONLY
        )
        self.store._transition_episode(
            proposal_id,
            EpisodeStatus.DURABLE_LOCAL,
            outcome,
            "local durability recorded; no CNCM or CAS-RRK commitment occurred",
            retention_receipt_id=retention_receipt_id,
            local_version_id=active.version_id,
            rollback_pointer=parent_version_id,
        )
        return active

    def record_cas_ohm_observation(
        self, proposal_id: str, observation: CASOhmObservation
    ) -> TeachingEpisode:
        if not isinstance(observation, CASOhmObservation):
            raise ApprenticeshipValidationError(
                "record_cas_ohm_observation requires CASOhmObservation"
            )
        episode = self.store.episode_for_proposal(proposal_id)
        return self.store._transition_episode(
            proposal_id,
            episode.status,
            episode.honest_outcome,
            "CAS-Ohm before/after metrics recorded as observational only",
            cas_ohm_observation=observation,
        )

    def rollback(self, version_id: str, reason: str) -> CapabilityVersion:
        _require_text("rollback reason", reason, limit=512)
        version = self.store.version(version_id)
        if version.status not in {
            VersionStatus.ACTIVE_LOCAL,
            VersionStatus.QUARANTINED,
        }:
            raise ApprenticeshipLifecycleError(
                f"cannot roll back a {version.status.value} version"
            )
        parent: CapabilityVersion | None = None
        if version.parent_version_id is not None:
            parent = self.store.version(version.parent_version_id)
            if parent.status is not VersionStatus.SUPERSEDED:
                raise ApprenticeshipLifecycleError(
                    "rollback parent is not in the superseded state"
                )
        rolled_back = self.store._transition_version(
            version_id,
            VersionStatus.ROLLED_BACK,
            reason,
        )
        self.store._transition_episode(
            version.proposal_id,
            EpisodeStatus.ROLLED_BACK,
            HonestOutcome.ROLLED_BACK,
            reason,
            rollback_pointer=version.parent_version_id,
        )
        if parent is not None:
            self.store._transition_version(
                parent.version_id,
                VersionStatus.ACTIVE_LOCAL,
                f"restored after rollback of {version_id}",
            )
            parent_episode = self.store.episode_for_proposal(parent.proposal_id)
            restored_outcome = (
                HonestOutcome.SOURCE_GROUNDED_LOCAL_ONLY
                if parent_episode.proposal.category is LessonCategory.SOURCE_GROUNDED_FACT
                else HonestOutcome.DURABLE_LOCAL_ONLY
            )
            self.store._transition_episode(
                parent.proposal_id,
                EpisodeStatus.DURABLE_LOCAL,
                restored_outcome,
                f"restored after rollback of {version_id}",
            )
        return rolled_back

    def run_local_capability(
        self,
        capability_key: str,
        inputs: tuple[NamedValue, ...],
        *,
        include_provisional: bool = False,
    ) -> ExecutionResult:
        versions = list(self.store.active_versions())
        if include_provisional:
            versions.extend(self.store.provisional_versions())
        matching = [
            version for version in versions if version.artifact.capability_key == capability_key
        ]
        if not matching:
            return ExecutionResult(
                ExecutionStatus.UNSUPPORTED_ARTIFACT,
                (),
                "no eligible local capability version exists",
            )
        selected = max(matching, key=lambda version: version.artifact.revision)
        return self.interpreter.run(selected.artifact, inputs)


def _demo_installed_capabilities() -> tuple[InstalledCapability, ...]:
    def installed(key: str, revision: int) -> InstalledCapability:
        return InstalledCapability(
            capability_key=key,
            revision=revision,
            evidence_digest=canonical_digest(
                {"capability_key": key, "revision": revision, "fixture": "demo-seed"}
            ),
            provenance="fixed local CCB-T1 demonstration prerequisite",
        )

    return (
        installed("exact-rational-arithmetic", 1),
        installed("typed-tool-intent", 1),
        installed("permission-gate", 1),
        installed("source-digest-validation", 1),
        installed("validity-window-check", 1),
        installed("protected-authority-sentinel", 1),
    )


def _demo_teacher_assignments() -> tuple[TeacherAssignment, ...]:
    return (
        TeacherAssignment(
            TeacherRole.DEMONSTRATOR,
            TeacherIdentity("foreign-faculty-demonstrator", "teacher-rev-1"),
        ),
        TeacherAssignment(
            TeacherRole.CRITIC,
            TeacherIdentity("foreign-faculty-critic", "teacher-rev-1"),
        ),
    )


def _demo_examiner() -> ExaminerIdentity:
    return ExaminerIdentity(
        "frozen-ccb-t1-verifier",
        "verifier-rev-1",
        "protected-fixture-custody",
    )


def _demo_sdg() -> CASSDGIdentity:
    return CASSDGIdentity("cas-sdg-demo-generator", "sdg-rev-1")


def _named_values(**values: str) -> tuple[NamedValue, ...]:
    return tuple(sorted(NamedValue(name, value) for name, value in values.items()))


def _math_artifact(revision: int = 1) -> CapabilityArtifact:
    return CapabilityArtifact(
        capability_key="solve-linear-ax-plus-b-equals-c",
        revision=revision,
        kind=ArtifactKind.PROCEDURE_PROGRAM,
        program=(
            Instruction(InstructionOp.LOAD_INPUT, "ra", ("a",)),
            Instruction(InstructionOp.LOAD_INPUT, "rb", ("b",)),
            Instruction(InstructionOp.LOAD_INPUT, "rc", ("c",)),
            Instruction(InstructionOp.SUBTRACT_EXACT, "numerator", ("rc", "rb")),
            Instruction(InstructionOp.DIVIDE_EXACT, "solution", ("numerator", "ra")),
            Instruction(InstructionOp.EMIT_REGISTER, "x", ("solution",)),
        ),
        source_claim=None,
        description="solve a*x+b=c using exact rational subtraction and division",
    )


_TOOL_PROCEDURE = (
    "recognize_need>form_tool_intent>obtain_permission>execute>"
    "validate_result>store_provenance>resume_parent_goal"
)


def _tool_artifact(revision: int = 1) -> CapabilityArtifact:
    return CapabilityArtifact(
        capability_key="governed-tool-use-procedure",
        revision=revision,
        kind=ArtifactKind.PROCEDURE_PROGRAM,
        program=(
            Instruction(InstructionOp.REQUIRE_TRUE, None, ("permission_granted",)),
            Instruction(InstructionOp.COPY_INPUT_TO_OUTPUT, "tool", ("tool_name",)),
            Instruction(InstructionOp.EMIT_LITERAL, "procedure", (_TOOL_PROCEDURE,)),
            Instruction(
                InstructionOp.EMIT_LITERAL,
                "verification_requirement",
                ("validate_returned_data",),
            ),
        ),
        source_claim=None,
        description="permission-gated reusable tool intent and result validation procedure",
    )


def _source_artifact(revision: int = 1) -> CapabilityArtifact:
    claim = SourceLinkedClaim.create(
        claim_key="demo-registry-current-release",
        claim_value="v3.2.1",
        source_locator="urn:demo:registry:snapshot-2026-08-28",
        observed_on="2026-08-28",
        valid_from="2026-08-01",
        valid_through="2026-09-30",
    )
    return CapabilityArtifact(
        capability_key="demo-registry-current-release-lookup",
        revision=revision,
        kind=ArtifactKind.SOURCE_LINKED_CLAIM,
        program=(Instruction(InstructionOp.SOURCE_LOOKUP, "release", ("as_of",)),),
        source_claim=claim,
        description="retrieve a changing fact only inside its source-bound validity window",
    )


def _protected_artifact() -> CapabilityArtifact:
    return CapabilityArtifact(
        capability_key="teacher-may-write-kernel-policy",
        revision=1,
        kind=ArtifactKind.POLICY_PROPOSAL,
        program=(
            Instruction(
                InstructionOp.EMIT_LITERAL,
                "policy",
                ("allow_foreign_teacher_kernel_commit",),
            ),
        ),
        source_claim=None,
        description="deliberately prohibited authority-contract mutation proposal",
    )


def _demo_material(
    case_id: str,
) -> tuple[
    LessonProposal,
    CASSDGExpansion,
    ExaminationSuite,
    ExaminationSuite,
    CASOhmObservation,
]:
    teachers = _demo_teacher_assignments()
    examiner = _demo_examiner()
    sdg_identity = _demo_sdg()
    installed = {
        capability.capability_key: capability
        for capability in _demo_installed_capabilities()
    }

    if case_id == "exact_reasoning_math":
        artifact = _math_artifact()
        positive = EvaluationCase(
            "teacher-math-positive",
            _named_values(a="2", b="3", c="11"),
            ExecutionStatus.SUCCESS,
            _named_values(x="4"),
        )
        counter = EvaluationCase(
            "teacher-math-zero-coefficient",
            _named_values(a="0", b="3", c="11"),
            ExecutionStatus.DIVISION_BY_ZERO,
            (),
        )
        proposal = LessonProposal(
            lesson_id="ccb-t1-demo-exact-reasoning-math",
            domain="CCB_T1_DOMAIN_MATHEMATICS",
            category=LessonCategory.MATHEMATICS,
            transfer_channel=TransferChannel.PROCEDURAL_INDUCTION,
            teachers=teachers,
            artifact=artifact,
            prerequisites=(CapabilityPrerequisite("exact-rational-arithmetic", 1),),
            positive_examples=(positive,),
            negative_examples=(),
            counterexamples=(counter,),
            verification_method="bounded exact rational interpreter",
            accepted_scope="single-variable nonzero-coefficient linear equations",
            known_exceptions=("zero coefficient requires a separate equation classifier",),
            teacher_confidence_basis_points=9_800,
            provenance=("typed foreign faculty lesson; confidence is informational",),
        )
        sdg_transfer = EvaluationCase(
            "sdg-math-transfer",
            _named_values(a="3", b="-1", c="8"),
            ExecutionStatus.SUCCESS,
            _named_values(x="3"),
        )
        sdg_adversarial = EvaluationCase(
            "sdg-math-rational",
            _named_values(a="4", b="1", c="3"),
            ExecutionStatus.SUCCESS,
            _named_values(x="1/2"),
        )
        held_out = EvaluationCase(
            "heldout-math-negative",
            _named_values(a="-2", b="4", c="10"),
            ExecutionStatus.SUCCESS,
            _named_values(x="-3"),
        )
        protected_counter = EvaluationCase(
            "heldout-math-zero",
            _named_values(a="0", b="4", c="10"),
            ExecutionStatus.DIVISION_BY_ZERO,
            (),
        )
        retention_case = EvaluationCase(
            "retention-math-transfer",
            _named_values(a="5", b="-5", c="20"),
            ExecutionStatus.SUCCESS,
            _named_values(x="5"),
        )
        guard_key = "exact-rational-arithmetic"
        before_metrics = CapabilityMetrics(3_200, 7_100, 1_400, EffectStatus.INCORRECT)
        after_metrics = CapabilityMetrics(7_000, 3_800, 2_600, EffectStatus.CORRECT)
    elif case_id == "tool_use_procedure":
        artifact = _tool_artifact()
        positive = EvaluationCase(
            "teacher-tool-positive",
            _named_values(permission_granted="true", tool_name="exact-calculator"),
            ExecutionStatus.SUCCESS,
            _named_values(
                procedure=_TOOL_PROCEDURE,
                tool="exact-calculator",
                verification_requirement="validate_returned_data",
            ),
        )
        counter = EvaluationCase(
            "teacher-tool-permission-denied",
            _named_values(permission_granted="false", tool_name="exact-calculator"),
            ExecutionStatus.PERMISSION_REQUIRED,
            (),
        )
        proposal = LessonProposal(
            lesson_id="ccb-t1-demo-tool-use",
            domain="CCB_T1_DOMAIN_TOOL_USE",
            category=LessonCategory.TOOL_USE,
            transfer_channel=TransferChannel.PROCEDURAL_INDUCTION,
            teachers=teachers,
            artifact=artifact,
            prerequisites=(
                CapabilityPrerequisite("typed-tool-intent", 1),
                CapabilityPrerequisite("permission-gate", 1),
            ),
            positive_examples=(positive,),
            negative_examples=(),
            counterexamples=(counter,),
            verification_method="ordered typed-intent and permission fixture",
            accepted_scope="tools with explicit permission and validated return data",
            known_exceptions=("interactive authentication remains a human boundary",),
            teacher_confidence_basis_points=9_500,
            provenance=("typed foreign faculty tool procedure",),
        )
        sdg_transfer = EvaluationCase(
            "sdg-tool-search",
            _named_values(permission_granted="true", tool_name="search"),
            ExecutionStatus.SUCCESS,
            _named_values(
                procedure=_TOOL_PROCEDURE,
                tool="search",
                verification_requirement="validate_returned_data",
            ),
        )
        sdg_adversarial = EvaluationCase(
            "sdg-tool-no-permission",
            _named_values(permission_granted="false", tool_name="filesystem"),
            ExecutionStatus.PERMISSION_REQUIRED,
            (),
        )
        held_out = EvaluationCase(
            "heldout-tool-theorem-prover",
            _named_values(permission_granted="true", tool_name="theorem-prover"),
            ExecutionStatus.SUCCESS,
            _named_values(
                procedure=_TOOL_PROCEDURE,
                tool="theorem-prover",
                verification_requirement="validate_returned_data",
            ),
        )
        protected_counter = EvaluationCase(
            "heldout-tool-permission-denied",
            _named_values(permission_granted="false", tool_name="database"),
            ExecutionStatus.PERMISSION_REQUIRED,
            (),
        )
        retention_case = EvaluationCase(
            "retention-tool-simulator",
            _named_values(permission_granted="true", tool_name="simulator"),
            ExecutionStatus.SUCCESS,
            _named_values(
                procedure=_TOOL_PROCEDURE,
                tool="simulator",
                verification_requirement="validate_returned_data",
            ),
        )
        guard_key = "permission-gate"
        before_metrics = CapabilityMetrics(2_800, 7_500, 1_700, EffectStatus.INCORRECT)
        after_metrics = CapabilityMetrics(6_500, 4_100, 2_900, EffectStatus.CORRECT)
    elif case_id == "source_grounded_changing_fact":
        artifact = _source_artifact()
        positive = EvaluationCase(
            "teacher-source-current",
            _named_values(as_of="2026-08-28"),
            ExecutionStatus.SUCCESS,
            _named_values(release="v3.2.1"),
        )
        counter = EvaluationCase(
            "teacher-source-stale",
            _named_values(as_of="2026-10-01"),
            ExecutionStatus.SOURCE_OUTSIDE_VALIDITY_WINDOW,
            (),
        )
        proposal = LessonProposal(
            lesson_id="ccb-t1-demo-source-grounded-changing-fact",
            domain="CCB_T1_DOMAIN_WORLD_KNOWLEDGE",
            category=LessonCategory.SOURCE_GROUNDED_FACT,
            transfer_channel=TransferChannel.RETRIEVAL_LINKED_KNOWLEDGE,
            teachers=teachers,
            artifact=artifact,
            prerequisites=(
                CapabilityPrerequisite("source-digest-validation", 1),
                CapabilityPrerequisite("validity-window-check", 1),
            ),
            positive_examples=(positive,),
            negative_examples=(),
            counterexamples=(counter,),
            verification_method="source digest plus explicit as-of validity window",
            accepted_scope="fictional demo registry release inside the stated validity window",
            known_exceptions=("outside-window queries return an honest non-success status",),
            teacher_confidence_basis_points=9_000,
            provenance=("source-linked fictional demonstration record",),
        )
        sdg_transfer = EvaluationCase(
            "sdg-source-window-start",
            _named_values(as_of="2026-08-01"),
            ExecutionStatus.SUCCESS,
            _named_values(release="v3.2.1"),
        )
        sdg_adversarial = EvaluationCase(
            "sdg-source-before-window",
            _named_values(as_of="2026-07-31"),
            ExecutionStatus.SOURCE_OUTSIDE_VALIDITY_WINDOW,
            (),
        )
        held_out = EvaluationCase(
            "heldout-source-window-end",
            _named_values(as_of="2026-09-30"),
            ExecutionStatus.SUCCESS,
            _named_values(release="v3.2.1"),
        )
        protected_counter = EvaluationCase(
            "heldout-source-after-window",
            _named_values(as_of="2027-01-01"),
            ExecutionStatus.SOURCE_OUTSIDE_VALIDITY_WINDOW,
            (),
        )
        retention_case = EvaluationCase(
            "retention-source-middle-window",
            _named_values(as_of="2026-09-15"),
            ExecutionStatus.SUCCESS,
            _named_values(release="v3.2.1"),
        )
        guard_key = "source-digest-validation"
        before_metrics = CapabilityMetrics(2_000, 8_000, 1_200, EffectStatus.UNKNOWN)
        after_metrics = CapabilityMetrics(5_500, 4_900, 2_100, EffectStatus.CORRECT)
    else:
        artifact = _protected_artifact()
        positive = EvaluationCase(
            "teacher-protected-positive",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        counter = EvaluationCase(
            "teacher-protected-repeat",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        proposal = LessonProposal(
            lesson_id="ccb-t1-demo-protected-authority-rejection",
            domain="CCB_T1_DOMAIN_BOARD_DESIGN",
            category=LessonCategory.AUTHORITY_CONTRACT,
            transfer_channel=TransferChannel.EXPLICIT_SYMBOLIC,
            teachers=teachers,
            artifact=artifact,
            prerequisites=(),
            positive_examples=(positive,),
            negative_examples=(),
            counterexamples=(counter,),
            verification_method="protected category deny-list before artifact execution",
            accepted_scope="proposal and explanation only; no promotion",
            known_exceptions=("only separate external authority may change this category",),
            teacher_confidence_basis_points=10_000,
            provenance=("deliberately prohibited authority mutation fixture",),
        )
        sdg_transfer = EvaluationCase(
            "sdg-protected-transfer",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        sdg_adversarial = EvaluationCase(
            "sdg-protected-adversarial",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        held_out = EvaluationCase(
            "heldout-protected",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        protected_counter = EvaluationCase(
            "heldout-protected-counter",
            (),
            ExecutionStatus.SUCCESS,
            _named_values(policy="allow_foreign_teacher_kernel_commit"),
        )
        retention_case = held_out
        guard_key = "protected-authority-sentinel"
        before_metrics = CapabilityMetrics(1_000, 9_000, 800, EffectStatus.INCORRECT)
        after_metrics = CapabilityMetrics(1_000, 9_000, 800, EffectStatus.INCORRECT)

    expansion = CASSDGExpansion(
        proposal_id=proposal.proposal_id,
        generator=sdg_identity,
        independent_seed=f"sdg-seed-{case_id}",
        transfer_cases=(sdg_transfer,),
        adversarial_cases=(sdg_adversarial,),
        provenance=("CAS-SDG demonstration expansion; separate from teacher examples",),
    )
    installed_guard = installed[guard_key]
    guard = RegressionGuard(
        installed_guard.capability_key,
        installed_guard.revision,
        installed_guard.evidence_digest,
    )
    qualification = ExaminationSuite(
        suite_id=f"qualification-{case_id}",
        purpose=SuitePurpose.QUALIFICATION,
        examiner=examiner,
        custody_seed=f"protected-qualification-seed-{case_id}",
        held_out_cases=(held_out,),
        counterexamples=(protected_counter,),
        regression_guards=(guard,),
    )
    retention = ExaminationSuite(
        suite_id=f"retention-{case_id}",
        purpose=SuitePurpose.DELAYED_RETENTION,
        examiner=examiner,
        custody_seed=f"protected-retention-seed-{case_id}",
        held_out_cases=(retention_case,),
        counterexamples=(),
        regression_guards=(guard,),
    )
    observation = CASOhmObservation.create(
        f"cas-ohm-{case_id}", before_metrics, after_metrics
    )
    return proposal, expansion, qualification, retention, observation


def cognitive_apprenticeship_demo_cases() -> tuple[str, ...]:
    """Return the stable browser-safe CCB-T1 demonstration identifiers."""

    return (
        "exact_reasoning_math",
        "tool_use_procedure",
        "source_grounded_changing_fact",
        "protected_authority_rejection",
    )


def run_cognitive_apprenticeship_demo(
    case_id: str = "exact_reasoning_math",
) -> dict[str, Any]:
    """Run one fresh deterministic local CCB-T1 demonstration."""

    if case_id not in cognitive_apprenticeship_demo_cases():
        raise ApprenticeshipValidationError(
            f"unknown demo case {case_id!r}; expected {cognitive_apprenticeship_demo_cases()}"
        )
    board = CognitiveApprenticeship(_demo_installed_capabilities())
    proposal, expansion, qualification_suite, retention_suite, observation = (
        _demo_material(case_id)
    )
    before_digest = board.active_local_digest
    episode = board.submit_teacher_proposal(proposal)
    after_proposal_digest = board.active_local_digest
    prerequisite = board.check_prerequisites(proposal.proposal_id)
    expansion_id = board.register_cas_sdg_expansion(expansion)
    qualification = board.qualify(
        proposal.proposal_id,
        prerequisite.receipt_id,
        expansion_id,
        qualification_suite,
    )
    provisional: CapabilityVersion | None = None
    retention: RetentionReceipt | None = None
    durable: CapabilityVersion | None = None
    if qualification.passed:
        provisional = board.promote_provisionally(
            proposal.proposal_id, qualification.receipt_id
        )
        retention = board.evaluate_delayed_retention(
            proposal.proposal_id,
            qualification.receipt_id,
            retention_suite,
        )
        if retention.passed:
            durable = board.promote_durably(
                proposal.proposal_id,
                qualification.receipt_id,
                retention.receipt_id,
            )
    final_episode = board.record_cas_ohm_observation(
        proposal.proposal_id, observation
    )
    result = {
        "case_id": case_id,
        "honest_outcome": final_episode.honest_outcome,
        "domain": proposal.domain,
        "teacher_roles": tuple(assignment.role for assignment in proposal.teachers),
        "transfer_channel": proposal.transfer_channel,
        "proposal": {
            "proposal_id": proposal.proposal_id,
            "lesson_id": proposal.lesson_id,
            "category": proposal.category,
            "artifact_content_id": proposal.artifact.artifact_content_id,
            "teacher_confidence_basis_points_informational_only": (
                proposal.teacher_confidence_basis_points
            ),
            "active_local_digest_before": before_digest,
            "active_local_digest_after_submission": after_proposal_digest,
            "proposal_directly_changed_active_local_store": (
                before_digest != after_proposal_digest
            ),
        },
        "prerequisite_check": prerequisite,
        "cas_sdg_expansion": {
            "expansion_id": expansion.expansion_id,
            "generator": expansion.generator,
            "independent_seed": expansion.independent_seed,
        },
        "qualification_receipt": qualification,
        "retention_receipt": retention,
        "local_version": durable or provisional,
        "teaching_episode": final_episode,
        "cas_ohm_observation": observation,
        "store_snapshot_digest": board.store.snapshot().snapshot_digest,
        "state_scope": "LOCAL CCB-T1 STORE ONLY",
        "authority_boundary": {
            "kernel_integrated": False,
            "cncm_state_writes": 0,
            "cas_rrk_commits": 0,
            "cas_rrk_promotion_receipt": False,
            "cas_ohm_promotion_authority": False,
        },
    }
    return to_primitive(result)


__all__ = [
    "ApprenticeshipLifecycleError",
    "ApprenticeshipPromotionError",
    "ApprenticeshipQualificationError",
    "ApprenticeshipStoreSnapshot",
    "ApprenticeshipValidationError",
    "ArtifactKind",
    "BoundedProcedureInterpreter",
    "CASOhmObservation",
    "CASSDGExpansion",
    "CASSDGIdentity",
    "CapabilityArtifact",
    "CapabilityMetrics",
    "CapabilityPrerequisite",
    "CapabilityVersion",
    "CognitiveApprenticeship",
    "CognitiveApprenticeshipError",
    "EffectStatus",
    "EpisodeLineageEvent",
    "EpisodeStatus",
    "EvaluationCase",
    "ExaminationSuite",
    "ExaminerIdentity",
    "ExecutionResult",
    "ExecutionStatus",
    "GateResult",
    "HonestOutcome",
    "InstalledCapability",
    "Instruction",
    "InstructionOp",
    "LessonCategory",
    "LessonProposal",
    "NamedValue",
    "PROTECTED_LESSON_CATEGORIES",
    "PrerequisiteCheckReceipt",
    "PrerequisiteResult",
    "QualificationGate",
    "QualificationReceipt",
    "RegressionGuard",
    "RetentionReceipt",
    "SourceLinkedClaim",
    "SuitePurpose",
    "TeacherAssignment",
    "TeacherIdentity",
    "TeacherRole",
    "TeachingEpisode",
    "TransferChannel",
    "VersionStatus",
    "VersionedTeachingStore",
    "cognitive_apprenticeship_demo_cases",
    "run_cognitive_apprenticeship_demo",
]
