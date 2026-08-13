"""Exact offline evidence-coverage dispersion for synthetic Stage 1 fixtures.

This module is deliberately a ``SYNTHETIC_ONLY / NON_AUTHORITY`` calculator.
It accepts three exact canonical-JSON byte strings, derives a coverage map and
an exact rational population CV2, and retains the inputs for fresh replay.  It
has no path, provider, model, network, process, clock, callback, adjacency, or
floating-point surface.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from math import gcd
import threading
import unicodedata
from typing import Any
import weakref

from ._strict_json import (
    MAX_DEPTH,
    MAX_DOCUMENT_BYTES,
    MAX_INTEGER_BITS,
    MAX_NODES,
    StrictJSONError,
    canonical_json_bytes,
    load_json_object,
    sha256_bytes,
)
from ._validation import ArtifactRef, MACHINE_ID_RE, SHA256_RE


EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_SCHEMA = (
    "cas_harness_v2.evidence_coverage_required_universe.v1"
)
EVIDENCE_COVERAGE_OBSERVATION_SCHEMA = (
    "cas_harness_v2.evidence_coverage_observation.v1"
)
EVIDENCE_COVERAGE_METRIC_POLICY_SCHEMA = (
    "cas_harness_v2.evidence_coverage_metric_policy.v1"
)
EVIDENCE_COVERAGE_DISPERSION_SCHEMA = (
    "cas_harness_v2.evidence_coverage_dispersion.v1"
)

EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-required-universe+json"
)
EVIDENCE_COVERAGE_OBSERVATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-observation+json"
)
EVIDENCE_COVERAGE_METRIC_POLICY_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-metric-policy+json"
)
EVIDENCE_COVERAGE_DISPERSION_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-dispersion+json"
)

EVIDENCE_COVERAGE_DISPERSION_SPEC_REPOSITORY_PATH = (
    "docs/working/project_coherence/gate5/evidence_coverage_dispersion_stage1/"
    "CAS_HARNESS_LACUNARITY_RND_HANDOFF_v0.2.md"
)
EVIDENCE_COVERAGE_DISPERSION_SPEC_SHA256 = (
    "9AB9CEF1419B431F6884BC758499F71F60C766A8635C5118FA454E640A971EC4"
)
EVIDENCE_COVERAGE_DISPERSION_SPEC_BYTE_LENGTH = 40_607

EVIDENCE_COVERAGE_MAX_DIMENSIONS = 16
EVIDENCE_COVERAGE_MAX_ROSTER_CELLS = 2_048
EVIDENCE_COVERAGE_MAX_ELIGIBLE_CELLS = 2_048
EVIDENCE_COVERAGE_MAX_EVIDENCE_ITEMS = 2_048
EVIDENCE_COVERAGE_MAX_IDENTIFIER_UTF8_BYTES = 128
EVIDENCE_COVERAGE_MAX_RECOMMENDATIONS = 2_048
EVIDENCE_COVERAGE_MAX_PROCESS_SEALS = 4_096

_COUNTING_UNIT = "ADMITTED_SYNTHETIC_EVIDENCE_ITEM"
_CELL_SEMANTICS = "JOINT_REQUIRED_CELL"
_CLASSIFICATION = "SYNTHETIC_ONLY"
_ELIGIBLE = "ELIGIBLE_OBSERVABLE_AT_SNAPSHOT"
_ELIGIBILITY_STATES = frozenset(
    {
        _ELIGIBLE,
        "UNAVAILABLE_AT_SNAPSHOT",
        "PENDING_ELIGIBILITY_AT_SNAPSHOT",
        "INELIGIBLE_AT_SNAPSHOT",
    }
)


class EvidenceCoverageDispersionError(ValueError):
    """A Stage 1 input, output, carrier, or replay failed closed."""


def _fail(message: str, _error=EvidenceCoverageDispersionError) -> None:
    raise _error(message)


def _exact_json_equal(left: Any, right: Any, _mapping=Mapping) -> bool:
    def visit(left_node: Any, right_node: Any) -> bool:
        if isinstance(left_node, _mapping):
            if not isinstance(right_node, _mapping) or len(left_node) != len(right_node):
                return False
            try:
                left_keys = tuple(left_node)
                right_keys = tuple(right_node)
                if (
                    any(type(key) is not str for key in left_keys)
                    or any(type(key) is not str for key in right_keys)
                    or set(left_keys) != set(right_keys)
                ):
                    return False
                return all(visit(left_node[key], right_node[key]) for key in left_keys)
            except (KeyError, TypeError, ValueError):
                return False
        if type(left_node) is tuple:
            return (
                type(right_node) is tuple
                and len(left_node) == len(right_node)
                and all(
                    visit(a, b)
                    for a, b in zip(left_node, right_node, strict=True)
                )
            )
        if type(left_node) in (str, int, bool) or left_node is None:
            return type(left_node) is type(right_node) and left_node == right_node
        return False

    return visit(left, right)


class _ImmutableJSONObject(tuple, Mapping[str, Any]):
    """A JSON object represented only by immutable tuples."""

    __slots__ = ()

    def __new__(cls, items: tuple[tuple[str, Any], ...]) -> "_ImmutableJSONObject":
        if type(items) is not tuple or any(
            type(item) is not tuple or len(item) != 2 or type(item[0]) is not str
            for item in items
        ):
            _fail("immutable JSON object requires exact key/value tuples")
        keys = tuple(item[0] for item in items)
        if len(keys) != len(set(keys)):
            _fail("immutable JSON object contains duplicate keys")
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
            candidate == key for candidate, _ in tuple.__iter__(self)
        )

    def __eq__(self, other: object, _equal=_exact_json_equal) -> bool:
        return _equal(self, other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    __hash__ = None


def _immutable_json(
    value: Any,
    _constructor=_ImmutableJSONObject,
    _fail_closed=_fail,
) -> Any:
    def visit(node: Any) -> Any:
        if type(node) is dict:
            return _constructor(tuple((key, visit(item)) for key, item in node.items()))
        if type(node) is list:
            return tuple(visit(item) for item in node)
        if type(node) in (str, int, bool) or node is None:
            return node
        _fail_closed(f"artifact payload contains forbidden {type(node).__name__}")

    return visit(value)


def _expect_keys(
    value: Any,
    expected: frozenset[str],
    path: str,
    _fail_closed=_fail,
) -> dict[str, Any]:
    if type(value) is not dict:
        _fail_closed(f"{path} must be an exact JSON object")
    if frozenset(value) != expected:
        _fail_closed(f"{path} must contain the exact closed field set")
    return value


def _expect_list(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int,
    _fail_closed=_fail,
) -> list[Any]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail_closed(f"{path} must be an exact JSON array with length in [{minimum}, {maximum}]")
    return value


def _expect_int(
    value: Any,
    path: str,
    *,
    minimum: int,
    maximum: int,
    _fail_closed=_fail,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail_closed(f"{path} must be an exact integer in [{minimum}, {maximum}]")
    return value


def _expect_machine_id(
    value: Any,
    path: str,
    _identifier_bytes=EVIDENCE_COVERAGE_MAX_IDENTIFIER_UTF8_BYTES,
    _machine_id_re=MACHINE_ID_RE,
    _normalize=unicodedata.normalize,
    _fail_closed=_fail,
) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value.encode("utf-8")) <= _identifier_bytes
        or _normalize("NFC", value) != value
        or _machine_id_re.fullmatch(value) is None
    ):
        _fail_closed(f"{path} must be a normalized ASCII machine identifier")
    return value


def _expect_dimension_value(
    value: Any,
    path: str,
    _identifier_bytes=EVIDENCE_COVERAGE_MAX_IDENTIFIER_UTF8_BYTES,
    _normalize=unicodedata.normalize,
    _unicode_category=unicodedata.category,
    _error=EvidenceCoverageDispersionError,
    _fail_closed=_fail,
) -> str:
    if type(value) is not str:
        _fail_closed(f"{path} must be an exact string")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise _error(
            f"{path} must be strict Unicode"
        ) from exc
    if (
        not encoded
        or len(encoded) > _identifier_bytes
        or _normalize("NFC", value) != value
        or value != value.strip()
        or any(_unicode_category(character) == "Cc" for character in value)
    ):
        _fail_closed(f"{path} must be a bounded normalized dimension value")
    return value


_REF_KEYS = frozenset({"artifact_id", "sha256", "byte_length", "media_type"})


def _parse_ref(
    value: Any,
    path: str,
    _constructor=ArtifactRef,
    _expect_closed=_expect_keys,
    _ref_keys=_REF_KEYS,
    _expect_id=_expect_machine_id,
    _sha_re=SHA256_RE,
    _expect_integer=_expect_int,
    _artifact_ref_max_byte_length=2**31 - 1,
    _error=EvidenceCoverageDispersionError,
    _fail_closed=_fail,
) -> ArtifactRef:
    obj = _expect_closed(value, _ref_keys, path)
    artifact_id = _expect_id(obj["artifact_id"], f"{path}.artifact_id")
    digest = obj["sha256"]
    if type(digest) is not str or _sha_re.fullmatch(digest) is None:
        _fail_closed(f"{path}.sha256 must be an uppercase SHA-256 digest")
    byte_length = _expect_integer(
        obj["byte_length"], f"{path}.byte_length", minimum=1,
        maximum=_artifact_ref_max_byte_length
    )
    media_type = obj["media_type"]
    if (
        type(media_type) is not str
        or not media_type.strip()
        or len(media_type) > 128
    ):
        _fail_closed(f"{path}.media_type must be a bounded exact string")
    try:
        return _constructor(artifact_id, digest, byte_length, media_type)
    except ValueError as exc:
        raise _error(f"{path} is not a valid ArtifactRef") from exc


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _derived_ref(
    raw: bytes,
    artifact_id: str,
    media_type: str,
    _constructor=ArtifactRef,
    _digest=sha256_bytes,
) -> ArtifactRef:
    return _constructor(artifact_id, _digest(raw), len(raw), media_type)


def _load_canonical_object(
    raw: bytes,
    label: str,
    _loader=load_json_object,
    _canonicalize=canonical_json_bytes,
    _strict_error=StrictJSONError,
    _error=EvidenceCoverageDispersionError,
    _fail_closed=_fail,
) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail_closed(f"{label} must be exact built-in bytes")
    try:
        snapshot, value = _loader(raw)
        if snapshot != raw or _canonicalize(value) != raw:
            _fail_closed(f"{label} must be exact canonical JSON bytes")
    except _strict_error as exc:
        raise _error(
            f"{label} is outside strict JSON: {exc}"
        ) from exc
    return value


@dataclass(frozen=True, slots=True)
class _Universe:
    reference: ArtifactRef
    scope_ref: ArtifactRef
    eligibility_snapshot_id: str
    dimension_order: tuple[str, ...]
    roster: tuple[tuple[int, str, tuple[str, ...], str], ...]


@dataclass(frozen=True, slots=True)
class _Observation:
    reference: ArtifactRef
    protocol_id: str
    items: tuple[tuple[int, ArtifactRef, str], ...]


def _parse_universe(
    raw: bytes,
    _load=_load_canonical_object,
    _expect_closed=_expect_keys,
    _schema=EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_SCHEMA,
    _counting_unit=_COUNTING_UNIT,
    _cell_semantics=_CELL_SEMANTICS,
    _classification=_CLASSIFICATION,
    _expect_id=_expect_machine_id,
    _parse_reference=_parse_ref,
    _expect_array=_expect_list,
    _maximum_dimensions=EVIDENCE_COVERAGE_MAX_DIMENSIONS,
    _maximum_roster=EVIDENCE_COVERAGE_MAX_ROSTER_CELLS,
    _expect_integer=_expect_int,
    _expect_dimension=_expect_dimension_value,
    _eligibility_states=_ELIGIBILITY_STATES,
    _eligible=_ELIGIBLE,
    _maximum_eligible=EVIDENCE_COVERAGE_MAX_ELIGIBLE_CELLS,
    _derive_reference=_derived_ref,
    _media_type=EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_MEDIA_TYPE,
    _universe_type=_Universe,
    _fail_closed=_fail,
) -> _Universe:
    value = _load(raw, "required_universe_bytes")
    _expect_closed(
        value,
        frozenset(
            {
                "schema_version", "universe_id", "scope_binding_ref",
                "eligibility_snapshot_id", "counting_unit", "cell_semantics",
                "dimension_order", "cell_roster", "classification",
            }
        ),
        "$required_universe",
    )
    if (
        value["schema_version"] != _schema
        or value["counting_unit"] != _counting_unit
        or value["cell_semantics"] != _cell_semantics
        or value["classification"] != _classification
    ):
        _fail_closed("required universe has a forbidden schema or semantic boundary")
    universe_id = _expect_id(value["universe_id"], "$.universe_id")
    scope_ref = _parse_reference(value["scope_binding_ref"], "$.scope_binding_ref")
    eligibility_snapshot_id = _expect_id(
        value["eligibility_snapshot_id"], "$.eligibility_snapshot_id"
    )
    dimensions_value = _expect_array(
        value["dimension_order"], "$.dimension_order", minimum=1,
        maximum=_maximum_dimensions,
    )
    dimensions = tuple(
        _expect_id(item, f"$.dimension_order[{index}]")
        for index, item in enumerate(dimensions_value)
    )
    if len(dimensions) != len(set(dimensions)):
        _fail_closed("$.dimension_order contains duplicate dimensions")
    roster_value = _expect_array(
        value["cell_roster"], "$.cell_roster", minimum=1,
        maximum=_maximum_roster,
    )
    roster: list[tuple[int, str, tuple[str, ...], str]] = []
    cell_ids: set[str] = set()
    dimension_tuples: set[tuple[str, ...]] = set()
    eligible_count = 0
    for expected_ordinal, row_value in enumerate(roster_value):
        row = _expect_closed(
            row_value,
            frozenset({"cell_ordinal", "cell_id", "dimension_values", "eligibility_status"}),
            f"$.cell_roster[{expected_ordinal}]",
        )
        ordinal = _expect_integer(
            row["cell_ordinal"], f"$.cell_roster[{expected_ordinal}].cell_ordinal",
            minimum=0, maximum=_maximum_roster - 1,
        )
        if ordinal != expected_ordinal:
            _fail_closed("$.cell_roster must use contiguous zero-based ordinal order")
        cell_id = _expect_id(
            row["cell_id"], f"$.cell_roster[{expected_ordinal}].cell_id"
        )
        if cell_id in cell_ids:
            _fail_closed("$.cell_roster contains duplicate cell_id values")
        cell_ids.add(cell_id)
        dimension_values_raw = _expect_array(
            row["dimension_values"],
            f"$.cell_roster[{expected_ordinal}].dimension_values",
            minimum=len(dimensions), maximum=len(dimensions),
        )
        dimension_values = tuple(
            _expect_dimension(
                item, f"$.cell_roster[{expected_ordinal}].dimension_values[{index}]"
            )
            for index, item in enumerate(dimension_values_raw)
        )
        if dimension_values in dimension_tuples:
            _fail_closed("$.cell_roster contains duplicate joint dimension tuples")
        dimension_tuples.add(dimension_values)
        status = row["eligibility_status"]
        if type(status) is not str or status not in _eligibility_states:
            _fail_closed("cell eligibility_status is outside the frozen closed enum")
        if status == _eligible:
            eligible_count += 1
        roster.append((ordinal, cell_id, dimension_values, status))
    if not 1 <= eligible_count <= _maximum_eligible:
        _fail_closed("required universe must contain at least one eligible required cell")
    return _universe_type(
        reference=_derive_reference(
            raw, universe_id, _media_type
        ),
        scope_ref=scope_ref,
        eligibility_snapshot_id=eligibility_snapshot_id,
        dimension_order=dimensions,
        roster=tuple(roster),
    )


def _parse_observation(
    raw: bytes,
    universe: _Universe,
    _load=_load_canonical_object,
    _expect_closed=_expect_keys,
    _schema=EVIDENCE_COVERAGE_OBSERVATION_SCHEMA,
    _counting_unit=_COUNTING_UNIT,
    _classification=_CLASSIFICATION,
    _expect_id=_expect_machine_id,
    _parse_reference=_parse_ref,
    _expect_array=_expect_list,
    _maximum_items=EVIDENCE_COVERAGE_MAX_EVIDENCE_ITEMS,
    _expect_integer=_expect_int,
    _eligible=_ELIGIBLE,
    _derive_reference=_derived_ref,
    _media_type=EVIDENCE_COVERAGE_OBSERVATION_MEDIA_TYPE,
    _observation_type=_Observation,
    _fail_closed=_fail,
) -> _Observation:
    value = _load(raw, "observation_bytes")
    _expect_closed(
        value,
        frozenset(
            {
                "schema_version", "observation_id", "universe_ref",
                "scope_binding_ref", "counting_unit", "observation_protocol_id",
                "evidence_items", "classification",
            }
        ),
        "$observation",
    )
    if (
        value["schema_version"] != _schema
        or value["counting_unit"] != _counting_unit
        or value["classification"] != _classification
    ):
        _fail_closed("observation has a forbidden schema or semantic boundary")
    observation_id = _expect_id(value["observation_id"], "$.observation_id")
    if _parse_reference(value["universe_ref"], "$.universe_ref") != universe.reference:
        _fail_closed("observation universe_ref does not bind the exact required universe")
    if _parse_reference(value["scope_binding_ref"], "$.scope_binding_ref") != universe.scope_ref:
        _fail_closed("observation scope_binding_ref does not match the universe")
    protocol_id = _expect_id(
        value["observation_protocol_id"], "$.observation_protocol_id"
    )
    items_value = _expect_array(
        value["evidence_items"], "$.evidence_items", minimum=0,
        maximum=_maximum_items,
    )
    statuses = {cell_id: status for _, cell_id, _, status in universe.roster}
    seen_refs: set[ArtifactRef] = set()
    identity_by_id: dict[str, ArtifactRef] = {}
    ids_by_content: dict[tuple[str, int], str] = {}
    items: list[tuple[int, ArtifactRef, str]] = []
    for expected_ordinal, item_value in enumerate(items_value):
        item = _expect_closed(
            item_value,
            frozenset({"item_ordinal", "evidence_ref", "cell_id"}),
            f"$.evidence_items[{expected_ordinal}]",
        )
        ordinal = _expect_integer(
            item["item_ordinal"], f"$.evidence_items[{expected_ordinal}].item_ordinal",
            minimum=0, maximum=_maximum_items - 1,
        )
        if ordinal != expected_ordinal:
            _fail_closed("$.evidence_items must use contiguous zero-based ordinal order")
        reference = _parse_reference(
            item["evidence_ref"], f"$.evidence_items[{expected_ordinal}].evidence_ref"
        )
        if reference in seen_refs:
            _fail_closed("$.evidence_items contains a duplicate exact evidence_ref")
        seen_refs.add(reference)
        previous = identity_by_id.get(reference.artifact_id)
        if previous is not None and previous != reference:
            _fail_closed("one evidence artifact_id has conflicting identity fields")
        identity_by_id[reference.artifact_id] = reference
        content_key = (reference.sha256, reference.byte_length)
        previous_id = ids_by_content.get(content_key)
        if previous_id is not None and previous_id != reference.artifact_id:
            _fail_closed("equal evidence content identity appears under different artifact IDs")
        ids_by_content[content_key] = reference.artifact_id
        cell_id = _expect_id(
            item["cell_id"], f"$.evidence_items[{expected_ordinal}].cell_id"
        )
        if cell_id not in statuses:
            _fail_closed("evidence item maps to an unknown cell_id")
        if statuses[cell_id] != _eligible:
            _fail_closed("evidence item maps to a non-eligible roster cell")
        items.append((ordinal, reference, cell_id))
    return _observation_type(
        reference=_derive_reference(
            raw, observation_id, _media_type
        ),
        protocol_id=protocol_id,
        items=tuple(items),
    )


def _parse_policy(
    raw: bytes,
    _load=_load_canonical_object,
    _expect_closed=_expect_keys,
    _schema=EVIDENCE_COVERAGE_METRIC_POLICY_SCHEMA,
    _classification=_CLASSIFICATION,
    _expect_id=_expect_machine_id,
    _derive_reference=_derived_ref,
    _media_type=EVIDENCE_COVERAGE_METRIC_POLICY_MEDIA_TYPE,
    _fail_closed=_fail,
) -> ArtifactRef:
    value = _load(raw, "metric_policy_bytes")
    _expect_closed(
        value,
        frozenset(
            {
                "schema_version", "policy_id", "counting_mode", "dispersion_mode",
                "rate_mode", "recommendation_order", "tie_break_order", "classification",
            }
        ),
        "$metric_policy",
    )
    if (
        value["schema_version"] != _schema
        or value["counting_mode"] != "EXACT_ITEM_COUNT"
        or value["dispersion_mode"] != "POPULATION_CV2_EXACT_RATIONAL"
        or value["rate_mode"] != "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1"
        or value["recommendation_order"] != ["ZERO_SUPPORT_FIRST", "MINIMUM_SUPPORT_NEXT"]
        or value["tie_break_order"] != ["CELL_ORDINAL_ASCENDING"]
        or value["classification"] != _classification
    ):
        _fail_closed("metric policy differs from the frozen Stage 1 policy")
    policy_id = _expect_id(value["policy_id"], "$.policy_id")
    return _derive_reference(raw, policy_id, _media_type)


def _reduced(numerator: int, denominator: int, _gcd=gcd) -> dict[str, int]:
    divisor = _gcd(numerator, denominator)
    return {"numerator": numerator // divisor, "denominator": denominator // divisor}


def _derive_value(
    required_universe_bytes: bytes,
    observation_bytes: bytes,
    metric_policy_bytes: bytes,
    _canonicalize=canonical_json_bytes,
    _digest=sha256_bytes,
    _parse_required=_parse_universe,
    _parse_observed=_parse_observation,
    _parse_metric=_parse_policy,
    _reference_value=_ref_value,
    _eligible=_ELIGIBLE,
    _eligibility_states=_ELIGIBILITY_STATES,
    _reduce=_reduced,
    _result_schema=EVIDENCE_COVERAGE_DISPERSION_SCHEMA,
    _classification=_CLASSIFICATION,
    _maximum_document_bytes=MAX_DOCUMENT_BYTES,
    _fail_closed=_fail,
) -> tuple[bytes, dict[str, Any], str]:
    universe = _parse_required(required_universe_bytes)
    observation = _parse_observed(observation_bytes, universe)
    policy_ref = _parse_metric(metric_policy_bytes)
    input_bindings = {
        "required_universe_ref": _reference_value(universe.reference),
        "observation_ref": _reference_value(observation.reference),
        "metric_policy_ref": _reference_value(policy_ref),
    }
    profile_id = "ecd-" + _digest(_canonicalize(input_bindings)).lower()
    counts = {
        cell_id: 0
        for _, cell_id, _, status in universe.roster
        if status == _eligible
    }
    for _, _, cell_id in observation.items:
        counts[cell_id] += 1
    eligible_rows = tuple(
        (ordinal, cell_id, counts[cell_id])
        for ordinal, cell_id, _, status in universe.roster
        if status == _eligible
    )
    n = len(eligible_rows)
    support_values = tuple(count for _, _, count in eligible_rows)
    total = sum(support_values)
    zero_count = sum(count == 0 for count in support_values)
    sum_squared = sum(count * count for count in support_values)
    status_counts = {
        status: sum(row_status == status for _, _, _, row_status in universe.roster)
        for status in _eligibility_states
    }
    if total == 0:
        dispersion = {
            "status": "UNAVAILABLE_ALL_CELLS_ZERO",
            "total_support": 0,
            "sum_squared_support": 0,
            "cv2": "ABSENT",
            "hhi_relationship": "UNAVAILABLE_ALL_CELLS_ZERO",
            "rate_status": "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1",
        }
    else:
        cv2_numerator = n * sum_squared - total * total
        if cv2_numerator < 0:
            _fail_closed("exact CV2 numerator violated nonnegativity")
        dispersion = {
            "status": "AVAILABLE_EXACT_COUNT_DISPERSION",
            "total_support": total,
            "sum_squared_support": sum_squared,
            "cv2": _reduce(cv2_numerator, total * total),
            "hhi_relationship": "CV2_EQUALS_N_TIMES_HHI_MINUS_ONE",
            "rate_status": "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1",
        }
    ordered_recommendations = sorted(
        eligible_rows, key=lambda row: (0 if row[2] == 0 else 1, row[2], row[0])
    )
    value = {
        "schema_version": _result_schema,
        "profile_id": profile_id,
        "input_bindings": input_bindings,
        "metric_identity": {
            "canonical_name": "EVIDENCE_COVERAGE_DISPERSION_POPULATION_CV2",
            "research_alias": "ONE_SCALE_CATEGORICAL_LACUNARITY_ALIAS_ONLY",
            "spatial_claim": "NONE",
            "multiscale_claim": "NONE",
        },
        "coverage_summary": {
            "roster_cell_count": len(universe.roster),
            "eligible_required_cell_count": n,
            "unavailable_cell_count": status_counts["UNAVAILABLE_AT_SNAPSHOT"],
            "pending_eligibility_cell_count": status_counts["PENDING_ELIGIBILITY_AT_SNAPSHOT"],
            "ineligible_cell_count": status_counts["INELIGIBLE_AT_SNAPSHOT"],
            "observed_nonzero_cell_count": n - zero_count,
            "zero_cell_count": zero_count,
            "evidence_item_count": len(observation.items),
            "gap_fraction": _reduce(zero_count, n),
            "coverage_fraction": _reduce(n - zero_count, n),
        },
        "dispersion_summary": dispersion,
        "cell_counts": [
            {
                "cell_ordinal": ordinal,
                "cell_id": cell_id,
                "eligibility_status": _eligible,
                "support_count": support_count,
            }
            for ordinal, cell_id, support_count in eligible_rows
        ],
        "recommendations": [
            {
                "recommendation_ordinal": recommendation_ordinal,
                "cell_ordinal": ordinal,
                "cell_id": cell_id,
                "support_count": support_count,
                "reason": (
                    "ZERO_SUPPORT_REQUIRED_CELL"
                    if support_count == 0
                    else "MINIMUM_SUPPORT_REQUIRED_CELL"
                ),
            }
            for recommendation_ordinal, (ordinal, cell_id, support_count)
            in enumerate(ordered_recommendations)
        ],
        "classification": _classification,
        "authority_boundary": {
            "authority": "NON_AUTHORITY",
            "recommendation_authority": "ADVISORY_ONLY",
            "decision_effect": "NONE",
            "execution_authority": "NOT_GRANTED",
            "scientific_status": "STRUCTURE_ONLY",
            "evidence_packet_effect": "NONE",
        },
    }
    raw = _canonicalize(value)
    if len(raw) > _maximum_document_bytes:
        _fail_closed("derived result exceeds the strict document-byte ceiling")
    return raw, value, profile_id


@dataclass(frozen=True, slots=True)
class _ArtifactSeal:
    artifact: weakref.ReferenceType[Any]
    raw_bytes: bytes
    sha256: str
    byte_length: int
    profile_id: str
    payload: Mapping[str, Any]
    required_universe_bytes: bytes
    observation_bytes: bytes
    metric_policy_bytes: bytes


def _make_seal_accessor(_error=EvidenceCoverageDispersionError):
    implementation = None

    def require(artifact: Any) -> _ArtifactSeal:
        current = implementation
        if current is None:
            raise _error("artifact seal verifier is not installed")
        return current(artifact)

    def install(candidate) -> None:
        nonlocal implementation
        if implementation is not None or not callable(candidate):
            raise _error("artifact seal verifier may be installed exactly once")
        implementation = candidate

    return require, install


_require_artifact_seal, _install_artifact_seal_verifier = _make_seal_accessor()
del _make_seal_accessor


def _validate_seal_fresh(
    seal: _ArtifactSeal,
    _derive=_derive_value,
    _digest=sha256_bytes,
    _freezer=_immutable_json,
    _payload_type=_ImmutableJSONObject,
    _equal=_exact_json_equal,
    _fail_closed=_fail,
) -> None:
    if (
        type(seal.raw_bytes) is not bytes
        or type(seal.required_universe_bytes) is not bytes
        or type(seal.observation_bytes) is not bytes
        or type(seal.metric_policy_bytes) is not bytes
        or type(seal.sha256) is not str
        or type(seal.byte_length) is not int
        or type(seal.profile_id) is not str
        or type(seal.payload) is not _payload_type
    ):
        _fail_closed("sealed artifact fields have wrong exact types")
    expected_raw, expected_value, expected_profile_id = _derive(
        seal.required_universe_bytes, seal.observation_bytes, seal.metric_policy_bytes
    )
    if (
        expected_raw != seal.raw_bytes
        or _digest(expected_raw) != seal.sha256
        or len(expected_raw) != seal.byte_length
        or expected_profile_id != seal.profile_id
        or not _equal(seal.payload, _freezer(expected_value))
    ):
        _fail_closed("artifact differs from fresh exact semantic replay")


@dataclass(frozen=True, slots=True, init=False, eq=False, weakref_slot=True)
class EvidenceCoverageDispersionArtifact:
    """Factory-only, tuple-backed, freshly replayable Stage 1 result."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    profile_id: str
    payload: Mapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "EvidenceCoverageDispersionArtifact is factory-only; use build, load, or replay"
        )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("EvidenceCoverageDispersionArtifact may not be subclassed")

    def __eq__(
        self,
        other: object,
        _require=_require_artifact_seal,
        _error=EvidenceCoverageDispersionError,
        _equal=_exact_json_equal,
    ) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        try:
            left = _require(self)
            right = _require(other)
        except _error:
            return False
        return (
            left.raw_bytes == right.raw_bytes
            and left.sha256 == right.sha256
            and left.byte_length == right.byte_length
            and left.profile_id == right.profile_id
            and _equal(left.payload, right.payload)
        )

    def __ne__(self, other: object) -> bool:
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal

    __hash__ = None

    @property
    def artifact_ref(
        self,
        _require=_require_artifact_seal,
        _validate=_validate_seal_fresh,
        _constructor=ArtifactRef,
        _media_type=EVIDENCE_COVERAGE_DISPERSION_MEDIA_TYPE,
    ) -> ArtifactRef:
        seal = _require(self)
        _validate(seal)
        return _constructor(
            seal.profile_id, seal.sha256, seal.byte_length, _media_type
        )


