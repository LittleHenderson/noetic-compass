from __future__ import annotations

import ast
import builtins
import copy
from dataclasses import dataclass, replace
import dis
from fractions import Fraction
import gc
import hashlib
import inspect
import itertools
import json
from math import gcd
from pathlib import Path
import socket
import subprocess
import sys
import os
import pickle
import time
import unicodedata
from typing import Any, Callable
import weakref

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import (  # noqa: E402
    MAX_DOCUMENT_BYTES,
    canonical_json_bytes,
)
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
import cas_harness_v2.diagnostic_evidence_coverage_dispersion as sut  # noqa: E402


UNIVERSE_SCHEMA = "cas_harness_v2.evidence_coverage_required_universe.v1"
OBSERVATION_SCHEMA = "cas_harness_v2.evidence_coverage_observation.v1"
POLICY_SCHEMA = "cas_harness_v2.evidence_coverage_metric_policy.v1"
RESULT_SCHEMA = "cas_harness_v2.evidence_coverage_dispersion.v1"
UNIVERSE_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-required-universe+json"
)
OBSERVATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-observation+json"
)
POLICY_MEDIA_TYPE = (
    "application/vnd.cas-harness.evidence-coverage-metric-policy+json"
)
RESULT_MEDIA_TYPE = "application/vnd.cas-harness.evidence-coverage-dispersion+json"

ELIGIBLE = "ELIGIBLE_OBSERVABLE_AT_SNAPSHOT"
UNAVAILABLE = "UNAVAILABLE_AT_SNAPSHOT"
PENDING = "PENDING_ELIGIBILITY_AT_SNAPSHOT"
INELIGIBLE = "INELIGIBLE_AT_SNAPSHOT"

COUNTING_UNIT = "ADMITTED_SYNTHETIC_EVIDENCE_ITEM"
CLASSIFICATION = "SYNTHETIC_ONLY"
CELL_SEMANTICS = "JOINT_REQUIRED_CELL"

MAX_DIMENSIONS = 16
MAX_ROSTER_CELLS = 2_048
MAX_EVIDENCE_ITEMS = 2_048
SPEC_RELATIVE_PATH = (
    "docs/working/project_coherence/gate5/evidence_coverage_dispersion_stage1/"
    "CAS_HARNESS_LACUNARITY_RND_HANDOFF_v0.2.md"
)
SPEC_SHA256 = "9AB9CEF1419B431F6884BC758499F71F60C766A8635C5118FA454E640A971EC4"
SPEC_BYTE_LENGTH = 40_607


