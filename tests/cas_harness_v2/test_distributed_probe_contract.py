from __future__ import annotations

import ast
from collections.abc import Mapping
import copy
from dataclasses import dataclass, replace
import gc
import json
from pathlib import Path
import pickle
from types import MappingProxyType

import pytest

import cas_harness_v2.distributed_probe_contract as distributed_module
from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.distributed_probe_contract import (
    COMPLETED,
    COORDINATOR,
    DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE,
    DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE,
    DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
    DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
    EXPERT_PARALLEL,
    FRAGMENT_OBJECT_VERSION,
    INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE,
    INDEPENDENT_RECONSTRUCTOR,
    NO_FULL_COPY_PROOF_MEDIA_TYPE,
    NON_AUTHORITY,
    PIPELINE_PARALLEL,
    RANK_FAILED,
    RANK_OOM,
    REPLAY_ONLY,
    STRUCTURE_ONLY,
    TENSOR_PARALLEL,
    TOPOLOGY_TYPES,
    UNMEASURED,
    WORKER,
    DistributedProbeBackendUnavailableError,
    DistributedProbeReplayRequest,
    DistributedRankOutcome,
    DistributedRankSpec,
    FragmentSlot,
    ParameterRange,
    ReplayDistributedProbeBackend,
    UnavailableDistributedProbeBackend,
    build_distributed_probe_fragment,
    build_distributed_probe_plan,
    build_distributed_runtime_identity_body,
    build_independent_reconstruction_evidence_body,
    build_independent_reconstruction_receipt,
    build_no_full_copy_proof_body,
    build_replay_distributed_probe_backend,
    build_unavailable_distributed_probe_backend,
    load_distributed_probe_fragment,
    load_distributed_probe_plan,
    load_independent_reconstruction_receipt,
    replay_distributed_probe_fragment,
    replay_distributed_probe_plan,
    replay_distributed_reconstruction,
    replay_independent_reconstruction_receipt,
)
from test_universal_probe_contract import DENSE_DECODER, make_bundle


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


DEFAULT_RANGES = (
    (ParameterRange(0, 100),),
    (ParameterRange(100, 200),),
    (ParameterRange(200, 300),),
)


@dataclass(frozen=True)
class DistributedBundle:
    universal: object
    topology_type: str
    rank_specs: tuple[DistributedRankSpec, ...]
    coordinator_runtime_bytes: bytes
    plan: object
    fragments: tuple[object, ...]
    outcomes: tuple[DistributedRankOutcome, ...]
    output_ref: ArtifactRef
    output_bytes: bytes
    independent_runtime_ref: ArtifactRef
    independent_runtime_bytes: bytes
    evidence_ref: ArtifactRef
    evidence_bytes: bytes
    receipt: object


def make_rank_specs(
    universal: object,
    topology_type: str,
    ranges_by_rank: tuple[tuple[ParameterRange, ...], ...] = DEFAULT_RANGES,
    *,
    shared_shard_bytes: bool = False,
    shared_exact_shard_ref: bool = False,
) -> tuple[DistributedRankSpec, ...]:
    world_size = 3
    result = []
    exact_shared_bytes = b"one-exact-shard-object"
    exact_shared_ref = ref(
        "model-shard-shared-exact",
        exact_shared_bytes,
        DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE,
    )
    for rank, ranges in enumerate(ranges_by_rank):
        if shared_exact_shard_ref:
            shard_bytes = exact_shared_bytes
            shard_ref = exact_shared_ref
        else:
            shard_bytes = (
                b"shared-shard-bytes"
                if shared_shard_bytes
                else f"exact-model-shard-rank-{rank}".encode()
            )
            shard_ref = ref(
                f"model-shard-{rank}",
                shard_bytes,
                DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE,
            )
        proof_bytes = build_no_full_copy_proof_body(
            proof_id=f"no-full-copy-proof-{rank}",
            identity=universal.identity,
            configuration_ref=universal.configuration_ref,
            topology_id="fixture-topology",
            topology_type=topology_type,
            world_size=world_size,
            rank=rank,
            total_parameter_units=300,
            parameter_ranges=ranges,
            model_shard_ref=shard_ref,
        )
        proof_ref = ref(
            f"no-full-copy-proof-{rank}",
            proof_bytes,
            NO_FULL_COPY_PROOF_MEDIA_TYPE,
        )
        runtime_bytes = build_distributed_runtime_identity_body(
            runtime_id=f"worker-runtime-{rank}",
            role=WORKER,
            rank=rank,
            implementation="fixture-distributed-runtime",
            version="fixture-runtime-v1",
            identity=universal.identity,
            configuration_ref=universal.configuration_ref,
            topology_id="fixture-topology",
            topology_type=topology_type,
            world_size=world_size,
        )
        runtime_ref = ref(
            f"worker-runtime-{rank}",
            runtime_bytes,
            DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
        )
        owned_sites = tuple(
            site.site_id
            for site in universal.manifest.sites
            if site.owning_rank == rank
        )
        result.append(
            DistributedRankSpec(
                rank=rank,
                parameter_ranges=ranges,
                owned_site_ids=owned_sites,
                model_shard_ref=shard_ref,
                model_shard_bytes=shard_bytes,
                no_full_copy_proof_ref=proof_ref,
                no_full_copy_proof_bytes=proof_bytes,
                worker_runtime_ref=runtime_ref,
                worker_runtime_bytes=runtime_bytes,
            )
        )
    return tuple(result)


