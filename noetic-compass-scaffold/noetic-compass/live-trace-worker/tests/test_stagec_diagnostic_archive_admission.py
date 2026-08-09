"""Fake-only tests for the worker-local diagnostic Stage C archive admission.

No test in this module loads real model files, calls a provider, executes an
HTTP route, builds a container, invokes RunPod, generates text, steers a model,
or promotes a scientific/product claim.
"""

from __future__ import annotations

import ast
import base64
from dataclasses import FrozenInstanceError
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types
from typing import Any

import pytest

from app.runtime import model_loader
from app.runtime import stagec_diagnostic_archive_admission as admission_module
from app.runtime.stagec_archive import (
    STAGEC_ARCHIVE_MEMBER_ROLES,
    STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
    STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
    STAGEC_LOCAL_ARCHIVE_SCHEMA,
    load_stagec_capture_archive,
    retain_stagec_capture,
)
from app.runtime.stagec_capture import ArtifactIdentity
from app.runtime.stagec_diagnostic_archive_admission import (
    AUTHORIZATION_AUTHORITY,
    AUTHORIZATION_BOUNDARY,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_DOMAIN,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
    DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
    DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
    DiagnosticStageCArchiveAdmissionArtifact,
    DiagnosticStageCArchiveAdmissionError,
    GOVERNANCE,
    HTTP_DOCKER_INTEGRATION_STATUS,
    LOCAL_LIVE_ADMISSION_BOUNDARY,
    SERIALIZED_ADMISSION_BOUNDARY,
    StageCLocalArchiveAdmission,
    admit_diagnostic_stagec_archive,
    load_diagnostic_stagec_archive_admission,
    replay_stagec_local_archive_admission,
)
from tests.test_stagec_capture import _FakeTokenizer, _capture, _loaded


_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