def _make_artifact_mechanism(
    _artifact_type=EvidenceCoverageDispersionArtifact,
    _seal_type=_ArtifactSeal,
    _derive=_derive_value,
    _digest=sha256_bytes,
    _freezer=_immutable_json,
    _equal=_exact_json_equal,
    _lock_factory=threading.RLock,
    _weak_reference=weakref.ref,
    _limit=EVIDENCE_COVERAGE_MAX_PROCESS_SEALS,
    _error=EvidenceCoverageDispersionError,
):
    """Return a mint and verifier; no callable can register a supplied object."""

    seals: tuple[tuple[int, _ArtifactSeal], ...] = ()
    lock = _lock_factory()

    def issue(
        raw: bytes,
        value: dict[str, Any],
        profile_id: str,
        required_universe_bytes: bytes,
        observation_bytes: bytes,
        metric_policy_bytes: bytes,
    ) -> EvidenceCoverageDispersionArtifact:
        nonlocal seals
        if any(
            type(item) is not bytes
            for item in (
                raw,
                required_universe_bytes,
                observation_bytes,
                metric_policy_bytes,
            )
        ):
            raise _error("artifact mint requires exact built-in bytes")
        expected_raw, expected_value, expected_profile_id = _derive(
            required_universe_bytes, observation_bytes, metric_policy_bytes
        )
        if (
            raw != expected_raw
            or profile_id != expected_profile_id
            or not _equal(_freezer(value), _freezer(expected_value))
        ):
            raise _error("artifact mint input differs from fresh semantic derivation")
        raw_snapshot = bytes(expected_raw)
        universe_snapshot = bytes(required_universe_bytes)
        observation_snapshot = bytes(observation_bytes)
        policy_snapshot = bytes(metric_policy_bytes)
        digest = _digest(raw_snapshot)
        payload = _freezer(expected_value)
        artifact = object.__new__(_artifact_type)
        for name, item in (
            ("raw_bytes", raw_snapshot),
            ("sha256", digest),
            ("byte_length", len(raw_snapshot)),
            ("profile_id", expected_profile_id),
            ("payload", payload),
        ):
            object.__setattr__(artifact, name, item)
        identity = id(artifact)

        def remove(reference: weakref.ReferenceType[Any]) -> None:
            nonlocal seals
            with lock:
                seals = tuple(
                    pair
                    for pair in seals
                    if not (pair[0] == identity and pair[1].artifact is reference)
                )

        reference = _weak_reference(artifact, remove)
        seal = _seal_type(
            reference,
            raw_snapshot,
            digest,
            len(raw_snapshot),
            expected_profile_id,
            payload,
            universe_snapshot,
            observation_snapshot,
            policy_snapshot,
        )
        with lock:
            retained = seals[-(_limit - 1):] if _limit > 1 else ()
            seals = (*retained, (identity, seal))
        return artifact

    def require(artifact: Any) -> _ArtifactSeal:
        with lock:
            seal = next(
                (
                    candidate
                    for identity, candidate in reversed(seals)
                    if identity == id(artifact)
                ),
                None,
            )
            if seal is None or seal.artifact() is not artifact:
                raise _error("artifact is not an exact process-sealed factory result")
            try:
                if (
                    type(artifact) is not _artifact_type
                    or artifact.raw_bytes is not seal.raw_bytes
                    or artifact.payload is not seal.payload
                    or artifact.sha256 != seal.sha256
                    or artifact.byte_length != seal.byte_length
                    or artifact.profile_id != seal.profile_id
                ):
                    raise _error("artifact differs from its exact process seal")
            except AttributeError as exc:
                raise _error("artifact differs from its exact process seal") from exc
            return seal

    return issue, require