def make_distributed_bundle(
    topology_type: str = TENSOR_PARALLEL,
) -> DistributedBundle:
    universal = make_bundle(DENSE_DECODER)
    rank_specs = make_rank_specs(universal, topology_type)
    coordinator_runtime_bytes = build_distributed_runtime_identity_body(
        runtime_id="coordinator-runtime",
        role=COORDINATOR,
        rank=None,
        implementation="fixture-distributed-runtime",
        version="fixture-runtime-v1",
        identity=universal.identity,
        configuration_ref=universal.configuration_ref,
        topology_id="fixture-topology",
        topology_type=topology_type,
        world_size=3,
    )
    coordinator_runtime_ref = ref(
        "coordinator-runtime",
        coordinator_runtime_bytes,
        DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
    )
    plan = build_distributed_probe_plan(
        plan_id=f"distributed-plan-{topology_type.lower()}",
        identity=universal.identity,
        capabilities=universal.capabilities,
        discovery=universal.discovery,
        manifest=universal.manifest,
        canary_plan=universal.plan,
        topology_id="fixture-topology",
        topology_type=topology_type,
        total_parameter_units=300,
        world_size=3,
        coordinator_runtime_ref=coordinator_runtime_ref,
        coordinator_runtime_bytes=coordinator_runtime_bytes,
        rank_specs=rank_specs,
        case_ids=("case-001", "case-002"),
    )
    fragments = []
    for slot in plan.fragment_slots:
        content_bytes = (
            f"fragment:{slot.merge_ordinal}:{slot.rank}:{slot.site_id}:{slot.case_id}|"
        ).encode()
        content_ref = ref(
            f"fragment-content-{slot.merge_ordinal:03d}",
            content_bytes,
            DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE,
        )
        fragments.append(
            build_distributed_probe_fragment(
                fragment_id=f"fragment-{slot.merge_ordinal:03d}",
                object_version=FRAGMENT_OBJECT_VERSION,
                plan=plan,
                identity=universal.identity,
                capabilities=universal.capabilities,
                discovery=universal.discovery,
                manifest=universal.manifest,
                canary_plan=universal.plan,
                merge_ordinal=slot.merge_ordinal,
                checkpoint_ordinal=slot.checkpoint_ordinal,
                rank=slot.rank,
                site_id=slot.site_id,
                case_id=slot.case_id,
                attempt_number=1,
                content_ref=content_ref,
                content_bytes=content_bytes,
            )
        )
    fragments = tuple(fragments)
    outcomes = tuple(
        DistributedRankOutcome(
            rank=rank,
            status=COMPLETED,
            attempt_number=1,
            resumed=False,
            replaced=False,
            final_checkpoint_ordinal=max(
                slot.checkpoint_ordinal
                for slot in plan.fragment_slots
                if slot.rank == rank
            ),
        )
        for rank in range(plan.world_size)
    )
    output_bytes = b"".join(fragment.content_bytes for fragment in fragments)
    output_ref = ref(
        "reconstructed-output",
        output_bytes,
        DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
    )
    independent_runtime_bytes = build_distributed_runtime_identity_body(
        runtime_id="independent-runtime",
        role=INDEPENDENT_RECONSTRUCTOR,
        rank=None,
        implementation="fixture-independent-reconstructor",
        version="fixture-reconstructor-v1",
        identity=universal.identity,
        configuration_ref=universal.configuration_ref,
        topology_id="fixture-topology",
        topology_type=topology_type,
        world_size=3,
    )
    independent_runtime_ref = ref(
        "independent-runtime",
        independent_runtime_bytes,
        DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
    )
    evidence_bytes = build_independent_reconstruction_evidence_body(
        evidence_id="independent-evidence",
        receipt_id="independent-receipt",
        identity=universal.identity,
        configuration_ref=universal.configuration_ref,
        plan_ref=plan.artifact_ref,
        fragment_refs=tuple(item.artifact_ref for item in fragments),
        reconstructed_output_ref=output_ref,
        independent_runtime_ref=independent_runtime_ref,
    )
    evidence_ref = ref(
        "independent-evidence",
        evidence_bytes,
        INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE,
    )
    receipt = build_independent_reconstruction_receipt(
        receipt_id="independent-receipt",
        identity=universal.identity,
        capabilities=universal.capabilities,
        discovery=universal.discovery,
        manifest=universal.manifest,
        canary_plan=universal.plan,
        plan=plan,
        fragments=fragments,
        rank_outcomes=outcomes,
        reconstructed_output_ref=output_ref,
        reconstructed_output_bytes=output_bytes,
        independent_runtime_ref=independent_runtime_ref,
        independent_runtime_bytes=independent_runtime_bytes,
        independent_evidence_ref=evidence_ref,
        independent_evidence_bytes=evidence_bytes,
    )
    return DistributedBundle(
        universal=universal,
        topology_type=topology_type,
        rank_specs=rank_specs,
        coordinator_runtime_bytes=coordinator_runtime_bytes,
        plan=plan,
        fragments=fragments,
        outcomes=outcomes,
        output_ref=output_ref,
        output_bytes=output_bytes,
        independent_runtime_ref=independent_runtime_ref,
        independent_runtime_bytes=independent_runtime_bytes,
        evidence_ref=evidence_ref,
        evidence_bytes=evidence_bytes,
        receipt=receipt,
    )


def rebuild_receipt(
    bundle: DistributedBundle,
    *,
    fragments=None,
    outcomes=None,
    output_ref=None,
    output_bytes=None,
):
    return build_independent_reconstruction_receipt(
        receipt_id="independent-receipt",
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
        plan=bundle.plan,
        fragments=bundle.fragments if fragments is None else fragments,
        rank_outcomes=bundle.outcomes if outcomes is None else outcomes,
        reconstructed_output_ref=bundle.output_ref if output_ref is None else output_ref,
        reconstructed_output_bytes=(
            bundle.output_bytes if output_bytes is None else output_bytes
        ),
        independent_runtime_ref=bundle.independent_runtime_ref,
        independent_runtime_bytes=bundle.independent_runtime_bytes,
        independent_evidence_ref=bundle.evidence_ref,
        independent_evidence_bytes=bundle.evidence_bytes,
    )


@pytest.mark.parametrize("topology_type", TOPOLOGY_TYPES)
def test_all_topology_types_bind_exact_ownership_and_zero_call_status(
    topology_type: str,
) -> None:
    bundle = make_distributed_bundle(topology_type)
    assert bundle.plan.topology_type == topology_type
    assert bundle.plan.world_size == 3
    assert bundle.plan.total_parameter_units == 300
    assert bundle.receipt.capability_state == UNMEASURED
    assert bundle.receipt.reconstructed_output_bytes == b"".join(
        item.content_bytes for item in bundle.fragments
    )
    for rank in bundle.rank_specs:
        assert sum(item.width for item in rank.parameter_ranges) < 300
        assert rank.model_shard_ref.verify_bytes(rank.model_shard_bytes)
    for artifact in (bundle.plan, *bundle.fragments, bundle.receipt):
        assert artifact.payload["status"] == {
            "scope": STRUCTURE_ONLY,
            "authority": NON_AUTHORITY,
            "license": "NOT_LICENSED",
            "capability": UNMEASURED,
        }
        assert all(
            artifact.payload["boundary"][field] == 0
            for field in (
                "distributed_framework_calls",
                "model_calls",
                "provider_calls",
                "network_calls",
                "filesystem_calls",
                "gpu_calls",
                "spend_microusd",
                "executed_attempts",
            )
        )


