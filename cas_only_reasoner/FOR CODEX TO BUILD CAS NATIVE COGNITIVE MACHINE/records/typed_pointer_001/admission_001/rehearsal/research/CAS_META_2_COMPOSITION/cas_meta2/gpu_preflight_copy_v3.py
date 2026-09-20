"""Actual-copy-policy preflight, separate from frozen-v2 geometry receipts.

Pure imports and training-plan construction. Runtime authorization precedes
Torch and all models. Three stress batches select existing training rows by
input, target and occurrence length. No invented targets, optimizer steps,
private evaluation data, checkpoint promotion or native execution is used.
The separate launcher must bind AWS identity, source freeze and spending.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
import sys
import time

from . import gpu_preflight_v3 as cleanup_tools
from .codec import action_to_ids, canonical_sha256, validate_action, validate_public
from .features_v2 import LosslessPublicTokenizer
from .features_v3 import encode_public_with_spans
from .ir import validate_program
from .loss_v3 import LOSS_CONTRACT

ROOT = Path(__file__).absolute().parent
SCHEMA = "cas-meta2-copy-policy-gpu-preflight/3"
REGISTERED_TRAINING_ROWS = 3072
REGISTERED_BATCH_SIZE = 16
REGISTERED_POLICY = {"d_model": 64, "heads": 4, "layers": 2, "cas_ff_width": 128,
    "decoder_layers": 1, "decoder_ff_width": 128, "max_length": 1024, "max_action_length": 256,
    "cas_initial_saturation_per_max_token": 2.0, "max_parameter_mismatch_fraction": 0.01}
STRESS_BATCHES = ("longest_input", "longest_target", "most_copy_occurrences")
PINNED_FILES = {
    "__init__.py": "07b7b2f1a52806b819e3820655fa578f3e5241ce2327695f157e542ce06a63da",
    "codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
    "ir.py": "02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637",
    "features_v2.py": "79dd26ad6183cde7e586dda2cd1b65d812e601e793d5c60e0658ad886c09b4dc",
    "policy.py": "6d5f3cbfc455c65ef9000c5145f8f5b691668fb355339eeebd61e4aa2b8d26d0",
    "features_v3.py": "713fef0b3b04742550cfe11937bb76fe06f1913f91de8c85a56b07bfa4df6dbd",
    "policy_v3.py": "8a1e03a570df83063c75083b4da67aec6d3fd475730c9c59b4b686cd095baa23",
    "grammar_v3.py": "92bb1e400053c83daf0700dd782b9b5014f0da1c36f7e602133f7341cf5a2e7b",
    "selection_v2.py": "27a2b183d6c6e8d0a407156e13cac21c3d10d8e7917bba289824255c2d9a3816",
    "selection_v3.py": "4f8a1de2e1736d2de4ef0a74e13932b55197a26ce6a059eaa881501ad0b6c913",
    "loss_v3.py": "78cf75fc2c7ddcf637c9ce34755e679bf034da7830ea86643ca0b522df266f71",
    "gpu_preflight_v3.py": "6c9231bc19a5aeaaacab11bd3834091bb043318b3ef9a67fcb64ff36ab5b6740",
}


class CopyPreflightError(RuntimeError):
    pass


def _require(condition, reason):
    if not condition:
        raise CopyPreflightError(reason)


def _source_identity():
    for name, expected in PINNED_FILES.items():
        path = ROOT / name
        _require(path.is_file() and not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
            for item in (path, *path.parents)), "COPY_V3_SOURCE_PATH_INVALID:" + name)
        _require(sha256(path.read_bytes()).hexdigest() == expected, "COPY_V3_SOURCE_BYTES_CHANGED:" + name)
        module_name = "cas_meta2" if name == "__init__.py" else "cas_meta2." + path.stem
        loaded = sys.modules.get(module_name)
        if loaded is not None:
            _require(getattr(loaded, "__file__", None) is not None and Path(loaded.__file__).resolve() == path.resolve(),
                     "COPY_V3_LOADED_SOURCE_PATH_CHANGED:" + module_name)
    return {"files_sha256": dict(PINNED_FILES), "helper_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "factory": "cas_meta2.policy_v3.build_matched_policies",
        "encoding": "cas_meta2.policy_v3.encode_batch",
        "loss": "cas_meta2.loss_v3.weighted_training_loss",
        "cleanup": "Version-bound primitives from gpu_preflight_v3; its frozen-v2 geometry routine is NOT called.",
        "source_binding": "Literal dependency hashes and observed helper bytes; launch archive supplies the source-freeze SHA."}


def prepare_training_geometry(train_tasks, policy, *, batch_size=REGISTERED_BATCH_SIZE):
    """Pure plan; only actual caller-designated training rows are selected."""
    _require(type(policy) is dict and policy == REGISTERED_POLICY and
             all(type(policy[key]) is type(value) for key, value in REGISTERED_POLICY.items()),
             "COPY_V3_REGISTERED_POLICY_GEOMETRY_REQUIRED")
    _require(type(batch_size) is int and batch_size == REGISTERED_BATCH_SIZE,
             "COPY_V3_REGISTERED_BATCH16_REQUIRED")
    _require(type(train_tasks) is list and len(train_tasks) == REGISTERED_TRAINING_ROWS,
             "COPY_V3_REGISTERED_3072_TRAINING_ROWS_REQUIRED")
    depth_counts, task_ids, dataset_ids = {1: 0, 2: 0, 3: 0}, set(), set()
    for task in train_tasks:
        _require(type(task) is dict and "public" in task and "target" in task, "COPY_V3_TRAINING_ROW_INVALID")
        provenance = task.get("provenance")
        _require(task.get("split", "train") == "train" and type(provenance) is dict
                 and provenance.get("evaluation_group") == "training" and provenance.get("triplet_id") is None,
                 "COPY_V3_NONTRAINING_SPLIT_REFUSED")
        task_id = task.get("task_id")
        matched = re.fullmatch(r"meta2-v3-([a-f0-9]{16})-train-[0-9]{5}", task_id) if type(task_id) is str else None
        _require(matched is not None and task_id not in task_ids, "COPY_V3_EXPLICIT_UNIQUE_TRAIN_TASK_ID_REQUIRED")
        task_ids.add(task_id)
        dataset_ids.add(matched[1])
        validate_public(task["public"])
        validate_action(task["target"])
        depth = validate_program(task["target"]["program"])["max_call_depth"]
        _require(depth in depth_counts and type(provenance.get("depth")) is int and provenance["depth"] == depth,
                 "COPY_V3_ACTUAL_TRAINING_DEPTH_MISMATCH")
        depth_counts[depth] += 1
    _require(len(dataset_ids) == 1, "COPY_V3_MIXED_TRAINING_DATASET_IDS")
    _require(depth_counts == {1: 1024, 2: 1024, 3: 1024}, "COPY_V3_REGISTERED_TRAINING_DEPTH_COUNTS_REQUIRED")
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in train_tasks], max_length=policy["max_length"])
    featured = [encode_public_with_spans(task["public"], tokenizer) for task in train_tasks]
    inputs = [len(row["encoded"]["ids"]) for row in featured]
    occurrences = [len(row["occurrences"]) for row in featured]
    targets = [len(action_to_ids(task["target"], max_length=policy["max_action_length"])) for task in train_tasks]
    metrics = dict(zip(STRESS_BATCHES, (inputs, targets, occurrences)))
    batches = {}
    for label, metric in metrics.items():
        indices = sorted(range(len(train_tasks)), key=lambda index: (-metric[index], index))[:batch_size]
        batches[label] = {"selected_training_indices": indices,
            "selected_input_lengths": [inputs[index] for index in indices],
            "selected_target_lengths_including_bos_eos": [targets[index] for index in indices],
            "selected_copy_occurrence_counts": [occurrences[index] for index in indices],
            "actual_padded_input_tokens": max(inputs[index] for index in indices),
            "actual_padded_target_tokens_excluding_bos": max(targets[index] for index in indices) - 1,
            "actual_padded_copy_occurrences": max(1, max(occurrences[index] for index in indices)),
            "selected_public_sha256": canonical_sha256([train_tasks[index]["public"] for index in indices]),
            "selected_target_sha256": canonical_sha256([train_tasks[index]["target"] for index in indices])}
    return tokenizer, {"training_examples": len(train_tasks), "batch_size": batch_size,
        "actual_ir_depth_counts": {str(depth): count for depth, count in depth_counts.items()},
        "training_dataset_id_prefix": next(iter(dataset_ids)), "explicit_training_provenance_verified": True,
        "selection": "Three independent descending length/count sorts; original training row breaks ties. No synthetic or rewritten rows.",
        "tokenizer_digest": tokenizer.digest, "vocabulary_size": len(tokenizer.vocabulary),
        "training_tasks_sha256": canonical_sha256(train_tasks),
        "training_public_sha256": canonical_sha256([task["public"] for task in train_tasks]),
        "maximum_training_input_tokens": max(inputs), "maximum_training_target_tokens_including_bos_eos": max(targets),
        "maximum_training_copy_occurrences": max(occurrences), "stress_batches": batches}


def gate_summary(layer, active_counts, valid_counts):
    """Pure per-head gate accounting; aggregate activity cannot hide a bad head."""
    _require(type(layer) is int and 0 <= layer < REGISTERED_POLICY["layers"]
             and type(active_counts) is list and type(valid_counts) is list
             and len(active_counts) == len(valid_counts) == REGISTERED_POLICY["heads"],
             "COPY_V3_GATE_COUNTER_GEOMETRY_INVALID")
    _require(all(type(active) is int and type(valid) is int and valid > 0 and 0 <= active <= valid
                 for active, valid in zip(active_counts, valid_counts)), "COPY_V3_GATE_COUNTER_VALUE_INVALID")
    fractions = [active / valid for active, valid in zip(active_counts, valid_counts)]
    return {"layer": layer, "valid_queries": sum(valid_counts), "active_queries": sum(active_counts),
        "active_fraction": sum(active_counts) / sum(valid_counts),
        "valid_queries_per_head": valid_counts, "active_queries_per_head": active_counts,
        "active_fraction_per_head": fractions, "all_heads_meet_active_fraction": all(value >= 0.95 for value in fractions)}


def _initial_matching(models, matching, torch):
    parameters = {family: dict(model.named_parameters()) for family, model in models.items()}
    counts = {family: sum(value.numel() for value in rows.values() if value.requires_grad) for family, rows in parameters.items()}
    _require(all(value.requires_grad for rows in parameters.values() for value in rows.values()), "COPY_V3_UNEXPECTED_FROZEN_PARAMETER")
    _require(counts["cas"] == matching["cas_trainable_parameters"] and counts["generic"] == matching["generic_trainable_parameters"],
             "COPY_V3_PARAMETER_COUNT_RECEIPT_MISMATCH")
    _require(abs(counts["cas"] - counts["generic"]) / counts["cas"] <= 0.01, "COPY_V3_PARAMETER_MATCH_FAILED")
    excluded = ("encoder.", "control_adapter.", "final_norm.")
    common = {family: {name for name in rows if not name.startswith(excluded)} for family, rows in parameters.items()}
    _require(common["cas"] == common["generic"] == set(matching["common_initial_parameter_names"]),
             "COPY_V3_SHARED_PARAMETER_SET_MISMATCH")
    _require({"copy_query.weight", "copy_key.weight", "copy_gate.weight", "copy_gate.bias"}.issubset(common["cas"]),
             "COPY_V3_COPY_PARAMETERS_MISSING")
    for name in common["cas"]:
        _require(torch.equal(parameters["cas"][name], parameters["generic"][name]), "COPY_V3_SHARED_INITIAL_PARAMETER_MISMATCH:" + name)
    buffers = {family: dict(model.named_buffers()) for family, model in models.items()}
    common_buffers = sorted(set(buffers["cas"]) & set(buffers["generic"]))
    for name in common_buffers:
        _require(torch.equal(buffers["cas"][name], buffers["generic"][name]), "COPY_V3_SHARED_INITIAL_BUFFER_MISMATCH:" + name)
    return {"counts": counts, "identical_common_initial_parameter_names": sorted(common["cas"]),
            "identical_common_initial_buffer_names": common_buffers}


def _check_stress_batch(models, train_tasks, tokenizer, geometry, receipt, deadline, torch, device):
    from casformer import OperatingRegion
    from .codec import ACTION_TO_ID
    from .loss_v3 import encode_loss_weights, weighted_training_loss
    from .policy_v3 import encode_batch, encode_targets
    selected = [train_tasks[index] for index in geometry["selected_training_indices"]]
    batch = encode_batch([task["public"] for task in selected], tokenizer, device=device)
    target = encode_targets([task["target"] for task in selected], device=device, max_length=REGISTERED_POLICY["max_action_length"])
    weights = encode_loss_weights([task["target"] for task in selected], target, device=device,
                                  max_length=REGISTERED_POLICY["max_action_length"])
    _require(batch["ids"].shape == (REGISTERED_BATCH_SIZE, geometry["actual_padded_input_tokens"])
             and target["target_ids"].shape == (REGISTERED_BATCH_SIZE, geometry["actual_padded_target_tokens_excluding_bos"])
             and batch["copy_valid"].shape == (REGISTERED_BATCH_SIZE, geometry["actual_padded_copy_occurrences"]),
             "COPY_V3_OBSERVED_BATCH_GEOMETRY_MISMATCH")
    receipt["positive_loss_weight_sum"] = float(weights.sum())
    receipt["families"] = {}
    for family, model in models.items():
        cleanup_tools._time_left(deadline)
        model._check_device(*batch.values(), *target.values(), weights)
        model.train()
        model.zero_grad(set_to_none=True)
        record = {"all_parameters_cuda": True, "all_buffers_cuda": True, "optimizer_updates": 0, "gate_layers": []}
        receipt["families"][family] = record
        if family == "cas":
            memory, telemetry = model.encode_with_telemetry(batch)
            _require(len(telemetry) == REGISTERED_POLICY["layers"], "COPY_V3_GATE_LAYER_COVERAGE")
            for index, observed in enumerate(telemetry):
                valid = batch["valid"][:, None, :].expand_as(observed.operating_region)
                active = (observed.operating_region == int(OperatingRegion.ACTIVE)) & valid
                gate = gate_summary(index, active.sum(dim=(0, 2)).tolist(), valid.sum(dim=(0, 2)).tolist())
                record["gate_layers"].append(gate)
                _require(gate["all_heads_meet_active_fraction"], "COPY_V3_ACTIVE_GATE_REQUIREMENT:" + str(index))
        else:
            memory = model.encode(batch)
        result = model.decode_with_telemetry(memory, batch, target["decoder_input_ids"])
        loss = weighted_training_loss(result["token_logits"], target, weights)
        record["weighted_training_loss"] = float(loss)
        record["copy_gate_min"] = float(result["copy_gate"].min())
        record["copy_gate_max"] = float(result["copy_gate"].max())
        loss.backward()
        cleanup_tools._time_left(deadline)
        missing, connected = [], []
        for name, parameter in model.named_parameters():
            if parameter.requires_grad:
                if (parameter.grad is None or not bool(torch.isfinite(parameter.grad).all())
                        or not bool(parameter.grad.abs().sum() > 0)):
                    missing.append(name)
                else:
                    connected.append(name)
        record["finite_nonzero_gradient_parameter_names"] = sorted(connected)
        record["missing_or_invalid_gradient_parameter_names"] = sorted(missing)
        _require(not missing, "COPY_V3_ACTIVE_GRADIENT_FAILURE:" + family + ":" + ",".join(missing))
        record["all_trainable_parameter_tensors_have_finite_nonzero_gradient"] = True
        with torch.no_grad():
            prefix = target["decoder_input_ids"]
            changed = prefix.clone()
            changed[:, -3:] = ACTION_TO_ID["v31"]
            before = model.decode_with_telemetry(memory.detach(), batch, prefix)
            after = model.decode_with_telemetry(memory.detach(), batch, changed)
            for field in ("token_logits", "occurrence_probabilities", "copy_gate"):
                _require(torch.allclose(before[field][:, :-3], after[field][:, :-3], atol=1e-6, rtol=1e-6),
                         "COPY_V3_DECODER_FUTURE_TOKEN_LEAK:" + family + ":" + field)
        record["causal_future_token_check"] = True
        model._check_device(*batch.values(), *target.values(), weights)
        torch.cuda.synchronize(device)
        record["peak_cuda_allocated_bytes_so_far"] = int(torch.cuda.max_memory_allocated(device))
        record["peak_cuda_reserved_bytes_so_far"] = int(torch.cuda.max_memory_reserved(device))
        model.zero_grad(set_to_none=True)
        del memory, result, loss, before, after, prefix, changed


def _execute(train_tasks, config, receipt, deadline, torch, device):
    from .policy_v3 import build_matched_policies
    config.validate()
    config_record = asdict(config)
    receipt["config"] = config_record
    _require(type(config_record.get("training_examples_per_depth")) is int
             and config_record["training_examples_per_depth"] == 1024, "COPY_V3_REGISTERED_TRAINING_CONFIG_REQUIRED")
    receipt["stage"] = "training_geometry"
    tokenizer, geometry = prepare_training_geometry(train_tasks, config_record["policy"], batch_size=config_record["batch_size"])
    receipt["geometry"] = geometry
    cleanup_tools._time_left(deadline)
    receipt["stage"] = "actual_copy_candidate_construction"
    cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=config.seed, device=device)
    models = {"cas": cas, "generic": generic}
    receipt["parameter_matching"] = matching
    receipt["initial_matching"] = _initial_matching(models, matching, torch)
    receipt["stress_batches"] = {}
    for label in STRESS_BATCHES:
        cleanup_tools._time_left(deadline)
        receipt["stage"] = "stress_batch:" + label
        record = {"geometry": geometry["stress_batches"][label]}
        receipt["stress_batches"][label] = record
        _check_stress_batch(models, train_tasks, tokenizer, geometry["stress_batches"][label], record, deadline, torch, device)
    receipt["stage"] = "geometry_checks_completed"


def _new_receipt_path(output):
    raw = Path(output).absolute() / "gpu_preflight_copy_v3.json"
    _require(not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
        for item in (raw, *raw.parents)), "COPY_V3_RECEIPT_LINK_REFUSED")
    directory = raw.parent.resolve()
    path = directory / raw.name
    _require(directory.is_dir() and not path.exists(), "COPY_V3_NEW_RECEIPT_IN_EXISTING_DIRECTORY_REQUIRED")
    return path


def run_preflight(train_tasks, config, output, deadline):
    path = _new_receipt_path(output)
    started = time.monotonic()
    receipt = {"schema": SCHEMA, "status": "CAS_META_2_COPY_V3_GPU_PREFLIGHT_RUNNING", "completed": False,
        "stage": "authorization", "started_utc": datetime.now(timezone.utc).isoformat(),
        "helper_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "loss_contract": dict(LOSS_CONTRACT),
        "candidate_only": True, "actual_copy_policy": True, "frozen_v2_geometry_called": False,
        "geometry_checks_completed": False, "optimizer_updates": 0, "model_training_performed": False,
        "native_execution_performed": False, "held_out_labels_accessed": False,
        "memory_contract": "Idle single-visible-GPU process; normalized baseline and final live allocations must both be zero.",
        "boundary": "Training-only forward/backward candidate checks. Not learning or release acceptance. No optimizer-state, open-generation or native-evaluation memory-capacity claim."}
    runtime, device = None, None
    try:
        job = os.environ.get("CAS_META2_AWS_JOB_ID", "")
        _require(os.environ.get("CAS_META2_RUN_GPU_TESTS") == "1" and re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", job) is not None,
                 "COPY_V3_AWS_PREFLIGHT_AUTHORIZATION_REQUIRED")
        receipt["aws_job_id"] = job
        cleanup_tools._time_left(deadline)
        receipt["geometry_source"] = _source_identity()
        receipt["stage"] = "runtime_guard"
        runtime = cleanup_tools._load_runtime()
        device = cleanup_tools._checked_runtime(runtime, receipt)
        receipt["stage"] = "baseline_cleanup"
        receipt["entry_memory"] = cleanup_tools._memory(runtime, device)
        baseline = cleanup_tools._cleanup(runtime, device, receipt, "baseline")
        receipt["cuda_allocated_bytes_before"] = baseline["allocated_bytes"]
        receipt["cuda_reserved_bytes_before"] = baseline["reserved_bytes"]
        _require(baseline["allocated_bytes"] == 0, "COPY_V3_PROCESS_NOT_IDLE_LIVE_ALLOCATIONS")
        runtime.cuda.reset_peak_memory_stats(device)
        cleanup_tools._time_left(deadline)
        receipt["stage"] = "actual_copy_geometry_checks"
        _execute(train_tasks, config, receipt, deadline, runtime, device)
        receipt["geometry_checks_completed"] = True
        _require(canonical_sha256(train_tasks) == receipt["geometry"]["training_tasks_sha256"],
                 "COPY_V3_TRAINING_INPUT_CHANGED_DURING_CHECK")
        receipt["training_tasks_unchanged"] = True
        cleanup_tools._time_left(deadline)
        _require(_source_identity() == receipt["geometry_source"], "COPY_V3_SOURCE_CHANGED_DURING_CHECK")
    except BaseException as error:
        cleanup_tools._failure(receipt, receipt["stage"], error)
    # No model-containing execution or exception frame is retained here.
    if runtime is not None and device is not None:
        receipt["stage"] = "final_cleanup"
        try:
            allocated = runtime.cuda.max_memory_allocated(device)
            reserved = runtime.cuda.max_memory_reserved(device)
            receipt["peak_cuda_allocated_bytes"] = allocated
            receipt["peak_cuda_reserved_bytes"] = reserved
            final = cleanup_tools._cleanup(runtime, device, receipt, "final")
            receipt["cuda_allocated_bytes_after_cleanup"] = final["allocated_bytes"]
            receipt["cuda_reserved_bytes_after_cleanup"] = final["reserved_bytes"]
            _require(final["allocated_bytes"] == receipt.get("cuda_allocated_bytes_before") == 0,
                     "COPY_V3_MEMORY_CLEANUP_UNCONFIRMED")
            receipt["memory_cleanup_confirmed"] = True
            after = cleanup_tools._settings(runtime)
            receipt["numerical_settings_after"] = after
            _require(after == receipt["numerical_settings_before"], "COPY_V3_NUMERICAL_SETTINGS_CHANGED")
            _require(_source_identity() == receipt["geometry_source"], "COPY_V3_SOURCE_CHANGED_DURING_CLEANUP")
            _require(type(allocated) is int and type(reserved) is int
                     and 0 < allocated <= reserved <= receipt["gpu_total_memory_bytes"], "COPY_V3_PEAK_MEMORY_COUNTERS_INVALID")
            cleanup_tools._time_left(deadline)
        except BaseException as error:
            cleanup_tools._failure(receipt, receipt["stage"], error)
    passed = receipt["geometry_checks_completed"] and receipt.get("memory_cleanup_confirmed") is True and not receipt.get("failures")
    receipt.update(completed=bool(passed), stage="completed" if passed else "failed",
        status="CAS_META_2_COPY_V3_GPU_PREFLIGHT_PASSED" if passed else "CAS_META_2_COPY_V3_GPU_PREFLIGHT_FAILED",
        wall_seconds=time.monotonic() - started)
    receipt, invalid = cleanup_tools._safe_diagnostics(receipt)
    if invalid:
        passed = False
        receipt.update(completed=False, stage="failed", status="CAS_META_2_COPY_V3_GPU_PREFLIGHT_FAILED")
        receipt.setdefault("failures", []).append({"stage": "receipt_serialization", "type": "ValueError",
            "message": "COPY_V3_INVALID_DIAGNOSTIC_METRIC", "metric_paths": invalid})
    cleanup_tools._save(path, receipt)
    if not passed:
        raise CopyPreflightError(receipt["failures"][0]["message"]) from None
    return receipt
