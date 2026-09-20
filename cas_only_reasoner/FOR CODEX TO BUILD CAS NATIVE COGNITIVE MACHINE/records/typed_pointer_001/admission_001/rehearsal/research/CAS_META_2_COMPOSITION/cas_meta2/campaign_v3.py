"""Learning-v3 bounded AWS-only composition pilot: smoke, learn, seal, then native checks.

The test-private file is first parsed after every arm's public-only predictions
are sealed. Native work runs in eight spawned, isolated processes. Unsupported
predictions count as model errors; failures of admitted programs stop the run.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import multiprocessing
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from .codec import PROCEDURE_NAMES, canonical_sha256, validate_action
from .curriculum import check_native_topology, parse_problem, permitted_view
from .ir import validate_program


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
MAX_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024
MAX_WALL_SECONDS = 6600
WORKERS = 8
SCHEMA = "cas-meta2-campaign-receipt/3"
PROFILE = "learning_v3"
ENTRYPOINT = "cas_meta2.campaign_v3"
SPEC_NAME = "EXPERIMENT_V3.json"
PHASE_SECONDS = {
    "dataset_construction": 120, "actual_copy_gpu_tests": 240, "trainer_gpu_tests": 180,
    "actual_copy_preflight": 120, "native_smoke": 180, "paired_training": 2700,
    "prediction_seal": 480, "native_evaluation": 2400, "final_evidence": 180,
}
GPU_GROUPS = {
    "actual_copy": ("tests/test_gpu_preflight_copy_v3_gpu.py", 3, "actual_copy_gpu_tests"),
    "trainer": ("tests/test_train_v3_gpu.py", 2, "trainer_gpu_tests"),
}
SOURCE_TESTS = (
    "test_campaign_v3_static.py", "test_train_v3_gpu.py", "test_train_v3_static.py",
    "test_policy_v3_gpu.py", "test_loss_v3_gpu.py", "test_gpu_preflight_copy_v3_gpu.py",
    "test_gpu_preflight_copy_v3_static.py", "test_gpu_preflight_v3_static.py",
    "test_curriculum_v3.py", "test_grammar_v3.py", "test_features_v3.py", "test_selection_v3.py",
)


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def _hash(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("CAMPAIGN_WALL_DEADLINE_REACHED")


def _output_bytes(output):
    total = 0
    for path in Path(output).rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except FileNotFoundError:
                # A worker may atomically replace its temporary file.
                continue
    if total > MAX_OUTPUT_BYTES:
        raise RuntimeError("EXPANDED_OUTPUT_CEILING_EXCEEDED")
    return total


def _source_identity():
    paths = list((ROOT / "cas_meta2").glob("*.py"))
    paths += [ROOT / "cas_meta2" / name for name in ("exclusions_v3.json", "development_exclusions_v3.json")]
    paths += [ROOT / "tests" / name for name in SOURCE_TESTS]
    paths += [ROOT / name for name in (SPEC_NAME, "pyproject.toml", "requirements-gpu.txt")]
    for path in paths:
        if not path.is_file() or any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
                                     for item in (path, *path.parents)):
            raise RuntimeError("V3_SOURCE_PATH_INVALID:" + str(path))
    return {path.relative_to(ROOT).as_posix(): _hash(path) for path in sorted(paths)}


def _baseline_identity():
    sibling = ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
    if not sibling.is_dir():
        raise RuntimeError("FROZEN_META1_HELPERS_MISSING")
    if str(sibling) not in sys.path:
        sys.path.insert(0, str(sibling))
    from cas_meta1.baseline import verify_baseline, verify_installed_wheels
    return {"source": verify_baseline(), "installed_wheels": verify_installed_wheels()}


def admission_error(action, public):
    """Separate invalid predicted programs from actual execution failures."""
    from .native import admit_action
    try:
        admit_action(public, action)
    except ValueError as error:
        return {"code": "PREDICTED_PROGRAM_INVALID", "type": type(error).__name__,
                "message": str(error)[:2048]}
    return None


def _smoke_tasks(train_tasks):
    """Three public-rule fixtures, separate from model training/evaluation."""
    from .curriculum import _render
    if not train_tasks:
        raise RuntimeError("SMOKE_REQUIRES_TRAINING_ANCHOR")
    first = deepcopy(train_tasks[0])
    deep_base = max(train_tasks, key=lambda task: validate_program(task["target"]["program"])["max_call_depth"])
    deep = deepcopy(deep_base)
    program = deep["target"]["program"]
    # Runtime smoke only. Select a free legal name; v2 trains on all names.
    free_names = [name for name in PROCEDURE_NAMES[1:] if name not in program["procedures"]]
    if not free_names or len(program["procedures"]) >= 16:
        raise RuntimeError("SMOKE_NO_FREE_WRAPPER_NAME")
    wrapper = free_names[-1]
    program["procedures"][wrapper] = program["procedures"].pop("main")
    program["procedures"]["main"] = {
        "input": "arg", "allowed_cjts": ["A", "B", "C"],
        "steps": [{"kind": "CALL", "procedure": wrapper, "input": "arg", "output": "v0"}],
        "return": "v0"}
    named = deepcopy(first)
    named["target"]["program"] = {
        "schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
            "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
                {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                {"kind": "RUN", "cjt_id": "B", "input": "v0", "output": "v1"},
                {"kind": "RUN", "cjt_id": "B", "input": "v0", "output": "v2"},
                {"kind": "RUN", "cjt_id": "C", "input": "v1", "output": "v3"}],
                "return": "v3"}}}
    fixtures = []
    for name, task in (("training_anchor", first), ("nested_depth", deep), ("named_earlier_value", named)):
        task["task_id"] = "meta2-smoke-" + name
        selected = next(row for row in task["public"]["observations"] if row["slot"] == task["target"]["binding"])
        task["public"]["problem"] = _render(task["target"]["program"], selected["tag"], 0)
        task["provenance"] = {"split": "runtime_smoke_not_learning", "fixture": name,
                              "source": "training anchor and independent bounded structural transformations"}
        if parse_problem(task["public"]) != task["target"]:
            raise RuntimeError("SMOKE_PUBLIC_RULE_TARGET_MISMATCH")
        if admission_error(task["target"], task["public"]) is not None:
            raise RuntimeError("SMOKE_PROGRAM_NOT_ADMITTED")
        fixtures.append((name, task))
    return fixtures


def run_smoke(train_tasks, output, deadline):
    from .native import execute_task, reference_task, verify_reference_task, verify_task
    from .train_v3 import setup_cuda
    _, device = setup_cuda()
    output = Path(output)
    rows = []
    for name, task in _smoke_tasks(train_tasks):
        _deadline(deadline)
        started = time.monotonic()
        directory = output / "smoke" / name
        reference = reference_task(task, directory / "reference", device=str(device))
        _write(directory / "reference_result.json", reference)
        reference_verdict = verify_reference_task(task, reference)
        _write(directory / "reference_verdict.json", reference_verdict)
        if reference.get("status") != "EXECUTED" or reference_verdict.get("task_correct") is not True:
            raise RuntimeError("SMOKE_NATIVE_REFERENCE_INVALID:" + name)
        action = parse_problem(permitted_view(task))
        result = execute_task(permitted_view(task), action, directory / "execution", device=str(device))
        _write(directory / "execution_result.json", result)
        verdict = verify_task(task, result, reference)
        _write(directory / "verification.json", verdict)
        row = {"fixture": name, "program_sha256": canonical_sha256(action["program"]),
               "structure": validate_program(action["program"]), "reference": reference_verdict,
               "verification": verdict, "wall_seconds": time.monotonic() - started}
        rows.append(row)
        _write(output / "smoke_receipt.json", {"status": "SMOKE_IN_PROGRESS", "completed": False, "cases": rows})
        if result.get("status") != "EXECUTED" or verdict.get("task_correct") is not True:
            raise RuntimeError("SMOKE_ADMITTED_NATIVE_EXECUTION_FAILED:" + name)
        _output_bytes(output)
        print(json.dumps({"stage": "native_smoke", "fixture": name, "task_correct": True,
                          "completed": len(rows), "total": 3}), flush=True)
    receipt = {"status": "CAS_META_2_NATIVE_SMOKE_COMPLETED", "completed": True,
               "cases": rows, "case_count": len(rows), "device": str(device),
               "boundary": "Runtime preflight only; no model training or held-out learning claim."}
    _write(output / "smoke_receipt.json", receipt)
    return receipt


def _worker_init():
    from .train_v3 import setup_cuda
    setup_cuda()


def _case_worker(job):
    from .native import execute_task, reference_task, verify_reference_task, verify_task
    from .train_v3 import setup_cuda
    _, device = setup_cuda()
    index, task, actions, output = job
    output = Path(output)
    case_directory = output / "evaluation" / f"case_{index:04d}"
    case_started = time.monotonic()
    try:
        reference_started = time.monotonic()
        reference = reference_task(task, case_directory / "reference", device=str(device))
        _write(case_directory / "reference_result.json", reference)
        reference_verdict = verify_reference_task(task, reference)
        _write(case_directory / "reference_verdict.json", reference_verdict)
        if reference.get("status") != "EXECUTED" or reference_verdict.get("task_correct") is not True:
            raise RuntimeError("HELD_OUT_NATIVE_REFERENCE_INVALID:" + str(index))
        reference_seconds = time.monotonic() - reference_started
        rows = {}
        for arm in ARMS:
            action = actions[arm]
            directory = case_directory / arm
            started = time.monotonic()
            rejected = admission_error(action, permitted_view(task))
            if rejected is not None:
                result = {"status": "REJECTED", "action": action, "failure": rejected,
                          "reserved_policy_units": 0, "native_runs": 0}
            else:
                result = execute_task(permitted_view(task), action, directory / "native", device=str(device))
                if result.get("status") != "EXECUTED":
                    _write(directory / "execution_result.json", result)
                    raise RuntimeError("ADMITTED_PROGRAM_NATIVE_FAILURE:" + arm + ":" + str(index))
            _write(directory / "execution_result.json", result)
            verdict = verify_task(task, result, reference)
            if rejected is not None and verdict.get("task_correct") is True:
                raise RuntimeError("REJECTED_PROGRAM_REPORTED_CORRECT")
            _write(directory / "verification.json", verdict)
            row = {"case_index": index, "arm": arm, "action": action,
                   "execution_status": result.get("status"), "failure": result.get("failure"),
                   "verification": verdict, "model_rejection": rejected is not None,
                   "wall_seconds": time.monotonic() - started,
                   "evidence_directory": str(directory)}
            rows[arm] = row
            _write(directory / "case_receipt.json", row)
        receipt = {"case_index": index, "task_id": task.get("task_id"), "arms": rows,
                   "reference_verification": reference_verdict,
                   "reference_wall_seconds": reference_seconds,
                   "case_wall_seconds": time.monotonic() - case_started}
        _write(case_directory / "case_receipt.json", receipt)
        return receipt
    except BaseException as error:
        _write(case_directory / "worker_failure.json",
               {"case_index": index, "type": type(error).__name__, "message": str(error)[:4096],
                "traceback": traceback.format_exc()[-16000:], "completed": False})
        raise


def aggregate_cases(cases, total_expected):
    if type(total_expected) is not int or total_expected < 1:
        raise ValueError("EVALUATION_DENOMINATOR_INVALID")
    if len(cases) != total_expected or sorted(case["case_index"] for case in cases) != list(range(total_expected)):
        raise RuntimeError("EVALUATION_CASE_COVERAGE_MISMATCH")
    result = {}
    fields = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct",
              "actual_output_correct", "trace_valid")
    for arm in ARMS:
        rows = [case["arms"][arm] for case in cases]
        counts = {field: sum(row["verification"].get(field) is True for row in rows) for field in fields}
        repair_required = [row for row in rows if row["verification"].get("repair_required") is True]
        result[arm] = {
            "total": total_expected, **counts, "task_accuracy": counts["task_correct"] / total_expected,
            "model_rejections": sum(row["model_rejection"] is True for row in rows),
            "native_executed": sum(row["execution_status"] == "EXECUTED" for row in rows),
            "native_runs": sum(row["verification"].get("native_runs", 0) for row in rows),
            "reserved_policy_units": sum(row["verification"].get("reserved_policy_units", 0) for row in rows),
            "repair_required_total": len(repair_required),
            "repair_success": (sum(row["verification"].get("repair_success") is True for row in repair_required)
                               if repair_required else None),
            "repair_boundary": "Repair is not exercised by this native RUN/CALL pilot when the required count is zero.",
            "worker_wall_seconds": sum(row["wall_seconds"] for row in rows),
            "all_cases_in_denominator": True,
        }
    return result


def evaluate_sealed(data, output, seal, deadline):
    """This is the only held-out private-label parser in the campaign."""
    data, output = Path(data), Path(output)
    if (seal.get("schema") != "cas-meta2-prediction-seal/1" or seal.get("arms") != list(ARMS)
            or type(seal.get("test_examples")) is not int or seal["test_examples"] != 72
            or type(seal.get("prediction_count")) is not int or seal["prediction_count"] != 360):
        raise RuntimeError("V3_FULL_PREDICTION_SEAL_REQUIRED")
    predictions_path = output / "predictions.jsonl"
    if _hash(predictions_path) != seal["sha256"] or seal["test_private_labels_loaded"] is not False:
        raise RuntimeError("PREDICTION_SEAL_INVALID")
    if set(seal["arms"]) != set(ARMS):
        raise RuntimeError("PREDICTION_ARM_COVERAGE_INVALID")
    if _hash(data / "test_private.json") != seal["test_private_sha256"]:
        raise RuntimeError("TEST_PRIVATE_CHANGED_AFTER_SEAL")
    if _hash(data / "test_public.json") != seal["test_public_sha256"]:
        raise RuntimeError("TEST_PUBLIC_CHANGED_AFTER_SEAL")
    predictions = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines()]
    publics = _read(data / "test_public.json")
    if len(predictions) != len(publics) or len(publics) != seal["test_examples"]:
        raise RuntimeError("PREDICTION_DENOMINATOR_MISMATCH")
    for index, (prediction, public) in enumerate(zip(predictions, publics, strict=True)):
        if prediction["case_index"] != index or prediction["public_sha256"] != canonical_sha256(public):
            raise RuntimeError("SEALED_PUBLIC_CASE_MAPPING_INVALID")
        if set(prediction["actions"]) != set(ARMS):
            raise RuntimeError("SEALED_CASE_ARM_COVERAGE_INVALID")
    opening = {"opened_utc": datetime.now(timezone.utc).isoformat(),
               "prediction_sha256_before_opening": seal["sha256"],
               "test_private_sha256": seal["test_private_sha256"]}
    if datetime.fromisoformat(opening["opened_utc"]) <= datetime.fromisoformat(seal["sealed_utc"]):
        raise RuntimeError("TEST_GOLD_OPENING_TIME_NOT_AFTER_SEAL")
    _write(output / "test_gold_opening_receipt.json", opening)
    tasks = _read(data / "test_private.json")
    if len(tasks) != len(publics) or any(permitted_view(task) != public
                                      for task, public in zip(tasks, publics, strict=True)):
        raise RuntimeError("TEST_PUBLIC_PRIVATE_BINDING_MISMATCH")
    # Full private-data validation occurs only after the explicit seal/opening above.
    from .curriculum_v3 import SCHEMA as DATA_SCHEMA, registered_development_exclusions, validate_dataset
    manifest = _read(data / "dataset_manifest.json")
    checked = validate_dataset({"schema": DATA_SCHEMA, "seed": manifest["seed"],
        "dataset_id": manifest["dataset_id"], "splits": {
            "train": _read(data / "train.json"), "validation": _read(data / "validation.json"), "test": tasks}},
        excluded_graph_signatures=registered_development_exclusions())
    if canonical_sha256(checked) != canonical_sha256({k: v for k, v in manifest.items() if k != "sha256"}):
        raise RuntimeError("V3_COLD_PRIVATE_VALIDATION_MANIFEST_CHANGED")
    _write(output / "dataset_validation_v3.json", {"schema": "cas-meta2-cold-dataset-validation/3",
        "completed": True, "dataset_id": manifest["dataset_id"], "manifest_sha256": _hash(data / "dataset_manifest.json"),
        "after_prediction_seal": True, "prediction_sha256": seal["sha256"],
        "checked_manifest_sha256": canonical_sha256(checked),
        "boundary": "Source-bound construction and public-meaning recheck; not native task verification."})
    context = multiprocessing.get_context("spawn")
    pool = ProcessPoolExecutor(max_workers=WORKERS, mp_context=context, initializer=_worker_init)
    futures = []
    completed = []
    succeeded = False
    try:
        for index, (task, prediction) in enumerate(zip(tasks, predictions, strict=True)):
            futures.append(pool.submit(_case_worker, (index, task, prediction["actions"], str(output))))
        _deadline(deadline)
        for future in as_completed(futures, timeout=max(0.01, deadline - time.monotonic())):
            _deadline(deadline)
            completed.append(future.result())
            _write(output / "evaluation_progress.json",
                   {"completed_cases": len(completed), "expected_cases": len(tasks),
                    "case_indices": sorted(case["case_index"] for case in completed),
                    "workers": WORKERS, "automatic_retry": False,
                    "output_bytes": _output_bytes(output)})
            print(json.dumps({"stage": "native_evaluation", "completed_cases": len(completed),
                              "total_cases": len(tasks), "completed_arm_verdicts": len(completed) * len(ARMS)}),
                  flush=True)
        completed.sort(key=lambda row: row["case_index"])
        metrics = aggregate_cases(completed, len(tasks))
        if _hash(predictions_path) != seal["sha256"]:
            raise RuntimeError("SEALED_PREDICTIONS_CHANGED_DURING_EVALUATION")
        _write(output / "evaluation_results.json", {"results": metrics, "cases": completed})
        succeeded = True
        return {"results": metrics, "cases": len(tasks), "arm_verdicts": len(tasks) * len(ARMS),
                "reference_cases": len(tasks), "workers": WORKERS, "gold_opening": opening}
    finally:
        if not succeeded:
            # Do not let a worker timeout keep the paid instance alive.
            processes = list(getattr(pool, "_processes", {}).values())
            for future in futures:
                future.cancel()
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
            pool.shutdown(wait=False, cancel_futures=True)
            _write(output / "evaluation_partial.json",
                   {"completed": False, "completed_cases": completed, "expected_cases": len(tasks),
                    "partial_case_files_retained": True, "automatic_retry": False})
        else:
            pool.shutdown(wait=True)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_experiment(spec):
    """Pure allowlist checks; no Torch import or dataset construction."""
    from .curriculum_v3 import DEFAULT_COUNTS, DEFAULT_SEED, EXCLUSION_ASSET_SHA256, DEVELOPMENT_EXCLUSION_ASSET_SHA256
    if (type(spec) is not dict or spec.get("schema") != "cas-meta2-experiment/3"
            or spec.get("profile") != PROFILE or spec.get("entrypoint") != ENTRYPOINT):
        raise ValueError("V3_EXPERIMENT_IDENTITY_INVALID")
    curriculum, execution, training = spec["curriculum"], spec["execution"], spec["training"]
    expected_training = {
        "seed": 7, "curriculum_seed": DEFAULT_SEED, "epochs": 60, "batch_size": 16,
        "prediction_batch_size": 16, "learning_rate": 0.001, "weight_decay": 0.01,
        "gradient_clip": 1.0, "max_training_seconds": 2700, "validation_generation_interval": 5,
        "training_examples_per_depth": 1024, "validation_examples_per_depth": 32,
        "test_triplets": 24, "train_probe_examples_per_depth": 8,
        "policy": {"d_model": 64, "heads": 4, "layers": 2, "cas_ff_width": 128,
            "decoder_layers": 1, "decoder_ff_width": 128, "max_length": 1024,
            "max_action_length": 256, "cas_initial_saturation_per_max_token": 2.0,
            "max_parameter_mismatch_fraction": 0.01}}
    if _canonical(training) != _canonical(expected_training):
        raise ValueError("V3_REGISTERED_TRAINING_CONFIG_MISMATCH")
    if (curriculum.get("schema") != "cas-meta2-dataset-manifest/3"
            or type(curriculum.get("seed")) is not int or curriculum["seed"] != DEFAULT_SEED
            or curriculum.get("counts") != DEFAULT_COUNTS
            or curriculum.get("training_depth_counts") != {"1": 1024, "2": 1024, "3": 1024}
            or curriculum.get("validation_depth_counts") != {"1": 32, "2": 32, "3": 32}
            or curriculum.get("test_groups") != {"same_depth": 24, "wording_shift": 24, "deeper_calls": 24}
            or curriculum.get("allowed_cjts") != ["A", "B", "C"]):
        raise ValueError("V3_REGISTERED_CURRICULUM_MISMATCH")
    exclusion = curriculum.get("exclusions", {})
    if exclusion != {"base_count": 4312, "development_count": 177, "overlap_count": 1,
            "combined_count": 4488, "base_asset_sha256": EXCLUSION_ASSET_SHA256,
            "development_asset_sha256": DEVELOPMENT_EXCLUSION_ASSET_SHA256,
            "loader": "cas_meta2.curriculum_v3.registered_development_exclusions"}:
        raise ValueError("V3_REGISTERED_EXCLUSIONS_MISMATCH")
    if (execution.get("phase_seconds") != PHASE_SECONDS or sum(PHASE_SECONDS.values()) != MAX_WALL_SECONDS
            or type(execution.get("max_wall_seconds")) is not int or execution["max_wall_seconds"] != MAX_WALL_SECONDS
            or execution.get("hard_resource_cutoff_seconds") != 7200 or execution.get("native_workers") != WORKERS
            or execution.get("automatic_retries") != 0 or execution.get("expanded_output_ceiling_bytes") != MAX_OUTPUT_BYTES
            or execution.get("compressed_packet_ceiling_bytes") != 1024**3
            or execution.get("total_owner_cap_usd") != "400.00" or execution.get("per_launch_reserved_cap_usd") != "7.00"):
        raise ValueError("V3_REGISTERED_EXECUTION_BOUND_MISMATCH")
    gates = spec["gpu_gates"]
    if (gates.get("launcher_early") != {"old_policy": 4, "copy_policy": 10, "weighted_loss": 13, "native_contract": 4}
            or gates.get("campaign") != {"actual_copy_modes": 3, "trainer_integration": 2}
            or gates.get("actual_copy_test_file") != GPU_GROUPS["actual_copy"][0]
            or gates.get("trainer_test_file") != GPU_GROUPS["trainer"][0]
            or gates.get("preflight") != "cas_meta2.gpu_preflight_copy_v3.run_preflight"
            or spec["evaluation"].get("arms") != list(ARMS)
            or spec["evaluation"]["checkpoints"].get("format") != "cas-meta2-candidate-checkpoint/3"):
        raise ValueError("V3_REGISTERED_GATE_OR_ARM_MISMATCH")
    if (spec["selection"].get("fixed_depth_denominators") != {"1": 32, "2": 32, "3": 32}
            or spec["selection"].get("train_probe_used_for_selection") is not False
            or spec["selection"].get("priority") != ["worst-depth generated joint accuracy",
                "macro-depth generated joint accuracy", "overall generated joint accuracy",
                "lower unweighted validation token NLL", "earliest eligible epoch"]
            or spec["loss"] != {"semantic_weight": 3.0, "structural_weight": 1.0, "padding_weight": 0.0,
                "normalization": "total positive weight", "same_for_all_learned_families": True}):
        raise ValueError("V3_REGISTERED_SELECTION_OR_LOSS_MISMATCH")
    if (spec["protected"].get("baseline_sha") != "0917267b1354e5d036263eaa6ba9a7197eafb776"
            or spec["protected"].get("executor") != "cas_meta2.executor"
            or spec["protected"].get("native_adapter") != "cas_meta2.native"
            or spec["protected"].get("action_codec") != "cas_meta2.codec"):
        raise ValueError("V3_PROTECTED_RUNTIME_MISMATCH")
    return spec


def experiment_identity():
    path = ROOT / SPEC_NAME
    spec = validate_experiment(_read(path))
    identity = {"profile": PROFILE, "entrypoint": ENTRYPOINT,
        "spec_path": "research/CAS_META_2_COMPOSITION/" + SPEC_NAME, "spec_sha256": _hash(path)}
    expected = {"CAS_META2_EXPERIMENT_PROFILE": PROFILE, "CAS_META2_EXPERIMENT_ENTRYPOINT": ENTRYPOINT,
                "CAS_META2_EXPERIMENT_SPEC_SHA256": identity["spec_sha256"]}
    if any(os.environ.get(name) != value for name, value in expected.items()):
        raise ValueError("V3_LAUNCHER_SPEC_BINDING_REQUIRED")
    if (os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1"
            or re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None
            or sys.platform != "linux"):
        raise ValueError("V3_AWS_LINUX_CUDA_AUTHORIZATION_REQUIRED")
    return identity, spec


def _new_output(output):
    raw = Path(output).absolute()
    if any(item.is_symlink() or getattr(item, "is_junction", lambda: False)() for item in (raw, *raw.parents)):
        raise ValueError("V3_OUTPUT_LINK_REFUSED")
    resolved = raw.resolve()
    if resolved == ROOT or not resolved.is_relative_to(ROOT) or resolved.exists():
        raise ValueError("V3_NEW_OUTPUT_INSIDE_CANDIDATE_REQUIRED")
    resolved.mkdir(parents=True, exist_ok=False)
    return resolved


def _phase_deadline(deadline, name):
    _deadline(deadline)
    return min(deadline, time.monotonic() + PHASE_SECONDS[name])


def _arm_deadline(end):
    if hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"):
        remaining = end - time.monotonic()
        # Once an alarm has fired, keep the remaining final-receipt window free
        # of repeated alarms. Explicit deadline checks still refuse more work.
        signal.setitimer(signal.ITIMER_REAL, max(0.01, remaining) if remaining > 0 else 0)


def _stop_group(process):
    """Terminate the complete Linux pytest/child group, not just its parent."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    if process.poll() is None:
        process.wait(timeout=2.0)