def test_plan_fragments_and_reconstruction_round_trip_exactly() -> None:
    bundle = make_distributed_bundle()
    kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )
    assert load_distributed_probe_plan(
        bundle.plan.raw_bytes,
        **kwargs,
        coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
        rank_specs=bundle.rank_specs,
    ) == bundle.plan
    assert replay_distributed_probe_plan(bundle.plan, **kwargs) == bundle.plan
    for fragment in bundle.fragments:
        assert load_distributed_probe_fragment(
            fragment.raw_bytes,
            plan=bundle.plan,
            **kwargs,
            content_bytes=fragment.content_bytes,
        ) == fragment
        assert replay_distributed_probe_fragment(
            fragment, plan=bundle.plan, **kwargs
        ) == fragment
    assert load_independent_reconstruction_receipt(
        bundle.receipt.raw_bytes,
        **kwargs,
        plan=bundle.plan,
        fragments=bundle.fragments,
        rank_outcomes=bundle.outcomes,
        reconstructed_output_bytes=bundle.output_bytes,
        independent_runtime_bytes=bundle.independent_runtime_bytes,
        independent_evidence_bytes=bundle.evidence_bytes,
    ) == bundle.receipt
    assert replay_independent_reconstruction_receipt(
        bundle.receipt,
        **kwargs,
        plan=bundle.plan,
        fragments=bundle.fragments,
    ) == bundle.receipt


def test_status_and_zero_call_boundary_constants_are_immutable() -> None:
    with pytest.raises(TypeError):
        distributed_module._STATUS["license"] = "LICENSED"
    with pytest.raises(TypeError):
        distributed_module._BOUNDARY["model_calls"] = 1
    with pytest.raises(TypeError):
        distributed_module._BOUNDARY["spend_microusd"] = 1


def test_status_and_boundary_global_rebinding_cannot_change_sealed_defaults(
    monkeypatch,
) -> None:
    status_backing = gc.get_referents(distributed_module._STATUS)[0]
    boundary_backing = gc.get_referents(distributed_module._BOUNDARY)[0]
    assert type(status_backing) is dict
    assert type(boundary_backing) is dict
    monkeypatch.setitem(status_backing, "license", "LICENSED")
    monkeypatch.setitem(status_backing, "authority", "GRANTED")
    monkeypatch.setitem(boundary_backing, "execution", "EXECUTED")
    monkeypatch.setitem(boundary_backing, "model_calls", 7)
    monkeypatch.setitem(boundary_backing, "spend_microusd", 123456)
    monkeypatch.setitem(boundary_backing, "execution_authority", "GRANTED")
    monkeypatch.setitem(boundary_backing, "authorization", "GRANTED")
    monkeypatch.setattr(
        distributed_module,
        "_STATUS",
        {
            "scope": "CURRENT_AUTHORITY",
            "authority": "GRANTED",
            "license": "LICENSED",
            "capability": "MEASURED",
        },
    )
    monkeypatch.setattr(
        distributed_module,
        "_BOUNDARY",
        {
            "execution": "EXECUTED",
            "distributed_framework_calls": 9,
            "model_calls": 7,
            "provider_calls": 6,
            "network_calls": 5,
            "filesystem_calls": 4,
            "gpu_calls": 3,
            "spend_microusd": 123456,
            "executed_attempts": 2,
            "execution_authority": "GRANTED",
        },
    )
    monkeypatch.setattr(distributed_module, "_ZERO_BOUNDARY_FIELDS", ())

    bundle = make_distributed_bundle()
    for artifact in (bundle.plan, *bundle.fragments, bundle.receipt):
        assert artifact.payload["status"] == {
            "scope": STRUCTURE_ONLY,
            "authority": NON_AUTHORITY,
            "license": "NOT_LICENSED",
            "capability": UNMEASURED,
        }
        assert artifact.payload["boundary"]["model_calls"] == 0
        assert artifact.payload["boundary"]["spend_microusd"] == 0
        assert artifact.payload["boundary"]["execution_authority"] == "NOT_GRANTED"


def test_zero_call_boundary_rejects_boolean_substitution_for_every_integer() -> None:
    bundle = make_distributed_bundle()
    kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
        coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
        rank_specs=bundle.rank_specs,
    )
    zero_fields = (
        "distributed_framework_calls",
        "model_calls",
        "provider_calls",
        "network_calls",
        "filesystem_calls",
        "gpu_calls",
        "spend_microusd",
        "executed_attempts",
    )
    for field in zero_fields:
        payload = json.loads(bundle.plan.raw_bytes)
        payload["boundary"][field] = False
        with pytest.raises(SchemaValidationError, match="exact integer"):
            load_distributed_probe_plan(canonical_json_bytes(payload), **kwargs)

    payload = json.loads(bundle.plan.raw_bytes)
    payload["status"]["license"] = False
    with pytest.raises(SchemaValidationError, match="exact string"):
        load_distributed_probe_plan(canonical_json_bytes(payload), **kwargs)


def test_raw_nested_projection_rows_reject_boolean_integer_aliases() -> None:
    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )
    plan_cases = (
        (("ranks", 0, "rank"), False),
        (("ranks", 0, "attempt_limit"), True),
        (("ranks", 0, "parameter_ranges", 0, "start"), False),
        (("fragment_slots", 0, "rank"), False),
        (("fragment_slots", 0, "merge_ordinal"), True),
        (("fragment_slots", 0, "checkpoint_ordinal"), True),
        (("model_identity", "identity_ref", "byte_length"), False),
    )
    for path, replacement in plan_cases:
        payload = json.loads(bundle.plan.raw_bytes)
        target = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        with pytest.raises(
            SchemaValidationError,
            match="exact JSON container and scalar types",
        ):
            load_distributed_probe_plan(
                canonical_json_bytes(payload),
                **dependency_kwargs,
                coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
                rank_specs=bundle.rank_specs,
            )

    receipt_cases = (
        (("fragments", 0, "rank"), False),
        (("fragments", 0, "merge_ordinal"), True),
        (("fragments", 0, "checkpoint_ordinal"), True),
        (("fragments", 0, "attempt_number"), True),
    )
    for path, replacement in receipt_cases:
        payload = json.loads(bundle.receipt.raw_bytes)
        target = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        with pytest.raises(
            SchemaValidationError,
            match="exact JSON container and scalar types",
        ):
            load_independent_reconstruction_receipt(
                canonical_json_bytes(payload),
                **dependency_kwargs,
                plan=bundle.plan,
                fragments=bundle.fragments,
                rank_outcomes=bundle.outcomes,
                reconstructed_output_bytes=bundle.output_bytes,
                independent_runtime_bytes=bundle.independent_runtime_bytes,
                independent_evidence_bytes=bundle.evidence_bytes,
            )