@dataclass(frozen=True, slots=True)
class Fixture:
    universe_value: dict[str, Any]
    observation_value: dict[str, Any]
    policy_value: dict[str, Any]
    universe_bytes: bytes
    observation_bytes: bytes
    policy_bytes: bytes


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _ref(artifact_id: str, raw: bytes, media_type: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": _sha(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


def _identity_ref(
    artifact_id: str,
    *,
    body: bytes,
    media_type: str = "application/vnd.cas-harness.synthetic-evidence+json",
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": _sha(body),
        "byte_length": len(body),
        "media_type": media_type,
    }


SCOPE_REF = _identity_ref(
    "synthetic-scope-binding-v1",
    body=b'{"scope":"synthetic-only"}',
    media_type="application/vnd.cas-harness.synthetic-scope-binding+json",
)


def _fixture(
    counts: tuple[int, ...] = (0, 1, 2),
    *,
    statuses: tuple[str, ...] | None = None,
    dimensions: int = 2,
    universe_id: str = "synthetic-required-universe-v1",
    observation_id: str = "synthetic-observation-v1",
    policy_id: str = "synthetic-metric-policy-v1",
) -> Fixture:
    if statuses is None:
        statuses = (ELIGIBLE,) * len(counts)
    assert len(counts) == len(statuses)
    assert dimensions >= 1

    dimension_order = [f"dimension-{index}" for index in range(dimensions)]
    roster: list[dict[str, Any]] = []
    evidence_items: list[dict[str, Any]] = []
    item_ordinal = 0
    for cell_ordinal, (count, status) in enumerate(zip(counts, statuses, strict=True)):
        assert count >= 0
        if status != ELIGIBLE:
            assert count == 0
        cell_id = f"cell-{cell_ordinal:04d}"
        roster.append(
            {
                "cell_ordinal": cell_ordinal,
                "cell_id": cell_id,
                "dimension_values": [
                    f"value-{dimension_index}-{cell_ordinal:04d}"
                    for dimension_index in range(dimensions)
                ],
                "eligibility_status": status,
            }
        )
        for within_cell in range(count):
            body = f"synthetic-body-{cell_ordinal}-{within_cell}".encode("ascii")
            evidence_items.append(
                {
                    "item_ordinal": item_ordinal,
                    "evidence_ref": _identity_ref(
                        f"synthetic-evidence-{cell_ordinal:04d}-{within_cell:04d}",
                        body=body,
                    ),
                    "cell_id": cell_id,
                }
            )
            item_ordinal += 1

    universe_value = {
        "schema_version": UNIVERSE_SCHEMA,
        "universe_id": universe_id,
        "scope_binding_ref": dict(SCOPE_REF),
        "eligibility_snapshot_id": "synthetic-eligibility-snapshot-v1",
        "counting_unit": COUNTING_UNIT,
        "cell_semantics": CELL_SEMANTICS,
        "dimension_order": dimension_order,
        "cell_roster": roster,
        "classification": CLASSIFICATION,
    }
    universe_bytes = canonical_json_bytes(universe_value)
    observation_value = {
        "schema_version": OBSERVATION_SCHEMA,
        "observation_id": observation_id,
        "universe_ref": _ref(universe_id, universe_bytes, UNIVERSE_MEDIA_TYPE),
        "scope_binding_ref": dict(SCOPE_REF),
        "counting_unit": COUNTING_UNIT,
        "observation_protocol_id": "synthetic-observation-protocol-v1",
        "evidence_items": evidence_items,
        "classification": CLASSIFICATION,
    }
    policy_value = {
        "schema_version": POLICY_SCHEMA,
        "policy_id": policy_id,
        "counting_mode": "EXACT_ITEM_COUNT",
        "dispersion_mode": "POPULATION_CV2_EXACT_RATIONAL",
        "rate_mode": "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1",
        "recommendation_order": ["ZERO_SUPPORT_FIRST", "MINIMUM_SUPPORT_NEXT"],
        "tie_break_order": ["CELL_ORDINAL_ASCENDING"],
        "classification": CLASSIFICATION,
    }
    return Fixture(
        universe_value=universe_value,
        observation_value=observation_value,
        policy_value=policy_value,
        universe_bytes=universe_bytes,
        observation_bytes=canonical_json_bytes(observation_value),
        policy_bytes=canonical_json_bytes(policy_value),
    )


def _rebuild_fixture(
    fixture: Fixture,
    *,
    universe_value: dict[str, Any] | None = None,
    observation_value: dict[str, Any] | None = None,
    policy_value: dict[str, Any] | None = None,
    rebind_observation_universe: bool = False,
) -> Fixture:
    universe = json.loads(canonical_json_bytes(universe_value or fixture.universe_value))
    observation = json.loads(
        canonical_json_bytes(observation_value or fixture.observation_value)
    )
    policy = json.loads(canonical_json_bytes(policy_value or fixture.policy_value))
    universe_bytes = canonical_json_bytes(universe)
    if rebind_observation_universe:
        observation["universe_ref"] = _ref(
            universe["universe_id"], universe_bytes, UNIVERSE_MEDIA_TYPE
        )
    return Fixture(
        universe_value=universe,
        observation_value=observation,
        policy_value=policy,
        universe_bytes=universe_bytes,
        observation_bytes=canonical_json_bytes(observation),
        policy_bytes=canonical_json_bytes(policy),
    )


def _build(fixture: Fixture):
    return sut.build_evidence_coverage_dispersion(
        required_universe_bytes=fixture.universe_bytes,
        observation_bytes=fixture.observation_bytes,
        metric_policy_bytes=fixture.policy_bytes,
    )


def _load(raw: bytes, fixture: Fixture):
    return sut.load_evidence_coverage_dispersion(
        raw,
        required_universe_bytes=fixture.universe_bytes,
        observation_bytes=fixture.observation_bytes,
        metric_policy_bytes=fixture.policy_bytes,
    )


def _rational(numerator: int, denominator: int) -> dict[str, int]:
    common = gcd(numerator, denominator)
    return {
        "numerator": numerator // common,
        "denominator": denominator // common,
    }


def _independent_expected_result(fixture: Fixture) -> dict[str, Any]:
    universe = fixture.universe_value
    observation = fixture.observation_value
    eligible_rows = [
        row for row in universe["cell_roster"] if row["eligibility_status"] == ELIGIBLE
    ]
    counts = {row["cell_id"]: 0 for row in eligible_rows}
    for item in observation["evidence_items"]:
        counts[item["cell_id"]] += 1

    n = len(eligible_rows)
    support = [counts[row["cell_id"]] for row in eligible_rows]
    total = sum(support)
    squared = sum(value * value for value in support)
    zero = sum(value == 0 for value in support)
    input_bindings = {
        "required_universe_ref": _ref(
            universe["universe_id"], fixture.universe_bytes, UNIVERSE_MEDIA_TYPE
        ),
        "observation_ref": _ref(
            observation["observation_id"],
            fixture.observation_bytes,
            OBSERVATION_MEDIA_TYPE,
        ),
        "metric_policy_ref": _ref(
            fixture.policy_value["policy_id"], fixture.policy_bytes, POLICY_MEDIA_TYPE
        ),
    }
    profile_id = "ecd-" + hashlib.sha256(
        canonical_json_bytes(input_bindings)
    ).hexdigest()

    state_counts = {
        UNAVAILABLE: 0,
        PENDING: 0,
        INELIGIBLE: 0,
    }
    for row in universe["cell_roster"]:
        if row["eligibility_status"] in state_counts:
            state_counts[row["eligibility_status"]] += 1

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
        dispersion = {
            "status": "AVAILABLE_EXACT_COUNT_DISPERSION",
            "total_support": total,
            "sum_squared_support": squared,
            "cv2": _rational(n * squared - total * total, total * total),
            "hhi_relationship": "CV2_EQUALS_N_TIMES_HHI_MINUS_ONE",
            "rate_status": "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1",
        }

    ranked = sorted(
        eligible_rows,
        key=lambda row: (
            counts[row["cell_id"]] != 0,
            counts[row["cell_id"]],
            row["cell_ordinal"],
        ),
    )
    return {
        "schema_version": RESULT_SCHEMA,
        "profile_id": profile_id,
        "input_bindings": input_bindings,
        "metric_identity": {
            "canonical_name": "EVIDENCE_COVERAGE_DISPERSION_POPULATION_CV2",
            "research_alias": "ONE_SCALE_CATEGORICAL_LACUNARITY_ALIAS_ONLY",
            "spatial_claim": "NONE",
            "multiscale_claim": "NONE",
        },
        "coverage_summary": {
            "roster_cell_count": len(universe["cell_roster"]),
            "eligible_required_cell_count": n,
            "unavailable_cell_count": state_counts[UNAVAILABLE],
            "pending_eligibility_cell_count": state_counts[PENDING],
            "ineligible_cell_count": state_counts[INELIGIBLE],
            "observed_nonzero_cell_count": n - zero,
            "zero_cell_count": zero,
            "evidence_item_count": total,
            "gap_fraction": _rational(zero, n),
            "coverage_fraction": _rational(n - zero, n),
        },
        "dispersion_summary": dispersion,
        "cell_counts": [
            {
                "cell_ordinal": row["cell_ordinal"],
                "cell_id": row["cell_id"],
                "eligibility_status": ELIGIBLE,
                "support_count": counts[row["cell_id"]],
            }
            for row in eligible_rows
        ],
        "recommendations": [
            {
                "recommendation_ordinal": ordinal,
                "cell_ordinal": row["cell_ordinal"],
                "cell_id": row["cell_id"],
                "support_count": counts[row["cell_id"]],
                "reason": (
                    "ZERO_SUPPORT_REQUIRED_CELL"
                    if counts[row["cell_id"]] == 0
                    else "MINIMUM_SUPPORT_REQUIRED_CELL"
                ),
            }
            for ordinal, row in enumerate(ranked)
        ],
        "classification": CLASSIFICATION,
        "authority_boundary": {
            "authority": "NON_AUTHORITY",
            "recommendation_authority": "ADVISORY_ONLY",
            "decision_effect": "NONE",
            "execution_authority": "NOT_GRANTED",
            "scientific_status": "STRUCTURE_ONLY",
            "evidence_packet_effect": "NONE",
        },
    }


def _mutate(raw: bytes, change: Callable[[dict[str, Any]], None]) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def _replace_path(value: Any, path: tuple[Any, ...], replacement: Any) -> None:
    target = value
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement


def _integer_paths(value: Any, path: tuple[Any, ...] = ()):
    if type(value) is dict:
        for key, item in value.items():
            yield from _integer_paths(item, (*path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _integer_paths(item, (*path, index))
    elif type(value) is int:
        yield path, value


def _reachable_mutable_backings(value: Any) -> tuple[Any, ...]:
    found: list[Any] = []
    seen: set[int] = set()

    def visit(node: Any) -> None:
        identity = id(node)
        if identity in seen:
            return
        seen.add(identity)
        for referent in gc.get_referents(node):
            if type(referent) is type:
                continue
            if type(referent) in (dict, list, set, bytearray):
                found.append(referent)
            elif isinstance(referent, tuple):
                visit(referent)

    visit(value)
    return tuple(found)


def _json_node_count(value: Any) -> int:
    if type(value) is dict:
        return 1 + sum(1 + _json_node_count(item) for item in value.values())
    if type(value) is list:
        return 1 + sum(_json_node_count(item) for item in value)
    return 1


def _artifact_seal(artifact: Any) -> Any:
    require = getattr(sut, "_require_artifact_seal", None)
    if require is not None:
        return require(artifact)
    registry = getattr(sut, "_SEALS", None)
    assert registry is not None
    seal = registry[id(artifact)]
    assert seal.artifact() is artifact
    return seal


def _callable_graph_mutable_stores(*roots: Any) -> tuple[Any, ...]:
    """Find reachable mutable registry-shaped stores without invoking callbacks."""

    found: list[Any] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if type(value) in (dict, list, set, bytearray):
            found.append(value)
            return
        if inspect.isfunction(value):
            defaults = value.__defaults__ or ()
            kwdefaults = tuple((value.__kwdefaults__ or {}).values())
            cells = tuple(
                cell.cell_contents
                for cell in (value.__closure__ or ())
                if hasattr(cell, "cell_contents")
            )
            for item in (*defaults, *kwdefaults, *cells):
                visit(item)
            return
        if type(value) is tuple:
            for item in value:
                visit(item)
            return
        if isinstance(value, property):
            if value.fget is not None:
                visit(value.fget)

    for root in roots:
        visit(root)
    return tuple(found)


def _seal_registry_snapshots(root: Any) -> tuple[tuple[Any, ...], ...]:
    found: list[tuple[Any, ...]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if inspect.isfunction(value):
            for cell in value.__closure__ or ():
                try:
                    visit(cell.cell_contents)
                except ValueError:
                    pass
            return
        if type(value) is tuple:
            if value and all(
                type(item) is tuple
                and len(item) == 2
                and type(item[0]) is int
                and hasattr(item[1], "artifact")
                for item in value
            ):
                found.append(value)
            for item in value:
                visit(item)

    visit(root)
    return tuple(found)


def _seal_registry_cells(root: Any) -> tuple[Any, ...]:
    """Locate registry closure cells for the explicit reflection-boundary test."""

    found: list[Any] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if inspect.isfunction(value):
            for cell in value.__closure__ or ():
                try:
                    item = cell.cell_contents
                except ValueError:
                    continue
                if (
                    type(item) is tuple
                    and item
                    and all(
                        type(pair) is tuple
                        and len(pair) == 2
                        and type(pair[0]) is int
                        and hasattr(pair[1], "artifact")
                        for pair in item
                    )
                ):
                    found.append(cell)
                visit(item)
            return
        if type(value) is tuple:
            for item in value:
                visit(item)

    visit(root)
    return tuple(found)


def _reachable_module_global_loads(*roots: Any) -> dict[str, tuple[str, ...]]:
    found: dict[str, tuple[str, ...]] = {}
    seen: set[int] = set()

    def visit(value: Any) -> None:
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if inspect.isfunction(value):
            if value.__module__ == sut.__name__:
                names = tuple(
                    sorted(
                        {
                            str(instruction.argval)
                            for instruction in dis.get_instructions(value)
                            if instruction.opname == "LOAD_GLOBAL"
                            and instruction.argval in vars(sut)
                        }
                    )
                )
                if names:
                    found[value.__qualname__] = names
            for item in value.__defaults__ or ():
                visit(item)
            for item in (value.__kwdefaults__ or {}).values():
                visit(item)
            for cell in value.__closure__ or ():
                try:
                    visit(cell.cell_contents)
                except ValueError:
                    pass
        elif type(value) is tuple:
            for item in value:
                visit(item)
        elif isinstance(value, property) and value.fget is not None:
            visit(value.fget)

    for root in roots:
        visit(root)
    return found


def test_public_contract_names_and_surface_are_exact() -> None:
    assert sut.EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_SCHEMA == UNIVERSE_SCHEMA
    assert sut.EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_MEDIA_TYPE == UNIVERSE_MEDIA_TYPE
    assert sut.EVIDENCE_COVERAGE_OBSERVATION_SCHEMA == OBSERVATION_SCHEMA
    assert sut.EVIDENCE_COVERAGE_OBSERVATION_MEDIA_TYPE == OBSERVATION_MEDIA_TYPE
    assert sut.EVIDENCE_COVERAGE_METRIC_POLICY_SCHEMA == POLICY_SCHEMA
    assert sut.EVIDENCE_COVERAGE_METRIC_POLICY_MEDIA_TYPE == POLICY_MEDIA_TYPE
    assert sut.EVIDENCE_COVERAGE_DISPERSION_SCHEMA == RESULT_SCHEMA
    assert sut.EVIDENCE_COVERAGE_DISPERSION_MEDIA_TYPE == RESULT_MEDIA_TYPE
    assert sut.EVIDENCE_COVERAGE_DISPERSION_SPEC_REPOSITORY_PATH == SPEC_RELATIVE_PATH
    assert sut.EVIDENCE_COVERAGE_DISPERSION_SPEC_SHA256 == SPEC_SHA256
    assert sut.EVIDENCE_COVERAGE_DISPERSION_SPEC_BYTE_LENGTH == SPEC_BYTE_LENGTH
    assert set(sut.__all__) == {
        "EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_SCHEMA",
        "EVIDENCE_COVERAGE_REQUIRED_UNIVERSE_MEDIA_TYPE",
        "EVIDENCE_COVERAGE_OBSERVATION_SCHEMA",
        "EVIDENCE_COVERAGE_OBSERVATION_MEDIA_TYPE",
        "EVIDENCE_COVERAGE_METRIC_POLICY_SCHEMA",
        "EVIDENCE_COVERAGE_METRIC_POLICY_MEDIA_TYPE",
        "EVIDENCE_COVERAGE_DISPERSION_SCHEMA",
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
    }
    assert sut.EVIDENCE_COVERAGE_MAX_DIMENSIONS == MAX_DIMENSIONS
    assert sut.EVIDENCE_COVERAGE_MAX_ROSTER_CELLS == MAX_ROSTER_CELLS
    assert sut.EVIDENCE_COVERAGE_MAX_ELIGIBLE_CELLS == MAX_ROSTER_CELLS
    assert sut.EVIDENCE_COVERAGE_MAX_EVIDENCE_ITEMS == MAX_EVIDENCE_ITEMS
    assert sut.EVIDENCE_COVERAGE_MAX_IDENTIFIER_UTF8_BYTES == 128
    assert sut.EVIDENCE_COVERAGE_MAX_RECOMMENDATIONS == MAX_ROSTER_CELLS
    assert sut.EVIDENCE_COVERAGE_MAX_PROCESS_SEALS == 4_096


def test_frozen_v02_spec_identity_is_exactly_bound() -> None:
    path = ROOT / Path(SPEC_RELATIVE_PATH)
    raw = path.read_bytes()
    assert len(raw) == SPEC_BYTE_LENGTH
    assert _sha(raw) == SPEC_SHA256


def test_build_matches_independent_byte_oracle_and_is_deterministic() -> None:
    fixture = _fixture((0, 0, 1, 1, 1, 1, 1, 1, 1, 3))
    expected = _independent_expected_result(fixture)
    artifact = _build(fixture)
    assert artifact.raw_bytes == canonical_json_bytes(expected)
    assert json.loads(artifact.raw_bytes) == expected
    assert artifact.profile_id == expected["profile_id"]
    assert artifact.sha256 == _sha(artifact.raw_bytes)
    assert artifact.byte_length == len(artifact.raw_bytes)
    assert _build(fixture) == artifact
    assert artifact.artifact_ref == ArtifactRef(
        artifact_id=artifact.profile_id,
        sha256=artifact.sha256,
        byte_length=artifact.byte_length,
        media_type=RESULT_MEDIA_TYPE,
    )


def test_worked_example_reduces_fractions_and_cv2_exactly() -> None:
    payload = json.loads(_build(_fixture((0, 0, 1, 1, 1, 1, 1, 1, 1, 3))).raw_bytes)
    assert payload["coverage_summary"]["gap_fraction"] == {
        "numerator": 1,
        "denominator": 5,
    }
    assert payload["coverage_summary"]["coverage_fraction"] == {
        "numerator": 4,
        "denominator": 5,
    }
    assert payload["dispersion_summary"]["cv2"] == {
        "numerator": 3,
        "denominator": 5,
    }


@pytest.mark.parametrize(
    "counts",
    [
        (1,),
        (1, 1),
        (1, 2),
        (0, 1, 5),
        (2, 3, 5, 7),
        (0, 0, 0, 9),
        (11, 11, 11, 11, 11),
        tuple((index * 7 + 3) % 13 for index in range(31)),
    ],
)
def test_exact_arithmetic_properties_match_fraction_oracle(
    counts: tuple[int, ...],
) -> None:
    payload = json.loads(_build(_fixture(counts)).raw_bytes)
    summary = payload["dispersion_summary"]
    n = len(counts)
    total = sum(counts)
    squared = sum(value * value for value in counts)
    expected = Fraction(n * squared - total * total, total * total)
    actual = Fraction(summary["cv2"]["numerator"], summary["cv2"]["denominator"])
    hhi = sum(Fraction(value * value, total * total) for value in counts)
    assert actual == expected == n * hhi - 1
    assert 0 <= actual <= n - 1
    assert gcd(summary["cv2"]["numerator"], summary["cv2"]["denominator"]) == 1


def test_exhaustive_small_integer_count_profiles_match_independent_oracle() -> None:
    checked = 0
    for n in range(1, 6):
        for counts in itertools.product(range(4), repeat=n):
            if not any(counts):
                continue
            summary = json.loads(_build(_fixture(counts)).raw_bytes)[
                "dispersion_summary"
            ]
            total = sum(counts)
            squared = sum(value * value for value in counts)
            expected = Fraction(n * squared - total * total, total * total)
            actual = Fraction(
                summary["cv2"]["numerator"], summary["cv2"]["denominator"]
            )
            assert actual == expected
            checked += 1
    assert checked == sum(4**n - 1 for n in range(1, 6))


def test_dispersion_is_permutation_invariant_while_profile_identity_is_not() -> None:
    counts = (0, 1, 3, 2, 0)
    base = _build(_fixture(counts))
    base_payload = json.loads(base.raw_bytes)
    for permutation in ((0, 3, 1, 2, 0), (2, 0, 0, 1, 3), tuple(reversed(counts))):
        candidate = _build(_fixture(permutation))
        candidate_payload = json.loads(candidate.raw_bytes)
        assert candidate_payload["dispersion_summary"]["cv2"] == (
            base_payload["dispersion_summary"]["cv2"]
        )
        assert candidate.profile_id != base.profile_id


@pytest.mark.parametrize("counts", [(1,), (1, 1, 1), (2, 2, 2, 2), (17,) * 9])
def test_uniform_positive_support_has_zero_dispersion(counts: tuple[int, ...]) -> None:
    summary = json.loads(_build(_fixture(counts)).raw_bytes)["dispersion_summary"]
    assert summary["cv2"] == {"numerator": 0, "denominator": 1}


def test_positive_integer_scale_invariance_is_exact() -> None:
    counts = (0, 1, 2, 3)
    base = json.loads(_build(_fixture(counts)).raw_bytes)["dispersion_summary"]["cv2"]
    for scale in (2, 3, 17, 257):
        scaled = json.loads(
            _build(_fixture(tuple(scale * count for count in counts))).raw_bytes
        )["dispersion_summary"]["cv2"]
        assert scaled == base


def test_one_cell_concentration_reaches_exact_upper_bound() -> None:
    for n in (1, 2, 7, 29):
        counts = (19,) + (0,) * (n - 1)
        cv2 = json.loads(_build(_fixture(counts)).raw_bytes)["dispersion_summary"][
            "cv2"
        ]
        assert Fraction(cv2["numerator"], cv2["denominator"]) == n - 1


def test_all_zero_is_unavailable_without_numeric_substitute() -> None:
    payload = json.loads(_build(_fixture((0, 0, 0, 0))).raw_bytes)
    assert payload["coverage_summary"]["gap_fraction"] == {
        "numerator": 1,
        "denominator": 1,
    }
    assert payload["coverage_summary"]["coverage_fraction"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert payload["dispersion_summary"] == {
        "status": "UNAVAILABLE_ALL_CELLS_ZERO",
        "total_support": 0,
        "sum_squared_support": 0,
        "cv2": "ABSENT",
        "hhi_relationship": "UNAVAILABLE_ALL_CELLS_ZERO",
        "rate_status": "UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1",
    }


def test_eligibility_partition_excludes_noneligible_cells_from_metrics_and_ranking() -> None:
    statuses = (ELIGIBLE, UNAVAILABLE, PENDING, INELIGIBLE, ELIGIBLE)
    fixture = _fixture((0, 0, 0, 0, 2), statuses=statuses)
    payload = json.loads(_build(fixture).raw_bytes)
    coverage = payload["coverage_summary"]
    assert coverage == {
        "roster_cell_count": 5,
        "eligible_required_cell_count": 2,
        "unavailable_cell_count": 1,
        "pending_eligibility_cell_count": 1,
        "ineligible_cell_count": 1,
        "observed_nonzero_cell_count": 1,
        "zero_cell_count": 1,
        "evidence_item_count": 2,
        "gap_fraction": {"numerator": 1, "denominator": 2},
        "coverage_fraction": {"numerator": 1, "denominator": 2},
    }
    assert [row["cell_ordinal"] for row in payload["cell_counts"]] == [0, 4]
    assert [row["cell_ordinal"] for row in payload["recommendations"]] == [0, 4]
    assert {
        row["cell_ordinal"] for row in payload["cell_counts"]
    }.isdisjoint({1, 2, 3})


def test_recommendation_order_is_zero_then_minimum_support_then_ordinal() -> None:
    counts = (2, 0, 1, 0, 2, 1)
    recommendations = json.loads(_build(_fixture(counts)).raw_bytes)[
        "recommendations"
    ]
    assert [row["cell_ordinal"] for row in recommendations] == [1, 3, 2, 5, 0, 4]
    assert [row["recommendation_ordinal"] for row in recommendations] == list(range(6))
    assert [row["reason"] for row in recommendations] == [
        "ZERO_SUPPORT_REQUIRED_CELL",
        "ZERO_SUPPORT_REQUIRED_CELL",
        "MINIMUM_SUPPORT_REQUIRED_CELL",
        "MINIMUM_SUPPORT_REQUIRED_CELL",
        "MINIMUM_SUPPORT_REQUIRED_CELL",
        "MINIMUM_SUPPORT_REQUIRED_CELL",
    ]


def test_cv2_does_not_change_stage1_recommendation_order() -> None:
    profiles = ((0, 1, 2, 3), (0, 10, 20, 30), (0, 1, 100, 1_000))
    rankings = []
    dispersions = []
    for counts in profiles:
        payload = json.loads(_build(_fixture(counts)).raw_bytes)
        rankings.append(tuple(row["cell_ordinal"] for row in payload["recommendations"]))
        dispersions.append(payload["dispersion_summary"]["cv2"])
    assert rankings == [(0, 1, 2, 3)] * 3
    assert len({tuple(value.items()) for value in dispersions}) > 1


def test_build_load_and_replay_are_fresh_exact_equal_artifacts() -> None:
    fixture = _fixture((0, 2, 1, 5))
    built = _build(fixture)
    loaded = _load(built.raw_bytes, fixture)
    replayed = sut.replay_evidence_coverage_dispersion(built)
    assert built == loaded == replayed
    assert built is not loaded and built is not replayed
    assert built.payload is not loaded.payload and built.payload is not replayed.payload
    assert built.artifact_ref.verify_bytes(built.raw_bytes)
    assert loaded.artifact_ref.verify_bytes(loaded.raw_bytes)
    assert replayed.artifact_ref.verify_bytes(replayed.raw_bytes)


def test_result_load_rederives_every_semantic_field() -> None:
    fixture = _fixture((0, 1, 4))
    artifact = _build(fixture)
    mutations = (
        lambda value: value["coverage_summary"].__setitem__("zero_cell_count", 0),
        lambda value: value["dispersion_summary"].__setitem__(
            "cv2", {"numerator": 0, "denominator": 1}
        ),
        lambda value: value["recommendations"][0].__setitem__(
            "reason", "MINIMUM_SUPPORT_REQUIRED_CELL"
        ),
        lambda value: value["authority_boundary"].__setitem__(
            "execution_authority", "GRANTED"
        ),
        lambda value: value.__setitem__("classification", "PRODUCTION"),
    )
    for mutation in mutations:
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _load(_mutate(artifact.raw_bytes, mutation), fixture)


def test_result_cannot_relabel_noneligible_roster_cells_as_gaps_or_recommendations() -> None:
    fixture = _fixture(
        (0, 0, 0, 0, 2), statuses=(ELIGIBLE, UNAVAILABLE, PENDING, INELIGIBLE, ELIGIBLE)
    )
    artifact = _build(fixture)
    forged = json.loads(artifact.raw_bytes)
    forged["coverage_summary"]["eligible_required_cell_count"] = 5
    forged["coverage_summary"]["zero_cell_count"] = 4
    forged["coverage_summary"]["gap_fraction"] = {"numerator": 4, "denominator": 5}
    for cell_ordinal in (1, 2, 3):
        forged["cell_counts"].append(
            {
                "cell_ordinal": cell_ordinal,
                "cell_id": f"cell-{cell_ordinal:04d}",
                "eligibility_status": ELIGIBLE,
                "support_count": 0,
            }
        )
        forged["recommendations"].append(
            {
                "recommendation_ordinal": len(forged["recommendations"]),
                "cell_ordinal": cell_ordinal,
                "cell_id": f"cell-{cell_ordinal:04d}",
                "support_count": 0,
                "reason": "ZERO_SUPPORT_REQUIRED_CELL",
            }
        )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _load(canonical_json_bytes(forged), fixture)


def test_old_result_rejects_against_rebound_universe_even_when_observation_is_rebound() -> None:
    fixture = _fixture((0, 1, 2))
    artifact = _build(fixture)
    changed_universe = json.loads(fixture.universe_bytes)
    changed_universe["eligibility_snapshot_id"] = "synthetic-eligibility-snapshot-v2"
    rebound = _rebuild_fixture(
        fixture,
        universe_value=changed_universe,
        rebind_observation_universe=True,
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _load(artifact.raw_bytes, rebound)


def test_old_result_rejects_protocol_scope_and_eligibility_identity_substitution() -> None:
    fixture = _fixture((0, 1, 2))
    artifact = _build(fixture)

    protocol_observation = json.loads(fixture.observation_bytes)
    protocol_observation["observation_protocol_id"] = "synthetic-observation-protocol-v2"
    protocol_changed = _rebuild_fixture(
        fixture, observation_value=protocol_observation
    )

    scope_universe = json.loads(fixture.universe_bytes)
    scope_observation = json.loads(fixture.observation_bytes)
    replacement_scope = _identity_ref(
        "synthetic-scope-binding-v2",
        body=b'{"scope":"synthetic-only-v2"}',
        media_type="application/vnd.cas-harness.synthetic-scope-binding+json",
    )
    scope_universe["scope_binding_ref"] = replacement_scope
    scope_observation["scope_binding_ref"] = replacement_scope
    scope_changed = _rebuild_fixture(
        fixture,
        universe_value=scope_universe,
        observation_value=scope_observation,
        rebind_observation_universe=True,
    )

    eligibility_universe = json.loads(fixture.universe_bytes)
    eligibility_universe["cell_roster"][2]["eligibility_status"] = UNAVAILABLE
    eligibility_observation = json.loads(fixture.observation_bytes)
    eligibility_observation["evidence_items"] = [
        item
        for item in eligibility_observation["evidence_items"]
        if item["cell_id"] != "cell-0002"
    ]
    for ordinal, item in enumerate(eligibility_observation["evidence_items"]):
        item["item_ordinal"] = ordinal
    eligibility_changed = _rebuild_fixture(
        fixture,
        universe_value=eligibility_universe,
        observation_value=eligibility_observation,
        rebind_observation_universe=True,
    )

    for changed in (protocol_changed, scope_changed, eligibility_changed):
        replacement = _build(changed)
        assert replacement.profile_id != artifact.profile_id
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _load(artifact.raw_bytes, changed)


@pytest.mark.parametrize("parameter", ["required_universe_bytes", "observation_bytes", "metric_policy_bytes"])
@pytest.mark.parametrize("replacement_factory", [bytearray, memoryview])
def test_public_inputs_require_exact_builtin_bytes(
    parameter: str,
    replacement_factory: Callable[[bytes], Any],
) -> None:
    fixture = _fixture()
    arguments = {
        "required_universe_bytes": fixture.universe_bytes,
        "observation_bytes": fixture.observation_bytes,
        "metric_policy_bytes": fixture.policy_bytes,
    }
    arguments[parameter] = replacement_factory(arguments[parameter])
    with pytest.raises(sut.EvidenceCoverageDispersionError, match="exact built-in bytes"):
        sut.build_evidence_coverage_dispersion(**arguments)


def test_bytes_subclasses_and_nonbytes_result_snapshot_reject() -> None:
    class HostileBytes(bytes):
        pass

    fixture = _fixture()
    with pytest.raises(sut.EvidenceCoverageDispersionError, match="exact built-in bytes"):
        sut.build_evidence_coverage_dispersion(
            required_universe_bytes=HostileBytes(fixture.universe_bytes),
            observation_bytes=fixture.observation_bytes,
            metric_policy_bytes=fixture.policy_bytes,
        )
    artifact = _build(fixture)
    with pytest.raises(sut.EvidenceCoverageDispersionError, match="exact built-in bytes"):
        _load(bytearray(artifact.raw_bytes), fixture)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "target",
    ["universe", "observation", "policy", "result"],
)
def test_unknown_keys_reject_in_every_closed_top_level_schema(target: str) -> None:
    fixture = _fixture()
    if target == "universe":
        raw = _mutate(fixture.universe_bytes, lambda value: value.__setitem__("adjacency", []))
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, universe_value=json.loads(raw)))
    elif target == "observation":
        raw = _mutate(fixture.observation_bytes, lambda value: value.__setitem__("exposures", []))
        changed = _rebuild_fixture(fixture, observation_value=json.loads(raw))
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(changed)
    elif target == "policy":
        raw = _mutate(fixture.policy_bytes, lambda value: value.__setitem__("random_seed", 1))
        changed = _rebuild_fixture(fixture, policy_value=json.loads(raw))
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(changed)
    else:
        artifact = _build(fixture)
        raw = _mutate(artifact.raw_bytes, lambda value: value.__setitem__("adjacency", {}))
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _load(raw, fixture)


@pytest.mark.parametrize("target", ["universe", "observation", "policy", "result"])
def test_missing_required_keys_reject_in_every_closed_top_level_schema(target: str) -> None:
    fixture = _fixture()
    if target == "universe":
        changed = json.loads(fixture.universe_bytes)
        del changed["cell_roster"]
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, universe_value=changed))
    elif target == "observation":
        changed = json.loads(fixture.observation_bytes)
        del changed["evidence_items"]
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, observation_value=changed))
    elif target == "policy":
        changed = json.loads(fixture.policy_bytes)
        del changed["rate_mode"]
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, policy_value=changed))
    else:
        artifact = _build(fixture)
        changed = json.loads(artifact.raw_bytes)
        del changed["authority_boundary"]
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _load(canonical_json_bytes(changed), fixture)


