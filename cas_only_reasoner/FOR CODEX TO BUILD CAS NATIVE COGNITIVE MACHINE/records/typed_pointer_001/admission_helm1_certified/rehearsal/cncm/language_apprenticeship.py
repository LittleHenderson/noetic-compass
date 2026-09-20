"""Bounded verified cognitive apprenticeship reference runtime.

This module is deliberately isolated from the CNCM kernel.  It models one
small, deterministic CCB-L1-GRAM laboratory in which a foreign teacher may
submit an immutable lesson proposal, but cannot make that proposal part of
the active grammar.  Independent qualification and retention receipts are
required before a construction becomes active.

The pattern compiler is a small interpreter over typed atoms.  It does not
use ``eval``, regular-expression replacement, executable teacher text, file
I/O, wall-clock time, or kernel mutation.  Its intentionally bounded language
supports single-token noun phrases (optionally introduced by ``the``), regular
or registered verb forms, active transitive clauses, passive transitive
clauses, and past-tense active negation.

This is a follow-on reference component, not a claim that CCB-L1, CAS-RRK,
CAS-Sem, CAS-SDG, or the production CNCM runtime is integrated with it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any, Iterable

from .canonical import content_id as canonical_content_id
from .canonical import digest as canonical_digest
from .canonical import to_primitive


class LanguageApprenticeshipError(ValueError):
    """Base error for the bounded apprenticeship laboratory."""


class PacketValidationError(LanguageApprenticeshipError):
    """An immutable packet or record violates its typed contract."""


class PatternCompilationError(LanguageApprenticeshipError):
    """A construction is outside the bounded, non-eval pattern language."""


class QualificationError(LanguageApprenticeshipError):
    """A qualification request violates evidence-channel separation."""


class PromotionError(LanguageApprenticeshipError):
    """A requested promotion lacks a locally issued passing receipt."""


class LifecycleError(LanguageApprenticeshipError):
    """A candidate or version transition is not allowed."""


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SLOT = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_LITERAL = re.compile(r"[a-z][a-z'-]{0,31}\Z")
_SENTENCE = re.compile(
    r"\s*[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*)*\s*[.!?]?\s*\Z"
)
_ALLOWED_ROLES = frozenset(
    {"agent", "patient", "recipient", "instrument", "location", "experiencer"}
)
_MAX_PATTERN_ATOMS = 16
_MAX_SENTENCE_TOKENS = 32


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise PacketValidationError(f"{name} must be a bounded identifier")


def _require_slot(name: str, value: str) -> None:
    if not isinstance(value, str) or _SLOT.fullmatch(value) is None:
        raise PacketValidationError(f"{name} must be a lowercase slot identifier")


def _require_text(name: str, value: str, *, limit: int = 512) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise PacketValidationError(f"{name} must be non-empty and at most {limit} characters")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise PacketValidationError(f"{name} contains a control character")


def _require_tuple(name: str, value: object) -> None:
    if type(value) is not tuple:
        raise PacketValidationError(f"{name} must be an immutable tuple")


def _require_unique(name: str, values: Iterable[str]) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise PacketValidationError(f"{name} must not contain duplicates")


class LessonType(str, Enum):
    GRAMMAR_CONSTRUCTION = "GRAMMAR_CONSTRUCTION"


class AtomKind(str, Enum):
    LITERAL = "LITERAL"
    NOUN_PHRASE = "NOUN_PHRASE"
    VERB = "VERB"


class VerbForm(str, Enum):
    BASE = "BASE"
    PAST = "PAST"
    PARTICIPLE = "PARTICIPLE"
    PAST_OR_PARTICIPLE = "PAST_OR_PARTICIPLE"


class Tense(str, Enum):
    PAST = "PAST"
    PRESENT = "PRESENT"


class Polarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class Voice(str, Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"


class ParseStatus(str, Enum):
    PARSED = "PARSED"
    UNKNOWN_CONSTRUCTION = "UNKNOWN_CONSTRUCTION"
    AMBIGUOUS_PARSE = "AMBIGUOUS_PARSE"


class PairRelation(str, Enum):
    SAME_MEANING = "SAME_MEANING"
    DIFFERENT_MEANING = "DIFFERENT_MEANING"


class EvidenceChannel(str, Enum):
    PROTECTED_FIXTURE = "PROTECTED_FIXTURE"
    FROZEN_VERIFIER = "FROZEN_VERIFIER"


class SuitePurpose(str, Enum):
    QUALIFICATION = "QUALIFICATION"
    DELAYED_RETENTION = "DELAYED_RETENTION"


class CandidateStatus(str, Enum):
    LANG_PROPOSED = "CCB_L1_GRAM_PROPOSED"
    LANG_QUALIFIED = "CCB_L1_GRAM_QUALIFIED"
    LANG_PROVISIONAL = "CCB_L1_GRAM_PROMOTED_PROVISIONALLY"
    LANG_DURABLE = "CCB_L1_GRAM_PROMOTED_DURABLY"
    LANG_QUARANTINED = "CCB_L1_GRAM_QUARANTINED"
    LANG_SUPERSEDED = "CCB_L1_GRAM_SUPERSEDED"
    LANG_ROLLED_BACK = "CCB_L1_GRAM_ROLLED_BACK"


class VersionStatus(str, Enum):
    LANG_PROVISIONAL = "CCB_L1_GRAM_PROMOTED_PROVISIONALLY"
    LANG_ACTIVE = "CCB_L1_GRAM_ACTIVE"
    LANG_QUARANTINED = "CCB_L1_GRAM_QUARANTINED"
    LANG_SUPERSEDED = "CCB_L1_GRAM_SUPERSEDED"
    LANG_ROLLED_BACK = "CCB_L1_GRAM_ROLLED_BACK"


class GateName(str, Enum):
    PROPOSED = "CCB_L1_GRAM_PROPOSED"
    SCHEMA_VALID = "CCB_L1_GRAM_SCHEMA_VALID"
    COMPILED = "CCB_L1_GRAM_COMPILED"
    POSITIVE_EXAMPLES_PASS = "CCB_L1_GRAM_POSITIVE_EXAMPLES_PASS"
    CONTRAST_TESTS_PASS = "CCB_L1_GRAM_CONTRAST_TESTS_PASS"
    HELD_OUT_GENERALIZATION_PASS = "CCB_L1_GRAM_HELD_OUT_GENERALIZATION_PASS"
    PRIOR_GRAMMAR_REGRESSION_PASS = "CCB_L1_GRAM_PRIOR_GRAMMAR_REGRESSION_PASS"
    AMBIGUITY_BEHAVIOR_PASS = "CCB_L1_GRAM_AMBIGUITY_BEHAVIOR_PASS"
    DETERMINISTIC_REPLAY_PASS = "CCB_L1_GRAM_DETERMINISTIC_REPLAY_PASS"
    DELAYED_RETENTION_PASS = "CCB_L1_GRAM_DELAYED_RETENTION_PASS"


_QUALIFICATION_GATES = (
    GateName.PROPOSED,
    GateName.SCHEMA_VALID,
    GateName.COMPILED,
    GateName.POSITIVE_EXAMPLES_PASS,
    GateName.CONTRAST_TESTS_PASS,
    GateName.HELD_OUT_GENERALIZATION_PASS,
    GateName.PRIOR_GRAMMAR_REGRESSION_PASS,
    GateName.AMBIGUITY_BEHAVIOR_PASS,
    GateName.DETERMINISTIC_REPLAY_PASS,
)


@dataclass(frozen=True, slots=True)
class TeacherIdentity:
    model: str
    revision: str

    def __post_init__(self) -> None:
        _require_identifier("teacher.model", self.model)
        _require_identifier("teacher.revision", self.revision)

    @property
    def identity_id(self) -> str:
        return canonical_content_id("teacher", self)


@dataclass(frozen=True, slots=True)
class ExaminerIdentity:
    examiner: str
    revision: str
    channel: EvidenceChannel

    def __post_init__(self) -> None:
        _require_identifier("examiner.examiner", self.examiner)
        _require_identifier("examiner.revision", self.revision)
        if not isinstance(self.channel, EvidenceChannel):
            raise PacketValidationError("examiner.channel must be an EvidenceChannel")

    @property
    def identity_id(self) -> str:
        return canonical_content_id("examiner", self)


@dataclass(frozen=True, slots=True)
class MorphologyEntry:
    surface: str
    lemma: str
    form: VerbForm
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.surface, str) or _LITERAL.fullmatch(self.surface) is None:
            raise PacketValidationError("morphology.surface must be one lowercase token")
        if not isinstance(self.lemma, str) or _LITERAL.fullmatch(self.lemma) is None:
            raise PacketValidationError("morphology.lemma must be one lowercase token")
        if not isinstance(self.form, VerbForm):
            raise PacketValidationError("morphology.form must be a VerbForm")
        _require_text("morphology.provenance", self.provenance, limit=256)


@dataclass(frozen=True, slots=True)
class PatternAtom:
    kind: AtomKind
    value: str | None = None
    slot: str | None = None
    verb_form: VerbForm | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AtomKind):
            raise PacketValidationError("pattern atom kind must be an AtomKind")
        if self.kind is AtomKind.LITERAL:
            if not isinstance(self.value, str) or _LITERAL.fullmatch(self.value) is None:
                raise PacketValidationError("literal atoms require one lowercase token")
            if self.slot is not None or self.verb_form is not None:
                raise PacketValidationError("literal atoms cannot carry a slot or verb form")
        elif self.kind is AtomKind.NOUN_PHRASE:
            if self.value is not None or self.verb_form is not None or self.slot is None:
                raise PacketValidationError("noun-phrase atoms require only a slot")
            _require_slot("noun phrase slot", self.slot)
        elif self.kind is AtomKind.VERB:
            if self.value is not None or self.slot is None or self.verb_form is None:
                raise PacketValidationError("verb atoms require a slot and verb form")
            _require_slot("verb slot", self.slot)
            if not isinstance(self.verb_form, VerbForm):
                raise PacketValidationError("verb atom form must be a VerbForm")

    @classmethod
    def literal(cls, value: str) -> "PatternAtom":
        return cls(kind=AtomKind.LITERAL, value=value)

    @classmethod
    def noun_phrase(cls, slot: str) -> "PatternAtom":
        return cls(kind=AtomKind.NOUN_PHRASE, slot=slot)

    @classmethod
    def verb(cls, slot: str, form: VerbForm) -> "PatternAtom":
        return cls(kind=AtomKind.VERB, slot=slot, verb_form=form)


@dataclass(frozen=True, slots=True)
class RoleBindingSpec:
    role: str
    source_slot: str

    def __post_init__(self) -> None:
        if self.role not in _ALLOWED_ROLES:
            raise PacketValidationError(f"unsupported semantic role: {self.role!r}")
        _require_slot("role source_slot", self.source_slot)


@dataclass(frozen=True, slots=True)
class SemanticTransformation:
    predicate_slot: str
    roles: tuple[RoleBindingSpec, ...]
    tense: Tense
    polarity: Polarity
    voice: Voice

    def __post_init__(self) -> None:
        _require_slot("semantic predicate_slot", self.predicate_slot)
        _require_tuple("semantic roles", self.roles)
        if not self.roles:
            raise PacketValidationError("semantic roles must not be empty")
        if any(not isinstance(binding, RoleBindingSpec) for binding in self.roles):
            raise PacketValidationError("semantic roles must contain RoleBindingSpec values")
        _require_unique("semantic roles", (binding.role for binding in self.roles))
        if not isinstance(self.tense, Tense):
            raise PacketValidationError("semantic tense must be a Tense")
        if not isinstance(self.polarity, Polarity):
            raise PacketValidationError("semantic polarity must be a Polarity")
        if not isinstance(self.voice, Voice):
            raise PacketValidationError("semantic voice must be a Voice")


@dataclass(frozen=True, slots=True)
class GrammarConstruction:
    construction_key: str
    revision: int
    surface_pattern: tuple[PatternAtom, ...]
    semantic_transformation: SemanticTransformation
    claimed_scope: str

    def __post_init__(self) -> None:
        _require_identifier("construction_key", self.construction_key)
        if type(self.revision) is not int or self.revision < 1:
            raise PacketValidationError("construction revision must be a positive integer")
        _require_tuple("surface_pattern", self.surface_pattern)
        if not self.surface_pattern or len(self.surface_pattern) > _MAX_PATTERN_ATOMS:
            raise PacketValidationError(
                f"surface_pattern must contain 1..{_MAX_PATTERN_ATOMS} atoms"
            )
        if any(not isinstance(atom, PatternAtom) for atom in self.surface_pattern):
            raise PacketValidationError("surface_pattern must contain PatternAtom values")
        if not isinstance(self.semantic_transformation, SemanticTransformation):
            raise PacketValidationError(
                "semantic_transformation must be a SemanticTransformation"
            )
        _require_text("claimed_scope", self.claimed_scope, limit=512)

    @property
    def construction_content_id(self) -> str:
        return canonical_content_id("construction", self)

    @property
    def construction_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True, order=True)
class SemanticRole:
    role: str
    referent: str

    def __post_init__(self) -> None:
        if self.role not in _ALLOWED_ROLES:
            raise PacketValidationError(f"unsupported semantic role: {self.role!r}")
        if not isinstance(self.referent, str) or _LITERAL.fullmatch(self.referent) is None:
            raise PacketValidationError("semantic referent must be one normalized token")


@dataclass(frozen=True, slots=True)
class SemanticFrame:
    predicate: str
    roles: tuple[SemanticRole, ...]
    tense: Tense
    polarity: Polarity

    def __post_init__(self) -> None:
        if not isinstance(self.predicate, str) or _LITERAL.fullmatch(self.predicate) is None:
            raise PacketValidationError("semantic predicate must be one normalized token")
        _require_tuple("semantic frame roles", self.roles)
        if not self.roles or any(not isinstance(role, SemanticRole) for role in self.roles):
            raise PacketValidationError("semantic frame roles must contain SemanticRole values")
        if tuple(sorted(self.roles)) != self.roles:
            raise PacketValidationError("semantic frame roles must be sorted canonically")
        _require_unique("semantic frame roles", (role.role for role in self.roles))
        if not isinstance(self.tense, Tense) or not isinstance(self.polarity, Polarity):
            raise PacketValidationError("semantic frame tense and polarity must be enums")

    @classmethod
    def event(
        cls,
        predicate: str,
        *,
        agent: str,
        patient: str,
        tense: Tense = Tense.PAST,
        polarity: Polarity = Polarity.POSITIVE,
    ) -> "SemanticFrame":
        roles = tuple(
            sorted(
                (
                    SemanticRole("agent", agent.lower()),
                    SemanticRole("patient", patient.lower()),
                )
            )
        )
        return cls(predicate.lower(), roles, tense, polarity)

    @property
    def frame_content_id(self) -> str:
        return canonical_content_id("semantic-frame", self)


@dataclass(frozen=True, slots=True)
class InterpretedFrame:
    semantics: SemanticFrame
    construction_content_id: str
    construction_key: str
    voice: Voice

    def __post_init__(self) -> None:
        if not isinstance(self.semantics, SemanticFrame):
            raise PacketValidationError("interpreted semantics must be a SemanticFrame")
        _require_identifier("construction_content_id", self.construction_content_id)
        _require_identifier("construction_key", self.construction_key)
        if not isinstance(self.voice, Voice):
            raise PacketValidationError("interpreted voice must be a Voice")


@dataclass(frozen=True, slots=True)
class ParseResult:
    status: ParseStatus
    frames: tuple[InterpretedFrame, ...]
    semantics: SemanticFrame | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ParseStatus):
            raise PacketValidationError("parse status must be a ParseStatus")
        _require_tuple("parse frames", self.frames)
        if any(not isinstance(frame, InterpretedFrame) for frame in self.frames):
            raise PacketValidationError("parse frames must contain InterpretedFrame values")
        if self.status is ParseStatus.UNKNOWN_CONSTRUCTION:
            if self.frames or self.semantics is not None:
                raise PacketValidationError("unknown parses cannot contain frames or semantics")
        elif self.status is ParseStatus.PARSED:
            if not self.frames or self.semantics is None:
                raise PacketValidationError("parsed results require frames and one semantic frame")
        elif self.status is ParseStatus.AMBIGUOUS_PARSE and (
            len(self.frames) < 2 or self.semantics is not None
        ):
            raise PacketValidationError("ambiguous parses require alternatives and no commitment")


@dataclass(frozen=True, slots=True)
class SemanticExample:
    case_id: str
    sentence: str
    expected: SemanticFrame

    def __post_init__(self) -> None:
        _require_identifier("semantic example case_id", self.case_id)
        _require_text("semantic example sentence", self.sentence, limit=256)
        if not isinstance(self.expected, SemanticFrame):
            raise PacketValidationError("semantic example expected must be a SemanticFrame")


@dataclass(frozen=True, slots=True)
class MinimalPair:
    pair_id: str
    left: SemanticExample
    right: SemanticExample
    relation: PairRelation

    def __post_init__(self) -> None:
        _require_identifier("minimal pair pair_id", self.pair_id)
        if not isinstance(self.left, SemanticExample) or not isinstance(
            self.right, SemanticExample
        ):
            raise PacketValidationError("minimal pairs require typed left and right examples")
        if not isinstance(self.relation, PairRelation):
            raise PacketValidationError("minimal pair relation must be a PairRelation")
        expected_same = self.left.expected == self.right.expected
        if (self.relation is PairRelation.SAME_MEANING) != expected_same:
            raise PacketValidationError("minimal pair relation contradicts expected frames")


@dataclass(frozen=True, slots=True)
class CounterexampleCase:
    case_id: str
    sentence: str

    def __post_init__(self) -> None:
        _require_identifier("counterexample case_id", self.case_id)
        _require_text("counterexample sentence", self.sentence, limit=256)


@dataclass(frozen=True, slots=True)
class AmbiguityCase:
    case_id: str
    sentence: str
    accepted_statuses: tuple[ParseStatus, ...]

    def __post_init__(self) -> None:
        _require_identifier("ambiguity case_id", self.case_id)
        _require_text("ambiguity sentence", self.sentence, limit=256)
        _require_tuple("ambiguity accepted_statuses", self.accepted_statuses)
        if not self.accepted_statuses or any(
            status not in {ParseStatus.UNKNOWN_CONSTRUCTION, ParseStatus.AMBIGUOUS_PARSE}
            for status in self.accepted_statuses
        ):
            raise PacketValidationError(
                "ambiguity cases may accept only UNKNOWN_CONSTRUCTION or AMBIGUOUS_PARSE"
            )
        _require_unique("ambiguity accepted_statuses", (status.value for status in self.accepted_statuses))


@dataclass(frozen=True, slots=True)
class LanguageLessonPacket:
    lesson_id: str
    lesson_type: LessonType
    teacher: TeacherIdentity
    prerequisite_rules: tuple[str, ...]
    construction: GrammarConstruction
    positive_examples: tuple[SemanticExample, ...]
    minimal_pairs: tuple[MinimalPair, ...]
    counterexamples: tuple[CounterexampleCase, ...]
    ambiguity_cases: tuple[AmbiguityCase, ...]
    exceptions: tuple[str, ...]
    teacher_confidence_basis_points: int
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier("lesson_id", self.lesson_id)
        if not isinstance(self.lesson_type, LessonType):
            raise PacketValidationError("lesson_type must be a LessonType")
        if not isinstance(self.teacher, TeacherIdentity):
            raise PacketValidationError("teacher must be a TeacherIdentity")
        _require_tuple("prerequisite_rules", self.prerequisite_rules)
        for prerequisite in self.prerequisite_rules:
            _require_identifier("prerequisite rule", prerequisite)
        _require_unique("prerequisite_rules", self.prerequisite_rules)
        if not isinstance(self.construction, GrammarConstruction):
            raise PacketValidationError("construction must be a GrammarConstruction")
        for name, values, expected_type, require_nonempty in (
            ("positive_examples", self.positive_examples, SemanticExample, True),
            ("minimal_pairs", self.minimal_pairs, MinimalPair, True),
            ("counterexamples", self.counterexamples, CounterexampleCase, True),
            ("ambiguity_cases", self.ambiguity_cases, AmbiguityCase, True),
        ):
            _require_tuple(name, values)
            if require_nonempty and not values:
                raise PacketValidationError(f"{name} must not be empty")
            if any(not isinstance(value, expected_type) for value in values):
                raise PacketValidationError(f"{name} contains an invalid record")
        _require_tuple("exceptions", self.exceptions)
        for exception in self.exceptions:
            _require_text("lesson exception", exception, limit=256)
        if (
            type(self.teacher_confidence_basis_points) is not int
            or not 0 <= self.teacher_confidence_basis_points <= 10_000
        ):
            raise PacketValidationError(
                "teacher_confidence_basis_points must be an integer in [0, 10000]"
            )
        _require_tuple("provenance", self.provenance)
        if not self.provenance:
            raise PacketValidationError("provenance must not be empty")
        for provenance_item in self.provenance:
            _require_text("provenance item", provenance_item, limit=512)
        all_case_ids = tuple(
            example.case_id for example in self.positive_examples
        ) + tuple(pair.pair_id for pair in self.minimal_pairs) + tuple(
            case.case_id for case in self.counterexamples
        ) + tuple(case.case_id for case in self.ambiguity_cases)
        _require_unique("lesson evidence ids", all_case_ids)

    @property
    def packet_content_id(self) -> str:
        return canonical_content_id("language-lesson", self)

    @property
    def packet_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class QualificationSuite:
    suite_id: str
    purpose: SuitePurpose
    examiner: ExaminerIdentity
    independent_seed: str
    held_out_examples: tuple[SemanticExample, ...]
    contrast_pairs: tuple[MinimalPair, ...]
    counterexamples: tuple[CounterexampleCase, ...]
    ambiguity_cases: tuple[AmbiguityCase, ...]
    regression_examples: tuple[SemanticExample, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier("suite_id", self.suite_id)
        if not isinstance(self.purpose, SuitePurpose):
            raise PacketValidationError("suite purpose must be a SuitePurpose")
        if not isinstance(self.examiner, ExaminerIdentity):
            raise PacketValidationError("suite examiner must be an ExaminerIdentity")
        _require_identifier("independent_seed", self.independent_seed)
        typed_groups = (
            ("held_out_examples", self.held_out_examples, SemanticExample),
            ("contrast_pairs", self.contrast_pairs, MinimalPair),
            ("counterexamples", self.counterexamples, CounterexampleCase),
            ("ambiguity_cases", self.ambiguity_cases, AmbiguityCase),
            ("regression_examples", self.regression_examples, SemanticExample),
        )
        for name, values, expected_type in typed_groups:
            _require_tuple(name, values)
            if any(not isinstance(value, expected_type) for value in values):
                raise PacketValidationError(f"{name} contains an invalid record")
        if not self.held_out_examples:
            raise PacketValidationError("every suite requires held-out examples")
        if self.purpose is SuitePurpose.QUALIFICATION and (
            not self.contrast_pairs or not self.counterexamples or not self.ambiguity_cases
        ):
            raise PacketValidationError(
                "qualification suites require contrasts, counterexamples, and ambiguity cases"
            )
        evidence_ids = tuple(case.case_id for case in self.held_out_examples) + tuple(
            pair.pair_id for pair in self.contrast_pairs
        ) + tuple(case.case_id for case in self.counterexamples) + tuple(
            case.case_id for case in self.ambiguity_cases
        ) + tuple(case.case_id for case in self.regression_examples)
        _require_unique("suite evidence ids", evidence_ids)

    @property
    def suite_content_id(self) -> str:
        return canonical_content_id("qualification-suite", self)

    @property
    def suite_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: GateName
    passed: bool
    details: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.gate, GateName) or type(self.passed) is not bool:
            raise PacketValidationError("gate records require a GateName and bool")
        _require_tuple("gate details", self.details)
        if not self.details:
            raise PacketValidationError("gate details must not be empty")
        for detail in self.details:
            _require_text("gate detail", detail, limit=512)


@dataclass(frozen=True, slots=True)
class QualificationReceipt:
    candidate_id: str
    lesson_content_id: str
    construction_digest: str
    suite_content_id: str
    suite_digest: str
    examiner: ExaminerIdentity
    independent_seed: str
    gates: tuple[GateResult, ...]
    passed: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("lesson_content_id", self.lesson_content_id),
            ("suite_content_id", self.suite_content_id),
        ):
            _require_identifier(name, value)
        if not isinstance(self.construction_digest, str) or re.fullmatch(
            r"[0-9a-f]{64}", self.construction_digest
        ) is None:
            raise PacketValidationError("construction_digest must be a SHA-256 digest")
        if not isinstance(self.suite_digest, str) or re.fullmatch(
            r"[0-9a-f]{64}", self.suite_digest
        ) is None:
            raise PacketValidationError("suite_digest must be a SHA-256 digest")
        if not isinstance(self.examiner, ExaminerIdentity):
            raise PacketValidationError("qualification receipt examiner is invalid")
        _require_identifier("independent_seed", self.independent_seed)
        _require_tuple("qualification gates", self.gates)
        if not self.gates or any(not isinstance(gate, GateResult) for gate in self.gates):
            raise PacketValidationError("qualification gates must contain GateResult values")
        if tuple(gate.gate for gate in self.gates) != _QUALIFICATION_GATES[: len(self.gates)]:
            raise PacketValidationError("qualification gates are not a valid ladder prefix")
        computed_pass = len(self.gates) == len(_QUALIFICATION_GATES) and all(
            gate.passed for gate in self.gates
        )
        if type(self.passed) is not bool or self.passed != computed_pass:
            raise PacketValidationError("qualification receipt pass flag contradicts its gates")

    @property
    def receipt_id(self) -> str:
        return canonical_content_id("qualification-receipt", self)

    @property
    def receipt_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class RetentionReceipt:
    candidate_id: str
    qualification_receipt_id: str
    suite_content_id: str
    suite_digest: str
    examiner: ExaminerIdentity
    independent_seed: str
    gate: GateResult
    passed: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("qualification_receipt_id", self.qualification_receipt_id),
            ("suite_content_id", self.suite_content_id),
        ):
            _require_identifier(name, value)
        if not isinstance(self.suite_digest, str) or re.fullmatch(
            r"[0-9a-f]{64}", self.suite_digest
        ) is None:
            raise PacketValidationError("retention suite_digest must be SHA-256")
        if not isinstance(self.examiner, ExaminerIdentity):
            raise PacketValidationError("retention receipt examiner is invalid")
        _require_identifier("independent_seed", self.independent_seed)
        if not isinstance(self.gate, GateResult) or self.gate.gate is not GateName.DELAYED_RETENTION_PASS:
            raise PacketValidationError("retention receipt requires DELAYED_RETENTION_PASS")
        if type(self.passed) is not bool or self.passed != self.gate.passed:
            raise PacketValidationError("retention pass flag contradicts its gate")

    @property
    def receipt_id(self) -> str:
        return canonical_content_id("retention-receipt", self)

    @property
    def receipt_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class CompiledConstruction:
    construction: GrammarConstruction
    compiler_revision: str

    def __post_init__(self) -> None:
        if not isinstance(self.construction, GrammarConstruction):
            raise PacketValidationError("compiled construction is invalid")
        _require_identifier("compiler_revision", self.compiler_revision)


def _tokenize(sentence: str) -> tuple[str, ...]:
    _require_text("sentence", sentence, limit=256)
    if _SENTENCE.fullmatch(sentence) is None:
        raise PatternCompilationError("sentence is outside the bounded token language")
    normalized = sentence.strip()
    if normalized[-1:] in {".", "!", "?"}:
        normalized = normalized[:-1]
    tokens = tuple(normalized.lower().split())
    if not tokens or len(tokens) > _MAX_SENTENCE_TOKENS:
        raise PatternCompilationError(
            f"sentence must contain 1..{_MAX_SENTENCE_TOKENS} tokens"
        )
    return tokens


class BoundedPatternCompiler:
    """Compile and interpret a deliberately small typed pattern language."""

    compiler_revision = "bounded-pattern-v0.1"

    def __init__(self, morphology: tuple[MorphologyEntry, ...] = ()) -> None:
        _require_tuple("morphology", morphology)
        if any(not isinstance(entry, MorphologyEntry) for entry in morphology):
            raise PacketValidationError("morphology must contain MorphologyEntry values")
        entries: dict[tuple[str, VerbForm], MorphologyEntry] = {}
        for entry in morphology:
            forms = (entry.form,)
            if entry.form is VerbForm.PAST_OR_PARTICIPLE:
                forms = (VerbForm.PAST, VerbForm.PARTICIPLE)
            for form in forms:
                key = (entry.surface, form)
                previous = entries.get(key)
                if previous is not None and previous.lemma != entry.lemma:
                    raise PacketValidationError("conflicting morphology entries")
                entries[key] = entry
        self._morphology = entries

    def validate(self, construction: GrammarConstruction) -> tuple[str, ...]:
        if not isinstance(construction, GrammarConstruction):
            return ("construction is not a GrammarConstruction",)
        defects: list[str] = []
        noun_slots: set[str] = set()
        verb_slots: set[str] = set()
        all_slots: list[str] = []
        literals: list[str] = []
        verb_forms: list[VerbForm] = []
        prior_kind: AtomKind | None = None
        for atom in construction.surface_pattern:
            if atom.kind is AtomKind.NOUN_PHRASE:
                if prior_kind is AtomKind.NOUN_PHRASE:
                    defects.append("adjacent noun-phrase slots are not deterministic")
                assert atom.slot is not None
                noun_slots.add(atom.slot)
                all_slots.append(atom.slot)
            elif atom.kind is AtomKind.VERB:
                assert atom.slot is not None and atom.verb_form is not None
                verb_slots.add(atom.slot)
                all_slots.append(atom.slot)
                verb_forms.append(atom.verb_form)
            else:
                assert atom.value is not None
                literals.append(atom.value)
            prior_kind = atom.kind
        if len(all_slots) != len(set(all_slots)):
            defects.append("pattern slots must be unique")
        transformation = construction.semantic_transformation
        if transformation.predicate_slot not in verb_slots:
            defects.append("predicate_slot is not bound by a verb atom")
        for role in transformation.roles:
            if role.source_slot not in noun_slots:
                defects.append(f"role {role.role!r} references an unbound noun slot")
        if not {"agent", "patient"}.issubset({role.role for role in transformation.roles}):
            defects.append("bounded transitive constructions require agent and patient")
        if transformation.voice is Voice.PASSIVE:
            if "by" not in literals or not {"was"}.intersection(literals):
                defects.append("passive constructions require literal 'was' and 'by'")
            if VerbForm.PARTICIPLE not in verb_forms:
                defects.append("passive constructions require a participle verb slot")
            if transformation.polarity is Polarity.NEGATIVE:
                defects.append("passive negation is outside bounded v0.1")
        elif transformation.polarity is Polarity.NEGATIVE:
            if "did" not in literals or "not" not in literals:
                defects.append("past active negation requires literal 'did' and 'not'")
            if VerbForm.BASE not in verb_forms:
                defects.append("past active negation requires a base verb slot")
        else:
            if "not" in literals:
                defects.append("positive constructions cannot contain literal 'not'")
            if transformation.tense is Tense.PAST and VerbForm.PAST not in verb_forms:
                defects.append("past active constructions require a past verb slot")
        return tuple(defects)

    def compile(self, construction: GrammarConstruction) -> CompiledConstruction:
        defects = self.validate(construction)
        if defects:
            raise PatternCompilationError("; ".join(defects))
        return CompiledConstruction(construction, self.compiler_revision)

    def _verb_lemma(self, surface: str, requested: VerbForm) -> str | None:
        registered = self._morphology.get((surface, requested))
        if registered is not None:
            return registered.lemma
        if requested is VerbForm.BASE:
            if surface.endswith("ed"):
                return None
            return surface
        if requested not in {VerbForm.PAST, VerbForm.PARTICIPLE}:
            return None
        if len(surface) <= 3 or not surface.endswith("ed"):
            return None
        if surface.endswith("ied") and len(surface) > 4:
            return surface[:-3] + "y"
        stem = surface[:-2]
        if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] in "bdfgmnprt":
            stem = stem[:-1]
        if stem.endswith(("v", "c", "g", "z")) or (
            stem.endswith("s") and not stem.endswith("ss")
        ):
            stem += "e"
        return stem

    def interpret(
        self, compiled: CompiledConstruction, sentence: str
    ) -> InterpretedFrame | None:
        tokens = _tokenize(sentence)
        bindings: dict[str, str] = {}
        index = 0
        for atom in compiled.construction.surface_pattern:
            if atom.kind is AtomKind.LITERAL:
                if index >= len(tokens) or tokens[index] != atom.value:
                    return None
                index += 1
            elif atom.kind is AtomKind.NOUN_PHRASE:
                if index >= len(tokens):
                    return None
                if tokens[index] == "the":
                    if index + 1 >= len(tokens):
                        return None
                    referent = tokens[index + 1]
                    index += 2
                else:
                    referent = tokens[index]
                    index += 1
                assert atom.slot is not None
                bindings[atom.slot] = referent
            else:
                if index >= len(tokens):
                    return None
                assert atom.slot is not None and atom.verb_form is not None
                lemma = self._verb_lemma(tokens[index], atom.verb_form)
                if lemma is None:
                    return None
                bindings[atom.slot] = lemma
                index += 1
        if index != len(tokens):
            return None
        transformation = compiled.construction.semantic_transformation
        predicate = bindings[transformation.predicate_slot]
        roles = tuple(
            sorted(
                SemanticRole(binding.role, bindings[binding.source_slot])
                for binding in transformation.roles
            )
        )
        frame = SemanticFrame(
            predicate=predicate,
            roles=roles,
            tense=transformation.tense,
            polarity=transformation.polarity,
        )
        return InterpretedFrame(
            semantics=frame,
            construction_content_id=compiled.construction.construction_content_id,
            construction_key=compiled.construction.construction_key,
            voice=transformation.voice,
        )

    def parse(
        self, constructions: tuple[GrammarConstruction, ...], sentence: str
    ) -> ParseResult:
        _require_tuple("constructions", constructions)
        interpreted: list[InterpretedFrame] = []
        for construction in constructions:
            compiled = self.compile(construction)
            frame = self.interpret(compiled, sentence)
            if frame is not None:
                interpreted.append(frame)
        interpreted.sort(key=lambda frame: frame.construction_content_id)
        if not interpreted:
            return ParseResult(ParseStatus.UNKNOWN_CONSTRUCTION, ())
        unique_semantics: list[SemanticFrame] = []
        for frame in interpreted:
            if frame.semantics not in unique_semantics:
                unique_semantics.append(frame.semantics)
        frames = tuple(interpreted)
        if len(unique_semantics) == 1:
            return ParseResult(ParseStatus.PARSED, frames, unique_semantics[0])
        return ParseResult(ParseStatus.AMBIGUOUS_PARSE, frames)


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    candidate_id: str
    packet: LanguageLessonPacket
    status: CandidateStatus
    logical_revision: int
    qualification_receipt_ids: tuple[str, ...] = ()
    retention_receipt_ids: tuple[str, ...] = ()
    reason: str = "teacher proposal recorded; no active grammar mutation"

    def __post_init__(self) -> None:
        _require_identifier("candidate_id", self.candidate_id)
        if not isinstance(self.packet, LanguageLessonPacket):
            raise PacketValidationError("candidate packet is invalid")
        if self.candidate_id != self.packet.packet_content_id:
            raise PacketValidationError("candidate_id does not match packet content")
        if not isinstance(self.status, CandidateStatus):
            raise PacketValidationError("candidate status is invalid")
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise PacketValidationError("candidate logical_revision must be positive")
        for name, values in (
            ("qualification_receipt_ids", self.qualification_receipt_ids),
            ("retention_receipt_ids", self.retention_receipt_ids),
        ):
            _require_tuple(name, values)
            for value in values:
                _require_identifier(name, value)
            _require_unique(name, values)
        _require_text("candidate reason", self.reason, limit=512)

    @property
    def record_id(self) -> str:
        return canonical_content_id("candidate-record", self)


@dataclass(frozen=True, slots=True)
class GrammarVersion:
    version_id: str
    candidate_id: str
    construction: GrammarConstruction
    status: VersionStatus
    logical_revision: int
    qualification_receipt_id: str
    retention_receipt_id: str | None = None
    supersedes_version_id: str | None = None
    reason: str = "receipt-gated provisional promotion"

    def __post_init__(self) -> None:
        for name, value in (
            ("version_id", self.version_id),
            ("candidate_id", self.candidate_id),
            ("qualification_receipt_id", self.qualification_receipt_id),
        ):
            _require_identifier(name, value)
        if not isinstance(self.construction, GrammarConstruction):
            raise PacketValidationError("grammar version construction is invalid")
        expected_id = canonical_content_id(
            "grammar-version",
            {
                "candidate_id": self.candidate_id,
                "construction_content_id": self.construction.construction_content_id,
            },
        )
        if self.version_id != expected_id:
            raise PacketValidationError("version_id is not canonical")
        if not isinstance(self.status, VersionStatus):
            raise PacketValidationError("grammar version status is invalid")
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise PacketValidationError("grammar version logical_revision must be positive")
        for optional_name, optional_value in (
            ("retention_receipt_id", self.retention_receipt_id),
            ("supersedes_version_id", self.supersedes_version_id),
        ):
            if optional_value is not None:
                _require_identifier(optional_name, optional_value)
        if (
            self.status is VersionStatus.LANG_ACTIVE
            and self.retention_receipt_id is None
        ):
            raise PacketValidationError("active grammar versions require a retention receipt")
        _require_text("grammar version reason", self.reason, limit=512)

    @property
    def record_id(self) -> str:
        return canonical_content_id("grammar-version-record", self)


@dataclass(frozen=True, slots=True)
class LineageEvent:
    logical_revision: int
    action: str
    target_id: str
    previous_state: str | None
    new_state: str
    reason: str
    receipt_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.logical_revision) is not int or self.logical_revision < 1:
            raise PacketValidationError("lineage logical_revision must be positive")
        _require_identifier("lineage action", self.action)
        _require_identifier("lineage target_id", self.target_id)
        if self.previous_state is not None:
            _require_identifier("lineage previous_state", self.previous_state)
        _require_identifier("lineage new_state", self.new_state)
        _require_text("lineage reason", self.reason, limit=512)
        _require_tuple("lineage receipt_ids", self.receipt_ids)
        for receipt_id in self.receipt_ids:
            _require_identifier("lineage receipt_id", receipt_id)

    @property
    def event_id(self) -> str:
        return canonical_content_id("language-lineage", self)


@dataclass(frozen=True, slots=True)
class CandidateStoreSnapshot:
    logical_revision: int
    candidates: tuple[CandidateRecord, ...]
    versions: tuple[GrammarVersion, ...]
    lineage: tuple[LineageEvent, ...]

    @property
    def snapshot_digest(self) -> str:
        return canonical_digest(self)


class VersionedCandidateStore:
    """Append-only histories for proposals and receipt-gated grammar versions."""

    def __init__(self) -> None:
        self._logical_revision = 0
        self._candidate_history: dict[str, list[CandidateRecord]] = {}
        self._version_history: dict[str, list[GrammarVersion]] = {}
        self._candidate_version: dict[str, str] = {}
        self._lineage: list[LineageEvent] = []

    def _next_revision(self) -> int:
        self._logical_revision += 1
        return self._logical_revision

    def _event(
        self,
        *,
        logical_revision: int,
        action: str,
        target_id: str,
        previous_state: str | None,
        new_state: str,
        reason: str,
        receipt_ids: tuple[str, ...] = (),
    ) -> None:
        self._lineage.append(
            LineageEvent(
                logical_revision,
                action,
                target_id,
                previous_state,
                new_state,
                reason,
                receipt_ids,
            )
        )

    def submit(self, packet: LanguageLessonPacket) -> CandidateRecord:
        if not isinstance(packet, LanguageLessonPacket):
            raise PacketValidationError("only a LanguageLessonPacket may be submitted")
        candidate_id = packet.packet_content_id
        history = self._candidate_history.get(candidate_id)
        if history is not None:
            return history[-1]
        revision = self._next_revision()
        record = CandidateRecord(
            candidate_id,
            packet,
            CandidateStatus.LANG_PROPOSED,
            revision,
        )
        self._candidate_history[candidate_id] = [record]
        self._event(
            logical_revision=revision,
            action="TEACHER_PROPOSAL_RECORDED",
            target_id=candidate_id,
            previous_state=None,
            new_state=record.status.value,
            reason=record.reason,
        )
        return record

    def candidate(self, candidate_id: str) -> CandidateRecord:
        try:
            return self._candidate_history[candidate_id][-1]
        except KeyError as exc:
            raise LifecycleError(f"unknown candidate: {candidate_id}") from exc

    def candidate_history(self, candidate_id: str) -> tuple[CandidateRecord, ...]:
        try:
            return tuple(self._candidate_history[candidate_id])
        except KeyError as exc:
            raise LifecycleError(f"unknown candidate: {candidate_id}") from exc

    def _transition_candidate(
        self,
        candidate_id: str,
        status: CandidateStatus,
        *,
        reason: str,
        qualification_receipt_id: str | None = None,
        retention_receipt_id: str | None = None,
    ) -> CandidateRecord:
        prior = self.candidate(candidate_id)
        revision = self._next_revision()
        qualification_ids = prior.qualification_receipt_ids
        if qualification_receipt_id is not None and qualification_receipt_id not in qualification_ids:
            qualification_ids += (qualification_receipt_id,)
        retention_ids = prior.retention_receipt_ids
        if retention_receipt_id is not None and retention_receipt_id not in retention_ids:
            retention_ids += (retention_receipt_id,)
        record = replace(
            prior,
            status=status,
            logical_revision=revision,
            qualification_receipt_ids=qualification_ids,
            retention_receipt_ids=retention_ids,
            reason=reason,
        )
        self._candidate_history[candidate_id].append(record)
        receipts = tuple(
            receipt
            for receipt in (qualification_receipt_id, retention_receipt_id)
            if receipt is not None
        )
        self._event(
            logical_revision=revision,
            action=f"CANDIDATE_{status.value}",
            target_id=candidate_id,
            previous_state=prior.status.value,
            new_state=status.value,
            reason=reason,
            receipt_ids=receipts,
        )
        return record

    def _create_provisional(
        self, candidate_id: str, qualification_receipt_id: str
    ) -> GrammarVersion:
        candidate = self.candidate(candidate_id)
        construction = candidate.packet.construction
        version_id = canonical_content_id(
            "grammar-version",
            {
                "candidate_id": candidate_id,
                "construction_content_id": construction.construction_content_id,
            },
        )
        if version_id in self._version_history:
            return self._version_history[version_id][-1]
        revision = self._next_revision()
        version = GrammarVersion(
            version_id=version_id,
            candidate_id=candidate_id,
            construction=construction,
            status=VersionStatus.LANG_PROVISIONAL,
            logical_revision=revision,
            qualification_receipt_id=qualification_receipt_id,
        )
        self._version_history[version_id] = [version]
        self._candidate_version[candidate_id] = version_id
        self._event(
            logical_revision=revision,
            action="GRAMMAR_PROMOTED_PROVISIONALLY",
            target_id=version_id,
            previous_state=None,
            new_state=version.status.value,
            reason=version.reason,
            receipt_ids=(qualification_receipt_id,),
        )
        return version

    def version(self, version_id: str) -> GrammarVersion:
        try:
            return self._version_history[version_id][-1]
        except KeyError as exc:
            raise LifecycleError(f"unknown grammar version: {version_id}") from exc

    def version_for_candidate(self, candidate_id: str) -> GrammarVersion:
        try:
            return self.version(self._candidate_version[candidate_id])
        except KeyError as exc:
            raise LifecycleError(f"candidate has no grammar version: {candidate_id}") from exc

    def version_history(self, version_id: str) -> tuple[GrammarVersion, ...]:
        try:
            return tuple(self._version_history[version_id])
        except KeyError as exc:
            raise LifecycleError(f"unknown grammar version: {version_id}") from exc

    def _transition_version(
        self,
        version_id: str,
        status: VersionStatus,
        *,
        reason: str,
        retention_receipt_id: str | None = None,
        supersedes_version_id: str | None = None,
    ) -> GrammarVersion:
        prior = self.version(version_id)
        revision = self._next_revision()
        version = replace(
            prior,
            status=status,
            logical_revision=revision,
            retention_receipt_id=(
                retention_receipt_id
                if retention_receipt_id is not None
                else prior.retention_receipt_id
            ),
            supersedes_version_id=(
                supersedes_version_id
                if supersedes_version_id is not None
                else prior.supersedes_version_id
            ),
            reason=reason,
        )
        self._version_history[version_id].append(version)
        receipts = tuple(
            receipt
            for receipt in (version.qualification_receipt_id, retention_receipt_id)
            if receipt is not None
        )
        self._event(
            logical_revision=revision,
            action=f"GRAMMAR_{status.value}",
            target_id=version_id,
            previous_state=prior.status.value,
            new_state=status.value,
            reason=reason,
            receipt_ids=receipts,
        )
        return version

    def active_versions(self) -> tuple[GrammarVersion, ...]:
        return tuple(
            sorted(
                (
                    history[-1]
                    for history in self._version_history.values()
                    if history[-1].status is VersionStatus.LANG_ACTIVE
                ),
                key=lambda version: version.version_id,
            )
        )

    def provisional_versions(self) -> tuple[GrammarVersion, ...]:
        return tuple(
            sorted(
                (
                    history[-1]
                    for history in self._version_history.values()
                    if history[-1].status is VersionStatus.LANG_PROVISIONAL
                ),
                key=lambda version: version.version_id,
            )
        )

    def snapshot(self) -> CandidateStoreSnapshot:
        candidates = tuple(
            sorted(
                (history[-1] for history in self._candidate_history.values()),
                key=lambda record: record.candidate_id,
            )
        )
        versions = tuple(
            sorted(
                (history[-1] for history in self._version_history.values()),
                key=lambda version: version.version_id,
            )
        )
        return CandidateStoreSnapshot(
            self._logical_revision,
            candidates,
            versions,
            tuple(self._lineage),
        )


class LanguageApprenticeship:
    """Local orchestrator for proposal, examination, and grammar lineage."""

    def __init__(self, morphology: tuple[MorphologyEntry, ...] = ()) -> None:
        self.compiler = BoundedPatternCompiler(morphology)
        self.store = VersionedCandidateStore()
        self._qualification_receipts: dict[str, QualificationReceipt] = {}
        self._retention_receipts: dict[str, RetentionReceipt] = {}

    @property
    def active_grammar_digest(self) -> str:
        return canonical_digest(
            tuple(
                version.construction.construction_content_id
                for version in self.store.active_versions()
            )
        )

    def submit_teacher_lesson(self, packet: LanguageLessonPacket) -> CandidateRecord:
        """Record a proposal only; this path cannot create active grammar."""
        return self.store.submit(packet)

    def _candidate_constructions(
        self,
        candidate: CandidateRecord,
        *,
        include_candidate: bool,
        include_provisional: bool = False,
    ) -> tuple[GrammarConstruction, ...]:
        construction = candidate.packet.construction
        selected = [
            version.construction
            for version in self.store.active_versions()
            if version.construction.construction_key != construction.construction_key
        ]
        if include_provisional:
            selected.extend(
                version.construction
                for version in self.store.provisional_versions()
                if version.candidate_id != candidate.candidate_id
                and version.construction.construction_key != construction.construction_key
            )
        if include_candidate:
            selected.append(construction)
        return tuple(selected)

    @staticmethod
    def _example_failure(
        compiler: BoundedPatternCompiler,
        constructions: tuple[GrammarConstruction, ...],
        example: SemanticExample,
    ) -> str | None:
        result = compiler.parse(constructions, example.sentence)
        if result.status is not ParseStatus.PARSED:
            return f"{example.case_id}: expected PARSED, got {result.status.value}"
        if result.semantics != example.expected:
            return f"{example.case_id}: semantic frame mismatch"
        return None

    @staticmethod
    def _pair_failures(
        compiler: BoundedPatternCompiler,
        constructions: tuple[GrammarConstruction, ...],
        pairs: tuple[MinimalPair, ...],
    ) -> tuple[str, ...]:
        failures: list[str] = []
        for pair in pairs:
            left = compiler.parse(constructions, pair.left.sentence)
            right = compiler.parse(constructions, pair.right.sentence)
            if left.status is not ParseStatus.PARSED or left.semantics != pair.left.expected:
                failures.append(f"{pair.pair_id}: left semantic mismatch")
                continue
            if right.status is not ParseStatus.PARSED or right.semantics != pair.right.expected:
                failures.append(f"{pair.pair_id}: right semantic mismatch")
                continue
            actual_same = left.semantics == right.semantics
            if (pair.relation is PairRelation.SAME_MEANING) != actual_same:
                failures.append(f"{pair.pair_id}: relation did not hold")
        return tuple(failures)

    def qualify(
        self, candidate_id: str, suite: QualificationSuite
    ) -> QualificationReceipt:
        candidate = self.store.candidate(candidate_id)
        if candidate.status is not CandidateStatus.LANG_PROPOSED:
            raise QualificationError(
                f"candidate must be PROPOSED, not {candidate.status.value}"
            )
        if suite.purpose is not SuitePurpose.QUALIFICATION:
            raise QualificationError("qualification requires a QUALIFICATION suite")
        if (
            suite.examiner.examiner == candidate.packet.teacher.model
            and suite.examiner.revision == candidate.packet.teacher.revision
        ):
            raise QualificationError("the teacher may not examine its own lesson")
        gates: list[GateResult] = []

        def gate(name: GateName, failures: tuple[str, ...], success: str) -> bool:
            passed = not failures
            gates.append(GateResult(name, passed, failures or (success,)))
            return passed

        if not gate(
            GateName.PROPOSED,
            (),
            "immutable teacher proposal is isolated from active grammar",
        ):
            raise AssertionError("the proposal gate cannot fail after typed submission")
        defects = self.compiler.validate(candidate.packet.construction)
        if not gate(GateName.SCHEMA_VALID, defects, "bounded construction schema valid"):
            return self._seal_qualification(candidate, suite, tuple(gates))
        try:
            compiled = self.compiler.compile(candidate.packet.construction)
            compile_failures: tuple[str, ...] = ()
        except PatternCompilationError as exc:
            compiled = None
            compile_failures = (str(exc),)
        if not gate(GateName.COMPILED, compile_failures, "non-eval pattern compiled"):
            return self._seal_qualification(candidate, suite, tuple(gates))
        assert compiled is not None
        positive_failures: list[str] = []
        candidate_only = (candidate.packet.construction,)
        for example in candidate.packet.positive_examples:
            failure = self._example_failure(self.compiler, candidate_only, example)
            if failure is not None:
                positive_failures.append(failure)
        if not gate(
            GateName.POSITIVE_EXAMPLES_PASS,
            tuple(positive_failures),
            f"{len(candidate.packet.positive_examples)} proposed examples reproduced",
        ):
            return self._seal_qualification(candidate, suite, tuple(gates))
        grammar = self._candidate_constructions(candidate, include_candidate=True)
        contrast_failures = list(
            self._pair_failures(self.compiler, grammar, suite.contrast_pairs)
        )
        for counterexample in suite.counterexamples:
            if self.compiler.interpret(compiled, counterexample.sentence) is not None:
                contrast_failures.append(
                    f"{counterexample.case_id}: candidate matched protected counterexample"
                )
        if not gate(
            GateName.CONTRAST_TESTS_PASS,
            tuple(contrast_failures),
            "protected minimal pairs and counterexamples held",
        ):
            return self._seal_qualification(candidate, suite, tuple(gates))
        held_out_failures = tuple(
            failure
            for failure in (
                self._example_failure(self.compiler, grammar, example)
                for example in suite.held_out_examples
            )
            if failure is not None
        )
        if not gate(
            GateName.HELD_OUT_GENERALIZATION_PASS,
            held_out_failures,
            f"{len(suite.held_out_examples)} independently seeded cases passed",
        ):
            return self._seal_qualification(candidate, suite, tuple(gates))
        regression_failures: list[str] = []
        active = tuple(version.construction for version in self.store.active_versions())
        for example in suite.regression_examples:
            before = self._example_failure(self.compiler, active, example)
            after = self._example_failure(self.compiler, grammar, example)
            if before is not None:
                regression_failures.append(f"{example.case_id}: invalid baseline: {before}")
            elif after is not None:
                regression_failures.append(f"{example.case_id}: candidate regression: {after}")
        if not gate(
            GateName.PRIOR_GRAMMAR_REGRESSION_PASS,
            tuple(regression_failures),
            (
                f"{len(suite.regression_examples)} prior-grammar guards held"
                if suite.regression_examples
                else "no prior grammar guards were applicable"
            ),
        ):
            return self._seal_qualification(candidate, suite, tuple(gates))
        ambiguity_failures: list[str] = []
        for case in suite.ambiguity_cases:
            result = self.compiler.parse(grammar, case.sentence)
            if result.status not in case.accepted_statuses:
                ambiguity_failures.append(
                    f"{case.case_id}: got {result.status.value}, expected honest uncertainty"
                )
        if not gate(
            GateName.AMBIGUITY_BEHAVIOR_PASS,
            tuple(ambiguity_failures),
            "unsupported or ambiguous inputs did not invent certainty",
        ):
            return self._seal_qualification(candidate, suite, tuple(gates))
        replay_failures: list[str] = []
        for example in suite.held_out_examples:
            first = self.compiler.parse(grammar, example.sentence)
            second = self.compiler.parse(grammar, example.sentence)
            if canonical_digest(first) != canonical_digest(second):
                replay_failures.append(f"{example.case_id}: replay digest changed")
        gate(
            GateName.DETERMINISTIC_REPLAY_PASS,
            tuple(replay_failures),
            "canonical replay digests were identical",
        )
        return self._seal_qualification(candidate, suite, tuple(gates))

    def _seal_qualification(
        self,
        candidate: CandidateRecord,
        suite: QualificationSuite,
        gates: tuple[GateResult, ...],
    ) -> QualificationReceipt:
        passed = len(gates) == len(_QUALIFICATION_GATES) and all(
            result.passed for result in gates
        )
        receipt = QualificationReceipt(
            candidate_id=candidate.candidate_id,
            lesson_content_id=candidate.packet.packet_content_id,
            construction_digest=candidate.packet.construction.construction_digest,
            suite_content_id=suite.suite_content_id,
            suite_digest=suite.suite_digest,
            examiner=suite.examiner,
            independent_seed=suite.independent_seed,
            gates=gates,
            passed=passed,
        )
        self._qualification_receipts[receipt.receipt_id] = receipt
        self.store._transition_candidate(
            candidate.candidate_id,
            CandidateStatus.LANG_QUALIFIED
            if passed
            else CandidateStatus.LANG_QUARANTINED,
            reason=(
                "independent qualification receipt passed"
                if passed
                else f"qualification stopped at {gates[-1].gate.value}"
            ),
            qualification_receipt_id=receipt.receipt_id,
        )
        return receipt

    def promote_provisionally(
        self, candidate_id: str, qualification_receipt_id: str
    ) -> GrammarVersion:
        candidate = self.store.candidate(candidate_id)
        try:
            receipt = self._qualification_receipts[qualification_receipt_id]
        except KeyError as exc:
            raise PromotionError("qualification receipt was not issued by this laboratory") from exc
        if (
            not receipt.passed
            or receipt.candidate_id != candidate_id
            or receipt.construction_digest != candidate.packet.construction.construction_digest
        ):
            raise PromotionError("qualification receipt does not authorize this candidate")
        if candidate.status is not CandidateStatus.LANG_QUALIFIED:
            raise PromotionError(f"candidate is {candidate.status.value}, not QUALIFIED")
        version = self.store._create_provisional(candidate_id, qualification_receipt_id)
        self.store._transition_candidate(
            candidate_id,
            CandidateStatus.LANG_PROVISIONAL,
            reason="passing local qualification receipt permits shadow-only provisional use",
            qualification_receipt_id=qualification_receipt_id,
        )
        return version

    def evaluate_delayed_retention(
        self,
        candidate_id: str,
        qualification_receipt_id: str,
        suite: QualificationSuite,
    ) -> RetentionReceipt:
        candidate = self.store.candidate(candidate_id)
        if candidate.status is not CandidateStatus.LANG_PROVISIONAL:
            raise QualificationError("delayed retention requires a PROVISIONAL candidate")
        try:
            qualification = self._qualification_receipts[qualification_receipt_id]
        except KeyError as exc:
            raise QualificationError("unknown local qualification receipt") from exc
        if not qualification.passed or qualification.candidate_id != candidate_id:
            raise QualificationError("qualification receipt does not match the candidate")
        if suite.purpose is not SuitePurpose.DELAYED_RETENTION:
            raise QualificationError("retention requires a DELAYED_RETENTION suite")
        if (
            suite.examiner.examiner == candidate.packet.teacher.model
            and suite.examiner.revision == candidate.packet.teacher.revision
        ):
            raise QualificationError("the teacher may not administer delayed retention")
        if suite.independent_seed == qualification.independent_seed:
            raise QualificationError("retention must use a different independent seed")
        grammar = self._candidate_constructions(candidate, include_candidate=True)
        failures = tuple(
            failure
            for failure in (
                self._example_failure(self.compiler, grammar, example)
                for example in suite.held_out_examples
            )
            if failure is not None
        )
        gate = GateResult(
            GateName.DELAYED_RETENTION_PASS,
            not failures,
            failures or (f"{len(suite.held_out_examples)} delayed cases retained",),
        )
        receipt = RetentionReceipt(
            candidate_id=candidate_id,
            qualification_receipt_id=qualification_receipt_id,
            suite_content_id=suite.suite_content_id,
            suite_digest=suite.suite_digest,
            examiner=suite.examiner,
            independent_seed=suite.independent_seed,
            gate=gate,
            passed=gate.passed,
        )
        self._retention_receipts[receipt.receipt_id] = receipt
        if not receipt.passed:
            version = self.store.version_for_candidate(candidate_id)
            self.store._transition_version(
                version.version_id,
                VersionStatus.LANG_QUARANTINED,
                reason="delayed retention failed; provisional grammar removed from shadow use",
                retention_receipt_id=receipt.receipt_id,
            )
            self.store._transition_candidate(
                candidate_id,
                CandidateStatus.LANG_QUARANTINED,
                reason="delayed retention failed",
                retention_receipt_id=receipt.receipt_id,
            )
        return receipt

    def promote_durably(
        self,
        candidate_id: str,
        qualification_receipt_id: str,
        retention_receipt_id: str,
        *,
        supersedes_version_id: str | None = None,
    ) -> GrammarVersion:
        candidate = self.store.candidate(candidate_id)
        if candidate.status is not CandidateStatus.LANG_PROVISIONAL:
            raise PromotionError("durable promotion requires a PROVISIONAL candidate")
        try:
            qualification = self._qualification_receipts[qualification_receipt_id]
            retention = self._retention_receipts[retention_receipt_id]
        except KeyError as exc:
            raise PromotionError("promotion receipt was not issued by this laboratory") from exc
        if (
            not qualification.passed
            or not retention.passed
            or qualification.candidate_id != candidate_id
            or retention.candidate_id != candidate_id
            or retention.qualification_receipt_id != qualification_receipt_id
        ):
            raise PromotionError("receipts do not authorize durable promotion")
        version = self.store.version_for_candidate(candidate_id)
        active_same_key = tuple(
            active
            for active in self.store.active_versions()
            if active.construction.construction_key
            == candidate.packet.construction.construction_key
        )
        prior: GrammarVersion | None = None
        if supersedes_version_id is not None:
            prior = self.store.version(supersedes_version_id)
            if prior.status is not VersionStatus.LANG_ACTIVE:
                raise PromotionError("the superseded grammar version is not ACTIVE")
            if (
                prior.construction.construction_key
                != candidate.packet.construction.construction_key
            ):
                raise PromotionError("only revisions of the same construction may supersede")
            if any(active.version_id != prior.version_id for active in active_same_key):
                raise PromotionError("another active revision has the same construction key")
        elif active_same_key:
            raise PromotionError("an active construction with this key must be explicitly superseded")
        activated = self.store._transition_version(
            version.version_id,
            VersionStatus.LANG_ACTIVE,
            reason="qualification and independent delayed-retention receipts passed",
            retention_receipt_id=retention_receipt_id,
            supersedes_version_id=supersedes_version_id,
        )
        if prior is not None:
            self.store._transition_version(
                prior.version_id,
                VersionStatus.LANG_SUPERSEDED,
                reason=f"superseded by receipt-gated version {activated.version_id}",
            )
            old_candidate = self.store.candidate(prior.candidate_id)
            if old_candidate.status is CandidateStatus.LANG_DURABLE:
                self.store._transition_candidate(
                    prior.candidate_id,
                    CandidateStatus.LANG_SUPERSEDED,
                    reason=f"durable grammar superseded by {activated.version_id}",
                )
        self.store._transition_candidate(
            candidate_id,
            CandidateStatus.LANG_DURABLE,
            reason="independent qualification and delayed retention both passed",
            qualification_receipt_id=qualification_receipt_id,
            retention_receipt_id=retention_receipt_id,
        )
        return activated

    def quarantine(self, version_id: str, reason: str) -> GrammarVersion:
        _require_text("quarantine reason", reason, limit=512)
        version = self.store.version(version_id)
        if version.status not in {
            VersionStatus.LANG_PROVISIONAL,
            VersionStatus.LANG_ACTIVE,
        }:
            raise LifecycleError(f"cannot quarantine a {version.status.value} version")
        quarantined = self.store._transition_version(
            version_id,
            VersionStatus.LANG_QUARANTINED,
            reason=reason,
        )
        self.store._transition_candidate(
            version.candidate_id,
            CandidateStatus.LANG_QUARANTINED,
            reason=reason,
        )
        return quarantined

    def supersede(
        self, version_id: str, replacement_version_id: str, reason: str
    ) -> GrammarVersion:
        _require_text("supersede reason", reason, limit=512)
        prior = self.store.version(version_id)
        replacement = self.store.version(replacement_version_id)
        if (
            prior.status is not VersionStatus.LANG_ACTIVE
            or replacement.status is not VersionStatus.LANG_ACTIVE
        ):
            raise LifecycleError("both grammar versions must be ACTIVE before supersession")
        if prior.construction.construction_key != replacement.construction.construction_key:
            raise LifecycleError("only revisions of the same construction may supersede")
        replacement = self.store._transition_version(
            replacement_version_id,
            VersionStatus.LANG_ACTIVE,
            reason=f"lineage link established: {reason}",
            supersedes_version_id=version_id,
        )
        superseded = self.store._transition_version(
            version_id,
            VersionStatus.LANG_SUPERSEDED,
            reason=f"superseded by {replacement.version_id}: {reason}",
        )
        self.store._transition_candidate(
            prior.candidate_id,
            CandidateStatus.LANG_SUPERSEDED,
            reason=f"superseded by {replacement.version_id}: {reason}",
        )
        return superseded

    def rollback(self, version_id: str, reason: str) -> GrammarVersion:
        _require_text("rollback reason", reason, limit=512)
        version = self.store.version(version_id)
        if version.status not in {
            VersionStatus.LANG_ACTIVE,
            VersionStatus.LANG_QUARANTINED,
        }:
            raise LifecycleError(f"cannot roll back a {version.status.value} version")
        prior: GrammarVersion | None = None
        if version.supersedes_version_id is not None:
            prior = self.store.version(version.supersedes_version_id)
            if prior.status is not VersionStatus.LANG_SUPERSEDED:
                raise LifecycleError("rollback parent is not in SUPERSEDED state")
        rolled_back = self.store._transition_version(
            version_id,
            VersionStatus.LANG_ROLLED_BACK,
            reason=reason,
        )
        self.store._transition_candidate(
            version.candidate_id,
            CandidateStatus.LANG_ROLLED_BACK,
            reason=reason,
        )
        if prior is not None:
            self.store._transition_version(
                prior.version_id,
                VersionStatus.LANG_ACTIVE,
                reason=f"restored after rollback of {version_id}",
            )
            self.store._transition_candidate(
                prior.candidate_id,
                CandidateStatus.LANG_DURABLE,
                reason=f"restored after rollback of {version_id}",
            )
        return rolled_back

    def parse(self, sentence: str, *, include_provisional: bool = False) -> ParseResult:
        versions = list(self.store.active_versions())
        if include_provisional:
            versions.extend(self.store.provisional_versions())
        constructions = tuple(version.construction for version in versions)
        return self.compiler.parse(constructions, sentence)

    def qualification_receipt(self, receipt_id: str) -> QualificationReceipt:
        try:
            return self._qualification_receipts[receipt_id]
        except KeyError as exc:
            raise QualificationError(f"unknown qualification receipt: {receipt_id}") from exc

    def retention_receipt(self, receipt_id: str) -> RetentionReceipt:
        try:
            return self._retention_receipts[receipt_id]
        except KeyError as exc:
            raise QualificationError(f"unknown retention receipt: {receipt_id}") from exc


def _demo_morphology() -> tuple[MorphologyEntry, ...]:
    return (
        MorphologyEntry("chased", "chase", VerbForm.PAST_OR_PARTICIPLE, "demo-seed-v0.1"),
        MorphologyEntry("kicked", "kick", VerbForm.PAST_OR_PARTICIPLE, "demo-seed-v0.1"),
        MorphologyEntry("opened", "open", VerbForm.PAST_OR_PARTICIPLE, "demo-seed-v0.1"),
    )


def _active_construction(revision: int = 1) -> GrammarConstruction:
    return GrammarConstruction(
        construction_key="transitive-active-past",
        revision=revision,
        surface_pattern=(
            PatternAtom.noun_phrase("agent"),
            PatternAtom.verb("predicate", VerbForm.PAST),
            PatternAtom.noun_phrase("patient"),
        ),
        semantic_transformation=SemanticTransformation(
            predicate_slot="predicate",
            roles=(RoleBindingSpec("agent", "agent"), RoleBindingSpec("patient", "patient")),
            tense=Tense.PAST,
            polarity=Polarity.POSITIVE,
            voice=Voice.ACTIVE,
        ),
        claimed_scope="regular and registered past transitive declaratives",
    )


def _passive_construction() -> GrammarConstruction:
    return GrammarConstruction(
        construction_key="transitive-passive-past",
        revision=1,
        surface_pattern=(
            PatternAtom.noun_phrase("patient"),
            PatternAtom.literal("was"),
            PatternAtom.verb("predicate", VerbForm.PARTICIPLE),
            PatternAtom.literal("by"),
            PatternAtom.noun_phrase("agent"),
        ),
        semantic_transformation=SemanticTransformation(
            predicate_slot="predicate",
            roles=(RoleBindingSpec("agent", "agent"), RoleBindingSpec("patient", "patient")),
            tense=Tense.PAST,
            polarity=Polarity.POSITIVE,
            voice=Voice.PASSIVE,
        ),
        claimed_scope="bounded was-by past passive transitive declaratives",
    )


def _negative_construction() -> GrammarConstruction:
    return GrammarConstruction(
        construction_key="transitive-active-past-negative",
        revision=1,
        surface_pattern=(
            PatternAtom.noun_phrase("agent"),
            PatternAtom.literal("did"),
            PatternAtom.literal("not"),
            PatternAtom.verb("predicate", VerbForm.BASE),
            PatternAtom.noun_phrase("patient"),
        ),
        semantic_transformation=SemanticTransformation(
            predicate_slot="predicate",
            roles=(RoleBindingSpec("agent", "agent"), RoleBindingSpec("patient", "patient")),
            tense=Tense.PAST,
            polarity=Polarity.NEGATIVE,
            voice=Voice.ACTIVE,
        ),
        claimed_scope="bounded did-not past transitive negation",
    )


def _teacher() -> TeacherIdentity:
    return TeacherIdentity("foreign-teacher-demo", "teacher-rev-1")


def _examiner() -> ExaminerIdentity:
    return ExaminerIdentity(
        "protected-language-fixtures",
        "fixture-rev-1",
        EvidenceChannel.PROTECTED_FIXTURE,
    )


def _lesson_for(construction: GrammarConstruction) -> LanguageLessonPacket:
    if construction.construction_key == "transitive-active-past":
        positive = SemanticExample(
            "teacher-active-positive",
            "The cat chased the dog.",
            SemanticFrame.event("chase", agent="cat", patient="dog"),
        )
        pair = MinimalPair(
            "teacher-active-role-reversal",
            positive,
            SemanticExample(
                "teacher-active-reversed",
                "The dog chased the cat.",
                SemanticFrame.event("chase", agent="dog", patient="cat"),
            ),
            PairRelation.DIFFERENT_MEANING,
        )
        counter = CounterexampleCase("teacher-active-counter", "The dog was chased by the cat.")
        ambiguity = AmbiguityCase(
            "teacher-active-ambiguity",
            "The cat quickly chased the dog.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    elif construction.construction_key == "transitive-passive-past":
        positive = SemanticExample(
            "teacher-passive-positive",
            "The dog was chased by the cat.",
            SemanticFrame.event("chase", agent="cat", patient="dog"),
        )
        pair = MinimalPair(
            "teacher-passive-paraphrase",
            SemanticExample(
                "teacher-passive-active-side",
                "The cat chased the dog.",
                SemanticFrame.event("chase", agent="cat", patient="dog"),
            ),
            positive,
            PairRelation.SAME_MEANING,
        )
        counter = CounterexampleCase("teacher-passive-counter", "The dog chased by the cat.")
        ambiguity = AmbiguityCase(
            "teacher-passive-ambiguity",
            "The dog was chased near the cat.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    else:
        positive = SemanticExample(
            "teacher-negative-positive",
            "Maria did not kick the ball.",
            SemanticFrame.event(
                "kick",
                agent="maria",
                patient="ball",
                polarity=Polarity.NEGATIVE,
            ),
        )
        pair = MinimalPair(
            "teacher-negative-contrast",
            SemanticExample(
                "teacher-negative-affirmative-side",
                "Maria kicked the ball.",
                SemanticFrame.event("kick", agent="maria", patient="ball"),
            ),
            positive,
            PairRelation.DIFFERENT_MEANING,
        )
        counter = CounterexampleCase("teacher-negative-counter", "Maria did not kicked the ball.")
        ambiguity = AmbiguityCase(
            "teacher-negative-ambiguity",
            "Maria probably did not kick the ball.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    return LanguageLessonPacket(
        lesson_id=f"lesson-{construction.construction_key}-r{construction.revision}",
        lesson_type=LessonType.GRAMMAR_CONSTRUCTION,
        teacher=_teacher(),
        prerequisite_rules=(),
        construction=construction,
        positive_examples=(positive,),
        minimal_pairs=(pair,),
        counterexamples=(counter,),
        ambiguity_cases=(ambiguity,),
        exceptions=(),
        teacher_confidence_basis_points=9_900,
        provenance=("owner-adopted verified apprenticeship demonstration",),
    )


def _suite_for(construction: GrammarConstruction, purpose: SuitePurpose) -> QualificationSuite:
    retention = purpose is SuitePurpose.DELAYED_RETENTION
    if construction.construction_key == "transitive-active-past":
        held_out = SemanticExample(
            "retention-active-open" if retention else "heldout-active-kick",
            "Alice opened the door." if retention else "Maria kicked the ball.",
            SemanticFrame.event(
                "open" if retention else "kick",
                agent="alice" if retention else "maria",
                patient="door" if retention else "ball",
            ),
        )
        pair = MinimalPair(
            "protected-active-role-reversal",
            SemanticExample(
                "protected-active-left",
                "The cat chased the dog.",
                SemanticFrame.event("chase", agent="cat", patient="dog"),
            ),
            SemanticExample(
                "protected-active-right",
                "The dog chased the cat.",
                SemanticFrame.event("chase", agent="dog", patient="cat"),
            ),
            PairRelation.DIFFERENT_MEANING,
        )
        counter = CounterexampleCase("protected-active-counter", "The dog was chased by the cat.")
        ambiguity = AmbiguityCase(
            "protected-active-ambiguity",
            "The cat quickly chased the dog.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    elif construction.construction_key == "transitive-passive-past":
        held_out = SemanticExample(
            "retention-passive-open" if retention else "heldout-passive-kick",
            "The door was opened by Alice."
            if retention
            else "The ball was kicked by Maria.",
            SemanticFrame.event(
                "open" if retention else "kick",
                agent="alice" if retention else "maria",
                patient="door" if retention else "ball",
            ),
        )
        pair = MinimalPair(
            "protected-passive-paraphrase",
            SemanticExample(
                "protected-passive-active-side",
                "Maria kicked the ball.",
                SemanticFrame.event("kick", agent="maria", patient="ball"),
            ),
            SemanticExample(
                "protected-passive-passive-side",
                "The ball was kicked by Maria.",
                SemanticFrame.event("kick", agent="maria", patient="ball"),
            ),
            PairRelation.SAME_MEANING,
        )
        counter = CounterexampleCase("protected-passive-counter", "The ball kicked by Maria.")
        ambiguity = AmbiguityCase(
            "protected-passive-ambiguity",
            "The ball was kicked near Maria.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    else:
        held_out = SemanticExample(
            "retention-negative-chase" if retention else "heldout-negative-open",
            "The cat did not chase the dog."
            if retention
            else "Alice did not open the door.",
            SemanticFrame.event(
                "chase" if retention else "open",
                agent="cat" if retention else "alice",
                patient="dog" if retention else "door",
                polarity=Polarity.NEGATIVE,
            ),
        )
        pair = MinimalPair(
            "protected-negative-polarity",
            SemanticExample(
                "protected-negative-positive-side",
                "Maria kicked the ball.",
                SemanticFrame.event("kick", agent="maria", patient="ball"),
            ),
            SemanticExample(
                "protected-negative-negative-side",
                "Maria did not kick the ball.",
                SemanticFrame.event(
                    "kick",
                    agent="maria",
                    patient="ball",
                    polarity=Polarity.NEGATIVE,
                ),
            ),
            PairRelation.DIFFERENT_MEANING,
        )
        counter = CounterexampleCase("protected-negative-counter", "Maria did not kicked the ball.")
        ambiguity = AmbiguityCase(
            "protected-negative-ambiguity",
            "Maria never did kick the ball.",
            (ParseStatus.UNKNOWN_CONSTRUCTION,),
        )
    return QualificationSuite(
        suite_id=(
            f"retention-{construction.construction_key}-r{construction.revision}"
            if retention
            else f"qualification-{construction.construction_key}-r{construction.revision}"
        ),
        purpose=purpose,
        examiner=_examiner(),
        independent_seed=(
            f"retention-seed-{construction.construction_key}-r{construction.revision}"
            if retention
            else f"protected-seed-{construction.construction_key}-r{construction.revision}"
        ),
        held_out_examples=(held_out,),
        contrast_pairs=() if retention else (pair,),
        counterexamples=() if retention else (counter,),
        ambiguity_cases=() if retention else (ambiguity,),
        regression_examples=(),
    )


def _teach_durably(
    apprenticeship: LanguageApprenticeship,
    construction: GrammarConstruction,
    *,
    supersedes_version_id: str | None = None,
) -> tuple[CandidateRecord, QualificationReceipt, RetentionReceipt, GrammarVersion]:
    candidate = apprenticeship.submit_teacher_lesson(_lesson_for(construction))
    qualification = apprenticeship.qualify(
        candidate.candidate_id,
        _suite_for(construction, SuitePurpose.QUALIFICATION),
    )
    apprenticeship.promote_provisionally(candidate.candidate_id, qualification.receipt_id)
    retention = apprenticeship.evaluate_delayed_retention(
        candidate.candidate_id,
        qualification.receipt_id,
        _suite_for(construction, SuitePurpose.DELAYED_RETENTION),
    )
    version = apprenticeship.promote_durably(
        candidate.candidate_id,
        qualification.receipt_id,
        retention.receipt_id,
        supersedes_version_id=supersedes_version_id,
    )
    return candidate, qualification, retention, version


def language_qualification_demo_cases() -> tuple[str, ...]:
    """Return the browser-safe identifiers accepted by the demo function."""

    return ("passive_voice", "negation", "teacher_cannot_commit")


def run_language_qualification_demo(
    case_id: str = "passive_voice",
) -> dict[str, Any]:
    """Run one deterministic local demo and return canonical JSON primitives.

    No returned object contains live runtime state, and each call starts from a
    fresh local store.  This makes the function suitable for a browser bridge
    without implying that the kernel or main conversational runtime uses it.
    """

    if case_id not in language_qualification_demo_cases():
        raise PacketValidationError(
            f"unknown demo case {case_id!r}; expected one of {language_qualification_demo_cases()}"
        )
    apprenticeship = LanguageApprenticeship(_demo_morphology())
    principle = "Foreign proposals are permitted. Foreign commitments are prohibited."
    if case_id == "teacher_cannot_commit":
        before = apprenticeship.active_grammar_digest
        candidate = apprenticeship.submit_teacher_lesson(_lesson_for(_active_construction()))
        parse = apprenticeship.parse("The cat chased the dog.")
        result = {
            "case_id": case_id,
            "principle": principle,
            "candidate_id": candidate.candidate_id,
            "candidate_status": candidate.status,
            "active_digest_before": before,
            "active_digest_after_submission": apprenticeship.active_grammar_digest,
            "active_count": len(apprenticeship.store.active_versions()),
            "parse_without_receipts": parse,
            "teacher_confidence_basis_points_informational_only": (
                candidate.packet.teacher_confidence_basis_points
            ),
            "state_scope": "LOCAL LANGUAGE STORE ONLY",
            "authority_boundary": {
                "kernel_integrated": False,
                "cncm_state_writes": 0,
                "cas_rrk_promotion_receipt": False,
            },
        }
        return to_primitive(result)

    _, _, _, active_version = _teach_durably(apprenticeship, _active_construction())
    target = _passive_construction() if case_id == "passive_voice" else _negative_construction()
    candidate = apprenticeship.submit_teacher_lesson(_lesson_for(target))
    active_count_after_teacher = len(apprenticeship.store.active_versions())
    before_parse = apprenticeship.parse(
        "The dog was chased by the cat."
        if case_id == "passive_voice"
        else "Maria did not kick the ball."
    )
    qualification = apprenticeship.qualify(
        candidate.candidate_id,
        _suite_for(target, SuitePurpose.QUALIFICATION),
    )
    provisional = apprenticeship.promote_provisionally(
        candidate.candidate_id, qualification.receipt_id
    )
    shadow_parse = apprenticeship.parse(
        "The dog was chased by the cat."
        if case_id == "passive_voice"
        else "Maria did not kick the ball.",
        include_provisional=True,
    )
    retention = apprenticeship.evaluate_delayed_retention(
        candidate.candidate_id,
        qualification.receipt_id,
        _suite_for(target, SuitePurpose.DELAYED_RETENTION),
    )
    durable = apprenticeship.promote_durably(
        candidate.candidate_id,
        qualification.receipt_id,
        retention.receipt_id,
    )
    if case_id == "passive_voice":
        left = apprenticeship.parse("The cat chased the dog.")
        right = apprenticeship.parse("The dog was chased by the cat.")
        contrast = apprenticeship.parse("The dog chased the cat.")
        semantic_law = {
            "active_equals_passive": left.semantics == right.semantics,
            "role_reversal_remains_different": left.semantics != contrast.semantics,
            "active": left,
            "passive": right,
            "role_reversed": contrast,
        }
    else:
        positive = apprenticeship.parse("Maria kicked the ball.")
        negative = apprenticeship.parse("Maria did not kick the ball.")
        semantic_law = {
            "same_predicate": (
                positive.semantics is not None
                and negative.semantics is not None
                and positive.semantics.predicate == negative.semantics.predicate
            ),
            "polarity_remains_different": positive.semantics != negative.semantics,
            "positive": positive,
            "negative": negative,
        }
    result = {
        "case_id": case_id,
        "principle": principle,
        "baseline_active_version_id": active_version.version_id,
        "candidate_id": candidate.candidate_id,
        "active_count_after_teacher_submission": active_count_after_teacher,
        "native_parse_before_qualification": before_parse,
        "qualification_receipt": qualification,
        "provisional_version": provisional,
        "shadow_parse_after_provisional": shadow_parse,
        "retention_receipt": retention,
        "durable_version": durable,
        "semantic_law": semantic_law,
        "store_snapshot_digest": apprenticeship.store.snapshot().snapshot_digest,
        "active_grammar_digest": apprenticeship.active_grammar_digest,
        "state_scope": "LOCAL LANGUAGE STORE ONLY",
        "authority_boundary": {
            "kernel_integrated": False,
            "cncm_state_writes": 0,
            "cas_rrk_promotion_receipt": False,
        },
    }
    return to_primitive(result)


__all__ = [
    "AmbiguityCase",
    "AtomKind",
    "BoundedPatternCompiler",
    "CandidateRecord",
    "CandidateStatus",
    "CandidateStoreSnapshot",
    "CompiledConstruction",
    "CounterexampleCase",
    "EvidenceChannel",
    "ExaminerIdentity",
    "GateName",
    "GateResult",
    "GrammarConstruction",
    "GrammarVersion",
    "LanguageApprenticeship",
    "LanguageApprenticeshipError",
    "LanguageLessonPacket",
    "LessonType",
    "LifecycleError",
    "LineageEvent",
    "MinimalPair",
    "MorphologyEntry",
    "PacketValidationError",
    "PairRelation",
    "ParseResult",
    "ParseStatus",
    "PatternAtom",
    "PatternCompilationError",
    "Polarity",
    "PromotionError",
    "QualificationError",
    "QualificationReceipt",
    "QualificationSuite",
    "RetentionReceipt",
    "RoleBindingSpec",
    "SemanticExample",
    "SemanticFrame",
    "SemanticRole",
    "SemanticTransformation",
    "SuitePurpose",
    "TeacherIdentity",
    "Tense",
    "VerbForm",
    "VersionStatus",
    "VersionedCandidateStore",
    "Voice",
    "language_qualification_demo_cases",
    "run_language_qualification_demo",
]