def test_stage_c_namespace_is_rejected_for_every_local_identity_and_case_role() -> None:
    bundle = make_distributed_bundle()
    slot = bundle.plan.fragment_slots[0]
    content_bytes = b"stage-namespace-regression"
    content_ref = ref(
        "stage-namespace-content",
        content_bytes,
        DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE,
    )

    for token in ("stagec", "stage-c", "stage_c", "C-Cal", "c_cal"):
        operations = (
            lambda token=token: build_distributed_runtime_identity_body(
                runtime_id=token,
                role=COORDINATOR,
                rank=None,
                implementation="separate-runtime",
                version="separate-runtime-v1",
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                topology_id="separate-topology",
                topology_type=TENSOR_PARALLEL,
                world_size=3,
            ),
            lambda token=token: build_distributed_runtime_identity_body(
                runtime_id="separate-runtime",
                role=COORDINATOR,
                rank=None,
                implementation=token,
                version="separate-runtime-v1",
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                topology_id="separate-topology",
                topology_type=TENSOR_PARALLEL,
                world_size=3,
            ),
            lambda token=token: build_distributed_runtime_identity_body(
                runtime_id="separate-runtime",
                role=COORDINATOR,
                rank=None,
                implementation="separate-runtime",
                version=f"{token}-runtime-v1",
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                topology_id="separate-topology",
                topology_type=TENSOR_PARALLEL,
                world_size=3,
            ),
            lambda token=token: build_no_full_copy_proof_body(
                proof_id=token,
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                topology_id="fixture-topology",
                topology_type=TENSOR_PARALLEL,
                world_size=3,
                rank=0,
                total_parameter_units=300,
                parameter_ranges=DEFAULT_RANGES[0],
                model_shard_ref=bundle.rank_specs[0].model_shard_ref,
            ),
            lambda token=token: build_no_full_copy_proof_body(
                proof_id="separate-proof",
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                topology_id="fixture-topology",
                topology_type=TENSOR_PARALLEL,
                world_size=3,
                rank=0,
                total_parameter_units=300,
                parameter_ranges=DEFAULT_RANGES[0],
                model_shard_ref=ArtifactRef(
                    artifact_id=f"{token}-model-shard",
                    sha256=bundle.rank_specs[0].model_shard_ref.sha256,
                    byte_length=bundle.rank_specs[0].model_shard_ref.byte_length,
                    media_type=bundle.rank_specs[0].model_shard_ref.media_type,
                ),
            ),
            lambda token=token: build_distributed_probe_plan(
                plan_id=token,
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                topology_id="fixture-topology",
                topology_type=TENSOR_PARALLEL,
                total_parameter_units=300,
                world_size=3,
                coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
                coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
                rank_specs=bundle.rank_specs,
                case_ids=("separate-case",),
            ),
            lambda token=token: build_distributed_probe_plan(
                plan_id="separate-plan",
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                topology_id=token,
                topology_type=TENSOR_PARALLEL,
                total_parameter_units=300,
                world_size=3,
                coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
                coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
                rank_specs=bundle.rank_specs,
                case_ids=("separate-case",),
            ),
            lambda token=token: build_distributed_probe_plan(
                plan_id="separate-plan",
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                topology_id="fixture-topology",
                topology_type=TENSOR_PARALLEL,
                total_parameter_units=300,
                world_size=3,
                coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
                coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
                rank_specs=bundle.rank_specs,
                case_ids=(token,),
            ),
            lambda token=token: build_distributed_probe_fragment(
                fragment_id=token,
                object_version=FRAGMENT_OBJECT_VERSION,
                plan=bundle.plan,
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                merge_ordinal=slot.merge_ordinal,
                checkpoint_ordinal=slot.checkpoint_ordinal,
                rank=slot.rank,
                site_id=slot.site_id,
                case_id=slot.case_id,
                attempt_number=1,
                content_ref=content_ref,
                content_bytes=content_bytes,
            ),
            lambda token=token: build_distributed_probe_fragment(
                fragment_id="separate-fragment",
                object_version=FRAGMENT_OBJECT_VERSION,
                plan=bundle.plan,
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                merge_ordinal=slot.merge_ordinal,
                checkpoint_ordinal=slot.checkpoint_ordinal,
                rank=slot.rank,
                site_id=slot.site_id,
                case_id=slot.case_id,
                attempt_number=1,
                content_ref=ArtifactRef(
                    artifact_id=f"{token}-fragment-content",
                    sha256=content_ref.sha256,
                    byte_length=content_ref.byte_length,
                    media_type=content_ref.media_type,
                ),
                content_bytes=content_bytes,
            ),
            lambda token=token: build_distributed_probe_fragment(
                fragment_id="separate-fragment",
                object_version=f"{token}-fragment-v1",
                plan=bundle.plan,
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                merge_ordinal=slot.merge_ordinal,
                checkpoint_ordinal=slot.checkpoint_ordinal,
                rank=slot.rank,
                site_id=slot.site_id,
                case_id=slot.case_id,
                attempt_number=1,
                content_ref=content_ref,
                content_bytes=content_bytes,
            ),
            lambda token=token: FragmentSlot(
                merge_ordinal=slot.merge_ordinal,
                checkpoint_ordinal=slot.checkpoint_ordinal,
                rank=slot.rank,
                site_id=f"{token}-probe-site",
                case_id=slot.case_id,
            ),
            lambda token=token: replace(
                bundle.rank_specs[0],
                owned_site_ids=(f"{token}-probe-site",),
            ),
            lambda token=token: build_independent_reconstruction_evidence_body(
                evidence_id=token,
                receipt_id="separate-receipt",
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                plan_ref=bundle.plan.artifact_ref,
                fragment_refs=tuple(item.artifact_ref for item in bundle.fragments),
                reconstructed_output_ref=bundle.output_ref,
                independent_runtime_ref=bundle.independent_runtime_ref,
            ),
            lambda token=token: build_independent_reconstruction_evidence_body(
                evidence_id="separate-evidence",
                receipt_id=token,
                identity=bundle.universal.identity,
                configuration_ref=bundle.universal.configuration_ref,
                plan_ref=bundle.plan.artifact_ref,
                fragment_refs=tuple(item.artifact_ref for item in bundle.fragments),
                reconstructed_output_ref=bundle.output_ref,
                independent_runtime_ref=bundle.independent_runtime_ref,
            ),
            lambda token=token: build_independent_reconstruction_receipt(
                receipt_id=token,
                identity=bundle.universal.identity,
                capabilities=bundle.universal.capabilities,
                discovery=bundle.universal.discovery,
                manifest=bundle.universal.manifest,
                canary_plan=bundle.universal.plan,
                plan=bundle.plan,
                fragments=bundle.fragments,
                rank_outcomes=bundle.outcomes,
                reconstructed_output_ref=bundle.output_ref,
                reconstructed_output_bytes=bundle.output_bytes,
                independent_runtime_ref=bundle.independent_runtime_ref,
                independent_runtime_bytes=bundle.independent_runtime_bytes,
                independent_evidence_ref=bundle.evidence_ref,
                independent_evidence_bytes=bundle.evidence_bytes,
            ),
        )
        for operation in operations:
            with pytest.raises(SchemaValidationError, match="Stage C"):
                operation()

        for field in ("plan_id", "case_id"):
            payload = json.loads(bundle.plan.raw_bytes)
            if field == "plan_id":
                payload["plan_id"] = token
            else:
                payload["case_ids"][0] = token
            with pytest.raises(SchemaValidationError, match="Stage C"):
                load_distributed_probe_plan(
                    canonical_json_bytes(payload),
                    identity=bundle.universal.identity,
                    capabilities=bundle.universal.capabilities,
                    discovery=bundle.universal.discovery,
                    manifest=bundle.universal.manifest,
                    canary_plan=bundle.universal.plan,
                    coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
                    rank_specs=bundle.rank_specs,
                )