def test_duplicate_keys_noncanonical_json_float_bom_and_non_utf8_reject() -> None:
    fixture = _fixture()
    float_value = json.loads(fixture.universe_bytes)
    float_value["cell_roster"][0]["cell_ordinal"] = 0.0
    invalid_universes = (
        b'{"schema_version":"a","schema_version":"b"}',
        json.dumps(fixture.universe_value, indent=2).encode("utf-8"),
        b"\xef\xbb\xbf" + fixture.universe_bytes,
        b"\xff",
        json.dumps(float_value, sort_keys=True, separators=(",", ":")).encode("ascii"),
    )
    for raw in invalid_universes:
        changed = Fixture(
            fixture.universe_value,
            fixture.observation_value,
            fixture.policy_value,
            raw,
            fixture.observation_bytes,
            fixture.policy_bytes,
        )
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(changed)


@pytest.mark.parametrize("target", ["universe", "observation", "policy", "result"])
def test_nested_or_otherwise_valid_duplicate_key_injection_rejects(target: str) -> None:
    fixture = _fixture((0, 1))
    artifact = _build(fixture)
    if target == "universe":
        raw = fixture.universe_bytes
        token = f'"byte_length":{SCOPE_REF["byte_length"]}'.encode("ascii")
    elif target == "observation":
        raw = fixture.observation_bytes
        token = f'"byte_length":{len(fixture.universe_bytes)}'.encode("ascii")
    elif target == "policy":
        raw = fixture.policy_bytes
        token = b'"counting_mode":"EXACT_ITEM_COUNT"'
    else:
        raw = artifact.raw_bytes
        token = f'"byte_length":{len(fixture.policy_bytes)}'.encode("ascii")
    assert token in raw
    injected = raw.replace(token, token + b"," + token, 1)
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        if target == "universe":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    injected,
                    fixture.observation_bytes,
                    fixture.policy_bytes,
                )
            )
        elif target == "observation":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    injected,
                    fixture.policy_bytes,
                )
            )
        elif target == "policy":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    fixture.observation_bytes,
                    injected,
                )
            )
        else:
            _load(injected, fixture)


