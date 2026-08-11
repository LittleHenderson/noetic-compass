from __future__ import annotations

import ast
import builtins
import copy
from dataclasses import dataclass, replace
import json
from pathlib import Path
import pickle
import socket
import subprocess
from types import MappingProxyType

import pytest

import cas_harness_v2.jspace_shadow_contract as shadow_module
from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.jspace_shadow_contract import (
    ADJOINT_IDENTITY,
    ARTIFACT_CORRUPTION,
    AUTOGRAD_IDENTITY,
    BACKEND_IDENTITY,
    BFLOAT16,
    COMPONENT_ROLES,
    CORRESPONDENCE_BASIS,
    DETACHED_GRAPH,
    DTYPE_DRIFT,
    FLOAT32,
    JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE,
    JSPACE_SHADOW_PROTOCOL_MEDIA_TYPE,
    JSPACE_VECTOR_MEDIA_TYPE,
    ADJOINT_VECTOR,
    JVP_VECTOR,
    TANGENT_VECTOR,
    VECTOR_ROLES,
    VJP_VECTOR,
    KNOWN_FAULT,
    KNOWN_FAULT_KINDS,
    MATCHED_CONTROL,
    NONE,
    NO_FAULT,
    NO_VERDICT,
    NON_AUTHORITY,
    OUTPUT_FUNCTIONAL,
    RANK_LOSS,
    REPLAY_ONLY,
    SCALAR_PROJECTION,
    SHADOW,
    SOURCE_IDENTITY,
    TANGENT_IDENTITY,
    TARGET,
    VECTOR_OUTPUT,
    WRONG_ADJOINT,
    WRONG_TANGENT,
    ZERO_DENOMINATOR_SCALAR_PROJECTION,
    JSpaceShadowBackendUnavailableError,
    JSpaceShadowReplayRequest,
    JSpaceShadowRow,
    JSpaceSourceMember,
    JSpaceVectorBinding,
    ReplayJSpaceShadowBackend,
    UnavailableJSpaceShadowBackend,
    build_jspace_registered_component_body,
    build_jspace_shadow_protocol,
    build_jspace_source_bundle_manifest,
    build_jspace_vector_body,
    build_replay_jspace_shadow_backend,
    build_unavailable_jspace_shadow_backend,
    load_jspace_shadow_protocol,
    load_jspace_source_bundle_manifest,
    replay_jspace_shadow,
    replay_jspace_shadow_protocol,
    replay_jspace_source_bundle_manifest,
)


def ref(
    artifact_id: str,
    body: bytes,
    media_type: str = JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE,
) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


def vector_binding(
    *,
    row_id: str,
    role: str,
    registered_values: tuple[int, ...],
    observed_values: tuple[int, ...],
    dtype: str = FLOAT32,
) -> JSpaceVectorBinding:
    vector_id = f"{row_id}-{role.lower().replace('_', '-')}"
    body = build_jspace_vector_body(
        vector_id=vector_id,
        row_id=row_id,
        role=role,
        dimension=len(registered_values),
        dtype=dtype,
        registered_values=registered_values,
        observed_values=observed_values,
    )
    return JSpaceVectorBinding(
        role=role,
        artifact_ref=ref(vector_id, body, JSPACE_VECTOR_MEDIA_TYPE),
        body_bytes=body,
    )