@pytest.mark.parametrize(
    ("ranges", "message"),
    (
        (
            (
                (ParameterRange(0, 120),),
                (ParameterRange(100, 200),),
                (ParameterRange(200, 300),),
            ),
            "overlap",
        ),
        (
            (
                (ParameterRange(0, 90),),
                (ParameterRange(100, 200),),
                (ParameterRange(200, 300),),
            ),
            "gap",
        ),
    ),
)
def test_global_parameter_range_overlap_and_gap_fail_closed(ranges, message) -> None:
    bundle = make_distributed_bundle()
    specs = make_rank_specs(bundle.universal, TENSOR_PARALLEL, ranges)
    with pytest.raises(SchemaValidationError, match=message):
        build_distributed_probe_plan(
            plan_id="bad-range-plan",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=specs,
            case_ids=("case-001",),
        )


def test_no_rank_can_own_a_full_model_copy() -> None:
    bundle = make_distributed_bundle()
    shard = bundle.rank_specs[0].model_shard_ref
    with pytest.raises(SchemaValidationError, match="full model copy"):
        build_no_full_copy_proof_body(
            proof_id="forbidden-full-copy",
            identity=bundle.universal.identity,
            configuration_ref=bundle.universal.configuration_ref,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            world_size=3,
            rank=0,
            total_parameter_units=300,
            parameter_ranges=(ParameterRange(0, 300),),
            model_shard_ref=shard,
        )


def test_non_owner_capture_and_stale_checkpoint_are_rejected() -> None:
    bundle = make_distributed_bundle()
    slot = bundle.plan.fragment_slots[0]
    content = b"non-owner-fragment"
    content_ref = ref(
        "non-owner-content", content, DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE
    )
    with pytest.raises(SchemaValidationError, match="non-owning rank"):
        build_distributed_probe_fragment(
            fragment_id="non-owner-fragment",
            object_version=FRAGMENT_OBJECT_VERSION,
            plan=bundle.plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            merge_ordinal=slot.merge_ordinal,
            checkpoint_ordinal=slot.checkpoint_ordinal,
            rank=1,
            site_id=slot.site_id,
            case_id=slot.case_id,
            attempt_number=1,
            content_ref=content_ref,
            content_bytes=content,
        )
    with pytest.raises(SchemaValidationError, match="checkpoint ordinal"):
        build_distributed_probe_fragment(
            fragment_id="stale-checkpoint-fragment",
            object_version=FRAGMENT_OBJECT_VERSION,
            plan=bundle.plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            merge_ordinal=slot.merge_ordinal,
            checkpoint_ordinal=slot.checkpoint_ordinal + 1,
            rank=slot.rank,
            site_id=slot.site_id,
            case_id=slot.case_id,
            attempt_number=1,
            content_ref=content_ref,
            content_bytes=content,
        )


@pytest.mark.parametrize(
    "fragments",
    (
        lambda items: items[:-1],
        lambda items: (items[0], items[0], *items[2:]),
        lambda items: (items[1], items[0], *items[2:]),
    ),
)
def test_missing_duplicate_and_out_of_order_fragments_fail_closed(fragments) -> None:
    bundle = make_distributed_bundle()
    with pytest.raises(SchemaValidationError):
        rebuild_receipt(bundle, fragments=tuple(fragments(bundle.fragments)))


def test_fragment_slots_require_distinct_content_references_and_identities() -> None:
    bundle = make_distributed_bundle()
    shared_bytes = b"same-content-cannot-fill-distinct-slots"
    shared_ref = ref(
        "one-shared-fragment-content",
        shared_bytes,
        DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE,
    )

    for reuse_exact_ref in (True, False):
        fragments = []
        for slot in bundle.plan.fragment_slots:
            content_ref = (
                shared_ref
                if reuse_exact_ref
                else ref(
                    f"aliased-fragment-content-{slot.merge_ordinal:03d}",
                    shared_bytes,
                    DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE,
                )
            )
            fragments.append(
                build_distributed_probe_fragment(
                    fragment_id=f"content-alias-fragment-{slot.merge_ordinal:03d}",
                    object_version=FRAGMENT_OBJECT_VERSION,
                    plan=bundle.plan,
                    identity=bundle.universal.identity,
                    capabilities=bundle.universal.capabilities,
                    discovery=bundle.universal.discovery,
                    manifest=bundle.universal.manifest,
                    canary_plan=bundle.universal.plan,
                    merge_ordinal=slot.merge_ordinal,
                    checkpoint_ordinal=slot.checkpoint_ordinal,
                    rank=slot.rank,
                    site_id=slot.site_id,
                    case_id=slot.case_id,
                    attempt_number=1,
                    content_ref=content_ref,
                    content_bytes=shared_bytes,
                )
            )
        with pytest.raises(
            SchemaValidationError,
            match="distinct artifact reference|content identity",
        ):
            rebuild_receipt(bundle, fragments=tuple(fragments))


def test_distinct_slot_fragments_cannot_share_one_fragment_id() -> None:
    bundle = make_distributed_bundle()
    fragments = list(bundle.fragments)
    for index in (0, 1):
        original = bundle.fragments[index]
        slot = bundle.plan.fragment_slots[index]
        fragments[index] = build_distributed_probe_fragment(
            fragment_id="one-fragment-id-for-two-slots",
            object_version=FRAGMENT_OBJECT_VERSION,
            plan=bundle.plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            merge_ordinal=slot.merge_ordinal,
            checkpoint_ordinal=slot.checkpoint_ordinal,
            rank=slot.rank,
            site_id=slot.site_id,
            case_id=slot.case_id,
            attempt_number=1,
            content_ref=original.content_ref,
            content_bytes=original.content_bytes,
        )
    with pytest.raises(SchemaValidationError, match="duplicate fragment object"):
        rebuild_receipt(bundle, fragments=tuple(fragments))


def test_fragment_content_corruption_hash_and_length_fail_closed() -> None:
    bundle = make_distributed_bundle()
    fragment = bundle.fragments[0]
    with pytest.raises(SchemaValidationError, match="hash or byte length"):
        load_distributed_probe_fragment(
            fragment.raw_bytes,
            plan=bundle.plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            content_bytes=b"corrupted",
        )
    forged = replace(fragment, content_bytes=b"corrupted")
    with pytest.raises(SchemaValidationError):
        replay_distributed_probe_fragment(
            forged,
            plan=bundle.plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
        )