@pytest.mark.parametrize("target", ["universe", "observation", "policy", "result"])
def test_redundant_unicode_escape_noncanonical_bytes_reject(target: str) -> None:
    fixture = _fixture((0, 1))
    artifact = _build(fixture)
    sources = {
        "universe": fixture.universe_bytes,
        "observation": fixture.observation_bytes,
        "policy": fixture.policy_bytes,
        "result": artifact.raw_bytes,
    }
    raw = sources[target]
    assert b"synthetic" in raw
    injected = raw.replace(b"synthetic", b"synthe\\u0074ic", 1)
    assert json.loads(injected) == json.loads(raw)
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        if target == "universe":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    injected,
                    fixture.observation_bytes,
                    fixture.policy_bytes,
                )
            )
        elif target == "observation":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    injected,
                    fixture.policy_bytes,
                )
            )
        elif target == "policy":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    fixture.observation_bytes,
                    injected,
                )
            )
        else:
            _load(injected, fixture)


def test_literal_utf8_noncanonical_dimension_value_rejects() -> None:
    fixture = _fixture((0, 1))
    assert b"value-0-0000" in fixture.universe_bytes
    injected = fixture.universe_bytes.replace(
        b"value-0-0000", "valué-0-0000".encode("utf-8"), 1
    )
    assert json.loads(injected)["cell_roster"][0]["dimension_values"][0] == (
        "valué-0-0000"
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(
            Fixture(
                fixture.universe_value,
                fixture.observation_value,
                fixture.policy_value,
                injected,
                fixture.observation_bytes,
                fixture.policy_bytes,
            )
        )


@pytest.mark.parametrize("target", ["universe", "observation", "policy", "result"])
@pytest.mark.parametrize("form", ["duplicate", "trailing-whitespace", "negative-zero"])
def test_ambiguous_or_noncanonical_forms_reject_for_every_document(
    target: str,
    form: str,
) -> None:
    fixture = _fixture((0, 1))
    artifact = _build(fixture)
    sources = {
        "universe": fixture.universe_bytes,
        "observation": fixture.observation_bytes,
        "policy": fixture.policy_bytes,
        "result": artifact.raw_bytes,
    }
    if form == "duplicate":
        raw = b'{"schema_version":"a","schema_version":"b"}'
    elif form == "trailing-whitespace":
        raw = sources[target] + b" "
    else:
        value = json.loads(sources[target])
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
        zero_paths = tuple(
            path for path, number in _integer_paths(value) if number == 0
        )
        if zero_paths:
            raw = raw.replace(b":0", b":-0", 1)
        else:
            raw = raw[:-1] + b',"negative_zero_probe":-0}'
        assert b":-0" in raw

    with pytest.raises(sut.EvidenceCoverageDispersionError):
        if target == "universe":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    raw,
                    fixture.observation_bytes,
                    fixture.policy_bytes,
                )
            )
        elif target == "observation":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    raw,
                    fixture.policy_bytes,
                )
            )
        elif target == "policy":
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    fixture.universe_bytes,
                    fixture.observation_bytes,
                    raw,
                )
            )
        else:
            _load(raw, fixture)