def good_row(
    row_id: str,
    row_kind: str,
    *,
    expected_vector=(10, 20, 30, 40),
    observed_vector=(10, 20, 30, 40),
    expected_vjp_vector=None,
    observed_vjp_vector=None,
    tangent_registered=(1, 2, 3, 4),
    tangent_observed=None,
    adjoint_registered=(4, 3, 2, 1),
    adjoint_observed=None,
    **changes,
) -> JSpaceShadowRow:
    if expected_vjp_vector is None:
        expected_vjp_vector = expected_vector
    if observed_vjp_vector is None:
        observed_vjp_vector = observed_vector
    if tangent_observed is None:
        tangent_observed = tangent_registered
    if adjoint_observed is None:
        adjoint_observed = adjoint_registered
    values = dict(
        row_id=row_id,
        row_kind=row_kind,
        fault_kind=NO_FAULT,
        tangent_identity_matches=True,
        adjoint_identity_matches=True,
        graph_connected=True,
        expected_rank=2,
        observed_rank=2,
        expected_shape=(2, 2),
        observed_shape=(2, 2),
        expected_dtype=FLOAT32,
        observed_dtype=FLOAT32,
        all_finite=True,
        output_projection=VECTOR_OUTPUT,
        artifact_integrity=True,
        expected_vector=expected_vector,
        observed_vector=observed_vector,
        expected_vjp_vector=expected_vjp_vector,
        observed_vjp_vector=observed_vjp_vector,
        denominator_units=max(
            *(abs(item) for item in expected_vector),
            *(abs(item) for item in expected_vjp_vector),
        ),
    )
    values.update(changes)
    if "vector_bindings" not in values:
        values["vector_bindings"] = (
            vector_binding(
                row_id=row_id,
                role=TANGENT_VECTOR,
                registered_values=tangent_registered,
                observed_values=tangent_observed,
            ),
            vector_binding(
                row_id=row_id,
                role=ADJOINT_VECTOR,
                registered_values=adjoint_registered,
                observed_values=adjoint_observed,
            ),
            vector_binding(
                row_id=row_id,
                role=JVP_VECTOR,
                registered_values=expected_vector,
                observed_values=observed_vector,
            ),
            vector_binding(
                row_id=row_id,
                role=VJP_VECTOR,
                registered_values=expected_vjp_vector,
                observed_values=observed_vjp_vector,
            ),
        )
    return JSpaceShadowRow(**values)


def make_rows() -> tuple[JSpaceShadowRow, ...]:
    target = good_row(
        "target-row",
        TARGET,
        expected_vector=(100, 200, -100, 50),
        observed_vector=(101, 199, -100, 51),
        denominator_units=200,
    )
    control = good_row(
        "matched-control-row",
        MATCHED_CONTROL,
        expected_vector=(0, 0, 0, 0),
        observed_vector=(1, 0, 0, 0),
        denominator_units=0,
    )
    faults = (
        good_row(
            "known-fault-wrong-tangent",
            KNOWN_FAULT,
            fault_kind=WRONG_TANGENT,
            tangent_identity_matches=False,
            tangent_observed=(9, 2, 3, 4),
        ),
        good_row(
            "known-fault-wrong-adjoint",
            KNOWN_FAULT,
            fault_kind=WRONG_ADJOINT,
            adjoint_identity_matches=False,
            adjoint_observed=(9, 3, 2, 1),
        ),
        good_row(
            "known-fault-detached-graph",
            KNOWN_FAULT,
            fault_kind=DETACHED_GRAPH,
            graph_connected=False,
        ),
        good_row(
            "known-fault-rank-loss",
            KNOWN_FAULT,
            fault_kind=RANK_LOSS,
            observed_rank=1,
            observed_shape=(4,),
        ),
        good_row(
            "known-fault-dtype-drift",
            KNOWN_FAULT,
            fault_kind=DTYPE_DRIFT,
            observed_dtype=BFLOAT16,
        ),
        good_row(
            "known-fault-zero-denominator-scalar",
            KNOWN_FAULT,
            fault_kind=ZERO_DENOMINATOR_SCALAR_PROJECTION,
            expected_vector=(0, 0, 0, 0),
            observed_vector=(0, 0, 0, 0),
            denominator_units=0,
            output_projection=SCALAR_PROJECTION,
        ),
        good_row(
            "known-fault-artifact-corruption",
            KNOWN_FAULT,
            fault_kind=ARTIFACT_CORRUPTION,
            artifact_integrity=False,
        ),
    )
    return (target, control, *faults)


@dataclass(frozen=True)
class Fixture:
    members: tuple[JSpaceSourceMember, ...]
    source_bundle: object
    rows: tuple[JSpaceShadowRow, ...]
    protocol: object


