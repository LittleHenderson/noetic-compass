"""Run or independently verify the frozen Pythia-160m engineering canary.

The execution lane is deliberately inert until the preregistration is bound to
an immutable source commit and OCI image digest.  It loads one already-local
model snapshot, performs exactly nine captures (baseline/noop/zero, three
repetitions each), and writes a create-once evidence bundle.  The verification
lane is portable and does not load a model: it recomputes every gate from the
saved safetensors bytes and capture receipts.

This is an engineering canary only.  A PASS is always NOT_PACKET_ELIGIBLE and
NOT_SCIENTIFIC_RESULT.  Local self-hashes and the process-local capture HMACs
are not signatures or trusted timestamps; the final manifest still needs an
independent immutable external anchor.

The runtime drift checks assume a trusted, single-purpose immutable OCI/process
with no post-freeze arbitrary code.  They are not a Python sandbox or proof
against an attacker already executing inside that process.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping, Sequence

import numpy as np


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PREREGISTRATION = (
    REPOSITORY_ROOT / "docs" / "working" / "OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json"
)
DEFAULT_ADAPTER_SOURCE = (
    WORKER_ROOT.parent / "api" / "services" / "cas_harness_interpretability_adapter.py"
)
DEFAULT_DEPENDENCY_LOCK = (
    REPOSITORY_ROOT
    / "tools"
    / "runpod_open_weight_canary_v2"
    / "requirements-canary-py312-cu128.lock.txt"
)
FROZEN_SOURCE_RELATIVE_PATHS = (
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_interpretability_adapter.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/__init__.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/adapter_binding.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/artifacts.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/contracts.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/engine.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/open_weight/identity.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/capture_open_weight_trajectory_v2.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/run_open_weight_trajectory_canary_v2.py",
    "tools/runpod_open_weight_canary_v2/requirements-canary-py312-cu128.lock.txt",
    "tools/runpod_open_weight_canary_v2/github_stop_supervisor.py",
    "tools/runpod_open_weight_canary_v2/arm_github_supervisor.ps1",
    "tools/runpod_open_weight_canary_v2/watchdog_armed.ps1",
    ".github/workflows/runpod-canary-stop-supervisor.yml",
)

PREREG_SCHEMA = "cas_open_weight_trajectory_canary_preregistration.v2"
RESULT_SCHEMA = "cas_open_weight_trajectory_canary_result.v2"
ERROR_SCHEMA = "cas_open_weight_trajectory_canary_error.v2"
WATCHDOG_SCHEMA = "cas_external_stop_watchdog_receipt.v2"
GITHUB_SUPERVISOR_SCHEMA = "cas_runpod_github_stop_supervisor.v2"
PROVIDER_LAUNCH_SCHEMA = "cas_runpod_provider_launch_receipt.v1"
SCENARIO_SCHEMA = "cas_open_weight_capture_scenario.v1"
RECEIPT_SCHEMA = "cas_open_weight_trajectory_receipt.v1"
TENSOR_SCHEMA = "cas_open_weight_trajectory_tensors.v1"

PASS_STATUS = "REAL_MODEL_ENGINEERING_CANARY_PASS"
FAIL_STATUS = "REAL_MODEL_ENGINEERING_CANARY_FAIL"
PACKET_STATUS = "NOT_PACKET_ELIGIBLE"
SCIENTIFIC_STATUS = "NOT_SCIENTIFIC_RESULT"
CAPTURE_STATUS = "REAL_MODEL_FORWARD_ENGINEERING_CAPTURE_COMPLETED"
CAPTURE_SCIENTIFIC_STATUS = "NOT_A_SCIENTIFIC_EXPERIMENT_RESULT"
EXTERNAL_ANCHOR_STATUS = "EXTERNAL_IMMUTABLE_ANCHOR_REQUIRED"
BOUND_EXECUTION_AUTHORITY = "GO_FOR_ONE_ENGINEERING_CANARY_ONLY"
UNBOUND_EXECUTION_AUTHORITY = "NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN"
FROZEN_EXPERIMENT_SHA256 = (
    "B5D00239E28DCCEC3CD54AF295D2AC525D598D1B371709AA89AE94B743A0C6C8"
)

RECEIPT_CLAIM_BOUNDARY = (
    "Create-once local integrity receipt. The self-hash is not a signature "
    "or external timestamp and does not establish scientific correctness."
)
OBSERVATION_CLAIM_BOUNDARY = (
    "This receipt proves a local byte-attested engineering capture only. "
    "It does not prove a detector, causal hypothesis, safety property, "
    "external custody, independent replication, or Evidence Packet."
)
ADAPTER_BINDING_STATUS = (
    "EXACT_SOURCE_SNAPSHOT_PLAN_SCHEMA_IDENTITY_AND_HOOK_PATHS_VERIFIED"
)
ADAPTER_CLAIM_BOUNDARY = (
    "Executable hook binding only. It is not scientific validation, "
    "detector evidence, or execution authority."
)
ADAPTER_PLAN_CLAIM_BOUNDARY = (
    "STRUCTURE/MECHANICS ONLY. NOT AN EXPERIMENT, DETECTOR, CAUSAL RESULT, "
    "MODEL-SAFETY CLAIM, OR EXECUTION AUTHORITY. DECLARED MODEL IDENTITY IS NOT "
    "LOADED-MODEL BYTE ATTESTATION. ALL CAPABILITY EVIDENCE IS NOT_RUN."
)
ENGINE_RECORD_CLAIM_BOUNDARY = (
    "Engine-issued one-use local execution record. HMAC key is process-local; "
    "durable authenticity still requires an external result-manifest anchor."
)
CANARY_CLAIM_BOUNDARY = (
    "Nine-capture real-model engineering canary only. A PASS establishes the "
    "frozen capture/noop/zero mechanics for this exact bundle under a trusted "
    "single-purpose immutable OCI/process with no post-freeze arbitrary code. "
    "The drift checks are not a Python sandbox. A PASS does not establish a "
    "detector, semantic circuit, safety property, causal science claim, Evidence "
    "Packet, product licence, or production readiness."
)
ANCHOR_CLAIM_BOUNDARY = (
    "The result manifest and all evidence-file hashes are cross-linked, but "
    "they remain locally produced and are not durable authenticity evidence "
    "until an independent immutable external anchor is attached and verified."
)
PROVIDER_LAUNCH_CLAIM_BOUNDARY = (
    "Locally captured canonical RunPod request/response JSON bodies and client "
    "timestamps. The receipt is not a RunPod signature, trusted timestamp, or "
    "billing settlement; it proves on-demand/unlocked only when those false "
    "values are present in the retained provider create response that also "
    "reports the Pod RUNNING and supplies lastStartedAt."
)

_HEX40_64 = re.compile(r"^[0-9a-f]{40,64}$")
_UPPER_SHA256 = re.compile(r"^[0-9A-F]{64}$")
_OCI_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CAPTURE_ID = re.compile(r"^[0-9]{2}-(baseline|noop|zero)-r[1-3]$")
_ARRAY_NAMES = (
    "generated_token_ids",
    "input_lengths",
    "mlp_states",
    "pre_selection_logits",
    "prompt_attention_mask",
    "prompt_input_ids",
    "residual_states",
)
_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_TENSOR_BYTES = 1024 * 1024 * 1024


@dataclass(frozen=True)
class CaptureEvidence:
    capture_id: str
    condition: str
    repetition: int
    receipt: Mapping[str, object]
    arrays: Mapping[str, np.ndarray]
    receipt_identity: Mapping[str, object]
    tensor_identity: Mapping[str, object]
    plan_identity: Mapping[str, object]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "execute":
            result = execute_canary(
                preregistration_path=args.preregistration,
                output_root=args.output_root,
                snapshot_root=args.snapshot_root,
                model_storage_root=args.model_storage_root,
                source_commit_sha256=args.source_commit_sha256,
                oci_image_digest=args.oci_image_digest,
                provider_launch_receipt_path=args.provider_launch_receipt,
                watchdog_receipt_path=args.external_watchdog_receipt,
                github_supervisor_receipt_path=args.github_supervisor_receipt,
                device=args.device,
            )
        else:
            result = verify_bundle(
                bundle_root=args.bundle_root,
                external_preregistration_path=args.preregistration,
            )
    except Exception as exc:
        print(
            canonical_json_bytes(
                {
                    "status": FAIL_STATUS,
                    "packet_eligibility": PACKET_STATUS,
                    "scientific_status": SCIENTIFIC_STATUS,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            ).decode("utf-8").rstrip(),
            file=sys.stderr,
        )
        return 1
    print(
        canonical_json_bytes(
            {
                "status": result["status"],
                "packet_eligibility": result["packet_eligibility"],
                "scientific_status": result["scientific_status"],
                "result_manifest_sha256": result["result_manifest_sha256"],
                "external_anchor_status": result["external_anchor"]["status"],
            }
        ).decode("utf-8").rstrip()
    )
    return 0 if result["status"] == PASS_STATUS else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    execute = subparsers.add_parser("execute", help="run the one-use nine-capture canary")
    execute.add_argument(
        "--preregistration",
        type=Path,
        default=DEFAULT_PREREGISTRATION,
    )
    execute.add_argument("--output-root", required=True, type=Path)
    execute.add_argument("--snapshot-root", required=True, type=Path)
    execute.add_argument("--model-storage-root", required=True, type=Path)
    execute.add_argument("--source-commit-sha256", required=True)
    execute.add_argument("--oci-image-digest", required=True)
    execute.add_argument("--provider-launch-receipt", required=True, type=Path)
    execute.add_argument("--external-watchdog-receipt", required=True, type=Path)
    execute.add_argument("--github-supervisor-receipt", required=True, type=Path)
    execute.add_argument("--device", default="cuda:0", choices=("cuda:0",))

    verify = subparsers.add_parser(
        "verify", help="recompute the result from a copied evidence bundle"
    )
    verify.add_argument("--bundle-root", required=True, type=Path)
    verify.add_argument("--preregistration", type=Path)
    return parser


def execute_canary(
    *,
    preregistration_path: Path,
    output_root: Path,
    snapshot_root: Path,
    model_storage_root: Path,
    source_commit_sha256: str,
    oci_image_digest: str,
    provider_launch_receipt_path: Path,
    watchdog_receipt_path: Path,
    github_supervisor_receipt_path: Path,
    device: str,
) -> dict[str, object]:
    """Execute the exact frozen schedule once and write a create-once bundle."""

    preregistration_path = preregistration_path.resolve(strict=True)
    preregistration, preregistration_raw = load_preregistration(preregistration_path)
    source_manifest_document = _current_source_file_manifest_document()
    if source_manifest_document["manifest_sha256"] != preregistration[
        "launch_bindings"
    ]["required_source_file_manifest_sha256"]:
        raise RuntimeError("current source-file manifest differs from preregistration")
    dependency_lock_raw = _read_plain_file(
        DEFAULT_DEPENDENCY_LOCK.resolve(strict=True), max_bytes=1024 * 1024
    )
    expected_dependency_lock_sha256 = preregistration["experiment"]["runtime"][
        "required_dependency_lock_sha256"
    ]
    if sha256_bytes(dependency_lock_raw) != expected_dependency_lock_sha256:
        raise RuntimeError("dependency lock bytes differ from preregistration")
    _require_execution_bindings(
        preregistration,
        source_commit_sha256=source_commit_sha256,
        oci_image_digest=oci_image_digest,
    )
    provider_launch_receipt_path = provider_launch_receipt_path.resolve(strict=True)
    provider_launch, provider_launch_raw = _load_provider_launch_receipt(
        provider_launch_receipt_path,
        source_commit_sha256=source_commit_sha256,
        oci_image_digest=oci_image_digest,
        expected_image_name=preregistration["launch_bindings"][
            "required_image_name"
        ],
        require_current_time=True,
    )
    watchdog_receipt_path = watchdog_receipt_path.resolve(strict=True)
    watchdog, watchdog_raw = _load_watchdog_receipt(
        watchdog_receipt_path,
        source_commit_sha256=source_commit_sha256,
        oci_image_digest=oci_image_digest,
        watchdog_script_sha256=preregistration["launch_bindings"][
            "required_watchdog_script_sha256"
        ],
        provider_launch_receipt_sha256=sha256_bytes(provider_launch_raw),
        expected_pod_id=_required_text(provider_launch, "pod_id"),
        expected_pod_name=_required_text(provider_launch, "pod_name"),
        expected_provider_started_at=_required_text(
            provider_launch, "provider_started_at_utc"
        ),
        expected_deadline=_required_text(provider_launch, "hard_stop_deadline_utc"),
    )
    github_supervisor_receipt_path = github_supervisor_receipt_path.resolve(strict=True)
    github_supervisor, github_supervisor_raw = _load_github_supervisor_receipt(
        github_supervisor_receipt_path,
        source_commit_sha256=source_commit_sha256,
        supervisor_source_sha256=preregistration["launch_bindings"][
            "required_github_supervisor_source_sha256"
        ],
        expected_pod_id=watchdog["workload_id"],
        expected_pod_name=watchdog["workload_name"],
        expected_provider_started_at=provider_launch["provider_started_at_utc"],
        expected_deadline=provider_launch["hard_stop_deadline_utc"],
    )
    _require_watchdog_time_remaining(
        watchdog, phase="pre-runtime-load", minimum_remaining_seconds=600
    )
    deterministic_controls = _configure_deterministic_gpu(
        preregistration, device=device
    )

    output_root = _require_new_absolute_directory_target(output_root)
    snapshot_root = snapshot_root.resolve(strict=True)
    model_storage_root = model_storage_root.resolve(strict=True)
    output_root.mkdir()
    try:
        _write_create_new(output_root / "preregistration.snapshot.json", preregistration_raw)
        _write_create_new(output_root / "runner.snapshot.py", Path(__file__).read_bytes())
        _write_create_new(output_root / "dependency-lock.snapshot.txt", dependency_lock_raw)
        _write_create_new(
            output_root / "source-files.manifest.json",
            canonical_json_bytes(source_manifest_document),
        )
        _write_create_new(
            output_root / "provider-launch.receipt.json", provider_launch_raw
        )
        _write_create_new(output_root / "external-watchdog.receipt.json", watchdog_raw)
        _write_create_new(
            output_root / "github-stop-supervisor.armed.receipt.json",
            github_supervisor_raw,
        )

        scenario = preregistration["experiment"]["scenario"]
        scenario_bytes = canonical_json_bytes(
            {
                "schema_version": SCENARIO_SCHEMA,
                "scenario_id": scenario["scenario_id"],
                "prompt": scenario["prompt"],
            }
        )
        scenario_path = output_root / "scenario.json"
        _write_create_new(scenario_path, scenario_bytes)
        scenario_source = {
            "path": str(scenario_path),
            "byte_count": len(scenario_bytes),
            "sha256": sha256_bytes(scenario_bytes),
            "snapshot_semantics": "one immutable byte snapshot strict-parsed and hashed",
        }

        bindings = {
            "schema_version": "cas_open_weight_trajectory_canary_execution_bindings.v3",
            "source_commit_sha256": source_commit_sha256,
            "oci_image_digest": oci_image_digest,
            "device": device,
            "deterministic_controls": deterministic_controls,
            "provider_launch_receipt_sha256": sha256_bytes(provider_launch_raw),
            "provider_launch_status": provider_launch["status"],
            "provider_pod_id": provider_launch["pod_id"],
            "provider_pod_name": provider_launch["pod_name"],
            "provider_started_at_utc": provider_launch["provider_started_at_utc"],
            "hard_stop_deadline_utc": provider_launch["hard_stop_deadline_utc"],
            "watchdog_receipt_sha256": sha256_bytes(watchdog_raw),
            "watchdog_status": watchdog["status"],
            "github_supervisor_receipt_sha256": sha256_bytes(
                github_supervisor_raw
            ),
            "github_supervisor_status": github_supervisor["status"],
            "claim_boundary": (
                "Execution-environment declarations and locally captured provider "
                "request/response bytes are cross-links, not a provider signature, "
                "trusted timestamp, image attestation, or billing settlement."
            ),
        }
        _write_create_new(
            output_root / "execution-bindings.json", canonical_json_bytes(bindings)
        )

        runtime_api = _load_runtime_api()
        model = preregistration["experiment"]["model"]
        runtime = runtime_api["load_open_weight_runtime"](
            runtime_api["RuntimeLoadConfig"](
                snapshot=runtime_api["LocalModelSnapshot"](
                    model_id=model["model_id"],
                    revision=model["revision"],
                    snapshot_root=snapshot_root,
                    model_storage_root=model_storage_root,
                ),
                adapter_source_path=DEFAULT_ADAPTER_SOURCE,
                entrypoint_source_path=Path(__file__).resolve(),
                device=device,
                dtype="auto",
                minimum_available_memory_bytes=preregistration["experiment"][
                    "runtime"
                ]["minimum_available_memory_bytes"],
                minimum_capture_available_bytes=preregistration["experiment"][
                    "runtime"
                ]["minimum_capture_available_bytes"],
            )
        )
        _verify_loaded_runtime_preregistration(runtime, preregistration)
        _require_watchdog_time_remaining(
            watchdog, phase="post-runtime-load", minimum_remaining_seconds=300
        )

        captures_root = output_root / "captures"
        captures_root.mkdir()
        for schedule_row in preregistration["experiment"]["schedule"]:
            _require_watchdog_time_remaining(
                watchdog,
                phase=f"pre-capture-{schedule_row['capture_id']}",
                minimum_remaining_seconds=60,
            )
            capture_directory = captures_root / schedule_row["capture_id"]
            capture_directory.mkdir()
            intervention = _intervention_for_schedule(
                runtime_api["InterventionSpec"], preregistration, schedule_row
            )
            capture = runtime_api["capture_greedy_trajectory"](
                runtime,
                scenario_id=scenario["scenario_id"],
                prompt=scenario["prompt"],
                max_new_tokens=preregistration["experiment"]["generation"][
                    "max_new_tokens"
                ],
                intervention=intervention,
                seed=preregistration["experiment"]["generation"]["seed"],
                scenario_source=scenario_source,
            )
            receipt = runtime_api["persist_capture_create_new"](
                runtime=runtime,
                capture=capture,
                output_directory=capture_directory,
                artifact_stem="capture",
            )
            context = runtime_api["CaptureVerificationContext"].from_runtime_capture(
                runtime, capture
            )
            verified = runtime_api["verify_capture_receipt"](
                (capture_directory / "capture.receipt.json").resolve(),
                context=context,
            )
            if verified != receipt:
                raise RuntimeError("capture receipt changed between exact verifications")
            _require_watchdog_time_remaining(
                watchdog,
                phase=f"post-capture-{schedule_row['capture_id']}",
                minimum_remaining_seconds=1,
            )

        _require_watchdog_time_remaining(
            watchdog, phase="pre-result-verification", minimum_remaining_seconds=1
        )
        result = _create_result_manifest(output_root, preregistration)
        verified_result = verify_bundle(
            bundle_root=output_root,
            external_preregistration_path=preregistration_path,
        )
        if verified_result != result:
            raise RuntimeError("portable verifier result differs from created result")
        return result
    except Exception as exc:
        _write_error_manifest_if_possible(
            output_root,
            preregistration_sha256=preregistration["preregistration_sha256"],
            error=exc,
        )
        raise


def verify_bundle(
    *, bundle_root: Path, external_preregistration_path: Path | None = None
) -> dict[str, object]:
    """Independently recompute a copied bundle without loading any model."""

    bundle_root = bundle_root.resolve(strict=True)
    if not bundle_root.is_dir() or bundle_root.is_symlink():
        raise ValueError("bundle_root must be a plain absolute directory")
    prereg_path = bundle_root / "preregistration.snapshot.json"
    preregistration, preregistration_raw = load_preregistration(prereg_path)
    if external_preregistration_path is not None:
        external = _read_plain_file(
            external_preregistration_path.resolve(strict=True),
            max_bytes=_MAX_JSON_BYTES,
        )
        if external != preregistration_raw:
            raise ValueError("bundle preregistration differs from external preregistration")

    _require_exact_bundle_topology(bundle_root, preregistration)
    watchdog_deadline, github_arm_written = _verify_bundle_support_files(
        bundle_root, preregistration
    )

    result_path = bundle_root / "canary.result.json"
    result_raw = _read_plain_file(result_path, max_bytes=_MAX_JSON_BYTES)
    result = strict_json_object(result_raw, "result manifest")
    _verify_result_manifest_self_hash(result)
    _verify_result_manifest_constants(result, preregistration)

    expected_files = _file_manifest(bundle_root, exclude={"canary.result.json"})
    if result["evidence_files"] != expected_files:
        raise ValueError("result evidence-file manifest differs from bundle bytes")

    captures, capture_links, evaluation = _recompute_capture_set(
        bundle_root, preregistration
    )
    _verify_watchdog_capture_window(
        captures,
        deadline=watchdog_deadline,
        arm_written=github_arm_written,
        maximum_wall_seconds=1800,
    )
    if result["captures"] != capture_links:
        raise ValueError("result capture cross-links differ from recomputation")
    if result["evaluation"] != evaluation:
        raise ValueError("stored result evaluation differs from recomputation")
    expected_status = _status_from_evaluation(evaluation)
    if result["status"] != expected_status:
        raise ValueError("stored result status differs from recomputed criteria")
    if len(captures) != 9:
        raise ValueError("portable verifier did not admit exactly nine captures")
    return result


def load_preregistration(path: Path) -> tuple[dict[str, object], bytes]:
    raw = _read_plain_file(path, max_bytes=_MAX_JSON_BYTES)
    value = strict_json_object(raw, "preregistration")
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "claim_boundary",
        "source_documents",
        "experiment",
        "launch_bindings",
        "external_anchor",
        "preregistration_sha256",
    }
    if set(value) != required:
        raise ValueError("preregistration keyset mismatch")
    _require_literal(value, "schema_version", PREREG_SCHEMA)
    _require_literal(value, "packet_eligibility", PACKET_STATUS)
    _require_literal(value, "scientific_status", SCIENTIFIC_STATUS)
    _require_literal(value, "claim_boundary", CANARY_CLAIM_BOUNDARY)
    expected_hash = _required_upper_sha256(value, "preregistration_sha256")
    unsigned = dict(value)
    unsigned.pop("preregistration_sha256")
    if sha256_bytes(canonical_json_bytes(unsigned)) != expected_hash:
        raise ValueError("preregistration self-hash mismatch")
    _validate_preregistration(value)
    return value, raw


def _validate_preregistration(value: Mapping[str, object]) -> None:
    status = value.get("status")
    launch_value = _required_mapping(value, "launch_bindings")
    authority = launch_value.get("execution_authority")
    if (status, authority) not in {
        (
            "FROZEN_DESIGN_ONLY_NO_EXECUTION_AUTHORITY",
            UNBOUND_EXECUTION_AUTHORITY,
        ),
        ("FROZEN_BOUND_SINGLE_ENGINEERING_CANARY", BOUND_EXECUTION_AUTHORITY),
    }:
        raise ValueError("preregistration status/authority pairing mismatch")
    sources = value.get("source_documents")
    expected_sources = {
        (
            "CAS PCBA Engineer Interior KDP",
            2069838,
            "53AE63494DFEDE8F5C9CA36CE387482C02E5005E7A5AACE68398C8053690F494",
        ),
        (
            "CAS Ohm Quantification Guide",
            2610388,
            "89AE13C0A5D6208E328E9EDC55F816609BB172076CC13093DCCCCF418145CE64",
        ),
    }
    if not isinstance(sources, list) or {
        (row.get("title"), row.get("byte_count"), row.get("sha256"))
        for row in sources
        if isinstance(row, Mapping)
    } != expected_sources:
        raise ValueError("preregistration source-document identities mismatch")
    experiment = _required_mapping(value, "experiment")
    if sha256_bytes(canonical_json_bytes(experiment)) != FROZEN_EXPERIMENT_SHA256:
        raise ValueError("preregistration experiment bytes differ from frozen design")
    required_experiment = {
        "purpose",
        "model",
        "scenario",
        "generation",
        "intervention",
        "schedule",
        "runtime",
        "expected_arrays",
        "decision_rule",
    }
    if set(experiment) != required_experiment:
        raise ValueError("preregistration experiment keyset mismatch")
    model = _required_mapping(experiment, "model")
    if model.get("model_id") != "EleutherAI/pythia-160m":
        raise ValueError("preregistered model_id mismatch")
    if model.get("revision") != "50f5173d932e8e61f858120bcb800b97af589f46":
        raise ValueError("preregistered model revision mismatch")
    _required_upper_sha256(model, "tree_manifest_sha256")
    files = model.get("files")
    if not isinstance(files, list) or len(files) != 5:
        raise ValueError("preregistered model file manifest must contain five files")
    expected_names = {
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    }
    if {row.get("relative_path") for row in files if isinstance(row, Mapping)} != expected_names:
        raise ValueError("preregistered model file names mismatch")
    for row in files:
        if not isinstance(row, Mapping) or set(row) != {
            "relative_path",
            "byte_count",
            "sha256",
        }:
            raise ValueError("preregistered model file row mismatch")
        if _required_int(row, "byte_count") <= 0:
            raise ValueError("preregistered model file size must be positive")
        _required_upper_sha256(row, "sha256")

    scenario = _required_mapping(experiment, "scenario")
    if set(scenario) != {"scenario_id", "prompt", "prompt_sha256"}:
        raise ValueError("preregistered scenario keyset mismatch")
    prompt = _required_text(scenario, "prompt")
    if sha256_bytes(prompt.encode("utf-8")) != _required_upper_sha256(
        scenario, "prompt_sha256"
    ):
        raise ValueError("preregistered prompt hash mismatch")

    generation = _required_mapping(experiment, "generation")
    expected_generation = {
        "method": "manual_greedy_argmax",
        "max_new_tokens": 2,
        "seed": 1729,
        "temperature": None,
        "sampling": False,
    }
    if generation != expected_generation:
        raise ValueError("preregistered generation contract mismatch")
    intervention = _required_mapping(experiment, "intervention")
    if intervention != {
        "target_layer_index": 6,
        "active_steps": [0],
        "noop_mode": "noop",
        "active_mode": "zero",
        "max_vector_norm": 0.0,
    }:
        raise ValueError("preregistered intervention contract mismatch")
    schedule = experiment.get("schedule")
    if schedule != expected_schedule():
        raise ValueError("preregistered capture schedule mismatch")

    runtime = _required_mapping(experiment, "runtime")
    if runtime.get("required_device") != "cuda:0":
        raise ValueError("preregistered device must be cuda:0")
    if runtime.get("required_device_name") != "NVIDIA A40":
        raise ValueError("preregistered device must be NVIDIA A40")
    if runtime.get("required_device_capability") != [8, 6]:
        raise ValueError("preregistered device capability must be [8, 6]")
    if runtime.get("required_python_version") != "3.12.3":
        raise ValueError("preregistered Python version mismatch")
    if runtime.get("required_dependency_versions") != {
        "numpy": "2.3.5",
        "safetensors": "0.7.0",
        "torch": "2.8.0",
        "transformers": "5.8.1",
    }:
        raise ValueError("preregistered dependency versions mismatch")
    if runtime.get("required_torch_runtime_version") != "2.8.0+cu128":
        raise ValueError("preregistered torch runtime version mismatch")
    if runtime.get("required_torch_cuda_version") != "12.8":
        raise ValueError("preregistered torch CUDA version mismatch")
    if runtime.get("required_dependency_lock_sha256") != (
        "9E990C06B907FE117E67D6BB4CCD8B5AF09FFD9E8B1D98D893A727102C33CB9A"
    ):
        raise ValueError("preregistered dependency lock mismatch")
    deterministic = runtime.get("deterministic_controls")
    if deterministic != {
        "PYTHONHASHSEED": "1729",
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "torch_deterministic_algorithms": True,
        "cudnn_benchmark": False,
        "cudnn_deterministic": True,
        "cuda_matmul_allow_tf32": False,
        "cudnn_allow_tf32": False,
        "float32_matmul_precision": "highest",
    }:
        raise ValueError("preregistered deterministic controls mismatch")
    for key in (
        "minimum_available_memory_bytes",
        "minimum_capture_available_bytes",
    ):
        if _required_int(runtime, key) <= 0:
            raise ValueError(f"preregistered {key} must be positive")

    arrays = _required_mapping(experiment, "expected_arrays")
    if arrays != {
        "residual_states": [2, 12, 768],
        "mlp_states": [2, 12, 768],
        "pre_selection_logits": [2, 50304],
        "generated_token_ids": [2],
        "input_lengths": [2],
    }:
        raise ValueError("preregistered expected array shapes mismatch")
    decision = _required_mapping(experiment, "decision_rule")
    if decision.get("all_required_criteria_must_pass") is not True:
        raise ValueError("preregistered decision rule must require all criteria")
    if decision.get("generated_text_change_required") is not False:
        raise ValueError("generated text must not be a preregistered PASS requirement")

    launch = _required_mapping(value, "launch_bindings")
    if set(launch) != {
        "execution_authority",
        "required_source_commit_sha256",
        "required_oci_image_digest",
        "required_runner_source_sha256",
        "required_source_file_manifest_sha256",
        "required_watchdog_script_sha256",
        "required_github_supervisor_source_sha256",
        "provider_launch_receipt_required",
        "required_provider_launch_receipt_schema",
        "required_image_name",
        "required_cloud_type",
        "required_interruptible",
        "required_locked",
        "required_volume_encrypted",
        "external_stop_watchdog_required",
        "maximum_wall_seconds",
        "maximum_spend_usd",
    }:
        raise ValueError("preregistration launch binding keyset mismatch")
    if launch.get("execution_authority") not in {
        UNBOUND_EXECUTION_AUTHORITY,
        BOUND_EXECUTION_AUTHORITY,
    }:
        raise ValueError("unknown preregistration execution authority")
    _required_upper_sha256(launch, "required_runner_source_sha256")
    _required_upper_sha256(launch, "required_source_file_manifest_sha256")
    _required_upper_sha256(launch, "required_watchdog_script_sha256")
    _required_upper_sha256(launch, "required_github_supervisor_source_sha256")
    if launch.get("provider_launch_receipt_required") is not True:
        raise ValueError("provider launch receipt must remain required")
    if launch.get("required_provider_launch_receipt_schema") != PROVIDER_LAUNCH_SCHEMA:
        raise ValueError("provider launch receipt schema mismatch")
    if launch.get("required_image_name") != (
        "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"
    ):
        raise ValueError("preregistered provider image name mismatch")
    if launch.get("required_cloud_type") != "SECURE":
        raise ValueError("preregistered provider cloud type mismatch")
    if launch.get("required_interruptible") is not False:
        raise ValueError("preregistered provider interruptible flag must be false")
    if launch.get("required_locked") is not False:
        raise ValueError("preregistered provider locked flag must be false")
    if launch.get("required_volume_encrypted") is not True:
        raise ValueError("preregistered provider volume encryption must be true")
    if launch.get("external_stop_watchdog_required") is not True:
        raise ValueError("external stop watchdog must remain required")
    if launch.get("maximum_wall_seconds") != 1800:
        raise ValueError("maximum wall time must remain 1800 seconds")
    if launch.get("maximum_spend_usd") != "0.50":
        raise ValueError("maximum spend must remain the exact string 0.50")

    anchor = _required_mapping(value, "external_anchor")
    if anchor != {
        "status": EXTERNAL_ANCHOR_STATUS,
        "anchor_uri": None,
        "anchor_receipt_sha256": None,
        "claim_boundary": ANCHOR_CLAIM_BOUNDARY,
    }:
        raise ValueError("preregistration external-anchor boundary mismatch")


def _require_exact_bundle_topology(
    bundle_root: Path, preregistration: Mapping[str, object]
) -> None:
    expected = {
        "preregistration.snapshot.json",
        "runner.snapshot.py",
        "dependency-lock.snapshot.txt",
        "source-files.manifest.json",
        "scenario.json",
        "execution-bindings.json",
        "provider-launch.receipt.json",
        "external-watchdog.receipt.json",
        "github-stop-supervisor.armed.receipt.json",
        "canary.result.json",
    }
    for row in preregistration["experiment"]["schedule"]:
        prefix = f"captures/{row['capture_id']}"
        expected.update(
            {
                f"{prefix}/capture.receipt.json",
                f"{prefix}/capture.safetensors",
                f"{prefix}/capture.adapter-plan.json",
            }
        )
    observed: set[str] = set()
    for path in bundle_root.rglob("*"):
        if path.is_symlink() or _is_reparse(path.lstat()):
            raise ValueError(f"bundle path must not be a link/reparse point: {path}")
        if path.is_file():
            observed.add(path.relative_to(bundle_root).as_posix())
        elif not path.is_dir():
            raise ValueError(f"bundle contains a non-file/non-directory path: {path}")
    if observed != expected:
        raise ValueError(
            "bundle file topology mismatch: "
            f"missing={sorted(expected - observed)} extra={sorted(observed - expected)}"
        )


def _verify_bundle_support_files(
    bundle_root: Path, preregistration: Mapping[str, object]
) -> tuple[datetime, datetime]:
    launch = _required_mapping(preregistration, "launch_bindings")
    if launch.get("execution_authority") != BOUND_EXECUTION_AUTHORITY:
        raise ValueError("completed bundle preregistration is not execution-bound")
    source_commit = launch.get("required_source_commit_sha256")
    image_digest = launch.get("required_oci_image_digest")
    if not isinstance(source_commit, str) or not _HEX40_64.fullmatch(source_commit):
        raise ValueError("completed bundle source commit is not bound")
    if not isinstance(image_digest, str) or not _OCI_DIGEST.fullmatch(image_digest):
        raise ValueError("completed bundle OCI digest is not bound")

    runner_raw = _read_plain_file(
        bundle_root / "runner.snapshot.py", max_bytes=4 * 1024 * 1024
    )
    if sha256_bytes(runner_raw) != launch["required_runner_source_sha256"]:
        raise ValueError("bundle runner snapshot differs from preregistration")
    dependency_lock_raw = _read_plain_file(
        bundle_root / "dependency-lock.snapshot.txt", max_bytes=1024 * 1024
    )
    if sha256_bytes(dependency_lock_raw) != preregistration["experiment"]["runtime"][
        "required_dependency_lock_sha256"
    ]:
        raise ValueError("bundle dependency lock differs from preregistration")
    source_manifest_raw = _read_plain_file(
        bundle_root / "source-files.manifest.json", max_bytes=1024 * 1024
    )
    source_manifest = strict_json_object(
        source_manifest_raw, "bundled source-file manifest"
    )
    if set(source_manifest) != {"schema_version", "files", "manifest_sha256"}:
        raise ValueError("bundle source-file manifest keyset mismatch")
    _require_literal(
        source_manifest,
        "schema_version",
        "cas_open_weight_canary_source_file_manifest.v1",
    )
    files = source_manifest.get("files")
    if not isinstance(files, list) or len(files) != len(FROZEN_SOURCE_RELATIVE_PATHS):
        raise ValueError("bundle source-file manifest rows are invalid")
    if sha256_bytes(canonical_json_bytes(files)) != source_manifest.get(
        "manifest_sha256"
    ):
        raise ValueError("bundle source-file manifest self-digest mismatch")
    if source_manifest["manifest_sha256"] != launch[
        "required_source_file_manifest_sha256"
    ]:
        raise ValueError("bundle source-file manifest differs from preregistration")
    scenario = preregistration["experiment"]["scenario"]
    expected_scenario = canonical_json_bytes(
        {
            "schema_version": SCENARIO_SCHEMA,
            "scenario_id": scenario["scenario_id"],
            "prompt": scenario["prompt"],
        }
    )
    if _read_plain_file(bundle_root / "scenario.json", max_bytes=1024 * 1024) != (
        expected_scenario
    ):
        raise ValueError("bundle scenario bytes differ from preregistration")

    provider_launch_raw = _read_plain_file(
        bundle_root / "provider-launch.receipt.json", max_bytes=256 * 1024
    )
    provider_launch = _validate_provider_launch_receipt(
        provider_launch_raw,
        source_commit_sha256=source_commit,
        oci_image_digest=image_digest,
        expected_image_name=launch["required_image_name"],
        require_current_time=False,
    )

    watchdog_raw = _read_plain_file(
        bundle_root / "external-watchdog.receipt.json", max_bytes=64 * 1024
    )
    watchdog = strict_json_object(watchdog_raw, "bundled watchdog receipt")
    required_watchdog = {
        "schema_version",
        "status",
        "provider",
        "provider_launch_receipt_sha256",
        "provider_started_at_utc",
        "workload_id",
        "workload_name",
        "hard_stop_deadline_utc",
        "maximum_wall_seconds",
        "maximum_spend_usd",
        "source_commit_sha256",
        "oci_image_digest",
        "watchdog_script_sha256",
        "emergency_task_name",
        "emergency_fallback_status",
        "claim_boundary",
    }
    if set(watchdog) != required_watchdog:
        raise ValueError("bundled watchdog receipt keyset mismatch")
    _require_literal(watchdog, "schema_version", WATCHDOG_SCHEMA)
    _require_literal(watchdog, "status", "ARMED")
    _require_literal(watchdog, "provider", "RUNPOD")
    _require_literal(watchdog, "workload_id", provider_launch["pod_id"])
    _require_literal(watchdog, "workload_name", provider_launch["pod_name"])
    _require_literal(
        watchdog,
        "provider_launch_receipt_sha256",
        sha256_bytes(provider_launch_raw),
    )
    if _parse_utc(_required_text(watchdog, "provider_started_at_utc")) != _parse_utc(
        _required_text(provider_launch, "provider_started_at_utc")
    ):
        raise ValueError("bundled watchdog/provider start timestamp mismatch")
    watchdog_deadline = _parse_utc(
        _required_text(watchdog, "hard_stop_deadline_utc")
    )
    if watchdog_deadline != _parse_utc(
        _required_text(provider_launch, "hard_stop_deadline_utc")
    ):
        raise ValueError("bundled watchdog/provider deadline mismatch")
    _require_literal(watchdog, "maximum_wall_seconds", 1800)
    _require_literal(watchdog, "maximum_spend_usd", "0.50")
    _require_literal(watchdog, "source_commit_sha256", source_commit)
    _require_literal(watchdog, "oci_image_digest", image_digest)
    _require_literal(
        watchdog,
        "watchdog_script_sha256",
        launch["required_watchdog_script_sha256"],
    )
    _require_literal(
        watchdog, "emergency_fallback_status", "REGISTERED_AND_REVALIDATED"
    )
    _require_literal(
        watchdog,
        "emergency_task_name",
        f"CAS-OpenWeight-Canary-Stop-{watchdog['workload_id']}",
    )
    _require_literal(
        watchdog,
        "claim_boundary",
        "Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.",
    )
    if canonical_json_bytes(watchdog) != watchdog_raw:
        raise ValueError("bundled watchdog receipt is not canonical JSON")

    github_supervisor_raw = _read_plain_file(
        bundle_root / "github-stop-supervisor.armed.receipt.json",
        max_bytes=64 * 1024,
    )
    github_supervisor = _validate_github_supervisor_receipt(
        github_supervisor_raw,
        source_commit_sha256=source_commit,
        supervisor_source_sha256=launch[
            "required_github_supervisor_source_sha256"
        ],
        expected_pod_id=watchdog["workload_id"],
        expected_pod_name=watchdog["workload_name"],
        expected_provider_started_at=provider_launch["provider_started_at_utc"],
        expected_deadline=provider_launch["hard_stop_deadline_utc"],
        require_current_time=False,
    )

    bindings_raw = _read_plain_file(
        bundle_root / "execution-bindings.json", max_bytes=1024 * 1024
    )
    bindings = strict_json_object(bindings_raw, "execution bindings")
    if set(bindings) != {
        "schema_version",
        "source_commit_sha256",
        "oci_image_digest",
        "device",
        "deterministic_controls",
        "provider_launch_receipt_sha256",
        "provider_launch_status",
        "provider_pod_id",
        "provider_pod_name",
        "provider_started_at_utc",
        "hard_stop_deadline_utc",
        "watchdog_receipt_sha256",
        "watchdog_status",
        "github_supervisor_receipt_sha256",
        "github_supervisor_status",
        "claim_boundary",
    }:
        raise ValueError("execution bindings keyset mismatch")
    _require_literal(
        bindings,
        "schema_version",
        "cas_open_weight_trajectory_canary_execution_bindings.v3",
    )
    _require_literal(bindings, "source_commit_sha256", source_commit)
    _require_literal(bindings, "oci_image_digest", image_digest)
    _require_literal(
        bindings,
        "device",
        preregistration["experiment"]["runtime"]["required_device"],
    )
    _require_literal(
        bindings,
        "deterministic_controls",
        preregistration["experiment"]["runtime"]["deterministic_controls"],
    )
    _require_literal(
        bindings,
        "provider_launch_receipt_sha256",
        sha256_bytes(provider_launch_raw),
    )
    _require_literal(bindings, "provider_launch_status", provider_launch["status"])
    _require_literal(bindings, "provider_pod_id", provider_launch["pod_id"])
    _require_literal(bindings, "provider_pod_name", provider_launch["pod_name"])
    _require_literal(
        bindings,
        "provider_started_at_utc",
        provider_launch["provider_started_at_utc"],
    )
    _require_literal(
        bindings,
        "hard_stop_deadline_utc",
        provider_launch["hard_stop_deadline_utc"],
    )
    _require_literal(bindings, "watchdog_receipt_sha256", sha256_bytes(watchdog_raw))
    _require_literal(bindings, "watchdog_status", "ARMED")
    _require_literal(
        bindings,
        "github_supervisor_receipt_sha256",
        sha256_bytes(github_supervisor_raw),
    )
    _require_literal(
        bindings,
        "github_supervisor_status",
        github_supervisor["status"],
    )
    _require_literal(
        bindings,
        "claim_boundary",
        "Execution-environment declarations and locally captured provider request/response bytes are cross-links, not a provider signature, trusted timestamp, image attestation, or billing settlement.",
    )
    if canonical_json_bytes(bindings) != bindings_raw:
        raise ValueError("execution bindings are not canonical JSON")
    github_arm_written = _parse_utc(
        _required_text(github_supervisor, "written_at_utc")
    )
    return watchdog_deadline, github_arm_written


def expected_schedule() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ordinal = 1
    for repetition in (1, 2, 3):
        for condition in ("baseline", "noop", "zero"):
            rows.append(
                {
                    "ordinal": ordinal,
                    "capture_id": f"{ordinal:02d}-{condition}-r{repetition}",
                    "condition": condition,
                    "repetition": repetition,
                }
            )
            ordinal += 1
    return rows


def _require_execution_bindings(
    preregistration: Mapping[str, object],
    *,
    source_commit_sha256: str,
    oci_image_digest: str,
) -> None:
    launch = _required_mapping(preregistration, "launch_bindings")
    if launch.get("execution_authority") != BOUND_EXECUTION_AUTHORITY:
        raise RuntimeError(
            "canary is inert: source commit and OCI digest are not frozen for execution"
        )
    expected_commit = launch.get("required_source_commit_sha256")
    expected_image = launch.get("required_oci_image_digest")
    if not isinstance(expected_commit, str) or not _HEX40_64.fullmatch(expected_commit):
        raise RuntimeError("preregistered source commit is not bound")
    if not isinstance(expected_image, str) or not _OCI_DIGEST.fullmatch(expected_image):
        raise RuntimeError("preregistered OCI image digest is not bound")
    if source_commit_sha256 != expected_commit:
        raise RuntimeError("source commit differs from frozen preregistration")
    if oci_image_digest != expected_image:
        raise RuntimeError("OCI image digest differs from frozen preregistration")
    runner_sha256 = sha256_bytes(Path(__file__).read_bytes())
    if runner_sha256 != launch["required_runner_source_sha256"]:
        raise RuntimeError("runner source bytes differ from frozen preregistration")


def _parse_provider_utc(value: str) -> datetime:
    legacy = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
        r"(?P<offset>[+-]\d{4}) UTC",
        value,
    )
    if legacy:
        try:
            return datetime.strptime(
                f"{legacy.group('date')} {legacy.group('offset')}",
                "%Y-%m-%d %H:%M:%S.%f %z",
            ).astimezone(timezone.utc)
        except ValueError as exc:
            raise ValueError("provider UTC timestamp is malformed") from exc
    return _parse_utc(value)


def _validate_provider_transaction(
    value: Mapping[str, object],
    *,
    label: str,
    expected_path: str,
    accepted_http_statuses: set[int],
) -> tuple[Mapping[str, object], Mapping[str, object], datetime, datetime]:
    required = {
        "request_body",
        "request_body_sha256",
        "request_method",
        "request_observed_at_utc",
        "request_path",
        "response_body",
        "response_body_sha256",
        "response_http_status",
        "response_observed_at_utc",
    }
    if set(value) != required:
        raise ValueError(f"provider {label} transaction keyset mismatch")
    _require_literal(value, "request_method", "POST")
    _require_literal(value, "request_path", expected_path)
    request = _required_mapping(value, "request_body")
    response = _required_mapping(value, "response_body")
    if sha256_bytes(canonical_json_bytes(request)) != _required_upper_sha256(
        value, "request_body_sha256"
    ):
        raise ValueError(f"provider {label} request-body hash mismatch")
    if sha256_bytes(canonical_json_bytes(response)) != _required_upper_sha256(
        value, "response_body_sha256"
    ):
        raise ValueError(f"provider {label} response-body hash mismatch")
    http_status = _required_int(value, "response_http_status")
    if http_status not in accepted_http_statuses:
        raise ValueError(f"provider {label} HTTP status mismatch")
    requested = _parse_utc(_required_text(value, "request_observed_at_utc"))
    responded = _parse_utc(_required_text(value, "response_observed_at_utc"))
    if responded < requested:
        raise ValueError(f"provider {label} response predates request")
    return request, response, requested, responded


def _validate_provider_launch_receipt(
    raw: bytes,
    *,
    source_commit_sha256: str,
    oci_image_digest: str,
    expected_image_name: str,
    require_current_time: bool,
) -> dict[str, object]:
    value = strict_json_object(raw, "provider launch receipt")
    if raw != canonical_json_bytes(value):
        raise ValueError("provider launch receipt is not canonical JSON")
    required = {
        "claim_boundary",
        "create_transaction",
        "dedicated_public_key_sha256",
        "hard_stop_deadline_utc",
        "image_name",
        "launch_mode",
        "oci_image_digest",
        "pod_id",
        "pod_name",
        "provider",
        "provider_started_at_utc",
        "receipt_sha256",
        "schema_version",
        "source_commit_sha256",
        "status",
    }
    if set(value) != required:
        raise ValueError("provider launch receipt keyset mismatch")
    _require_literal(value, "schema_version", PROVIDER_LAUNCH_SCHEMA)
    _require_literal(value, "status", "EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED")
    _require_literal(value, "launch_mode", "CREATE_RESPONSE_STARTED_POD")
    _require_literal(value, "provider", "RUNPOD")
    _require_literal(value, "source_commit_sha256", source_commit_sha256)
    _require_literal(value, "oci_image_digest", oci_image_digest)
    _require_literal(value, "image_name", expected_image_name)
    _require_literal(value, "claim_boundary", PROVIDER_LAUNCH_CLAIM_BOUNDARY)
    pod_id = _required_text(value, "pod_id")
    if not re.fullmatch(r"[a-z0-9]{6,32}", pod_id):
        raise ValueError("provider launch receipt Pod ID is malformed")
    pod_name = _required_text(value, "pod_name")
    if not re.fullmatch(r"cas-open-weight-canary-v2-[a-z0-9-]+", pod_name):
        raise ValueError("provider launch receipt Pod name is malformed")
    public_key_sha256 = _required_upper_sha256(
        value, "dedicated_public_key_sha256"
    )

    unsigned = dict(value)
    unsigned.pop("receipt_sha256")
    if sha256_bytes(canonical_json_bytes(unsigned)) != _required_upper_sha256(
        value, "receipt_sha256"
    ):
        raise ValueError("provider launch receipt self-hash mismatch")

    create_request, create_response, create_requested, create_responded = (
        _validate_provider_transaction(
            _required_mapping(value, "create_transaction"),
            label="create",
            expected_path="/v1/pods",
            accepted_http_statuses={201},
        )
    )
    required_create_request = {
        "cloudType",
        "containerDiskInGb",
        "env",
        "gpuCount",
        "gpuTypeIds",
        "imageName",
        "interruptible",
        "locked",
        "name",
        "networkVolumeId",
        "ports",
        "volumeEncrypted",
        "volumeInGb",
        "volumeMountPath",
    }
    if set(create_request) != required_create_request:
        raise ValueError("provider create request keyset mismatch")
    expected_create_literals = {
        "cloudType": "SECURE",
        "gpuTypeIds": ["NVIDIA A40"],
        "imageName": expected_image_name,
        "interruptible": False,
        "locked": False,
        "name": pod_name,
        "networkVolumeId": None,
        "ports": ["22/tcp"],
        "volumeEncrypted": True,
        "volumeMountPath": "/workspace",
    }
    for key, expected in {
        "containerDiskInGb": 50,
        "gpuCount": 1,
        "volumeInGb": 20,
    }.items():
        if _required_int(create_request, key) != expected:
            raise ValueError(f"provider create request {key} literal mismatch")
    for key, expected in expected_create_literals.items():
        observed = create_request.get(key)
        if isinstance(expected, bool):
            if observed is not expected:
                raise ValueError(f"provider create request {key} literal mismatch")
        elif observed != expected:
            raise ValueError(f"provider create request {key} literal mismatch")
    environment = _required_mapping(create_request, "env")
    if set(environment) != {"PUBLIC_KEY"}:
        raise ValueError("provider create request environment keyset mismatch")
    public_key = _required_text(environment, "PUBLIC_KEY")
    if sha256_bytes(public_key.encode("utf-8")) != public_key_sha256:
        raise ValueError("provider create request public-key hash mismatch")

    _require_literal(create_response, "id", pod_id)
    _require_literal(create_response, "name", pod_name)
    if create_response.get("interruptible") is not False:
        raise ValueError(
            "provider create response does not prove interruptible=false"
        )
    if create_response.get("locked") is not False:
        raise ValueError("provider create response does not prove locked=false")
    if create_response.get("volumeEncrypted") is not True:
        raise ValueError("provider create response does not prove volumeEncrypted=true")
    _require_literal(create_response, "desiredStatus", "RUNNING")
    response_started = _parse_provider_utc(
        _required_text(create_response, "lastStartedAt")
    )
    provider_started = _parse_utc(
        _required_text(value, "provider_started_at_utc")
    )
    if response_started != provider_started:
        raise ValueError("provider start response timestamp mismatch")
    if provider_started < create_requested - timedelta(seconds=30) or (
        provider_started > create_responded + timedelta(seconds=30)
    ):
        raise ValueError("provider start timestamp is outside the create exchange")
    deadline = _parse_utc(_required_text(value, "hard_stop_deadline_utc"))
    if deadline != provider_started + timedelta(seconds=1800):
        raise ValueError("provider launch deadline is not exactly start plus 1800 seconds")
    if create_requested > create_responded:
        raise ValueError("provider create chronology mismatch")
    if require_current_time:
        now = datetime.now(timezone.utc)
        if provider_started > now + timedelta(minutes=2) or (
            provider_started < now - timedelta(minutes=5)
        ):
            raise ValueError("provider launch receipt start is outside the arm window")
        if not 0 < (deadline - now).total_seconds() <= 1800:
            raise ValueError("provider launch receipt deadline is not currently active")
    return value


def _load_provider_launch_receipt(
    path: Path,
    *,
    source_commit_sha256: str,
    oci_image_digest: str,
    expected_image_name: str,
    require_current_time: bool,
) -> tuple[dict[str, object], bytes]:
    raw = _read_plain_file(path, max_bytes=256 * 1024)
    value = _validate_provider_launch_receipt(
        raw,
        source_commit_sha256=source_commit_sha256,
        oci_image_digest=oci_image_digest,
        expected_image_name=expected_image_name,
        require_current_time=require_current_time,
    )
    return value, raw


def _load_watchdog_receipt(
    path: Path,
    *,
    source_commit_sha256: str,
    oci_image_digest: str,
    watchdog_script_sha256: str,
    provider_launch_receipt_sha256: str,
    expected_pod_id: str,
    expected_pod_name: str,
    expected_provider_started_at: str,
    expected_deadline: str,
) -> tuple[dict[str, object], bytes]:
    raw = _read_plain_file(path, max_bytes=64 * 1024)
    value = strict_json_object(raw, "external watchdog receipt")
    if raw != canonical_json_bytes(value):
        raise ValueError("external watchdog receipt is not canonical JSON")
    required = {
        "schema_version",
        "status",
        "provider",
        "provider_launch_receipt_sha256",
        "provider_started_at_utc",
        "workload_id",
        "workload_name",
        "hard_stop_deadline_utc",
        "maximum_wall_seconds",
        "maximum_spend_usd",
        "source_commit_sha256",
        "oci_image_digest",
        "watchdog_script_sha256",
        "emergency_task_name",
        "emergency_fallback_status",
        "claim_boundary",
    }
    if set(value) != required:
        raise ValueError("external watchdog receipt keyset mismatch")
    _require_literal(value, "schema_version", WATCHDOG_SCHEMA)
    _require_literal(value, "status", "ARMED")
    _require_literal(value, "provider", "RUNPOD")
    _require_literal(
        value, "provider_launch_receipt_sha256", provider_launch_receipt_sha256
    )
    if _parse_utc(_required_text(value, "provider_started_at_utc")) != _parse_utc(
        expected_provider_started_at
    ):
        raise ValueError("external watchdog/provider start timestamp mismatch")
    _require_literal(value, "workload_id", expected_pod_id)
    _require_literal(value, "workload_name", expected_pod_name)
    if _parse_utc(_required_text(value, "hard_stop_deadline_utc")) != _parse_utc(
        expected_deadline
    ):
        raise ValueError("external watchdog/provider deadline mismatch")
    _require_literal(value, "maximum_wall_seconds", 1800)
    _require_literal(value, "maximum_spend_usd", "0.50")
    _require_literal(value, "source_commit_sha256", source_commit_sha256)
    _require_literal(value, "oci_image_digest", oci_image_digest)
    _require_literal(
        value,
        "watchdog_script_sha256",
        watchdog_script_sha256,
    )
    _require_literal(
        value, "emergency_fallback_status", "REGISTERED_AND_REVALIDATED"
    )
    _require_literal(
        value,
        "emergency_task_name",
        f"CAS-OpenWeight-Canary-Stop-{value['workload_id']}",
    )
    _require_literal(
        value,
        "claim_boundary",
        "Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.",
    )
    _required_text(value, "workload_id")
    deadline = _parse_utc(_required_text(value, "hard_stop_deadline_utc"))
    now = datetime.now(timezone.utc)
    remaining = (deadline - now).total_seconds()
    if not 0 < remaining <= 1800:
        raise ValueError("external watchdog deadline must be within the next 1800 seconds")
    return value, raw


def _validate_github_supervisor_receipt(
    raw: bytes,
    *,
    source_commit_sha256: str,
    supervisor_source_sha256: str,
    expected_pod_id: str,
    expected_pod_name: str,
    expected_provider_started_at: str,
    expected_deadline: str,
    require_current_time: bool,
) -> dict[str, object]:
    value = strict_json_object(raw, "GitHub stop-supervisor arm receipt")
    if raw != canonical_json_bytes(value):
        raise ValueError("GitHub stop-supervisor arm receipt is not canonical JSON")
    required = {
        "claim_boundary",
        "delete_attempted",
        "github_repository",
        "github_run_attempt",
        "github_run_id",
        "github_sha",
        "hard_stop_deadline_utc",
        "mode",
        "observed_status",
        "pod_id",
        "pod_name",
        "provider_started_at_utc",
        "schema_version",
        "source_commit_sha",
        "status",
        "supervisor_source_sha256",
        "written_at_utc",
    }
    if set(value) != required:
        raise ValueError("GitHub stop-supervisor arm receipt keyset mismatch")
    _require_literal(value, "schema_version", GITHUB_SUPERVISOR_SCHEMA)
    _require_literal(value, "status", "ARMED_PROVIDER_GET_SUCCEEDED")
    _require_literal(value, "mode", "PRE_DEADLINE_ARM_CHECK")
    _require_literal(value, "observed_status", "RUNNING")
    _require_literal(value, "delete_attempted", False)
    _require_literal(value, "github_repository", "LittleHenderson/noetic-compass")
    _require_literal(value, "github_sha", source_commit_sha256)
    _require_literal(value, "source_commit_sha", source_commit_sha256)
    _require_literal(value, "pod_id", expected_pod_id)
    _require_literal(value, "pod_name", expected_pod_name)
    if _parse_utc(_required_text(value, "provider_started_at_utc")) != _parse_utc(
        expected_provider_started_at
    ):
        raise ValueError("GitHub stop-supervisor/provider start timestamp mismatch")
    if _parse_utc(_required_text(value, "hard_stop_deadline_utc")) != _parse_utc(
        expected_deadline
    ):
        raise ValueError("GitHub stop-supervisor/provider deadline mismatch")
    _require_literal(
        value,
        "supervisor_source_sha256",
        supervisor_source_sha256,
    )
    _require_literal(
        value,
        "claim_boundary",
        "GitHub-hosted operational stop evidence; not a RunPod signature or billing settlement record.",
    )
    pod_name = _required_text(value, "pod_name")
    if not re.fullmatch(r"cas-open-weight-canary-v2-[a-z0-9-]+", pod_name):
        raise ValueError("GitHub stop-supervisor pod name is malformed")
    if not _required_text(value, "github_run_id").isdigit():
        raise ValueError("GitHub stop-supervisor run id is malformed")
    if not _required_text(value, "github_run_attempt").isdigit():
        raise ValueError("GitHub stop-supervisor run attempt is malformed")
    deadline = _parse_utc(_required_text(value, "hard_stop_deadline_utc"))
    provider_started = _parse_utc(
        _required_text(value, "provider_started_at_utc")
    )
    if deadline != provider_started + timedelta(seconds=1800):
        raise ValueError("GitHub stop-supervisor deadline/start binding mismatch")
    written = _parse_utc(_required_text(value, "written_at_utc"))
    if written >= deadline:
        raise ValueError("GitHub stop-supervisor armed after its hard-stop deadline")
    lead_seconds = (deadline - written).total_seconds()
    if not 600 <= lead_seconds <= 2100:
        raise ValueError("GitHub stop-supervisor arm lead time is outside 10 to 35 minutes")
    if require_current_time:
        now = datetime.now(timezone.utc)
        if not 0 < (deadline - now).total_seconds() <= 1800:
            raise ValueError("GitHub stop-supervisor deadline is not currently active")
        if written > now + timedelta(seconds=30) or written < now - timedelta(minutes=10):
            raise ValueError("GitHub stop-supervisor arm receipt is not fresh")
    return value


def _load_github_supervisor_receipt(
    path: Path,
    *,
    source_commit_sha256: str,
    supervisor_source_sha256: str,
    expected_pod_id: str,
    expected_pod_name: str,
    expected_provider_started_at: str,
    expected_deadline: str,
) -> tuple[dict[str, object], bytes]:
    raw = _read_plain_file(path, max_bytes=64 * 1024)
    value = _validate_github_supervisor_receipt(
        raw,
        source_commit_sha256=source_commit_sha256,
        supervisor_source_sha256=supervisor_source_sha256,
        expected_pod_id=expected_pod_id,
        expected_pod_name=expected_pod_name,
        expected_provider_started_at=expected_provider_started_at,
        expected_deadline=expected_deadline,
        require_current_time=True,
    )
    return value, raw


def _require_watchdog_time_remaining(
    watchdog: Mapping[str, object],
    *,
    phase: str,
    minimum_remaining_seconds: int,
) -> None:
    deadline = _parse_utc(_required_text(watchdog, "hard_stop_deadline_utc"))
    remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
    if remaining < minimum_remaining_seconds:
        raise RuntimeError(
            f"external watchdog deadline is too near or expired at {phase}: "
            f"remaining_seconds={remaining:.3f}"
        )


def _verify_watchdog_capture_window(
    captures: Sequence[CaptureEvidence],
    *,
    deadline: datetime,
    arm_written: datetime,
    maximum_wall_seconds: int,
) -> None:
    window_start = max(
        deadline.timestamp() - maximum_wall_seconds,
        arm_written.timestamp(),
    )
    for capture in captures:
        record = capture.receipt["observation"]["execution_record"]
        started = _parse_utc(_required_text(record, "started_utc"))
        ended = _parse_utc(_required_text(record, "ended_utc"))
        if started.timestamp() < window_start or ended > deadline:
            raise ValueError(
                "capture execution falls outside the externally armed watchdog window"
            )


def _configure_deterministic_gpu(
    preregistration: Mapping[str, object], *, device: str
) -> dict[str, object]:
    runtime = preregistration["experiment"]["runtime"]
    controls = runtime["deterministic_controls"]
    if os.environ.get("PYTHONHASHSEED") != controls["PYTHONHASHSEED"]:
        raise RuntimeError("PYTHONHASHSEED must be fixed before the Python process starts")
    existing_cublas = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    if existing_cublas not in (None, controls["CUBLAS_WORKSPACE_CONFIG"]):
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG conflicts with preregistration")
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = controls["CUBLAS_WORKSPACE_CONFIG"]

    import torch

    if device != runtime["required_device"]:
        raise RuntimeError("requested device differs from preregistration")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable for the preregistered A40 canary")
    torch.cuda.set_device(0)
    if torch.cuda.get_device_name(0) != runtime["required_device_name"]:
        raise RuntimeError("CUDA device name differs from preregistration")
    if list(torch.cuda.get_device_capability(0)) != runtime["required_device_capability"]:
        raise RuntimeError("CUDA device capability differs from preregistration")
    if sys.version.split()[0] != runtime["required_python_version"]:
        raise RuntimeError("Python version differs from preregistration")
    if torch.__version__ != runtime["required_torch_runtime_version"]:
        raise RuntimeError("PyTorch CUDA build identity differs from preregistration")
    if torch.version.cuda != runtime["required_torch_cuda_version"]:
        raise RuntimeError("PyTorch CUDA runtime differs from preregistration")

    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    torch.manual_seed(1729)
    torch.cuda.manual_seed_all(1729)
    if not torch.are_deterministic_algorithms_enabled():
        raise RuntimeError("PyTorch deterministic algorithms did not remain enabled")
    observed = {
        "PYTHONHASHSEED": os.environ["PYTHONHASHSEED"],
        "CUBLAS_WORKSPACE_CONFIG": os.environ["CUBLAS_WORKSPACE_CONFIG"],
        "torch_deterministic_algorithms": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cuda_matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
    }
    if observed != controls:
        raise RuntimeError("observed deterministic controls differ from preregistration")
    return observed


def _load_runtime_api() -> dict[str, object]:
    if str(WORKER_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKER_ROOT))
    from app.runtime.open_weight.artifacts import (
        CaptureVerificationContext,
        persist_capture_create_new,
        verify_capture_receipt,
    )
    from app.runtime.open_weight.engine import (
        InterventionSpec,
        RuntimeLoadConfig,
        capture_greedy_trajectory,
        load_open_weight_runtime,
    )
    from app.runtime.open_weight.identity import LocalModelSnapshot

    return {
        "CaptureVerificationContext": CaptureVerificationContext,
        "persist_capture_create_new": persist_capture_create_new,
        "verify_capture_receipt": verify_capture_receipt,
        "InterventionSpec": InterventionSpec,
        "RuntimeLoadConfig": RuntimeLoadConfig,
        "capture_greedy_trajectory": capture_greedy_trajectory,
        "load_open_weight_runtime": load_open_weight_runtime,
        "LocalModelSnapshot": LocalModelSnapshot,
    }


def _verify_loaded_runtime_preregistration(
    runtime: object, preregistration: Mapping[str, object]
) -> None:
    model = preregistration["experiment"]["model"]
    attestation = runtime.initial_attestation.to_dict()
    for key in ("model_id", "revision", "tree_manifest_sha256"):
        if attestation.get(key) != model[key]:
            raise RuntimeError(f"loaded model {key} differs from preregistration")
    observed_files = {
        row["relative_path"]: (row["byte_count"], row["sha256"])
        for row in attestation["files"]
    }
    expected_files = {
        row["relative_path"]: (row["byte_count"], row["sha256"])
        for row in model["files"]
    }
    if observed_files != expected_files:
        raise RuntimeError("loaded model file bytes differ from preregistration")
    dependencies = dict(runtime.dependency_versions)
    if dependencies != preregistration["experiment"]["runtime"][
        "required_dependency_versions"
    ]:
        raise RuntimeError("loaded runtime dependencies differ from preregistration")


def _intervention_for_schedule(
    intervention_type: object,
    preregistration: Mapping[str, object],
    schedule_row: Mapping[str, object],
) -> object:
    condition = schedule_row["condition"]
    if condition == "baseline":
        return intervention_type()
    frozen = preregistration["experiment"]["intervention"]
    return intervention_type(
        mode=condition,
        layer_index=frozen["target_layer_index"],
        active_steps=tuple(frozen["active_steps"]),
        max_vector_norm=0.0,
    )


def _create_result_manifest(
    bundle_root: Path, preregistration: Mapping[str, object]
) -> dict[str, object]:
    _captures, capture_links, evaluation = _recompute_capture_set(
        bundle_root, preregistration
    )
    unsigned = {
        "schema_version": RESULT_SCHEMA,
        "status": _status_from_evaluation(evaluation),
        "packet_eligibility": PACKET_STATUS,
        "scientific_status": SCIENTIFIC_STATUS,
        "claim_boundary": CANARY_CLAIM_BOUNDARY,
        "preregistration_sha256": preregistration["preregistration_sha256"],
        "captures": capture_links,
        "evaluation": evaluation,
        "evidence_files": _file_manifest(
            bundle_root, exclude={"canary.result.json"}
        ),
        "external_anchor": {
            "status": EXTERNAL_ANCHOR_STATUS,
            "anchor_uri": None,
            "anchor_receipt_sha256": None,
            "claim_boundary": ANCHOR_CLAIM_BOUNDARY,
        },
    }
    result = dict(unsigned)
    result["result_manifest_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    _write_create_new(bundle_root / "canary.result.json", canonical_json_bytes(result))
    return result


def _recompute_capture_set(
    bundle_root: Path, preregistration: Mapping[str, object]
) -> tuple[list[CaptureEvidence], list[dict[str, object]], dict[str, object]]:
    captures: list[CaptureEvidence] = []
    for schedule_row in preregistration["experiment"]["schedule"]:
        captures.append(
            _load_capture_evidence(bundle_root, preregistration, schedule_row)
        )
    capture_links = [
        {
            "ordinal": index + 1,
            "capture_id": capture.capture_id,
            "condition": capture.condition,
            "repetition": capture.repetition,
            "receipt_path": f"captures/{capture.capture_id}/capture.receipt.json",
            "receipt_byte_count": capture.receipt_identity["byte_count"],
            "receipt_file_sha256": capture.receipt_identity["sha256"],
            "receipt_self_sha256": capture.receipt["receipt_sha256"],
            "tensor_path": f"captures/{capture.capture_id}/capture.safetensors",
            "tensor_byte_count": capture.tensor_identity["byte_count"],
            "tensor_sha256": capture.tensor_identity["sha256"],
            "adapter_plan_path": f"captures/{capture.capture_id}/capture.adapter-plan.json",
            "adapter_plan_byte_count": capture.plan_identity["byte_count"],
            "adapter_plan_sha256": capture.plan_identity["sha256"],
            "execution_nonce": capture.receipt["observation"]["execution_record"][
                "execution_nonce"
            ],
        }
        for index, capture in enumerate(captures)
    ]
    evaluation = _evaluate_captures(captures, preregistration)
    return captures, capture_links, evaluation


def _load_capture_evidence(
    bundle_root: Path,
    preregistration: Mapping[str, object],
    schedule_row: Mapping[str, object],
) -> CaptureEvidence:
    capture_id = schedule_row["capture_id"]
    if not isinstance(capture_id, str) or not _CAPTURE_ID.fullmatch(capture_id):
        raise ValueError("capture_id is not canonical")
    directory = bundle_root / "captures" / capture_id
    receipt_path = directory / "capture.receipt.json"
    tensor_path = directory / "capture.safetensors"
    plan_path = directory / "capture.adapter-plan.json"
    receipt_raw = _read_plain_file(receipt_path, max_bytes=_MAX_JSON_BYTES)
    tensor_raw = _read_plain_file(tensor_path, max_bytes=_MAX_TENSOR_BYTES)
    plan_raw = _read_plain_file(plan_path, max_bytes=16 * 1024 * 1024)
    receipt = strict_json_object(receipt_raw, f"capture receipt {capture_id}")
    plan = strict_json_object(plan_raw, f"adapter plan {capture_id}")

    _verify_portable_receipt(
        receipt,
        receipt_path=receipt_path,
        receipt_raw=receipt_raw,
        tensor_raw=tensor_raw,
        plan_raw=plan_raw,
        plan=plan,
        preregistration=preregistration,
        schedule_row=schedule_row,
    )
    try:
        from safetensors.numpy import load
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(f"portable safetensors reader unavailable: {exc}") from exc
    arrays = load(tensor_raw)
    _verify_portable_arrays(arrays, receipt, preregistration)
    return CaptureEvidence(
        capture_id=capture_id,
        condition=schedule_row["condition"],
        repetition=schedule_row["repetition"],
        receipt=receipt,
        arrays=arrays,
        receipt_identity=_identity_from_bytes(receipt_raw),
        tensor_identity=_identity_from_bytes(tensor_raw),
        plan_identity=_identity_from_bytes(plan_raw),
    )


def _verify_portable_receipt(
    receipt: Mapping[str, object],
    *,
    receipt_path: Path,
    receipt_raw: bytes,
    tensor_raw: bytes,
    plan_raw: bytes,
    plan: Mapping[str, object],
    preregistration: Mapping[str, object],
    schedule_row: Mapping[str, object],
) -> None:
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "input",
        "output",
        "observation",
        "claim_boundary",
        "receipt_sha256",
    }
    if set(receipt) != required:
        raise ValueError("capture receipt keyset mismatch")
    _require_literal(receipt, "schema_version", RECEIPT_SCHEMA)
    _require_literal(receipt, "status", CAPTURE_STATUS)
    _require_literal(receipt, "packet_eligibility", PACKET_STATUS)
    _require_literal(receipt, "scientific_status", CAPTURE_SCIENTIFIC_STATUS)
    _require_literal(receipt, "claim_boundary", RECEIPT_CLAIM_BOUNDARY)
    self_hash = _required_upper_sha256(receipt, "receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    if sha256_bytes(canonical_json_bytes(unsigned)) != self_hash:
        raise ValueError("capture receipt self-hash mismatch")

    scenario = preregistration["experiment"]["scenario"]
    input_row = _required_mapping(receipt, "input")
    if input_row != {
        "scenario_id": scenario["scenario_id"],
        "prompt": scenario["prompt"],
        "prompt_sha256": scenario["prompt_sha256"],
    }:
        raise ValueError("capture input differs from preregistration")
    output = _required_mapping(receipt, "output")
    if set(output) != {
        "generated_text",
        "tensor_path",
        "tensor_byte_count",
        "tensor_sha256",
        "adapter_plan_path",
        "adapter_plan_byte_count",
        "adapter_plan_file_sha256",
        "array_manifest",
    }:
        raise ValueError("capture output keyset mismatch")
    if output.get("tensor_path") != "capture.safetensors":
        raise ValueError("capture tensor path is not portable/canonical")
    if output.get("adapter_plan_path") != "capture.adapter-plan.json":
        raise ValueError("capture adapter plan path is not portable/canonical")
    if _required_int(output, "tensor_byte_count") != len(tensor_raw):
        raise ValueError("capture tensor byte count mismatch")
    if _required_upper_sha256(output, "tensor_sha256") != sha256_bytes(tensor_raw):
        raise ValueError("capture tensor hash mismatch")
    if _required_int(output, "adapter_plan_byte_count") != len(plan_raw):
        raise ValueError("capture adapter plan byte count mismatch")
    if _required_upper_sha256(
        output, "adapter_plan_file_sha256"
    ) != sha256_bytes(plan_raw):
        raise ValueError("capture adapter plan file hash mismatch")

    _verify_portable_adapter_plan(plan, preregistration)
    observation = _required_mapping(receipt, "observation")
    _verify_portable_observation(observation, preregistration, schedule_row)
    adapter = _required_mapping(observation, "adapter")
    if adapter.get("adapter_plan_sha256") != plan["plan_sha256"]:
        raise ValueError("receipt adapter plan identity differs from saved plan")
    if adapter.get("adapter_plan_file_sha256") != sha256_bytes(plan_raw):
        raise ValueError("receipt adapter plan file identity differs from saved plan")
    _require_literal(adapter, "binding_status", ADAPTER_BINDING_STATUS)
    _require_literal(adapter, "claim_boundary", ADAPTER_CLAIM_BOUNDARY)
    _required_upper_sha256(adapter, "adapter_source_sha256")
    snapshot = _required_mapping(observation, "model_snapshot")
    plan_identity = _required_mapping(plan, "identity")
    if plan_identity.get("config_sha256") != snapshot.get("config_sha256"):
        raise ValueError("adapter plan config identity differs from model snapshot")
    if plan_identity.get("weights_manifest_sha256") != snapshot.get(
        "weights_manifest_sha256"
    ):
        raise ValueError("adapter plan weight identity differs from model snapshot")
    generated_text = output.get("generated_text")
    if not isinstance(generated_text, str):
        raise ValueError("capture generated_text must be text")
    record = _required_mapping(observation, "execution_record")
    if record["generated_text_sha256"] != sha256_bytes(
        generated_text.encode("utf-8")
    ):
        raise ValueError("execution-record generated-text hash mismatch")
    _verify_tensor_header(
        tensor_raw,
        observation=observation,
        plan=plan,
        preregistration=preregistration,
    )
    if receipt_path.name != "capture.receipt.json":
        raise ValueError("capture receipt basename mismatch")
    if canonical_json_bytes(receipt) != receipt_raw:
        raise ValueError("capture receipt is not canonical JSON bytes")


def _verify_portable_adapter_plan(
    plan: Mapping[str, object], preregistration: Mapping[str, object]
) -> None:
    if set(plan) != {
        "schema_version",
        "identity",
        "declaration",
        "discovery",
        "runtime_verification",
        "capabilities",
        "claim_boundary",
        "plan_sha256",
    }:
        raise ValueError("adapter plan keyset mismatch")
    plan_hash = _required_upper_sha256(plan, "plan_sha256")
    unsigned = dict(plan)
    unsigned.pop("plan_sha256")
    if sha256_bytes(canonical_json_bytes(unsigned)) != plan_hash:
        raise ValueError("adapter plan self-hash mismatch")
    _require_literal(
        plan, "schema_version", "cas_harness_interpretability_adapter_plan.v1"
    )
    _require_literal(plan, "runtime_verification", None)
    _require_literal(plan, "claim_boundary", ADAPTER_PLAN_CLAIM_BOUNDARY)
    model = preregistration["experiment"]["model"]
    identity = _required_mapping(plan, "identity")
    if identity.get("model_id") != model["model_id"] or identity.get(
        "revision"
    ) != model["revision"]:
        raise ValueError("adapter plan model identity mismatch")
    if identity.get("trust_remote_code") is not False:
        raise ValueError("adapter plan trust_remote_code must remain false")
    config_sha256 = next(
        row["sha256"]
        for row in model["files"]
        if row["relative_path"] == "config.json"
    )
    if identity.get("config_sha256") != config_sha256:
        raise ValueError("adapter plan config hash differs from preregistration")
    _required_upper_sha256(identity, "weights_manifest_sha256")
    declaration = _required_mapping(plan, "declaration")
    if declaration != {
        "model_type": "gpt_neox",
        "num_hidden_layers": 12,
        "hidden_size": 768,
        "num_attention_heads": 12,
    }:
        raise ValueError("adapter plan architecture declaration mismatch")
    discovery = _required_mapping(plan, "discovery")
    if discovery.get("status") != "STRUCTURE_VERIFIED":
        raise ValueError("adapter plan architecture is not structure-verified")
    if discovery.get("family") != "gpt_neox":
        raise ValueError("adapter plan family mismatch")
    if discovery.get("observed_layer_count") != 12:
        raise ValueError("adapter plan observed layer count mismatch")
    hooks = discovery.get("layer_hooks")
    if not isinstance(hooks, list) or len(hooks) != 12:
        raise ValueError("adapter plan must expose twelve layer hooks")
    if [row.get("layer_index") for row in hooks if isinstance(row, Mapping)] != list(
        range(12)
    ):
        raise ValueError("adapter plan layer indices mismatch")
    for index, row in enumerate(hooks):
        if not isinstance(row, Mapping) or row.get("residual_module") != (
            f"gpt_neox.layers.{index}"
        ):
            raise ValueError("adapter plan residual hook path mismatch")
        if row.get("mlp_module") != f"gpt_neox.layers.{index}.mlp":
            raise ValueError("adapter plan MLP hook path mismatch")
        if row.get("attention_module") != f"gpt_neox.layers.{index}.attention":
            raise ValueError("adapter plan attention hook path mismatch")
    capabilities = plan.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 14:
        raise ValueError("adapter plan must contain all fourteen capabilities")
    if [row.get("capability_id") for row in capabilities if isinstance(row, Mapping)] != [
        f"C{index:02d}" for index in range(1, 15)
    ]:
        raise ValueError("adapter plan capability identities mismatch")
    if any(
        not isinstance(row, Mapping) or row.get("evidence_status") != "NOT_RUN"
        for row in capabilities
    ):
        raise ValueError("adapter plan capability evidence must remain NOT_RUN")


def _verify_portable_observation(
    observation: Mapping[str, object],
    preregistration: Mapping[str, object],
    schedule_row: Mapping[str, object],
) -> None:
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "scenario_id",
        "prompt_sha256",
        "seed",
        "generation",
        "capture_contract",
        "intervention",
        "model_snapshot",
        "loaded_weight_value_manifest_sha256",
        "tokenizer_canary",
        "adapter",
        "dependencies",
        "runtime",
        "claim_boundary",
        "execution_record",
        "scenario_source",
    }
    if set(observation) != required:
        raise ValueError("capture observation keyset mismatch")
    scenario = preregistration["experiment"]["scenario"]
    generation = preregistration["experiment"]["generation"]
    _require_literal(
        observation, "schema_version", "cas_open_weight_trajectory_capture.v1"
    )
    _require_literal(observation, "status", CAPTURE_STATUS)
    _require_literal(observation, "packet_eligibility", PACKET_STATUS)
    _require_literal(observation, "scientific_status", CAPTURE_SCIENTIFIC_STATUS)
    _require_literal(observation, "scenario_id", scenario["scenario_id"])
    _require_literal(observation, "prompt_sha256", scenario["prompt_sha256"])
    _require_literal(observation, "seed", generation["seed"])
    _require_literal(observation, "claim_boundary", OBSERVATION_CLAIM_BOUNDARY)
    _required_upper_sha256(observation, "loaded_weight_value_manifest_sha256")
    if not isinstance(observation.get("tokenizer_canary"), Mapping):
        raise ValueError("capture tokenizer canary is missing")
    if observation.get("generation") != {
        "method": "manual_greedy_argmax",
        "max_new_tokens": 2,
        "temperature": None,
        "sampling": False,
    }:
        raise ValueError("capture generation observation mismatch")
    expected_intervention = _expected_intervention_observation(
        preregistration, schedule_row["condition"]
    )
    if observation.get("intervention") != expected_intervention:
        raise ValueError("capture intervention observation mismatch")

    model = preregistration["experiment"]["model"]
    snapshot = _required_mapping(observation, "model_snapshot")
    for key in ("model_id", "revision", "tree_manifest_sha256"):
        if snapshot.get(key) != model[key]:
            raise ValueError(f"capture model snapshot {key} mismatch")
    observed_files = {
        row.get("relative_path"): (row.get("byte_count"), row.get("sha256"))
        for row in snapshot.get("files", [])
        if isinstance(row, Mapping)
    }
    expected_files = {
        row["relative_path"]: (row["byte_count"], row["sha256"])
        for row in model["files"]
    }
    if observed_files != expected_files:
        raise ValueError("capture model file manifest mismatch")

    runtime = _required_mapping(observation, "runtime")
    frozen_runtime = preregistration["experiment"]["runtime"]
    if runtime.get("python") != frozen_runtime["required_python_version"]:
        raise ValueError("capture Python version mismatch")
    if runtime.get("device") != frozen_runtime["required_device"]:
        raise ValueError("capture runtime device mismatch")
    if runtime.get("dtype_request") != "auto":
        raise ValueError("capture dtype request mismatch")
    if runtime.get("torch_deterministic_algorithms_enabled") is not True:
        raise ValueError("capture deterministic-algorithms flag is false")
    hardware = _required_mapping(runtime, "hardware")
    if hardware.get("requested_device") != frozen_runtime["required_device"]:
        raise ValueError("capture hardware requested-device mismatch")
    if hardware.get("cuda_available") is not True:
        raise ValueError("capture hardware reports CUDA unavailable")
    if hardware.get("device_name") != frozen_runtime["required_device_name"]:
        raise ValueError("capture device name mismatch")
    if hardware.get("device_capability") != frozen_runtime[
        "required_device_capability"
    ]:
        raise ValueError("capture device capability mismatch")
    if observation.get("dependencies") != frozen_runtime[
        "required_dependency_versions"
    ]:
        raise ValueError("capture dependency versions mismatch")
    if hardware.get("torch_cuda_version") != frozen_runtime[
        "required_torch_cuda_version"
    ]:
        raise ValueError("capture CUDA runtime version mismatch")
    source_manifest = runtime.get("source_manifest")
    if not isinstance(source_manifest, list) or not source_manifest:
        raise ValueError("capture runtime source manifest is empty")
    for row in source_manifest:
        if not isinstance(row, Mapping) or set(row) != {
            "path",
            "byte_count",
            "sha256",
        }:
            raise ValueError("capture runtime source row mismatch")
        _required_text(row, "path")
        if _required_int(row, "byte_count") <= 0:
            raise ValueError("capture runtime source byte count is invalid")
        _required_upper_sha256(row, "sha256")
    for key in ("callable_manifest", "tokenizer_callable_manifest"):
        rows = runtime.get(key)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"capture {key} is empty")

    scenario_source = _required_mapping(observation, "scenario_source")
    expected_scenario_raw = canonical_json_bytes(
        {
            "schema_version": SCENARIO_SCHEMA,
            "scenario_id": scenario["scenario_id"],
            "prompt": scenario["prompt"],
        }
    )
    if scenario_source.get("byte_count") != len(expected_scenario_raw):
        raise ValueError("capture scenario-source byte count mismatch")
    if scenario_source.get("sha256") != sha256_bytes(expected_scenario_raw):
        raise ValueError("capture scenario-source hash mismatch")
    if scenario_source.get("snapshot_semantics") != (
        "one immutable byte snapshot strict-parsed and hashed"
    ):
        raise ValueError("capture scenario-source semantics mismatch")
    if Path(_required_text(scenario_source, "path")).name != "scenario.json":
        raise ValueError("capture scenario-source basename mismatch")

    record = _required_mapping(observation, "execution_record")
    _verify_execution_record(record, observation, preregistration, schedule_row)


def _verify_execution_record(
    record: Mapping[str, object],
    observation: Mapping[str, object],
    preregistration: Mapping[str, object],
    schedule_row: Mapping[str, object],
) -> None:
    required = {
        "schema_version",
        "execution_nonce",
        "scenario_id",
        "prompt_sha256",
        "generated_text_sha256",
        "intervention",
        "residual_hook_invocations",
        "mlp_hook_invocations",
        "intervention_hook_invocations",
        "array_manifest_sha256",
        "observation_without_execution_record_sha256",
        "model_tree_manifest_sha256",
        "adapter_plan_sha256",
        "runtime_source_manifest_sha256",
        "hook_state_before",
        "hook_state_after",
        "claim_boundary",
        "started_utc",
        "ended_utc",
        "started_monotonic_ns",
        "ended_monotonic_ns",
        "model_forward_calls",
        "execution_hmac_sha256",
    }
    if set(record) != required:
        raise ValueError("capture execution-record keyset mismatch")
    _require_literal(
        record, "schema_version", "cas_open_weight_engine_execution_record.v1"
    )
    _required_upper_sha256(record, "execution_nonce")
    _required_upper_sha256(record, "generated_text_sha256")
    _required_upper_sha256(record, "array_manifest_sha256")
    _required_upper_sha256(record, "observation_without_execution_record_sha256")
    _required_upper_sha256(record, "model_tree_manifest_sha256")
    _required_upper_sha256(record, "adapter_plan_sha256")
    _required_upper_sha256(record, "runtime_source_manifest_sha256")
    _required_upper_sha256(record, "execution_hmac_sha256")
    _require_literal(record, "hook_state_before", "CLEAN")
    _require_literal(record, "hook_state_after", "CLEAN")
    _require_literal(record, "claim_boundary", ENGINE_RECORD_CLAIM_BOUNDARY)
    _require_literal(record, "model_forward_calls", 2)
    scenario = preregistration["experiment"]["scenario"]
    _require_literal(record, "scenario_id", scenario["scenario_id"])
    _require_literal(record, "prompt_sha256", scenario["prompt_sha256"])
    _require_literal(
        record,
        "model_tree_manifest_sha256",
        preregistration["experiment"]["model"]["tree_manifest_sha256"],
    )
    if record.get("intervention") != _expected_intervention_observation(
        preregistration, schedule_row["condition"]
    ):
        raise ValueError("execution-record intervention mismatch")
    expected_layer_calls = {
        str(step): {str(layer): 1 for layer in range(12)} for step in range(2)
    }
    if record.get("residual_hook_invocations") != expected_layer_calls:
        raise ValueError("execution-record residual hook counts mismatch")
    if record.get("mlp_hook_invocations") != expected_layer_calls:
        raise ValueError("execution-record MLP hook counts mismatch")
    expected_intervention_calls = {
        str(step): 0 if schedule_row["condition"] == "baseline" else 1
        for step in range(2)
    }
    if record.get("intervention_hook_invocations") != expected_intervention_calls:
        raise ValueError("execution-record intervention hook counts mismatch")
    started_ns = _required_int(record, "started_monotonic_ns")
    ended_ns = _required_int(record, "ended_monotonic_ns")
    if ended_ns < started_ns:
        raise ValueError("execution-record monotonic chronology mismatch")
    if _parse_utc(_required_text(record, "ended_utc")) < _parse_utc(
        _required_text(record, "started_utc")
    ):
        raise ValueError("execution-record UTC chronology mismatch")
    without_record = dict(observation)
    without_record.pop("execution_record", None)
    if record["observation_without_execution_record_sha256"] != sha256_bytes(
        canonical_json_bytes(without_record)
    ):
        raise ValueError("execution-record observation hash mismatch")
    source_manifest = observation["runtime"]["source_manifest"]
    if record["runtime_source_manifest_sha256"] != sha256_bytes(
        canonical_json_bytes(source_manifest)
    ):
        raise ValueError("execution-record runtime source hash mismatch")
    if record["adapter_plan_sha256"] != observation["adapter"][
        "adapter_plan_sha256"
    ]:
        raise ValueError("execution-record adapter plan hash mismatch")


def _verify_tensor_header(
    raw: bytes,
    *,
    observation: Mapping[str, object],
    plan: Mapping[str, object],
    preregistration: Mapping[str, object],
) -> None:
    if len(raw) < 9:
        raise ValueError("safetensors artifact is too short")
    header_length = int.from_bytes(raw[:8], "little", signed=False)
    if header_length <= 0 or 8 + header_length > len(raw):
        raise ValueError("safetensors header length is invalid")
    header = strict_json_object(raw[8 : 8 + header_length], "safetensors header")
    if set(header) - {"__metadata__"} != set(_ARRAY_NAMES):
        raise ValueError("safetensors tensor keyset mismatch")
    metadata = _required_mapping(header, "__metadata__")
    expected = {
        "schema_version": TENSOR_SCHEMA,
        "scenario_id": preregistration["experiment"]["scenario"]["scenario_id"],
        "prompt_sha256": preregistration["experiment"]["scenario"]["prompt_sha256"],
        "model_tree_manifest_sha256": preregistration["experiment"]["model"][
            "tree_manifest_sha256"
        ],
        "loaded_weight_value_manifest_sha256": observation[
            "loaded_weight_value_manifest_sha256"
        ],
        "adapter_plan_sha256": plan["plan_sha256"],
        "packet_eligibility": PACKET_STATUS,
    }
    if metadata != expected:
        raise ValueError("safetensors metadata differs from receipt/preregistration")


def _verify_portable_arrays(
    arrays: Mapping[str, np.ndarray],
    receipt: Mapping[str, object],
    preregistration: Mapping[str, object],
) -> None:
    if set(arrays) != set(_ARRAY_NAMES):
        raise ValueError("capture tensor array keyset mismatch")
    manifest = _array_manifest(arrays)
    output = receipt["output"]
    if manifest != output["array_manifest"]:
        raise ValueError("capture array manifest mismatch")
    record = receipt["observation"]["execution_record"]
    if sha256_bytes(canonical_json_bytes(manifest)) != record[
        "array_manifest_sha256"
    ]:
        raise ValueError("capture arrays differ from execution-record hash")
    expected = preregistration["experiment"]["expected_arrays"]
    for name, shape in expected.items():
        if list(arrays[name].shape) != shape:
            raise ValueError(f"capture {name} shape mismatch")
    if arrays["prompt_input_ids"].dtype != np.int64:
        raise ValueError("prompt_input_ids dtype mismatch")
    if arrays["prompt_attention_mask"].dtype != np.int64:
        raise ValueError("prompt_attention_mask dtype mismatch")
    if arrays["generated_token_ids"].dtype != np.int64:
        raise ValueError("generated_token_ids dtype mismatch")
    if arrays["input_lengths"].dtype != np.int64:
        raise ValueError("input_lengths dtype mismatch")
    for name in ("residual_states", "mlp_states", "pre_selection_logits"):
        if arrays[name].dtype != np.float32 or not np.isfinite(arrays[name]).all():
            raise ValueError(f"capture {name} dtype/finiteness mismatch")
    prompt_ids = arrays["prompt_input_ids"]
    mask = arrays["prompt_attention_mask"]
    if prompt_ids.ndim != 2 or prompt_ids.shape[0] != 1 or prompt_ids.shape[1] < 1:
        raise ValueError("capture prompt input shape mismatch")
    if mask.shape != prompt_ids.shape or not np.isin(mask, (0, 1)).all():
        raise ValueError("capture attention-mask shape/value mismatch")
    expected_lengths = np.arange(
        prompt_ids.shape[1], prompt_ids.shape[1] + 2, dtype=np.int64
    )
    if not np.array_equal(arrays["input_lengths"], expected_lengths):
        raise ValueError("capture input lengths mismatch")
    logits = arrays["pre_selection_logits"]
    tokens = arrays["generated_token_ids"]
    if not np.array_equal(tokens, np.argmax(logits, axis=1).astype(np.int64)):
        raise ValueError("capture generated tokens are not greedy logit argmax")
    if (tokens < 0).any() or (tokens >= 50304).any():
        raise ValueError("capture generated token is outside the frozen vocabulary")
    capture_contract = receipt["observation"].get("capture_contract")
    expected_contract = {
        "residual": "full_width_last_current_token_for_every_decoder_layer",
        "mlp": "full_width_last_current_token_for_every_decoder_layer",
        "logits": "full_vocabulary_pre_selection_each_generation_step",
        "attention": "NOT_CAPTURED_IN_V1",
        "shapes": {name: list(value.shape) for name, value in arrays.items()},
    }
    if capture_contract != expected_contract:
        raise ValueError("capture contract differs from saved tensor arrays")


def _evaluate_captures(
    captures: Sequence[CaptureEvidence], preregistration: Mapping[str, object]
) -> dict[str, object]:
    by_condition = {
        condition: sorted(
            (capture for capture in captures if capture.condition == condition),
            key=lambda capture: capture.repetition,
        )
        for condition in ("baseline", "noop", "zero")
    }
    criteria: list[dict[str, object]] = []

    def add(identifier: str, passed: bool, summary: str, evidence: object) -> None:
        criteria.append(
            {
                "criterion_id": identifier,
                "required": True,
                "status": "PASS" if passed else "FAIL",
                "summary": summary,
                "evidence": evidence,
            }
        )

    exact_schedule = [
        (capture.capture_id, capture.condition, capture.repetition)
        for capture in captures
    ] == [
        (row["capture_id"], row["condition"], row["repetition"])
        for row in expected_schedule()
    ]
    add(
        "C01_EXACT_NINE_CAPTURE_SCHEDULE",
        exact_schedule,
        "Exactly baseline/noop/zero x3 in the frozen interleaved order.",
        {"capture_count": len(captures)},
    )

    common_rows = [
        {
            "input": capture.receipt["input"],
            "model_snapshot": capture.receipt["observation"]["model_snapshot"],
            "loaded_weight_value_manifest_sha256": capture.receipt["observation"][
                "loaded_weight_value_manifest_sha256"
            ],
            "adapter": capture.receipt["observation"]["adapter"],
            "dependencies": capture.receipt["observation"]["dependencies"],
            "runtime": capture.receipt["observation"]["runtime"],
            "tokenizer_canary": capture.receipt["observation"]["tokenizer_canary"],
            "scenario_source": capture.receipt["observation"]["scenario_source"],
            "generation": capture.receipt["observation"]["generation"],
            "seed": capture.receipt["observation"]["seed"],
        }
        for capture in captures
    ]
    common_metadata = bool(common_rows) and all(
        row == common_rows[0] for row in common_rows[1:]
    )
    common_prompt_arrays = bool(captures) and all(
        np.array_equal(
            capture.arrays["prompt_input_ids"],
            captures[0].arrays["prompt_input_ids"],
        )
        and np.array_equal(
            capture.arrays["prompt_attention_mask"],
            captures[0].arrays["prompt_attention_mask"],
        )
        for capture in captures[1:]
    )
    common_identity = common_metadata and common_prompt_arrays
    add(
        "C02_SAME_INPUT_MODEL_RUNTIME_SEED",
        common_identity,
        "All nine captures bind the exact same input, model, adapter, runtime, and seed.",
        {
            "common_identity_sha256": sha256_bytes(
                canonical_json_bytes(common_rows[0])
            ),
            "prompt_token_arrays_identical": common_prompt_arrays,
        },
    )

    nonces = [
        capture.receipt["observation"]["execution_record"]["execution_nonce"]
        for capture in captures
    ]
    chronology = True
    for previous, current in zip(captures, captures[1:]):
        before = previous.receipt["observation"]["execution_record"]
        after = current.receipt["observation"]["execution_record"]
        if after["started_monotonic_ns"] < before["ended_monotonic_ns"]:
            chronology = False
        if _parse_utc(after["started_utc"]) < _parse_utc(before["ended_utc"]):
            chronology = False
    nonce_chronology = len(set(nonces)) == 9 and chronology
    add(
        "C03_UNIQUE_NONCES_AND_SERIAL_CHRONOLOGY",
        nonce_chronology,
        "All execution nonces are unique and captures are serially ordered.",
        {"unique_nonce_count": len(set(nonces)), "serial_chronology": chronology},
    )

    baseline_repeat = _all_arrays_equal(by_condition["baseline"])
    noop_repeat = _all_arrays_equal(by_condition["noop"])
    zero_repeat = _all_arrays_equal(by_condition["zero"])
    add(
        "C04_BASELINE_REPEATS_BYTE_IDENTICAL",
        baseline_repeat,
        "All seven saved baseline arrays repeat exactly.",
        _array_hashes(by_condition["baseline"][0]),
    )
    add(
        "C05_NOOP_REPEATS_BYTE_IDENTICAL",
        noop_repeat,
        "All seven saved noop arrays repeat exactly.",
        _array_hashes(by_condition["noop"][0]),
    )
    add(
        "C06_ZERO_REPEATS_BYTE_IDENTICAL",
        zero_repeat,
        "All seven saved zero-intervention arrays repeat exactly.",
        _array_hashes(by_condition["zero"][0]),
    )
    baseline_noop_equal = all(
        _capture_arrays_equal(baseline, noop)
        for baseline in by_condition["baseline"]
        for noop in by_condition["noop"]
    )
    baseline_noop_text_equal = len(
        {
            capture.receipt["output"]["generated_text"]
            for capture in (*by_condition["baseline"], *by_condition["noop"])
        }
    ) == 1
    add(
        "C07_BASELINE_NOOP_BYTE_IDENTITY",
        baseline_noop_equal and baseline_noop_text_equal,
        "Every baseline/noop tensor array and generated text are exactly identical.",
        {
            "arrays_byte_identical": baseline_noop_equal,
            "generated_text_identical": baseline_noop_text_equal,
        },
    )

    target = preregistration["experiment"]["intervention"]["target_layer_index"]
    baseline_vectors = [
        capture.arrays["residual_states"][0, target, :]
        for capture in by_condition["baseline"]
    ]
    zero_vectors = [
        capture.arrays["residual_states"][0, target, :]
        for capture in by_condition["zero"]
    ]
    baseline_nonzero = all(np.any(vector != 0) for vector in baseline_vectors)
    zero_exact = all(np.all(vector == 0) for vector in zero_vectors)
    add(
        "C08_BASELINE_TARGET_NONZERO",
        baseline_nonzero,
        "The baseline target vector is not the all-zero vector in every repeat.",
        {
            "target_layer_index": target,
            "minimum_nonzero_count": min(
                int(np.count_nonzero(vector)) for vector in baseline_vectors
            ),
        },
    )
    add(
        "C09_ZERO_TARGET_EXACTLY_ZERO",
        zero_exact,
        "The registered active-step target vector is exactly zero in every repeat.",
        {
            "target_layer_index": target,
            "active_step": 0,
            "maximum_nonzero_count": max(
                int(np.count_nonzero(vector)) for vector in zero_vectors
            ),
        },
    )

    upstream_equal = True
    downstream_changed = True
    residual_max_deltas: list[float] = []
    logit_max_deltas: list[float] = []
    for baseline, zero in zip(by_condition["baseline"], by_condition["zero"]):
        upstream_equal = upstream_equal and np.array_equal(
            baseline.arrays["residual_states"][0, :target, :],
            zero.arrays["residual_states"][0, :target, :],
        )
        residual_delta = _maximum_absolute_delta(
            baseline.arrays["residual_states"][0, target + 1 :, :],
            zero.arrays["residual_states"][0, target + 1 :, :],
        )
        logit_delta = _maximum_absolute_delta(
            baseline.arrays["pre_selection_logits"][0, :],
            zero.arrays["pre_selection_logits"][0, :],
        )
        residual_max_deltas.append(residual_delta)
        logit_max_deltas.append(logit_delta)
        downstream_changed = downstream_changed and (
            residual_delta > 0.0 or logit_delta > 0.0
        )
    add(
        "C10_UPSTREAM_MATCHED_AND_DOWNSTREAM_EFFECT",
        upstream_equal and downstream_changed,
        "Step-0 upstream residuals match while a later residual or logit changes in every pair.",
        {
            "upstream_exactly_equal": upstream_equal,
            "downstream_effect_in_every_pair": downstream_changed,
            "downstream_residual_max_abs_delta_by_repeat": residual_max_deltas,
            "logit_max_abs_delta_by_repeat": logit_max_deltas,
        },
    )

    liveness_rows: list[dict[str, object]] = []
    liveness_pass = True
    for capture in captures:
        array_status: dict[str, bool] = {}
        for name in ("residual_states", "mlp_states", "pre_selection_logits"):
            array = capture.arrays[name]
            live = bool(
                array.size > 1
                and np.isfinite(array).all()
                and np.any(array != 0)
                and np.any(array != array.reshape(-1)[0])
            )
            array_status[name] = live
            liveness_pass = liveness_pass and live
        liveness_rows.append(
            {"capture_id": capture.capture_id, "arrays_live": array_status}
        )
    add(
        "C11_CAPTURE_LIVENESS",
        liveness_pass,
        "Every residual, MLP, and logit capture is finite, nonzero, and nonconstant.",
        liveness_rows,
    )

    generated_change = [
        not np.array_equal(
            baseline.arrays["generated_token_ids"],
            zero.arrays["generated_token_ids"],
        )
        or baseline.receipt["output"]["generated_text"]
        != zero.receipt["output"]["generated_text"]
        for baseline, zero in zip(by_condition["baseline"], by_condition["zero"])
    ]
    return {
        "decision_rule": "ALL_REQUIRED_CRITERIA_MUST_PASS",
        "criteria": criteria,
        "required_pass_count": sum(
            1 for criterion in criteria if criterion["status"] == "PASS"
        ),
        "required_criterion_count": len(criteria),
        "informational_observations": {
            "generated_output_change_required": False,
            "generated_output_changed_by_repeat": generated_change,
            "later_step_equality_required_after_step0_intervention": False,
        },
    }


def _status_from_evaluation(evaluation: Mapping[str, object]) -> str:
    criteria = evaluation.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("evaluation criteria are missing")
    return (
        PASS_STATUS
        if all(
            isinstance(row, Mapping)
            and row.get("required") is True
            and row.get("status") == "PASS"
            for row in criteria
        )
        else FAIL_STATUS
    )


def _expected_intervention_observation(
    preregistration: Mapping[str, object], condition: str
) -> dict[str, object]:
    if condition == "baseline":
        return {
            "mode": "baseline",
            "layer_index": None,
            "active_steps": [],
            "vector_sha256": None,
            "vector_length": 0,
            "max_vector_norm": 0.0,
        }
    frozen = preregistration["experiment"]["intervention"]
    return {
        "mode": condition,
        "layer_index": frozen["target_layer_index"],
        "active_steps": frozen["active_steps"],
        "vector_sha256": None,
        "vector_length": 0,
        "max_vector_norm": 0.0,
    }


def _all_arrays_equal(captures: Sequence[CaptureEvidence]) -> bool:
    return len(captures) == 3 and all(
        _capture_arrays_equal(captures[0], capture) for capture in captures[1:]
    )


def _capture_arrays_equal(left: CaptureEvidence, right: CaptureEvidence) -> bool:
    return all(
        left.arrays[name].dtype == right.arrays[name].dtype
        and left.arrays[name].shape == right.arrays[name].shape
        and np.ascontiguousarray(left.arrays[name]).tobytes(order="C")
        == np.ascontiguousarray(right.arrays[name]).tobytes(order="C")
        for name in _ARRAY_NAMES
    )


def _array_hashes(capture: CaptureEvidence) -> dict[str, str]:
    return {
        name: sha256_bytes(np.ascontiguousarray(capture.arrays[name]).tobytes(order="C"))
        for name in _ARRAY_NAMES
    }


def _maximum_absolute_delta(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape or left.dtype != right.dtype:
        return math.inf
    if left.size == 0:
        return 0.0
    return float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))


def _array_manifest(arrays: Mapping[str, np.ndarray]) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "shape": list(arrays[name].shape),
            "dtype": str(arrays[name].dtype),
            "byte_count": int(arrays[name].nbytes),
            "value_sha256": sha256_bytes(
                np.ascontiguousarray(arrays[name]).tobytes(order="C")
            ),
        }
        for name in sorted(arrays)
    ]


def _verify_result_manifest_self_hash(result: Mapping[str, object]) -> None:
    expected = _required_upper_sha256(result, "result_manifest_sha256")
    unsigned = dict(result)
    unsigned.pop("result_manifest_sha256")
    if sha256_bytes(canonical_json_bytes(unsigned)) != expected:
        raise ValueError("result manifest self-hash mismatch")


def _verify_result_manifest_constants(
    result: Mapping[str, object], preregistration: Mapping[str, object]
) -> None:
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "claim_boundary",
        "preregistration_sha256",
        "captures",
        "evaluation",
        "evidence_files",
        "external_anchor",
        "result_manifest_sha256",
    }
    if set(result) != required:
        raise ValueError("result manifest keyset mismatch")
    _require_literal(result, "schema_version", RESULT_SCHEMA)
    if result.get("status") not in {PASS_STATUS, FAIL_STATUS}:
        raise ValueError("result manifest status vocabulary mismatch")
    _require_literal(result, "packet_eligibility", PACKET_STATUS)
    _require_literal(result, "scientific_status", SCIENTIFIC_STATUS)
    _require_literal(result, "claim_boundary", CANARY_CLAIM_BOUNDARY)
    _require_literal(
        result,
        "preregistration_sha256",
        preregistration["preregistration_sha256"],
    )
    if result.get("external_anchor") != {
        "status": EXTERNAL_ANCHOR_STATUS,
        "anchor_uri": None,
        "anchor_receipt_sha256": None,
        "claim_boundary": ANCHOR_CLAIM_BOUNDARY,
    }:
        raise ValueError("result manifest external-anchor boundary mismatch")


def _file_manifest(root: Path, *, exclude: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().encode("utf-8")):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in exclude:
            continue
        raw = _read_plain_file(path)
        rows.append(
            {
                "path": relative,
                "byte_count": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )
    return rows


def _identity_from_bytes(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": sha256_bytes(raw)}


def _write_error_manifest_if_possible(
    output_root: Path, *, preregistration_sha256: str, error: Exception
) -> None:
    path = output_root / "canary.error.json"
    if path.exists() or not output_root.is_dir():
        return
    unsigned = {
        "schema_version": ERROR_SCHEMA,
        "status": FAIL_STATUS,
        "packet_eligibility": PACKET_STATUS,
        "scientific_status": SCIENTIFIC_STATUS,
        "preregistration_sha256": preregistration_sha256,
        "error_type": type(error).__name__,
        "error": str(error),
        "external_anchor_status": EXTERNAL_ANCHOR_STATUS,
        "claim_boundary": CANARY_CLAIM_BOUNDARY,
    }
    value = dict(unsigned)
    value["error_manifest_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    try:
        _write_create_new(path, canonical_json_bytes(value))
    except Exception:
        return


def _require_new_absolute_directory_target(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("output_root must be absolute")
    path = path.resolve(strict=False)
    if path.exists() or path.is_symlink():
        raise FileExistsError("output_root must not already exist")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("output_root parent must be an existing plain directory")
    return path


def _write_create_new(path: Path, payload: bytes) -> None:
    with path.open("xb", buffering=0) as handle:
        offset = 0
        while offset < len(payload):
            written = handle.write(payload[offset:])
            if written is None or written <= 0:
                raise OSError(f"short write while creating {path}")
            offset += written
        handle.flush()
        os.fsync(handle.fileno())


def _read_plain_file(path: Path, *, max_bytes: int | None = None) -> bytes:
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"required plain file is missing: {path}")
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
        raise ValueError(f"required file must not be a link/reparse point: {path}")
    with path.open("rb", buffering=0) as handle:
        before = os.fstat(handle.fileno())
        if max_bytes is not None and before.st_size > max_bytes:
            raise ValueError(f"required file exceeds size cap: {path}")
        raw = handle.read()
        after = os.fstat(handle.fileno())
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or len(raw) != before.st_size:
        raise ValueError(f"required file changed while reading: {path}")
    return raw


def strict_json_object(raw: bytes, label: str) -> dict[str, object]:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key in {label}: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number in {label}: {value}")

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=pairs_hook,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _current_source_file_manifest_document() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for relative_path in FROZEN_SOURCE_RELATIVE_PATHS:
        path = REPOSITORY_ROOT.joinpath(*relative_path.split("/")).resolve(strict=True)
        if not path.is_file() or path.is_symlink() or _is_reparse(path.lstat()):
            raise RuntimeError(f"source path is not an exact plain file: {relative_path}")
        raw = _read_plain_file(path, max_bytes=8 * 1024 * 1024)
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )
    return {
        "schema_version": "cas_open_weight_canary_source_file_manifest.v1",
        "files": rows,
        "manifest_sha256": sha256_bytes(canonical_json_bytes(rows)),
    }


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ValueError(f"{key} must be an object")
    return item


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{key} must be non-empty text")
    return item


def _required_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"{key} must be an integer")
    return item


def _required_upper_sha256(value: Mapping[str, Any], key: str) -> str:
    item = _required_text(value, key)
    if not _UPPER_SHA256.fullmatch(item):
        raise ValueError(f"{key} must be uppercase SHA-256")
    return item


def _require_literal(value: Mapping[str, Any], key: str, expected: object) -> None:
    if value.get(key) != expected:
        raise ValueError(f"{key} literal mismatch")


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("UTC timestamp is malformed") from exc
    if parsed.tzinfo != timezone.utc:
        raise ValueError("timestamp must use UTC")
    return parsed


def _is_reparse(value: os.stat_result) -> bool:
    attributes = getattr(value, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)


if __name__ == "__main__":
    raise SystemExit(main())
