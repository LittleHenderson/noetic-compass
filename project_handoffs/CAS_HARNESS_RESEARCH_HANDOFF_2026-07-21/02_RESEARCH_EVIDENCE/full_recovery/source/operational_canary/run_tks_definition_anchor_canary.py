"""Run the bounded, permanently non-claim TKS definition-anchor GPU canary.

This is an execution-integrity check for the frozen 2026-07-21 diagnostic. It
captures four complete Stage-7 validation counterfactual pairs (eight prompts)
and all 84 D3/A124/compact definition prototypes at transformer blocks 0 and 1.
It does not calculate or license a scientific result.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable, Sequence

import numpy as np


CANARY_SCHEMA = "cas_harness_tks_definition_anchor_canary_receipt.v1"
CANARY_CLASS = "ZERO_SHOT_DEFINITION_ANCHOR_CAPTURE_CANARY"
CANARY_STATUS = "CANARY_PASS"
LICENSING_STATUS = "NOT_LICENSED_CANARY_ONLY"

MODEL_ID = "EleutherAI/pythia-160m"
MODEL_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
MODEL_PARAMETER_COUNT = 162_322_944
TORCH_DTYPE = "float16"
DEVICE_MAP = "cuda:0"
MAX_LENGTH = 512
LAYER_IDS = (0, 1)
SEED = 20260721
PAIR_COUNT = 4
PROMPT_COUNT = 8
ARM_COUNT = 3
DEFINITION_COUNT_PER_ARM = 28
DEFINITION_COUNT = ARM_COUNT * DEFINITION_COUNT_PER_ARM

PROTOCOL_RELATIVE_PATH = Path(
    "docs/reference/tks_definition_anchor_diagnostic_protocol_20260721.json"
)
ARM_MANIFEST_RELATIVE_PATH = Path(
    "docs/reference/tks_definition_anchor_diagnostic_arms_20260721.json"
)
RUNNER_RELATIVE_PATH = Path(
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/"
    "run_tks_definition_anchor_diagnostic.py"
)
STAGE7_RELATIVE_PATH = Path(
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/"
    "stage7_foundation_rolebound_pilot_20260526.json"
)
SENSITIVITY_RELATIVE_PATH = Path(
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/"
    "foundation28_balanced_v0_20260526.json"
)

EXPECTED_PROTOCOL_SHA256 = (
    "d0e154c7ac9913425a16de8d9394b391ae0c788c1bfcdd8959e4d2554b10b715"
)
EXPECTED_ARM_MANIFEST_SHA256 = (
    "5ef95e61b8df526fec1d66d59635f8b2a6d0f298537019463cd4babefa9b0d5b"
)
EXPECTED_RUNNER_SHA256 = (
    "5b069f43af2d50cbc9cfd4735f316497b0c8ab26762cc871d18cd38edee761da"
)
EXPECTED_STAGE7_SHA256 = (
    "c2fa18078feaad6f4970f31a380b67557f3684bb871f96695dbf00c750516d75"
)
EXPECTED_SENSITIVITY_SHA256 = (
    "0868b37a718798cb30a7db8b8a23f5326d4e1ae2b6464842d16218e97ec1751a"
)

NON_CLAIMS = (
    "This bounded canary proves only that the exact frozen code can load the exact pinned "
    "Pythia-160M revision, validate the pinned definition/scenario sources, hook complete "
    "transformer blocks 0 and 1, and durably round-trip finite raw vectors for eight selected "
    "Stage-7 validation prompts plus all 84 definition prototypes. It is not a semantic-probe "
    "validation, accuracy result, causal-control result, prompt-injection detector, output-"
    "control result, cross-architecture or universal result, 300B execution, production "
    "readiness evidence, Evidence Packet, WORM anchor, ACCEPT verdict, LICENSED capability, "
    "or customer/investor claim. Passing this canary only permits the separately frozen full "
    "NOT_LICENSED_DIAGNOSTIC_ONLY run to proceed."
)

HELPER_PATH = Path(__file__).resolve()


def parse_args(argv: Sequence[str] | None = None) -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        required=True,
        type=Path,
        help="Root of the extracted, hash-verified frozen Git archive.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New persistent output directory under /workspace.",
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual} ({path})"
        )
    return actual


def resolve_frozen_paths(repository_root: Path) -> dict[str, Path]:
    root = repository_root.resolve()
    paths = {
        "repository_root": root,
        "protocol": root / PROTOCOL_RELATIVE_PATH,
        "arm_manifest": root / ARM_MANIFEST_RELATIVE_PATH,
        "runner": root / RUNNER_RELATIVE_PATH,
        "stage7": root / STAGE7_RELATIVE_PATH,
        "sensitivity": root / SENSITIVITY_RELATIVE_PATH,
    }
    missing = [f"{key}={path}" for key, path in paths.items() if key != "repository_root" and not path.is_file()]
    if missing:
        raise RuntimeError(f"Frozen canary inputs are missing: {missing}")
    return paths


def validate_protocol_contract(paths: dict[str, Path]) -> dict[str, Any]:
    require_sha256(paths["protocol"], EXPECTED_PROTOCOL_SHA256, "protocol")
    require_sha256(paths["arm_manifest"], EXPECTED_ARM_MANIFEST_SHA256, "arm manifest")
    require_sha256(paths["runner"], EXPECTED_RUNNER_SHA256, "frozen diagnostic runner")
    require_sha256(paths["stage7"], EXPECTED_STAGE7_SHA256, "Stage-7 bank")
    require_sha256(
        paths["sensitivity"], EXPECTED_SENSITIVITY_SHA256, "sensitivity bank"
    )

    protocol = read_json(paths["protocol"])
    if protocol.get("diagnostic_class") != "ZERO_SHOT_DEFINITION_ANCHOR_DIAGNOSTIC":
        raise RuntimeError("Frozen protocol diagnostic_class mismatch")
    if protocol.get("licensing_status") != "NOT_LICENSED_DIAGNOSTIC_ONLY":
        raise RuntimeError("Frozen protocol licensing boundary mismatch")

    model = protocol.get("model")
    if not isinstance(model, dict):
        raise RuntimeError("Frozen protocol model contract is missing")
    expected_model = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "parameter_count": MODEL_PARAMETER_COUNT,
    }
    for key, expected in expected_model.items():
        if model.get(key) != expected:
            raise RuntimeError(
                f"Frozen protocol model.{key} mismatch: expected {expected!r}, "
                f"got {model.get(key)!r}"
            )

    capture = protocol.get("capture")
    if not isinstance(capture, dict):
        raise RuntimeError("Frozen protocol capture contract is missing")
    expected_capture = {
        "torch_dtype": TORCH_DTYPE,
        "max_length": MAX_LENGTH,
        "hook_target": "complete transformer block output, never MLP-only",
    }
    for key, expected in expected_capture.items():
        if capture.get(key) != expected:
            raise RuntimeError(
                f"Frozen protocol capture.{key} mismatch: expected {expected!r}, "
                f"got {capture.get(key)!r}"
            )

    declared_runner = (
        protocol.get("source_code", {}).get("diagnostic_script", {}).get("sha256")
    )
    declared_manifest = protocol.get("definition_arms", {}).get("manifest_sha256")
    declared_stage7 = (
        protocol.get("scenario_banks", {}).get("stage7_rolebound", {}).get("sha256")
    )
    declared_sensitivity = (
        protocol.get("scenario_banks", {})
        .get("source_derived_sensitivity", {})
        .get("sha256")
    )
    declared = {
        "runner": declared_runner,
        "arm_manifest": declared_manifest,
        "stage7": declared_stage7,
        "sensitivity": declared_sensitivity,
    }
    expected_declared = {
        "runner": EXPECTED_RUNNER_SHA256,
        "arm_manifest": EXPECTED_ARM_MANIFEST_SHA256,
        "stage7": EXPECTED_STAGE7_SHA256,
        "sensitivity": EXPECTED_SENSITIVITY_SHA256,
    }
    if declared != expected_declared:
        raise RuntimeError(
            f"Frozen protocol declared hashes mismatch: expected {expected_declared}, got {declared}"
        )
    return protocol


def load_frozen_runner(path: Path) -> ModuleType:
    require_sha256(path, EXPECTED_RUNNER_SHA256, "frozen diagnostic runner")
    module_name = "cas_frozen_tks_definition_anchor_diagnostic_da00bd94"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not construct an import specification for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def load_and_validate_inputs(
    runner: ModuleType,
    paths: dict[str, Path],
) -> tuple[list[Any], list[Any], dict[str, Any], dict[str, Any]]:
    arm_args = SimpleNamespace(
        arm_manifest=paths["arm_manifest"],
        allow_unadmitted_arm_canary=False,
        original_source=None,
        operational_source=None,
        compact_source=None,
    )
    arms, arm_manifest_provenance = runner.load_definition_arms(arm_args)
    scenarios, scenario_provenance = runner.load_evaluation_scenarios(
        paths["stage7"],
        paths["sensitivity"],
        allow_unpinned_canary=False,
    )
    if len(arms) != ARM_COUNT or any(len(arm.definitions) != 28 for arm in arms):
        raise RuntimeError("Canary requires exactly the admitted D3/A124/compact 3x28 arm set")
    if not all(bool(arm.admitted) for arm in arms):
        raise RuntimeError("Canary refuses an unadmitted definition arm")
    if arm_manifest_provenance.get("sha256") != EXPECTED_ARM_MANIFEST_SHA256:
        raise RuntimeError("Loaded arm manifest provenance does not match the frozen hash")
    if not bool(scenario_provenance.get("integrity_pinned")):
        raise RuntimeError("Scenario banks are not pinned")
    runner.derive_definition_change_contract(arms)
    return arms, scenarios, arm_manifest_provenance, scenario_provenance


def deterministic_pair_rank(group_id: str, seed: int = SEED) -> str:
    material = f"{seed}|stage7_val_complete_pair|{group_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def select_four_complete_stage7_val_pairs(
    scenarios: Sequence[Any],
    *,
    seed: int = SEED,
) -> tuple[list[Any], list[str]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for scenario in scenarios:
        if scenario.split == "stage7_val":
            groups[str(scenario.group_id)].append(scenario)
    if len(groups) < PAIR_COUNT:
        raise RuntimeError(f"Need at least {PAIR_COUNT} Stage-7 validation pairs")
    invalid: dict[str, Any] = {}
    for group_id, rows in groups.items():
        foundations = {str(row.foundation) for row in rows}
        scenario_ids = {str(row.scenario_id) for row in rows}
        if len(rows) != 2 or len(foundations) != 2 or len(scenario_ids) != 2:
            invalid[group_id] = {
                "row_count": len(rows),
                "foundation_count": len(foundations),
                "scenario_id_count": len(scenario_ids),
            }
    if invalid:
        raise RuntimeError(f"Incomplete or malformed Stage-7 validation pairs: {invalid}")

    ranked_group_ids = sorted(
        groups,
        key=lambda group_id: (deterministic_pair_rank(group_id, seed), group_id),
    )
    selected_group_ids = ranked_group_ids[:PAIR_COUNT]
    selected: list[Any] = []
    for group_id in selected_group_ids:
        selected.extend(sorted(groups[group_id], key=lambda row: str(row.scenario_id)))
    if len(selected) != PROMPT_COUNT:
        raise RuntimeError(f"Canary selection must contain exactly {PROMPT_COUNT} prompts")
    if {str(row.split) for row in selected} != {"stage7_val"}:
        raise RuntimeError("Canary selection escaped the Stage-7 validation split")
    return selected, selected_group_ids


def file_entry(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": str(resolved),
        "sha256": sha256_file(resolved),
        "bytes": int(resolved.stat().st_size),
    }


def capture_input_snapshot(
    runner: ModuleType,
    arms: Sequence[Any],
    scenario_provenance: dict[str, Any],
    *,
    extra_paths: Iterable[Path],
) -> dict[str, Any]:
    base = runner.capture_input_integrity_snapshot(arms, scenario_provenance)
    paths = {Path(item["path"]).resolve() for item in base["files"]}
    paths.update(Path(path).resolve() for path in extra_paths)
    entries = [file_entry(path) for path in sorted(paths, key=lambda item: str(item))]
    return {
        "files": entries,
        "snapshot_sha256": sha256_json(entries),
    }


def model_artifact_paths(model_info: dict[str, Any]) -> list[Path]:
    resolved = model_info.get("resolved_artifacts")
    if not isinstance(resolved, dict):
        raise RuntimeError("Model artifact provenance is missing")
    artifacts = resolved.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError("No resolved model artifacts were recorded")
    paths: list[Path] = []
    for item in artifacts:
        if not isinstance(item, dict) or not item.get("resolved_path"):
            raise RuntimeError("Malformed resolved model-artifact provenance")
        paths.append(Path(str(item["resolved_path"])))
    return paths


def validate_model_contract(
    protocol: dict[str, Any],
    model_info: dict[str, Any],
) -> dict[str, str]:
    if model_info.get("model_id") != MODEL_ID:
        raise RuntimeError("Loaded model ID mismatch")
    if str(model_info.get("requested_revision", "")).lower() != MODEL_REVISION:
        raise RuntimeError("Loaded model revision request mismatch")
    commits = {str(value).lower() for value in model_info.get("resolved_commit_hashes", [])}
    if commits != {MODEL_REVISION}:
        raise RuntimeError(f"Resolved model commits are not exactly pinned: {sorted(commits)}")
    if int(model_info.get("parameter_count", -1)) != MODEL_PARAMETER_COUNT:
        raise RuntimeError(
            f"Parameter-count mismatch: expected {MODEL_PARAMETER_COUNT}, "
            f"got {model_info.get('parameter_count')}"
        )
    if model_info.get("torch_dtype") != "torch.float16":
        raise RuntimeError(f"Loaded torch dtype is not float16: {model_info.get('torch_dtype')}")
    if model_info.get("device_map") != DEVICE_MAP:
        raise RuntimeError(f"Loaded device map mismatch: {model_info.get('device_map')}")

    resolved = model_info["resolved_artifacts"]
    errors = list(resolved.get("inspection_errors") or [])
    singular_error = resolved.get("inspection_error")
    if singular_error:
        errors.append(str(singular_error))
    if errors:
        raise RuntimeError(f"Model-artifact inspection reported errors: {errors}")

    expected_artifacts = protocol["model"].get("expected_artifacts")
    if not isinstance(expected_artifacts, dict) or not expected_artifacts:
        raise RuntimeError("Protocol expected model-artifact hashes are missing")
    actual_by_filename: dict[str, set[str]] = defaultdict(set)
    for item in resolved.get("artifacts", []):
        actual_by_filename[str(item.get("filename"))].add(str(item.get("sha256")))
    verified: dict[str, str] = {}
    for filename, expected in sorted(expected_artifacts.items()):
        observed = actual_by_filename.get(filename, set())
        if observed != {str(expected)}:
            raise RuntimeError(
                f"Model artifact {filename} hash mismatch: expected {expected}, "
                f"observed {sorted(observed)}"
            )
        verified[str(filename)] = str(expected)
    return verified


def enforce_cuda_float16(model: Any) -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        raise RuntimeError("CUDA GPU is unavailable; CPU execution is forbidden for this canary")
    parameters = list(model.parameters())
    if not parameters:
        raise RuntimeError("Loaded model exposes no parameters")
    parameter_devices = sorted({parameter.device.type for parameter in parameters})
    if parameter_devices != ["cuda"]:
        raise RuntimeError(f"All model parameters must be on CUDA, got {parameter_devices}")
    floating_dtypes = sorted(
        {str(parameter.dtype) for parameter in parameters if parameter.is_floating_point()}
    )
    if floating_dtypes != ["torch.float16"]:
        raise RuntimeError(f"All floating parameters must be float16, got {floating_dtypes}")
    return {
        "cuda_available": True,
        "cuda_device_count": int(torch.cuda.device_count()),
        "parameter_device_types": parameter_devices,
        "floating_parameter_dtypes": floating_dtypes,
    }


def validate_capture_arrays(
    *,
    eval_mean: np.ndarray,
    eval_last: np.ndarray,
    eval_token_counts: np.ndarray,
    eval_token_hashes: np.ndarray,
    definition_mean: np.ndarray,
    definition_last: np.ndarray,
    definition_token_counts: np.ndarray,
    definition_token_hashes: np.ndarray,
    hidden_size: int,
) -> dict[str, list[int]]:
    expected_eval = (PROMPT_COUNT, len(LAYER_IDS), hidden_size)
    expected_definition = (
        ARM_COUNT,
        DEFINITION_COUNT_PER_ARM,
        len(LAYER_IDS),
        hidden_size,
    )
    for name, array, expected in (
        ("eval_mean", eval_mean, expected_eval),
        ("eval_last", eval_last, expected_eval),
        ("definition_mean", definition_mean, expected_definition),
        ("definition_last", definition_last, expected_definition),
    ):
        if tuple(array.shape) != expected:
            raise RuntimeError(f"{name} shape mismatch: expected {expected}, got {array.shape}")
        if array.dtype != np.float16:
            raise RuntimeError(f"{name} storage dtype must be float16, got {array.dtype}")
        if not np.all(np.isfinite(array)):
            raise RuntimeError(f"{name} contains non-finite values")

    expected_eval_tokens = (PROMPT_COUNT,)
    expected_definition_tokens = (ARM_COUNT, DEFINITION_COUNT_PER_ARM)
    if tuple(eval_token_counts.shape) != expected_eval_tokens:
        raise RuntimeError("Evaluation token-count shape mismatch")
    if tuple(definition_token_counts.shape) != expected_definition_tokens:
        raise RuntimeError("Definition token-count shape mismatch")
    all_counts = np.concatenate(
        [eval_token_counts.reshape(-1), definition_token_counts.reshape(-1)]
    )
    if np.any(all_counts < 1) or np.any(all_counts > MAX_LENGTH):
        raise RuntimeError("A captured sequence was empty or exceeded max_length")
    if tuple(eval_token_hashes.shape) != expected_eval_tokens:
        raise RuntimeError("Evaluation token-ID hash shape mismatch")
    if tuple(definition_token_hashes.shape) != expected_definition_tokens:
        raise RuntimeError("Definition token-ID hash shape mismatch")
    all_hashes = np.concatenate(
        [eval_token_hashes.reshape(-1), definition_token_hashes.reshape(-1)]
    )
    invalid_hashes = [value for value in all_hashes if not re.fullmatch(r"[0-9a-f]{64}", str(value))]
    if invalid_hashes:
        raise RuntimeError("One or more token-ID hashes are invalid")
    return {
        "eval_shape": list(expected_eval),
        "definition_shape": list(expected_definition),
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing receipt: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        prepublish_bytes = temporary.read_bytes()
        if prepublish_bytes != encoded or json.loads(prepublish_bytes) != payload:
            raise RuntimeError("JSON receipt failed pre-publish reopen verification")
        expected_sha256 = hashlib.sha256(encoded).hexdigest()
        os.replace(temporary, path)
        final_bytes = path.read_bytes()
        if final_bytes != encoded or json.loads(final_bytes) != payload:
            raise RuntimeError("JSON receipt failed post-replace reopen verification")
        final_sha256 = hashlib.sha256(final_bytes).hexdigest()
        if final_sha256 != expected_sha256:
            raise RuntimeError("JSON receipt hash changed across atomic replace")
        return {
            "status": "ATOMIC_JSON_WRITE_PREPUBLISH_AND_FINAL_REOPEN_VERIFIED",
            "sha256": final_sha256,
            "bytes": len(final_bytes),
            "path": str(path.resolve()),
        }
    finally:
        if temporary.exists():
            temporary.unlink()


def require_persistent_workspace_output(output_dir: Path) -> Path:
    output = output_dir.resolve()
    workspace = Path("/workspace").resolve()
    if output != workspace and workspace not in output.parents:
        raise RuntimeError(
            f"Canary output must be on persistent /workspace storage, got {output}"
        )
    return output


def token_hash_receipt(
    arms: Sequence[Any],
    eval_hashes: np.ndarray,
    definition_hashes: np.ndarray,
) -> dict[str, Any]:
    return {
        "evaluation_prompt_token_id_sha256": [str(value) for value in eval_hashes],
        "definition_token_id_sha256_by_arm": {
            arm.name: [str(value) for value in definition_hashes[index]]
            for index, arm in enumerate(arms)
        },
        "hash_contract": (
            "SHA-256 of canonical JSON integer token-ID list after tokenizer special-token "
            "handling and before device transfer"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = require_persistent_workspace_output(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    raw_path = output_dir / "tks_definition_anchor_canary_vectors.npz"
    receipt_path = output_dir / "tks_definition_anchor_canary_receipt.json"

    paths = resolve_frozen_paths(args.repository_root)
    protocol = validate_protocol_contract(paths)
    runner = load_frozen_runner(paths["runner"])
    arms, scenarios, arm_manifest_provenance, scenario_provenance = (
        load_and_validate_inputs(runner, paths)
    )
    selected_scenarios, selected_group_ids = select_four_complete_stage7_val_pairs(
        scenarios,
        seed=SEED,
    )

    source_extra_paths = [
        paths["protocol"],
        paths["arm_manifest"],
        paths["runner"],
        HELPER_PATH,
    ]
    source_snapshot_start = capture_input_snapshot(
        runner,
        arms,
        scenario_provenance,
        extra_paths=source_extra_paths,
    )

    model_args = SimpleNamespace(
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        torch_dtype=TORCH_DTYPE,
        device_map=DEVICE_MAP,
        trust_remote_code=False,
    )
    pin_status = runner.validate_model_revision(MODEL_REVISION, False)
    model, tokenizer, model_info = runner.load_model(model_args)
    verified_model_artifacts = validate_model_contract(protocol, model_info)
    cuda_contract = enforce_cuda_float16(model)

    source_snapshot_after_model_load = capture_input_snapshot(
        runner,
        arms,
        scenario_provenance,
        extra_paths=source_extra_paths,
    )
    if source_snapshot_start != source_snapshot_after_model_load:
        raise RuntimeError("Source/code inputs changed while loading the pinned model")

    artifact_paths = model_artifact_paths(model_info)
    capture_snapshot_start = capture_input_snapshot(
        runner,
        arms,
        scenario_provenance,
        extra_paths=[*source_extra_paths, *artifact_paths],
    )

    layers = runner.locate_transformer_layers(model)
    runner.validate_layer_range(layer_start=0, layer_end=1, total_layers=len(layers))
    selected_layers = runner.select_assigned_layers(layers, 0, 1)
    actual_layer_ids = tuple(int(index) for index, _module in selected_layers)
    if actual_layer_ids != LAYER_IDS:
        raise RuntimeError(f"Canary layer selection mismatch: {actual_layer_ids}")
    hook_modules = runner.qualified_module_records(model, selected_layers)

    eval_texts = [scenario.prompt for scenario in selected_scenarios]
    eval_mean, eval_last, eval_token_counts, eval_token_hashes = runner.capture_text_vectors(
        model=model,
        tokenizer=tokenizer,
        texts=eval_texts,
        selected_layers=selected_layers,
        max_length=MAX_LENGTH,
        progress_prefix="canary-eval-8",
    )
    definition_texts = [
        definition.prototype_text
        for arm in arms
        for definition in arm.definitions
    ]
    if len(definition_texts) != DEFINITION_COUNT:
        raise RuntimeError(f"Canary requires exactly {DEFINITION_COUNT} definition prototypes")
    (
        definition_mean_flat,
        definition_last_flat,
        definition_token_counts_flat,
        definition_token_hashes_flat,
    ) = runner.capture_text_vectors(
        model=model,
        tokenizer=tokenizer,
        texts=definition_texts,
        selected_layers=selected_layers,
        max_length=MAX_LENGTH,
        progress_prefix="canary-definitions-84",
    )

    hidden_size = int(model_info.get("hidden_size") or definition_mean_flat.shape[-1])
    definition_mean = definition_mean_flat.reshape(
        ARM_COUNT, DEFINITION_COUNT_PER_ARM, len(LAYER_IDS), hidden_size
    )
    definition_last = definition_last_flat.reshape(
        ARM_COUNT, DEFINITION_COUNT_PER_ARM, len(LAYER_IDS), hidden_size
    )
    definition_token_counts = definition_token_counts_flat.reshape(
        ARM_COUNT, DEFINITION_COUNT_PER_ARM
    )
    definition_token_hashes = definition_token_hashes_flat.reshape(
        ARM_COUNT, DEFINITION_COUNT_PER_ARM
    )
    shapes = validate_capture_arrays(
        eval_mean=eval_mean,
        eval_last=eval_last,
        eval_token_counts=eval_token_counts,
        eval_token_hashes=eval_token_hashes,
        definition_mean=definition_mean,
        definition_last=definition_last,
        definition_token_counts=definition_token_counts,
        definition_token_hashes=definition_token_hashes,
        hidden_size=hidden_size,
    )

    capture_snapshot_end = capture_input_snapshot(
        runner,
        arms,
        scenario_provenance,
        extra_paths=[*source_extra_paths, *artifact_paths],
    )
    if capture_snapshot_start != capture_snapshot_end:
        raise RuntimeError("Source/code/model inputs changed during hidden-state capture")

    created_at = datetime.now(UTC).isoformat()
    canary_provenance = {
        "schema_version": runner.RAW_SCHEMA,
        "canary_schema_version": CANARY_SCHEMA,
        "diagnostic_class": CANARY_CLASS,
        "status": CANARY_STATUS,
        "licensing_status": LICENSING_STATUS,
        "claim_eligible": False,
        "created_at": created_at,
        "model": model_info,
        "model_pin_status": pin_status,
        "hardware": runner.capture_hardware_provenance(),
        "source_code": {
            "canary_helper": file_entry(HELPER_PATH),
            "frozen_runner": file_entry(paths["runner"]),
            "frozen_protocol": file_entry(paths["protocol"]),
        },
        "input_integrity_start_end": {
            "status": "VERIFIED_IDENTICAL",
            "start_snapshot_sha256": capture_snapshot_start["snapshot_sha256"],
            "end_snapshot_sha256": capture_snapshot_end["snapshot_sha256"],
            "snapshot": capture_snapshot_start,
        },
        "arms": [runner.arm_provenance(arm) for arm in arms],
        "arm_manifest": arm_manifest_provenance,
        "scenario_sources": scenario_provenance,
        "selection": {
            "split": "stage7_val",
            "algorithm": (
                "sort complete pair IDs by SHA-256(seed|stage7_val_complete_pair|group_id), "
                "tie-break group_id; take first four; sort rows within pair by scenario_id"
            ),
            "seed": SEED,
            "pair_count": PAIR_COUNT,
            "prompt_count": PROMPT_COUNT,
            "selected_group_ids": selected_group_ids,
            "selected_scenario_ids": [row.scenario_id for row in selected_scenarios],
            "selection_sha256": sha256_json(
                {
                    "seed": SEED,
                    "group_ids": selected_group_ids,
                    "scenario_ids": [row.scenario_id for row in selected_scenarios],
                }
            ),
        },
        "capture_contract": {
            "hook_target": "complete_transformer_block_output",
            "explicitly_not_hooked": "mlp_submodule",
            "selected_transformer_block_modules": hook_modules,
            "layers": list(LAYER_IDS),
            "evaluation_prompt_forward_passes": PROMPT_COUNT,
            "definition_prompt_forward_passes": DEFINITION_COUNT,
            "definition_arm_count": ARM_COUNT,
            "definition_count_per_arm": DEFINITION_COUNT_PER_ARM,
            "pooling": ["attention_masked_mean_token", "last_nonpadding_token"],
            "max_length": MAX_LENGTH,
            "truncation_policy": "fail_closed_before_forward",
            "truncated_sequence_count": 0,
            "raw_vector_storage_dtype": "float16",
            "cuda_contract": cuda_contract,
        },
        "non_claims": NON_CLAIMS,
    }

    raw_verification = runner.save_raw_diagnostic_artifact(
        raw_path,
        provenance=canary_provenance,
        scenarios=selected_scenarios,
        arms=arms,
        layers=np.asarray(LAYER_IDS, dtype=np.int16),
        eval_mean=eval_mean,
        eval_last=eval_last,
        eval_token_counts=eval_token_counts,
        eval_token_id_sha256=eval_token_hashes,
        definition_mean=definition_mean,
        definition_last=definition_last,
        definition_token_counts=definition_token_counts,
        definition_token_id_sha256=definition_token_hashes,
    )

    receipt = {
        "schema_version": CANARY_SCHEMA,
        "diagnostic_class": CANARY_CLASS,
        "created_at": created_at,
        "status": CANARY_STATUS,
        "claim_eligible": False,
        "licensing_status": LICENSING_STATUS,
        "non_claims": NON_CLAIMS,
        "model": {
            "model_id": MODEL_ID,
            "requested_revision": MODEL_REVISION,
            "resolved_commit_hashes": model_info["resolved_commit_hashes"],
            "parameter_count": model_info["parameter_count"],
            "torch_dtype": model_info["torch_dtype"],
            "device_map": model_info["device_map"],
            "expected_artifact_sha256": verified_model_artifacts,
            "resolved_artifacts": model_info["resolved_artifacts"],
        },
        "source_and_script_hashes": {
            "canary_helper": file_entry(HELPER_PATH),
            "frozen_protocol": file_entry(paths["protocol"]),
            "frozen_runner": file_entry(paths["runner"]),
            "arm_manifest": file_entry(paths["arm_manifest"]),
            "stage7_bank": file_entry(paths["stage7"]),
            "sensitivity_bank_validated_but_not_captured": file_entry(paths["sensitivity"]),
            "definition_arms": [runner.arm_provenance(arm) for arm in arms],
        },
        "input_integrity_start_end": {
            "status": "VERIFIED_IDENTICAL",
            "start_snapshot_sha256": capture_snapshot_start["snapshot_sha256"],
            "end_snapshot_sha256": capture_snapshot_end["snapshot_sha256"],
            "hashes_equal": (
                capture_snapshot_start["snapshot_sha256"]
                == capture_snapshot_end["snapshot_sha256"]
            ),
            "file_count": len(capture_snapshot_start["files"]),
            "files": capture_snapshot_start["files"],
        },
        "selection": canary_provenance["selection"],
        "capture": {
            **canary_provenance["capture_contract"],
            **shapes,
            "qualified_hook_modules": hook_modules,
        },
        "token_id_hashes": token_hash_receipt(
            arms,
            eval_token_hashes,
            definition_token_hashes,
        ),
        "raw_npz": raw_verification,
        "receipt_atomicity_contract": {
            "temporary_file_fsync": True,
            "prepublish_reopen_and_parse": True,
            "atomic_replace": True,
            "final_reopen_parse_and_hash": True,
        },
    }
    receipt_verification = atomic_write_json(receipt_path, receipt)
    print(
        json.dumps(
            {
                "status": CANARY_STATUS,
                "claim_eligible": False,
                "licensing_status": LICENSING_STATUS,
                "raw_npz": raw_verification,
                "receipt": receipt_verification,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