def make_fixture() -> Fixture:
    members = []
    for role in COMPONENT_ROLES:
        component_id = f"component-{role.lower().replace('_', '-')}"
        body = build_jspace_registered_component_body(
            component_id=component_id,
            role=role,
            dimension=4,
            rank=2,
            shape=(2, 2),
            dtype=FLOAT32,
        )
        members.append(
            JSpaceSourceMember(
                role=role,
                artifact_ref=ref(component_id, body),
                body_bytes=body,
            )
        )
    members = tuple(members)
    source_bundle = build_jspace_source_bundle_manifest(
        bundle_id="jspace-source-bundle", members=members
    )
    rows = make_rows()
    protocol = build_jspace_shadow_protocol(
        protocol_id="jspace-shadow-protocol",
        source_bundle=source_bundle,
        absolute_tolerance_units=2,
        relative_tolerance_ppm=10_000,
        dose_schedule_units=(0, 1, 2, 4),
        rows=rows,
        phase=SHADOW,
        intervention=NONE,
    )
    return Fixture(
        members=members,
        source_bundle=source_bundle,
        rows=rows,
        protocol=protocol,
    )


def rebuild_protocol(fx: Fixture, *, rows=None, **changes):
    values = dict(
        protocol_id="jspace-shadow-protocol",
        source_bundle=fx.source_bundle,
        absolute_tolerance_units=2,
        relative_tolerance_ppm=10_000,
        dose_schedule_units=(0, 1, 2, 4),
        rows=fx.rows if rows is None else rows,
        phase=SHADOW,
        intervention=NONE,
    )
    values.update(changes)
    return build_jspace_shadow_protocol(**values)


def test_valid_shadow_binds_exact_registered_vectors_without_authority() -> None:
    fx = make_fixture()
    assert fx.source_bundle.payload["import_state"] == "NOT_IMPORTED"
    assert fx.source_bundle.payload["all_bodies_verified"] is True
    assert fx.protocol.payload["phase"] == SHADOW
    assert fx.protocol.payload["intervention"] == NONE
    assert fx.protocol.payload["status"] == {
        "mode": SHADOW,
        "intervention": NONE,
        "license": "NOT_LICENSED",
        "authority": NON_AUTHORITY,
        "verdict": NO_VERDICT,
    }
    assert fx.protocol.payload["boundary"]["canary_count"] == 0
    assert fx.protocol.payload["boundary"]["dose_executions"] == 0
    assert tuple(row.fault_kind for row in fx.protocol.rows if row.row_kind == KNOWN_FAULT) == KNOWN_FAULT_KINDS
    assert set(fx.protocol.payload["component_refs"]) == set(COMPONENT_ROLES)


def test_source_bundle_and_protocol_round_trip_exactly() -> None:
    fx = make_fixture()
    assert load_jspace_source_bundle_manifest(
        fx.source_bundle.raw_bytes, members=fx.members
    ) == fx.source_bundle
    assert replay_jspace_source_bundle_manifest(fx.source_bundle) == fx.source_bundle
    assert load_jspace_shadow_protocol(
        fx.protocol.raw_bytes, source_bundle=fx.source_bundle
    ) == fx.protocol
    assert replay_jspace_shadow_protocol(
        fx.protocol, source_bundle=fx.source_bundle
    ) == fx.protocol


def test_source_body_corruption_fails_before_any_import() -> None:
    fx = make_fixture()
    with pytest.raises(SchemaValidationError, match="body differs"):
        replace(fx.members[0], body_bytes=b"corrupted")


def test_source_bundle_missing_order_and_geometry_drift_fail_closed() -> None:
    fx = make_fixture()
    with pytest.raises(SchemaValidationError, match="every fixed component"):
        build_jspace_source_bundle_manifest(
            bundle_id="missing-component-bundle", members=fx.members[:-1]
        )
    with pytest.raises(SchemaValidationError, match="fixed role order"):
        build_jspace_source_bundle_manifest(
            bundle_id="wrong-order-bundle",
            members=(fx.members[1], fx.members[0], *fx.members[2:]),
        )
    role = fx.members[-1].role
    body = build_jspace_registered_component_body(
        component_id="geometry-drift-component",
        role=role,
        dimension=6,
        rank=2,
        shape=(2, 3),
        dtype=FLOAT32,
    )
    drift = JSpaceSourceMember(
        role=role,
        artifact_ref=ref("geometry-drift-component", body),
        body_bytes=body,
    )
    with pytest.raises(SchemaValidationError, match="geometry drifted"):
        build_jspace_source_bundle_manifest(
            bundle_id="geometry-drift-bundle",
            members=(*fx.members[:-1], drift),
        )