@pytest.mark.parametrize("target", ["universe", "observation", "result"])
def test_recursive_integer_boolean_aliases_reject(target: str) -> None:
    fixture = _fixture((0, 1, 2))
    artifact = _build(fixture)
    source = {
        "universe": fixture.universe_bytes,
        "observation": fixture.observation_bytes,
        "result": artifact.raw_bytes,
    }[target]
    integer_paths = tuple(_integer_paths(json.loads(source)))
    assert integer_paths
    for path, value in integer_paths:
        changed_value = json.loads(source)
        _replace_path(changed_value, path, bool(value))
        raw = canonical_json_bytes(changed_value)
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            if target == "universe":
                _build(
                    Fixture(
                        changed_value,
                        fixture.observation_value,
                        fixture.policy_value,
                        raw,
                        fixture.observation_bytes,
                        fixture.policy_bytes,
                    )
                )
            elif target == "observation":
                _build(
                    Fixture(
                        fixture.universe_value,
                        changed_value,
                        fixture.policy_value,
                        fixture.universe_bytes,
                        raw,
                        fixture.policy_bytes,
                    )
                )
            else:
                _load(raw, fixture)


def test_universe_rejects_duplicate_dimensions_cells_tuples_and_bad_ordinals() -> None:
    fixture = _fixture((0, 1, 2))
    mutations = (
        lambda value: value["dimension_order"].__setitem__(1, value["dimension_order"][0]),
        lambda value: value["cell_roster"][1].__setitem__(
            "cell_id", value["cell_roster"][0]["cell_id"]
        ),
        lambda value: value["cell_roster"][1].__setitem__(
            "dimension_values", value["cell_roster"][0]["dimension_values"]
        ),
        lambda value: value["cell_roster"][1].__setitem__("cell_ordinal", 9),
        lambda value: value["cell_roster"].reverse(),
        lambda value: value.__setitem__("dimension_order", []),
        lambda value: value.__setitem__("cell_roster", []),
    )
    for mutation in mutations:
        changed = json.loads(fixture.universe_bytes)
        mutation(changed)
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, universe_value=changed))


def test_universe_requires_at_least_one_eligible_cell_and_exact_dimension_arity() -> None:
    fixture = _fixture((0, 0), statuses=(UNAVAILABLE, PENDING))
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(fixture)
    fixture = _fixture((0, 1))
    changed = json.loads(fixture.universe_bytes)
    changed["cell_roster"][0]["dimension_values"].pop()
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, universe_value=changed))


def test_observation_rejects_duplicate_conflicting_and_content_alias_refs() -> None:
    fixture = _fixture((3,))
    original = json.loads(fixture.observation_bytes)

    duplicate = json.loads(fixture.observation_bytes)
    duplicate["evidence_items"][1]["evidence_ref"] = dict(
        duplicate["evidence_items"][0]["evidence_ref"]
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, observation_value=duplicate))

    conflict = json.loads(fixture.observation_bytes)
    conflict["evidence_items"][1]["evidence_ref"]["artifact_id"] = (
        conflict["evidence_items"][0]["evidence_ref"]["artifact_id"]
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, observation_value=conflict))

    alias = json.loads(fixture.observation_bytes)
    alias["evidence_items"][1]["evidence_ref"]["sha256"] = (
        alias["evidence_items"][0]["evidence_ref"]["sha256"]
    )
    alias["evidence_items"][1]["evidence_ref"]["byte_length"] = (
        alias["evidence_items"][0]["evidence_ref"]["byte_length"]
    )
    assert alias["evidence_items"][1]["evidence_ref"]["artifact_id"] != (
        alias["evidence_items"][0]["evidence_ref"]["artifact_id"]
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, observation_value=alias))
    assert original == fixture.observation_value


def test_observation_rejects_noncontiguous_ordinal_unknown_and_noneligible_cells() -> None:
    fixture = _fixture(
        (1, 0, 0, 0), statuses=(ELIGIBLE, UNAVAILABLE, PENDING, INELIGIBLE)
    )
    base = json.loads(fixture.observation_bytes)
    cases = []
    bad_ordinal = json.loads(fixture.observation_bytes)
    bad_ordinal["evidence_items"][0]["item_ordinal"] = 1
    cases.append(bad_ordinal)
    unknown = json.loads(fixture.observation_bytes)
    unknown["evidence_items"][0]["cell_id"] = "cell-unknown"
    cases.append(unknown)
    for ordinal in (1, 2, 3):
        noneligible = json.loads(fixture.observation_bytes)
        noneligible["evidence_items"][0]["cell_id"] = f"cell-{ordinal:04d}"
        cases.append(noneligible)
    for changed in cases:
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, observation_value=changed))
    assert base == fixture.observation_value


