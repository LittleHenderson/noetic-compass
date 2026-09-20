"""AWS-only v2 geometry checks, without optimizer updates or test-label access.

Importing this module is pure. Torch is imported only after both explicit AWS
flags are checked. This is a candidate implementation check, not learning,
native execution, checkpoint qualification, or a full memory-capacity proof.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import gc
import json
import math
import os
from pathlib import Path
import time
import traceback


class GPUPreflightError(RuntimeError):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _time_left(deadline):
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)
            or not time.monotonic() < deadline):
        raise GPUPreflightError("V2_GPU_PREFLIGHT_DEADLINE")


def _save(path, receipt):
    # The caller supplies an existing output directory; never replace evidence.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _device_checks(model, device):
    if any(value.device != device for value in model.parameters()):
        raise GPUPreflightError("V2_GPU_PREFLIGHT_PARAMETER_DEVICE_MISMATCH")
    if any(value.device != device for value in model.buffers()):
        raise GPUPreflightError("V2_GPU_PREFLIGHT_BUFFER_DEVICE_MISMATCH")


def _execute(train_tasks, config, receipt, deadline, torch, device):
    """Keep every model/tensor local, so the caller can clear memory afterward."""
    from torch.nn import functional as F
    from casformer import OperatingRegion
    from .codec import PAD_ID, action_to_ids, validate_action, validate_public
    from .features_v2 import LosslessPublicTokenizer
    from .policy import build_matched_policies, encode_batch, encode_targets

    config.validate()
    policy = config.policy
    if config.batch_size != 16 or policy.max_length != 1024:
        raise GPUPreflightError("V2_GPU_PREFLIGHT_REGISTERED_GEOMETRY_REQUIRED")
    if type(train_tasks) is not list or len(train_tasks) < config.batch_size:
        raise GPUPreflightError("V2_GPU_PREFLIGHT_TRAINING_BATCH_INCOMPLETE")
    receipt["config"] = asdict(config)
    receipt["stage"] = "training_text_encoding"
    _time_left(deadline)
    for task in train_tasks:
        validate_public(task["public"])
        validate_action(task["target"])
    tokenizer = LosslessPublicTokenizer.fit_train(
        [task["public"] for task in train_tasks], max_length=policy.max_length)
    input_lengths = [len(tokenizer.encode_public(task["public"])["ids"])
                     for task in train_tasks]
    action_lengths = [len(action_to_ids(task["target"], max_length=policy.max_action_length))
                      for task in train_tasks]
    indices = sorted(range(len(train_tasks)), key=lambda index: (-input_lengths[index], index))[:config.batch_size]
    selected = [train_tasks[index] for index in indices]
    receipt["geometry"] = {
        "selection": "Longest encoded training inputs; original row index breaks equal-length ties.",
        "training_examples": len(train_tasks), "batch_size": len(selected),
        "selected_training_indices": indices,
        "selected_input_lengths": [input_lengths[index] for index in indices],
        "selected_action_lengths_including_bos_eos": [action_lengths[index] for index in indices],
        "maximum_training_input_tokens": max(input_lengths),
        "maximum_training_action_tokens_including_bos_eos": max(action_lengths),
        "maximum_selected_action_tokens_including_bos_eos": max(action_lengths[index] for index in indices),
        "configured_input_limit": policy.max_length,
        "configured_action_limit": policy.max_action_length,
        "tokenizer_digest": tokenizer.digest, "vocabulary_size": len(tokenizer.vocabulary),
        "training_public_sha256": sha256(_canonical([task["public"] for task in train_tasks])).hexdigest(),
        "selected_target_sha256": sha256(_canonical([task["target"] for task in selected])).hexdigest(),
    }
    receipt["stage"] = "matched_candidate_construction"
    _time_left(deadline)
    cas, generic, matching = build_matched_policies(tokenizer, policy, seed=config.seed, device=device)
    receipt["parameter_matching"] = matching
    if matching["frozen_candidate_parameter_names"]:
        raise GPUPreflightError("V2_GPU_PREFLIGHT_UNEXPECTED_FROZEN_PARAMETERS")
    if matching["relative_difference"] > policy.max_parameter_mismatch_fraction:
        raise GPUPreflightError("V2_GPU_PREFLIGHT_PARAMETER_MATCH_FAILED")
    common = ("word_embedding.", "kind_embedding.", "slot_embedding.", "numeric_projection.",
              "action_embedding.", "decoder.", "decoder_norm.", "token_head.",
              "binding_query.", "binding_key.")
    generic_parameters = dict(generic.named_parameters())
    common_names = []
    for name, parameter in cas.named_parameters():
        if name.startswith(common):
            if name not in generic_parameters or not torch.equal(parameter, generic_parameters[name]):
                raise GPUPreflightError("V2_GPU_PREFLIGHT_COMMON_INITIAL_PARAMETERS_DIFFER:" + name)
            common_names.append(name)
    if not common_names:
        raise GPUPreflightError("V2_GPU_PREFLIGHT_COMMON_PARAMETERS_EMPTY")
    receipt["identical_common_initial_parameter_names"] = sorted(common_names)
    batch = encode_batch([task["public"] for task in selected], tokenizer, device=device)
    target = encode_targets([task["target"] for task in selected], device=device,
                            max_length=policy.max_action_length)
    receipt["geometry"]["actual_padded_input_tokens"] = int(batch["ids"].shape[1])
    receipt["geometry"]["actual_padded_target_tokens_excluding_bos"] = int(target["target_ids"].shape[1])
    receipt["families"] = {}
    for family, model in (("cas", cas), ("generic", generic)):
        receipt["stage"] = family + "_forward_backward"
        _time_left(deadline)
        _device_checks(model, device)
        model.train()
        model.zero_grad(set_to_none=True)
        started = time.monotonic()
        record = {"all_parameters_cuda": True, "all_buffers_cuda": True,
                  "optimizer_updates": 0, "gate_layers": []}
        receipt["families"][family] = record
        if family == "cas":
            memory, telemetry = model.encode_with_telemetry(batch)
            logits = model.decode(memory, batch, target["decoder_input_ids"])
            if len(telemetry) != policy.layers:
                raise GPUPreflightError("V2_GPU_PREFLIGHT_GATE_LAYER_COVERAGE")
            for index, observed in enumerate(telemetry):
                valid = batch["valid"][:, None, :].expand_as(observed.operating_region)
                active = (observed.operating_region == int(OperatingRegion.ACTIVE)) & valid
                per_head = active.sum(dim=(0, 2))
                valid_count = int(valid.sum().item())
                active_count = int(active.sum().item())
                fraction = active_count / valid_count
                gate = {"layer": index, "valid_queries": valid_count,
                        "active_queries": active_count, "active_fraction": fraction,
                        "active_queries_per_head": per_head.tolist(),
                        "gate_min": float(observed.cjt_gate[valid].min().item()),
                        "gate_max": float(observed.cjt_gate[valid].max().item()),
                        "total_current_min": float(observed.attention.total_current[valid].min().item()),
                        "total_current_max": float(observed.attention.total_current[valid].max().item())}
                record["gate_layers"].append(gate)
                if not bool((per_head > 0).all()) or fraction < 0.95:
                    raise GPUPreflightError("V2_GPU_PREFLIGHT_ACTIVE_GATE_REQUIREMENT:" + str(index))
        else:
            logits = model(batch, target["decoder_input_ids"])["token_logits"]
        _time_left(deadline)
        loss = F.cross_entropy(logits.flatten(0, 1), target["target_ids"].flatten(), ignore_index=PAD_ID)
        if not bool(torch.isfinite(loss)):
            raise GPUPreflightError("V2_GPU_PREFLIGHT_NONFINITE_LOSS:" + family)
        record["diagnostic_token_cross_entropy"] = float(loss.item())
        loss.backward()
        _time_left(deadline)
        missing = []
        connected = []
        for name, parameter in model.named_parameters():
            if parameter.requires_grad:
                if (parameter.grad is None or not bool(torch.isfinite(parameter.grad).all())
                        or not bool(parameter.grad.abs().sum() > 0)):
                    missing.append(name)
                else:
                    connected.append(name)
        record["finite_nonzero_gradient_parameter_names"] = sorted(connected)
        record["missing_or_invalid_gradient_parameter_names"] = sorted(missing)
        if missing:
            raise GPUPreflightError("V2_GPU_PREFLIGHT_GRADIENT_FAILURE:" + family + ":" + ",".join(missing))
        _device_checks(model, device)
        torch.cuda.synchronize(device)
        record["wall_seconds"] = time.monotonic() - started
        record["all_trainable_parameter_tensors_have_finite_nonzero_gradient"] = True
        record["peak_cuda_allocated_bytes_so_far"] = int(torch.cuda.max_memory_allocated(device))
        record["peak_cuda_reserved_bytes_so_far"] = int(torch.cuda.max_memory_reserved(device))
        del logits, loss
    receipt["stage"] = "geometry_checks_completed"


def run_preflight(train_tasks, config, output, deadline):
    """Check the registered v2 TrainingConfig on the actual longest train batch.

    Both CAS_META2_RUN_GPU_TESTS=1 and a CAS_META2_AWS_JOB_ID are required.
    The caller owns the overall process deadline and resource cutoff; checks
    here occur between stages and cannot interrupt an in-flight CUDA kernel.
    """
    directory = Path(output).resolve()
    path = directory / "gpu_preflight_v2.json"
    if not directory.is_dir() or path.exists():
        raise GPUPreflightError("V2_GPU_PREFLIGHT_NEW_RECEIPT_IN_EXISTING_OUTPUT_REQUIRED")
    started = time.monotonic()
    receipt = {
        "schema": "cas-meta2-gpu-preflight/2", "status": "CAS_META_2_V2_GPU_PREFLIGHT_RUNNING",
        "completed": False, "stage": "authorization", "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_training_performed": False, "optimizer_updates": 0,
        "native_execution_performed": False, "held_out_labels_accessed": False,
        "boundary": "Candidate training-geometry forward/backward check only. No learning result. Peak memory excludes AdamW state, open generation, and parallel native evaluation.",
    }
    torch_module = None
    device = None
    failure = None
    try:
        if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1" or not os.environ.get("CAS_META2_AWS_JOB_ID"):
            raise GPUPreflightError("V2_GPU_PREFLIGHT_AWS_AUTHORIZATION_REQUIRED")
        _time_left(deadline)
        import torch as torch_module
        from .policy import require_cuda
        device = require_cuda("cuda")
        receipt["aws_job_id"] = os.environ["CAS_META2_AWS_JOB_ID"]
        receipt["device"] = str(device)
        properties = torch_module.cuda.get_device_properties(device)
        receipt["gpu_name"] = properties.name
        receipt["gpu_total_memory_bytes"] = int(properties.total_memory)
        receipt["cuda_allocated_bytes_before"] = int(torch_module.cuda.memory_allocated(device))
        receipt["cuda_reserved_bytes_before"] = int(torch_module.cuda.memory_reserved(device))
        torch_module.cuda.reset_peak_memory_stats(device)
        _execute(train_tasks, config, receipt, deadline, torch_module, device)
        _time_left(deadline)
        receipt["completed"] = True
        receipt["status"] = "CAS_META_2_V2_GPU_PREFLIGHT_PASSED"
    except BaseException as error:
        failure = type(error).__name__ + ":" + str(error)
        receipt["status"] = "CAS_META_2_V2_GPU_PREFLIGHT_FAILED"
        receipt["failure"] = failure
        receipt["traceback"] = traceback.format_exc()
    # The exception scope and _execute frame have ended. No model/tensor is
    # returned or retained in the receipt; collect cycles before clearing cache.
    if torch_module is not None and device is not None:
        try:
            receipt["peak_cuda_allocated_bytes"] = int(torch_module.cuda.max_memory_allocated(device))
            receipt["peak_cuda_reserved_bytes"] = int(torch_module.cuda.max_memory_reserved(device))
            gc.collect()
            torch_module.cuda.empty_cache()
            torch_module.cuda.synchronize(device)
            receipt["cuda_allocated_bytes_after_cleanup"] = int(torch_module.cuda.memory_allocated(device))
            receipt["cuda_reserved_bytes_after_cleanup"] = int(torch_module.cuda.memory_reserved(device))
        except Exception as error:
            receipt["cleanup_failure"] = type(error).__name__ + ":" + str(error)
            failure = failure or receipt["cleanup_failure"]
            receipt["completed"] = False
            receipt["status"] = "CAS_META_2_V2_GPU_PREFLIGHT_FAILED"
    receipt["wall_seconds"] = time.monotonic() - started
    _save(path, receipt)
    if failure is not None:
        raise GPUPreflightError(failure) from None
    return receipt