@pytest.mark.parametrize(("status", "message"), ((RANK_FAILED, "failed"), (RANK_OOM, "OOM")))
def test_rank_failure_and_oom_fail_reconstruction(status: str, message: str) -> None:
    bundle = make_distributed_bundle()
    outcomes = (replace(bundle.outcomes[0], status=status), *bundle.outcomes[1:])
    with pytest.raises(SchemaValidationError, match=message):
        rebuild_receipt(bundle, outcomes=outcomes)


@pytest.mark.parametrize("field", ("resumed", "replaced"))
def test_resume_or_replacement_is_never_an_extra_attempt(field: str) -> None:
    bundle = make_distributed_bundle()
    outcomes = (
        replace(bundle.outcomes[0], **{field: True}),
        *bundle.outcomes[1:],
    )
    with pytest.raises(SchemaValidationError, match="resume cannot imply"):
        rebuild_receipt(bundle, outcomes=outcomes)


def test_stale_final_checkpoint_fails_closed() -> None:
    bundle = make_distributed_bundle()
    outcomes = (
        replace(
            bundle.outcomes[0],
            final_checkpoint_ordinal=bundle.outcomes[0].final_checkpoint_ordinal - 1,
        ),
        *bundle.outcomes[1:],
    )
    with pytest.raises(SchemaValidationError, match="final checkpoint"):
        rebuild_receipt(bundle, outcomes=outcomes)


def test_reconstruction_hash_length_and_merge_bytes_must_all_agree() -> None:
    bundle = make_distributed_bundle()
    wrong_bytes = bundle.output_bytes + b"corruption"
    wrong_ref = ref(
        "wrong-output", wrong_bytes, DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE
    )
    with pytest.raises(SchemaValidationError, match="hash or byte length"):
        rebuild_receipt(bundle, output_ref=wrong_ref, output_bytes=wrong_bytes)
    with pytest.raises(SchemaValidationError, match="hash or byte length"):
        rebuild_receipt(bundle, output_bytes=bundle.output_bytes[:-1])


def test_reconstructed_output_reference_cannot_alias_the_plan_identity() -> None:
    bundle = make_distributed_bundle()
    alias_ref = ArtifactRef(
        artifact_id=bundle.plan.plan_id,
        sha256=sha256_bytes(bundle.output_bytes),
        byte_length=len(bundle.output_bytes),
        media_type=DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
    )
    evidence_bytes = build_independent_reconstruction_evidence_body(
        evidence_id="output-alias-evidence",
        receipt_id="output-alias-receipt",
        identity=bundle.universal.identity,
        configuration_ref=bundle.universal.configuration_ref,
        plan_ref=bundle.plan.artifact_ref,
        fragment_refs=tuple(item.artifact_ref for item in bundle.fragments),
        reconstructed_output_ref=alias_ref,
        independent_runtime_ref=bundle.independent_runtime_ref,
    )
    evidence_ref = ref(
        "output-alias-evidence",
        evidence_bytes,
        INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="aliases one artifact ID"):
        build_independent_reconstruction_receipt(
            receipt_id="output-alias-receipt",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            plan=bundle.plan,
            fragments=bundle.fragments,
            rank_outcomes=bundle.outcomes,
            reconstructed_output_ref=alias_ref,
            reconstructed_output_bytes=bundle.output_bytes,
            independent_runtime_ref=bundle.independent_runtime_ref,
            independent_runtime_bytes=bundle.independent_runtime_bytes,
            independent_evidence_ref=evidence_ref,
            independent_evidence_bytes=evidence_bytes,
        )


def test_same_exact_model_shard_reference_cannot_be_reused_across_ranks() -> None:
    bundle = make_distributed_bundle()
    specs = make_rank_specs(
        bundle.universal,
        TENSOR_PARALLEL,
        shared_exact_shard_ref=True,
    )
    with pytest.raises(SchemaValidationError, match="distinct artifact reference"):
        build_distributed_probe_plan(
            plan_id="shared-exact-shard-plan",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=specs,
            case_ids=("case-001",),
        )


@pytest.mark.parametrize(
    ("ref_field", "bytes_field", "plan_id"),
    (
        (
            "no_full_copy_proof_ref",
            "no_full_copy_proof_bytes",
            "shared-proof-ref-plan",
        ),
        ("worker_runtime_ref", "worker_runtime_bytes", "shared-runtime-ref-plan"),
    ),
)
def test_rank_owned_proof_and_runtime_references_cannot_be_reused(
    ref_field: str,
    bytes_field: str,
    plan_id: str,
) -> None:
    bundle = make_distributed_bundle()
    source = bundle.rank_specs[0]
    reused = replace(
        bundle.rank_specs[1],
        **{
            ref_field: getattr(source, ref_field),
            bytes_field: getattr(source, bytes_field),
        },
    )
    specs = (bundle.rank_specs[0], reused, bundle.rank_specs[2])
    with pytest.raises(SchemaValidationError, match="distinct artifact reference"):
        build_distributed_probe_plan(
            plan_id=plan_id,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=specs,
            case_ids=("case-001",),
        )


def test_shard_corruption_alias_and_wrong_worker_runtime_fail_closed() -> None:
    bundle = make_distributed_bundle()
    with pytest.raises(SchemaValidationError, match="model_shard_bytes"):
        replace(bundle.rank_specs[0], model_shard_bytes=b"corrupted-shard")

    alias_specs = make_rank_specs(
        bundle.universal, TENSOR_PARALLEL, shared_shard_bytes=True
    )
    with pytest.raises(SchemaValidationError, match="content identity"):
        build_distributed_probe_plan(
            plan_id="aliased-shard-plan",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=alias_specs,
            case_ids=("case-001",),
        )

    wrong_runtime = replace(
        bundle.rank_specs[1],
        worker_runtime_ref=bundle.rank_specs[0].worker_runtime_ref,
        worker_runtime_bytes=bundle.rank_specs[0].worker_runtime_bytes,
    )
    with pytest.raises(SchemaValidationError, match="distinct artifact reference"):
        build_distributed_probe_plan(
            plan_id="wrong-runtime-plan",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=(bundle.rank_specs[0], wrong_runtime, bundle.rank_specs[2]),
            case_ids=("case-001",),
        )