def test_component_content_alias_is_rejected_transitively() -> None:
    fx = make_fixture()
    original = fx.members[0]
    alias_ref = ArtifactRef(
        artifact_id="component-content-alias",
        sha256=original.artifact_ref.sha256,
        byte_length=original.artifact_ref.byte_length,
        media_type=original.artifact_ref.media_type,
    )
    alias = JSpaceSourceMember(
        role=fx.members[1].role,
        artifact_ref=alias_ref,
        body_bytes=original.body_bytes,
    )
    with pytest.raises(SchemaValidationError):
        build_jspace_source_bundle_manifest(
            bundle_id="aliased-bundle",
            members=(fx.members[0], alias, *fx.members[2:]),
        )


def test_mandatory_known_fault_rows_cannot_be_missing_duplicated_or_reordered() -> None:
    fx = make_fixture()
    with pytest.raises(SchemaValidationError, match="known-fault"):
        rebuild_protocol(fx, rows=fx.rows[:-1])
    duplicated = (*fx.rows[:-1], fx.rows[-2])
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=duplicated)
    reordered = (*fx.rows[:2], fx.rows[3], fx.rows[2], *fx.rows[4:])
    with pytest.raises(SchemaValidationError, match="every known fault"):
        rebuild_protocol(fx, rows=reordered)


@pytest.mark.parametrize(
    ("index", "changes"),
    (
        (2, {"tangent_identity_matches": True}),
        (3, {"adjoint_identity_matches": True}),
        (4, {"graph_connected": True}),
        (5, {"observed_rank": 2, "observed_shape": (2, 2)}),
        (6, {"observed_dtype": FLOAT32}),
        (7, {"output_projection": VECTOR_OUTPUT}),
        (8, {"artifact_integrity": True}),
    ),
)
def test_each_known_fault_row_must_contain_its_exact_single_defect(
    index: int, changes: dict[str, object]
) -> None:
    fx = make_fixture()
    rows = list(fx.rows)
    rows[index] = replace(rows[index], **changes)
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=tuple(rows))


@pytest.mark.parametrize(
    "changes",
    (
        {"all_finite": False},
        {"tangent_identity_matches": False},
        {"adjoint_identity_matches": False},
        {"graph_connected": False},
        {"observed_rank": 1, "observed_shape": (4,)},
        {"observed_dtype": BFLOAT16},
        {"output_projection": SCALAR_PROJECTION},
        {"artifact_integrity": False},
    ),
)
def test_target_and_matched_control_rows_require_all_exact_invariants(changes) -> None:
    fx = make_fixture()
    rows = (replace(fx.rows[0], **changes), *fx.rows[1:])
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=rows)


def test_dimension_rank_shape_dtype_and_vector_lengths_are_exact() -> None:
    fx = make_fixture()
    for changes in (
        {"expected_rank": 1},
        {"expected_shape": (4,)},
        {"expected_dtype": BFLOAT16},
        {"expected_vector": (1, 2, 3)},
        {"observed_vector": (1, 2, 3)},
        {"denominator_units": 999},
    ):
        rows = (replace(fx.rows[0], **changes), *fx.rows[1:])
        with pytest.raises(SchemaValidationError):
            rebuild_protocol(fx, rows=rows)


def test_integer_tolerances_and_zero_denominator_absolute_only_policy() -> None:
    fx = make_fixture()
    assert fx.protocol.rows[1].denominator_units == 0
    assert fx.protocol.payload["zero_denominator_policy"] == (
        "ABSOLUTE_ONLY_ZERO_DENOMINATOR"
    )
    with pytest.raises(SchemaValidationError, match="at least one"):
        rebuild_protocol(
            fx, absolute_tolerance_units=0, relative_tolerance_ppm=0
        )
    excessive = good_row(
        "target-row",
        TARGET,
        expected_vector=(100, 200, -100, 50),
        observed_vector=(999, 199, -100, 51),
        denominator_units=200,
    )
    with pytest.raises(SchemaValidationError, match="exceeds explicit"):
        rebuild_protocol(fx, rows=(excessive, *fx.rows[1:]))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("component_id", "stagec-component"),
        ("component_id", "Stage-C-component"),
        ("component_id", "stage_c_component"),
    ),
)
def test_every_stage_c_component_identity_is_rejected(field: str, value: str) -> None:
    del field
    with pytest.raises(SchemaValidationError, match="Stage C"):
        build_jspace_registered_component_body(
            component_id=value,
            role=SOURCE_IDENTITY,
            dimension=4,
            rank=2,
            shape=(2, 2),
            dtype=FLOAT32,
        )


