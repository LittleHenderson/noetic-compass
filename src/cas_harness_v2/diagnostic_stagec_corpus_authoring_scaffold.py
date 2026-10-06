"""Offline Stage C corpus authoring and two-review worksheet.

This module creates a deterministic 320-group/960-row draft worksheet.  It is
deliberately a ``DRAFT / SYNTHETIC / NON_AUTHORITY`` carrier: it does not read
the retained historical W0 prompt bodies, admit any row, freeze a corpus,
authenticate reviewers, contact a provider, or authorize execution.

The worksheet does enforce the mechanical shape needed for later work:

* one contiguous canonical three-variant block per base-intent group;
* disjoint whole-group 160/80/80 draft split preassignment;
* exact prompt and row-authoring content hashes;
* no exact base-intent or prompt reuse and no template family crossing splits;
* two separately identified, content-bound structural review slots per row.

Those checks help author and review a candidate.  They are not the later
external adjudication, storage, DRC, admission, or execution evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import threading
import unicodedata
from typing import Any
import weakref

from ._strict_json import (
    MAX_DOCUMENT_BYTES,
    StrictJSONError,
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
)
from ._validation import ArtifactRef, MACHINE_ID_RE
from .diagnostic_stagec_historical_source_inventory import (
    HISTORICAL_W0_RAW_ROW_COUNT,
    HISTORICAL_W0_SOURCE_BYTE_LENGTH,
    HISTORICAL_W0_SOURCE_SCHEMA,
    HISTORICAL_W0_SOURCE_SHA256,
)
from .diagnostic_study_protocol import (
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
    DIAGNOSTIC_VARIANT_ROLES,
)


STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA = (
    "cas_harness_v2.stagec_corpus_authoring_scaffold.v1"
)
STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-corpus-authoring-scaffold+json"
)
STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID = "stagec-corpus-authoring-scaffold-v1"
STAGEC_CORPUS_AUTHORING_SUBJECT_DOMAIN = (
    "cas_harness_v2.stagec_corpus_authoring_subject.v1"
)

STAGEC_AUTHORING_GROUP_COUNT = 320
STAGEC_AUTHORING_ROW_COUNT = 960
STAGEC_AUTHORING_VARIANT_COUNT = 3
STAGEC_AUTHORING_REVIEW_SLOTS = ("A", "B")
STAGEC_AUTHORING_CARRIERS = ("base64", "plaintext", "unicode", "url")
STAGEC_AUTHORING_REVIEW_DECISIONS = (
    "APPROVE_DRAFT",
    "REJECT_DRAFT",
    "REVISE_DRAFT",
)

DIAGNOSTIC_CALIBRATION = "DIAGNOSTIC_CALIBRATION"
CONFIRMATORY = "CONFIRMATORY"
HELD_OUT_REPLICATION = "HELD_OUT_REPLICATION"
STAGEC_AUTHORING_SPLIT_ROLES = (
    DIAGNOSTIC_CALIBRATION,
    CONFIRMATORY,
    HELD_OUT_REPLICATION,
)
STAGEC_AUTHORING_SPLIT_GROUP_COUNTS = (
    (DIAGNOSTIC_CALIBRATION, 160),
    (CONFIRMATORY, 80),
    (HELD_OUT_REPLICATION, 80),
)

# These primitive-only tuples are the sealed render sources.  The frozen
# mappings below are useful inspection surfaces, but rendering never trusts
# their backing dictionaries.  Rebinding a module global or mutating a mapping
# backing through reflection therefore cannot promote the draft boundary.
_VARIANT_SLUG_ITEMS = (
    (ADVERSARIAL_PRESENT, "adversarial-present"),
    (CLEAN_ABSENT, "clean-absent"),
    (CLEAN_NULL_ABSENT, "clean-null-absent"),
)
_CLASSIFICATION_ITEMS = (
    ("lifecycle", "DRAFT"),
    ("content_status", "SYNTHETIC"),
    ("authority", "NON_AUTHORITY"),
    ("scope", "AUTHORING_WORKSHEET_ONLY"),
    ("admission", "NOT_ESTABLISHED"),
    ("evidence_relabeling", "FORBIDDEN"),
)
_HISTORICAL_W0_BOUNDARY_ITEMS = (
    ("schema_version", HISTORICAL_W0_SOURCE_SCHEMA),
    ("sha256", HISTORICAL_W0_SOURCE_SHA256),
    ("byte_length", HISTORICAL_W0_SOURCE_BYTE_LENGTH),
    ("historical_raw_row_count", HISTORICAL_W0_RAW_ROW_COUNT),
    ("role", "AGGREGATE_GAP_CONTEXT_ONLY"),
    ("prompt_body_access", "NOT_PERFORMED"),
    ("prompt_overlap_check", "NOT_PERFORMED"),
    ("row_import_count", 0),
    ("stagec_evidence_row_count", 0),
    ("evidence_relabeling", "FORBIDDEN"),
)
_CONTRACT_SCALAR_ITEMS = (
    ("required_group_count", 320),
    ("required_row_count", 960),
    ("variant_count", 3),
    ("row_order", "GROUP_THEN_CANONICAL_VARIANT"),
    ("group_assignment", "DISJOINT_WHOLE_BASE_INTENT_GROUPS"),
    ("split_assignment_status", "DRAFT_PREASSIGNMENT_NOT_FROZEN"),
    ("review_slots_per_row", 2),
    ("review_identity_authentication", "NOT_PROVIDED"),
)
_CONTRACT_VARIANT_ROLES = (
    "ADVERSARIAL_PRESENT",
    "CLEAN_ABSENT",
    "CLEAN_NULL_ABSENT",
)
_CONTRACT_SPLIT_GROUP_COUNT_ITEMS = (
    ("DIAGNOSTIC_CALIBRATION", 160),
    ("CONFIRMATORY", 80),
    ("HELD_OUT_REPLICATION", 80),
)
_CONTRACT_REVIEW_SLOTS = ("A", "B")
_CONTRACT_RECORDED_REVIEW_FIELD_ORDER = (
    "row_ordinal",
    "review_slot",
    "reviewer_id",
    "decision",
    "rationale_code",
    "subject_sha256",
)
_DRAFT_LEAKAGE_CONTROL_ITEMS = (
    ("exact_base_intent_duplicate_policy", "FORBIDDEN"),
    ("exact_prompt_duplicate_policy", "FORBIDDEN"),
    ("template_family_cross_split_policy", "FORBIDDEN"),
    ("semantic_equivalence_review", "NOT_PERFORMED"),
)
_BOUNDARY_ITEMS = (
    ("stagec_corpus", "DRAFT"),
    ("stagec_corpus_freeze", "NOT_ESTABLISHED"),
    ("double_adjudication_authority", "NOT_ESTABLISHED"),
    ("reviewer_identity_authentication", "NOT_PROVIDED"),
    ("admitted_group_count", 0),
    ("admitted_row_count", 0),
    ("execution_authority", "NOT_GRANTED"),
    ("scientific_conclusion", "NOT_ESTABLISHED"),
    ("license", "NOT LICENSED"),
    ("disclosure", "HELD"),
)

_VARIANT_SLUGS = freeze_json(dict(_VARIANT_SLUG_ITEMS))
_CLASSIFICATION = freeze_json(dict(_CLASSIFICATION_ITEMS))
_HISTORICAL_W0_BOUNDARY = freeze_json(dict(_HISTORICAL_W0_BOUNDARY_ITEMS))
_CONTRACT = freeze_json(
    {
        **dict(_CONTRACT_SCALAR_ITEMS),
        "variant_roles": list(_CONTRACT_VARIANT_ROLES),
        "split_group_counts": dict(_CONTRACT_SPLIT_GROUP_COUNT_ITEMS),
        "review_slots": list(_CONTRACT_REVIEW_SLOTS),
        "recorded_review_field_order": list(
            _CONTRACT_RECORDED_REVIEW_FIELD_ORDER
        ),
    }
)
_DRAFT_LEAKAGE_CONTROLS = freeze_json(dict(_DRAFT_LEAKAGE_CONTROL_ITEMS))
_BOUNDARY = freeze_json(dict(_BOUNDARY_ITEMS))


class StageCCorpusAuthoringScaffoldError(ValueError):
    """A draft worksheet or its exact replay failed closed."""


def _exact_immutable_json_equal(left: Any, right: Any) -> bool:
    """Compare frozen JSON recursively without Python bool/int aliases."""

    if isinstance(left, Mapping):
        if not isinstance(right, Mapping) or len(left) != len(right):
            return False
        try:
            left_keys = tuple(left)
            right_keys = tuple(right)
            if (
                any(type(key) is not str for key in left_keys)
                or any(type(key) is not str for key in right_keys)
                or set(left_keys) != set(right_keys)
            ):
                return False
            return all(
                _exact_immutable_json_equal(left[key], right[key])
                for key in left_keys
            )
        except (KeyError, TypeError, ValueError):
            return False
    if type(left) is tuple:
        return type(right) is tuple and len(left) == len(right) and all(
            _exact_immutable_json_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    if type(left) in (str, int, bool) or left is None:
        return type(left) is type(right) and left == right
    return False


class _ImmutableJSONObject(tuple, Mapping[str, Any]):
    """Tuple-backed JSON object with no dictionary or list data backing."""

    __slots__ = ()

    def __new__(
        cls,
        items: tuple[tuple[str, Any], ...],
    ) -> "_ImmutableJSONObject":
        if type(items) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            for item in items
        ):
            raise StageCCorpusAuthoringScaffoldError(
                "immutable JSON object items must be exact key/value tuples"
            )
        keys = tuple(item[0] for item in items)
        if len(keys) != len(set(keys)):
            raise StageCCorpusAuthoringScaffoldError(
                "immutable JSON object contains duplicate keys"
            )
        return tuple.__new__(cls, items)

    def __iter__(self) -> Iterator[str]:
        return (item[0] for item in tuple.__iter__(self))

    def __len__(self) -> int:
        return tuple.__len__(self)

    def __getitem__(self, key: str) -> Any:
        if type(key) is not str:
            raise KeyError(key)
        for candidate, value in tuple.__iter__(self):
            if candidate == key:
                return value
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return type(key) is str and any(
            candidate == key for candidate, _value in tuple.__iter__(self)
        )

    def __eq__(self, other: object) -> bool:
        return _exact_immutable_json_equal(self, other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    __hash__ = None


def _immutable_json_value(
    value: Any,
    _object_constructor=_ImmutableJSONObject,
    _error=StageCCorpusAuthoringScaffoldError,
) -> Any:
    def visit(node: Any) -> Any:
        if type(node) is dict:
            return _object_constructor(
                tuple((key, visit(item)) for key, item in node.items())
            )
        if type(node) is list:
            return tuple(visit(item) for item in node)
        if type(node) in (str, int, bool) or node is None:
            return node
        raise _error(
            f"artifact payload contains non-JSON type {type(node).__name__}"
        )

    return visit(value)


@dataclass(frozen=True, slots=True)
class StageCCorpusDraftRowInput:
    """Human-authored content for one exact variant slot."""

    variant_role: str
    prompt_utf8: str
    carrier: str


@dataclass(frozen=True, slots=True)
class StageCCorpusDraftGroupInput:
    """One newly authored base-intent triplet; never a historical row import."""

    group_ordinal: int
    base_intent_utf8: str
    taxonomy: str
    payload_family: str
    template_family: str
    rows: tuple[StageCCorpusDraftRowInput, ...]


@dataclass(frozen=True, slots=True)
class StageCCorpusDraftReviewInput:
    """One unauthenticated but content-bound structural review record."""

    group_ordinal: int
    variant_role: str
    review_slot: str
    reviewer_id: str
    decision: str
    rationale_code: str


def _make_artifact_semantic_validator():
    """Create one install-once validator with no mutable module backing."""

    implementation = None

    def validate(**fields: Any) -> None:
        validator = implementation
        if validator is None:
            raise StageCCorpusAuthoringScaffoldError(
                "artifact semantic validation is not installed"
            )
        validator(**fields)

    def install(validator) -> None:
        nonlocal implementation
        if implementation is not None or not callable(validator):
            raise StageCCorpusAuthoringScaffoldError(
                "artifact semantic validation may be installed exactly once"
            )
        implementation = validator

    return validate, install


(
    _validate_artifact_semantics,
    _install_artifact_semantic_validator,
) = _make_artifact_semantic_validator()
del _make_artifact_semantic_validator


@dataclass(frozen=True, slots=True)
class _StageCCorpusAuthoringScaffoldArtifactSeal:
    artifact: weakref.ReferenceType[Any]
    raw_bytes: bytes
    sha256: str
    byte_length: int
    scaffold_id: str
    counts: tuple[int, ...]
    payload: Mapping[str, Any]


_ARTIFACT_SEALS_LOCK = threading.RLock()
_ARTIFACT_SEALS: dict[
    int, _StageCCorpusAuthoringScaffoldArtifactSeal
] = {}


def _register_artifact_seal(
    artifact: Any,
    *,
    raw_bytes: bytes,
    sha256: str,
    byte_length: int,
    scaffold_id: str,
    counts: tuple[int, ...],
    payload: Mapping[str, Any],
    _seals: dict[
        int, _StageCCorpusAuthoringScaffoldArtifactSeal
    ] = _ARTIFACT_SEALS,
    _lock: threading.RLock = _ARTIFACT_SEALS_LOCK,
) -> None:
    identity = id(artifact)

    def remove(reference: weakref.ReferenceType[Any]) -> None:
        with _lock:
            current = _seals.get(identity)
            if current is not None and current.artifact is reference:
                del _seals[identity]

    reference = weakref.ref(artifact, remove)
    seal = _StageCCorpusAuthoringScaffoldArtifactSeal(
        artifact=reference,
        raw_bytes=raw_bytes,
        sha256=sha256,
        byte_length=byte_length,
        scaffold_id=scaffold_id,
        counts=counts,
        payload=payload,
    )
    with _lock:
        _seals[identity] = seal


def _require_artifact_seal(
    artifact: Any,
    _seals: dict[
        int, _StageCCorpusAuthoringScaffoldArtifactSeal
    ] = _ARTIFACT_SEALS,
    _lock: threading.RLock = _ARTIFACT_SEALS_LOCK,
) -> _StageCCorpusAuthoringScaffoldArtifactSeal:
    with _lock:
        seal = _seals.get(id(artifact))
        if seal is None or seal.artifact() is not artifact:
            raise StageCCorpusAuthoringScaffoldError(
                "artifact is not an exact process-sealed factory result"
            )
        try:
            counts = (
                artifact.authored_group_count,
                artifact.authored_row_count,
                artifact.recorded_review_count,
                artifact.two_review_row_count,
                artifact.two_review_approve_row_count,
                artifact.admitted_group_count,
                artifact.admitted_row_count,
            )
            if (
                type(artifact.raw_bytes) is not bytes
                or type(artifact.sha256) is not str
                or type(artifact.byte_length) is not int
                or type(artifact.scaffold_id) is not str
                or any(type(value) is not int for value in counts)
                or artifact.raw_bytes is not seal.raw_bytes
                or artifact.payload is not seal.payload
                or artifact.sha256 != seal.sha256
                or artifact.byte_length != seal.byte_length
                or artifact.scaffold_id != seal.scaffold_id
                or counts != seal.counts
            ):
                raise StageCCorpusAuthoringScaffoldError(
                    "artifact differs from its exact process seal"
                )
        except AttributeError as exc:
            raise StageCCorpusAuthoringScaffoldError(
                "artifact differs from its exact process seal"
            ) from exc
        return seal


@dataclass(frozen=True, slots=True, init=False, eq=False, weakref_slot=True)
class StageCCorpusAuthoringScaffoldArtifact:
    """Immutable canonical draft worksheet and non-authority progress counts."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    scaffold_id: str
    authored_group_count: int
    authored_row_count: int
    recorded_review_count: int
    two_review_row_count: int
    two_review_approve_row_count: int
    admitted_group_count: int
    admitted_row_count: int
    payload: Mapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCCorpusAuthoringScaffoldArtifact is factory-only; use "
            "build_stagec_corpus_authoring_scaffold or "
            "load_stagec_corpus_authoring_scaffold"
        )

    def __eq__(
        self,
        other: object,
        _require_seal=_require_artifact_seal,
        _exact_json_equal=_exact_immutable_json_equal,
    ) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        try:
            left = _require_seal(self)
            right = _require_seal(other)
        except StageCCorpusAuthoringScaffoldError:
            return False
        return (
            left.raw_bytes == right.raw_bytes
            and left.sha256 == right.sha256
            and left.byte_length == right.byte_length
            and left.scaffold_id == right.scaffold_id
            and left.counts == right.counts
            and _exact_json_equal(left.payload, right.payload)
        )

    def __ne__(self, other: object) -> bool:
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    __hash__ = None

    @property
    def artifact_ref(
        self,
        _media_type: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE,
        _constructor=ArtifactRef,
        _require_seal=_require_artifact_seal,
        _validate_semantics=_validate_artifact_semantics,
    ) -> ArtifactRef:
        seal = _require_seal(self)
        _validate_semantics(
            raw_bytes=seal.raw_bytes,
            sha256=seal.sha256,
            byte_length=seal.byte_length,
            scaffold_id=seal.scaffold_id,
            counts=seal.counts,
            payload=seal.payload,
        )
        return _constructor(
            artifact_id=seal.scaffold_id,
            sha256=seal.sha256,
            byte_length=seal.byte_length,
            media_type=_media_type,
        )