def test_plan_retry_and_merge_order_tampering_fail_closed() -> None:
    bundle = make_distributed_bundle()
    kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
        coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
        rank_specs=bundle.rank_specs,
    )
    retry_payload = json.loads(bundle.plan.raw_bytes)
    retry_payload["retry"] = "ALLOWED"
    with pytest.raises(SchemaValidationError, match="retry"):
        load_distributed_probe_plan(canonical_json_bytes(retry_payload), **kwargs)

    order_payload = json.loads(bundle.plan.raw_bytes)
    order_payload["fragment_slots"][0], order_payload["fragment_slots"][1] = (
        order_payload["fragment_slots"][1],
        order_payload["fragment_slots"][0],
    )
    with pytest.raises(SchemaValidationError, match="merge order"):
        load_distributed_probe_plan(canonical_json_bytes(order_payload), **kwargs)


def test_artifact_mutation_replacement_and_forgery_fail_replay() -> None:
    bundle = make_distributed_bundle()
    with pytest.raises(TypeError):
        bundle.plan.payload["retry"] = "ALLOWED"
    forged_plan = replace(bundle.plan, raw_bytes=b"forged")
    with pytest.raises(SchemaValidationError):
        replay_distributed_probe_plan(
            forged_plan,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
        )
    empty_forgery = object.__new__(type(bundle.receipt))
    with pytest.raises(SchemaValidationError, match="storage projections"):
        replay_independent_reconstruction_receipt(
            empty_forgery,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            plan=bundle.plan,
            fragments=bundle.fragments,
        )


def test_replay_rejects_custom_backed_mapping_proxies_without_callbacks() -> None:
    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )

    class InertMapping(Mapping):
        def __init__(self) -> None:
            self.calls = []

        def __iter__(self):
            self.calls.append("iter")
            return iter(())

        def __len__(self):
            self.calls.append("len")
            return 0

        def __getitem__(self, key):
            self.calls.append(("getitem", key))
            raise KeyError(key)

        def __eq__(self, other):
            self.calls.append(("eq", type(other).__name__))
            return False

    cases = (
        (
            bundle.plan,
            lambda artifact: replay_distributed_probe_plan(
                artifact,
                **dependency_kwargs,
            ),
        ),
        (
            bundle.fragments[0],
            lambda artifact: replay_distributed_probe_fragment(
                artifact,
                plan=bundle.plan,
                **dependency_kwargs,
            ),
        ),
        (
            bundle.receipt,
            lambda artifact: replay_independent_reconstruction_receipt(
                artifact,
                plan=bundle.plan,
                fragments=bundle.fragments,
                **dependency_kwargs,
            ),
        ),
    )
    for artifact, replay in cases:
        backing = InertMapping()
        forged = replace(artifact, payload=MappingProxyType(backing))
        with pytest.raises(SchemaValidationError, match="exact dict-backed"):
            replay(forged)
        assert backing.calls == []


def test_replay_binds_frozen_payload_scalars_to_exact_raw_json_types() -> None:
    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )
    plan_backing = gc.get_referents(bundle.plan.payload)[0]
    plan_rank_backing = gc.get_referents(plan_backing["ranks"][0])[0]
    plan_rank_backing["rank"] = False
    with pytest.raises(
        SchemaValidationError,
        match="exact JSON container and scalar types",
    ):
        replay_distributed_probe_plan(bundle.plan, **dependency_kwargs)

    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )
    fragment_backing = gc.get_referents(bundle.fragments[0].payload)[0]
    fragment_backing["rank"] = False
    with pytest.raises(
        SchemaValidationError,
        match="exact JSON container and scalar types",
    ):
        replay_distributed_probe_fragment(
            bundle.fragments[0],
            plan=bundle.plan,
            **dependency_kwargs,
        )

    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )
    receipt_backing = gc.get_referents(bundle.receipt.payload)[0]
    receipt_fragment_backing = gc.get_referents(
        receipt_backing["fragments"][0]
    )[0]
    receipt_fragment_backing["rank"] = False
    with pytest.raises(
        SchemaValidationError,
        match="exact JSON container and scalar types",
    ):
        replay_independent_reconstruction_receipt(
            bundle.receipt,
            plan=bundle.plan,
            fragments=bundle.fragments,
            **dependency_kwargs,
        )