@pytest.mark.parametrize("phase", ("stagec-calibration", "C-Cal", "stage_c"))
def test_every_stage_c_phase_is_rejected(phase: str) -> None:
    fx = make_fixture()
    with pytest.raises(SchemaValidationError, match="Stage C"):
        rebuild_protocol(fx, phase=phase)


@pytest.mark.parametrize(
    "component_id",
    (
        "component-c-cal",
        "component-ccal",
        "gate5-c-calibration",
        "gate5-c_cal",
        "c-cal-component",
        "ccal-component",
    ),
)
def test_embedded_stage_c_namespace_aliases_are_rejected(component_id: str) -> None:
    with pytest.raises(SchemaValidationError, match="Stage C"):
        build_jspace_registered_component_body(
            component_id=component_id,
            role=SOURCE_IDENTITY,
            dimension=4,
            rank=2,
            shape=(2, 2),
            dtype=FLOAT32,
        )


@pytest.mark.parametrize(
    "counter",
    (
        "canary_count",
        "import_calls",
        "torch_calls",
        "autograd_calls",
        "model_calls",
        "provider_calls",
        "network_calls",
        "filesystem_calls",
        "dose_executions",
    ),
)
def test_boundary_bool_never_aliases_integer_zero(counter: str) -> None:
    fx = make_fixture()
    payload = json.loads(fx.protocol.raw_bytes)
    payload["boundary"][counter] = False
    with pytest.raises(SchemaValidationError, match="boundary"):
        load_jspace_shadow_protocol(
            canonical_json_bytes(payload), source_bundle=fx.source_bundle
        )


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("status", "mode", "ACTIVE"),
        ("status", "intervention", "STEER"),
        ("status", "license", "LICENSED"),
        ("status", "authority", "AUTHORITY"),
        ("status", "verdict", "ACCEPT"),
        ("boundary", "execution", "EXECUTED"),
        ("boundary", "execution_authority", "GRANTED"),
    ),
)
def test_status_and_authority_promotion_fail_closed(
    section: str, field: str, value: str
) -> None:
    fx = make_fixture()
    payload = json.loads(fx.protocol.raw_bytes)
    payload[section][field] = value
    with pytest.raises(SchemaValidationError):
        load_jspace_shadow_protocol(
            canonical_json_bytes(payload), source_bundle=fx.source_bundle
        )


def test_every_artifact_projection_requires_exact_scalar_types() -> None:
    fx = make_fixture()
    forged_bundles = (
        replace(fx.source_bundle, dimension=4.0),
        replace(fx.source_bundle, rank=2.0),
        replace(fx.source_bundle, shape=(2.0, 2.0)),
        replace(fx.source_bundle, byte_length=float(fx.source_bundle.byte_length)),
    )
    for forged in forged_bundles:
        with pytest.raises(SchemaValidationError):
            replay_jspace_source_bundle_manifest(forged)

    forged_protocols = (
        replace(fx.protocol, dimension=4.0),
        replace(fx.protocol, rank=2.0),
        replace(fx.protocol, shape=(2.0, 2.0)),
        replace(fx.protocol, absolute_tolerance_units=2.0),
        replace(fx.protocol, relative_tolerance_ppm=10_000.0),
        replace(fx.protocol, dose_schedule_units=(0.0, 1, 2, 4)),
        replace(
            fx.protocol,
            rows=(
                replace(fx.protocol.rows[0], expected_rank=2.0),
                *fx.protocol.rows[1:],
            ),
        ),
    )
    for forged in forged_protocols:
        with pytest.raises(SchemaValidationError):
            replay_jspace_shadow_protocol(forged, source_bundle=fx.source_bundle)