def _fail(message: str) -> None:
    raise StageCCorpusAuthoringScaffoldError(message)


def _expect_keys(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{path} must be an exact JSON object")
    if set(value) != expected:
        _fail(f"{path} must contain the exact closed field set")
    return value


def _expect_exact_list(value: Any, *, length: int, path: str) -> list[Any]:
    if type(value) is not list or len(value) != length:
        _fail(f"{path} must be an exact {length}-item JSON array")
    return value


def _expect_ordinal(
    value: Any,
    path: str,
    _group_count: int = STAGEC_AUTHORING_GROUP_COUNT,
) -> int:
    if type(value) is not int or not 1 <= value <= _group_count:
        _fail(f"{path} must be an exact integer in [1, 320]")
    return value


def _expect_machine_text(value: Any, path: str) -> str:
    if (
        type(value) is not str
        or not MACHINE_ID_RE.fullmatch(value)
        or unicodedata.normalize("NFC", value) != value
    ):
        _fail(f"{path} must be a normalized ASCII machine identifier")
    return value


def _expect_authored_text(
    value: Any,
    path: str,
    *,
    maximum_canonical_bytes: int,
    _canonicalize=canonical_json_bytes,
) -> str:
    if type(value) is not str or not value.strip():
        _fail(f"{path} must be nonblank exact text")
    if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        _fail(f"{path} contains forbidden Unicode")
    if unicodedata.normalize("NFC", value) != value:
        _fail(f"{path} must be NFC-normalized")
    try:
        encoded = _canonicalize(value)
    except StrictJSONError as exc:
        raise StageCCorpusAuthoringScaffoldError(
            f"{path} is outside the strict JSON profile"
        ) from exc
    if len(encoded) > maximum_canonical_bytes:
        _fail(f"{path} exceeds its canonical byte bound")
    return value


def _split_role(
    group_ordinal: int,
    _diagnostic: str = DIAGNOSTIC_CALIBRATION,
    _confirmatory: str = CONFIRMATORY,
    _held_out: str = HELD_OUT_REPLICATION,
) -> str:
    if group_ordinal <= 160:
        return _diagnostic
    if group_ordinal <= 240:
        return _confirmatory
    return _held_out


def _group_id(group_ordinal: int) -> str:
    return f"stagec-draft-group-{group_ordinal:03d}"


def _case_id(
    group_ordinal: int,
    variant_role: str,
    _variant_slug_items: tuple[tuple[str, str], ...] = _VARIANT_SLUG_ITEMS,
) -> str:
    slugs = dict(_variant_slug_items)
    return f"stagec-draft-case-{group_ordinal:03d}-{slugs[variant_role]}"


def _subject_value(
    *,
    group: StageCCorpusDraftGroupInput,
    row: StageCCorpusDraftRowInput,
    _domain: str = STAGEC_CORPUS_AUTHORING_SUBJECT_DOMAIN,
    _group_id_value=_group_id,
    _split_role_value=_split_role,
    _case_id_value=_case_id,
    _sha256=sha256_bytes,
) -> dict[str, Any]:
    prompt_sha256 = _sha256(row.prompt_utf8.encode("utf-8"))
    return {
        "domain": _domain,
        "group_ordinal": group.group_ordinal,
        "base_intent_group_id": _group_id_value(group.group_ordinal),
        "split_role": _split_role_value(group.group_ordinal),
        "base_intent_utf8": group.base_intent_utf8,
        "taxonomy": group.taxonomy,
        "payload_family": group.payload_family,
        "template_family": group.template_family,
        "case_id": _case_id_value(group.group_ordinal, row.variant_role),
        "variant_role": row.variant_role,
        "frozen_label": row.variant_role,
        "prompt_utf8": row.prompt_utf8,
        "prompt_sha256": prompt_sha256,
        "carrier": row.carrier,
    }


def derive_stagec_corpus_authoring_subject_sha256(
    group: StageCCorpusDraftGroupInput,
    row: StageCCorpusDraftRowInput,
    _subject_value_factory=_subject_value,
    _canonical_hash=canonical_sha256,
) -> str:
    """Derive one exact draft-row content identity without external access."""

    _validate_group_input(group)
    if type(row) is not StageCCorpusDraftRowInput or row not in group.rows:
        _fail("row must be one exact member of the validated group input")
    return _canonical_hash(_subject_value_factory(group=group, row=row))


def _validate_group_input(
    group: StageCCorpusDraftGroupInput,
    _variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
    _carriers: tuple[str, ...] = STAGEC_AUTHORING_CARRIERS,
) -> StageCCorpusDraftGroupInput:
    if type(group) is not StageCCorpusDraftGroupInput:
        _fail("authored_groups must contain exact StageCCorpusDraftGroupInput values")
    ordinal = _expect_ordinal(group.group_ordinal, "group.group_ordinal")
    _expect_authored_text(
        group.base_intent_utf8,
        f"group[{ordinal}].base_intent_utf8",
        maximum_canonical_bytes=4_096,
    )
    _expect_machine_text(group.taxonomy, f"group[{ordinal}].taxonomy")
    _expect_machine_text(group.payload_family, f"group[{ordinal}].payload_family")
    _expect_machine_text(group.template_family, f"group[{ordinal}].template_family")
    if type(group.rows) is not tuple or len(group.rows) != 3:
        _fail(f"group[{ordinal}].rows must be one exact three-row tuple")
    for index, (row, expected_variant) in enumerate(
        zip(group.rows, _variant_roles, strict=True),
        start=1,
    ):
        if type(row) is not StageCCorpusDraftRowInput:
            _fail(f"group[{ordinal}].rows[{index}] has the wrong exact type")
        if type(row.variant_role) is not str or row.variant_role != expected_variant:
            _fail(f"group[{ordinal}] rows must use the canonical variant order")
        _expect_authored_text(
            row.prompt_utf8,
            f"group[{ordinal}].rows[{index}].prompt_utf8",
            maximum_canonical_bytes=8_192,
        )
        if (
            type(row.carrier) is not str
            or row.carrier not in _carriers
        ):
            _fail(f"group[{ordinal}].rows[{index}].carrier is outside the closed enum")
    return group


def _validate_review_input(
    review: StageCCorpusDraftReviewInput,
    _variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
    _review_slots: tuple[str, ...] = _CONTRACT_REVIEW_SLOTS,
    _review_decisions: tuple[str, ...] = STAGEC_AUTHORING_REVIEW_DECISIONS,
) -> StageCCorpusDraftReviewInput:
    if type(review) is not StageCCorpusDraftReviewInput:
        _fail("reviews must contain exact StageCCorpusDraftReviewInput values")
    ordinal = _expect_ordinal(review.group_ordinal, "review.group_ordinal")
    if (
        type(review.variant_role) is not str
        or review.variant_role not in _variant_roles
    ):
        _fail(f"review for group {ordinal} has a noncanonical variant")
    if (
        type(review.review_slot) is not str
        or review.review_slot not in _review_slots
    ):
        _fail(f"review for group {ordinal} has a noncanonical review slot")
    _expect_machine_text(review.reviewer_id, "review.reviewer_id")
    if (
        type(review.decision) is not str
        or review.decision not in _review_decisions
    ):
        _fail("review.decision is outside the closed draft-review enum")
    _expect_machine_text(review.rationale_code, "review.rationale_code")
    return review


def _prepare_inputs(
    authored_groups: tuple[StageCCorpusDraftGroupInput, ...],
    reviews: tuple[StageCCorpusDraftReviewInput, ...],
    _validate_group=_validate_group_input,
    _validate_review=_validate_review_input,
    _split_role_value=_split_role,
    _sha256=sha256_bytes,
) -> tuple[
    dict[int, StageCCorpusDraftGroupInput],
    dict[tuple[int, str, str], StageCCorpusDraftReviewInput],
]:
    if type(authored_groups) is not tuple:
        _fail("authored_groups must be an exact tuple")
    if type(reviews) is not tuple:
        _fail("reviews must be an exact tuple")

    groups: dict[int, StageCCorpusDraftGroupInput] = {}
    base_intent_sha256s: set[str] = set()
    prompt_sha256s: set[str] = set()
    template_splits: dict[str, set[str]] = defaultdict(set)
    for group in authored_groups:
        group = _validate_group(group)
        if group.group_ordinal in groups:
            _fail("authored_groups contains a duplicate group ordinal")
        base_intent_sha256 = _sha256(group.base_intent_utf8.encode("utf-8"))
        if base_intent_sha256 in base_intent_sha256s:
            _fail("authored_groups contains an exact duplicate base intent")
        base_intent_sha256s.add(base_intent_sha256)
        for row in group.rows:
            prompt_sha256 = _sha256(row.prompt_utf8.encode("utf-8"))
            if prompt_sha256 in prompt_sha256s:
                _fail("authored_groups contains an exact duplicate prompt")
            prompt_sha256s.add(prompt_sha256)
        template_splits[group.template_family].add(
            _split_role_value(group.group_ordinal)
        )
        groups[group.group_ordinal] = group
    if any(len(splits) != 1 for splits in template_splits.values()):
        _fail("a template family crosses draft split boundaries")

    review_map: dict[
        tuple[int, str, str], StageCCorpusDraftReviewInput
    ] = {}
    for review in reviews:
        review = _validate_review(review)
        if review.group_ordinal not in groups:
            _fail("a review targets a row that has not been authored")
        key = (review.group_ordinal, review.variant_role, review.review_slot)
        if key in review_map:
            _fail("reviews contains a duplicate group/variant/slot record")
        review_map[key] = review

    for group_ordinal, group in groups.items():
        for row in group.rows:
            left = review_map.get((group_ordinal, row.variant_role, "A"))
            right = review_map.get((group_ordinal, row.variant_role, "B"))
            if (
                left is not None
                and right is not None
                and left.reviewer_id == right.reviewer_id
            ):
                _fail("the two review slots for a row must use distinct reviewer IDs")
    return groups, review_map


def _recorded_review_value(
    review: StageCCorpusDraftReviewInput,
    subject_sha256: str,
    _variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
) -> list[Any]:
    row_ordinal = (
        (review.group_ordinal - 1) * 3
        + _variant_roles.index(review.variant_role)
        + 1
    )
    return [
        row_ordinal,
        review.review_slot,
        review.reviewer_id,
        review.decision,
        review.rationale_code,
        subject_sha256,
    ]


def _render_value(
    authored_groups: tuple[StageCCorpusDraftGroupInput, ...],
    reviews: tuple[StageCCorpusDraftReviewInput, ...],
    _classification_items: tuple[tuple[str, Any], ...] = _CLASSIFICATION_ITEMS,
    _historical_items: tuple[
        tuple[str, Any], ...
    ] = _HISTORICAL_W0_BOUNDARY_ITEMS,
    _contract_scalar_items: tuple[
        tuple[str, Any], ...
    ] = _CONTRACT_SCALAR_ITEMS,
    _contract_variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
    _contract_split_items: tuple[
        tuple[str, int], ...
    ] = _CONTRACT_SPLIT_GROUP_COUNT_ITEMS,
    _contract_review_slots: tuple[str, ...] = _CONTRACT_REVIEW_SLOTS,
    _contract_review_fields: tuple[
        str, ...
    ] = _CONTRACT_RECORDED_REVIEW_FIELD_ORDER,
    _leakage_items: tuple[
        tuple[str, str], ...
    ] = _DRAFT_LEAKAGE_CONTROL_ITEMS,
    _boundary_items: tuple[tuple[str, Any], ...] = _BOUNDARY_ITEMS,
    _variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
    _review_slots: tuple[str, ...] = _CONTRACT_REVIEW_SLOTS,
    _carriers: tuple[str, ...] = STAGEC_AUTHORING_CARRIERS,
    _group_count: int = 320,
    _row_count: int = 960,
    _schema: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA,
    _scaffold_id: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
    _prepare=_prepare_inputs,
    _subject_value_factory=_subject_value,
    _review_value_factory=_recorded_review_value,
    _case_id_value=_case_id,
    _group_id_value=_group_id,
    _split_role_value=_split_role,
    _sha256=sha256_bytes,
    _canonical_hash=canonical_sha256,
) -> dict[str, Any]:
    groups, review_map = _prepare(authored_groups, reviews)
    rendered_groups: list[dict[str, Any]] = []
    review_count_by_row: Counter[tuple[int, str]] = Counter()
    decision_by_row: dict[tuple[int, str], list[str]] = defaultdict(list)
    carrier_counts: Counter[str] = Counter()
    taxonomy_counts: Counter[str] = Counter()
    payload_family_counts: Counter[str] = Counter()
    template_family_counts: Counter[str] = Counter()
    rendered_reviews: list[list[Any]] = []

    for group_ordinal in range(1, _group_count + 1):
        group = groups.get(group_ordinal)
        if group is None:
            authoring = {
                "status": "PENDING",
                "source_classification": "NEW_STAGEC_SYNTHETIC_DRAFT",
                "base_intent_utf8": None,
                "base_intent_sha256": None,
                "taxonomy": None,
                "payload_family": None,
                "template_family": None,
            }
        else:
            authoring = {
                "status": "AUTHORED_DRAFT",
                "source_classification": "NEW_STAGEC_SYNTHETIC_DRAFT",
                "base_intent_utf8": group.base_intent_utf8,
                "base_intent_sha256": _sha256(
                    group.base_intent_utf8.encode("utf-8")
                ),
                "taxonomy": group.taxonomy,
                "payload_family": group.payload_family,
                "template_family": group.template_family,
            }
            taxonomy_counts[group.taxonomy] += 3
            payload_family_counts[group.payload_family] += 3
            template_family_counts[group.template_family] += 3

        rendered_rows: list[dict[str, Any]] = []
        for row_ordinal_in_group, variant_role in enumerate(
            _variant_roles,
            start=1,
        ):
            row_ordinal = (group_ordinal - 1) * 3 + row_ordinal_in_group
            row = None if group is None else group.rows[row_ordinal_in_group - 1]
            if row is None:
                prompt_utf8 = None
                prompt_sha256 = None
                carrier = None
                subject_sha256 = None
            else:
                prompt_utf8 = row.prompt_utf8
                prompt_sha256 = _sha256(row.prompt_utf8.encode("utf-8"))
                carrier = row.carrier
                subject_sha256 = _canonical_hash(
                    _subject_value_factory(group=group, row=row)
                )
                carrier_counts[carrier] += 1

            for slot in _review_slots:
                review = review_map.get((group_ordinal, variant_role, slot))
                if review is not None:
                    if subject_sha256 is None:
                        _fail("a review cannot bind an unauthored row")
                    rendered_reviews.append(
                        _review_value_factory(review, subject_sha256)
                    )
                    review_count_by_row[(group_ordinal, variant_role)] += 1
                    decision_by_row[(group_ordinal, variant_role)].append(
                        review.decision
                    )

            rendered_rows.append(
                {
                    "row_ordinal": row_ordinal,
                    "case_id": _case_id_value(group_ordinal, variant_role),
                    "variant_role": variant_role,
                    "frozen_label": variant_role,
                    "prompt_utf8": prompt_utf8,
                    "prompt_sha256": prompt_sha256,
                    "carrier": carrier,
                    "authoring_subject_sha256": subject_sha256,
                }
            )
        rendered_groups.append(
            {
                "group_ordinal": group_ordinal,
                "base_intent_group_id": _group_id_value(group_ordinal),
                "split_role": _split_role_value(group_ordinal),
                "authoring": authoring,
                "rows": rendered_rows,
            }
        )

    unreviewed = sum(
        count == 0
        for count in (
            review_count_by_row.get((group, variant), 0)
            for group in range(1, _group_count + 1)
            for variant in _variant_roles
        )
    )
    single_review = sum(value == 1 for value in review_count_by_row.values())
    two_review = sum(value == 2 for value in review_count_by_row.values())
    agreements = sum(
        len(decisions) == 2 and decisions[0] == decisions[1]
        for decisions in decision_by_row.values()
    )
    approves = sum(
        decisions == ["APPROVE_DRAFT", "APPROVE_DRAFT"]
        for decisions in decision_by_row.values()
    )
    nonapproves = sum(
        len(decisions) == 2
        and decisions[0] == decisions[1]
        and decisions[0] != "APPROVE_DRAFT"
        for decisions in decision_by_row.values()
    )
    disagreements = sum(
        len(decisions) == 2 and decisions[0] != decisions[1]
        for decisions in decision_by_row.values()
    )
    progress = {
        "status": "DRAFT",
        "required_group_count": _group_count,
        "required_row_count": _row_count,
        "authored_group_count": len(groups),
        "authored_row_count": len(groups) * 3,
        "pending_group_count": _group_count - len(groups),
        "pending_row_count": _row_count - len(groups) * 3,
        "recorded_review_count": len(review_map),
        "unreviewed_row_count": unreviewed,
        "single_review_row_count": single_review,
        "two_review_row_count": two_review,
        "two_review_agreement_row_count": agreements,
        "two_review_approve_row_count": approves,
        "two_review_nonapprove_row_count": nonapproves,
        "two_review_disagreement_row_count": disagreements,
        "admitted_group_count": 0,
        "admitted_row_count": 0,
    }
    inventory = {
        "carrier_row_counts": {
            carrier: carrier_counts[carrier]
            for carrier in _carriers
        },
        "taxonomy_row_counts": [
            {"taxonomy": key, "row_count": taxonomy_counts[key]}
            for key in sorted(taxonomy_counts)
        ],
        "payload_family_row_counts": [
            {"payload_family": key, "row_count": payload_family_counts[key]}
            for key in sorted(payload_family_counts)
        ],
        "template_family_row_counts": [
            {"template_family": key, "row_count": template_family_counts[key]}
            for key in sorted(template_family_counts)
        ],
        "counts_status": "DRAFT_NOT_FROZEN",
        "contingency_table_status": "NOT_ESTABLISHED",
    }
    contract = {
        **dict(_contract_scalar_items),
        "variant_roles": list(_contract_variant_roles),
        "split_group_counts": dict(_contract_split_items),
        "review_slots": list(_contract_review_slots),
        "recorded_review_field_order": list(_contract_review_fields),
    }
    return {
        "schema_version": _schema,
        "scaffold_id": _scaffold_id,
        "classification": dict(_classification_items),
        "historical_w0_boundary": dict(_historical_items),
        "contract": contract,
        "draft_leakage_controls": dict(_leakage_items),
        "groups": rendered_groups,
        "recorded_reviews": rendered_reviews,
        "progress": progress,
        "draft_inventory": inventory,
        "boundary": dict(_boundary_items),
    }


def _artifact(
    raw: bytes,
    value: dict[str, Any],
    _scaffold_id: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
    _sha256=sha256_bytes,
    _payload_freezer=_immutable_json_value,
    _constructor=StageCCorpusAuthoringScaffoldArtifact,
    _register_seal=_register_artifact_seal,
    _validate_semantics=_validate_artifact_semantics,
) -> StageCCorpusAuthoringScaffoldArtifact:
    progress = value["progress"]
    digest = _sha256(raw)
    payload = _payload_freezer(value)
    counts = (
        progress["authored_group_count"],
        progress["authored_row_count"],
        progress["recorded_review_count"],
        progress["two_review_row_count"],
        progress["two_review_approve_row_count"],
        0,
        0,
    )
    _validate_semantics(
        raw_bytes=raw,
        sha256=digest,
        byte_length=len(raw),
        scaffold_id=_scaffold_id,
        counts=counts,
        payload=payload,
    )
    artifact = object.__new__(_constructor)
    for name, item in (
        ("raw_bytes", raw),
        ("sha256", digest),
        ("byte_length", len(raw)),
        ("scaffold_id", _scaffold_id),
        ("authored_group_count", counts[0]),
        ("authored_row_count", counts[1]),
        ("recorded_review_count", counts[2]),
        ("two_review_row_count", counts[3]),
        ("two_review_approve_row_count", counts[4]),
        ("admitted_group_count", counts[5]),
        ("admitted_row_count", counts[6]),
        ("payload", payload),
    ):
        object.__setattr__(artifact, name, item)
    _register_seal(
        artifact,
        raw_bytes=raw,
        sha256=digest,
        byte_length=len(raw),
        scaffold_id=_scaffold_id,
        counts=counts,
        payload=payload,
    )
    return artifact


def _bind_scaffold_builder(
    render,
    canonicalize,
    artifact_factory,
    maximum_document_bytes: int,
    fail,
):
    def build_stagec_corpus_authoring_scaffold(
        *,
        authored_groups: tuple[StageCCorpusDraftGroupInput, ...] = (),
        reviews: tuple[StageCCorpusDraftReviewInput, ...] = (),
    ) -> StageCCorpusAuthoringScaffoldArtifact:
        """Build a deterministic draft; never build an admission carrier."""

        value = render(authored_groups, reviews)
        raw = canonicalize(value)
        if len(raw) > maximum_document_bytes:
            fail("the draft worksheet exceeds the strict 2,000,000-byte limit")
        return artifact_factory(raw, value)

    return build_stagec_corpus_authoring_scaffold


build_stagec_corpus_authoring_scaffold = _bind_scaffold_builder(
    _render_value,
    canonical_json_bytes,
    _artifact,
    MAX_DOCUMENT_BYTES,
    _fail,
)
del _bind_scaffold_builder


def _parse_scaffold_inputs(
    value: dict[str, Any],
    _group_count: int = 320,
    _row_count: int = 960,
    _variant_roles: tuple[str, ...] = _CONTRACT_VARIANT_ROLES,
    _group_id_value=_group_id,
    _case_id_value=_case_id,
    _split_role_value=_split_role,
) -> tuple[
    tuple[StageCCorpusDraftGroupInput, ...],
    tuple[StageCCorpusDraftReviewInput, ...],
]:
    _expect_keys(
        value,
        {
            "schema_version",
            "scaffold_id",
            "classification",
            "historical_w0_boundary",
            "contract",
            "draft_leakage_controls",
            "groups",
            "recorded_reviews",
            "progress",
            "draft_inventory",
            "boundary",
        },
        "$",
    )
    groups_value = _expect_exact_list(
        value["groups"], length=_group_count, path="$.groups"
    )
    authored_groups: list[StageCCorpusDraftGroupInput] = []
    reviews: list[StageCCorpusDraftReviewInput] = []
    for expected_group_ordinal, group_value in enumerate(groups_value, start=1):
        group = _expect_keys(
            group_value,
            {
                "group_ordinal",
                "base_intent_group_id",
                "split_role",
                "authoring",
                "rows",
            },
            f"$.groups[{expected_group_ordinal - 1}]",
        )
        if group["group_ordinal"] != expected_group_ordinal:
            _fail("$.groups must retain exact ordinal order")
        if group["base_intent_group_id"] != _group_id_value(
            expected_group_ordinal
        ):
            _fail("a generated draft group ID drifted")
        if group["split_role"] != _split_role_value(expected_group_ordinal):
            _fail("a draft whole-group split preassignment drifted")
        authoring = _expect_keys(
            group["authoring"],
            {
                "status",
                "source_classification",
                "base_intent_utf8",
                "base_intent_sha256",
                "taxonomy",
                "payload_family",
                "template_family",
            },
            f"$.groups[{expected_group_ordinal - 1}].authoring",
        )
        rows_value = _expect_exact_list(
            group["rows"],
            length=3,
            path=f"$.groups[{expected_group_ordinal - 1}].rows",
        )
        authored = authoring["status"] == "AUTHORED_DRAFT"
        if authoring["status"] not in {"PENDING", "AUTHORED_DRAFT"}:
            _fail("group authoring status is outside the closed draft enum")
        row_inputs: list[StageCCorpusDraftRowInput] = []
        for row_index, (row_value, expected_variant) in enumerate(
            zip(rows_value, _variant_roles, strict=True)
        ):
            row = _expect_keys(
                row_value,
                {
                    "row_ordinal",
                    "case_id",
                    "variant_role",
                    "frozen_label",
                    "prompt_utf8",
                    "prompt_sha256",
                    "carrier",
                    "authoring_subject_sha256",
                },
                f"$.groups[{expected_group_ordinal - 1}].rows[{row_index}]",
            )
            expected_row_ordinal = (expected_group_ordinal - 1) * 3 + row_index + 1
            if (
                row["row_ordinal"] != expected_row_ordinal
                or row["case_id"]
                != _case_id_value(expected_group_ordinal, expected_variant)
                or row["variant_role"] != expected_variant
                or row["frozen_label"] != expected_variant
            ):
                _fail("a generated draft row identity or canonical variant order drifted")
            if authored:
                row_inputs.append(
                    StageCCorpusDraftRowInput(
                        variant_role=row["variant_role"],
                        prompt_utf8=row["prompt_utf8"],
                        carrier=row["carrier"],
                    )
                )
        if authored:
            authored_groups.append(
                StageCCorpusDraftGroupInput(
                    group_ordinal=expected_group_ordinal,
                    base_intent_utf8=authoring["base_intent_utf8"],
                    taxonomy=authoring["taxonomy"],
                    payload_family=authoring["payload_family"],
                    template_family=authoring["template_family"],
                    rows=tuple(row_inputs),
                )
            )
    recorded_reviews = value["recorded_reviews"]
    if type(recorded_reviews) is not list:
        _fail("$.recorded_reviews must be an exact JSON array")
    for index, review in enumerate(recorded_reviews):
        if type(review) is not list or len(review) != 6:
            _fail(f"$.recorded_reviews[{index}] must follow the six-field order")
        row_ordinal, slot, reviewer_id, decision, rationale_code, _subject = review
        if type(row_ordinal) is not int or not 1 <= row_ordinal <= _row_count:
            _fail(f"$.recorded_reviews[{index}][0] must be a row ordinal")
        group_ordinal = (row_ordinal - 1) // 3 + 1
        variant_role = _variant_roles[(row_ordinal - 1) % 3]
        reviews.append(
            StageCCorpusDraftReviewInput(
                group_ordinal=group_ordinal,
                variant_role=variant_role,
                review_slot=slot,
                reviewer_id=reviewer_id,
                decision=decision,
                rationale_code=rationale_code,
            )
        )
    return tuple(authored_groups), tuple(reviews)


def _strict_replay_stagec_corpus_authoring_scaffold(
    raw: bytes,
    _parse_json=load_json_object,
    _canonicalize=canonical_json_bytes,
    _parse_inputs=_parse_scaffold_inputs,
    _render=_render_value,
    _fail_closed=_fail,
    _strict_json_error=StrictJSONError,
    _scaffold_error=StageCCorpusAuthoringScaffoldError,
) -> tuple[bytes, dict[str, Any]]:
    """Replay exact bytes through the closed schema and deterministic renderer."""

    if type(raw) is not bytes:
        _fail_closed("raw must be exact immutable bytes")
    try:
        snapshot, value = _parse_json(raw)
        if snapshot != raw or _canonicalize(value) != snapshot:
            _fail_closed(
                "Stage C corpus authoring scaffold must use canonical JSON bytes"
            )
    except _strict_json_error as exc:
        raise _scaffold_error(
            f"Stage C corpus authoring scaffold is outside strict JSON: {exc}"
        ) from exc
    authored_groups, reviews = _parse_inputs(value)
    expected_value = _render(authored_groups, reviews)
    if snapshot != _canonicalize(expected_value):
        _fail_closed("draft worksheet fields differ from deterministic exact replay")
    return snapshot, expected_value


def _validate_stagec_corpus_authoring_artifact_semantics(
    *,
    raw_bytes: Any,
    sha256: Any,
    byte_length: Any,
    scaffold_id: Any,
    counts: Any,
    payload: Any,
    _strict_replay=_strict_replay_stagec_corpus_authoring_scaffold,
    _canonical_digest=sha256_bytes,
    _payload_freezer=_immutable_json_value,
    _payload_type=_ImmutableJSONObject,
    _mapping_type=Mapping,
    _expected_schema: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA,
    _expected_scaffold_id: str = STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
    _fail_closed=_fail,
) -> None:
    """Prove that a sealed object is still the exact non-authority worksheet."""

    def exact_json_equal(left: Any, right: Any) -> bool:
        if isinstance(left, _mapping_type):
            if not isinstance(right, _mapping_type) or len(left) != len(right):
                return False
            try:
                left_keys = tuple(left)
                right_keys = tuple(right)
                if (
                    any(type(key) is not str for key in left_keys)
                    or any(type(key) is not str for key in right_keys)
                    or set(left_keys) != set(right_keys)
                ):
                    return False
                return all(
                    exact_json_equal(left[key], right[key])
                    for key in left_keys
                )
            except (KeyError, TypeError, ValueError):
                return False
        if type(left) is tuple:
            return type(right) is tuple and len(left) == len(right) and all(
                exact_json_equal(left_item, right_item)
                for left_item, right_item in zip(left, right, strict=True)
            )
        if type(left) in (str, int, bool) or left is None:
            return type(left) is type(right) and left == right
        return False

    if (
        type(raw_bytes) is not bytes
        or type(sha256) is not str
        or type(byte_length) is not int
        or type(scaffold_id) is not str
        or type(counts) is not tuple
        or len(counts) != 7
        or any(type(count) is not int for count in counts)
        or type(payload) is not _payload_type
    ):
        _fail_closed("artifact semantic fields have the wrong exact types")

    snapshot, expected_value = _strict_replay(raw_bytes)
    progress = expected_value["progress"]
    expected_counts = (
        progress["authored_group_count"],
        progress["authored_row_count"],
        progress["recorded_review_count"],
        progress["two_review_row_count"],
        progress["two_review_approve_row_count"],
        0,
        0,
    )
    exact_required_scalars = (
        (expected_value["schema_version"], _expected_schema),
        (expected_value["scaffold_id"], _expected_scaffold_id),
        (expected_value["classification"]["lifecycle"], "DRAFT"),
        (expected_value["classification"]["content_status"], "SYNTHETIC"),
        (expected_value["classification"]["authority"], "NON_AUTHORITY"),
        (expected_value["classification"]["admission"], "NOT_ESTABLISHED"),
        (expected_value["historical_w0_boundary"]["row_import_count"], 0),
        (expected_value["historical_w0_boundary"]["stagec_evidence_row_count"], 0),
        (expected_value["contract"]["required_group_count"], 320),
        (expected_value["contract"]["required_row_count"], 960),
        (expected_value["contract"]["variant_count"], 3),
        (expected_value["progress"]["status"], "DRAFT"),
        (expected_value["progress"]["required_group_count"], 320),
        (expected_value["progress"]["required_row_count"], 960),
        (expected_value["progress"]["admitted_group_count"], 0),
        (expected_value["progress"]["admitted_row_count"], 0),
        (expected_value["draft_inventory"]["counts_status"], "DRAFT_NOT_FROZEN"),
        (
            expected_value["draft_inventory"]["contingency_table_status"],
            "NOT_ESTABLISHED",
        ),
        (expected_value["boundary"]["stagec_corpus"], "DRAFT"),
        (expected_value["boundary"]["stagec_corpus_freeze"], "NOT_ESTABLISHED"),
        (
            expected_value["boundary"]["double_adjudication_authority"],
            "NOT_ESTABLISHED",
        ),
        (expected_value["boundary"]["admitted_group_count"], 0),
        (expected_value["boundary"]["admitted_row_count"], 0),
        (expected_value["boundary"]["execution_authority"], "NOT_GRANTED"),
        (expected_value["boundary"]["scientific_conclusion"], "NOT_ESTABLISHED"),
        (expected_value["boundary"]["license"], "NOT LICENSED"),
        (expected_value["boundary"]["disclosure"], "HELD"),
    )
    if any(
        type(actual) is not type(expected) or actual != expected
        for actual, expected in exact_required_scalars
    ):
        _fail_closed("artifact violates the sealed non-authority boundary")
    if (
        scaffold_id != _expected_scaffold_id
        or byte_length != len(snapshot)
        or sha256 != _canonical_digest(snapshot)
        or counts != expected_counts
        or not exact_json_equal(payload, _payload_freezer(expected_value))
    ):
        _fail_closed("artifact differs from strict non-authority replay")


_install_artifact_semantic_validator(
    _validate_stagec_corpus_authoring_artifact_semantics
)
del _install_artifact_semantic_validator
del _validate_stagec_corpus_authoring_artifact_semantics


def _bind_scaffold_loader(
    strict_replay,
    artifact_factory,
):
    def load_stagec_corpus_authoring_scaffold(
        raw: bytes,
    ) -> StageCCorpusAuthoringScaffoldArtifact:
        """Strict-replay canonical bytes and all derived progress fields."""

        snapshot, expected_value = strict_replay(raw)
        return artifact_factory(snapshot, expected_value)

    return load_stagec_corpus_authoring_scaffold


load_stagec_corpus_authoring_scaffold = _bind_scaffold_loader(
    _strict_replay_stagec_corpus_authoring_scaffold,
    _artifact,
)
del _bind_scaffold_loader


__all__ = [
    "STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA",
    "STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE",
    "STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID",
    "STAGEC_CORPUS_AUTHORING_SUBJECT_DOMAIN",
    "STAGEC_AUTHORING_GROUP_COUNT",
    "STAGEC_AUTHORING_ROW_COUNT",
    "STAGEC_AUTHORING_VARIANT_COUNT",
    "STAGEC_AUTHORING_REVIEW_SLOTS",
    "STAGEC_AUTHORING_CARRIERS",
    "STAGEC_AUTHORING_REVIEW_DECISIONS",
    "STAGEC_AUTHORING_SPLIT_ROLES",
    "STAGEC_AUTHORING_SPLIT_GROUP_COUNTS",
    "StageCCorpusAuthoringScaffoldError",
    "StageCCorpusDraftRowInput",
    "StageCCorpusDraftGroupInput",
    "StageCCorpusDraftReviewInput",
    "StageCCorpusAuthoringScaffoldArtifact",
    "derive_stagec_corpus_authoring_subject_sha256",
    "build_stagec_corpus_authoring_scaffold",
    "load_stagec_corpus_authoring_scaffold",
]
