from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
STAGEC_VECTOR_WIDTH = 4864
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2._strict_json import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    thaw_json,
)
from cas_harness_v2._validation import (  # noqa: E402
    ArtifactRef,
    SchemaValidationError,
)
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE,
)
from cas_harness_v2.stagec_outcome import (  # noqa: E402
    STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE,
    STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_SCHEMA,
    STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
    STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA,
    STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE,
    STAGEC_WORKER_OUTPUT_MEDIA_TYPE,
    STAGEC_STUDY_REQUEST_BINDING_SCHEMA,
    StageCCaptureArchiveProjection,
    StageCPostTerminalChild,
    build_stagec_post_terminal_outcome_index,
    build_stagec_worker_output,
    load_stagec_capture_archive_projection,
    load_stagec_post_terminal_outcome_index,
    load_stagec_study_request_binding,
    load_stagec_worker_output,
)
from cas_harness_v2.study_protocol import (  # noqa: E402
    STUDY_CASE_PACKAGE_MEDIA_TYPE,
    STUDY_REQUEST_MEDIA_TYPE,
    load_study_plan,
)
from cas_harness_v2.preregistration import (  # noqa: E402
    PreregistrationChain,
    load_preregistration,
)
from cas_harness_v2.worker_protocol import (  # noqa: E402
    build_worker_terminal_receipt,
)
from test_study_protocol import (  # noqa: E402
    Fixture as ResearchFixture,
    StudyProtocolFixture,
    encode as study_encode,
    package_bytes,
)


