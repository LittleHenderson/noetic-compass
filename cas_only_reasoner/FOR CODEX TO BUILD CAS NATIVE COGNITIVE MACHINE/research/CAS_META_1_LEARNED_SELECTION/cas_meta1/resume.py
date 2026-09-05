"""AWS-only, evaluation-only recovery of the immutable first-run predictions.

No training, selector inference, changed answers, or dropped test cases. Separate
spawned processes own separate native stores and share only read-only source.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import cProfile
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import multiprocessing
import os
from pathlib import Path
import pstats
import time
import shutil

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("cas_untrained", "cas_trained", "rule", "generic_untrained", "generic_trained")
ORIGINAL_SOURCE = "a4dc9f2fc6f6d4f3d5e0b31100ac131327e02109"
ORIGINAL_JOB = "cas-meta1-20260905103339-cd06685e"
ORIGINAL_PACKET = "76fbb522a97e3018e946857ce71599fbdea8bb6daffd29bd15fb7cf2d091f7a0"
ORIGINAL_PREDICTIONS = "00e7a2b7d72c86d4dc9d7bdb3dd74f2c7338bb650b7e7e8136dfa6dd9ee09bc8"
MAX_OUTPUT = 900 * 1024 * 1024
_CUDA_CONTEXT = None


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    os.replace(temporary, path)


def file_hash(path):
    digest = sha256()
    with Path(path).open("rb") as source:
        for part in iter(lambda: source.read(1024*1024), b""):
            digest.update(part)
    return digest.hexdigest()


def rebound_result(result, directory):
    """Change only in-memory locations; never rewrite original durable evidence."""
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT):
        raise ValueError("REBOUND_EVIDENCE_OUTSIDE_PILOT")
    return {**result, "output_dir": str(directory), "native_database": str(directory/"native.db"),
            "semantic_projection_path": str(directory/"semantic_projection.json")}


def validate_inputs(training, data):
    training, data = Path(training), Path(data)
    predictions = read(training/"predictions.json")
    seal = read(training/"predictions_seal.json")
    opening = read(training/"test_gold_opening_receipt.json")
    if file_hash(training/"predictions.json") != ORIGINAL_PREDICTIONS or seal["sha256"] != ORIGINAL_PREDICTIONS:
        raise ValueError("ORIGINAL_PREDICTION_SEAL_CHANGED")
    if seal["test_private_labels_loaded"] is not False or opening["prediction_sha256_before_opening"] != ORIGINAL_PREDICTIONS:
        raise ValueError("ORIGINAL_GOLD_CUSTODY_INVALID")
    if datetime.fromisoformat(seal["sealed_utc"]) >= datetime.fromisoformat(opening["opened_utc"]):
        raise ValueError("GOLD_OPENED_BEFORE_PREDICTION_SEAL")
    manifest = read(data/"dataset_manifest.json")
    for name, expected in manifest["sha256"].items():
        if file_hash(data/name) != expected:
            raise ValueError("DATASET_BYTES_CHANGED")
    if predictions["test_public_sha256"] != manifest["sha256"]["test_public.json"]:
        raise ValueError("PREDICTIONS_DATASET_MISMATCH")
    if opening["test_private_sha256"] != manifest["sha256"]["test_private.json"]:
        raise ValueError("PRIVATE_DATASET_CHANGED")
    publics, tasks = read(data/"test_public.json"), read(data/"test_private.json")
    if len(tasks) != 72 or len(publics) != 72 or set(predictions["arms"]) != set(ARMS):
        raise ValueError("ORIGINAL_DENOMINATORS_REQUIRED")
    from .curriculum import permitted_view
    from .execution import validate_action
    for index, (task, public) in enumerate(zip(tasks, publics, strict=True)):
        if permitted_view(task) != public:
            raise ValueError("PUBLIC_PRIVATE_MAPPING_CHANGED")
        for arm in ARMS:
            if len(predictions["arms"][arm]) != 72 or validate_action(public, predictions["arms"][arm][index]):
                raise ValueError("INVALID_ORIGINAL_ACTION_SET")
    checkpoints = read(training/"checkpoints.json")
    for family in ("cas", "generic"):
        if checkpoints[family]["optimizer_steps"] != 840:
            raise ValueError("ORIGINAL_TRAINING_STEPS_CHANGED")
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            if file_hash(training/f"{family}_{suffix}.pt") != checkpoints[family][state]["sha256"]:
                raise ValueError("ORIGINAL_CHECKPOINT_CHANGED")
    return tasks, publics, predictions, checkpoints


def work_items(predictions):
    # All cases are repeated on the same new hardware for comparable evidence.
    # No case or arm is selected based on its correct/incorrect outcome.
    return [{"index": index, "actions": {arm: predictions["arms"][arm][index] for arm in ARMS}}
            for index in range(72)]


def setup_cuda():
    global _CUDA_CONTEXT
    if _CUDA_CONTEXT is not None:
        return _CUDA_CONTEXT
    import torch
    from .policy import require_cuda
    device = require_cuda("cuda")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    _CUDA_CONTEXT = (torch, device)
    return _CUDA_CONTEXT


def require_healthy_execution(result, verdict=None):
    from .execution import ExecutionInfrastructureError
    # All sealed actions name supported procedures and valid inputs. A runtime
    # failure is not evidence that the selector chose the wrong procedure.
    if result.get("status") != "EXECUTED":
        raise ExecutionInfrastructureError("VALID_ACTION_EXECUTION_FAILED:"+json.dumps(result.get("failure")))
    if verdict is not None and any(reason.startswith(("INVALID_DURABLE_EVIDENCE", "PRIVATE_REFERENCE_UNAVAILABLE"))
                                   for reason in verdict.get("reasons", [])):
        raise ExecutionInfrastructureError("DURABLE_VERIFICATION_UNAVAILABLE:"+json.dumps(verdict["reasons"]))


def stop_pool(pool):
    # Python 3.12 has no terminate_workers(). Capture its workers, then use the
    # public multiprocessing.Process stop methods with one shared deadline.
    processes = list((pool._processes or {}).values())
    pool.shutdown(wait=False, cancel_futures=True)
    for process in processes:
        if process.is_alive():
            process.terminate()
    limit = time.monotonic()+5
    for process in processes:
        process.join(timeout=max(0, limit-time.monotonic()))
        if process.is_alive():
            process.kill()


def profile_call(function, profile_base):
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        return function()
    finally:
        profiler.disable()
        profiler.dump_stats(str(profile_base)+".pstats")
        summary = io.StringIO()
        pstats.Stats(profiler, stream=summary).sort_stats("cumulative").print_stats(60)
        Path(str(profile_base)+".txt").write_text(summary.getvalue(), encoding="utf-8")


def run_case(item, task, public, output, old_training, deadline, profile=False):
    """One isolated process owns the new reference and all five arm executions."""
    from .execution import ExecutionInfrastructureError, execute_task, reference_task, verify_task
    from .train import _timed_cuda
    torch, device = setup_cuda()
    output, old_training = Path(output), Path(old_training)
    index, rows = item["index"], {}
    case = output/"cases"/f"case_{index:04d}"
    case.mkdir(parents=True, exist_ok=False)
    def require_time():
        if time.time() > deadline:
            raise RuntimeError("RECOVERY_TIME_CEILING")
    require_time()
    old_dir = old_training/"references"/f"case_{index:04d}"
    old_reference = rebound_result(read(old_dir/"result.json"), old_dir)
    # Fresh GPU reference avoids treating cross-GPU floating-point differences as
    # model errors. The prior T4 reference is retained and the difference reported.
    reference, reference_timing = _timed_cuda(
        lambda: reference_task(task, case/"reference", device=str(device)), device)
    require_healthy_execution(reference)
    if not verify_task(task, reference, reference)["success"]:
        raise ExecutionInfrastructureError("NEW_HARDWARE_REFERENCE_INVALID")
    for field in ("frozen_model_digest_after", "frozen_parameter_bytes_sha256_after", "input_tensor_bytes_sha256"):
        if reference[field] != old_reference[field]:
            raise ExecutionInfrastructureError("FROZEN_EXECUTOR_WEIGHTS_CHANGED_ACROSS_HARDWARE")
    reference_comparison = {"new_gpu": torch.cuda.get_device_name(device),
        "old_input_sha256": old_reference["input_tensor_bytes_sha256"],
        "new_input_sha256": reference["input_tensor_bytes_sha256"],
        "old_output_sha256": old_reference["output_tensor_bytes_sha256"],
        "new_output_sha256": reference["output_tensor_bytes_sha256"],
        "output_bytes_equal": old_reference["output_tensor_bytes_sha256"] == reference["output_tensor_bytes_sha256"],
        "new_reference_timing": reference_timing, "frozen_weight_bytes_unchanged": True}
    write(case/"reference_comparison.json", reference_comparison)
    for arm in ARMS:
        require_time()
        action = item["actions"][arm]
        before = time.perf_counter()
        run = lambda: execute_task(public, action, case/arm, device=str(device))
        try:
            if profile and arm == "cas_untrained":
                result, timing = _timed_cuda(lambda: profile_call(run, case/"execution_profile"), device)
                verdict = profile_call(lambda: verify_task(task, result, reference), case/"verification_profile")
            else:
                result, timing = _timed_cuda(run, device)
                verdict = verify_task(task, result, reference)
            require_healthy_execution(result, verdict)
        except ExecutionInfrastructureError:
            raise
        except Exception as exc:
            raise ExecutionInfrastructureError("SUPPORTED_ACTION_INFRASTRUCTURE_FAILURE:"+type(exc).__name__+":"+str(exc)) from exc
        rows[arm] = {"case_index": index, "action": action, "verification": verdict,
            "execution_status": result.get("status"), "failure": result.get("failure"),
            "reserved_policy_units": result.get("reserved_policy_units"), "repair_count": result.get("repair_count"),
            "execution_timing": timing, "evidence_directory": str(case/arm)}
        write(case/(arm+"_case_result.json"), rows[arm])
    write(case/"completed.json", {"case_index": index, "arms": rows, "reference_comparison": reference_comparison})
    return {"case_index": index, "arms": rows, "reference_comparison": reference_comparison}


def recount(completed, predictions):
    from .train import _aggregate
    if len(completed) != 72 or sorted(row["case_index"] for row in completed) != list(range(72)):
        raise ValueError("MISSING_OR_DUPLICATE_CASES")
    ordered = sorted(completed, key=lambda row: row["case_index"])
    results, all_rows = {}, {}
    for arm in ARMS:
        rows = [row["arms"][arm] for row in ordered]
        if [row["action"] for row in rows] != predictions["arms"][arm]:
            raise ValueError("EXECUTED_ACTIONS_DIFFER_FROM_ORIGINAL_SEAL")
        all_rows[arm] = rows
        results[arm] = _aggregate(rows)
    return results, all_rows


def run(data, predecessor, output, workers=8, max_wall_seconds=1650):
    if type(workers) is not int or workers not in (1, 2, 4, 8) or not 60 <= max_wall_seconds <= 1800:
        raise ValueError("INVALID_BOUNDED_RECOVERY_LIMITS")
    # Fail before any extraction, model construction, or evidence execution on CPU.
    torch, device = setup_cuda()
    from tools.inspect_cloud_packet import inspect_packet
    from .baseline import verify_baseline, verify_installed_wheels
    output, predecessor, data = Path(output).resolve(), Path(predecessor).resolve(), Path(data).resolve()
    if not output.is_relative_to(ROOT/"runs") or output.exists() or not predecessor.is_relative_to(ROOT):
        raise ValueError("NEW_OWNED_RECOVERY_OUTPUT_REQUIRED")
    output.mkdir(parents=True)
    started = time.time()
    deadline = started + max_wall_seconds
    job = os.environ.get("CAS_META1_AWS_JOB_ID", "")
    if not job.startswith("cas-meta1-") or "/" in job or "\\" in job:
        raise ValueError("BOUNDED_AWS_JOB_ID_REQUIRED")
    baseline_before = {"source": verify_baseline(), "wheels": verify_installed_wheels()}
    incoming = ROOT/"records"/"incoming"/job
    try:
        packet = inspect_packet(predecessor/"cloud_artifacts.zip", predecessor/"launch_receipt.json", extract_to=incoming)
        if packet["archive_sha256"] != ORIGINAL_PACKET or packet["source_sha"] != ORIGINAL_SOURCE or packet["job"] != ORIGINAL_JOB or packet["partial_evidence"]:
            raise ValueError("EXACT_FULL_PREDECESSOR_PACKET_REQUIRED")
        training = incoming/"cloud_job"/"training"
        tasks, publics, predictions, checkpoints = validate_inputs(training, data)
        for name in ("predictions.json", "predictions_seal.json", "test_gold_opening_receipt.json", "checkpoints.json"):
            shutil.copyfile(training/name, output/name)
        write(output/"predecessor_inspection.json", packet)
        write(output/"custody.json", {"original_source": ORIGINAL_SOURCE, "original_job": ORIGINAL_JOB,
            "original_packet_sha256": ORIGINAL_PACKET, "original_predictions_sha256": ORIGINAL_PREDICTIONS,
            "recovery_source": os.environ.get("CAS_META1_SOURCE_SHA"), "training_performed": False,
            "selector_predictions_changed": False, "private_targets_changed": False,
            "checkpoints": checkpoints, "workers": workers, "all_cases_repeated_on_new_hardware": True,
            "gpu": torch.cuda.get_device_name(device), "cpu_threads_per_worker": 1,
            "timing_boundary": "Concurrent per-process CUDA spans include host gaps; not additive kernel time."})
        items = work_items(predictions)
        completed = []
        def progress(stage):
            size = 0
            for path in output.rglob("*"):
                try:
                    if path.is_file():
                        size += path.stat().st_size
                except FileNotFoundError:
                    pass  # Another worker atomically renamed its temporary JSON.
            if size > MAX_OUTPUT:
                raise RuntimeError("RECOVERY_OUTPUT_CEILING")
            write(output/"progress.json", {"utc": datetime.now(timezone.utc).isoformat(), "stage": stage,
                "completed_cases": len(completed), "total_cases": 72, "completed_arm_executions": len(completed)*5,
                "total_arm_executions": 360, "wall_seconds": time.time()-started, "output_bytes": size})
        progress("single_case_profile")
        # Fixed case zero is profiled first, independently of model correctness.
        context = multiprocessing.get_context("spawn")
        pool = ProcessPoolExecutor(max_workers=workers, mp_context=context)
        try:
            first = pool.submit(run_case, items[0], tasks[0], publics[0], output, training, deadline, True)
            completed.append(first.result(timeout=min(360, max_wall_seconds)))
            progress("parallel_verification")
            futures = [pool.submit(run_case, item, tasks[item["index"]], publics[item["index"]],
                       output, training, deadline, False) for item in items[1:]]
            for future in as_completed(futures, timeout=max(1, deadline-time.time())):
                completed.append(future.result())
                progress("parallel_verification")
        except BaseException as exc:
            write(output/"worker_failure.json", {"type": type(exc).__name__, "message": str(exc),
                 "completed_cases": len(completed), "wall_seconds": time.time()-started})
            stop_pool(pool)
            raise
        else:
            pool.shutdown(wait=True)
        results, rows = recount(completed, predictions)
        for arm in ARMS:
            write(output/(arm+"_case_results.json"), rows[arm])
        baseline_after = {"source": verify_baseline(), "wheels": verify_installed_wheels()}
        if baseline_before != baseline_after:
            raise RuntimeError("PROTECTED_BASELINE_CHANGED")
        if file_hash(training/"predictions.json") != ORIGINAL_PREDICTIONS:
            raise RuntimeError("SEALED_PREDICTIONS_CHANGED")
        validate_inputs(training, data)
        receipt = {"status": "CAS_META_1_EVALUATION_RECOVERY_COMPLETED", "results": results,
            "cas_actual_success_gain": results["cas_trained"]["success_rate"]-results["cas_untrained"]["success_rate"],
            "generic_actual_success_gain": results["generic_trained"]["success_rate"]-results["generic_untrained"]["success_rate"],
            "source_sha": os.environ.get("CAS_META1_SOURCE_SHA"), "original_source_sha": ORIGINAL_SOURCE,
            "original_packet_sha256": ORIGINAL_PACKET, "original_prediction_sha256": ORIGINAL_PREDICTIONS,
            "cases_per_arm": 72, "arms": 5, "new_reference_count": 72,
            "cross_gpu_reference_output_differences": sum(not row["reference_comparison"]["output_bytes_equal"] for row in completed),
            "training_performed": False, "selector_forward_performed": False, "checkpoints": checkpoints,
            "baseline_before": baseline_before, "baseline_after": baseline_after,
            "gpu": torch.cuda.get_device_name(device), "workers": workers, "total_wall_seconds": time.time()-started,
            "claim_boundary": "Fixed three-procedure synthetic pilot, one seed. No CAS-specific advantage or general reasoning claim."}
        write(output/"receipt.json", receipt)
        progress("completed")
        write(output/"payload_sha256.json", {str(p.relative_to(output)): file_hash(p) for p in sorted(output.rglob("*"))
             if p.is_file() and p.name != "payload_sha256.json"})
        print(json.dumps({"status": receipt["status"], "results": results}), flush=True)
        return receipt
    except BaseException as exc:
        write(output/"recovery_failure.json", {"status": "CAS_META_1_RECOVERY_INCOMPLETE", "type": type(exc).__name__,
             "message": str(exc), "wall_seconds": time.time()-started, "completed": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-wall-seconds", type=int, default=1650)
    args = parser.parse_args()
    run(args.data, args.predecessor, args.output, args.workers, args.max_wall_seconds)


if __name__ == "__main__":
    main()