_issue_artifact, _sealed_artifact_verifier = _make_artifact_mechanism()
_install_artifact_seal_verifier(_sealed_artifact_verifier)
del _install_artifact_seal_verifier
del _sealed_artifact_verifier
del _make_artifact_mechanism


def _bind_public_api(
    _derive=_derive_value,
    _factory=_issue_artifact,
    _fail_closed=_fail,
    _load_snapshot=_load_canonical_object,
    _artifact_type=EvidenceCoverageDispersionArtifact,
    _require=_require_artifact_seal,
    _validate=_validate_seal_fresh,
    _freezer=_immutable_json,
    _equal=_exact_json_equal,
):
    def build_evidence_coverage_dispersion(
        *, required_universe_bytes: bytes, observation_bytes: bytes,
        metric_policy_bytes: bytes,
    ) -> EvidenceCoverageDispersionArtifact:
        if any(
            type(value) is not bytes
            for value in (required_universe_bytes, observation_bytes, metric_policy_bytes)
        ):
            _fail_closed("all public byte parameters must be exact built-in bytes")
        raw, value, profile_id = _derive(
            required_universe_bytes, observation_bytes, metric_policy_bytes
        )
        return _factory(
            raw, value, profile_id, required_universe_bytes,
            observation_bytes, metric_policy_bytes,
        )

    def load_evidence_coverage_dispersion(
        snapshot_bytes: bytes,
        *, required_universe_bytes: bytes, observation_bytes: bytes,
        metric_policy_bytes: bytes,
    ) -> EvidenceCoverageDispersionArtifact:
        if any(
            type(value) is not bytes
            for value in (
                snapshot_bytes, required_universe_bytes,
                observation_bytes, metric_policy_bytes,
            )
        ):
            _fail_closed("all public byte parameters must be exact built-in bytes")
        expected_raw, value, profile_id = _derive(
            required_universe_bytes, observation_bytes, metric_policy_bytes
        )
        supplied = _load_snapshot(snapshot_bytes, "snapshot_bytes")
        if (
            snapshot_bytes != expected_raw
            or not _equal(_freezer(supplied), _freezer(value))
        ):
            _fail_closed("result snapshot differs from fresh exact semantic replay")
        return _factory(
            expected_raw, value, profile_id, required_universe_bytes,
            observation_bytes, metric_policy_bytes,
        )

    def replay_evidence_coverage_dispersion(
        artifact: EvidenceCoverageDispersionArtifact,
    ) -> EvidenceCoverageDispersionArtifact:
        if type(artifact) is not _artifact_type:
            _fail_closed("artifact must be an exact EvidenceCoverageDispersionArtifact")
        seal = _require(artifact)
        _validate(seal)
        raw, value, profile_id = _derive(
            seal.required_universe_bytes, seal.observation_bytes,
            seal.metric_policy_bytes,
        )
        if (
            raw != seal.raw_bytes
            or profile_id != seal.profile_id
            or not _equal(_freezer(value), seal.payload)
        ):
            _fail_closed("artifact replay changed bytes, scalars, or payload")
        return _factory(
            raw, value, profile_id, seal.required_universe_bytes,
            seal.observation_bytes, seal.metric_policy_bytes,
        )

    return (
        build_evidence_coverage_dispersion,
        load_evidence_coverage_dispersion,
        replay_evidence_coverage_dispersion,
    )