@pytest.fixture(autouse=True)
def _select_qwen_and_make_archive_cleanup_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    yield
    for path in sorted(tmp_path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            if path.is_symlink():
                continue
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        except OSError:
            pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest().upper()


def _ref(artifact_id: str, media_type: str) -> dict[str, Any]:
    raw = f"body-for-{artifact_id}".encode("ascii")
    return {
        "artifact_id": artifact_id,
        "sha256": _digest(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


def _authorization_ref(payload: dict[str, Any]) -> tuple[ArtifactIdentity, bytes]:
    raw = _canonical_bytes(payload)
    return (
        ArtifactIdentity(
            artifact_id=payload["authorization_id"],
            sha256=_digest(raw),
            byte_length=len(raw),
            media_type=DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
        ),
        raw,
    )


def _rehash_context(payload: dict[str, Any]) -> None:
    raw = _canonical_bytes(payload["execution_context"])
    payload["execution_context_sha256"] = _digest(raw)
    payload["execution_context_byte_length"] = len(raw)


def _authorization_payload(receipt, loaded) -> dict[str, Any]:
    association = loaded.index.association
    nonce = bytes(range(32))
    nonce_b64 = base64.urlsafe_b64encode(nonce).decode("ascii").rstrip("=")
    plan_ref = _ref(
        association["plan_id"], admission_module.DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE
    )
    context = {
        "diagnostic_preregistration_binding": {
            "base_artifact": _ref(
                "diagnostic-preregistration-base-001",
                "application/vnd.cas-harness.diagnostic-preregistration+json",
            ),
            "pre_outcome_chain_sha256": "1" * 64,
            "protected_design_sha256": "2" * 64,
            "study_phase": "DIAGNOSTIC_CALIBRATION",
            "claim_ceiling": "DIAGNOSTIC_ONLY",
            "ordered_amendments": [
                _ref(
                    "diagnostic-window-amendment-001",
                    "application/vnd.cas-harness.diagnostic-amendment+json",
                )
            ],
        },
        "study_binding": {
            "diagnostic_study_plan": plan_ref,
            "diagnostic_study_request": _ref(
                "diagnostic-study-request-001",
                admission_module.DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
            ),
            "stagec_capture_request": loaded.request_artifact.ref.to_payload(),
        },
        "case_binding": {
            "study_id": association["study_id"],
            "case_id": association["case_id"],
            "case_execution_ordinal": 1,
            "split_id": association["split_id"],
            "base_intent_group_id": association["base_intent_group_id"],
            "frozen_variant": association["frozen_variant"],
            "frozen_label": association["frozen_label"],
            "invocation_id": association["invocation_id"],
        },
        "execution_contract": _ref(
            "diagnostic-execution-contract-001",
            admission_module.DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE,
        ),
        "execution_identity_artifacts": [
            _ref(
                "diagnostic-execution-identity-001",
                "application/vnd.cas-harness.execution-identity+json",
            )
        ],
        "model_runtime_capture_contract": {
            "model_contract": dict(admission_module._STAGEC_MODEL_CONTRACT),
            "runtime_contract": dict(admission_module._RUNTIME_CONTRACT),
            "capture_contract": dict(admission_module._STAGEC_CAPTURE_CONTRACT),
        },
        "attempt_binding": {
            "attempt_subject_sha256": "3" * 64,
            "run_nonce": {
                "value_b64url": nonce_b64,
                "sha256": _digest(nonce),
                "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
                "structural_assurance": "LENGTH_ENCODING_AND_DIGEST_ONLY",
            },
            "retry_policy": dict(admission_module._RETRY_POLICY),
        },
        "worker_assignment": {
            "assigned_worker_id": "diagnostic-worker-001",
            "assignment_semantic": "PROSPECTIVE_STRUCTURAL_BINDING_ONLY",
        },
        "execution_window": {
            "amendment": _ref(
                "diagnostic-window-amendment-001",
                "application/vnd.cas-harness.diagnostic-amendment+json",
            ),
            "window_start": "2030-01-01T00:00:00Z",
            "window_end": "2030-01-02T00:00:00Z",
            "semantic": "DECLARED_UTC_TIMESTAMP_WINDOW_ONLY",
            "trust": "NOT_TRUSTED",
        },
        "artifact_expectations": {
            "authorization": {
                "artifact_id": "diagnostic-worker-authorization-001",
                "schema_version": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
                "media_type": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            },
            "capture": {
                "authorization_projection": (
                    loaded.authorization_projection_artifact.ref.to_payload()
                ),
                "capture_index": {
                    "artifact_id": loaded.index_artifact.ref.artifact_id,
                    "schema_version": "cas_harness.stagec.capture_index.v1",
                    "media_type": loaded.index_artifact.ref.media_type,
                },
                "raw_arrays": {
                    "input_ids": {
                        "artifact_id": loaded.input_ids.ref.artifact_id,
                        "dtype": "<i8",
                        "role": "input_ids",
                    },
                    "attention_mask": {
                        "artifact_id": loaded.attention_mask.ref.artifact_id,
                        "dtype": "<i8",
                        "role": "attention_mask",
                    },
                    "target_vector": {
                        "artifact_id": loaded.target_vector.ref.artifact_id,
                        "dtype": "<f4",
                        "role": "target_final_token_activation",
                        "layer_index": 18,
                        "module_path": "model.layers[18].mlp.down_proj",
                    },
                    "wrong_layer_vector": {
                        "artifact_id": loaded.wrong_layer_vector.ref.artifact_id,
                        "dtype": "<f4",
                        "role": "wrong_layer_final_token_activation",
                        "layer_index": 0,
                        "module_path": "model.layers[0].mlp.down_proj",
                    },
                },
            },
            "archive": {
                "schema_version": STAGEC_LOCAL_ARCHIVE_SCHEMA,
                "media_type": STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
                "manifest_name": STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
                "manifest_id_derivation": admission_module.ARCHIVE_MANIFEST_ID_DERIVATION,
                "content_path_derivation": admission_module.ARCHIVE_CONTENT_PATH_DERIVATION,
                "absolute_root": receipt.root.as_posix(),
                "ordered_member_roles": list(STAGEC_ARCHIVE_MEMBER_ROLES),
                "expected_member_artifact_ids": {
                    "request_artifact": loaded.request_artifact.ref.artifact_id,
                    "authorization_projection_artifact": (
                        loaded.authorization_projection_artifact.ref.artifact_id
                    ),
                    "capture_index_artifact": loaded.index_artifact.ref.artifact_id,
                    "input_ids": loaded.input_ids.ref.artifact_id,
                    "attention_mask": loaded.attention_mask.ref.artifact_id,
                    "target_vector": loaded.target_vector.ref.artifact_id,
                    "wrong_layer_vector": loaded.wrong_layer_vector.ref.artifact_id,
                },
                "admission": {
                    "artifact_id": "diagnostic-archive-admission-001",
                    "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
                    "media_type": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
                    "admission_domain": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_DOMAIN,
                },
            },
            "output": {
                "artifact_id": "diagnostic-child-output-001",
                "output_name": "diagnostic_stagec_child_output",
                "schema_version": admission_module.DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
                "media_type": admission_module.DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
            },
            "terminal_receipt": {
                "artifact_id": "diagnostic-terminal-receipt-001",
                "schema_version": (
                    admission_module.DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA
                ),
                "media_type": (
                    admission_module.DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE
                ),
            },
        },
    }
    context_bytes = _canonical_bytes(context)
    return {
        "schema_version": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
        "authorization_id": "diagnostic-worker-authorization-001",
        "issued_at": "2029-12-31T23:00:00Z",
        "not_before": "2030-01-01T00:00:00Z",
        "expires_at": "2030-01-01T12:00:00Z",
        "child_execution_binding": _ref(
            "diagnostic-child-binding-001",
            admission_module.DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE,
        ),
        "execution_context": context,
        "execution_context_sha256": _digest(context_bytes),
        "execution_context_byte_length": len(context_bytes),
        "boundary": dict(AUTHORIZATION_BOUNDARY),
        "authority": dict(AUTHORIZATION_AUTHORITY),
        "governance": dict(GOVERNANCE),
    }


def _archive_bundle(tmp_path: Path, *, identical_arrays: bool = False):
    result = (
        _capture(loaded=_loaded(tokenizer=_FakeTokenizer(mode="identical_one_token")))
        if identical_arrays
        else _capture()
    )
    root = tmp_path / "diagnostic-stagec-archive"
    receipt = retain_stagec_capture(result, root)
    loaded = load_stagec_capture_archive(
        root, expected_manifest_ref=receipt.manifest_ref
    )
    payload = _authorization_payload(receipt, loaded)
    authorization_ref, authorization_bytes = _authorization_ref(payload)
    return result, receipt, loaded, payload, authorization_ref, authorization_bytes


def test_factory_freshly_replays_seven_members_and_mints_canonical_non_authority(
    tmp_path: Path,
) -> None:
    _, receipt, loaded, _, authorization_ref, authorization_bytes = _archive_bundle(
        tmp_path
    )
    live = admit_diagnostic_stagec_archive(
        archive_receipt=receipt,
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )

    assert type(live) is StageCLocalArchiveAdmission
    assert type(live.artifact) is DiagnosticStageCArchiveAdmissionArtifact
    assert live.archive.manifest_artifact.ref == receipt.manifest_ref
    assert tuple(live.archive.member_paths) == STAGEC_ARCHIVE_MEMBER_ROLES
    assert live.artifact.payload["authority"] == AUTHORIZATION_AUTHORITY
    assert live.artifact.payload["boundary"] == SERIALIZED_ADMISSION_BOUNDARY
    assert live.boundary == LOCAL_LIVE_ADMISSION_BOUNDARY
    assert live.boundary["http_integration"] == HTTP_DOCKER_INTEGRATION_STATUS
    assert live.boundary["docker_integration"] == HTTP_DOCKER_INTEGRATION_STATUS
    assert live.boundary["execution_authority"] == "NOT_GRANTED"
    assert live.boundary["case_execution_ordinal"] == (
        "AUTHORIZATION_DECLARED_RANGE_BOUND_NOT_ARCHIVE_DERIVED"
    )
    assert live.boundary["controller_replay"] == (
        "CANONICAL_CONTROLLER_CHAIN_REPLAY_STILL_REQUIRED"
    )
    assert live.artifact.payload["case_binding"]["case_execution_ordinal"] == 1
    assert replay_stagec_local_archive_admission(live).index.to_payload() == (
        loaded.index.to_payload()
    )

    serialized = load_diagnostic_stagec_archive_admission(
        live.artifact.raw_bytes,
        expected_artifact_ref=live.artifact.ref,
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    assert serialized == live.artifact
    with pytest.raises(DiagnosticStageCArchiveAdmissionError, match="exact StageCLocal"):
        replay_stagec_local_archive_admission(serialized)  # type: ignore[arg-type]


def test_serialized_and_live_carriers_cannot_be_directly_constructed_or_forged(
    tmp_path: Path,
) -> None:
    _, receipt, _, _, authorization_ref, authorization_bytes = _archive_bundle(tmp_path)
    live = admit_diagnostic_stagec_archive(
        archive_receipt=receipt,
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    with pytest.raises(DiagnosticStageCArchiveAdmissionError, match="strict loader"):
        DiagnosticStageCArchiveAdmissionArtifact()
    with pytest.raises(DiagnosticStageCArchiveAdmissionError, match="factory"):
        StageCLocalArchiveAdmission()
    with pytest.raises(FrozenInstanceError):
        live.authorization_bytes = b"drift"  # type: ignore[misc]

    forged = object.__new__(StageCLocalArchiveAdmission)
    for name in (
        "archive_receipt",
        "archive",
        "artifact",
        "authorization_ref",
        "authorization_bytes",
        "boundary",
    ):
        object.__setattr__(forged, name, getattr(live, name))
    with pytest.raises(DiagnosticStageCArchiveAdmissionError, match="not factory-created"):
        replay_stagec_local_archive_admission(forged)


@pytest.mark.parametrize("defect", ["root", "case", "plan", "member_id"])
def test_authorization_to_archive_mismatches_fail_closed(
    tmp_path: Path,
    defect: str,
) -> None:
    _, receipt, _, payload, _, _ = _archive_bundle(tmp_path)
    context = payload["execution_context"]
    if defect == "root":
        context["artifact_expectations"]["archive"]["absolute_root"] = (
            tmp_path / "different-absolute-root"
        ).as_posix()
    elif defect == "case":
        context["case_binding"]["case_id"] = "different-case-id"
    elif defect == "plan":
        context["study_binding"]["diagnostic_study_plan"]["artifact_id"] = (
            "different-plan-id"
        )
    else:
        context["artifact_expectations"]["capture"]["raw_arrays"]["target_vector"][
            "artifact_id"
        ] = "different-target-vector-id"
        context["artifact_expectations"]["archive"]["expected_member_artifact_ids"][
            "target_vector"
        ] = "different-target-vector-id"
    _rehash_context(payload)
    authorization_ref, authorization_bytes = _authorization_ref(payload)
    with pytest.raises(DiagnosticStageCArchiveAdmissionError):
        admit_diagnostic_stagec_archive(
            archive_receipt=receipt,
            authorization_ref=authorization_ref,
            authorization_bytes=authorization_bytes,
        )


@pytest.mark.parametrize(
    "collision",
    [
        "admission_base",
        "output_base",
        "contract_binding",
        "study_request_plan",
        "admission_manifest",
    ],
)
def test_complete_identifier_collision_closure_rejects_cross_family_reuse(
    tmp_path: Path,
    collision: str,
) -> None:
    _, receipt, _, payload, _, _ = _archive_bundle(tmp_path)
    context = payload["execution_context"]
    base_id = context["diagnostic_preregistration_binding"]["base_artifact"][
        "artifact_id"
    ]
    if collision == "admission_base":
        context["artifact_expectations"]["archive"]["admission"][
            "artifact_id"
        ] = base_id
    elif collision == "output_base":
        context["artifact_expectations"]["output"]["artifact_id"] = base_id
    elif collision == "contract_binding":
        context["execution_contract"]["artifact_id"] = payload[
            "child_execution_binding"
        ]["artifact_id"]
    elif collision == "study_request_plan":
        context["study_binding"]["diagnostic_study_request"]["artifact_id"] = (
            context["study_binding"]["diagnostic_study_plan"]["artifact_id"]
        )
    else:
        context["artifact_expectations"]["archive"]["admission"][
            "artifact_id"
        ] = receipt.manifest_ref.artifact_id
    _rehash_context(payload)
    authorization_ref, authorization_bytes = _authorization_ref(payload)
    with pytest.raises(
        DiagnosticStageCArchiveAdmissionError,
        match="reuse one artifact ID|manifest ID collides",
    ):
        admit_diagnostic_stagec_archive(
            archive_receipt=receipt,
            authorization_ref=authorization_ref,
            authorization_bytes=authorization_bytes,
        )


def test_windows_archive_root_must_use_canonical_forward_slashes(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("Windows lexical-root regression")
    _, receipt, _, payload, _, _ = _archive_bundle(tmp_path)
    canonical_root = payload["execution_context"]["artifact_expectations"][
        "archive"
    ]["absolute_root"]
    assert canonical_root == receipt.root.as_posix()
    assert "\\" not in canonical_root

    payload["execution_context"]["artifact_expectations"]["archive"][
        "absolute_root"
    ] = str(receipt.root)
    assert "\\" in str(receipt.root)
    _rehash_context(payload)
    authorization_ref, authorization_bytes = _authorization_ref(payload)
    with pytest.raises(
        DiagnosticStageCArchiveAdmissionError, match="normalized absolute path"
    ):
        admit_diagnostic_stagec_archive(
            archive_receipt=receipt,
            authorization_ref=authorization_ref,
            authorization_bytes=authorization_bytes,
        )


def test_declared_case_execution_ordinal_is_range_bound_not_archive_derived(
    tmp_path: Path,
) -> None:
    _, receipt, _, payload, _, _ = _archive_bundle(tmp_path)
    payload["execution_context"]["case_binding"]["case_execution_ordinal"] = 0
    _rehash_context(payload)
    authorization_ref, authorization_bytes = _authorization_ref(payload)
    with pytest.raises(DiagnosticStageCArchiveAdmissionError, match="bounded integer"):
        admit_diagnostic_stagec_archive(
            archive_receipt=receipt,
            authorization_ref=authorization_ref,
            authorization_bytes=authorization_bytes,
        )


def test_noncanonical_extra_duplicate_and_ref_drift_authorizations_fail_closed(
    tmp_path: Path,
) -> None:
    _, receipt, _, payload, authorization_ref, authorization_bytes = _archive_bundle(
        tmp_path
    )
    variants: list[tuple[ArtifactIdentity, bytes]] = []

    extra = json.loads(authorization_bytes)
    extra["extra"] = "forbidden"
    variants.append(_authorization_ref(extra))

    noncanonical = authorization_bytes + b"\n"
    variants.append(
        (
            ArtifactIdentity(
                artifact_id=payload["authorization_id"],
                sha256=_digest(noncanonical),
                byte_length=len(noncanonical),
                media_type=DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            ),
            noncanonical,
        )
    )

    duplicate = b'{"schema_version":"a","schema_version":"b"}'
    variants.append(
        (
            ArtifactIdentity(
                artifact_id=payload["authorization_id"],
                sha256=_digest(duplicate),
                byte_length=len(duplicate),
                media_type=DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            ),
            duplicate,
        )
    )
    variants.append((authorization_ref, authorization_bytes[:-1] + b"X"))

    for candidate_ref, candidate_bytes in variants:
        with pytest.raises(DiagnosticStageCArchiveAdmissionError):
            admit_diagnostic_stagec_archive(
                archive_receipt=receipt,
                authorization_ref=candidate_ref,
                authorization_bytes=candidate_bytes,
            )


def test_factory_requires_a_fresh_unchanged_local_archive_replay(tmp_path: Path) -> None:
    _, receipt, loaded, _, authorization_ref, authorization_bytes = _archive_bundle(
        tmp_path
    )
    member_path = loaded.member_paths["target_vector"]
    original = member_path.read_bytes()
    os.chmod(member_path, 0o600)
    member_path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    os.chmod(member_path, 0o444)

    with pytest.raises(
        DiagnosticStageCArchiveAdmissionError, match="fresh worker-local"
    ):
        admit_diagnostic_stagec_archive(
            archive_receipt=receipt,
            authorization_ref=authorization_ref,
            authorization_bytes=authorization_bytes,
        )


def test_equal_content_sha_is_allowed_for_distinct_unique_array_roles_and_ids(
    tmp_path: Path,
) -> None:
    result, receipt, _, _, authorization_ref, authorization_bytes = _archive_bundle(
        tmp_path, identical_arrays=True
    )
    assert result.input_ids.ref.sha256 == result.attention_mask.ref.sha256
    assert result.input_ids.ref.artifact_id != result.attention_mask.ref.artifact_id
    assert result.input_ids.ref.role != result.attention_mask.ref.role

    live = admit_diagnostic_stagec_archive(
        archive_receipt=receipt,
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    assert live.archive.input_ids.ref.sha256 == live.archive.attention_mask.ref.sha256


def test_worker_module_has_app_only_import_closure() -> None:
    source_path = Path(admission_module.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert not any(name == "cas_harness_v2" or name.startswith("cas_harness_v2.") for name in imported)

    worker_root = source_path.parents[2]
    script = (
        "import sys;"
        f"sys.path.insert(0, {str(worker_root)!r});"
        "import app.runtime.stagec_diagnostic_archive_admission;"
        "assert not any(n == 'cas_harness_v2' or n.startswith('cas_harness_v2.') "
        "for n in sys.modules)"
    )
    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-P", "-B", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=clean_environment,
    )
    assert completed.returncode == 0, completed.stderr


def test_duplicated_literals_and_serialized_document_match_canonical_protocol(
    tmp_path: Path,
) -> None:
    package_name = "_canonical_cas_harness_v2_probe"
    canonical_src = Path(__file__).resolve().parents[4] / "src" / "cas_harness_v2"
    package = types.ModuleType(package_name)
    package.__path__ = [str(canonical_src)]  # type: ignore[attr-defined]
    package.__package__ = package_name
    sys.modules[package_name] = package
    canonical = importlib.import_module(
        f"{package_name}.diagnostic_execution_protocol"
    )

    assert canonical.DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA == (
        DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA
    )
    assert canonical.DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE == (
        DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE
    )
    assert canonical.DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA == (
        DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA
    )
    assert canonical.DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE == (
        DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE
    )
    assert canonical._AUTHORITY == dict(AUTHORIZATION_AUTHORITY)
    assert canonical._AUTHORIZATION_BOUNDARY == dict(AUTHORIZATION_BOUNDARY)
    assert canonical._ARCHIVE_ADMISSION_DOCUMENT_BOUNDARY == dict(
        SERIALIZED_ADMISSION_BOUNDARY
    )
    assert canonical._RETRY_POLICY == admission_module._RETRY_POLICY
    assert canonical._STAGEC_MODEL == admission_module._STAGEC_MODEL_CONTRACT
    assert canonical._STAGEC_CAPTURE == admission_module._STAGEC_CAPTURE_CONTRACT
    assert canonical._ARCHIVE_MEMBER_ROLES == STAGEC_ARCHIVE_MEMBER_ROLES

    _, receipt, _, payload, authorization_ref, authorization_bytes = _archive_bundle(
        tmp_path
    )
    live = admit_diagnostic_stagec_archive(
        archive_receipt=receipt,
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    nonce = payload["execution_context"]["attempt_binding"]["run_nonce"][
        "value_b64url"
    ]
    canonical_authorization = canonical.DiagnosticWorkerAuthorizationV2Artifact(
        raw_bytes=authorization_bytes,
        sha256=authorization_ref.sha256,
        byte_length=authorization_ref.byte_length,
        authorization_id=authorization_ref.artifact_id,
        issued_at=payload["issued_at"],
        not_before=payload["not_before"],
        expires_at=payload["expires_at"],
        study_id=payload["execution_context"]["case_binding"]["study_id"],
        case_id=payload["execution_context"]["case_binding"]["case_id"],
        case_execution_ordinal=1,
        attempt_ordinal=1,
        run_nonce_b64url=nonce,
        execution_context_sha256=payload["execution_context_sha256"],
        execution_context_byte_length=payload["execution_context_byte_length"],
        payload=payload,
        artifact_refs=(),
    )
    canonical_admission_ref = canonical.ArtifactRef(
        artifact_id=live.artifact.ref.artifact_id,
        sha256=live.artifact.ref.sha256,
        byte_length=live.artifact.ref.byte_length,
        media_type=live.artifact.ref.media_type,
    )
    dependent = canonical._validate_produced_documents(
        (("archive_admission", canonical_admission_ref, live.artifact.raw_bytes),),
        authorization=canonical_authorization,
    )
    assert len(dependent) == 1
    assert dependent[0].artifact_id == receipt.manifest_ref.artifact_id