def test_identity_scope_universe_counting_and_classification_mismatches_reject() -> None:
    fixture = _fixture((0, 1))
    mutations = (
        lambda value: value["scope_binding_ref"].__setitem__("sha256", "F" * 64),
        lambda value: value["universe_ref"].__setitem__("sha256", "F" * 64),
        lambda value: value.__setitem__("counting_unit", "WEIGHTED_COUNT"),
        lambda value: value.__setitem__("classification", "PRODUCTION"),
        lambda value: value["universe_ref"].__setitem__("byte_length", 0),
    )
    for mutation in mutations:
        changed = json.loads(fixture.observation_bytes)
        mutation(changed)
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, observation_value=changed))


def test_artifact_ref_shapes_reject_zero_length_wrong_digest_case_and_extra_key() -> None:
    fixture = _fixture((1,))
    mutations = (
        lambda value: value["scope_binding_ref"].__setitem__("byte_length", 0),
        lambda value: value["scope_binding_ref"].__setitem__("sha256", "a" * 64),
        lambda value: value["scope_binding_ref"].__setitem__("extra", "forbidden"),
    )
    for mutation in mutations:
        changed = json.loads(fixture.universe_bytes)
        mutation(changed)
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, universe_value=changed))


def test_embedded_artifact_ref_length_may_exceed_direct_document_ceiling() -> None:
    fixture = _fixture((0, 1))
    universe = json.loads(fixture.universe_bytes)
    observation = json.loads(fixture.observation_bytes)
    embedded_length = MAX_DOCUMENT_BYTES + 1
    universe["scope_binding_ref"]["byte_length"] = embedded_length
    observation["scope_binding_ref"]["byte_length"] = embedded_length
    changed = _rebuild_fixture(
        fixture,
        universe_value=universe,
        observation_value=observation,
        rebind_observation_universe=True,
    )
    assert embedded_length == 2_000_001
    assert all(
        len(raw) <= MAX_DOCUMENT_BYTES
        for raw in (
            changed.universe_bytes,
            changed.observation_bytes,
            changed.policy_bytes,
        )
    )
    artifact = _build(changed)
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)

    universe["scope_binding_ref"]["byte_length"] = 2**31
    observation["scope_binding_ref"]["byte_length"] = 2**31
    too_large = _rebuild_fixture(
        fixture,
        universe_value=universe,
        observation_value=observation,
        rebind_observation_universe=True,
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(too_large)


def test_embedded_artifact_ref_media_type_limit_counts_python_characters() -> None:
    fixture = _fixture((0, 1))
    media_type = "\u00e9" * 128
    assert len(media_type) == 128
    assert len(media_type.encode("utf-8")) == 256
    assert ArtifactRef(
        artifact_id="synthetic-external-ref-v1",
        sha256="A" * 64,
        byte_length=1,
        media_type=media_type,
    ).media_type == media_type

    universe = json.loads(fixture.universe_bytes)
    observation = json.loads(fixture.observation_bytes)
    universe["scope_binding_ref"]["media_type"] = media_type
    observation["scope_binding_ref"]["media_type"] = media_type
    changed = _rebuild_fixture(
        fixture,
        universe_value=universe,
        observation_value=observation,
        rebind_observation_universe=True,
    )
    assert len(changed.universe_bytes) <= MAX_DOCUMENT_BYTES
    assert len(changed.observation_bytes) <= MAX_DOCUMENT_BYTES
    artifact = _build(changed)
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)

    universe["scope_binding_ref"]["media_type"] = media_type + "x"
    observation["scope_binding_ref"]["media_type"] = media_type + "x"
    too_long = _rebuild_fixture(
        fixture,
        universe_value=universe,
        observation_value=observation,
        rebind_observation_universe=True,
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(too_long)


def test_policy_is_frozen_and_rejects_rate_weight_random_and_threshold_modes() -> None:
    fixture = _fixture()
    mutations = (
        lambda value: value.__setitem__("counting_mode", "WEIGHTED_COUNT"),
        lambda value: value.__setitem__("dispersion_mode", "SAMPLE_CV2"),
        lambda value: value.__setitem__("rate_mode", "EXPOSURE_NORMALIZED"),
        lambda value: value["recommendation_order"].reverse(),
        lambda value: value.__setitem__("tie_break_order", ["RANDOM"]),
        lambda value: value.__setitem__("threshold", 2),
    )
    for mutation in mutations:
        changed = json.loads(fixture.policy_bytes)
        mutation(changed)
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(_rebuild_fixture(fixture, policy_value=changed))


def test_adjacency_graph_rate_exposure_and_extra_public_arguments_are_absent() -> None:
    build_parameters = tuple(inspect.signature(sut.build_evidence_coverage_dispersion).parameters)
    load_parameters = tuple(inspect.signature(sut.load_evidence_coverage_dispersion).parameters)
    assert build_parameters == (
        "required_universe_bytes",
        "observation_bytes",
        "metric_policy_bytes",
    )
    assert load_parameters == (
        "snapshot_bytes",
        "required_universe_bytes",
        "observation_bytes",
        "metric_policy_bytes",
    )
    fixture = _fixture((1,))
    observation = json.loads(fixture.observation_bytes)
    observation["evidence_items"][0]["exposure"] = 10
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, observation_value=observation))
    with pytest.raises(TypeError):
        sut.build_evidence_coverage_dispersion(
            required_universe_bytes=fixture.universe_bytes,
            observation_bytes=fixture.observation_bytes,
            metric_policy_bytes=fixture.policy_bytes,
            adjacency_bytes=b"{}",  # type: ignore[call-arg]
        )


def test_joint_universe_order_is_identity_bound_and_marginal_substitution_rejects() -> None:
    fixture = _fixture((0, 1, 2), dimensions=2)
    joint = _build(fixture)
    changed_universe = json.loads(fixture.universe_bytes)
    changed_universe["dimension_order"].reverse()
    for row in changed_universe["cell_roster"]:
        row["dimension_values"].reverse()
    changed = _rebuild_fixture(
        fixture,
        universe_value=changed_universe,
        rebind_observation_universe=True,
    )
    reordered_joint = _build(changed)
    assert reordered_joint.profile_id != joint.profile_id

    marginal = _fixture((0, 3), dimensions=1, universe_id="synthetic-marginal-v1")
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.build_evidence_coverage_dispersion(
            required_universe_bytes=marginal.universe_bytes,
            observation_bytes=fixture.observation_bytes,
            metric_policy_bytes=fixture.policy_bytes,
        )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("dimension_value", " leading"),
        ("dimension_value", "trailing "),
        ("dimension_value", "control\u0001"),
        ("dimension_value", "e\u0301"),
        ("dimension_value", "x" * 129),
        ("universe_id", "bad id"),
        ("eligibility_snapshot_id", "é"),
    ],
)
def test_identifier_and_dimension_value_profile_rejects(
    field: str,
    bad_value: str,
) -> None:
    fixture = _fixture((0, 1))
    changed = json.loads(fixture.universe_bytes)
    if field == "dimension_value":
        changed["cell_roster"][0]["dimension_values"][0] = bad_value
    else:
        changed[field] = bad_value
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, universe_value=changed))


@pytest.mark.parametrize(
    "code_point",
    [0x80, 0x85, 0x9F],
    ids=["U+0080", "U+0085", "U+009F"],
)
def test_dimension_values_reject_unicode_c1_cc_controls(code_point: int) -> None:
    control = chr(code_point)
    assert unicodedata.category(control) == "Cc"
    fixture = _fixture((0, 1))
    changed = json.loads(fixture.universe_bytes)
    changed["cell_roster"][0]["dimension_values"][0] = (
        f"synthetic{control}dimension"
    )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, universe_value=changed))


def test_dimension_value_limit_is_utf8_bytes_not_code_points() -> None:
    fixture = _fixture((0, 1))
    changed = json.loads(fixture.universe_bytes)
    changed["cell_roster"][0]["dimension_values"][0] = "é" * 65
    assert len(changed["cell_roster"][0]["dimension_values"][0]) == 65
    assert len(changed["cell_roster"][0]["dimension_values"][0].encode("utf-8")) == 130
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(_rebuild_fixture(fixture, universe_value=changed))


def test_global_document_byte_depth_node_and_integer_bounds_fail_closed() -> None:
    fixture = _fixture()
    too_large = b"{" + b" " * MAX_DOCUMENT_BYTES + b"}"
    too_deep_value: Any = 0
    for _ in range(42):
        too_deep_value = [too_deep_value]
    too_deep = dict(fixture.universe_value)
    too_deep["forbidden"] = too_deep_value
    too_many_nodes = dict(fixture.universe_value)
    too_many_nodes["forbidden"] = [0] * 50_001
    huge_integer = dict(fixture.universe_value)
    huge_integer["forbidden"] = 1 << 2_048
    for raw in (
        too_large,
        json.dumps(too_deep, separators=(",", ":")).encode("ascii"),
        json.dumps(too_many_nodes, separators=(",", ":")).encode("ascii"),
        json.dumps(huge_integer, separators=(",", ":")).encode("ascii"),
    ):
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _build(
                Fixture(
                    fixture.universe_value,
                    fixture.observation_value,
                    fixture.policy_value,
                    raw,
                    fixture.observation_bytes,
                    fixture.policy_bytes,
                )
            )