def _ref(artifact_id: str, raw: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def _ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _canonical_mutation(raw: bytes, mutate) -> bytes:
    value = json.loads(raw)
    mutate(value)
    return canonical_json_bytes(value)


def _array_ref_value(
    artifact_id: str,
    raw: bytes,
    *,
    dtype: str,
    shape: list[int],
    role: str,
    layer_index: int | None = None,
    module_path: str | None = None,
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "byte_length": len(raw),
        "byte_order": "little",
        "dtype": dtype,
        "durability_status": "NOT_DURABLY_RETAINED",
        "format": "RAW C-ORDER ARRAY BYTES / NO HEADER / NO PICKLE",
        "layer_index": layer_index,
        "layout": "C_CONTIGUOUS",
        "media_type": "application/vnd.cas-harness.ndarray.raw",
        "module_path": module_path,
        "retention_location": "IN_MEMORY",
        "role": role,
        "sha256": sha256_bytes(raw),
        "shape": shape,
    }


def _structural_identity() -> dict[str, object]:
    return {
        "device": 1,
        "file_attributes": None,
        "inode": 1,
        "mode_type": 16384,
        "reparse_tag": None,
    }


def _file_identity(byte_length: int, inode: int) -> dict[str, object]:
    return {
        "byte_length": byte_length,
        "ctime_ns": 1_000_000_000 + inode,
        "device": 1,
        "file_attributes": None,
        "inode": inode,
        "link_count": 1,
        "mode_type": 32768,
        "mtime_ns": 1_000_000_000 + inode,
        "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
        "reparse_tag": None,
    }


class CarrierFixture:
    def __init__(self) -> None:
        self.study = StudyProtocolFixture()
        original_cases = self.study.loaded_plan.cases
        capture_request_bytes: list[bytes] = []
        capture_request_refs: list[ArtifactRef] = []
        study_request_bytes: list[bytes] = []
        study_request_refs: list[ArtifactRef] = []
        for index, case in enumerate(original_cases):
            invocation_id = f"stagec-invocation-{index + 1:03d}"
            capture_raw = canonical_json_bytes(
                {
                    "schema_version": STAGEC_CAPTURE_REQUEST_SCHEMA,
                    "study_id": self.study.study_id,
                    "case_id": case.case_id,
                    "split_id": case.split_id,
                    "base_intent_group_id": case.group_id,
                    "frozen_variant": case.variant_role,
                    "frozen_label": case.variant_role,
                    "invocation_id": invocation_id,
                    "prompt": f"Exact Stage C prompt {index + 1:03d}",
                }
            )
            capture_ref = _ref(
                f"stagec-capture-request-{index + 1:03d}",
                capture_raw,
                STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
            )
            study_raw = canonical_json_bytes(
                {
                    "schema_version": STAGEC_STUDY_REQUEST_BINDING_SCHEMA,
                    "study_request_id": f"stagec-request-{index + 1:03d}",
                    "study_id": self.study.study_id,
                    "case_id": case.case_id,
                    "split_id": case.split_id,
                    "base_intent_group_id": case.group_id,
                    "frozen_variant": case.variant_role,
                    "frozen_label": case.variant_role,
                    "invocation_id": invocation_id,
                    "stagec_capture_request": _ref_value(capture_ref),
                }
            )
            study_ref = _ref(
                f"stagec-request-{index + 1:03d}",
                study_raw,
                STUDY_REQUEST_MEDIA_TYPE,
            )
            capture_request_bytes.append(capture_raw)
            capture_request_refs.append(capture_ref)
            study_request_bytes.append(study_raw)
            study_request_refs.append(study_ref)

        plan = deepcopy(self.study.plan)
        for row, request_ref in zip(
            plan["case_inventory"], study_request_refs, strict=True
        ):
            row["request"] = _ref_value(request_ref)
        for package in plan["split_packages"]:
            package_raw = package_bytes(
                study_id=self.study.study_id,
                study_phase=plan["study_phase"],
                split_id=package["split_id"],
                role=package["role"],
                cases=plan["case_inventory"],
            )
            package["package"] = _ref_value(
                _ref(
                    package["package"]["artifact_id"],
                    package_raw,
                    STUDY_CASE_PACKAGE_MEDIA_TYPE,
                )
            )
        package_by_role = {
            package["role"]: package["package"] for package in plan["split_packages"]
        }
        research = ResearchFixture()
        preregistration = deepcopy(research.prereg)
        for split in preregistration["splits"]:
            split["minimum_groups"] = 1
            split["target_groups"] = 1
            split["target_enrolled_rows"] = 3
            split["target_analyzed_rows"] = 3
            split["maximum_missing_rows"] = 0
            split["maximum_excluded_rows"] = 0
            if split["role"] in package_by_role:
                split["source_artifact"] = deepcopy(package_by_role[split["role"]])
        base = load_preregistration(
            study_encode(preregistration),
            claim_ledger_bytes=research.claim_ledger_bytes,
        )
        chain = PreregistrationChain(base)
        plan["preregistration_binding"] = {
            "base_artifact": _ref_value(
                _ref(
                    base.preregistration_id,
                    base.raw_bytes,
                    "application/vnd.cas-harness.preregistration+json",
                )
            ),
            "pre_outcome_chain_sha256": chain.chain_sha256,
            "claim_id": base.claim_id,
            "claim_record_sha256": base.claim_record_sha256,
            "protected_design_sha256": base.protected_design_sha256,
        }
        plan["governance"] = deepcopy(json.loads(base.raw_bytes)["governance"])
        self.study.base = base
        self.study.chain = chain
        self.study.base_json = json.loads(base.raw_bytes)
        self.study.split_packages = tuple(
            ArtifactRef(**package["package"]) for package in plan["split_packages"]
        )
        self.study.plan = plan
        self.study.plan_raw = canonical_json_bytes(plan)
        self.study.loaded_plan = load_study_plan(
            self.study.plan_raw,
            chain=self.study.chain,
        )
        self.study.request_bytes = tuple(study_request_bytes)
        self.study.requests = tuple(study_request_refs)
        self.capture_request_bytes = tuple(capture_request_bytes)
        self.capture_request_refs = tuple(capture_request_refs)

    def authorization(self, index: int, *, nonce_byte: int | None = None):
        authorization, _ = self.study.child(index, nonce_byte=nonce_byte)
        return authorization

    def archive(
        self,
        index: int,
    ) -> StageCCaptureArchiveProjection:
        case = self.study.loaded_plan.cases[index]
        capture_request_ref = self.capture_request_refs[index]
        capture_request_bytes = self.capture_request_bytes[index]
        binding = load_stagec_study_request_binding(self.study.request_bytes[index])
        invocation_id = binding.payload["invocation_id"]
        authorization_projection_bytes = canonical_json_bytes(
            {
                "schema_version": "cas_harness.stagec.authorization_projection.v1",
                "scope": "STRUCTURE_ONLY",
                "authority_status": (
                    "NON_AUTHORITY / DOES_NOT_AUTHORIZE_MODEL_EXECUTION"
                ),
                "request_sha256": capture_request_ref.sha256,
                "plan_id": self.study.study_id,
                "study_id": self.study.study_id,
                "case_id": case.case_id,
                "invocation_id": invocation_id,
            }
        )
        authorization_projection_ref = _ref(
            f"stagec-auth-projection-{index + 1:03d}",
            authorization_projection_bytes,
            STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE,
        )
        input_ids = (index + 1).to_bytes(8, "little", signed=True)
        attention_mask = (index + 11).to_bytes(8, "little", signed=True)
        target_vector = bytes((index + 21, 1, 2, 3)) * STAGEC_VECTOR_WIDTH
        wrong_layer_vector = bytes((index + 31, 4, 5, 6)) * STAGEC_VECTOR_WIDTH
        input_ref = _array_ref_value(
            f"stagec-input-ids-{index + 1:03d}",
            input_ids,
            dtype="<i8",
            shape=[1, 1],
            role="input_ids",
        )
        mask_ref = _array_ref_value(
            f"stagec-attention-mask-{index + 1:03d}",
            attention_mask,
            dtype="<i8",
            shape=[1, 1],
            role="attention_mask",
        )
        target_ref = _array_ref_value(
            f"stagec-target-vector-{index + 1:03d}",
            target_vector,
            dtype="<f4",
            shape=[STAGEC_VECTOR_WIDTH],
            role="target_final_token_activation",
            layer_index=18,
            module_path="model.layers[18].mlp.down_proj",
        )
        wrong_ref = _array_ref_value(
            f"stagec-wrong-vector-{index + 1:03d}",
            wrong_layer_vector,
            dtype="<f4",
            shape=[STAGEC_VECTOR_WIDTH],
            role="wrong_layer_final_token_activation",
            layer_index=0,
            module_path="model.layers[0].mlp.down_proj",
        )
        capture_index_bytes = canonical_json_bytes(
            {
                "schema_version": "cas_harness.stagec.capture_index.v1",
                "scope": "STRUCTURE_ONLY",
                "retention": {
                    "location": "IN_MEMORY",
                    "durability_status": "NOT_DURABLY_RETAINED",
                },
                "association": {
                    "study_id": self.study.study_id,
                    "case_id": case.case_id,
                    "split_id": case.split_id,
                    "base_intent_group_id": case.group_id,
                    "frozen_variant": case.variant_role,
                    "frozen_label": case.variant_role,
                    "invocation_id": invocation_id,
                    "plan_id": self.study.study_id,
                    "request_artifact": _ref_value(capture_request_ref),
                    "authorization_projection_artifact": _ref_value(
                        authorization_projection_ref
                    ),
                },
                "identity": {},
                "prompt": {},
                "tokens": {
                    "input_ids_artifact": input_ref,
                    "attention_mask_artifact": mask_ref,
                    "sequence_length": 1,
                    "final_prompt_token_index": 0,
                    "final_prompt_token_id": 1,
                    "truncation_enabled": False,
                    "truncation_occurred": False,
                },
                "activations": {
                    "target": {
                        "array_artifact": target_ref,
                        "layer_index": 18,
                        "module_path": "model.layers[18].mlp.down_proj",
                        "source_dtype": "float32",
                        "source_device": "cpu",
                        "source_autocast_enabled": False,
                    },
                    "wrong_layer": {
                        "array_artifact": wrong_ref,
                        "layer_index": 0,
                        "module_path": "model.layers[0].mlp.down_proj",
                        "source_dtype": "float32",
                        "source_device": "cpu",
                        "source_autocast_enabled": False,
                    },
                },
                "logits": {},
                "hooks": {},
                "endpoint_checks": {},
                "telemetry": {},
            }
        )
        capture_index_ref = _ref(
            f"stagec-capture-index-{index + 1:03d}",
            capture_index_bytes,
            STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
        )
        exact_members: list[tuple[str, dict[str, object], bytes]] = [
            ("request_artifact", _ref_value(capture_request_ref), capture_request_bytes),
            (
                "authorization_projection_artifact",
                _ref_value(authorization_projection_ref),
                authorization_projection_bytes,
            ),
            ("capture_index_artifact", _ref_value(capture_index_ref), capture_index_bytes),
            ("input_ids", input_ref, input_ids),
            ("attention_mask", mask_ref, attention_mask),
            ("target_vector", target_ref, target_vector),
            ("wrong_layer_vector", wrong_ref, wrong_layer_vector),
        ]
        rows = []
        members: dict[str, bytes] = {}
        for inode, (role, reference, raw) in enumerate(exact_members, start=10):
            digest = str(reference["sha256"]).lower()
            rows.append(
                {
                    "archive_copy_status": "LOCAL_FILE_COPY_RETAINED_AND_REVALIDATED",
                    "file_identity": _file_identity(len(raw), inode),
                    "path_ancestors": [
                        {"identity": _structural_identity(), "relative_path": "."},
                        {
                            "identity": _structural_identity(),
                            "relative_path": "objects",
                        },
                        {
                            "identity": _structural_identity(),
                            "relative_path": "objects/sha256",
                        },
                        {
                            "identity": _structural_identity(),
                            "relative_path": f"objects/sha256/{digest[:2]}",
                        },
                    ],
                    "ref": reference,
                    "relative_path": f"objects/sha256/{digest[:2]}/{digest[2:]}",
                    "role": role,
                }
            )
            members[role] = raw
        manifest_bytes = canonical_json_bytes(
            {
                "schema_version": STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA,
                "authority": {
                    "scope": "LOCAL_SINGLE_HOST_FILE_BACKED",
                    "write_mode": "CREATE_ONLY",
                    "file_sync": "FILE_FSYNC_AND_REREAD_VERIFIED_AT_CREATION",
                    "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
                    "worm_authority": "NOT_ESTABLISHED",
                    "trusted_time": "NOT_ESTABLISHED",
                    "external_anchor": "NOT_ESTABLISHED",
                    "capture_provenance": "NOT_CONFERRED_BY_ARCHIVE_REPLAY",
                    "execution_authority": "NOT_GRANTED",
                    "relocatability": "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY",
                    "membership_scope": (
                        "MANIFEST_LISTED_MEMBERS_ONLY_CLOSED_WORLD_NOT_ESTABLISHED"
                    ),
                },
                "source_retention_boundary": (
                    "CAPTURE-TIME IN_MEMORY / NOT_DURABLY_RETAINED LABELS PRESERVED; "
                    "THIS MANIFEST BINDS A SEPARATE LOCAL FILE COPY"
                ),
                "relocatability_boundary": (
                    "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY"
                ),
                "manifest_membership_boundary": (
                    "MANIFEST_LISTED_MEMBERS_ONLY / "
                    "CLOSED_WORLD_DIRECTORY CONTENT NOT ESTABLISHED"
                ),
                "manifest_publication_boundary": (
                    "THE READ_ONLY REREAD-VERIFIED MANIFEST IS THE LOCAL "
                    "PUBLICATION POINT; A STOP AFTER PUBLICATION MAY LEAVE "
                    "AN INTERNALLY VALID ORPHAN"
                ),
                "member_directory_fsync_status": "PERFORMED",
                "root_path": f"C:/stagec/archive-{index + 1:03d}",
                "root_identity": _structural_identity(),
                "association": {
                    "study_id": self.study.study_id,
                    "case_id": case.case_id,
                    "split_id": case.split_id,
                    "base_intent_group_id": case.group_id,
                    "frozen_variant": case.variant_role,
                    "frozen_label": case.variant_role,
                    "invocation_id": invocation_id,
                    "plan_id": self.study.study_id,
                },
                "members": rows,
            }
        )
        manifest_ref = _ref(
            "stagec-local-archive-"
            + sha256_bytes(canonical_json_bytes(_ref_value(capture_index_ref))).lower(),
            manifest_bytes,
            STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
        )
        return load_stagec_capture_archive_projection(
            manifest_ref=manifest_ref,
            manifest_bytes=manifest_bytes,
            member_bytes=members,
        )

    def worker_output(
        self,
        index: int,
        *,
        authorization=None,
        archive: StageCCaptureArchiveProjection | None = None,
        output_id: str | None = None,
    ):
        case = self.study.loaded_plan.cases[index]
        authorization = (
            self.authorization(index) if authorization is None else authorization
        )
        archive = self.archive(index) if archive is None else archive
        output = build_stagec_worker_output(
            chain=self.study.chain,
            plan=self.study.loaded_plan,
            case_id=case.case_id,
            request_bytes=self.study.request_bytes[index],
            authorization=authorization,
            archive=archive,
            output_id=(
                f"stagec-worker-output-{index + 1:03d}"
                if output_id is None
                else output_id
            ),
        )
        return authorization, archive, output

    def terminal(
        self,
        index: int,
        *,
        authorization,
        worker_output,
        terminal_status: str = "COMPLETED",
        produced_ref: ArtifactRef | None = None,
        receipt_id: str | None = None,
    ):
        if terminal_status == "COMPLETED":
            produced_outputs = [
                {
                    "output_name": worker_output.output_name,
                    "artifact": _ref_value(
                        worker_output.artifact_ref
                        if produced_ref is None
                        else produced_ref
                    ),
                }
            ]
            missing_outputs: list[str] = []
            error = None
        else:
            produced_outputs = []
            missing_outputs = [worker_output.output_name]
            error = {
                "code": "EXECUTION_FAILED",
                "category": "EXECUTION_FAILED",
                "message": "synthetic Stage C failure",
                "retryable": False,
            }
        return build_worker_terminal_receipt(
            chain=self.study.chain,
            authorization=authorization,
            receipt_id=(
                f"stagec-terminal-{index + 1:03d}"
                if receipt_id is None
                else receipt_id
            ),
            worker_started_at=(
                "2026-08-05T08:21:00Z"
                if index == 0
                else "2026-08-05T08:32:00Z"
            ),
            terminal_at=f"2026-08-05T08:40:{index:02d}Z",
            terminal_status=terminal_status,
            produced_outputs=produced_outputs,
            missing_outputs=missing_outputs,
            error=error,
        )

    def child(
        self,
        index: int,
        *,
        authorization=None,
        archive: StageCCaptureArchiveProjection | None = None,
        terminal_status: str = "COMPLETED",
        produced_ref: ArtifactRef | None = None,
        receipt_id: str | None = None,
    ) -> StageCPostTerminalChild:
        authorization, archive, output = self.worker_output(
            index,
            authorization=authorization,
            archive=archive,
        )
        terminal = self.terminal(
            index,
            authorization=authorization,
            worker_output=output,
            terminal_status=terminal_status,
            produced_ref=produced_ref,
            receipt_id=receipt_id,
        )
        return StageCPostTerminalChild(
            case_id=self.study.loaded_plan.cases[index].case_id,
            request_bytes=self.study.request_bytes[index],
            authorization=authorization,
            archive=archive,
            worker_output=output,
            terminal_receipt=terminal,
        )

    def children(self) -> tuple[StageCPostTerminalChild, ...]:
        return tuple(self.child(index) for index in range(6))

    def outcome(self, children: tuple[StageCPostTerminalChild, ...] | None = None):
        children = self.children() if children is None else children
        return build_stagec_post_terminal_outcome_index(
            chain=self.study.chain,
            plan=self.study.loaded_plan,
            children=children,
            outcome_index_id="stagec-study-outcome-index-001",
            accessed_at="2026-08-05T08:50:00Z",
        )


def _load_coherently_swapped_archive_arrays(
    archive: StageCCaptureArchiveProjection,
    left: str,
    right: str,
) -> StageCCaptureArchiveProjection:
    manifest = json.loads(archive.manifest_bytes)
    members = dict(archive.member_bytes)
    capture_index = json.loads(members["capture_index_artifact"])
    index_slots = {
        "input_ids": ("tokens", "input_ids_artifact"),
        "attention_mask": ("tokens", "attention_mask_artifact"),
        "target_vector": ("activations", "target", "array_artifact"),
        "wrong_layer_vector": (
            "activations",
            "wrong_layer",
            "array_artifact",
        ),
    }

    rows = {row["role"]: row for row in manifest["members"]}
    for field in ("ref", "relative_path", "file_identity", "path_ancestors"):
        rows[left][field], rows[right][field] = (
            deepcopy(rows[right][field]),
            deepcopy(rows[left][field]),
        )
    members[left], members[right] = members[right], members[left]

    def slot(role: str) -> tuple[dict[str, object], str]:
        path = index_slots[role]
        owner: dict[str, object] = capture_index
        for key in path[:-1]:
            owner = owner[key]  # type: ignore[assignment]
        return owner, path[-1]

    left_owner, left_key = slot(left)
    right_owner, right_key = slot(right)
    left_owner[left_key], right_owner[right_key] = (
        deepcopy(right_owner[right_key]),
        deepcopy(left_owner[left_key]),
    )

    capture_index_bytes = canonical_json_bytes(capture_index)
    capture_index_ref = _ref(
        archive.capture_index_ref.artifact_id,
        capture_index_bytes,
        STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
    )
    members["capture_index_artifact"] = capture_index_bytes
    index_row = rows["capture_index_artifact"]
    index_row["ref"] = _ref_value(capture_index_ref)
    index_digest = capture_index_ref.sha256.lower()
    index_row["relative_path"] = (
        f"objects/sha256/{index_digest[:2]}/{index_digest[2:]}"
    )
    index_row["file_identity"]["byte_length"] = len(capture_index_bytes)
    index_row["path_ancestors"][-1]["relative_path"] = (
        f"objects/sha256/{index_digest[:2]}"
    )

    manifest_bytes = canonical_json_bytes(manifest)
    manifest_ref = _ref(
        "stagec-local-archive-"
        + sha256_bytes(canonical_json_bytes(_ref_value(capture_index_ref))).lower(),
        manifest_bytes,
        STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
    )
    return load_stagec_capture_archive_projection(
        manifest_ref=manifest_ref,
        manifest_bytes=manifest_bytes,
        member_bytes=members,
    )


def test_archive_projection_is_loader_only_and_keeps_request_media_distinct() -> None:
    fx = CarrierFixture()
    archive = fx.archive(0)
    binding = load_stagec_study_request_binding(fx.study.request_bytes[0])

    assert archive.manifest_ref.verify_bytes(archive.manifest_bytes)
    assert archive.capture_request_ref.verify_bytes(archive.capture_request_bytes)
    assert archive.capture_index_ref.verify_bytes(archive.capture_index_bytes)
    assert archive.authorization_projection_ref.verify_bytes(
        archive.authorization_projection_bytes
    )
    assert binding.artifact_ref.media_type == STUDY_REQUEST_MEDIA_TYPE
    assert archive.capture_request_ref.media_type == STAGEC_CAPTURE_REQUEST_MEDIA_TYPE
    assert binding.artifact_ref.media_type != archive.capture_request_ref.media_type
    assert binding.capture_request_ref == archive.capture_request_ref
    with pytest.raises(SchemaValidationError, match="strict seven-member replay"):
        replace(archive, manifest_bytes=b"forged archive bytes")
    with pytest.raises(SchemaValidationError, match="strict seven-member replay"):
        StageCCaptureArchiveProjection()


def test_study_request_binding_rejects_capture_request_id_collision() -> None:
    fx = CarrierFixture()
    capture_request_id = fx.capture_request_refs[0].artifact_id
    raw = _canonical_mutation(
        fx.study.request_bytes[0],
        lambda value: value.__setitem__("study_request_id", capture_request_id),
    )
    with pytest.raises(SchemaValidationError, match="artifact IDs must be distinct"):
        load_stagec_study_request_binding(raw)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("input_ids", "attention_mask"),
        ("input_ids", "target_vector"),
        ("input_ids", "wrong_layer_vector"),
        ("attention_mask", "target_vector"),
        ("attention_mask", "wrong_layer_vector"),
        ("target_vector", "wrong_layer_vector"),
    ],
)
def test_archive_projection_rejects_every_coherent_array_role_swap(
    left: str,
    right: str,
) -> None:
    archive = CarrierFixture().archive(0)
    with pytest.raises(SchemaValidationError, match="Stage C slot"):
        _load_coherently_swapped_archive_arrays(archive, left, right)