def test_artifact_ref_is_reconstructed_with_exact_scalar_types() -> None:
    fx = make_fixture()
    original = fx.members[0].artifact_ref
    forged = ArtifactRef(
        artifact_id=original.artifact_id,
        sha256=original.sha256,
        byte_length=original.byte_length,
        media_type=original.media_type,
    )
    object.__setattr__(forged, "byte_length", float(original.byte_length))
    with pytest.raises(SchemaValidationError, match="scalar types"):
        JSpaceSourceMember(
            role=fx.members[0].role,
            artifact_ref=forged,
            body_bytes=fx.members[0].body_bytes,
        )

    mutated = copy.copy(fx.members[0])
    object.__setattr__(mutated.artifact_ref, "byte_length", float(original.byte_length))
    with pytest.raises(SchemaValidationError, match="scalar types"):
        build_jspace_source_bundle_manifest(
            bundle_id="forged-ref-bundle",
            members=(mutated, *fx.members[1:]),
        )


def test_payload_is_recursively_frozen() -> None:
    fx = make_fixture()
    assert type(fx.protocol.payload).__name__ == "mappingproxy"
    assert type(fx.protocol.payload["status"]).__name__ == "mappingproxy"
    assert type(fx.protocol.payload["boundary"]).__name__ == "mappingproxy"
    assert type(fx.protocol.payload["rows"]) is tuple
    assert type(fx.protocol.payload["rows"][0]).__name__ == "mappingproxy"
    assert type(fx.protocol.payload["rows"][0]["expected_vector"]) is tuple
    with pytest.raises(TypeError):
        fx.protocol.payload["status"]["license"] = "LICENSED"
    with pytest.raises(TypeError):
        fx.protocol.payload["boundary"]["canary_count"] = 1
    with pytest.raises(TypeError):
        fx.protocol.payload["rows"][0]["all_finite"] = False


def test_payload_is_derived_and_hostile_mapping_proxy_cannot_enter_replay() -> None:
    fx = make_fixture()
    assert "payload" not in type(fx.source_bundle).__dataclass_fields__
    assert "payload" not in type(fx.protocol).__dataclass_fields__
    calls: list[str] = []

    class HostileMapping(dict):
        def __iter__(self):
            calls.append("iter")
            raise AssertionError("hostile mapping callback ran")

        def keys(self):
            calls.append("keys")
            raise AssertionError("hostile mapping callback ran")

    hostile = MappingProxyType(HostileMapping())
    with pytest.raises(TypeError):
        replace(fx.source_bundle, payload=hostile)
    with pytest.raises(TypeError):
        replace(fx.protocol, payload=hostile)
    assert calls == []


def test_build_and_member_projection_reject_hostile_fields_before_callbacks() -> None:
    fx = make_fixture()
    role_calls: list[str] = []

    class HostileRole:
        def __eq__(self, other: object) -> bool:
            del other
            role_calls.append("eq")
            raise AssertionError("hostile role callback ran")

    forged_member = object.__new__(JSpaceSourceMember)
    object.__setattr__(forged_member, "role", HostileRole())
    object.__setattr__(forged_member, "artifact_ref", fx.members[0].artifact_ref)
    object.__setattr__(forged_member, "body_bytes", fx.members[0].body_bytes)
    hostile_members = (forged_member, *fx.members[1:])
    with pytest.raises(SchemaValidationError, match="exact string"):
        build_jspace_source_bundle_manifest(
            bundle_id="jspace-hostile-source-bundle",
            members=hostile_members,
        )
    with pytest.raises(SchemaValidationError, match="exact string"):
        replace(fx.source_bundle, members=hostile_members).member(CORRESPONDENCE_BASIS)

    forged_binding = object.__new__(JSpaceVectorBinding)
    original_binding = fx.rows[0].vector_bindings[0]
    object.__setattr__(forged_binding, "role", HostileRole())
    object.__setattr__(forged_binding, "artifact_ref", original_binding.artifact_ref)
    object.__setattr__(forged_binding, "body_bytes", original_binding.body_bytes)
    forged_row = replace(
        fx.rows[0],
        vector_bindings=(forged_binding, *fx.rows[0].vector_bindings[1:]),
    )
    with pytest.raises(SchemaValidationError, match="exact string"):
        rebuild_protocol(fx, rows=(forged_row, *fx.rows[1:]))
    assert role_calls == []

    phase_calls: list[str] = []

    class HostilePhase:
        def __eq__(self, other: object) -> bool:
            del other
            phase_calls.append("eq")
            raise AssertionError("hostile phase callback ran")

    with pytest.raises(SchemaValidationError, match="exact strings"):
        rebuild_protocol(fx, intervention=HostilePhase())
    assert phase_calls == []