def test_tighter_dimension_roster_and_item_bounds_reject_above_maximum() -> None:
    too_many_dimensions = _fixture((0,), dimensions=MAX_DIMENSIONS + 1)
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(too_many_dimensions)

    too_many_cells = _fixture((0,) * (MAX_ROSTER_CELLS + 1), dimensions=1)
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(too_many_cells)

    too_many_items = _fixture((MAX_EVIDENCE_ITEMS + 1,), dimensions=1)
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _build(too_many_items)


def test_exact_maximum_roster_and_item_bounds_are_admitted_synthetic_only() -> None:
    fixture = _fixture((1,) * MAX_ROSTER_CELLS, dimensions=1)
    artifact = _build(fixture)
    payload = json.loads(artifact.raw_bytes)
    assert payload["coverage_summary"]["roster_cell_count"] == MAX_ROSTER_CELLS
    assert payload["coverage_summary"]["eligible_required_cell_count"] == (
        MAX_ROSTER_CELLS
    )
    assert payload["coverage_summary"]["evidence_item_count"] == MAX_EVIDENCE_ITEMS
    assert len(payload["cell_counts"]) == MAX_ROSTER_CELLS
    assert len(payload["recommendations"]) == MAX_ROSTER_CELLS
    assert payload["classification"] == CLASSIFICATION
    assert len(artifact.raw_bytes) <= MAX_DOCUMENT_BYTES
    assert _json_node_count(payload) <= 50_000


def test_maximum_roster_concentration_reaches_exact_cv2_upper_bound() -> None:
    counts = (MAX_EVIDENCE_ITEMS,) + (0,) * (MAX_ROSTER_CELLS - 1)
    payload = json.loads(_build(_fixture(counts, dimensions=1)).raw_bytes)
    cv2 = payload["dispersion_summary"]["cv2"]
    assert cv2 == {"numerator": MAX_ROSTER_CELLS - 1, "denominator": 1}


def test_payload_and_retained_snapshots_are_deeply_immutable_and_detached() -> None:
    fixture = _fixture((0, 1, 2))
    artifact = _build(fixture)
    assert _reachable_mutable_backings(artifact.payload) == ()
    assert not any(type(item) in (dict, list, set, bytearray) for item in gc.get_referents(artifact.payload))
    with pytest.raises(TypeError):
        artifact.payload["classification"] = "PRODUCTION"
    with pytest.raises(TypeError):
        artifact.payload["recommendations"][0]["reason"] = "FORGED"
    fixture.universe_value["classification"] = "PRODUCTION"
    fixture.observation_value["evidence_items"].clear()
    assert json.loads(artifact.raw_bytes)["classification"] == CLASSIFICATION
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)


def test_artifact_is_factory_only_and_object_new_slot_forgery_cannot_mint_ref() -> None:
    fixture = _fixture((0, 1))
    artifact = _build(fixture)
    with pytest.raises(TypeError, match="factory-only"):
        sut.EvidenceCoverageDispersionArtifact()  # type: ignore[call-arg]

    forged = object.__new__(sut.EvidenceCoverageDispersionArtifact)
    slot_names: list[str] = []
    for base in type(artifact).__mro__:
        slots = getattr(base, "__slots__", ())
        if type(slots) is str:
            slots = (slots,)
        slot_names.extend(slots)
    for name in slot_names:
        if name == "__weakref__" or not hasattr(artifact, name):
            continue
        object.__setattr__(forged, name, getattr(artifact, name))
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = forged.artifact_ref
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.replay_evidence_coverage_dispersion(forged)
    assert forged != artifact and artifact != forged


def test_exposed_registrar_cannot_bless_a_direct_slot_clone() -> None:
    artifact = _build(_fixture((0, 1, 2)))
    forged = object.__new__(sut.EvidenceCoverageDispersionArtifact)
    for name in ("raw_bytes", "sha256", "byte_length", "profile_id", "payload"):
        object.__setattr__(forged, name, getattr(artifact, name))

    registrar = getattr(sut, "_register_artifact_seal", None)
    if registrar is None:
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _ = forged.artifact_ref
        return
    defaults = registrar.__defaults__
    assert type(defaults) is tuple and defaults
    leaked_ticket = defaults[0]
    seal = _artifact_seal(artifact)
    seal_fields = (
        seal.raw_bytes,
        seal.sha256,
        seal.byte_length,
        seal.profile_id,
        seal.payload,
        seal.required_universe_bytes,
        seal.observation_bytes,
        seal.metric_policy_bytes,
    )
    try:
        registrar(leaked_ticket, forged, seal_fields)
    except sut.EvidenceCoverageDispersionError:
        pass
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = forged.artifact_ref


def test_registry_cell_reflection_is_an_explicit_non_provenance_boundary() -> None:
    """Registry reflection invalidates claims; equal descriptors prove no issuance."""

    fixture = _fixture((0, 1, 2))
    issued = _build(fixture)
    issued_ref = issued.artifact_ref
    source_seal = _artifact_seal(issued)

    exact_clone = object.__new__(sut.EvidenceCoverageDispersionArtifact)
    for name in ("raw_bytes", "sha256", "byte_length", "profile_id", "payload"):
        object.__setattr__(exact_clone, name, getattr(issued, name))
    exact_clone_seal = replace(source_seal, artifact=weakref.ref(exact_clone))

    authority_value = json.loads(issued.raw_bytes)
    authority_value["authority_boundary"]["authority"] = "AUTHORITY"
    authority_value["authority_boundary"]["execution_authority"] = "GRANTED"
    authority_raw = canonical_json_bytes(authority_value)
    authority_payload = sut._immutable_json(authority_value)
    authority_clone = object.__new__(sut.EvidenceCoverageDispersionArtifact)
    authority_fields = {
        "raw_bytes": authority_raw,
        "sha256": _sha(authority_raw),
        "byte_length": len(authority_raw),
        "profile_id": issued.profile_id,
        "payload": authority_payload,
    }
    for name, value in authority_fields.items():
        object.__setattr__(authority_clone, name, value)
    authority_clone_seal = replace(
        source_seal,
        artifact=weakref.ref(authority_clone),
        raw_bytes=authority_raw,
        sha256=_sha(authority_raw),
        byte_length=len(authority_raw),
        payload=authority_payload,
    )

    cells = _seal_registry_cells(sut._require_artifact_seal)
    assert len(cells) == 1
    registry_cell = cells[0]
    original_registry = registry_cell.cell_contents
    try:
        # Deliberate closure mutation is outside the provenance boundary and
        # invalidates every in-process seal claim made while it is installed.
        registry_cell.cell_contents = (
            *original_registry,
            (id(exact_clone), exact_clone_seal),
            (id(authority_clone), authority_clone_seal),
        )
        reflected_ref = exact_clone.artifact_ref
        assert exact_clone is not issued
        assert reflected_ref == issued_ref
        assert reflected_ref.verify_bytes(exact_clone.raw_bytes)
        assert (
            sut.replay_evidence_coverage_dispersion(exact_clone).artifact_ref
            == issued_ref
        )

        # Registry-only injection cannot defeat fresh semantic derivation.
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _ = authority_clone.artifact_ref
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            sut.replay_evidence_coverage_dispersion(authority_clone)
    finally:
        registry_cell.cell_contents = original_registry

    # Restoring the unmodified verifier removes even the exact clone's seal.
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = exact_clone.artifact_ref
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.replay_evidence_coverage_dispersion(exact_clone)
    assert issued.artifact_ref == issued_ref


def test_copy_deepcopy_pickle_and_dataclass_replace_cannot_create_sealed_clone() -> None:
    artifact = _build(_fixture((0, 1, 2)))
    for clone_factory in (copy.copy, copy.deepcopy):
        try:
            clone = clone_factory(artifact)
        except Exception:
            continue
        assert clone is not artifact
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _ = clone.artifact_ref
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            sut.replay_evidence_coverage_dispersion(clone)

    try:
        encoded = pickle.dumps(artifact)
        clone = pickle.loads(encoded)
    except Exception:
        pass
    else:
        assert clone is not artifact
        with pytest.raises(sut.EvidenceCoverageDispersionError):
            _ = clone.artifact_ref

    with pytest.raises((TypeError, ValueError)):
        replace(artifact)


def test_process_seal_weakref_cleanup_removes_dead_identity() -> None:
    artifact = _build(_fixture((0, 1)))
    identity = id(artifact)
    require = sut._require_artifact_seal
    closure_tuples = _seal_registry_snapshots(require)
    assert len(closure_tuples) == 1
    assert any(item[0] == identity for item in closure_tuples[0])
    del artifact
    gc.collect()
    closure_tuples_after = _seal_registry_snapshots(require)
    assert not any(
        type(item) is tuple and len(item) == 2 and item[0] == identity
        for registry in closure_tuples_after
        for item in registry
    )


def test_bounded_process_seal_eviction_fails_closed() -> None:
    fixture = _fixture((0,))
    oldest = _build(fixture)
    retained = [oldest]
    retained.extend(
        _build(fixture) for _ in range(sut.EVIDENCE_COVERAGE_MAX_PROCESS_SEALS)
    )
    require = sut._require_artifact_seal
    closure_registries = _seal_registry_snapshots(require)
    assert len(closure_registries) == 1
    assert len(closure_registries[0]) <= sut.EVIDENCE_COVERAGE_MAX_PROCESS_SEALS
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = oldest.artifact_ref
    assert retained[-1].artifact_ref.verify_bytes(retained[-1].raw_bytes)


