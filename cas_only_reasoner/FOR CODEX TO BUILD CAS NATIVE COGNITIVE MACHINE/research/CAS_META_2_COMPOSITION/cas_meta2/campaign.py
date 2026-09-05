"""Bounded AWS-only composition pilot: smoke, learn, seal, then native checks.

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
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from .codec import canonical_sha256, validate_action
from .curriculum import check_native_topology, parse_problem, permitted_view
from .ir import validate_program


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
MAX_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024
MAX_WALL_SECONDS = 6600
WORKERS = 8


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
    paths += [path for path in (ROOT / "pyproject.toml", ROOT / "BASELINE_MANIFEST.json") if path.is_file()]
    return {str(path.relative_to(ROOT)): _hash(path) for path in sorted(paths)}


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
    # Curriculum names stop below p15. This extra wrapper tests real depth,
    # without taking an example or label from the held-out partition.
    if "p15" in program["procedures"]:
        raise RuntimeError("SMOKE_WRAPPER_NAME_COLLISION")
    program["procedures"]["p15"] = program["procedures"].pop("main")
    program["procedures"]["main"] = {
        "input": "arg", "allowed_cjts": ["A", "B", "C"],
        "steps": [{"kind": "CALL", "procedure": "p15", "input": "arg", "output": "v0"}],
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
    from .train import setup_cuda
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
    from .train import setup_cuda
    setup_cuda()


def _case_worker(job):
    from .native import execute_task, reference_task, verify_reference_task, verify_task
    from .train import setup_cuda
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


def _construct_data(output, seed, deadline):
    data = Path(output) / "dataset"
    # The construction process owns all partitions, exits, and does not share
    # label objects with the learner. The learner opens only permitted files.
    command = [sys.executable, "-B", "-c",
               "import sys;from cas_meta2.curriculum import write_dataset;"
               "write_dataset(sys.argv[1],seed=int(sys.argv[2]))", str(data), str(seed)]
    _deadline(deadline)
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=max(1.0, min(120.0, deadline - time.monotonic())), check=False)
    _write(Path(output) / "dataset_construction_receipt.json",
           {"command": command, "returncode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr,
            "separate_process": True,
            "boundary": "Construction-first synthetic fixture generation, not independently authored semantic truth."})
    if completed.returncode != 0:
        raise RuntimeError("DATASET_CONSTRUCTION_FAILED")
    return data


def run(output, max_wall_seconds=MAX_WALL_SECONDS, *, smoke_only=False, data=None, epochs=200):
    from .train import TrainingConfig, environment_identity, setup_cuda, train_and_seal
    if type(max_wall_seconds) is not int or not 60 <= max_wall_seconds <= MAX_WALL_SECONDS:
        raise ValueError("CAMPAIGN_WALL_BOUND_INVALID")
    if type(epochs) is not int or not 1 <= epochs <= 200:
        raise ValueError("CAMPAIGN_EPOCH_BOUND_INVALID")
    _, device = setup_cuda()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("CAMPAIGN_OUTPUT_MUST_BE_A_NEW_DIRECTORY")
    output.mkdir(parents=True)
    started = time.monotonic()
    deadline = started + max_wall_seconds
    stage = "preflight"
    source_before = _source_identity()
    baseline_before = None
    old_alarm = None
    def interrupted(signum, frame):
        raise TimeoutError("CAMPAIGN_HARD_WALL_SIGNAL:" + str(signum))
    if hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"):
        old_alarm = signal.signal(signal.SIGALRM, interrupted)
        signal.setitimer(signal.ITIMER_REAL, max(1, max_wall_seconds - 10))
    try:
        _write(output / "campaign_receipt.json", {"status": "CAS_META_2_AWS_CAMPAIGN_RUNNING",
               "completed": False, "evaluation_completed": False, "stage": stage,
               "max_wall_seconds": max_wall_seconds, "automatic_retry": False})
        _write(output / "environment.json", environment_identity(device))
        baseline_before = _baseline_identity()
        data = _construct_data(output, 20260906, deadline) if data is None else Path(data).resolve()
        manifest = _read(data / "dataset_manifest.json")
        for name, expected in manifest["sha256"].items():
            if name not in ("train.json", "validation.json", "test_public.json", "test_private.json"):
                raise RuntimeError("DATASET_MANIFEST_UNEXPECTED_FILE")
            if _hash(data / name) != expected:
                raise RuntimeError("DATASET_MANIFEST_MISMATCH")
        stage = "native_smoke"
        smoke = run_smoke(_read(data / "train.json"), output, deadline)
        if smoke_only:
            if _source_identity() != source_before:
                raise RuntimeError("CAMPAIGN_SOURCE_CHANGED")
            receipt = {
                "status": "CAS_META_2_AWS_SMOKE_COMPLETED", "completed": True,
                "evaluation_completed": False, "smoke_only": True, "smoke": smoke,
                "training_performed": False, "candidate_checkpoint_created": False,
                "source": source_before, "baseline_before": baseline_before,
                "baseline_after": _baseline_identity(), "max_wall_seconds": max_wall_seconds,
                "wall_seconds": time.monotonic() - started, "output_bytes": _output_bytes(output),
                "boundary": "CUDA native-runtime smoke only. No learning result or model-completion claim.",
            }
            _write(output / "campaign_receipt.json", receipt)
            return receipt
        stage = "paired_training_and_prediction_seal"
        remaining = deadline - time.monotonic()
        if remaining < 900:
            raise TimeoutError("INSUFFICIENT_TIME_AFTER_SMOKE_FOR_LEARNING_AND_NATIVE_EVALUATION")
        evaluation_reserve = min(1800.0, remaining * 0.35)
        learning_deadline = deadline - evaluation_reserve
        training_seconds = max(1, min(3300, int(learning_deadline - time.monotonic() - 300)))
        learned = train_and_seal(data, output,
                                 TrainingConfig(epochs=epochs, max_training_seconds=training_seconds),
                                 learning_deadline)
        stage = "held_out_native_evaluation"
        evaluation = evaluate_sealed(data, output, learned["seal"], deadline)
        stage = "final_evidence_checks"
        _deadline(deadline)
        baseline_after = _baseline_identity()
        if _source_identity() != source_before:
            raise RuntimeError("CAMPAIGN_SOURCE_CHANGED")
        if _hash(output / "predictions.jsonl") != learned["seal"]["sha256"]:
            raise RuntimeError("SEALED_PREDICTIONS_CHANGED")
        result = evaluation["results"]
        receipt = {
            "status": "CAS_META_2_AWS_CAMPAIGN_COMPLETED", "completed": True,
            "evaluation_completed": True, "smoke_only": False,
            "source": source_before, "baseline_before": baseline_before, "baseline_after": baseline_after,
            "smoke": smoke, "training": learned["training"], "prediction_seal": learned["seal"],
            "results": result, "reference_cases": evaluation["reference_cases"],
            "all_test_cases_evaluated_per_arm": evaluation["cases"], "arm_verdicts": evaluation["arm_verdicts"],
            "cas_task_accuracy_gain": result["cas_trained"]["task_accuracy"] - result["cas_untrained"]["task_accuracy"],
            "generic_task_accuracy_gain": result["generic_trained"]["task_accuracy"] - result["generic_untrained"]["task_accuracy"],
            "workers": WORKERS, "max_wall_seconds": max_wall_seconds,
            "wall_seconds": time.monotonic() - started, "output_bytes": _output_bytes(output),
            "expanded_output_ceiling_bytes": MAX_OUTPUT_BYTES, "automatic_retry": False,
            "claim_boundary": "One bounded synthetic program-generation pilot and seed. Completion means all comparisons were measured, not that learning improved or CAS is superior.",
            "open": ["General language understanding", "CAS-specific advantage", "full Noetic semantics",
                     "lifelong skill acquisition", "general recursion", "complete CNCM", "physical analog hardware"],
        }
        _write(output / "campaign_receipt.json", receipt)
        _write(output / "payload_sha256.json", {
            str(path.relative_to(output)): _hash(path)
            for path in sorted(output.rglob("*")) if path.is_file() and path.name != "payload_sha256.json"})
        print(json.dumps({"status": receipt["status"], "results": result}, sort_keys=True), flush=True)
        return receipt
    except BaseException as error:
        receipt = {
            "status": "CAS_META_2_AWS_CAMPAIGN_BLOCKED", "completed": False,
            "evaluation_completed": False, "stage": stage, "typed_reason": type(error).__name__ + ":" + str(error)[:4096],
            "traceback": traceback.format_exc()[-16000:], "source": source_before,
            "baseline_before": baseline_before, "wall_seconds": time.monotonic() - started,
            "max_wall_seconds": max_wall_seconds, "partial_artifacts_retained": True, "automatic_retry": False,
        }
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
    parser.add_argument("--data", type=Path)
    parser.add_argument("--epochs", type=int, default=200)
    arguments = parser.parse_args()
    run(arguments.output, arguments.max_wall_seconds, smoke_only=arguments.smoke_only,
        data=arguments.data, epochs=arguments.epochs)


if __name__ == "__main__":
    main()
