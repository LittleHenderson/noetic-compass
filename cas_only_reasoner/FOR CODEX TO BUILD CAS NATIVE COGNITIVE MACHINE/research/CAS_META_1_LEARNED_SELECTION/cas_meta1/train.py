"""Preregistered, CUDA-only learned-selection pilot; this module launches no AWS jobs.

Only train/validation labels are loaded before all held-out predictions are
sealed. Frozen native execution and an independent direct-native reference
grade every arm, including wrong selections and rejected executions.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

# Must precede the first Torch import/CUDA initialization in this entry point.
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
import torch
from torch.nn import functional as F

from .policy import (PolicyConfig, PublicTokenizer, build_matched_policies, canonical_sha256,
                     encode_batch, parameter_count, predict_public, require_cuda, validate_public)


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("cas_untrained", "cas_trained", "rule", "generic_untrained", "generic_trained")
MAX_OUTPUT_BYTES = 900 * 1024 * 1024


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 7
    epochs: int = 60
    batch_size: int = 64
    learning_rate: float = 0.003
    weight_decay: float = 0.01
    gradient_clip: float = 1.0
    max_wall_seconds: int = 3300
    policy: PolicyConfig = field(default_factory=PolicyConfig)

    def validate(self):
        self.policy.validate()
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("TRAINING_SEED_INVALID")
        if any(type(value) is not int or value < 1 for value in (self.epochs, self.batch_size, self.max_wall_seconds)):
            raise ValueError("TRAINING_LIMIT_INVALID")
        if self.epochs > 1000 or self.batch_size > 4096 or self.max_wall_seconds > 3600:
            raise ValueError("TRAINING_LIMIT_EXCEEDS_PILOT_BOUND")
        if not 0 < self.learning_rate <= 0.1 or not 0 <= self.weight_decay <= 1 or not 0 < self.gradient_clip <= 100:
            raise ValueError("TRAINING_OPTIMIZER_INVALID")


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str:
    checksum = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _require_time(deadline):
    if time.monotonic() >= deadline:
        raise RuntimeError("CAS_META_1_TIME_CEILING_REACHED:NO_AUTOMATIC_RETRY")


def _check_output_budget(output):
    used = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    if used > MAX_OUTPUT_BYTES:
        raise RuntimeError("CAS_META_1_OUTPUT_DISK_CEILING_REACHED")
    return used


def _source_identity():
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    paths = sorted(path for path in ROOT.rglob("*.py") if "runs" not in path.relative_to(ROOT).parts
                   and "__pycache__" not in path.parts)
    return {"git_sha": head, "declared_source_sha": os.environ.get("CAS_META1_SOURCE_SHA"),
            "python_source_sha256": {str(path.relative_to(ROOT)): _file_hash(path) for path in paths}}


def _timed_cuda(function, device):
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    baseline_memory = torch.cuda.memory_allocated(device)
    start_event = torch.cuda.Event(enable_timing=True)
    end_event = torch.cuda.Event(enable_timing=True)
    start = time.perf_counter()
    start_event.record()
    result = function()
    end_event.record()
    torch.cuda.synchronize(device)
    return result, {"wall_seconds": time.perf_counter() - start,
                    "cuda_event_elapsed_ms": start_event.elapsed_time(end_event),
                    "baseline_allocated_bytes": baseline_memory,
                    "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
                    "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
                    "timing_boundary": "Synchronized call span; CUDA-event elapsed includes host gaps, not summed kernel execution time."}


def _labels(tasks, device):
    procedures, bindings = [], []
    for task in tasks:
        target = task["target"]
        if type(target["procedure"]) is not int or target["procedure"] not in (0, 1, 2):
            raise ValueError("TRAIN_TARGET_PROCEDURE_INVALID")
        if type(target["binding"]) is not int or target["binding"] not in (0, 1, 2):
            raise ValueError("TRAIN_TARGET_BINDING_INVALID")
        procedures.append(target["procedure"])
        bindings.append(target["binding"])
    return (torch.tensor(procedures, dtype=torch.long, device=device),
            torch.tensor(bindings, dtype=torch.long, device=device))


def _classification_metrics(predictions, tasks):
    count = len(tasks)
    if len(predictions) != count or count == 0:
        raise ValueError("CLASSIFICATION_DENOMINATOR_INVALID")
    procedure = sum(action["procedure"] == task["target"]["procedure"] for action, task in zip(predictions, tasks, strict=True))
    binding = sum(action["binding"] == task["target"]["binding"] for action, task in zip(predictions, tasks, strict=True))
    joint = sum(action["procedure"] == task["target"]["procedure"] and action["binding"] == task["target"]["binding"]
                for action, task in zip(predictions, tasks, strict=True))
    return {"total": count, "procedure_correct": procedure, "binding_correct": binding,
            "joint_correct": joint, "joint_accuracy": joint / count}


def _checkpoint(path, model, *, tokenizer, config, epoch, validation, family):
    payload = {"schema": "cas-meta1-candidate-checkpoint/1", "family": family,
               "state_dict": model.state_dict(), "tokenizer_digest": tokenizer.digest,
               "training_config": asdict(config), "epoch": epoch, "validation": validation}
    torch.save(payload, path)
    return {"path": str(path), "sha256": _file_hash(path), "epoch": epoch, "validation": validation}


def _load_checkpoint(model, record, tokenizer, device):
    path = Path(record["path"])
    if _file_hash(path) != record["sha256"]:
        raise RuntimeError("CANDIDATE_CHECKPOINT_HASH_MISMATCH")
    payload = torch.load(path, map_location=device, weights_only=True)
    if payload["tokenizer_digest"] != tokenizer.digest:
        raise RuntimeError("CANDIDATE_TOKENIZER_BINDING_MISMATCH")
    model.load_state_dict(payload["state_dict"], strict=True)


def _train_family(model, family, tokenizer, train_tasks, validation_tasks, output, config, device, deadline):
    from .curriculum import permitted_view
    train_public = [permitted_view(task) for task in train_tasks]
    validation_public = [permitted_view(task) for task in validation_tasks]
    # Initial and selected-trained checkpoints are both preserved, separately.
    initial_validation = _classification_metrics(predict_public(model, tokenizer, validation_public,
                                                                device=device, batch_size=config.batch_size), validation_tasks)
    initial = _checkpoint(output / (family + "_initial.pt"), model, tokenizer=tokenizer,
                          config=config, epoch=0, validation=initial_validation, family=family)
    best = None
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate,
                                 weight_decay=config.weight_decay)
    generator = torch.Generator(device=device)
    generator.manual_seed(config.seed)
    history = []
    active_record = None
    steps = 0
    for epoch in range(1, config.epochs + 1):
        _require_time(deadline)
        model.train()
        indices = torch.randperm(len(train_tasks), generator=generator, device=device).tolist()
        total_loss = 0.0
        for offset in range(0, len(indices), config.batch_size):
            _require_time(deadline)
            batch_indices = indices[offset:offset + config.batch_size]
            tasks = [train_tasks[index] for index in batch_indices]
            publics = [train_public[index] for index in batch_indices]
            batch = encode_batch(publics, tokenizer, device=device)
            target_procedure, target_binding = _labels(tasks, device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch)
            loss = (F.cross_entropy(logits["procedure_logits"], target_procedure)
                    + F.cross_entropy(logits["binding_logits"], target_binding))
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError("NONFINITE_TRAINING_LOSS")
            loss.backward()
            if active_record is None:
                disconnected = [name for name, parameter in model.named_parameters()
                                if parameter.requires_grad and parameter.grad is None]
                connected = {name: parameter.numel() for name, parameter in model.named_parameters()
                             if parameter.requires_grad and parameter.grad is not None}
                active_record = {"connected_trainable_parameters": sum(connected.values()),
                                 "total_trainable_parameters": parameter_count(model),
                                 "connected_parameter_tensors": connected, "disconnected": disconnected,
                                 "training_device": str(device),
                                 "parameter_devices": sorted({str(parameter.device) for parameter in model.parameters()}),
                                 "batch_tensor_devices": {name: str(value.device) for name, value in batch.items()},
                                 "boundary": "Graph-connected parameter tensors; individual sparse embedding rows may have zero gradient in a batch."}
                _write(output / (family + "_active_parameter_receipt.json"), active_record)
                if disconnected:
                    raise RuntimeError("UNUSED_TRAINABLE_PARAMETER_TENSORS:" + ",".join(disconnected))
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip, error_if_nonfinite=True)
            optimizer.step()
            steps += 1
            total_loss += float(loss.detach().item()) * len(tasks)
        validation = _classification_metrics(predict_public(model, tokenizer, validation_public,
                                                             device=device, batch_size=config.batch_size), validation_tasks)
        # Fixed criterion: validation joint accuracy, earliest trained epoch wins ties.
        selected = best is None or validation["joint_correct"] > best["validation"]["joint_correct"]
        if selected:
            best = _checkpoint(output / (family + "_best.pt"), model, tokenizer=tokenizer,
                               config=config, epoch=epoch, validation=validation, family=family)
        history.append({"epoch": epoch, "optimizer_steps": steps, "train_loss": total_loss / len(train_tasks),
                        "validation": validation, "selected": selected})
        _write(output / (family + "_training_history.json"), history)
        print(json.dumps({"stage": "training", "family": family, "epoch": epoch,
                          "steps": steps, "device": str(device),
                          "validation_joint_correct": validation["joint_correct"]}), flush=True)
    assert best is not None
    last = _checkpoint(output / (family + "_last.pt"), model, tokenizer=tokenizer,
                       config=config, epoch=config.epochs, validation=history[-1]["validation"], family=family)
    expected_steps = config.epochs * math.ceil(len(train_tasks) / config.batch_size)
    if steps != expected_steps:
        raise RuntimeError("TRAINING_STEP_BUDGET_MISMATCH")
    return {"initial": initial, "selected": best, "last": last, "optimizer_steps": steps,
            "initial_validation": initial_validation, "active_parameters": active_record,
            "selection_rule": "Maximum validation procedure-and-binding joint accuracy; earliest trained epoch wins ties; test labels unavailable."}


def _failure(error):
    return {"code": "EXECUTION_EXCEPTION", "type": type(error).__name__, "message": str(error)[:2048]}


def _aggregate(rows):
    total = len(rows)
    metrics = {key: sum(row["verification"].get(key) is True for row in rows)
               for key in ("success", "procedure_correct", "binding_correct", "repair_correct", "output_correct", "evidence_valid")}
    repair_rows = [row for row in rows if row["verification"].get("repair_required") is True]
    known_units = [row["reserved_policy_units"] for row in rows if type(row.get("reserved_policy_units")) is int]
    return {"total": total, **metrics, "success_rate": metrics["success"] / total if total else None,
            "repair_required_total": len(repair_rows),
            "repair_required_correct": sum(row["verification"].get("repair_correct") is True for row in repair_rows),
            "execution_failures": sum(row["execution_status"] != "EXECUTED" for row in rows),
            "reserved_policy_units_total_known": sum(known_units),
            "reserved_policy_units_unknown_cases": total - len(known_units),
            "native_execution_wall_seconds": sum(row["execution_timing"].get("wall_seconds", 0) for row in rows),
            "all_cases_in_denominator": True}


def run(data: Path, output: Path, config: TrainingConfig):
    config.validate()
    device = require_cuda("cuda")  # No model construction or neural execution before this gate.
    from .baseline import verify_baseline, verify_installed_wheels
    from .curriculum import permitted_view, rule_select
    from .execution import ExecutionInfrastructureError, execute_task, reference_task, verify_task
    data, output = data.resolve(), output.resolve()
    allowed_output = (ROOT / "runs").resolve()
    if allowed_output not in output.parents or output.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW_DIRECTORY_INSIDE_PILOT_RUNS")
    output.mkdir(parents=True)
    start = time.monotonic()
    deadline = start + config.max_wall_seconds
    try:
        baseline_before = {"source": verify_baseline(), "installed_wheels": verify_installed_wheels()}
        source_before = _source_identity()
        manifest = _read(data / "dataset_manifest.json")
        expected_files = ("train.json", "validation.json", "test_public.json", "test_private.json")
        hashes = {name: _file_hash(data / name) for name in expected_files}
        if any(manifest["sha256"].get(name) != hashes[name] for name in expected_files):
            raise RuntimeError("DATASET_HASH_MISMATCH")
        train_tasks = _read(data / "train.json")
        validation_tasks = _read(data / "validation.json")
        test_public = _read(data / "test_public.json")
        if not train_tasks or not validation_tasks or not test_public:
            raise ValueError("EMPTY_DATASET_SPLIT")
        for public in test_public:
            validate_public(public)
        tokenizer = PublicTokenizer.fit_train([permitted_view(task) for task in train_tasks],
                                              max_length=config.policy.max_length)
        _write(output / "tokenizer.json", tokenizer.to_dict())
        preregistration = {"schema": "cas-meta1-run-preregistration/1", "config": asdict(config),
                           "arms": list(ARMS), "dataset_sha256": hashes,
                           "test_examples": len(test_public), "train_examples": len(train_tasks),
                           "validation_examples": len(validation_tasks),
                           "held_out_rule": "Test private labels are unopened until every arm prediction is sealed.",
                           "checkpoint_selection": "Validation joint procedure-and-binding accuracy; earliest trained epoch tie-break.",
                           "baseline_before": baseline_before, "source_before": source_before}
        _write(output / "preregistered_run.json", preregistration)
        _write(output / "environment.json", {
            "python": sys.version, "platform": platform.platform(), "executable": sys.executable,
            "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
            "cuda_device": str(device), "cuda_device_name": torch.cuda.get_device_name(device),
            "cuda_total_memory": torch.cuda.get_device_properties(device).total_memory,
            "utc_started": datetime.now(timezone.utc).isoformat(),
            "argv": sys.argv, "aws_execution_claim": "CUDA required; provider identity is bound separately by the AWS launcher."})
        # Only TRAIN anchors are used here. Failure aborts before learning;
        # this is a CUDA/runtime check, not a held-out accuracy result.
        anchors = {}
        for task in train_tasks:
            key = (task["target"]["procedure"], task["target"]["binding"])
            anchors.setdefault(key, task)
        if set(anchors) != {(procedure, binding) for procedure in range(3) for binding in range(3)}:
            raise RuntimeError("TRAIN_PREFLIGHT_REQUIRES_NINE_JOINT_CELLS")
        preflight = []
        for (procedure, binding), task in sorted(anchors.items()):
            _require_time(deadline)
            directory = output / "preflight" / f"procedure_{procedure}_binding_{binding}"
            reference = reference_task(task, directory / "reference", device=str(device))
            reference_check = verify_task(task, reference, reference)
            if reference.get("status") != "EXECUTED" or reference_check.get("success") is not True:
                raise ExecutionInfrastructureError("TRAIN_PREFLIGHT_DIRECT_REFERENCE_INVALID")
            public = permitted_view(task)
            execution = execute_task(public, rule_select(public), directory / "execution", device=str(device))
            checked = verify_task(task, execution, reference)
            preflight.append({"procedure": procedure, "binding": binding, "device": str(device),
                              "reference": reference_check, "execution": checked})
            _write(output / "training_anchor_gpu_preflight.json", preflight)
            if checked.get("success") is not True:
                raise ExecutionInfrastructureError("TRAIN_PREFLIGHT_AUTHORED_EXECUTION_INVALID")
            _check_output_budget(output)
        random.seed(config.seed)
        torch.manual_seed(config.seed)
        torch.cuda.manual_seed_all(config.seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
        cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=config.seed, device=device)
        _write(output / "parameter_matching_before_training.json", matching)
        checkpoint_records = {}
        training_timing = {}
        for family, model in (("cas", cas), ("generic", generic)):
            _require_time(deadline)
            record, timing = _timed_cuda(lambda: _train_family(model, family, tokenizer, train_tasks,
                                                               validation_tasks, output, config, device, deadline), device)
            checkpoint_records[family] = record
            training_timing[family] = timing
        if checkpoint_records["cas"]["optimizer_steps"] != checkpoint_records["generic"]["optimizer_steps"]:
            raise RuntimeError("MATCHED_TRAINING_STEPS_DIFFER")
        _write(output / "checkpoints.json", checkpoint_records)
        _write(output / "training_timing.json", training_timing)

        predictions, selection_timing = {}, {}
        for arm in ARMS:
            _require_time(deadline)
            if arm == "rule":
                before = time.perf_counter()
                predictions[arm] = [rule_select(public) for public in test_public]
                selection_timing[arm] = {"wall_seconds": time.perf_counter() - before,
                                         "device": "non-neural Python rule"}
            else:
                family = "cas" if arm.startswith("cas") else "generic"
                model = cas if family == "cas" else generic
                state = "initial" if arm.endswith("untrained") else "selected"
                _load_checkpoint(model, checkpoint_records[family][state], tokenizer, device)
                actions, timing = _timed_cuda(lambda: predict_public(model, tokenizer, test_public,
                                                                     device=device, batch_size=config.batch_size), device)
                predictions[arm], selection_timing[arm] = actions, timing
                selection_timing[arm]["test_neural_device"] = str(device)
            if len(predictions[arm]) != len(test_public):
                raise RuntimeError("PREDICTION_DENOMINATOR_MISMATCH")
        prediction_record = {"schema": "cas-meta1-sealed-test-predictions/1", "seed": config.seed,
                             "test_public_sha256": hashes["test_public.json"],
                             "tokenizer_digest": tokenizer.digest, "arms": predictions,
                             "selection_timing": selection_timing,
                             "public_case_digests": [canonical_sha256(public) for public in test_public]}
        prediction_path = output / "predictions.json"
        _write(prediction_path, prediction_record)
        prediction_digest = _file_hash(prediction_path)
        _write(output / "predictions_seal.json", {"sha256": prediction_digest,
               "sealed_utc": datetime.now(timezone.utc).isoformat(), "test_private_labels_loaded": False})

        # This is the FIRST parsing of held-out labels in the GPU run.
        if _file_hash(data / "test_private.json") != hashes["test_private.json"]:
            raise RuntimeError("TEST_PRIVATE_CHANGED_AFTER_PREDICTION_SEAL")
        test_tasks = _read(data / "test_private.json")
        if len(test_tasks) != len(test_public) or any(permitted_view(task) != public
                for task, public in zip(test_tasks, test_public, strict=True)):
            raise RuntimeError("TEST_PUBLIC_PRIVATE_BINDING_MISMATCH")
        _write(output / "test_gold_opening_receipt.json", {"opened_utc": datetime.now(timezone.utc).isoformat(),
               "prediction_sha256_before_opening": prediction_digest,
               "test_private_sha256": hashes["test_private.json"]})
        references = []
        reference_timings = []
        for index, task in enumerate(test_tasks):
            _require_time(deadline)
            reference, timing = _timed_cuda(lambda: reference_task(task, output / "references" / f"case_{index:04d}",
                                                                  device=str(device)), device)
            reference_check = verify_task(task, reference, reference)
            if reference.get("status") != "EXECUTED" or reference_check.get("success") is not True:
                _write(output / "reference_failure.json", {"case_index": index, "verification": reference_check,
                                                          "reference_status": reference.get("status")})
                raise ExecutionInfrastructureError("HELD_OUT_DIRECT_REFERENCE_INVALID")
            references.append(reference)
            reference_timings.append(timing)
            _check_output_budget(output)
        _write(output / "reference_timing.json", reference_timings)
        results = {}
        for arm in ARMS:
            rows = []
            for index, (task, public, action, reference) in enumerate(zip(test_tasks, test_public, predictions[arm], references, strict=True)):
                _require_time(deadline)
                case_output = output / "execution" / arm / f"case_{index:04d}"
                attempt_started = time.perf_counter()
                try:
                    result, timing = _timed_cuda(lambda: execute_task(public, action, case_output, device=str(device)), device)
                    verification = verify_task(task, result, reference)
                except ExecutionInfrastructureError:
                    raise
                except Exception as error:
                    # A GPU infrastructure loss stops the pilot; never silently run on CPU.
                    if "GPU_REQUIRED" in str(error) or "CUDA" in str(error) or "cuda" in str(error):
                        raise
                    result = {"status": "REJECTED", "failure": _failure(error), "reserved_policy_units": None}
                    timing = {"wall_seconds": time.perf_counter() - attempt_started,
                              "cuda_timing_unavailable_due_to_exception": True}
                    verification = {"success": False, "procedure_correct": action["procedure"] == task["target"]["procedure"],
                                    "binding_correct": action["binding"] == task["target"]["binding"],
                                    "repair_required": task["target"]["procedure"] == 2,
                                    "repair_correct": False, "output_correct": False, "evidence_valid": False,
                                    "reasons": ["EXECUTION_EXCEPTION"]}
                rows.append({"case_index": index, "action": action, "verification": verification,
                             "execution_status": result.get("status", "UNKNOWN"),
                             "failure": result.get("failure"), "reserved_policy_units": result.get("reserved_policy_units"),
                             "repair_count": result.get("repair_count"), "execution_timing": timing,
                             "evidence_directory": str(case_output)})
                _write(output / (arm + "_case_results.json"), rows)
                _check_output_budget(output)
            results[arm] = _aggregate(rows)
        if _file_hash(prediction_path) != prediction_digest:
            raise RuntimeError("SEALED_PREDICTIONS_CHANGED")
        baseline_after = {"source": verify_baseline(), "installed_wheels": verify_installed_wheels()}
        source_after = _source_identity()
        if source_after != source_before:
            raise RuntimeError("PILOT_SOURCE_CHANGED_DURING_RUN")
        matching["cas_active_trainable_parameters"] = checkpoint_records["cas"]["active_parameters"]["connected_trainable_parameters"]
        matching["generic_active_trainable_parameters"] = checkpoint_records["generic"]["active_parameters"]["connected_trainable_parameters"]
        receipt = {
            "status": "CAS_META_1_AWS_GPU_PILOT_COMPLETED", "seed": config.seed,
            "source": source_before, "dataset_sha256": hashes, "prediction_sha256": prediction_digest,
            "all_test_cases_executed_per_arm": len(test_tasks), "results": results,
            "cas_actual_success_gain": results["cas_trained"]["success_rate"] - results["cas_untrained"]["success_rate"],
            "generic_actual_success_gain": results["generic_trained"]["success_rate"] - results["generic_untrained"]["success_rate"],
            "parameter_matching": matching, "checkpoints": checkpoint_records,
            "training_timing": training_timing, "selection_timing": selection_timing,
            "total_wall_seconds": time.monotonic() - start,
            "output_disk_bytes_before_final_receipt": _check_output_budget(output),
            "output_disk_ceiling_bytes": MAX_OUTPUT_BYTES,
            "training_anchor_preflight_cases": len(preflight),
            "baseline_before": baseline_before, "baseline_after": baseline_after,
            "claim_boundary": "One synthetic curriculum, fixed executor, one preregistered seed. Not broad language, general reasoning, complete Fractals, CAS-specific advantage, or production readiness.",
            "reserved_units_boundary": "Frozen native policy-ceiling accounting; not FLOPs, energy, elapsed time, or GPU work."}
        _write(output / "receipt.json", receipt)
        _write(output / "payload_sha256.json", {str(path.relative_to(output)): _file_hash(path)
                                                for path in sorted(output.rglob("*")) if path.is_file()
                                                and path.name != "payload_sha256.json"})
        print(json.dumps({"status": receipt["status"], "results": results}, sort_keys=True), flush=True)
        return receipt
    except Exception as error:
        _write(output / "run_failure.json", {"status": "CAS_META_1_GPU_PILOT_BLOCKED",
               "failure": _failure(error), "wall_seconds": time.monotonic() - start,
               "completed": False, "automatic_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-wall-seconds", type=int, default=3300)
    arguments = parser.parse_args()
    run(arguments.data, arguments.output, TrainingConfig(seed=arguments.seed, epochs=arguments.epochs,
        batch_size=arguments.batch_size, max_wall_seconds=arguments.max_wall_seconds))


if __name__ == "__main__":
    main()