def test_worker_output_exactly_binds_all_predecessors_without_forward_refs() -> None:
    fx = CarrierFixture()
    authorization, archive, output = fx.worker_output(0)
    payload = thaw_json(output.payload)

    assert output.artifact_ref.media_type == STAGEC_WORKER_OUTPUT_MEDIA_TYPE
    assert output.plan_case_ordinal == 1
    assert payload["association"]["plan_case_ordinal"] == 1
    assert payload["association"]["execution_ordinal"] == "NOT_ATTESTED"
    assert payload["study_binding"]["study_plan"] == _ref_value(
        fx.study.loaded_plan.artifact_ref
    )
    assert payload["study_request"] == _ref_value(fx.study.requests[0])
    assert payload["stagec_capture_request"] == _ref_value(
        fx.capture_request_refs[0]
    )
    assert payload["worker_authorization"] == _ref_value(
        authorization.artifact_ref
    )
    assert payload["archive_manifest"] == _ref_value(archive.manifest_ref)
    assert payload["capture_index"] == _ref_value(archive.capture_index_ref)
    assert "terminal_receipt" not in payload
    assert "outcome_index" not in payload
    assert payload["boundary"]["state_scope"] == "PROCESS_LOCAL_ONLY"
    assert payload["boundary"]["forward_references"] == "FORBIDDEN"
    assert payload["authority"]["scope"] == "STRUCTURE_ONLY"

    replayed = load_stagec_worker_output(
        output.raw_bytes,
        chain=fx.study.chain,
        plan=fx.study.loaded_plan,
        case_id=fx.study.loaded_plan.cases[0].case_id,
        request_bytes=fx.study.request_bytes[0],
        authorization=authorization,
        archive=archive,
    )
    assert replayed.raw_bytes == output.raw_bytes
    assert replayed.artifact_ref == output.artifact_ref