def _rebind_row_vector(
    row: JSpaceShadowRow,
    role: str,
    *,
    registered_values: tuple[int, ...] | None = None,
    observed_values: tuple[int, ...] | None = None,
) -> JSpaceShadowRow:
    index = VECTOR_ROLES.index(role)
    old = row.vector_bindings[index]
    body = json.loads(old.body_bytes)
    replacement = vector_binding(
        row_id=row.row_id,
        role=role,
        registered_values=(
            tuple(body["registered_values"])
            if registered_values is None
            else registered_values
        ),
        observed_values=(
            tuple(body["observed_values"])
            if observed_values is None
            else observed_values
        ),
        dtype=body["dtype"],
    )
    bindings = list(row.vector_bindings)
    bindings[index] = replacement
    return replace(row, vector_bindings=tuple(bindings))


@pytest.mark.parametrize(
    ("role", "registered_values", "observed_values"),
    (
        (TANGENT_VECTOR, None, (99, 2, 3, 4)),
        (ADJOINT_VECTOR, None, (99, 3, 2, 1)),
        (JVP_VECTOR, (99, 200, -100, 50), None),
        (VJP_VECTOR, (99, 200, -100, 50), None),
    ),
)
def test_each_numeric_vector_body_is_checked_against_its_row(
    role: str,
    registered_values: tuple[int, ...] | None,
    observed_values: tuple[int, ...] | None,
) -> None:
    fx = make_fixture()
    row = _rebind_row_vector(
        fx.rows[0],
        role,
        registered_values=registered_values,
        observed_values=observed_values,
    )
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=(row, *fx.rows[1:]))


def test_crossed_vector_refs_bodies_roles_and_rows_fail_closed() -> None:
    fx = make_fixture()
    payload = json.loads(fx.protocol.raw_bytes)
    bindings = payload["rows"][0]["vector_bindings"]
    bindings[0]["body_hex"], bindings[1]["body_hex"] = (
        bindings[1]["body_hex"],
        bindings[0]["body_hex"],
    )
    with pytest.raises(SchemaValidationError, match="body differs"):
        load_jspace_shadow_protocol(
            canonical_json_bytes(payload), source_bundle=fx.source_bundle
        )

    payload = json.loads(fx.protocol.raw_bytes)
    bindings = payload["rows"][0]["vector_bindings"]
    bindings[0], bindings[1] = bindings[1], bindings[0]
    with pytest.raises(SchemaValidationError, match="order"):
        load_jspace_shadow_protocol(
            canonical_json_bytes(payload), source_bundle=fx.source_bundle
        )

    crossed = replace(
        fx.rows[1],
        vector_bindings=(fx.rows[0].vector_bindings[0], *fx.rows[1].vector_bindings[1:]),
    )
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=(fx.rows[0], crossed, *fx.rows[2:]))


def test_scalar_vector_and_scalar_target_control_projection_fail_closed() -> None:
    with pytest.raises(SchemaValidationError, match="tuple"):
        build_jspace_vector_body(
            vector_id="scalar-tangent-vector",
            row_id="scalar-row",
            role=TANGENT_VECTOR,
            dimension=4,
            dtype=FLOAT32,
            registered_values=1,
            observed_values=(1, 2, 3, 4),
        )
    fx = make_fixture()
    scalar_target = replace(fx.rows[0], output_projection=SCALAR_PROJECTION)
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(fx, rows=(scalar_target, *fx.rows[1:]))
    scalar_zero_control = replace(fx.rows[1], output_projection=SCALAR_PROJECTION)
    with pytest.raises(SchemaValidationError):
        rebuild_protocol(
            fx, rows=(fx.rows[0], scalar_zero_control, *fx.rows[2:])
        )