def _run_process(command, directory, deadline, *, environment=None):
    """Retain raw files and exact command even when a subprocess fails."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    _deadline(deadline)
    started, started_utc = time.monotonic(), datetime.now(timezone.utc).isoformat()
    record = {"schema": "cas-meta2-campaign-subprocess/3", "command": list(command), "cwd": str(ROOT),
        "started_utc": started_utc, "completed": False, "returncode": None, "timed_out": False,
        "new_process_group": os.name == "posix", "automatic_retry": False,
        "stdout": str(directory / "stdout.txt"), "stderr": str(directory / "stderr.txt")}
    process, error_text = None, None
    try:
        with (directory / "stdout.txt").open("xb") as stdout, (directory / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                start_new_session=os.name == "posix")
            record["pid"] = process.pid
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            record["returncode"] = process.returncode
            record["completed"] = process.returncode == 0
    except BaseException as error:
        record["timed_out"] = isinstance(error, (subprocess.TimeoutExpired, TimeoutError))
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        error_text = type(error).__name__ + ":" + str(error)
        if process is not None:
            _stop_group(process)
            record["returncode"] = process.returncode
    finally:
        record["wall_seconds"] = time.monotonic() - started
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        for name in ("stdout", "stderr"):
            path = Path(record[name])
            if path.is_file():
                record[name + "_sha256"] = _hash(path)
        _write(directory / "process_receipt.json", record)
    if not record["completed"]:
        if process is not None:
            _stop_group(process)
        raise RuntimeError("V3_SUBPROCESS_FAILED:" + (error_text or str(record["returncode"])))
    _deadline(deadline)
    return record


def _construct_data(output, seed, deadline):
    data = Path(output) / "dataset"
    command = [sys.executable, "-B", "-c",
        "import sys;from cas_meta2.curriculum_v3 import write_dataset,registered_development_exclusions;"
        "write_dataset(sys.argv[1],seed=int(sys.argv[2]),excluded_graph_signatures=registered_development_exclusions())",
        str(data), str(seed)]
    process = _run_process(command, Path(output) / "dataset_construction", deadline)
    receipt = {"schema": "cas-meta2-dataset-construction/3", "completed": True, "separate_process": True,
        "command": command, "returncode": process["returncode"],
        "process_receipt": str(Path(output) / "dataset_construction" / "process_receipt.json"),
        "process_receipt_sha256": _hash(Path(output) / "dataset_construction" / "process_receipt.json"),
        "dataset_manifest_sha256": _hash(data / "dataset_manifest.json"),
        "seed": seed, "combined_excluded_graphs": 4488,
        "boundary": "Constructor owns private labels and exits; learner does not inherit its objects. Construction-first synthetic truth, not a native-answer result."}
    _write(Path(output) / "dataset_construction_receipt.json", receipt)
    return data


def _validate_data_public(data, spec):
    from .curriculum_v3 import validate_manifest, registered_development_exclusions
    data = Path(data)
    manifest = _read(data / "dataset_manifest.json")
    checked = validate_manifest(manifest, expected_counts=spec["curriculum"]["counts"],
        expected_seed=spec["curriculum"]["seed"], excluded_graph_signatures=registered_development_exclusions())
    for name, digest in manifest["sha256"].items():
        path = data / name
        if path.is_symlink() or _hash(path) != digest:
            raise RuntimeError("V3_DATASET_PARTITION_BYTES_CHANGED:" + name)
    return checked


def _xml_receipt(path, expected):
    tree = ET.parse(path)
    cases = tree.findall(".//testcase")
    if tree.getroot().tag == "testcase":
        cases = [tree.getroot()]
    rows = [{"classname": case.attrib.get("classname"), "name": case.attrib.get("name"),
             "failed": case.find("failure") is not None, "error": case.find("error") is not None,
             "skipped": case.find("skipped") is not None} for case in cases]
    if (len(cases) != expected or len({(row["classname"], row["name"]) for row in rows}) != expected
            or any(row["failed"] or row["error"] or row["skipped"] for row in rows)
            or tree.findall(".//error") or tree.findall(".//failure")):
        raise RuntimeError("V3_GPU_JUNIT_FULL_PASS_REQUIRED")
    return {"path": str(path), "sha256": _hash(path), "tests": len(cases), "passed": len(cases),
            "failed": 0, "errors": 0, "skipped": 0, "cases": rows}


def run_gpu_gates(data, output, deadline):
    """New-data-dependent tests only; launcher owns the earlier 27+4 cases."""
    train_path = Path(data) / "train.json"
    train_hash = _hash(train_path)
    receipt = {"schema": "cas-meta2-campaign-gpu-gates/3", "completed": False, "groups": {},
        "training_file": str(train_path), "training_sha256": train_hash,
        "expected_total_cases": 5, "actual_copy_modes": 3, "trainer_integration_cases": 2,
        "boundary": "AWS software/CUDA checks, not learned held-out performance."}
    _write(Path(output) / "gpu_gates_v3.json", receipt)
    environment = {**os.environ, "CAS_META2_COPY_PREFLIGHT_TRAIN_JSON": str(train_path),
        "CAS_META2_COPY_PREFLIGHT_TRAIN_SHA256": train_hash, "PYTHONDONTWRITEBYTECODE": "1"}
    for group, (test_file, expected, phase) in GPU_GROUPS.items():
        directory = Path(output) / "gpu_tests" / group
        xml = directory / "junit.xml"
        command = [sys.executable, "-B", "-m", "pytest", "-m", "gpu", "-q", "-p", "no:cacheprovider",
            "--junitxml=" + str(xml), "--basetemp=" + str(directory / "basetemp"), test_file]
        process = _run_process(command, directory, _phase_deadline(deadline, phase), environment=environment)
        receipt["groups"][group] = {"test_file": test_file, "expected_cases": expected, "process": process,
            "process_receipt_sha256": _hash(directory / "process_receipt.json"), "junit": _xml_receipt(xml, expected)}
        _write(Path(output) / "gpu_gates_v3.json", receipt)
        if _hash(train_path) != train_hash:
            raise RuntimeError("V3_TRAINING_FILE_CHANGED_BY_GPU_GATE")
    receipt["completed"] = True
    receipt["passed_cases"] = sum(row["junit"]["passed"] for row in receipt["groups"].values())
    _write(Path(output) / "gpu_gates_v3.json", receipt)
    return receipt


def report_evaluation_groups(data, output):
    """Only called after all private native checks have finished."""
    tasks = _read(Path(data) / "test_private.json")
    evaluated = _read(Path(output) / "evaluation_results.json")["cases"]
    if len(tasks) != len(evaluated) or len(tasks) != 72:
        raise RuntimeError("V3_GROUP_CASE_DENOMINATOR_MISMATCH")
    groups = {}
    for index, (task, case) in enumerate(zip(tasks, evaluated, strict=True)):
        if case["case_index"] != index or case["task_id"] != task["task_id"]:
            raise RuntimeError("V3_GROUP_CASE_MAPPING_MISMATCH")
        groups.setdefault(task["provenance"]["evaluation_group"], []).append(case)
    if set(groups) != {"same_depth", "wording_shift", "deeper_calls"} or any(len(rows) != 24 for rows in groups.values()):
        raise RuntimeError("V3_GROUP_COUNTS_CHANGED")
    results = {group: aggregate_cases([{**row, "case_index": i} for i, row in enumerate(rows)], len(rows))
               for group, rows in groups.items()}
    receipt = {"schema": "cas-meta2-group-results/3", "groups": results,
        "group_case_indices": {name: [row["case_index"] for row in rows] for name, rows in groups.items()},
        "boundary": "24 matched triplets; not 72 independent graphs."}
    _write(Path(output) / "evaluation_groups.json", receipt)
    return results


def _final_payload_index(output):
    entries = {}
    for path in sorted(Path(output).rglob("*")):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise RuntimeError("V3_OUTPUT_LINK_DETECTED")
        if path.is_file() and path != Path(output) / "payload_sha256.json":
            entries[path.relative_to(output).as_posix()] = _hash(path)
    _write(Path(output) / "payload_sha256.json", entries)
    return _hash(Path(output) / "payload_sha256.json")


def run(output, max_wall_seconds=MAX_WALL_SECONDS, *, smoke_only=False):
    if type(max_wall_seconds) is not int or not 60 <= max_wall_seconds <= MAX_WALL_SECONDS:
        raise ValueError("V3_CAMPAIGN_WALL_BOUND_INVALID")
    if type(smoke_only) is not bool:
        raise ValueError("V3_SMOKE_FLAG_INVALID")
    # Caller/job/spec authorization is pure and precedes any neural import.
    experiment, spec = experiment_identity()
    output = _new_output(output)
    started = time.monotonic()
    deadline = started + max_wall_seconds
    stage, phase_records = "initialization", {}
    source_before, baseline_before = _source_identity(), None
    old_alarm = None
    def interrupted(signum, frame):
        raise TimeoutError("V3_CAMPAIGN_HARD_WALL_SIGNAL:" + str(signum))
    if hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"):
        old_alarm = signal.signal(signal.SIGALRM, interrupted)
        signal.setitimer(signal.ITIMER_REAL, max(1, max_wall_seconds - 10))
    def phase(name, function):
        nonlocal stage
        stage = name
        beginning = time.monotonic()
        end = _phase_deadline(deadline, name)
        phase_records[name] = {"started_seconds": beginning - started, "cap_seconds": PHASE_SECONDS[name], "completed": False}
        try:
            _arm_deadline(min(end, deadline - 10))
            result = function(end)
            _deadline(end)
            phase_records[name]["completed"] = True
            return result
        finally:
            _arm_deadline(deadline - 10)
            phase_records[name]["wall_seconds"] = time.monotonic() - beginning
            _write(output / "phase_timing_v3.json", {"phase_seconds": PHASE_SECONDS, "phases": phase_records})
    try:
        _write(output / "campaign_receipt.json", {"schema": SCHEMA, "status": "CAS_META_2_V3_AWS_CAMPAIGN_RUNNING",
            "completed": False, "evaluation_completed": False, "stage": stage, "experiment": experiment,
            "max_wall_seconds": max_wall_seconds, "automatic_retry": False})
        from .train_v3 import TrainingConfig, environment_identity, setup_cuda, train_and_seal
        from .policy_v3 import PolicyConfig
        _, device = setup_cuda(spec["training"]["seed"])
        registered = {**spec["training"], "policy": PolicyConfig(**spec["training"]["policy"])}
        config = TrainingConfig(**registered)
        config.validate()
        _write(output / "environment.json", environment_identity(device))
        baseline_before = _baseline_identity()
        data = phase("dataset_construction", lambda end: _construct_data(output, spec["curriculum"]["seed"], end))
        public_data = _validate_data_public(data, spec)
        _write(output / "public_dataset_check_v3.json", public_data)
        stage = "campaign_gpu_tests"
        gates = run_gpu_gates(data, output, deadline)
        training_tasks = _read(data / "train.json")
        from .gpu_preflight_copy_v3 import run_preflight
        preflight = phase("actual_copy_preflight", lambda end: run_preflight(training_tasks, config, output, end))
        if (preflight.get("completed") is not True or preflight.get("actual_copy_policy") is not True
                or preflight.get("frozen_v2_geometry_called") is not False
                or preflight.get("cuda_allocated_bytes_after_cleanup") != 0
                or preflight.get("cuda_reserved_bytes_after_cleanup") != 0):
            raise RuntimeError("V3_ACTUAL_COPY_PREFLIGHT_NOT_FULLY_CLEAN")
        smoke = phase("native_smoke", lambda end: run_smoke(training_tasks, output, end))
        del training_tasks
        if smoke_only:
            if _source_identity() != source_before:
                raise RuntimeError("V3_CAMPAIGN_SOURCE_CHANGED")
            baseline_after = _baseline_identity()
            if baseline_after != baseline_before:
                raise RuntimeError("V3_ACCEPTED_BASELINE_IDENTITY_CHANGED")
            receipt = {"schema": SCHEMA, "status": "CAS_META_2_V3_AWS_SMOKE_COMPLETED",
                "completed": True, "evaluation_completed": False, "smoke_only": True,
                "smoke": smoke, "gpu_preflight": preflight, "gpu_gates": gates,
                "training_performed": False, "candidate_checkpoint_created": False,
                "authored_gpu_fixture_checkpoint_files_created": True,
                "experiment": experiment, "aws_job_id": os.environ["CAS_META2_AWS_JOB_ID"],
                "source": source_before, "baseline_before": baseline_before,
                "baseline_after": baseline_after, "max_wall_seconds": max_wall_seconds,
                "phase_seconds": PHASE_SECONDS, "phases": phase_records,
                "wall_seconds": time.monotonic() - started, "output_bytes": _output_bytes(output),
                "boundary": "Runtime and authored CUDA fixture smoke only; no curriculum learning or candidate selection."}
            _write(output / "campaign_receipt.json", receipt)
            _final_payload_index(output)
            return receipt
        stage = "paired_training_and_prediction_seal"
        protected_reserve = PHASE_SECONDS["native_evaluation"] + PHASE_SECONDS["final_evidence"]
        required = PHASE_SECONDS["paired_training"] + PHASE_SECONDS["prediction_seal"] + protected_reserve
        if deadline - time.monotonic() < required:
            raise TimeoutError("V3_INSUFFICIENT_TIME_FOR_REGISTERED_LEARNING_AND_EVALUATION_RESERVES")
        learning_deadline = min(deadline - protected_reserve,
            time.monotonic() + PHASE_SECONDS["paired_training"] + PHASE_SECONDS["prediction_seal"])
        learning_started = time.monotonic()
        try:
            _arm_deadline(learning_deadline)
            learned = train_and_seal(data, output, config, learning_deadline)
        finally:
            _arm_deadline(deadline - 10)
        _deadline(learning_deadline)
        phase_records["paired_training_and_prediction_seal"] = {
            "completed": True, "wall_seconds": time.monotonic() - learning_started,
            "training_allocation_seconds": PHASE_SECONDS["paired_training"],
            "prediction_reserve_seconds": PHASE_SECONDS["prediction_seal"]}
        cleanup = _read(output / "training_cleanup_v3.json")
        if (cleanup.get("completed") is not True or cleanup.get("failures")
                or cleanup.get("status") != "CAS_META_2_V3_TRAINING_CLEANUP_PASSED"):
            raise RuntimeError("V3_TRAINING_CLEANUP_REQUIRED_BEFORE_NATIVE_EVALUATION")
        evaluation = phase("native_evaluation", lambda end: evaluate_sealed(data, output, learned["seal"], end))
        stage = "final_evidence"
        final_deadline = _phase_deadline(deadline, "final_evidence")
        _arm_deadline(min(final_deadline, deadline - 10))
        group_results = report_evaluation_groups(data, output)
        _validate_data_public(data, spec)
        baseline_after = _baseline_identity()
        if baseline_after != baseline_before:
            raise RuntimeError("V3_ACCEPTED_BASELINE_IDENTITY_CHANGED")
        if _source_identity() != source_before:
            raise RuntimeError("V3_CAMPAIGN_SOURCE_CHANGED")
        if _hash(output / "predictions.jsonl") != learned["seal"]["sha256"]:
            raise RuntimeError("V3_SEALED_PREDICTIONS_CHANGED")
        result = evaluation["results"]
        if (evaluation["cases"] != 72 or evaluation["arm_verdicts"] != 360
                or any(result[arm]["total"] != 72 for arm in ARMS)):
            raise RuntimeError("V3_FINAL_FULL_DENOMINATORS_REQUIRED")
        receipt = {"schema": SCHEMA, "status": "CAS_META_2_V3_AWS_CAMPAIGN_COMPLETED",
            "completed": True, "evaluation_completed": True, "smoke_only": False,
            "experiment": experiment, "aws_job_id": os.environ["CAS_META2_AWS_JOB_ID"],
            "source": source_before, "baseline_before": baseline_before,
            "baseline_after": baseline_after, "smoke": smoke, "gpu_preflight": preflight, "gpu_gates": gates,
            "training": learned["training"], "training_cleanup": cleanup, "prediction_seal": learned["seal"],
            "evaluation_groups": group_results, "results": result, "reference_cases": evaluation["reference_cases"],
            "all_test_cases_evaluated_per_arm": evaluation["cases"], "arm_verdicts": evaluation["arm_verdicts"],
            "cas_task_accuracy_gain": result["cas_trained"]["task_accuracy"] - result["cas_untrained"]["task_accuracy"],
            "generic_task_accuracy_gain": result["generic_trained"]["task_accuracy"] - result["generic_untrained"]["task_accuracy"],
            "workers": WORKERS, "max_wall_seconds": max_wall_seconds, "phase_seconds": PHASE_SECONDS, "phases": phase_records,
            "wall_seconds": time.monotonic() - started, "output_bytes": _output_bytes(output),
            "expanded_output_ceiling_bytes": MAX_OUTPUT_BYTES, "automatic_retry": False,
            "claim_boundary": spec["claim_boundary"]}
        _deadline(final_deadline)
        _write(output / "campaign_receipt.json", receipt)
        _final_payload_index(output)
        _deadline(final_deadline)
        print(json.dumps({"status": receipt["status"], "results": result}, sort_keys=True), flush=True)
        return receipt
    except BaseException as error:
        receipt = {"schema": SCHEMA, "status": "CAS_META_2_V3_AWS_CAMPAIGN_BLOCKED",
            "completed": False, "evaluation_completed": False, "stage": stage,
            "typed_reason": type(error).__name__ + ":" + str(error)[:4096], "traceback": traceback.format_exc()[-16000:],
            "source": source_before, "experiment": experiment, "aws_job_id": os.environ["CAS_META2_AWS_JOB_ID"],
            "baseline_before": baseline_before,
            "wall_seconds": time.monotonic() - started, "max_wall_seconds": max_wall_seconds,
            "phase_seconds": PHASE_SECONDS, "phases": phase_records,
            "partial_artifacts_retained": True, "automatic_retry": False}
        _write(output / "campaign_receipt.json", receipt)
        print(json.dumps({"status": receipt["status"], "typed_reason": receipt["typed_reason"]}), flush=True)
        raise
    finally:
        if old_alarm is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_alarm)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-wall-seconds", type=int, default=MAX_WALL_SECONDS)
    parser.add_argument("--smoke-only", action="store_true")
    arguments = parser.parse_args()
    run(arguments.output, arguments.max_wall_seconds, smoke_only=arguments.smoke_only)


if __name__ == "__main__":
    main()