def test_worker_loader_rejects_noncanonical_duplicate_and_extra_fields() -> None:
    fx = CarrierFixture()
    authorization, archive, output = fx.worker_output(0)
    kwargs = {
        "chain": fx.study.chain,
        "plan": fx.study.loaded_plan,
        "case_id": fx.study.loaded_plan.cases[0].case_id,
        "request_bytes": fx.study.request_bytes[0],
        "authorization": authorization,
        "archive": archive,
    }
    pretty = json.dumps(json.loads(output.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_stagec_worker_output(pretty, **kwargs)

    duplicate = output.raw_bytes.replace(
        b'{"archive_manifest":',
        b'{"output_id":"duplicate","archive_manifest":',
        1,
    )
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_stagec_worker_output(duplicate, **kwargs)

    extra = _canonical_mutation(
        output.raw_bytes,
        lambda value: value.__setitem__("terminal_receipt", {}),
    )
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_stagec_worker_output(extra, **kwargs)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["association"].__setitem__("execution_ordinal", 2),
        lambda value: value["study_request"].__setitem__("byte_length", 1),
        lambda value: value["authority"].__setitem__("scope", "AUTHORITATIVE"),
        lambda value: value["boundary"].__setitem__(
            "state_scope", "DURABLE_GLOBAL"
        ),
    ],
)
def test_worker_loader_rejects_binding_and_authority_drift(mutation) -> None:
    fx = CarrierFixture()
    authorization, archive, output = fx.worker_output(0)
    raw = _canonical_mutation(output.raw_bytes, mutation)
    with pytest.raises(SchemaValidationError, match="does not exactly replay"):
        load_stagec_worker_output(
            raw,
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=fx.study.loaded_plan.cases[0].case_id,
            request_bytes=fx.study.request_bytes[0],
            authorization=authorization,
            archive=archive,
        )