def test_public_callable_graph_exposes_no_mutable_seal_registry_store() -> None:
    roots = (
        sut.build_evidence_coverage_dispersion,
        sut.load_evidence_coverage_dispersion,
        sut.replay_evidence_coverage_dispersion,
        sut.EvidenceCoverageDispersionArtifact.__eq__,
        sut.EvidenceCoverageDispersionArtifact.__ne__,
        sut.EvidenceCoverageDispersionArtifact.artifact_ref,
        sut._require_artifact_seal,
    )
    assert _callable_graph_mutable_stores(*roots) == ()

    artifact = _build(_fixture((0, 1)))
    forged = object.__new__(sut.EvidenceCoverageDispersionArtifact)
    for name in ("raw_bytes", "sha256", "byte_length", "profile_id", "payload"):
        object.__setattr__(forged, name, getattr(artifact, name))
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = forged.artifact_ref


def test_public_callable_graph_has_no_module_owned_global_dependency_loads() -> None:
    roots = (
        sut.build_evidence_coverage_dispersion,
        sut.load_evidence_coverage_dispersion,
        sut.replay_evidence_coverage_dispersion,
        sut.EvidenceCoverageDispersionArtifact.__eq__,
        sut.EvidenceCoverageDispersionArtifact.__ne__,
        sut.EvidenceCoverageDispersionArtifact.artifact_ref,
    )
    assert _reachable_module_global_loads(*roots) == {}


def test_hostile_callback_objects_reject_without_invoking_hooks() -> None:
    fixture = _fixture((0, 1))

    class Hostile:
        invoked = False

        def _fail(self, *_args, **_kwargs):
            type(self).invoked = True
            raise AssertionError("hostile callback invoked")

        __bytes__ = _fail
        __eq__ = _fail
        __hash__ = _fail
        __iter__ = _fail

    hostile = Hostile()
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.build_evidence_coverage_dispersion(
            required_universe_bytes=hostile,  # type: ignore[arg-type]
            observation_bytes=fixture.observation_bytes,
            metric_policy_bytes=fixture.policy_bytes,
        )
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.replay_evidence_coverage_dispersion(hostile)  # type: ignore[arg-type]
    assert not Hostile.invoked


@pytest.mark.parametrize("field", ["raw_bytes", "sha256", "byte_length", "profile_id", "payload"])
def test_sealed_artifact_public_slot_forgery_fails_fresh_replay(field: str) -> None:
    artifact = _build(_fixture((0, 1, 3)))
    replacements = {
        "raw_bytes": b"{}",
        "sha256": "F" * 64,
        "byte_length": 2,
        "profile_id": "ecd-forged",
        "payload": {"authority_boundary": {"authority": "AUTHORITY"}},
    }
    object.__setattr__(artifact, field, replacements[field])
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = artifact.artifact_ref
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.replay_evidence_coverage_dispersion(artifact)


@pytest.mark.parametrize(
    "name",
    ["required_universe_bytes", "observation_bytes", "metric_policy_bytes"],
)
def test_retained_input_snapshot_seal_forgery_fails_replay(name: str) -> None:
    candidate = _build(_fixture((0, 1, 2)))
    seal = _artifact_seal(candidate)
    assert type(getattr(seal, name)) is bytes
    object.__setattr__(seal, name, b"{}")
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        _ = candidate.artifact_ref
    with pytest.raises(sut.EvidenceCoverageDispersionError):
        sut.replay_evidence_coverage_dispersion(candidate)


def test_module_global_rebinding_cannot_change_build_load_replay_or_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture((0, 1, 3))
    baseline = _build(fixture)
    error_type = sut.EvidenceCoverageDispersionError

    forged_value = json.loads(baseline.raw_bytes)
    forged_value["authority_boundary"]["authority"] = "AUTHORITY"
    forged_value["authority_boundary"]["execution_authority"] = "GRANTED"
    forged_raw = canonical_json_bytes(forged_value)

    for name in (
        "canonical_json_bytes",
        "sha256_bytes",
        "load_json_object",
        "freeze_json",
        "ArtifactRef",
        "_fail",
        "_expect_keys",
        "_expect_list",
        "_expect_int",
        "_expect_machine_id",
        "_expect_dimension_value",
        "_parse_ref",
        "_parse_universe",
        "_parse_observation",
        "_parse_policy",
        "_ref_value",
        "_derived_ref",
        "_reduced",
        "_derive_value",
        "_make_artifact",
        "_load_canonical_object",
        "_immutable_json",
        "_exact_json_equal",
        "gcd",
        "_render_result",
        "_validate_result",
        "_artifact",
        "_immutable_json_value",
        "_register_artifact_seal",
        "_require_artifact_seal",
    ):
        if hasattr(sut, name):
            monkeypatch.setattr(sut, name, lambda *_args, **_kwargs: forged_value)
    for name in tuple(vars(sut)):
        if name.endswith(("_SCHEMA", "_MEDIA_TYPE")):
            monkeypatch.setattr(sut, name, "forged")
        elif name.startswith("EVIDENCE_COVERAGE_MAX_") or name in {
            "MAX_DOCUMENT_BYTES",
            "MAX_DEPTH",
            "MAX_NODES",
            "MAX_INTEGER_BITS",
        }:
            monkeypatch.setattr(sut, name, 1)
    monkeypatch.setattr(sut, "_COUNTING_UNIT", "FORGED")
    monkeypatch.setattr(sut, "_CELL_SEMANTICS", "FORGED")
    monkeypatch.setattr(sut, "_CLASSIFICATION", "PRODUCTION")
    monkeypatch.setattr(sut, "_ELIGIBLE", "INELIGIBLE_AT_SNAPSHOT")
    monkeypatch.setattr(sut, "_ELIGIBILITY_STATES", frozenset({"FORGED"}))
    monkeypatch.setattr(sut, "_Universe", lambda *_args, **_kwargs: forged_value)
    monkeypatch.setattr(sut, "_Observation", lambda *_args, **_kwargs: forged_value)
    monkeypatch.setattr(sut, "_ArtifactSeal", lambda *_args, **_kwargs: forged_value)
    monkeypatch.setattr(sut, "EvidenceCoverageDispersionArtifact", lambda: forged_value)
    monkeypatch.setattr(sut, "EvidenceCoverageDispersionError", RuntimeError)
    if hasattr(sut, "_SEALS"):
        monkeypatch.setattr(sut, "_SEALS", {})
    if hasattr(sut, "_SEAL_LOCK"):
        monkeypatch.setattr(sut, "_SEAL_LOCK", object())

    assert _build(fixture) == baseline
    assert _load(baseline.raw_bytes, fixture) == baseline
    assert sut.replay_evidence_coverage_dispersion(baseline) == baseline
    assert baseline.artifact_ref.verify_bytes(baseline.raw_bytes)
    with pytest.raises(error_type):
        _load(forged_raw, fixture)


def test_public_paths_perform_no_filesystem_network_process_clock_or_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture((0, 1, 2))
    artifact = _build(fixture)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external capability")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(os, "stat", forbidden)
    monkeypatch.setattr(os, "listdir", forbidden)
    monkeypatch.setattr(os, "scandir", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    assert _build(fixture) == artifact
    assert _load(artifact.raw_bytes, fixture) == artifact
    assert sut.replay_evidence_coverage_dispersion(artifact) == artifact
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)


def test_source_has_no_sensitive_io_model_numeric_or_provider_imports() -> None:
    source_path = SRC / "cas_harness_v2" / "diagnostic_evidence_coverage_dispersion.py"
    tree = ast.parse(source_path.read_bytes(), filename=source_path.as_posix())
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.lstrip(".").split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "asyncio",
            "datetime",
            "httpx",
            "importlib",
            "numpy",
            "os",
            "pathlib",
            "random",
            "requests",
            "socket",
            "sqlite3",
            "subprocess",
            "time",
            "torch",
            "transformers",
            "urllib",
        }
    )
    assert "socket" not in sut.__dict__
    assert "subprocess" not in sut.__dict__
    assert "requests" not in sut.__dict__
    assert "torch" not in sut.__dict__
    assert "numpy" not in sut.__dict__


def test_public_surface_has_no_activation_admission_packet_or_decision_capability() -> None:
    lowered = {name.lower() for name in sut.__all__}
    forbidden_tokens = (
        "accept",
        "activate",
        "admit",
        "authorize",
        "execute",
        "freeze",
        "license",
        "packet",
        "provider",
        "runpod",
        "spend",
    )
    assert not any(token in name for name in lowered for token in forbidden_tokens)
    payload = json.loads(_build(_fixture()).raw_bytes)
    assert payload["authority_boundary"] == {
        "authority": "NON_AUTHORITY",
        "recommendation_authority": "ADVISORY_ONLY",
        "decision_effect": "NONE",
        "execution_authority": "NOT_GRANTED",
        "scientific_status": "STRUCTURE_ONLY",
        "evidence_packet_effect": "NONE",
    }


def test_canonical_and_packaged_source_are_byte_identical() -> None:
    relative = Path("cas_harness_v2") / "diagnostic_evidence_coverage_dispersion.py"
    canonical = SRC / relative
    packaged = ROOT / "noetic-compass-scaffold" / "noetic-compass" / relative
    assert canonical.is_file()
    assert packaged.is_file()
    assert packaged.read_bytes() == canonical.read_bytes()
    assert hashlib.sha256(packaged.read_bytes()).digest() == hashlib.sha256(
        canonical.read_bytes()
    ).digest()