def test_replay_and_unavailable_backends_are_sealed_and_non_authoritative() -> None:
    fx = make_fixture()
    backend, request = build_replay_jspace_shadow_backend(
        source_bundle=fx.source_bundle, protocol=fx.protocol
    )
    assert backend.mode == REPLAY_ONLY
    assert backend.phase == SHADOW
    assert backend.intervention == NONE
    assert backend.canary_count == 0
    detached = replay_jspace_shadow(backend, request)
    assert detached == fx.protocol
    assert detached is not fx.protocol
    with pytest.raises(SchemaValidationError, match="already consumed"):
        replay_jspace_shadow(backend, request)

    backend, request = build_replay_jspace_shadow_backend(
        source_bundle=fx.source_bundle, protocol=fx.protocol
    )
    with pytest.raises(SchemaValidationError, match="exact sealed request object"):
        replay_jspace_shadow(backend, replace(request))
    for operation in (
        lambda: copy.copy(backend),
        lambda: copy.deepcopy(backend),
        lambda: pickle.dumps(backend),
        lambda: backend.__replace__(),
    ):
        with pytest.raises(TypeError):
            operation()

    forged = object.__new__(ReplayJSpaceShadowBackend)
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        replay_jspace_shadow(forged, request)

    unavailable = build_unavailable_jspace_shadow_backend(
        source_bundle=fx.source_bundle, reason="typed autograd backend unavailable"
    )
    assert unavailable.phase == SHADOW
    assert unavailable.intervention == NONE
    assert unavailable.canary_count == 0
    with pytest.raises(JSpaceShadowBackendUnavailableError, match="unavailable"):
        replay_jspace_shadow(unavailable, object())

    class LiveBackend:
        def replay(self, request):
            return request

    with pytest.raises(SchemaValidationError, match="not installed"):
        replay_jspace_shadow(LiveBackend(), object())


def test_replay_performs_no_external_io(monkeypatch: pytest.MonkeyPatch) -> None:
    fx = make_fixture()
    backend, request = build_replay_jspace_shadow_backend(
        source_bundle=fx.source_bundle, protocol=fx.protocol
    )
    calls: list[str] = []

    def blocked(name: str):
        def fail(*args, **kwargs):
            del args, kwargs
            calls.append(name)
            raise AssertionError(f"unexpected external call: {name}")

        return fail

    monkeypatch.setattr(builtins, "open", blocked("open"))
    monkeypatch.setattr(socket, "create_connection", blocked("socket"))
    monkeypatch.setattr(subprocess, "run", blocked("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", blocked("subprocess.Popen"))
    replay_jspace_shadow(backend, request)
    assert calls == []


def test_module_ast_has_no_live_execution_or_external_io_imports() -> None:
    source = Path(shadow_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = {
        "torch", "transformers", "requests", "urllib", "http", "socket",
        "subprocess", "pathlib", "os", "runpod",
    }
    imported: set[str] = set()
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "open", "exec", "eval", "compile", "__import__",
            }:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "connect", "create_connection", "urlopen", "request", "run", "Popen",
            }:
                forbidden_calls.append(node.func.attr)
    assert imported.isdisjoint(forbidden_imports)
    assert forbidden_calls == []


def test_vjp_and_known_fault_rows_cannot_hide_tolerance_drift() -> None:
    fx = make_fixture()
    vjp_drift = good_row(
        "target-row",
        TARGET,
        expected_vector=(100, 200, -100, 50),
        observed_vector=(101, 199, -100, 51),
        expected_vjp_vector=(100, 200, -100, 50),
        observed_vjp_vector=(999, 199, -100, 51),
        denominator_units=200,
    )
    with pytest.raises(SchemaValidationError, match="exceeds explicit"):
        rebuild_protocol(fx, rows=(vjp_drift, *fx.rows[1:]))

    fault_with_extra_drift = good_row(
        "known-fault-wrong-tangent",
        KNOWN_FAULT,
        fault_kind=WRONG_TANGENT,
        tangent_identity_matches=False,
        tangent_observed=(9, 2, 3, 4),
        observed_vector=(999, 20, 30, 40),
    )
    with pytest.raises(SchemaValidationError, match="exceeds explicit"):
        rebuild_protocol(
            fx,
            rows=(
                *fx.rows[:2],
                fault_with_extra_drift,
                *fx.rows[3:],
            ),
        )