def test_worker_builder_rejects_wrong_case_archive_request_auth_and_id_collision() -> None:
    fx = CarrierFixture()
    case = fx.study.loaded_plan.cases[0]
    authorization = fx.authorization(0)
    archive = fx.archive(0)

    with pytest.raises(SchemaValidationError, match="case_id"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id="unknown-case",
            request_bytes=fx.study.request_bytes[0],
            authorization=authorization,
            archive=archive,
            output_id="stagec-output-unknown",
        )
    with pytest.raises(SchemaValidationError, match="request bytes"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=case.case_id,
            request_bytes=b"forged request bytes",
            authorization=authorization,
            archive=archive,
            output_id="stagec-output-forged-request",
        )
    with pytest.raises(SchemaValidationError, match="execution_mapping.job_id"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=case.case_id,
            request_bytes=fx.study.request_bytes[0],
            authorization=fx.authorization(1),
            archive=archive,
            output_id="stagec-output-wrong-auth",
        )
    relabeled_archive = fx.archive(1)
    for field, value in {
        "case_id": case.case_id,
        "split_id": case.split_id,
        "base_intent_group_id": case.group_id,
        "frozen_variant": case.variant_role,
        "frozen_label": case.variant_role,
        "invocation_id": "stagec-invocation-001",
        "capture_request_ref": fx.capture_request_refs[0],
        "capture_request_bytes": fx.capture_request_bytes[0],
    }.items():
        object.__setattr__(relabeled_archive, field, value)
    with pytest.raises(SchemaValidationError, match="strict seven-member replay"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=case.case_id,
            request_bytes=fx.study.request_bytes[0],
            authorization=authorization,
            archive=relabeled_archive,
            output_id="stagec-output-wrong-archive",
        )
    with pytest.raises(SchemaValidationError, match="collides"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=case.case_id,
            request_bytes=fx.study.request_bytes[0],
            authorization=authorization,
            archive=archive,
            output_id=archive.manifest_ref.artifact_id,
        )