def test_tuple_and_dataclass_elements_fail_type_checks_before_callbacks() -> None:
    bundle = make_distributed_bundle()
    calls = []

    class InertElement:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError(f"element attribute read: {name}")

        def __eq__(self, other):
            calls.append(("eq", type(other).__name__))
            raise AssertionError("element equality called")

    with pytest.raises(SchemaValidationError, match="exact DistributedRankSpec"):
        build_distributed_probe_plan(
            plan_id="inert-rank-plan",
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=(InertElement(), *bundle.rank_specs[1:]),
            case_ids=("case-001",),
        )
    assert calls == []

    with pytest.raises(
        SchemaValidationError,
        match="exact DistributedProbeFragmentArtifact",
    ):
        rebuild_receipt(
            bundle,
            fragments=(InertElement(), *bundle.fragments[1:]),
        )
    assert calls == []

    forged_receipt = replace(
        bundle.receipt,
        rank_outcomes=(InertElement(), *bundle.outcomes[1:]),
    )
    with pytest.raises(SchemaValidationError, match="exact DistributedRankOutcome"):
        replay_independent_reconstruction_receipt(
            forged_receipt,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            plan=bundle.plan,
            fragments=bundle.fragments,
        )
    assert calls == []

    bad_outcome = copy.copy(bundle.outcomes[0])
    object.__setattr__(bad_outcome, "rank", InertElement())
    forged_receipt = replace(
        bundle.receipt,
        rank_outcomes=(bad_outcome, *bundle.outcomes[1:]),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        replay_independent_reconstruction_receipt(
            forged_receipt,
            identity=bundle.universal.identity,
            capabilities=bundle.universal.capabilities,
            discovery=bundle.universal.discovery,
            manifest=bundle.universal.manifest,
            canary_plan=bundle.universal.plan,
            plan=bundle.plan,
            fragments=bundle.fragments,
        )
    assert calls == []


def test_boolean_scalar_substitution_cannot_survive_frozen_projection_replay() -> None:
    bundle = make_distributed_bundle()
    dependency_kwargs = dict(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
    )

    bad_rank = copy.copy(bundle.rank_specs[0])
    object.__setattr__(bad_rank, "rank", False)
    with pytest.raises(SchemaValidationError, match="exact integer"):
        build_distributed_probe_plan(
            plan_id="boolean-rank-plan",
            **dependency_kwargs,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=(bad_rank, *bundle.rank_specs[1:]),
            case_ids=("case-001",),
        )

    bad_range = copy.copy(bundle.rank_specs[0].parameter_ranges[0])
    object.__setattr__(bad_range, "start", False)
    bad_range_spec = replace(
        bundle.rank_specs[0],
        parameter_ranges=(bad_range,),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        build_distributed_probe_plan(
            plan_id="boolean-range-plan",
            **dependency_kwargs,
            topology_id="fixture-topology",
            topology_type=TENSOR_PARALLEL,
            total_parameter_units=300,
            world_size=3,
            coordinator_runtime_ref=bundle.plan.coordinator_runtime_ref,
            coordinator_runtime_bytes=bundle.coordinator_runtime_bytes,
            rank_specs=(bad_range_spec, *bundle.rank_specs[1:]),
            case_ids=("case-001",),
        )

    bad_slot = copy.copy(bundle.plan.fragment_slots[0])
    object.__setattr__(bad_slot, "merge_ordinal", True)
    object.__setattr__(bad_slot, "checkpoint_ordinal", True)
    forged_plan = replace(
        bundle.plan,
        fragment_slots=(bad_slot, *bundle.plan.fragment_slots[1:]),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        replay_distributed_probe_plan(forged_plan, **dependency_kwargs)

    bad_fragment = copy.copy(bundle.fragments[0])
    object.__setattr__(bad_fragment, "merge_ordinal", True)
    with pytest.raises(SchemaValidationError, match="exact integer"):
        replay_distributed_probe_fragment(
            bad_fragment,
            plan=bundle.plan,
            **dependency_kwargs,
        )

    bad_outcome = copy.copy(bundle.outcomes[0])
    object.__setattr__(bad_outcome, "attempt_number", True)
    forged_receipt = replace(
        bundle.receipt,
        rank_outcomes=(bad_outcome, *bundle.outcomes[1:]),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        replay_independent_reconstruction_receipt(
            forged_receipt,
            plan=bundle.plan,
            fragments=bundle.fragments,
            **dependency_kwargs,
        )


def test_replay_backend_is_exact_single_use_and_detaches_receipt() -> None:
    bundle = make_distributed_bundle()
    backend, request = build_replay_distributed_probe_backend(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
        plan=bundle.plan,
        fragments=bundle.fragments,
        receipt=bundle.receipt,
    )
    assert backend.mode == REPLAY_ONLY
    assert backend.status == STRUCTURE_ONLY
    assert backend.authority == NON_AUTHORITY
    with pytest.raises(SchemaValidationError, match="exact sealed request"):
        replay_distributed_reconstruction(backend, replace(request))
    result = replay_distributed_reconstruction(backend, request)
    assert result == bundle.receipt
    assert result is not bundle.receipt
    assert backend.consumed is True
    with pytest.raises(SchemaValidationError, match="already consumed"):
        replay_distributed_reconstruction(backend, request)


@pytest.mark.parametrize(
    "operation",
    (
        lambda value: copy.copy(value),
        lambda value: copy.deepcopy(value),
        lambda value: pickle.dumps(value),
        lambda value: value.__replace__(),
    ),
)
def test_backends_reject_copy_deepcopy_pickle_and_replace(operation) -> None:
    bundle = make_distributed_bundle()
    replay_backend, _ = build_replay_distributed_probe_backend(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        discovery=bundle.universal.discovery,
        manifest=bundle.universal.manifest,
        canary_plan=bundle.universal.plan,
        plan=bundle.plan,
        fragments=bundle.fragments,
        receipt=bundle.receipt,
    )
    unavailable = build_unavailable_distributed_probe_backend(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        configuration_ref=bundle.universal.configuration_ref,
        configuration_bytes=bundle.universal.configuration_bytes,
        reason="NO_DISTRIBUTED_BACKEND",
    )
    with pytest.raises(TypeError, match="cannot be copied"):
        operation(replay_backend)
    with pytest.raises(TypeError, match="cannot be copied"):
        operation(unavailable)


def test_factory_construction_subclass_and_forgery_are_rejected() -> None:
    with pytest.raises(TypeError, match="factory-only"):
        ReplayDistributedProbeBackend()
    with pytest.raises(TypeError, match="factory-only"):
        UnavailableDistributedProbeBackend()
    with pytest.raises(TypeError, match="cannot be subclassed"):
        class ForbiddenSubclass(ReplayDistributedProbeBackend):
            pass
    replay_forgery = object.__new__(ReplayDistributedProbeBackend)
    unavailable_forgery = object.__new__(UnavailableDistributedProbeBackend)
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        _ = replay_forgery.mode
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        _ = unavailable_forgery.mode


def test_unavailable_backend_fails_before_inspecting_input() -> None:
    bundle = make_distributed_bundle()
    backend = build_unavailable_distributed_probe_backend(
        identity=bundle.universal.identity,
        capabilities=bundle.universal.capabilities,
        configuration_ref=bundle.universal.configuration_ref,
        configuration_bytes=bundle.universal.configuration_bytes,
        reason="NO_DISTRIBUTED_BACKEND",
    )

    class ExplosiveInput:
        def __getattribute__(self, name):
            raise AssertionError(f"input inspected: {name}")

    with pytest.raises(
        DistributedProbeBackendUnavailableError, match="NO_DISTRIBUTED_BACKEND"
    ):
        replay_distributed_reconstruction(backend, ExplosiveInput())


def test_arbitrary_backend_is_rejected_without_calling_it() -> None:
    class ArbitraryBackend:
        called = False

        def reconstruct(self, request):
            del request
            self.called = True
            raise AssertionError("arbitrary backend ran")

    backend = ArbitraryBackend()
    with pytest.raises(SchemaValidationError, match="not installed"):
        replay_distributed_reconstruction(backend, object())
    assert backend.called is False


def test_request_closure_rejects_content_alias() -> None:
    bundle = make_distributed_bundle()
    alias_receipt = ArtifactRef(
        artifact_id="receipt-content-alias",
        sha256=bundle.plan.artifact_ref.sha256,
        byte_length=bundle.plan.artifact_ref.byte_length,
        media_type=bundle.receipt.artifact_ref.media_type,
    )
    with pytest.raises(SchemaValidationError, match="content identity"):
        DistributedProbeReplayRequest(
            plan_ref=bundle.plan.artifact_ref,
            reconstruction_receipt_ref=alias_receipt,
        )


def test_module_has_no_live_framework_model_gpu_network_or_filesystem_imports() -> None:
    source_path = Path(distributed_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "torch", "transformers", "accelerate", "ray", "deepspeed",
            "requests", "httpx", "socket", "subprocess", "urllib", "os", "pathlib",
        }
    )
    lowered = source_path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "init_process_group(", "all_gather(", "from_pretrained(", "cuda(",
        "urlopen(", "requests.get(", "subprocess.run(", "open(",
    ):
        assert forbidden not in lowered


def test_public_exports_are_unique_and_provider_neutral() -> None:
    assert len(distributed_module.__all__) == len(set(distributed_module.__all__))
    assert all(hasattr(distributed_module, name) for name in distributed_module.__all__)
    assert not any(
        word in name.lower()
        for name in distributed_module.__all__
        for word in ("runpod", "huggingface", "openai", "torch", "deepspeed")
    )