(
    build_evidence_coverage_dispersion,
    load_evidence_coverage_dispersion,
    replay_evidence_coverage_dispersion,
) = _bind_public_api()
del _bind_public_api
del _issue_artifact


__all__ = [
    "EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_SCHEMA",
    "EVIDENCE_COVERAGE_OBSERVATION_SCHEMA",
    "EVIDENCE_COVERAGE_METRIC_POLICY_SCHEMA",
    "EVIDENCE_COVERAGE_DISPERSION_SCHEMA",
    "EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_MEDIA_TYPE",
    "EVIDENCE_COVERAGE_OBSERVATION_MEDIA_TYPE",
    "EVIDENCE_COVERAGE_METRIC_POLICY_MEDIA_TYPE",
    "EVIDENCE_COVERAGE_DISPERSION_MEDIA_TYPE",
    "EVIDENCE_COVERAGE_DISPERSION_SPEC_REPOSITORY_PATH",
    "EVIDENCE_COVERAGE_DISPERSION_SPEC_SHA256",
    "EVIDENCE_COVERAGE_DISPERSION_SPEC_BYTE_LENGTH",
    "EVIDENCE_COVERAGE_MAX_DIMENSIONS",
    "EVIDENCE_COVERAGE_MAX_ROSTER_CELLS",
    "EVIDENCE_COVERAGE_MAX_ELIGIBLE_CELLS",
    "EVIDENCE_COVERAGE_MAX_EVIDENCE_ITEMS",
    "EVIDENCE_COVERAGE_MAX_IDENTIFIER_UTF8_BYTES",
    "EVIDENCE_COVERAGE_MAX_RECOMMENDATIONS",
    "EVIDENCE_COVERAGE_MAX_PROCESS_SEALS",
    "EvidenceCoverageDispersionError",
    "EvidenceCoverageDispersionArtifact",
    "build_evidence_coverage_dispersion",
    "load_evidence_coverage_dispersion",
    "replay_evidence_coverage_dispersion",
    "MAX_DOCUMENT_BYTES",
    "MAX_DEPTH",
    "MAX_NODES",
    "MAX_INTEGER_BITS",
]