def test_outcome_index_binds_every_case_and_replays_after_aggregate_seal() -> None:
    fx = CarrierFixture()
    children = fx.children()
    outcome = fx.outcome(children)
    payload = thaw_json(outcome.payload)

    assert (
        STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE
        != DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE
    )
    assert outcome.outcome_access_receipt_ref == outcome.artifact_ref
    assert fx.study.chain.outcome_access is None
    assert outcome.execution_completed_at == "2026-08-05T08:40:05Z"
    assert len(payload["ordered_case_outcomes"]) == 6
    assert [row["plan_case_ordinal"] for row in payload["ordered_case_outcomes"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert {
        row["execution_ordinal"] for row in payload["ordered_case_outcomes"]
    } == {"NOT_ATTESTED"}
    assert {row["retry_count"] for row in payload["ordered_case_outcomes"]} == {
        "NOT_ATTESTED"
    }
    assert {
        row["terminal_disposition"] for row in payload["ordered_case_outcomes"]
    } == {"COMPLETED"}
    for child, row in zip(children, payload["ordered_case_outcomes"], strict=True):
        assert row["study_request"] == _ref_value(
            fx.study.loaded_plan.cases[row["plan_case_ordinal"] - 1].request
        )
        assert row["stagec_capture_request"] == _ref_value(
            child.archive.capture_request_ref
        )
        assert row["worker_authorization"] == _ref_value(
            child.authorization.artifact_ref
        )
        assert row["archive_manifest"] == _ref_value(child.archive.manifest_ref)
        assert row["capture_index"] == _ref_value(child.archive.capture_index_ref)
        assert row["worker_output"] == _ref_value(child.worker_output.artifact_ref)
        assert row["terminal_receipt"] == _ref_value(
            child.terminal_receipt.artifact_ref
        )
    assert outcome.sha256.encode("ascii") not in outcome.raw_bytes
    assert payload["boundary"]["references"] == "PREDECESSORS_ONLY"
    assert payload["boundary"]["self_reference"] == "FORBIDDEN"
    assert payload["boundary"]["state_scope"] == "PROCESS_LOCAL_ONLY"

    fx.study.chain.record_outcome_access(
        accessed_at=outcome.accessed_at,
        execution_completed_at=outcome.execution_completed_at,
        receipt=outcome.outcome_access_receipt_ref,
    )
    replayed = load_stagec_post_terminal_outcome_index(
        outcome.raw_bytes,
        chain=fx.study.chain,
        plan=fx.study.loaded_plan,
        children=children,
    )
    assert replayed.artifact_ref == outcome.artifact_ref
    assert replayed.raw_bytes == outcome.raw_bytes


def test_outcome_requires_exact_fixed_cardinality_and_order() -> None:
    fx = CarrierFixture()
    children = fx.children()
    with pytest.raises(SchemaValidationError, match="every fixed Study case"):
        fx.outcome(children[:-1])
    with pytest.raises(SchemaValidationError, match="fixed case-inventory order"):
        fx.outcome((children[1], children[0], *children[2:]))
    with pytest.raises(SchemaValidationError, match="every fixed Study case"):
        fx.outcome((*children, children[-1]))


def test_outcome_rejects_failed_receipt_and_wrong_terminal_output_ref() -> None:
    fx = CarrierFixture()
    children = list(fx.children())
    children[0] = fx.child(0, terminal_status="FAILED")
    with pytest.raises(SchemaValidationError, match="only exact COMPLETED"):
        fx.outcome(tuple(children))

    children = list(fx.children())
    wrong_bytes = b"not the Stage C worker output envelope\n"
    wrong_ref = _ref(
        "wrong-terminal-output-001",
        wrong_bytes,
        "application/octet-stream",
    )
    children[0] = fx.child(0, produced_ref=wrong_ref)
    with pytest.raises(SchemaValidationError, match="must bind only the exact"):
        fx.outcome(tuple(children))


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            lambda value: value["ordered_case_outcomes"][0].__setitem__(
                "retry_count", 1
            ),
            "does not exactly replay",
        ),
        (
            lambda value: value["ordered_case_outcomes"][0].__setitem__(
                "execution_ordinal", 0
            ),
            "does not exactly replay",
        ),
        (
            lambda value: value["ordered_case_outcomes"][0].__setitem__(
                "terminal_disposition", "FAILED"
            ),
            "does not exactly replay",
        ),
        (
            lambda value: value["boundary"].__setitem__(
                "state_scope", "DURABLE_GLOBAL"
            ),
            "does not exactly replay",
        ),
        (
            lambda value: value.__setitem__("self_artifact_ref", {}),
            "forbidden extra",
        ),
    ],
)
def test_outcome_loader_rejects_retry_ordinal_disposition_boundary_and_self_ref(
    mutation,
    match: str,
) -> None:
    fx = CarrierFixture()
    children = fx.children()
    outcome = fx.outcome(children)
    raw = _canonical_mutation(outcome.raw_bytes, mutation)
    with pytest.raises(SchemaValidationError, match=match):
        load_stagec_post_terminal_outcome_index(
            raw,
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            children=children,
        )


def test_outcome_loader_requires_canonical_exact_bytes() -> None:
    fx = CarrierFixture()
    children = fx.children()
    outcome = fx.outcome(children)
    pretty = json.dumps(json.loads(outcome.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_stagec_post_terminal_outcome_index(
            pretty,
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            children=children,
        )


def test_outcome_requires_access_strictly_after_latest_terminal() -> None:
    fx = CarrierFixture()
    children = fx.children()
    with pytest.raises(SchemaValidationError, match="strictly after"):
        build_stagec_post_terminal_outcome_index(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            children=children,
            outcome_index_id="stagec-study-outcome-index-001",
            accessed_at="2026-08-05T08:40:05Z",
        )


def test_outcome_rejects_cross_case_nonce_replay() -> None:
    fx = CarrierFixture()
    children = list(fx.children())
    replayed_nonce_authorization = fx.authorization(1, nonce_byte=1)
    children[1] = fx.child(1, authorization=replayed_nonce_authorization)
    with pytest.raises(SchemaValidationError, match="run_nonce.*duplicate"):
        fx.outcome(tuple(children))


def test_outcome_does_not_invent_zero_retries_when_an_attempt_is_not_supplied() -> None:
    fx = CarrierFixture()
    first_attempt = fx.child(
        0,
        authorization=fx.authorization(0, nonce_byte=20),
        receipt_id="stagec-terminal-attempt-one-001",
    )
    selected_attempt = fx.child(
        0,
        authorization=fx.authorization(0, nonce_byte=21),
        receipt_id="stagec-terminal-attempt-two-001",
    )
    assert first_attempt.authorization.artifact_ref != selected_attempt.authorization.artifact_ref
    assert (
        first_attempt.terminal_receipt.artifact_ref
        != selected_attempt.terminal_receipt.artifact_ref
    )

    outcome = fx.outcome((selected_attempt, *fx.children()[1:]))
    row = thaw_json(outcome.payload)["ordered_case_outcomes"][0]
    assert row["retry_count"] == "NOT_ATTESTED"
    assert row["execution_ordinal"] == "NOT_ATTESTED"
    assert first_attempt.authorization.artifact_ref not in outcome.artifact_refs
    assert first_attempt.terminal_receipt.artifact_ref not in outcome.artifact_refs


def test_sealed_chain_must_backlink_the_exact_outcome_index_ref_and_times() -> None:
    fx = CarrierFixture()
    children = fx.children()
    outcome = fx.outcome(children)
    wrong_bytes = b"different aggregate Study outcome index\n"
    wrong_ref = _ref(
        "different-stagec-outcome-index",
        wrong_bytes,
        STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE,
    )
    fx.study.chain.record_outcome_access(
        accessed_at=outcome.accessed_at,
        execution_completed_at=outcome.execution_completed_at,
        receipt=wrong_ref,
    )
    with pytest.raises(SchemaValidationError, match="does not bind this exact"):
        load_stagec_post_terminal_outcome_index(
            outcome.raw_bytes,
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            children=children,
        )


def test_builders_fail_closed_after_outcome_access_finalization() -> None:
    fx = CarrierFixture()
    children = fx.children()
    outcome = fx.outcome(children)
    fx.study.chain.record_outcome_access(
        accessed_at=outcome.accessed_at,
        execution_completed_at=outcome.execution_completed_at,
        receipt=outcome.outcome_access_receipt_ref,
    )
    with pytest.raises(SchemaValidationError, match="cannot be built after"):
        build_stagec_post_terminal_outcome_index(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            children=children,
            outcome_index_id="stagec-study-outcome-index-002",
            accessed_at="2026-08-05T09:00:00Z",
        )
    with pytest.raises(SchemaValidationError, match="cannot be built after"):
        build_stagec_worker_output(
            chain=fx.study.chain,
            plan=fx.study.loaded_plan,
            case_id=children[0].case_id,
            request_bytes=children[0].request_bytes,
            authorization=children[0].authorization,
            archive=children[0].archive,
            output_id="stagec-worker-output-after-seal",
        )
